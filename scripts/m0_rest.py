"""Compare fixed-source REST behavior on the isolated Gitea side of M0-S04."""
import hashlib
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from m0_issues import REPO, collect_pages, create_issue, read_issue, renew
from m0_local import ROOT, RUNTIME, write_private
from m0_oauth import BinaryBody, authorize, expect
from m0_releases import asset_path, create_release, current_tag, download, read_release, release_view, upload


ORIGIN = 'https://localhost:18443'
MAIN = '37aa3d3ca05aa645e8d970a233b95fcebf35452c'
HEAD = '3527c7d63bebdc0eb5df3405dc23020950df2816'
TAG = 'm0-release-01'
REFS = {'refs/heads/main': MAIN, 'refs/heads/m0-fixture-pr': HEAD, 'refs/tags/' + TAG: MAIN}
ATTACHMENT = b'M0 fixture\n'
DENIED = {403, 404}


def check(condition, label):
    if not condition:
        raise RuntimeError(label)


def import_fixture(target):
    fixture = (ROOT / 'tests/contracts/m0/compat/rest-source.fi').read_bytes()
    check(hashlib.sha256(fixture).hexdigest() == '223a5feddbd5791ad883a2a4b30aabdd209aa15193508e929334650b55cb7cef',
          'Same-source fixture SHA-256 differs')
    check(target == ORIGIN + '/alice/private-fixture.git', 'Unexpected Git fixture destination')
    with tempfile.TemporaryDirectory(dir=RUNTIME, prefix='rest-git-') as work:
        directory = Path(work)
        askpass = directory / 'askpass'
        write_private(askpass, f'''#!{sys.executable}
import json
import sys
from pathlib import Path

prompt = sys.argv[1]
if "https://localhost:18443" not in prompt and "https://alice@localhost:18443" not in prompt:
    raise SystemExit(1)
user, password = json.loads(Path({str(RUNTIME / 'credentials.json')!r}).read_text())["forge"]["alice"]
if prompt.startswith("Username"):
    print(user)
elif prompt.startswith("Password"):
    print(password)
else:
    raise SystemExit(1)
''')
        askpass.chmod(0o700)
        env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
        env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, LC_ALL='C',
                   GIT_TERMINAL_PROMPT='0', GIT_ASKPASS=str(askpass), NO_PROXY='localhost,127.0.0.1')
        config = ['-c', 'credential.helper=', '-c', 'http.proxy=', '-c', 'http.sslVerify=true',
                  '-c', f'http.sslCAInfo={RUNTIME / "ca.crt"}', '-c', 'http.followRedirects=false']

        def git(step, *args, data=None):
            result = subprocess.run(['git', *config, *args], cwd=directory, env=env, input=data,
                                    capture_output=True, timeout=30)
            check(result.returncode == 0, f'Git {step} failed with exit {result.returncode}; reconcile before any retry')
            return result.stdout.decode()

        git('initialize fixture', 'init', '--bare', '--object-format=sha1', '--initial-branch=main')
        git('import fixture', 'fast-import', '--quiet', data=fixture)
        git('check objects', 'fsck', '--strict', '--no-reflogs')
        check({ref: sha for sha, ref in (line.split() for line in git('check refs', 'show-ref').splitlines())} == REFS,
              'Local Git fixture refs differ')
        check(not git('check empty target', 'ls-remote', '--refs', target).strip(), 'Git fixture target is not empty')
        git('push fixture', 'push', '--atomic', target, *(f'{ref}:{ref}' for ref in REFS))
        remote = git('read pushed refs', 'ls-remote', '--refs', target)
        check({ref: sha for sha, ref in (line.split() for line in remote.splitlines())} == REFS,
              'Remote Git fixture refs differ')


