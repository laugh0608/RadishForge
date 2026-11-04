"""Issue preflight, pagination and uncertain-write decisions; no Docker/network."""
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock
import urllib.error

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import m0_issues as issues
import m0_oauth as oauth


def response(body, status=200):
    return status, body, None, 'https://localhost:18443/api/v1/repos/alice/private-fixture/issues'


def issue(number=1, **overrides):
    return {**dict(id=number, number=number, title='marker', body='exact body', user={'id': 7},
                   state='open', labels=[], assignees=[], milestone=None, content_version=0), **overrides}


class IssueBoundaries(unittest.TestCase):
    def test_pagination_visits_empty_terminal_page_without_duplicates(self):
        client = Mock()
        client.request.side_effect = [response([issue(1), issue(2)]), response([issue(3)]), response([])]
        rows, pages = issues.collect_pages(client, '/fixture/issues', 'synthetic', limit=2, issue_only=True)
        self.assertEqual([v['id'] for v in rows], [1, 2, 3])
        self.assertEqual(pages, [2, 1, 0])

    def test_denied_malformed_repeating_or_pr_pages_never_become_empty_success(self):
        cases = [[response({}, 403)], [response({})], [response([issue()]), response([issue()])],
                 [response([issue(pull_request={})])], [response([{'id': True}])]]
        for replies in cases:
            with self.subTest(replies=replies):
                client = Mock(); client.request.side_effect = replies
                with self.assertRaises(RuntimeError):
                    issues.collect_pages(client, '/fixture/issues', 'synthetic', issue_only=True)

    def test_associations_require_current_repository_catalog_and_precise_types(self):
        catalog = {'labels': {1}, 'assignees': {'alice'}, 'milestones': {2}}
        issues.validate_associations(catalog, {'labels': [1], 'assignees': ['alice'], 'milestone': 2})
        issues.validate_associations(catalog, {'labels': [], 'assignees': [], 'milestone': 0})
        for payload in [{'labels': [9]}, {'labels': [True]}, {'labels': [1.0]}, {'labels': [1, 1]},
                        {'assignees': ['outsider']}, {'assignees': ['alice', 'alice']},
                        {'milestone': 9}, {'milestone': True}, {'milestone': -1}, {'labels': None}]:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                issues.validate_associations(catalog, payload)

    def test_no_match_ambiguous_or_wrong_author_stays_unknown_without_writes(self):
        payload = {'title': 'marker', 'body': 'exact body'}
        for rows in [[], [issue(1), issue(2)], [issue(user={'id': 8})]]:
            with self.subTest(rows=rows):
                client = Mock(); client.request.side_effect = [response(rows), response([])] if rows else [response([])]
                result = issues.reconcile_create(client, '/fixture', 'synthetic', payload, 7)
                self.assertEqual(result['state'], 'unknown')
                self.assertTrue(all(call.args[0] == 'GET' for call in client.request.call_args_list))

    def test_unique_match_requires_current_detail_and_exact_body(self):
        payload = {'title': 'marker', 'body': 'exact body'}
        client = Mock(); client.request.side_effect = [response([issue()]), response([]), response(issue())]
        result = issues.reconcile_create(client, '/fixture', 'synthetic', payload, 7)
        self.assertEqual(result['state'], 'observed')
        self.assertTrue(all(call.args[0] == 'GET' for call in client.request.call_args_list))
        client.request.side_effect = [response([issue()]), response([]), response(issue(body='changed after list'))]
        self.assertEqual(issues.reconcile_create(client, '/fixture', 'synthetic', payload, 7)['state'], 'unknown')
        client.request.side_effect = [response([issue()]), response([]), response({}, 404)]
        with self.assertRaises(RuntimeError):
            issues.reconcile_create(client, '/fixture', 'synthetic', payload, 7)

    def test_fault_relay_cannot_target_another_path_or_truthy_non_boolean_mode(self):
        for path, mode in [('/api/v1/users', True), (issues.REPO + '/issues', 1)]:
            with self.assertRaises(ValueError):
                issues.ResponseLoss('issue_create', path, 'synthetic', {'title': 'fixture'}, forward=mode)

    def test_malformed_issue_cannot_be_normalized_as_a_successful_readback(self):
        for fields in [{'content_version': True}, {'labels': [{'id': 0}]}, {'assignees': [{'login': ''}]},
                       {'milestone': {'id': 0}}, {'state': 'unknown'}, {'pull_request': {}}]:
            with self.subTest(fields=fields), self.assertRaises(RuntimeError):
                issues.snapshot(issue(**fields))


class TimeoutTransport(unittest.TestCase):
    def setUp(self):
        self.start = len(oauth.REQUESTS)
        self.client = object.__new__(oauth.Client)
        self.client.base = 'https://localhost:18443'
        self.client.opener = Mock()

    def tearDown(self):
        del oauth.REQUESTS[self.start:]

    def test_transport_error_is_unknown_and_never_retried_or_logged_with_token(self):
        self.client.opener.open.side_effect = TimeoutError('synthetic')
        with self.assertRaises(TimeoutError):
            self.client.request('POST', '/issues?filter=synthetic', token='synthetic-secret',
                                payload={'title': 'fixture'}, timeout=1)
        self.assertEqual(self.client.opener.open.call_count, 1)
        record = oauth.REQUESTS[-1]
        self.assertIsNone(record['status'])
        self.assertEqual(record['outcome'], 'unknown')
        self.assertNotIn('synthetic-secret', json.dumps(record))
        self.assertNotIn('?', record['path'])

    def test_http_rejection_is_preserved_as_http_instead_of_network_unknown(self):
        self.client.opener.open.side_effect = urllib.error.HTTPError(
            self.client.base + '/issues', 403, 'Forbidden', {'Content-Type': 'application/json'}, io.BytesIO(b'{}'))
        result = self.client.request('POST', '/issues', payload={'title': 'fixture'})
        self.assertEqual(result[0], 403)
        self.assertEqual(oauth.REQUESTS[-1]['status'], 403)
        self.assertNotIn('outcome', oauth.REQUESTS[-1])

    def test_invalid_deadlines_are_refused_before_network(self):
        for value in [0, -1, True, float('nan'), float('inf'), 16, '1']:
            with self.subTest(timeout=value), self.assertRaises(ValueError):
                self.client.request('GET', '/issues', timeout=value)
        self.client.opener.open.assert_not_called()


if __name__ == '__main__':
    unittest.main()
