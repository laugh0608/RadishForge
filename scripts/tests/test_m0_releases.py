"""Release bytes, exact references and uncertain results; no network/listeners."""
import http.client
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import m0_oauth as oauth
import m0_releases as releases
from m0_response_loss import ResponseLoss

SHA = 'a' * 40
UUID = '00000000-0000-0000-0000-000000000001'


def response(value, status=200):
    return status, value, None, releases.ORIGIN + releases.REPO


def release(**overrides):
    return {**dict(id=1, tag_name='m0-marker', name='M0 title', body='M0 body', draft=True,
                   prerelease=False, target_commitish=SHA, author={'id': 7}, assets=[]), **overrides}


def asset(**overrides):
    return {**dict(id=1, name='m0-fixture.bin', size=3, uuid=UUID,
                   browser_download_url=releases.ORIGIN + '/attachments/' + UUID), **overrides}


class RawHTTP(io.BytesIO):
    def __init__(self, data, headers=None):
        super().__init__(data)
        self.code = 200
        self.url = releases.ORIGIN + '/attachments/' + UUID
        self.headers = headers or {'Content-Type': 'application/octet-stream'}


class BinaryTransport(unittest.TestCase):
    def setUp(self):
        self.start = len(oauth.REQUESTS)
        self.client = object.__new__(oauth.Client)
        self.client.base = releases.ORIGIN
        self.client.opener = Mock()

    def tearDown(self):
        del oauth.REQUESTS[self.start:]

    def test_exact_non_utf8_bytes_and_only_selected_response_headers(self):
        self.client.opener.open.return_value = RawHTTP(b'\x00\xff\x80', {
            'Content-Type': 'application/octet-stream', 'Content-Length': '3', 'Set-Cookie': 'synthetic-private'})
        result = self.client.request('GET', '/attachments/' + UUID, binary=True, max_bytes=3)
        self.assertEqual(result[1].data, b'\x00\xff\x80')
        self.assertEqual(result[1].headers, {'Content-Type': 'application/octet-stream', 'Content-Length': '3'})
        self.assertNotIn('synthetic-private', json.dumps(oauth.REQUESTS[self.start:]))

    def test_binary_size_limit_is_failure_and_never_partial_success(self):
        self.client.opener.open.return_value = RawHTTP(b'abcd')
        with self.assertRaisesRegex(RuntimeError, 'size limit'):
            self.client.request('GET', '/attachments/' + UUID, binary=True, max_bytes=3)
        self.assertEqual(self.client.opener.open.call_count, 1)

    def test_incomplete_response_is_unknown_without_exporting_partial_bytes(self):
        result = RawHTTP(b'')
        result.read = Mock(side_effect=http.client.IncompleteRead(b'synthetic-private', 4))
        self.client.opener.open.return_value = result
        with self.assertRaises(http.client.IncompleteRead):
            self.client.request('GET', '/attachments/' + UUID, binary=True)
        self.assertEqual(oauth.REQUESTS[-1]['outcome'], 'unknown')
        self.assertNotIn('synthetic-private', json.dumps(oauth.REQUESTS[self.start:]))
        self.assertEqual(self.client.opener.open.call_count, 1)

    def test_ambiguous_bodies_credentials_and_bad_limits_stop_before_io(self):
        for kwargs in [dict(payload={}, raw=b'x'), dict(form={}, payload={}), dict(token='x', basic=('a', 'b')),
                       dict(raw='text'), dict(binary=1), dict(max_bytes=True), dict(max_bytes=2_000_001),
                       dict(content_type='application/octet-stream'), dict(raw=b'x', content_type='text/html')]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.client.request('POST', '/fixture', **kwargs)
        self.client.opener.open.assert_not_called()