def issue_checks(client, owner, writer, read, revoked, remove_writer, record):
    opened = create_issue(client, writer, 'm0-list-open', body='m0 fixture')
    closed = create_issue(client, writer, 'm0-list-closed', body='m0 fixture')
    closed_path = f'{REPO}/issues/{closed["number"]}'
    close = client.request('PATCH', closed_path, token=writer, payload={'state': 'closed'})
    expect(close, {200, 201}, 'close seed Issue')
    check(read_issue(client, read, closed['number'])['state'] == 'closed', 'Seed Issue did not close')
    pr = expect(client.request('POST', REPO + '/pulls', basic=owner, payload={
        'title': 'm0-list-pr', 'head': 'm0-fixture-pr', 'base': 'main'}), {201}, 'open same-source PR')
    current = expect(client.request('GET', f'{REPO}/pulls/{pr["number"]}', token=read), {200}, 'read same-source PR')
    check(current['id'] == pr['id'] and current['state'] == 'open'
          and current['head']['sha'] == HEAD and current['base']['sha'] == MAIN, 'PR readback differs from fixed refs')
    issues, issue_pages = collect_pages(client, REPO + '/issues', read, query={'state': 'all', 'type': 'issues'},
                                        limit=1, issue_only=True)
    pulls, pull_pages = collect_pages(client, REPO + '/issues', read, query={'state': 'all', 'type': 'pulls'}, limit=1)
    check({(v['id'], v['number'], v['state']) for v in issues} == {
        (opened['id'], opened['number'], 'open'), (closed['id'], closed['number'], 'closed')}
        and [(v['number'], v['state']) for v in pulls if isinstance(v.get('pull_request'), dict)] == [(pr['number'], 'open')]
        and len(pulls) == 1, 'Issue and PR result sets differ from the fixture')
    record('issue_and_pr_collection', issue_pages=issue_pages, pull_pages=pull_pages, seed_close_status=close[0],
           issues=[{'id': v['id'], 'number': v['number'], 'state': v['state']} for v in issues], pr_number=pr['number'],
           pr_head=HEAD, pr_base=MAIN)

    issue = create_issue(client, writer, 'm0-compat-issue', body='m0 fixture')
    path = f'{REPO}/issues/{issue["number"]}'
    comments = path + '/comments'
    comment = expect(client.request('POST', comments, token=writer, payload={'body': 'm0 compat comment'}),
                     {201}, 'comment on Issue')
    close = client.request('PATCH', path, token=writer, payload={'state': 'closed'})
    expect(close, {200, 201}, 'close Issue')
    current = read_issue(client, read, issue['number'])
    rows = expect(client.request('GET', comments, token=read, max_bytes=65536), {200}, 'read fixture comments')
    check(current['state'] == 'closed' and current['body'] == 'm0 fixture'
          and isinstance(rows, list) and [(v['id'], v['body']) for v in rows] == [(comment['id'], 'm0 compat comment')],
          'Issue write readback differs')
    record('issue_write_readback', id=issue['id'], number=issue['number'], state=current['state'],
           close_status=close[0], comment_id=comment['id'])

    denied_issue = client.request('POST', REPO + '/issues', token=read, payload={'title': 'm0-denied-readonly'})
    expect(denied_issue, DENIED, 'read scope cannot create Issue')
    listed, _ = collect_pages(client, REPO + '/issues', writer, query={'state': 'all', 'type': 'issues'}, issue_only=True)
    check({v['id'] for v in listed} == {opened['id'], closed['id'], issue['id']}, 'Denied Issue request created an object')
    expect(client.request('GET', path, token=revoked), {200}, 'read Issue before collaborator removal')
    remove_writer()
    expect(client.request('GET', '/api/v1/user', token=revoked), {200}, 'revoked collaborator credential still active')
    denied_get = client.request('GET', path, token=revoked)
    denied_comment = client.request('POST', comments, token=revoked, payload={'body': 'm0-denied-revoked'})
    expect(denied_get, DENIED, 'revoked collaborator cannot read Issue')
    expect(denied_comment, DENIED, 'revoked collaborator cannot comment')
    after_rows = expect(client.request('GET', comments, token=writer, max_bytes=65536), {200}, 'recheck fixture comments')
    check(read_issue(client, writer, issue['number']) == current and after_rows == rows, 'Denied comment changed the Issue')
    record('issue_scope_and_revocation', read_scope_status=denied_issue[0], revoked_read_status=denied_get[0],
           revoked_comment_status=denied_comment[0], no_side_effect=True)


