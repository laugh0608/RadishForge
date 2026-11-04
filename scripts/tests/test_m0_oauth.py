"""Credential decisions and transport rejection boundaries; no real provider evidence."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock
import urllib.error
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import m0_oauth as oauth


def response(body, status=200):
    return status, body, None, 'https://localhost:18443/login/oauth/introspect'


class CredentialBoundary(unittest.TestCase):
    def setUp(self):
        self.app = {'client_id': 'fixture-client', 'client_secret': 'fixture-secret'}
        self.tokens = {'token_type': 'bearer', 'expires_in': 30,
                       'access_token': 'synthetic-access', 'refresh_token': 'synthetic-refresh'}
        self.metadata = {'active': True, 'sub': '7', 'scope': oauth.scope_for('resource_read')}
        self.client = Mock(base='https://localhost:18443')

    def test_active_metadata_does_not_override_disabled_account(self):
        self.client.request.side_effect = [response(self.metadata), response({}, 403)]
        with self.assertRaises(oauth.GrantRejected) as error:
            oauth.receipt('resource_read', self.client, self.app, self.tokens)
        self.assertEqual(error.exception.reason, 'account_access_denied')
        self.assertEqual(self.client.request.call_count, 2)

    def test_html_inactive_and_malformed_metadata_stop_before_account_request(self):
        examples = ['<html>Account disabled</html>', [], None, {'active': False}, {},
                    dict(self.metadata, active=1), dict(self.metadata, active='true'),
                    dict(self.metadata, sub=''), dict(self.metadata, sub='True'),
                    dict(self.metadata, sub='0'), dict(self.metadata, sub='٧'), dict(self.metadata, scope=None),
                    dict(self.metadata, scope='openid email profile')]
        for body in examples:
            with self.subTest(body=body):
                self.client.request.reset_mock(side_effect=True)
                self.client.request.return_value = response(body)
                with self.assertRaises(oauth.GrantRejected):
                    oauth.receipt('resource_read', self.client, self.app, self.tokens)
                self.assertEqual(self.client.request.call_count, 1)

    def test_401_stays_unattributed_without_control_evidence(self):
        self.client.request.return_value = response('no valid authorization', 401)
        with self.assertRaises(oauth.GrantRejected) as error:
            oauth.receipt('resource_read', self.client, self.app, self.tokens)
        self.assertEqual(error.exception.reason, 'introspection_unauthorized_unattributed')
        self.assertEqual(self.client.request.call_count, 1)

    def test_network_unknown_and_invalid_json_stop_without_retry(self):
        for failure, reason in [(urllib.error.URLError('synthetic timeout'), 'verification_result_unknown'),
                                (TimeoutError(), 'verification_result_unknown'),
                                (json.JSONDecodeError('invalid JSON', '', 0), 'invalid_verification_response')]:
            with self.subTest(failure=type(failure).__name__):
                self.client.request.reset_mock(side_effect=True)
                self.client.request.side_effect = failure
                with self.assertRaises(oauth.GrantRejected) as error:
                    oauth.receipt('resource_read', self.client, self.app, self.tokens)
                self.assertEqual(error.exception.reason, reason)
                self.assertEqual(self.client.request.call_count, 1)

    def test_valid_subject_and_current_account_are_both_required(self):
        self.client.request.side_effect = [response(self.metadata), response({'id': 7})]
        self.assertEqual(oauth.receipt('resource_read', self.client, self.app, self.tokens, subject='7'), self.metadata)
        for account, subject in [({'id': 8}, '7'), ({'id': 7}, '8'), ({'id': '7'}, '7'),
                                 ({'id': True}, '7'), ('not an account', '7')]:
            with self.subTest(account=account, subject=subject):
                self.client.request.side_effect = [response(self.metadata), response(account)]
                with self.assertRaises(oauth.GrantRejected):
                    oauth.receipt('resource_read', self.client, self.app, self.tokens, subject=subject)

    def test_server_errors_and_api_redirects_never_establish_a_grant(self):
        for status in (302, 403, 429, 500, 503):
            with self.subTest(status=status):
                self.client.request.reset_mock(side_effect=True)
                self.client.request.return_value = response({}, status)
                with self.assertRaises(oauth.GrantRejected):
                    oauth.receipt('resource_read', self.client, self.app, self.tokens)
                self.assertEqual(self.client.request.call_count, 1)

    def test_api_redirect_is_preserved_and_cross_origin_is_refused(self):
        handler = oauth.Redirects('https://localhost:18443')
        request = urllib.request.Request('https://localhost:18443/login/oauth/introspect')
        self.assertIsNone(handler.redirect_request(request, None, 302, 'Found', {},
                                                  'https://localhost:18443/user/login'))
        with self.assertRaises(RuntimeError):
            handler.redirect_request(request, None, 302, 'Found', {}, 'https://other.example.test/')
        self.assertIsNone(handler.redirect_request(request, None, 302, 'Found', {}, oauth.CALLBACK + '?code=synthetic'))


if __name__ == '__main__':
    unittest.main()
