"""Provider drift and task ownership failures; no Docker calls."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import m0_local as local


INI = '''APP_NAME = isolated fixture
[security]
DISABLE_QUERY_AUTH_TOKEN = true
[oauth2]
INVALIDATE_REFRESH_TOKENS = true
ACCESS_TOKEN_EXPIRATION_TIME = 30
REFRESH_TOKEN_EXPIRATION_TIME = 1
DEFAULT_APPLICATIONS =
[actions]
ENABLED = false
'''


class LocalBoundary(unittest.TestCase):
    def test_effective_setting_drift_does_not_record_ready(self):
        for before, after in [('DISABLE_QUERY_AUTH_TOKEN = true', 'DISABLE_QUERY_AUTH_TOKEN = false'),
                              ('INVALIDATE_REFRESH_TOKENS = true', 'INVALIDATE_REFRESH_TOKENS = false'),
                              ('ENABLED = false', 'ENABLED = true')]:
            with self.subTest(setting=before), patch.object(local, 'compose') as compose, \
                    patch.object(local, 'write_private') as write:
                compose.return_value = SimpleNamespace(stdout=INI.replace(before, after).encode())
                with self.assertRaises(RuntimeError):
                    local.verify_provider_settings({'legacy_query_auth': False})
                write.assert_not_called()

    def test_malformed_configuration_error_withholds_raw_line(self):
        with patch.object(local, 'compose') as compose, patch.object(local, 'write_private') as write:
            compose.return_value = SimpleNamespace(stdout=(INI + '\n[broken]\nsynthetic-private-value\n').encode())
            with self.assertRaises(RuntimeError) as error:
                local.verify_provider_settings({'legacy_query_auth': False})
            self.assertNotIn('synthetic-private-value', str(error.exception))
            write.assert_not_called()

    def test_consent_cannot_use_a_different_project_or_replay_a_stage(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(local, 'RUNTIME', Path(directory)):
            target = {'project': 'rf-m0-local-other', 'user': 'bob', 'application_id': 7}
            (Path(directory) / 'consent-target.json').write_text(json.dumps(target))
            with self.assertRaises(RuntimeError):
                local.consent_marker({'project': 'rf-m0-local-current'})
            target['project'] = 'rf-m0-local-current'
            (Path(directory) / 'consent-target.json').write_text(json.dumps(target))
            with self.assertRaises(RuntimeError):
                local.consent_marker({'project': target['project']}, revoked=True)
            (Path(directory) / 'consent-ui-ready.json').write_text('{}')
            with self.assertRaises(RuntimeError):
                local.consent_marker({'project': target['project']})

    def test_cleanup_keeps_ownership_marker_when_network_remains(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(local, 'RUNTIME', Path(directory)), \
                patch.object(local, 'compose'), patch.object(local, 'docker') as docker:
            marker = Path(directory) / 'owner.json'
            marker.write_text('{}')
            docker.side_effect = [SimpleNamespace(stdout=b''), SimpleNamespace(stdout=b''),
                                  SimpleNamespace(stdout=b'owned-network-remains')]
            with self.assertRaises(RuntimeError):
                local.cleanup({'project': 'rf-m0-local-current'})
            self.assertTrue(marker.exists())


if __name__ == '__main__':
    unittest.main()