def release_checks(client, writer, writer_read, reader, outsider, record):
    release = create_release(client, writer, {'tag_name': TAG, 'target_commitish': MAIN, 'name': 'M0 fixture',
                                               'body': 'm0 notes', 'draft': True, 'prerelease': False})
    release_id = release['id']
    path = f'{REPO}/releases/{release_id}'
    tag_path = f'{REPO}/releases/tags/{TAG}'
    asset = upload(client, writer, release_id, 'm0-fixture.bin', ATTACHMENT)
    attachment_path = asset_path(release_id, asset['id'])
    check(current_tag(client, writer, TAG) == MAIN, 'Fixed Git tag differs after draft creation')
    check(release_view(expect(client.request('GET', tag_path, token=writer), {200}, 'writer draft by Tag'))['id'] == release_id,
          'Draft by Tag differs from created Release')
    tag_download = f'/alice/private-fixture/releases/download/{TAG}/m0-fixture.bin'
    uuid_download = '/attachments/' + asset['uuid']
    check(download(client, writer, asset, expected=ATTACHMENT)['bytes'] == len(ATTACHMENT), 'Writer attachment read differs')
    for who, token in (('writer_read_scope', writer_read), ('reader_role', reader), ('outsider', outsider)):
        access = {}
        for key, target in (('by_id', path), ('by_tag', tag_path), ('asset_metadata', attachment_path),
                            ('uuid_download', uuid_download), ('tag_download', tag_download)):
            binary = key.endswith('_download')
            response = client.request('GET', target, token=token, binary=binary, max_bytes=65536)
            expect(response, {200, *DENIED}, 'draft access comparison')
            access[key] = response[0]
            if response[0] == 200:
                body = response[1]
                check((isinstance(body, BinaryBody) and body.data == ATTACHMENT) if binary else
                      body['id'] == (asset['id'] if key == 'asset_metadata' else release_id),
                      'Successful draft response differs from fixture')
        record('draft_access_' + who, 'gap' if 200 in access.values() else 'pass', **access)
        if who == 'outsider':
            check(200 not in access.values(), 'Outsider unexpectedly gained draft access')

    expect(client.request('PATCH', path, token=writer, payload={'body': ''}), {200}, 'clear draft body')
    draft = read_release(client, writer, release_id)
    check(draft['draft'] and draft['tag_name'] == TAG and draft['name'] == release['name']
          and draft['assets'] == [asset['id']] and current_tag(client, writer, TAG) == MAIN,
          'Draft association or fixed Tag drifted before publication')
    record('release_empty_body', 'pass' if draft['body'] == '' else 'gap', cleared=draft['body'] == '',
           original_retained=draft['body'] == release['body'], tag=TAG, tag_sha=MAIN)
    expect(client.request('PATCH', path, token=writer, payload={'draft': False}), {200}, 'publish fixture')
    after = read_release(client, writer, release_id)
    check(not after['draft'] and after['tag_name'] == TAG and after['assets'] == [asset['id']]
          and after['body'] == draft['body'] and current_tag(client, writer, TAG) == MAIN,
          'Published Release readback differs')
    public_read = release_view(expect(client.request('GET', tag_path, token=reader), {200}, 'reader published Release by Tag'))
    check(public_read == after, 'Reader received a different published Release')
    expect(client.request('GET', path, token=outsider), DENIED, 'outsider published private Release')
    attachment = download(client, reader, asset, expected=ATTACHMENT)
    record('release_publication_and_attachment', release_id=release_id, asset_id=asset['id'], draft=False,
           tag=TAG, tag_sha=MAIN, **attachment)


