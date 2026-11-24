"""Exercise byte-level verification for the arm64 scratch fixture without a Registry."""
import gzip
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from m0_image_source import digest, verify


class Arm64ImageSource(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)
        self.source = 'a' * 40

    def fixture(self, *, arch='arm64', paths=('source-sha',)):
        def blob(raw, media_type):
            identity = digest(raw)
            (self.directory / identity.split(':')[1]).write_bytes(raw)
            return {'mediaType': media_type, 'size': len(raw), 'digest': identity}

        stream = io.BytesIO()
        content = (self.source + '\n').encode()
        with tarfile.open(fileobj=stream, mode='w') as archive:
            for path in paths:
                entry = tarfile.TarInfo(path)
                entry.size = len(content)
                archive.addfile(entry, io.BytesIO(content))
        tar = stream.getvalue()
        config = {'os': 'linux', 'architecture': arch, 'rootfs': {'type': 'layers', 'diff_ids': [digest(tar)]}}
        manifest = {'schemaVersion': 2, 'mediaType': 'application/vnd.oci.image.manifest.v1+json',
                    'config': blob(json.dumps(config).encode(), 'application/vnd.oci.image.config.v1+json'),
                    'layers': [blob(gzip.compress(tar), 'application/vnd.oci.image.layer.v1.tar+gzip')]}
        raw = json.dumps(manifest).encode()
        (self.directory / 'manifest.json').write_bytes(raw)
        return digest(raw), manifest

    def test_digest_pull_must_contain_the_triggering_git_sha(self):
        identity, _ = self.fixture()
        self.assertEqual(verify(self.directory, identity, self.source)['source_sha'], self.source)
        with self.assertRaisesRegex(ValueError, 'source SHA'):
            verify(self.directory, identity, 'b' * 40)
        with self.assertRaisesRegex(ValueError, 'Manifest Digest'):
            verify(self.directory, 'sha256:' + '0' * 64, self.source)

    def test_platform_layer_and_single_file_must_match(self):
        identity, _ = self.fixture(arch='amd64')
        with self.assertRaisesRegex(ValueError, 'platform'):
            verify(self.directory, identity, self.source)
        identity, manifest = self.fixture(paths=('source-sha', 'source-sha'))
        with self.assertRaisesRegex(ValueError, 'regular'):
            verify(self.directory, identity, self.source)
        (self.directory / manifest['layers'][0]['digest'].split(':')[1]).write_bytes(b'wrong')
        with self.assertRaisesRegex(ValueError, 'Blob'):
            verify(self.directory, identity, self.source)
