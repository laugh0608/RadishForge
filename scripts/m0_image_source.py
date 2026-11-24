#!/usr/bin/env python3
"""Verify the single-layer scratch image downloaded by Digest with skopeo's dir transport."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import tarfile


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return 'sha256:' + hashlib.sha256(data).hexdigest()


def bounded_read(path, limit):
    with path.open('rb') as source:
        raw = source.read(limit + 1)
    require(len(raw) <= limit, 'Fixture exceeds its byte budget')
    return raw


def blob(directory, descriptor, media_type):
    require(descriptor['mediaType'] == media_type, 'Unexpected blob media type')
    expected = descriptor['digest']
    require(re.fullmatch('sha256:[a-f0-9]{64}', expected), 'Invalid blob Digest')
    data = bounded_read(directory / expected.split(':')[1], 1_048_576)
    require(len(data) == descriptor['size'] and digest(data) == expected, 'Blob size or Digest differs')
    return data


def verify(directory, expected_manifest, expected_sha):
    require(re.fullmatch('[a-f0-9]{40}', expected_sha), 'Expected a full Git SHA')
    raw = bounded_read(directory / 'manifest.json', 65536)
    require(digest(raw) == expected_manifest, 'Manifest Digest differs from the workflow result')
    manifest = json.loads(raw)
    require(manifest['schemaVersion'] == 2 and manifest['mediaType'] == 'application/vnd.oci.image.manifest.v1+json',
            'Expected a single OCI image manifest')
    require(len(manifest['layers']) == 1, 'Expected one scratch image layer')
    config = json.loads(blob(directory, manifest['config'], 'application/vnd.oci.image.config.v1+json'))
    require((config['os'], config['architecture']) == ('linux', 'arm64'), 'Unexpected image platform')
    layer = blob(directory, manifest['layers'][0], 'application/vnd.oci.image.layer.v1.tar+gzip')
    with gzip.GzipFile(fileobj=io.BytesIO(layer)) as stream:
        tar = stream.read(1_048_577)
    require(len(tar) <= 1_048_576, 'Uncompressed layer exceeds its byte budget')
    require(config['rootfs']['type'] == 'layers' and config['rootfs']['diff_ids'] == [digest(tar)],
            'Uncompressed layer differs from the config')
    with tarfile.open(fileobj=io.BytesIO(tar), mode='r:') as archive:
        members = archive.getmembers()
        require(len(members) == 1 and members[0].name == 'source-sha' and members[0].isreg()
                and members[0].size == 41, 'Expected one regular /source-sha file')
        with archive.extractfile(members[0]) as source:
            require(source.read() == (expected_sha + '\n').encode('ascii'), 'Image source SHA differs')
    return {'manifest': expected_manifest, 'config': manifest['config']['digest'],
            'layer': manifest['layers'][0]['digest'], 'diff_id': digest(tar),
            'platform': 'linux/arm64', 'source_sha': expected_sha}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('manifest_digest')
    parser.add_argument('source_sha')
    args = parser.parse_args()
    print(json.dumps(verify(args.directory, args.manifest_digest, args.source_sha), indent=2))