def rest_checks(owner, client, users, record):
    check(client.base == ORIGIN and owner['effective_provider_settings']['forge']['actions_enabled'] is False,
          'REST comparison requires the isolated Actions-disabled provider')
    alice = users['alice']
    repo = expect(client.request('POST', '/api/v1/user/repos', basic=alice, payload={
        'name': 'private-fixture', 'private': True, 'auto_init': False, 'default_branch': 'main'}), {201}, 'create empty private repo')
    initial = expect(client.request('GET', REPO, basic=alice), {200}, 'empty private repo readback')
    check(initial['id'] == repo['id'] and initial['full_name'] == 'alice/private-fixture' and initial['private']
          and initial['empty'] and initial['has_issues'] and initial['default_branch'] == 'main',
          'Empty private fixture settings differ')
    record('empty_private_repository', repository_id=initial['id'], actions_enabled=False)
    import_fixture(initial['clone_url'])
    record('identical_git_fixture_refs', refs=REFS, push='atomic', git_transport='HTTPS with task CA')

    def role(name):
        return client.request('GET', f'{REPO}/collaborators/{name}/permission', basic=alice)

    roles = {'bob': 'write', 'carol': 'read', 'dave': 'write'}
    for name, permission in roles.items():
        expect(client.request('PUT', f'{REPO}/collaborators/{name}', basic=alice,
                              payload={'permission': permission}), {204}, 'configure ordinary collaborator')
        check(expect(role(name), {200}, 'read collaborator role')['permission'] == permission, 'Collaborator role differs')
    reader_app, reader, _, _ = authorize('resource_read', client, users['carol'], 'm0-rest-reader')
    outsider_app, outsider, _, _ = authorize('resource_read', client, users['erin'], 'm0-rest-outsider')
    reader_token, outsider_token = reader['access_token'], outsider['access_token']
    repo = expect(client.request('GET', REPO, token=reader_token), {200}, 'ordinary repository reader')
    check(repo['id'] == initial['id'] and repo['private'] and not repo['empty'] and repo['has_issues']
          and repo['default_branch'] == 'main', 'Repository metadata differs after importing refs')
    commit_path = REPO + '/git/commits/' + MAIN
    check(expect(client.request('GET', commit_path, token=reader_token), {200}, 'read fixed commit')['sha'] == MAIN,
          'Commit readback differs from fixture')
    for branch, sha in (('main', MAIN), ('m0-fixture-pr', HEAD)):
        branch_row = expect(client.request('GET', f'{REPO}/branches/{branch}', token=reader_token), {200}, 'read fixed branch')
        check(branch_row['commit']['id'] == sha, 'Branch readback differs from fixture')
    check(current_tag(client, reader_token, TAG) == MAIN, 'Tag readback differs from fixture')
    denied = {}
    for name, token in (('outsider', outsider_token), ('anonymous', None)):
        denied[name] = [client.request('GET', target, token=token)[0] for target in (REPO, commit_path)]
        check(all(status in {401, *DENIED} for status in denied[name]), 'Private repository access was not refused')
    record('ordinary_repository_read_and_private_denials', repository_id=repo['id'], source_sha=MAIN, roles=roles,
           statuses=denied)

    issue_app, issue, _, _ = authorize('issue_write', client, users['bob'], 'm0-rest-issue-writer')
    read_app, writer_read, _, _ = authorize('resource_read', client, users['bob'], 'm0-rest-writer-read')
    _, revocable, _, _ = authorize('issue_write', client, users['dave'], 'm0-rest-revocable')

    def remove_writer():
        expect(client.request('DELETE', REPO + '/collaborators/dave', basic=alice), {204}, 'remove revocable collaborator')
        result = role('dave')
        check(result[0] == 404 or (result[0] == 200 and result[1].get('permission') in ('none', '')),
              'Removed collaborator still has a role')

    issue = renew(client, 'issue_write', issue_app, issue)
    writer_read = renew(client, 'resource_read', read_app, writer_read)
    issue_checks(client, alice, issue['access_token'], writer_read['access_token'],
                 revocable['access_token'], remove_writer, record)
    _, release, _, _ = authorize('release_write', client, users['bob'], 'm0-rest-release-writer')
    reader = renew(client, 'resource_read', reader_app, reader)
    outsider = renew(client, 'resource_read', outsider_app, outsider)
    writer_read = renew(client, 'resource_read', read_app, writer_read)
    release_checks(client, release['access_token'], writer_read['access_token'], reader['access_token'],
                   outsider['access_token'], record)
