"""Task-local regctl and a no-network scratch build; no daemon trust changes."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tarfile

from m0_local import RUNTIME, docker, write_private
from m0_registry import ORG, SOURCE_BYTES, contract, read_manifest, read_blob, sha


def client_path(value):
    path = Path(value).resolve()
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != contract()['client']['sha256']:
        raise ValueError('regctl binary does not match the pinned official asset')
    return path


def client_env(pat):
    config = RUNTIME / 'regctl.json'
    write_private(config, json.dumps({'version': 1, 'incDockerCert': False, 'incDockerCred': False, 'blobLimit': 2_000_000,
                                      'hosts': {'localhost:18443': {'tls': 'enabled', 'regcert': (RUNTIME / 'ca.crt').read_text(),
                                                                   'user': pat['user'], 'pass': pat['value']}}}))
    folder = RUNTIME / 'docker-client-config'; folder.mkdir(mode=0o700, exist_ok=True)
    write_private(folder / 'config.json', json.dumps({'auths': {}}))
    env = dict(os.environ, REGCTL_CONFIG=str(config), DOCKER_CONFIG=str(folder))
    env.pop('DOCKER_AUTH_CONFIG', None)
    return env


def cli(path, env, *args):
    try:
        result = subprocess.run([str(path), *args], env=env, capture_output=True, timeout=60)
    except subprocess.TimeoutExpired:
        raise RuntimeError('regctl result unknown after timeout; do not repeat a write') from None
    if result.returncode:
        write_private(RUNTIME / 'regctl-error.txt', result.stderr[:100_000])
        raise RuntimeError('regctl operation failed; private diagnostic saved, do not blindly retry')
    return result.stdout


def real_client_checks(owner, client, binary, pat, registry_token, source_sha, record):
    path = client_path(binary); env = client_env(pat)
    version = cli(path, env, 'version').decode()
    if 'VCSTag:     v0.11.7' not in version or 'Platform:   darwin/arm64' not in version:
        raise RuntimeError('regctl version/platform differs from the pinned client')
    untrusted = json.loads((RUNTIME / 'regctl.json').read_text())
    del untrusted['hosts']['localhost:18443']['regcert']
    write_private(RUNTIME / 'regctl-untrusted.json', json.dumps(untrusted))
    negative_env = dict(env, REGCTL_CONFIG=str(RUNTIME / 'regctl-untrusted.json'))
    negative = subprocess.run([str(path), 'image', 'digest', 'localhost:18443/' + ORG + '/m0-built:m0-cli'],
                              env=negative_env, capture_output=True, timeout=15)
    if negative.returncode == 0 or b'x509' not in negative.stderr.lower():
        raise RuntimeError('regctl without the task CA did not reject the TLS certificate')
    record('regctl_requires_task_ca_without_system_trust_changes', tls_error_verified=True, exit_code=negative.returncode)
    folder = RUNTIME / 'oci-build'; folder.mkdir(mode=0o700)
    write_private(folder / 'm0-source.txt', SOURCE_BYTES)
    write_private(folder / 'Dockerfile', 'FROM scratch\nCOPY m0-source.txt /m0-source.txt\n')
    build_tag, pulled_tag = owner['project'] + ':built', owner['project'] + ':pulled'
    image_label = 'io.radishforge.m0.project'
    archive, pulled = RUNTIME / 'oci-built.tar', RUNTIME / 'oci-pulled.tar'
    created = []
    for tag in (build_tag, pulled_tag):
        if docker(owner, 'image', 'inspect', tag, check=False).returncode == 0:
            raise RuntimeError('Refusing to overwrite an existing task image tag')
    try:
        build_state = RUNTIME / 'buildx'; build_state.mkdir(mode=0o700)
        build_env = dict(os.environ, BUILDX_CONFIG=str(build_state))
        build_env.pop('BUILDX_BUILDER', None)
        try:
            built = subprocess.run(['docker', '--context', owner['context'], 'build', '--builder', owner['context'],
                                    '--network=none', '--pull=false', '--provenance=false', '--tag', build_tag,
                                    '--label', image_label + '=' + owner['project'],
                                    '--label', 'org.opencontainers.image.revision=' + source_sha, str(folder)],
                                   env=build_env, capture_output=True, timeout=60)
        except subprocess.TimeoutExpired:
            raise RuntimeError('Docker build result unknown; inspect builder state before recovery') from None
        if built.returncode:
            write_private(RUNTIME / 'docker-build-error.txt', built.stderr[:100_000])
            raise RuntimeError('Docker build failed; private diagnostic saved')
        created.append(build_tag)
        initial = json.loads(docker(owner, 'image', 'inspect', build_tag).stdout)[0]
        if initial['Config']['Labels'].get(image_label) != owner['project']:
            raise RuntimeError('Built image ownership differs')
        docker(owner, 'image', 'save', '--output', str(archive), build_tag, timeout=60)
        archive.chmod(0o600)
        if archive.stat().st_size > 2_000_000:
            raise RuntimeError('Synthetic image archive exceeds its fixture bound')
        ref = 'localhost:18443/' + ORG + '/m0-built:m0-cli'
        # Positive transfers only. Any CLI failure/timeout stops; never invoke import again as recovery.
        cli(path, env, 'image', 'import', ref, str(archive), '--name', build_tag)
        digest = cli(path, env, 'image', 'digest', ref).decode().strip()
        actual, manifest, raw = read_manifest(client, registry_token, digest, image=ORG + '/m0-built')
        if actual != digest:
            raise RuntimeError('CLI and Registry disagree on the manifest Digest')
        if manifest.get('schemaVersion') != 2 or not isinstance(manifest.get('layers'), list) or not manifest['layers']:
            raise RuntimeError('CLI image is not a concrete single-platform image manifest')
        for desc in [manifest['config'], *manifest['layers']]:
            data = read_blob(client, registry_token, desc['digest'], image=ORG + '/m0-built')
            if len(data) != desc['size']:
                raise RuntimeError('CLI image descriptor length differs')
        cli(path, env, 'image', 'export', ref.split(':m0-cli')[0] + '@' + digest, str(pulled), '--name', pulled_tag)
        pulled.chmod(0o600)
        if pulled.stat().st_size > 2_000_000:
            raise RuntimeError('Pulled image archive exceeds its fixture bound')
        verified_blobs = 0
        with tarfile.open(pulled) as stream:
            for member in stream:
                if member.size > 2_000_000:
                    raise RuntimeError('Exported image member exceeds its fixture bound')
                if member.isfile() and member.name.startswith('blobs/sha256/'):
                    data = stream.extractfile(member).read(2_000_001)
                    if sha(data) != 'sha256:' + member.name.split('/')[-1]:
                        raise RuntimeError('Exported content-addressed member differs')
                    verified_blobs += 1
        docker(owner, 'image', 'load', '--input', str(pulled), timeout=60)
        created.append(pulled_tag)
        loaded = json.loads(docker(owner, 'image', 'inspect', pulled_tag).stdout)[0]
        if loaded['Id'] != initial['Id'] or loaded['Config']['Labels'].get('org.opencontainers.image.revision') != source_sha:
            raise RuntimeError('Fixed-Digest pull did not restore the built source image config')
        record('docker_build_regctl_push_and_fixed_digest_pull', source_sha=source_sha, manifest_digest=digest,
               built_image_id=initial['Id'], loaded_image_id=loaded['Id'], registry_config_digest=manifest['config']['digest'],
               registry_manifest_bytes=len(raw),
               archive_bytes=archive.stat().st_size, pulled_bytes=pulled.stat().st_size,
               exported_content_addressed_blobs_verified=verified_blobs, registry_tls='enabled with task CA',
               client='regctl v0.11.7 darwin/arm64', client_asset_sha256=contract()['client']['sha256'],
               docker_push_pull_used=False, build_network='none', runner_run_id=None)
    finally:
        removed = []
        for tag in (pulled_tag, build_tag):
            result = docker(owner, 'image', 'inspect', tag, check=False)
            if result.returncode:
                continue
            info = json.loads(result.stdout)[0]
            if info['Config']['Labels'].get(image_label) != owner['project']:
                raise RuntimeError('Refusing to delete an image without the task ownership label')
            docker(owner, 'image', 'rm', tag)
            removed.append(tag)
        record('task_built_and_loaded_image_tags_removed', created_tags=created, removed_tags=removed, shared_builder_cache_pruned=False)
