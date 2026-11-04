"""Bounded OCI Registry reads/writes and scoped PATs for the fixed M0 provider."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile
import urllib.parse
import urllib.request

from m0_local import RUNTIME, write_private
from m0_oauth import BinaryBody, expect, unb64

PROFILE = Path(__file__).resolve().parent.parent / 'tests/contracts/m0/gitea-registry-profile.json'
ORG = 'm0-private-org'
IMAGE = ORG + '/m0-probe'
ORIGIN = 'https://localhost:18443'
OCI_MANIFEST = 'application/vnd.oci.image.manifest.v1+json'
DOCKER_MANIFEST = 'application/vnd.docker.distribution.manifest.v2+json'
ACCEPT = {'Accept': OCI_MANIFEST + ', ' + DOCKER_MANIFEST + ', application/vnd.oci.image.index.v1+json'}
SOURCE_BYTES = b'RadishForge M0 isolated OCI source fixture\n'


def contract():
    value = json.loads(PROFILE.read_text())
    if (set(value) != {'schema_version', 'provider', 'provider_version', 'origin', 'service', 'token_path', 'pat_profiles', 'client'}
            or value['schema_version'] != 1 or value['provider'] != 'gitea' or value['provider_version'] != '28.2.0'
            or value['origin'] != ORIGIN or value['service'] != 'container_registry' or value['token_path'] != '/v2/token'
            or value['pat_profiles'] != {'read': ['read:package'], 'write': ['write:package']}
            or value['client'] != {'name': 'regctl', 'version': 'v0.11.7', 'platform': 'darwin/arm64',
                                   'sha256': '8ac077a1eeb834d3053714e86ccbd838d0da46567df8cd7c2695d1a19135bf60', 'license': 'Apache-2.0'}):
        raise ValueError('Unsupported M0 Registry contract')
    return value


def sha(data):
    return 'sha256:' + hashlib.sha256(data).hexdigest()


def json_bytes(value):
    return json.dumps(value, separators=(',', ':'), sort_keys=True).encode()


def body_json(result, statuses, label):
    data = expect(result, statuses, label)
    if not isinstance(data, BinaryBody):
        raise RuntimeError('Registry response did not preserve bytes')
    try:
        return json.loads(data.data)
    except (ValueError, UnicodeError):
        raise RuntimeError('Registry JSON response is invalid; body withheld') from None


def challenge(client):
    result = client.request('GET', '/v2/', binary=True)
    data = expect(result, {401}, 'anonymous Registry challenge')
    header = data.headers.get('WWW-Authenticate', '')
    # Parse the challenge as quoted HTTP parameters, never follow an arbitrary realm.
    scheme, _, rest = header.partition(' ')
    pairs = urllib.request.parse_keqv_list(urllib.request.parse_http_list(rest))
    if (scheme.lower() != 'bearer' or pairs.get('realm') != ORIGIN + '/v2/token'
            or pairs.get('service') != contract()['service'] or pairs.get('scope') != '*'):
        raise RuntimeError('Registry challenge differs from the fixed realm/service')
    return {'status': result[0], 'realm': pairs['realm'], 'service': pairs['service'], 'scope': pairs['scope']}


def create_pat(client, credentials, purpose, name):
    profiles = contract()['pat_profiles']
    if purpose not in profiles:
        raise ValueError('Unapproved package token purpose')
    row = expect(client.request('POST', '/api/v1/users/' + credentials[0] + '/tokens', basic=credentials,
                                payload={'name': name, 'scopes': profiles[purpose]}), {201}, 'create scoped package PAT')
    if (type(row.get('id')) is not int or row['id'] <= 0 or row.get('scopes') != profiles[purpose]
            or not isinstance(row.get('sha1'), str) or not re.fullmatch('[a-f0-9]{40}', row['sha1'])):
        raise RuntimeError('Package PAT differs from its explicit scope or identity')
    return {'id': row['id'], 'value': row['sha1'], 'user': credentials[0], 'purpose': purpose, 'scopes': row['scopes']}


def mint(client, pat, *, actions='pull,push'):
    if actions not in ('pull', 'pull,push'):
        raise ValueError('Unreviewed Registry action request')
    query = urllib.parse.urlencode({'service': contract()['service'], 'scope': 'repository:' + IMAGE + ':' + actions})
    result = client.request('GET', '/v2/token?' + query, basic=(pat['user'], pat['value']), binary=True)
    row = body_json(result, {200}, 'exchange scoped PAT for Registry Token')
    if not isinstance(row, dict) or not isinstance(row.get('token'), str) or row['token'].count('.') != 2:
        raise RuntimeError('Invalid Registry Token receipt')
    # Claims are diagnostic input, not locally verified HMAC authentication/authorization.
    try:
        claims = json.loads(unb64(row['token'].split('.')[1]))
    except (ValueError, UnicodeError):
        raise RuntimeError('Invalid Registry Token claim encoding') from None
    if (type(claims.get('UserID')) is not int or claims['UserID'] <= 0
            or claims.get('Scope') != ' '.join(pat['scopes'])
            or type(claims.get('exp')) is not int or type(claims.get('nbf')) is not int
            or claims['exp'] <= claims['nbf']):
        raise RuntimeError('Registry Token claims differ from the requested PAT purpose')
    return row['token'], {'user_id': claims['UserID'], 'scope': claims['Scope'],
                          'declared_lifetime_seconds': claims['exp'] - claims['nbf'], 'claims_locally_signature_verified': False}


def location(value, *, image=IMAGE):
    if not isinstance(value, str):
        raise RuntimeError('Missing Registry upload Location')
    parsed = urllib.parse.urlsplit(urllib.parse.urljoin(ORIGIN, value))
    pattern = '/v2/' + re.escape(image) + r'/blobs/uploads/[-A-Za-z0-9_.=]+'
    if (f'{parsed.scheme}://{parsed.netloc}' != ORIGIN or parsed.query or parsed.fragment
            or not re.fullmatch(pattern, parsed.path)):
        raise RuntimeError('Upload Location is outside the exact task image and origin')
    return parsed.path


def start_upload(client, token, *, image=IMAGE):
    result = client.request('POST', '/v2/' + image + '/blobs/uploads/', token=token, raw=b'', binary=True)
    expect(result, {202}, 'start blob upload')
    return location(result[2], image=image)


def upload_blob(client, token, data, *, chunked=False, image=IMAGE):
    digest = sha(data)
    path = start_upload(client, token, image=image)
    if chunked:
        split = len(data) // 2
        result = client.request('PATCH', path, token=token, raw=data[:split], binary=True,
                                headers={'Content-Range': '0-' + str(split - 1)})
        expect(result, {202}, 'append bounded blob chunk')
        path = location(result[2], image=image)
        current = expect(client.request('GET', path, token=token, binary=True), {204}, 'query upload Range')
        if current.headers.get('Range') != '0-' + str(split - 1):
            raise RuntimeError('Upload Range differs from confirmed prefix')
        data = data[split:]
    result = client.request('PUT', path + '?digest=' + digest, token=token, raw=data, binary=True)
    final = expect(result, {201}, 'complete exact blob')
    if final.headers.get('Docker-Content-Digest') != digest:
        raise RuntimeError('Registry did not confirm the requested blob Digest')
    return digest


def read_blob(client, token, digest, *, image=IMAGE, expected=None):
    if not re.fullmatch('sha256:[a-f0-9]{64}', digest):
        raise ValueError('Invalid content Digest')
    result = client.request('GET', '/v2/' + image + '/blobs/' + digest, token=token, binary=True)
    body = expect(result, {200}, 'pull exact blob Digest')
    if sha(body.data) != digest or (expected is not None and body.data != expected):
        raise RuntimeError('Downloaded blob does not match the requested Digest/content')
    if body.headers.get('Docker-Content-Digest') != digest:
        raise RuntimeError('Downloaded blob confirmation differs')
    return body.data


def fixture(source_sha, marker):
    if not re.fullmatch('[a-f0-9]{40}', source_sha):
        raise ValueError('Fixture source must be a full commit SHA')
    content = SOURCE_BYTES
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w', format=tarfile.USTAR_FORMAT) as archive:
        entry = tarfile.TarInfo('m0-source.txt'); entry.size = len(content); entry.mode = 0o644
        archive.addfile(entry, io.BytesIO(content))
    layer_raw = stream.getvalue(); layer = gzip.compress(layer_raw, mtime=0)
    config = json_bytes({'architecture': 'arm64', 'os': 'linux', 'rootfs': {'type': 'layers', 'diff_ids': [sha(layer_raw)]},
                         'config': {'Labels': {'org.opencontainers.image.revision': source_sha}},
                         'history': [{'created_by': 'M0 bounded synthetic fixture'}]})
    manifest = json_bytes({'schemaVersion': 2, 'mediaType': OCI_MANIFEST,
                           'config': {'mediaType': 'application/vnd.oci.image.config.v1+json', 'digest': sha(config), 'size': len(config)},
                           'layers': [{'mediaType': 'application/vnd.oci.image.layer.v1.tar+gzip', 'digest': sha(layer), 'size': len(layer)}],
                           'annotations': {'org.opencontainers.image.revision': source_sha, 'io.radishforge.m0.marker': marker}})
    return config, layer, manifest


def put_manifest(client, token, tag, raw, *, image=IMAGE, media_type=OCI_MANIFEST):
    if not re.fullmatch('m0-[a-z0-9-]+', tag):
        raise ValueError('Only task manifest tags are accepted')
    result = client.request('PUT', '/v2/' + image + '/manifests/' + tag, token=token,
                            raw=raw, content_type=media_type, binary=True)
    body = expect(result, {201}, 'push exact manifest')
    if body.headers.get('Docker-Content-Digest') != sha(raw):
        raise RuntimeError('Registry manifest Digest differs from exact serialized bytes')
    return sha(raw)


def read_manifest(client, token, reference, *, image=IMAGE, expected=None):
    if not re.fullmatch(r'(sha256:[a-f0-9]{64}|m0-[a-z0-9-]+)', reference):
        raise ValueError('Invalid task manifest reference')
    path = '/v2/' + image + '/manifests/' + reference
    result = client.request('GET', path, token=token, binary=True, headers=ACCEPT)
    body = expect(result, {200}, 'pull exact manifest')
    digest = sha(body.data)
    if (reference.startswith('sha256:') and digest != reference
            or expected is not None and body.data != expected
            or body.headers.get('Docker-Content-Digest') != digest):
        raise RuntimeError('Manifest content/Digest confirmation differs')
    if body.headers.get('Content-Type', '').split(';')[0] not in (OCI_MANIFEST, DOCKER_MANIFEST, 'application/vnd.oci.image.index.v1+json'):
        raise RuntimeError('Unexpected manifest media type')
    row = body_json(result, {200}, 'manifest JSON')
    return digest, row, body.data


def remember(data):
    write_private(RUNTIME / 'oci-credentials.json', json.dumps(data))
