#!/usr/bin/env python3
"""Local upstream contract environment; Python standard library, explicit Docker context."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import secrets
import shutil
import socket
import ssl
import subprocess
import tarfile
import time
import urllib.request

from m0_scope import PROFILE_PATH, load_contract

ROOT = Path(__file__).resolve().parent.parent
COMPOSE = ROOT / 'tests/contracts/m0/compose.yaml'
RUNTIME = ROOT / '.local/m0'
MARKER = RUNTIME / 'owner.json'
SERVICES = ('postgres', 'forge', 'idp')


def command(args, *, data=None, timeout=60, check=True):
    result = subprocess.run(args, input=data, capture_output=True, timeout=timeout)
    if check and result.returncode:
        # Raw command output can contain generated credentials; do not print it.
        raise RuntimeError(f'{args[0]} failed (exit {result.returncode}); raw output withheld')
    return result


def state():
    data = json.loads(MARKER.read_text())
    if (RUNTIME.resolve().parent != (ROOT / '.local').resolve()
            or data['repository'] != str(ROOT)
            or not data['project'].startswith('rf-m0-local-')
            or len(data['project']) != len('rf-m0-local-') + 8):
        raise RuntimeError('Runtime ownership marker is invalid')
    return data


def docker(owner, *args, **kwargs):
    return command(['docker', '--context', owner['context'], *args], **kwargs)


def compose(owner, *args, **kwargs):
    return docker(owner, 'compose', '--project-name', owner['project'],
                  '--project-directory', str(COMPOSE.parent),
                  '--env-file', str(RUNTIME / 'compose.env'), '-f', str(COMPOSE),
                  *args, **kwargs)


def write_private(path, content):
    path.write_bytes(content.encode() if isinstance(content, str) else content)
    path.chmod(0o600)


def prepare(context, auth_profile=False):
    if RUNTIME.exists():
        raise RuntimeError('Runtime directory already exists; inspect ownership before continuing')
    server = command(['docker', '--context', context, 'version', '--format', '{{json .Server}}'])
    version = json.loads(server.stdout)
    if (version['Os'], version['Arch']) != ('linux', 'arm64'):
        raise RuntimeError('This local candidate requires a linux/arm64 daemon')
    for port in (18443, 19443):
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', port))
    RUNTIME.mkdir(parents=True, mode=0o700)
    RUNTIME.chmod(0o700)
    data = {'repository': str(ROOT), 'context': context,
            'project': 'rf-m0-local-' + secrets.token_hex(4),
            'server': {k: version[k] for k in ('Version', 'Os', 'Arch', 'KernelVersion')},
            'auth_profile': auth_profile,
            'auth_profile_sha256': hashlib.sha256(PROFILE_PATH.read_bytes()).hexdigest() if auth_profile else None}
    write_private(MARKER, json.dumps(data, indent=2) + '\n')
    write_private(RUNTIME / 'compose.env', '# Explicit empty environment; no automatic .env loading.\n')
    command(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-noenc',
             '-keyout', str(RUNTIME / 'ca.key'), '-out', str(RUNTIME / 'ca.crt'),
             '-days', '2', '-subj', '/CN=RadishForge M0 transient CA',
             '-addext', 'basicConstraints=critical,CA:TRUE',
             '-addext', 'keyUsage=critical,keyCertSign,cRLSign',
             '-addext', 'subjectKeyIdentifier=hash'])
    command(['openssl', 'req', '-new', '-newkey', 'rsa:2048', '-noenc',
             '-keyout', str(RUNTIME / 'server.key'), '-out', str(RUNTIME / 'server.csr'),
             '-subj', '/CN=localhost'])
    write_private(RUNTIME / 'tls.ext',
                  'subjectAltName=DNS:localhost,IP:127.0.0.1\n'
                  'basicConstraints=critical,CA:FALSE\n'
                  'keyUsage=critical,digitalSignature,keyEncipherment\n'
                  'subjectKeyIdentifier=hash\n'
                  'authorityKeyIdentifier=keyid:always,issuer\n'
                  'extendedKeyUsage=serverAuth\n')
    command(['openssl', 'x509', '-req', '-in', str(RUNTIME / 'server.csr'),
             '-CA', str(RUNTIME / 'ca.crt'), '-CAkey', str(RUNTIME / 'ca.key'),
             '-CAcreateserial', '-out', str(RUNTIME / 'server.crt'), '-days', '2',
             '-sha256', '-extfile', str(RUNTIME / 'tls.ext')])
    for p in RUNTIME.iterdir():
        if p.is_file():
            p.chmod(0o600)
    passwords = {name: secrets.token_hex(24) for name in ('bootstrap', 'forge', 'idp')}
    oauth_settings = ''
    if auth_profile:
        settings = load_contract()['test_provider_settings']
        oauth_settings = ''.join(f'{key} = {str(value).lower() if type(value) is bool else value}\n'
                                 for key, value in settings.items())
    seed = {}
    for name, port in (('forge', 18443), ('idp', 19443)):
        seed[f'{name}/app.ini'] = f'''APP_NAME = RadishForge M0 {name}
RUN_USER = git
WORK_PATH = /var/lib/gitea
[server]
PROTOCOL = https
HTTP_ADDR = 0.0.0.0
HTTP_PORT = 3000
ROOT_URL = https://localhost:{port}/
DOMAIN = localhost
CERT_FILE = /etc/gitea/server.crt
KEY_FILE = /etc/gitea/server.key
DISABLE_SSH = true
OFFLINE_MODE = true
[database]
DB_TYPE = postgres
HOST = postgres:5432
NAME = m0_{name}
USER = m0_{name}
PASSWD = {passwords[name]}
SSL_MODE = disable
[security]
INSTALL_LOCK = true
SECRET_KEY = {secrets.token_hex(32)}
INTERNAL_TOKEN = {secrets.token_hex(48)}
[service]
DISABLE_REGISTRATION = true
REQUIRE_SIGNIN_VIEW = true
[actions]
ENABLED = false
[oauth2]
ENABLED = true
JWT_SIGNING_ALGORITHM = RS256
{oauth_settings}[log]
MODE = console
LEVEL = Warn
'''.encode()
        for filename in ('server.key', 'server.crt', 'ca.crt'):
            seed[f'{name}/{filename}'] = (RUNTIME / filename).read_bytes()
    for name, password in passwords.items():
        seed[f'database/{name}-password'] = password.encode()
    with tarfile.open(RUNTIME / 'seed.tar', 'w') as archive:
        for name, raw in seed.items():
            entry = tarfile.TarInfo(name)
            entry.size, entry.mode = len(raw), 0o600
            archive.addfile(entry, io.BytesIO(raw))
    (RUNTIME / 'seed.tar').chmod(0o600)
    compose(data, 'config', '--quiet')
    print(json.dumps({'prepared': True, 'context': context, 'project': data['project'],
                      'runtime': str(RUNTIME), 'runner': 'absent'}, ensure_ascii=False))


def pull(data):
    result = compose(data, 'pull', *SERVICES, timeout=600, check=False)
    # Pull errors contain no runtime configuration or credentials; retain useful diagnostics.
    if result.returncode:
        print(result.stderr.decode(errors='replace')[-6000:])
        raise RuntimeError(f'Pinned image pull failed (exit {result.returncode}); no version fallback')
    print('Pinned platform images pulled; Runner was not requested.')


def up(data):
    # Refuse to overwrite live or previously initialized task data.
    existing = docker(data, 'ps', '-aq', '--filter', f'label=com.docker.compose.project={data["project"]}')
    volumes = docker(data, 'volume', 'ls', '-q', '--filter', f'label=com.docker.compose.project={data["project"]}')
    if existing.stdout.strip() or volumes.stdout.strip():
        raise RuntimeError('Task containers or volumes already exist; inspect rather than reseed')
    compose(data, '--profile', 'prepare', 'run', '--rm', '--no-deps', '-T', 'seed',
            data=(RUNTIME / 'seed.tar').read_bytes(), timeout=60)
    compose(data, 'up', '-d', '--pull', 'never', *SERVICES, timeout=120)
    trust = ssl.create_default_context(cafile=str(RUNTIME / 'ca.crt'))
    for service, port in (('forge', 18443), ('idp', 19443)):
        last = None
        for _ in range(60):
            try:
                with urllib.request.urlopen(f'https://localhost:{port}/api/healthz',
                                            context=trust, timeout=3) as response:
                    health = json.load(response)
                if health.get('status') != 'pass':
                    raise RuntimeError('Gitea health endpoint reports failure')
                version = compose(data, 'exec', '-T', service, 'gitea', '--version').stdout.decode()
                if not version.startswith('gitea version 28.2.0 '):
                    raise RuntimeError('Running Gitea version differs from candidate')
                break
            except (OSError, ValueError) as exc:
                last = type(exc).__name__
                time.sleep(1)
        else:
            raise RuntimeError(f'HTTPS readiness failed on port {port}: {last}')
    print('Both Gitea instances ready over verified local TLS; no system CA changed.')


def cleanup(data):
    compose(data, 'down', '--volumes', '--remove-orphans', timeout=120)
    if docker(data, 'ps', '-aq', '--filter', f'label=com.docker.compose.project={data["project"]}').stdout.strip():
        raise RuntimeError('Task containers remain; refusing to remove runtime marker')
    if docker(data, 'volume', 'ls', '-q', '--filter', f'label=com.docker.compose.project={data["project"]}').stdout.strip():
        raise RuntimeError('Task volumes remain; refusing to remove runtime marker')
    shutil.rmtree(RUNTIME)
    print('Task containers, volumes, network and local credentials removed; shared image cache preserved.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'pull', 'up', 'status', 'cleanup'])
    parser.add_argument('--context', default='orbstack')
    parser.add_argument('--auth-profile', action='store_true',
                        help='prepare reviewed scope profiles with short-lived tokens and refresh rotation')
    args = parser.parse_args()
    try:
        if args.action == 'prepare':
            prepare(args.context, args.auth_profile)
        else:
            if args.auth_profile:
                raise RuntimeError('--auth-profile applies only to prepare')
            data = state()
            if args.action == 'pull':
                pull(data)
            elif args.action == 'up':
                up(data)
            elif args.action == 'cleanup':
                cleanup(data)
            else:
                print(compose(data, 'ps', '--format', 'json').stdout.decode())
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print(f'FAIL: {exc}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