class ReleaseDecisions(unittest.TestCase):
    def test_malformed_release_or_asset_is_not_success(self):
        for fields in [{'id': True}, {'draft': 1}, {'author': {'id': 0}}, {'assets': None}, {'body': None}]:
            with self.subTest(fields=fields), self.assertRaises(RuntimeError):
                releases.release_view(release(**fields))
        for fields in [{'size': True}, {'id': 0}, {'uuid': 'bad'}]:
            with self.subTest(fields=fields), self.assertRaises(RuntimeError):
                releases.asset_view(asset(**fields))

    def test_download_url_must_be_the_task_origin_and_exact_uuid_path(self):
        for url in ['https://example.test/attachments/' + UUID, releases.ORIGIN + '/api/v1/user',
                    releases.ORIGIN + '/attachments/' + UUID + '?token=synthetic',
                    releases.ORIGIN + '/attachments/' + UUID + '#fragment']:
            with self.subTest(url=url), self.assertRaises(RuntimeError):
                releases.asset_view(asset(browser_download_url=url))
        canonical = releases.ORIGIN + '/alice/private-fixture/releases/download/m0-tag/m0-fixture.bin'
        releases.asset_view(asset(browser_download_url=canonical), tag='m0-tag')
        with self.assertRaises(RuntimeError):
            releases.asset_view(asset(browser_download_url=canonical), tag='m0-other-tag')
        with self.assertRaises(RuntimeError):
            releases.asset_view(asset(browser_download_url=canonical.replace('m0-fixture.bin', 'm0-other.bin')))

    def test_tag_mismatch_or_disappearance_only_reads_and_stops_publication(self):
        for result in [response({}, 404), response({'commit': {'sha': 'b' * 40}})]:
            client = Mock(); client.request.return_value = result
            with self.assertRaises(ValueError):
                releases.check_tag(client, 'synthetic', 'm0-tag', SHA)
            self.assertTrue(all(v.args[0] == 'GET' for v in client.request.call_args_list))
        client = Mock()
        with self.assertRaises(ValueError):
            releases.check_tag(client, 'synthetic', 'm0-tag', 'branch')
        client.request.assert_not_called()

    def test_release_missing_wrong_author_or_changed_detail_stays_unknown(self):
        wanted = {k: release()[k] for k in ('tag_name', 'name', 'body', 'target_commitish', 'draft', 'prerelease')}
        for replies in [[response({}, 404)], [response(release(author={'id': 8})), response(release(author={'id': 8}))],
                        [response(release()), response(release(body='changed'))]]:
            client = Mock(); client.request.side_effect = replies
            result = releases.reconcile_release(client, 'synthetic', wanted, 7)
            self.assertEqual(result['state'], 'unknown')
            self.assertTrue(all(v.args[0] == 'GET' for v in client.request.call_args_list))

    def test_asset_zero_duplicate_and_wrong_bytes_never_trigger_another_write(self):
        for rows, data in [([], []), ([asset(), asset(id=2)], [b'abc', b'abc']), ([asset()], [b'abx'])]:
            replies = [response(rows)] + [response(oauth.BinaryBody(v, {})) for v in data]
            client = Mock(); client.request.side_effect = replies
            result = releases.reconcile_asset(client, 'synthetic', 1, 'm0-fixture.bin', b'abc')
            self.assertEqual(result['state'], 'unknown')
            self.assertTrue(all(v.args[0] == 'GET' for v in client.request.call_args_list))

    def test_unique_asset_requires_exact_bytes_and_stable_metadata(self):
        client = Mock(); client.request.side_effect = [response([asset()]), response(oauth.BinaryBody(b'abc', {})), response(asset())]
        self.assertEqual(releases.reconcile_asset(client, 'synthetic', 1, 'm0-fixture.bin', b'abc')['state'], 'observed')
        client.request.side_effect = [response([asset()]), response(oauth.BinaryBody(b'abc', {})), response(asset(name='changed.bin'))]
        self.assertEqual(releases.reconcile_asset(client, 'synthetic', 1, 'm0-fixture.bin', b'abc')['state'], 'unknown')
        canonical = asset(browser_download_url=releases.ORIGIN + '/alice/private-fixture/releases/download/m0-tag/m0-fixture.bin')
        client.request.side_effect = [response([canonical]), response(oauth.BinaryBody(b'abc', {})), response(asset())]
        self.assertEqual(releases.reconcile_asset(client, 'synthetic', 1, 'm0-fixture.bin', b'abc')['state'], 'observed')

    def test_wrong_or_truncated_download_bytes_are_rejected(self):
        for data, headers in [(b'abx', {}), (b'ab', {}), (b'abc', {'Content-Length': '4'})]:
            client = Mock(); client.request.return_value = response(oauth.BinaryBody(data, headers))
            with self.subTest(data=data, headers=headers), self.assertRaises(RuntimeError):
                releases.download(client, 'synthetic', asset(), expected=b'abc')

    def test_fault_operation_cannot_change_endpoint_or_partial_mode(self):
        cases = [('release_create', releases.REPO + '/issues', {}, True, None),
                 ('issue_create', releases.REPO + '/releases', {}, True, None),
                 ('release_asset', releases.asset_path(1) + '?name=m0-fixture.bin', b'abc', True, 3),
                 ('release_asset', releases.asset_path(1) + '?name=m0-fixture.bin', b'abc', False, 1),
                 ('release_create', releases.REPO + '/releases', {}, True, 1)]
        for op, path, body, forward, partial in cases:
            with self.subTest(op=op, path=path), self.assertRaises(ValueError):
                ResponseLoss(op, path, 'synthetic', body, forward=forward, partial_bytes=partial)


if __name__ == '__main__':
    unittest.main()
