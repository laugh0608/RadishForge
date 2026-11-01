"""Security policy examples for complete scope combinations; no Docker or network."""
import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('m0_scope', SOURCE / 'scripts/m0_scope.py')
SCOPE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SCOPE)


class ScopePolicy(unittest.TestCase):
    def test_reviewed_profiles_are_distinct_and_canonical(self):
        identity = SCOPE.scope_for('identity')
        self.assertEqual(SCOPE.scope_for('identity', identity.split()[::-1]), identity)
        self.assertIn('public-only', identity.split())
        self.assertNotIn('write:issue', SCOPE.scope_for('resource_read').split())
        self.assertNotIn('public-only', SCOPE.scope_for('issue_write').split())

    def test_default_oidc_and_unknown_or_admin_scopes_rejected(self):
        for scopes in ['openid email profile', 'openid m0-unknown-scope', 'all',
                       SCOPE.scope_for('identity') + ' read:admin',
                       SCOPE.scope_for('identity').replace('public-only ', '')]:
            with self.subTest(scopes=scopes), self.assertRaises(SCOPE.ProfileError):
                SCOPE.scope_for('identity', scopes)

    def test_scope_union_and_wrong_issuer_rejected(self):
        with self.assertRaises(SCOPE.ProfileError):
            SCOPE.scope_for('resource_read', SCOPE.scope_for('issue_write'))
        with self.assertRaises(SCOPE.ProfileError):
            SCOPE.scope_for('identity', origin='https://localhost:18443')
        with self.assertRaises(SCOPE.ProfileError):
            SCOPE.scope_for('unknown')

    def test_profiles_do_not_add_unneeded_resource_groups(self):
        profiles = SCOPE.load_contract()['profiles']
        for name, profile in profiles.items():
            with self.subTest(profile=name):
                self.assertNotIn('all', profile['scopes'])
                self.assertFalse(any(s.endswith((':admin', ':package')) for s in profile['scopes']))
                self.assertNotIn('write:repository', profile['scopes'])
        self.assertFalse(any(s.startswith('write:') for s in profiles['resource_read']['scopes']))
        self.assertEqual([s for s in profiles['issue_write']['scopes'] if s.startswith('write:')], ['write:issue'])

    def test_empty_duplicate_and_malformed_inputs_rejected(self):
        for value in ['', [], {}, 3, ['openid', 'openid'], ['openid', 1],
                      SCOPE.scope_for('identity') + ' ',
                      SCOPE.scope_for('identity').replace(' ', '\t')]:
            with self.subTest(value=value), self.assertRaises(SCOPE.ProfileError):
                SCOPE.scope_for('identity', value)


if __name__ == '__main__':
    unittest.main()
