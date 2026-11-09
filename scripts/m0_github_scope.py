#!/usr/bin/env python3
"""Check a disposable read-only owner PAT against the M0 private GitHub fixture."""
import argparse
from datetime import datetime, timezone
import getpass
from http.client import HTTPException
import json
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener
import warnings


ACCOUNT = 'laugh0608'
ACCOUNT_ID = 48167499
REPO = '/repos/laugh0608/RadishForge-Test'
REPO_ID = 1451320859
SOURCE = '37aa3d3ca05aa645e8d970a233b95fcebf35452c'
RELEASE_ID = 439093746
API_VERSION = '2026-03-10'
RUNTIME = Path(__file__).resolve().parent.parent / '.local'


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def request(opener, report, label, method, path, token=None, payload=None):
    require(path == '/user' or path == REPO or path.startswith(REPO + '/'), 'Unexpected GitHub API target')
    headers = {'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': API_VERSION,
               'User-Agent': 'RadishForge-M0-scope-probe'}
    if method == 'GET':
        headers['Cache-Control'] = 'no-cache'
    if token:
        headers['Authorization'] = 'Bearer ' + token
    if payload is not None:
        headers['Content-Type'] = 'application/json'
    req = Request('https://api.github.com' + path, data=None if payload is None else json.dumps(payload).encode(),
                  headers=headers, method=method)
    try:
        response = opener.open(req, timeout=15)
    except HTTPError as exc:
        response = exc
    except (URLError, TimeoutError):
        report['requests'].append({'check': label, 'method': method, 'path': path, 'status': None})
        raise RuntimeError(f'{label}: transport outcome unknown; reconcile the marker before repeating') from None
    with response:
        report['requests'].append({'check': label, 'method': method, 'path': path, 'status': response.code})
        raw = response.read(1_000_001)
        require(len(raw) <= 1_000_000, f'{label}: response exceeds fixture limit')
        body = json.loads(raw) if raw and 'json' in response.headers.get('Content-Type', '') else None
        return response.code, body, response.headers


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--preflight', action='store_true', help='read-only controls with the existing gh credential')
    modes.add_argument('--revocation-only', action='store_true', help='verify an existing test PAT using only GET requests')
    modes.add_argument('--check-revoked', action='store_true', help='check a test PAT after it was already deleted')
    args = parser.parse_args()
    mode = 'owner_pat'
    if args.revocation_only:
        mode = 'owner_pat_revocation'
    elif args.check_revoked:
        mode = 'owner_pat_post_delete'
    report = {'repository_id': REPO_ID, 'api_version': API_VERSION, 'requests': [], 'mode': mode,
              'started_at_utc': datetime.now(timezone.utc).isoformat()}
    opener = build_opener(NoRedirect)
    result_path = None

    def call(label, method, path, token=None, payload=None):
        return request(opener, report, label, method, path, token, payload)

    def read(label, path, token):
        status, body, _ = call(label, 'GET', path, token)
        require(status == 200, f'{label}: expected 200, got {status}')
        return body

    def owner_identity(label, token):
        user = read(label, '/user', token)
        require(user['id'] == ACCOUNT_ID and user['login'] == ACCOUNT, 'Credential is not the fixture owner')

    def private_fixture(label, token):
        repo = read(label, REPO, token)
        require(repo['id'] == REPO_ID and repo['full_name'] == ACCOUNT + '/RadishForge-Test'
                and repo['visibility'] == 'private' and repo['default_branch'] == 'main' and repo['has_issues'] is True,
                'Private repository identity or fixture settings changed')

    try:
        owner = subprocess.check_output(['gh', 'auth', 'token', '--hostname', 'github.com'],
                                        text=True, stderr=subprocess.DEVNULL).strip()
        require(bool(owner), 'Existing gh credential is unavailable')
        owner_identity('owner_identity', owner)
        private_fixture('owner_repository', owner)
        require(read('owner_commit', REPO + '/commits/' + SOURCE, owner)['sha'] == SOURCE, 'Fixed source changed')
        release = read('owner_release', REPO + '/releases/tags/m0-release-01', owner)
        require(release['id'] == RELEASE_ID and release['draft'] is False, 'Published reference Release changed')
        require(read('actions_settings', REPO + '/actions/permissions', owner)['enabled'] is False,
                'Actions must stay disabled')
        require(call('anonymous_repository', 'GET', REPO)[0] == 404, 'Anonymous private repository control differed')
        if args.preflight:
            report['result'] = 'preflight_only'
            return 0

        require(sys.stdin.isatty(), 'Use an interactive local terminal for the masked credential prompt')
        marker = 'm0-scope-' + secrets.token_hex(6)
        if mode == 'owner_pat':
            report['fixture_marker'] = marker
        RUNTIME.mkdir(mode=0o700, exist_ok=True)
        require(not RUNTIME.is_symlink(), 'Expected a local runtime directory')
        result_path = RUNTIME / (marker + '.json')
        with result_path.open('x'):
            result_path.chmod(0o600)
        print(f'Result file: {result_path}', flush=True)
        with warnings.catch_warnings():
            warnings.simplefilter('error', getpass.GetPassWarning)
            token = getpass.getpass('Paste the disposable fine-grained PAT (hidden): ').strip()
        require(re.fullmatch(r'github_pat_[A-Za-z0-9_]+', token) and token != owner,
                'Use a separate fine-grained PAT for this fixture')
        if args.check_revoked:
            status, _, _ = call('supplied_pat_after_confirmed_deletion', 'GET', REPO, token)
            private_fixture('owner_repository_after_revocation', owner)
            require(status == 401, f'Supplied PAT rejection was not established: HTTP {status}')
            report['result'] = 'supplied_pat_rejected'
            return 0

        owner_identity('pat_identity_before', token)
        private_fixture('pat_repository_before', token)
        if not args.revocation_only:
            require(read('pat_issue_read', REPO + '/issues/4', token)['title'] == 'm0-compat-issue', 'Issue fixture changed')
            require(read('pat_release_read', REPO + '/releases/' + str(RELEASE_ID), token)['id'] == RELEASE_ID,
                    'Release fixture changed')

            for name, suffix, payload in (
                    ('issue', '/issues', {'title': marker, 'body': 'M0 synthetic scope probe'}),
                    ('release', '/releases', {'tag_name': marker, 'target_commitish': SOURCE,
                                              'name': marker, 'body': 'M0 synthetic scope probe', 'draft': True})):
                status, body, headers = call('pat_' + name + '_write', 'POST', REPO + suffix, token, payload)
                if status == 201:
                    report['unexpected_created_object'] = {'type': name}
                    if isinstance(body, dict):
                        report['unexpected_created_object'].update(id=body.get('id'), number=body.get('number'))
                require(status == 403 and isinstance(body, dict)
                        and body.get('message') == 'Resource not accessible by personal access token'
                        and headers.get('X-RateLimit-Remaining') != '0',
                        f'{name} scope refusal was not established; reconcile the marker')
                time.sleep(1)
                query = '?state=all&per_page=100' if name == 'issue' else '?per_page=100'
                status, rows, headers = call('owner_' + name + '_recheck', 'GET', REPO + suffix + query, owner)
                require(status == 200 and isinstance(rows, list) and 'rel="next"' not in headers.get('Link', '')
                        and all(row.get('title' if name == 'issue' else 'tag_name') != marker for row in rows),
                        f'Owner readback could not confirm no {name} was created')
            print('Read-only scope and no write side effects verified.', flush=True)

        require(input('Delete only this PAT in GitHub Settings. Confirm it is absent from the list, then type REVOKED: ')
                .strip() == 'REVOKED',
                'PAT deletion was not confirmed')
        report['operator_confirmed_at_utc'] = datetime.now(timezone.utc).isoformat()
        status, _, _ = call('same_pat_after_revocation', 'GET', REPO, token)
        private_fixture('owner_repository_after_revocation', owner)
        require(status == 401, f'Same PAT revocation was not established: HTTP {status}')
        report['result'] = 'owner_pat_revocation_verified' if args.revocation_only else 'owner_pat_scope_and_revocation_verified'
        return 0
    except (RuntimeError, OSError, HTTPException, subprocess.CalledProcessError, ValueError, KeyError, EOFError,
            KeyboardInterrupt, getpass.GetPassWarning) as exc:
        report['result'] = 'interrupted'
        report['reason'] = str(exc) if type(exc) is RuntimeError else type(exc).__name__
        return 1
    finally:
        output = json.dumps(report, indent=2) + '\n'
        if result_path is not None:
            result_path.write_text(output, encoding='utf-8')
        print(output, end='')


if __name__ == '__main__':
    raise SystemExit(main())
