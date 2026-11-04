"""Real isolated Release contracts; synthetic bytes and references, no product publisher."""
import base64
import hashlib
import re
import secrets
import urllib.parse

from m0_issues import collect_pages, renew
from m0_oauth import BinaryBody, Client, REQUESTS, authorize, expect
from m0_response_loss import FAULT_ORIGIN, ResponseLoss

REPO = '/api/v1/repos/alice/private-fixture'
ORIGIN = 'https://localhost:18443'
BYTES = b'RadishForge M0 synthetic attachment\x00\xff\x80\r\n' + bytes(range(256)) * 4


def digest(data):
    return hashlib.sha256(data).hexdigest()


def release_view(row):
    keys = {'id', 'tag_name', 'name', 'body', 'draft', 'prerelease', 'target_commitish', 'author', 'assets'}
    if (not isinstance(row, dict) or not keys.issubset(row)
            or type(row['id']) is not int or row['id'] <= 0
            or any(not isinstance(row[k], str) for k in ('tag_name', 'name', 'body', 'target_commitish'))
            or any(type(row[k]) is not bool for k in ('draft', 'prerelease'))
            or not isinstance(row['author'], dict) or type(row['author'].get('id')) is not int
            or row['author']['id'] <= 0 or not isinstance(row['assets'], list)):
        raise RuntimeError('Invalid Release response identity, state or fields')
    assets = [asset_view(v, tag=row['tag_name'])['id'] for v in row['assets']]
    if len(set(assets)) != len(assets):
        raise RuntimeError('Duplicate attachment identity in Release')
    return {**{k: row[k] for k in ('id', 'tag_name', 'name', 'body', 'draft', 'prerelease', 'target_commitish')},
            'author_id': row['author']['id'], 'assets': sorted(assets)}


def asset_view(row, *, tag=None):
    if (not isinstance(row, dict) or type(row.get('id')) is not int or row['id'] <= 0
            or type(row.get('size')) is not int or row['size'] < 0
            or not isinstance(row.get('name'), str) or not row['name']
            or not isinstance(row.get('uuid'), str) or not re.fullmatch(r'[a-f0-9-]{36}', row['uuid'])
            or not isinstance(row.get('browser_download_url'), str)):
        raise RuntimeError('Invalid attachment metadata')
    url = urllib.parse.urlsplit(row['browser_download_url'])
    canonical = re.fullmatch(r'/alice/private-fixture/releases/download/(m0-[a-z0-9-]+)/([^/]+)', url.path)
    canonical = (canonical is not None and urllib.parse.unquote(canonical[2]) == row['name']
                 and (tag is None or canonical[1] == tag))
    if (f'{url.scheme}://{url.netloc}' != ORIGIN or url.query or url.fragment
            or not (url.path == '/attachments/' + row['uuid'] or canonical)):
        raise RuntimeError('Attachment download URL is outside its exact task UUID or Release/name endpoint')
    return {k: row[k] for k in ('id', 'uuid', 'name', 'size', 'browser_download_url')}


def asset_path(release_id, asset_id=None, *, repo=REPO):
    path = repo + '/releases/' + str(release_id) + '/assets'
    return path if asset_id is None else path + '/' + str(asset_id)


def read_release(client, token, release_id):
    return release_view(expect(client.request('GET', REPO + '/releases/' + str(release_id), token=token),
                               {200}, 'Release readback'))


def payload(tag, sha, **changes):
    return dict({'tag_name': tag, 'target_commitish': sha, 'name': 'M0 ' + tag,
                 'body': 'M0 synthetic operation ' + tag, 'draft': True, 'prerelease': False}, **changes)


def create_release(client, token, data):
    row = expect(client.request('POST', REPO + '/releases', token=token, payload=data), {201}, 'create synthetic Release')
    current = read_release(client, token, row['id'])
    if any(current[k] != data[k] for k in ('tag_name', 'target_commitish', 'name', 'body', 'draft', 'prerelease')):
        raise RuntimeError('Created Release differs from its explicit request')
    return current


def current_tag(client, token, tag, *, repo=REPO):
    result = client.request('GET', repo + '/tags/' + urllib.parse.quote(tag, safe=''), token=token)
    if result[0] == 404:
        return None
    row = expect(result, {200}, 'read exact Tag')
    commit = row.get('commit', {}).get('sha') if isinstance(row, dict) else None
    if not isinstance(commit, str) or not re.fullmatch(r'[a-f0-9]{40}', commit):
        raise RuntimeError('Tag did not resolve to a full commit SHA')
    return commit


def check_tag(client, token, tag, expected, *, allow_missing=False):
    if not isinstance(expected, str) or not re.fullmatch(r'[a-f0-9]{40}', expected):
        raise ValueError('Expected commit must be an explicit full SHA')
    actual = current_tag(client, token, tag)
    if actual is None and allow_missing:
        return None
    if actual != expected:
        raise ValueError('Tag is missing or points to a different commit; do not publish')
    return actual


def publish(client, token, release_id, expected_sha):
    before = read_release(client, token, release_id)
    check_tag(client, token, before['tag_name'], expected_sha, allow_missing=True)
    expect(client.request('PATCH', REPO + '/releases/' + str(release_id), token=token,
                          payload={'draft': False}), {200}, 'publish synthetic Release')
    after = read_release(client, token, release_id)
    check_tag(client, token, after['tag_name'], expected_sha)
    if after['draft'] or after['id'] != before['id']:
        raise RuntimeError('Publication readback differs')
    return after


def assets(client, token, release_id):
    rows = expect(client.request('GET', asset_path(release_id), token=token), {200}, 'list Release attachments')
    if not isinstance(rows, list) or len(rows) > 20:
        raise RuntimeError('Attachment list exceeds the bounded fixture')
    result = [asset_view(v) for v in rows]
    if len({v['id'] for v in result}) != len(result):
        raise RuntimeError('Duplicate attachment identity')
    return result


def download(client, token, asset, *, expected=None):
    asset = asset_view(asset)
    body = expect(client.request('GET', asset['browser_download_url'], token=token,
                                 binary=True, max_bytes=65536), {200}, 'download exact attachment bytes')
    if not isinstance(body, BinaryBody) or len(body.data) != asset['size']:
        raise RuntimeError('Attachment size or binary response differs')
    length = body.headers.get('Content-Length')
    if length is not None and length != str(len(body.data)):
        raise RuntimeError('Attachment Content-Length differs')
    if expected is not None and body.data != expected:
        raise RuntimeError('Attachment content SHA-256 differs from its source fixture')
    return {'bytes': len(body.data), 'sha256': digest(body.data)}


def upload(client, token, release_id, name, data=BYTES, *, multipart=False):
    if not re.fullmatch(r'm0-[a-z0-9-]+\.bin', name):
        raise ValueError('Only synthetic attachment names are allowed')
    path = asset_path(release_id) + '?' + urllib.parse.urlencode({'name': name})
    raw, content_type = data, 'application/octet-stream'
    if multipart:
        raw = (b'--m0-release-boundary\r\nContent-Disposition: form-data; name="attachment"; filename="' + name.encode()
               + b'"\r\nContent-Type: application/octet-stream\r\n\r\n' + data + b'\r\n--m0-release-boundary--\r\n')
        content_type = 'multipart/form-data; boundary=m0-release-boundary'
    row = expect(client.request('POST', path, token=token, raw=raw, content_type=content_type), {201}, 'upload synthetic attachment')
    current = asset_view(expect(client.request('GET', asset_path(release_id, row['id']), token=token), {200}, 'attachment metadata readback'))
    if current['name'] != name or current['size'] != len(data):
        raise RuntimeError('Attachment upload metadata differs')
    download(client, token, current, expected=data)
    return current


def reconcile_release(client, token, wanted, author_id):
    result = client.request('GET', REPO + '/releases/tags/' + urllib.parse.quote(wanted['tag_name'], safe=''), token=token)
    if result[0] == 404:
        return {'state': 'unknown', 'matches': 0}
    row = release_view(expect(result, {200}, 'reconcile Release by exact tag'))
    matches = row['author_id'] == author_id and all(row[k] == wanted[k] for k in (
        'tag_name', 'name', 'body', 'target_commitish', 'draft', 'prerelease'))
    detail = read_release(client, token, row['id'])
    if not matches or detail != row:
        return {'state': 'unknown', 'matches': 1}
    return {'state': 'observed', 'matches': 1, 'id': row['id']}


def reconcile_asset(client, token, release_id, name, data):
    candidates = [v for v in assets(client, token, release_id) if v['name'] == name]
    receipts = [{'id': v['id'], **download(client, token, v)} for v in candidates]
    verified = [r for r in receipts if r['bytes'] == len(data) and r['sha256'] == digest(data)]
    result = {'state': 'unknown', 'matches': len(candidates), 'verified_contents': len(verified)}
    if len(candidates) == len(verified) == 1:
        current = asset_view(expect(client.request('GET', asset_path(release_id, candidates[0]['id']), token=token),
                                    {200}, 'reconcile attachment detail'))
        if all(current[k] == candidates[0][k] for k in ('id', 'uuid', 'name', 'size')):
            result.update(state='observed', id=current['id'])
    return result


def fault_call(client, token, operation, path, data, *, forward, partial_bytes=None):
    with ResponseLoss(operation, path, token, data, forward=forward, partial_bytes=partial_bytes) as fault:
        try:
            Client(FAULT_ORIGIN).request(fault.method, path, token=token, timeout=1,
                                        **({'raw': data} if isinstance(data, bytes) else {'payload': data}))
        except OSError as error:
            error_type = type(error).__name__
        else:
            raise RuntimeError('Response-loss caller did not actually time out')
    if fault.error_type or fault.attempts != 1 or fault.forwarded != int(forward):
        raise RuntimeError('Response-loss transport did not match its bounded scenario')
    return {'caller_error': error_type, 'request_attempts': fault.attempts, 'upstream_writes': fault.forwarded,
            'upstream_status': fault.upstream_status, 'upstream_body_bytes': fault.sent_bytes,
            'fault_listener_stopped': True, 'automatic_retries': 0}


def release_checks(client, credentials, record):
    alice, bob, carol = (credentials['forge'][v] for v in ('alice', 'bob', 'carol'))
    expect(client.request('PUT', REPO + '/collaborators/bob', basic=alice, payload={'permission': 'write'}), {204}, 'Release collaborator fixture')
    repo = expect(client.request('GET', REPO, basic=alice), {200}, 'Release source fixture')
    initial = expect(client.request('GET', REPO + '/git/commits/' + urllib.parse.quote(repo['default_branch'], safe=''), basic=alice),
                     {200}, 'resolve initial source commit')['sha']
    changed = expect(client.request('POST', REPO + '/contents/m0-release-source.txt', basic=alice,
                                    payload={'content': base64.b64encode(b'M0 isolated Release source\n').decode(),
                                             'message': 'test: isolate Release source'}), {201}, 'second source fixture')['commit']['sha']
    if initial == changed or any(not re.fullmatch(r'[a-f0-9]{40}', v) for v in (initial, changed)):
        raise RuntimeError('Source fixture did not contain two distinct full commits')
    app, write, claims, _ = authorize('release_write', client, alice, 'm0-release-owner')
    read_app, read, _, _ = authorize('resource_read', client, alice, 'm0-release-reader-scope')
    issue_app, issue, _, _ = authorize('issue_write', client, alice, 'm0-release-wrong-purpose')
    bob_app, bob_grant, _, _ = authorize('release_write', client, bob, 'm0-release-collaborator')
    carol_app, carol_grant, _, _ = authorize('release_write', client, carol, 'm0-release-outsider')
    token = write['access_token']
    rows, _ = collect_pages(client, REPO + '/releases', token)
    if rows:
        raise RuntimeError('Fresh repository Release list was not empty')
    if len({v['client_id'] for v in (app, read_app, issue_app, bob_app, carol_app)}) != 5:
        raise RuntimeError('Release purposes or principals reused an OAuth client')
    record('release_purpose_separate_confidential_grants_and_source_commits', source_sha=initial, second_sha=changed,
           scope='openid read:user write:repository', scope_is_not_release_only=True,
           distinct_clients=len({v['client_id'] for v in (app, read_app, issue_app, bob_app, carol_app)}))
    targets = [create_release(client, token, payload('m0-release-' + str(i), initial)) for i in range(3)]
    main = targets[0]
    rows, pages = collect_pages(client, REPO + '/releases', token, query={'draft': 'true'}, limit=2)
    if {v['id'] for v in rows} != {v['id'] for v in targets} or pages != [2, 1, 0]:
        raise RuntimeError('Release pagination omitted or duplicated a draft')
    for target in targets:
        if current_tag(client, token, target['tag_name']) is not None:
            raise RuntimeError('A newly created draft unexpectedly created a Tag')
    read_rows, _ = collect_pages(client, REPO + '/releases', read['access_token'], query={'draft': 'true'})
    if read_rows:
        raise RuntimeError('Read scope listed draft Releases')
    expect(client.request('GET', REPO + '/releases/' + str(main['id']), token=read['access_token']), {404}, 'read scope cannot read draft metadata')
    for candidate in (read['access_token'], issue['access_token']):
        expect(client.request('POST', REPO + '/releases', token=candidate, payload=payload('m0-forbidden', initial)), {403}, 'wrong Release write scope')
        expect(client.request('POST', asset_path(main['id']) + '?name=m0-forbidden.bin', token=candidate, raw=BYTES), {403}, 'wrong attachment write scope')
    duplicate = client.request('POST', REPO + '/releases', token=token, payload=payload(main['tag_name'], initial))
    expect(duplicate, {409}, 'duplicate exact Release tag')
    if read_release(client, token, main['id']) != main:
        raise RuntimeError('Duplicate Release request changed its existing object')
    record('release_empty_draft_pages_read_scope_exclusion_and_duplicate_tag', pages=pages, duplicate_status=409, draft_creates_tag=False)
    write = renew(client, 'release_write', app, write); token = write['access_token']
    read = renew(client, 'resource_read', read_app, read)
    bob_grant = renew(client, 'release_write', bob_app, bob_grant)
    carol_grant = renew(client, 'release_write', carol_app, carol_grant)
    raw_asset = upload(client, token, main['id'], 'm0-raw.bin')
    multipart_asset = upload(client, token, main['id'], 'm0-multipart.bin', multipart=True)
    full_draft = expect(client.request('GET', REPO + '/releases/' + str(main['id']), token=token), {200}, 'draft advertised URLs')
    advertised = asset_view(next(v for v in full_draft['assets'] if v['id'] == raw_asset['id']), tag=main['tag_name'])
    download(client, token, advertised, expected=BYTES)
    draft_read = client.request('GET', raw_asset['browser_download_url'], token=read['access_token'], binary=True)
    advertised_read = client.request('GET', advertised['browser_download_url'], token=read['access_token'], binary=True)
    draft_leak = draft_read[0] == 200 and isinstance(draft_read[1], BinaryBody) and draft_read[1].data == BYTES
    denied = all(v[0] in (401, 403, 404) for v in (draft_read, advertised_read))
    record('draft_attachment_read_scope_matches_draft_api_gate', 'pass' if denied else 'gap',
           metadata_status=404, direct_download_status=draft_read[0], advertised_download_status=advertised_read[0],
           original_bytes_visible=draft_leak)
    aux = targets[1]
    expect(client.request('PATCH', REPO + '/releases/' + str(aux['id']), token=bob_grant['access_token'],
                          payload={'name': 'M0 writer edit', 'body': 'M0 writer explanation'}), {200}, 'ordinary collaborator edits Release')
    if read_release(client, token, aux['id'])['body'] != 'M0 writer explanation':
        raise RuntimeError('Collaborator Release edit was not persisted')
    collaborator_asset = upload(client, bob_grant['access_token'], aux['id'], 'm0-collaborator.bin')
    for method, path, data in [('GET', REPO + '/releases', None), ('GET', REPO + '/releases/' + str(main['id']), None),
                               ('POST', REPO + '/releases', payload('m0-outsider', initial)),
                               ('PATCH', REPO + '/releases/' + str(main['id']), {'name': 'must not change'})]:
        expect(client.request(method, path, token=carol_grant['access_token'], payload=data), {403, 404}, 'outsider Release access')
    outsider_download = client.request('GET', raw_asset['browser_download_url'], token=carol_grant['access_token'], binary=True)
    expect(outsider_download, {403, 404}, 'outsider direct attachment')
    anonymous = client.request('GET', raw_asset['browser_download_url'], binary=True)
    expect(anonymous, {302, 303, 401, 403, 404}, 'anonymous private attachment')
    record('ordinary_writer_release_and_attachment_mutations_outsider_and_anonymous_denied',
           writer='ordinary collaborator', outsider_direct_status=outsider_download[0],
           anonymous_status=anonymous[0], attachment_sha256=digest(BYTES), attachment_bytes=len(BYTES))
    expect(client.request('PATCH', REPO + '/releases/' + str(main['id']), token=token,
                          payload={'name': 'M0 edited release', 'body': 'M0 edited explanation', 'prerelease': True}), {200}, 'edit Release description')
    edited = read_release(client, token, main['id'])
    if (edited['name'], edited['body'], edited['prerelease']) != ('M0 edited release', 'M0 edited explanation', True):
        raise RuntimeError('Release description/state edit was not persisted')
    expect(client.request('PATCH', REPO + '/releases/' + str(main['id']), token=token,
                          payload={'body': '', 'name': ''}), {200}, 'raw empty Release fields')
    empty = read_release(client, token, main['id'])
    record('release_empty_name_and_body_clear', 'pass' if empty['name'] == empty['body'] == '' else 'gap',
           http_status=200, name_cleared=empty['name'] == '', body_cleared=empty['body'] == '')
    published = publish(client, token, main['id'], initial)
    if not published['prerelease']:
        raise RuntimeError('Publication lost prerelease flag')
    expect(client.request('PATCH', REPO + '/releases/' + str(main['id']), token=token, payload={'prerelease': False}), {200}, 'stable Release flag')
    for candidate in (token, read['access_token'], bob_grant['access_token']):
        result = expect(client.request('GET', REPO + '/releases/' + str(main['id']), token=candidate), {200}, 'published Release visibility')
        if release_view(result)['draft']:
            raise RuntimeError('Published Release still marked draft')
        download(client, candidate, raw_asset, expected=BYTES)
        download(client, candidate, advertised, expected=BYTES)
    record('release_publish_full_tag_commit_and_binary_download_verified', release_id=main['id'], source_sha=initial,
           tag_commit=current_tag(client, token, main['tag_name']), raw_sha256=digest(BYTES), multipart_sha256=digest(BYTES))
    expect(client.request('PATCH', asset_path(main['id'], multipart_asset['id']), token=token,
                          payload={'name': 'm0-renamed.bin'}), {201}, 'rename attachment')
    renamed = asset_view(expect(client.request('GET', asset_path(main['id'], multipart_asset['id']), token=token), {200}, 'renamed metadata'))
    if renamed['name'] != 'm0-renamed.bin':
        raise RuntimeError('Attachment rename did not persist')
    download(client, token, renamed, expected=BYTES)
    record('release_raw_multipart_upload_and_attachment_rename', raw_id=raw_asset['id'], multipart_id=renamed['id'])
    incorrect = upload(client, token, main['id'], 'm0-incorrect-content.bin', BYTES[:-1] + b'X')
    try:
        download(client, token, incorrect, expected=BYTES)
    except RuntimeError as error:
        if str(error) != 'Attachment content SHA-256 differs from its source fixture':
            raise
    else:
        raise RuntimeError('Wrong artifact bytes passed the expected-content verification')
    record('incorrect_artifact_bytes_rejected_after_real_download', expected_sha256=digest(BYTES),
           actual_sha256=digest(BYTES[:-1] + b'X'), fixture='deliberately uploaded different content, not wire corruption')
    write = renew(client, 'release_write', app, write); token = write['access_token']
    tag_and_invalid_cases(client, token, alice, initial, changed, record)
    write = renew(client, 'release_write', app, write); token = write['access_token']
    association_and_deletion(client, token, main['id'], renamed, collaborator_asset, aux['id'], alice, initial, record)
    write = renew(client, 'release_write', app, write); token = write['access_token']
    bob_grant = renew(client, 'release_write', bob_app, bob_grant)
    role_checks(client, alice, token, bob_grant['access_token'], main['id'], raw_asset, aux['id'], record)
    for forward in (True, False):
        write = renew(client, 'release_write', app, write); token = write['access_token']
        timeout_create(client, token, int(claims['sub']), initial, forward, record)
        timeout_publish(client, token, initial, forward, record)
        timeout_asset(client, token, main['id'], forward, record)
    write = renew(client, 'release_write', app, write); token = write['access_token']
    timeout_asset(client, token, main['id'], True, record, partial=True)
    upload(client, token, main['id'], 'm0-ambiguous.bin')
    upload(client, token, main['id'], 'm0-ambiguous.bin')
    start = len(REQUESTS)
    result = reconcile_asset(client, token, main['id'], 'm0-ambiguous.bin', BYTES)
    if result['state'] != 'unknown' or result['matches'] != 2 or any(v['method'] != 'GET' for v in REQUESTS[start:]):
        raise RuntimeError('Same-name attachment reconciliation did not remain unknown')
    record('same_name_attachments_are_not_an_idempotency_key', reconciliation=result, automatic_retries=0)
    expect(client.request('DELETE', REPO, basic=alice), {204}, 'delete task repository as ordinary owner')
    expect(client.request('GET', REPO + '/releases/' + str(main['id']), token=token), {404}, 'deleted repository Release')
    expect(client.request('GET', raw_asset['browser_download_url'], token=token, binary=True), {404}, 'deleted repository attachment')
    record('deleted_repository_release_and_attachment_not_readable')


def tag_and_invalid_cases(client, token, owner, initial, changed, record):
    tag = 'm0-existing-other-commit'
    result = client.request('POST', REPO + '/tags', token=token, payload={'tag_name': tag, 'target': changed})
    expect(result, {201}, 'existing Tag fixture; fixed handler uses 201 despite OpenAPI 200')
    record('tag_create_status_differs_from_fixed_openapi', 'gap', declared_status=200, actual_status=result[0])
    before = len(REQUESTS)
    try:
        check_tag(client, token, tag, initial)
    except ValueError:
        pass
    else:
        raise RuntimeError('Mismatched Tag passed the local publication preflight')
    if any(r['method'] != 'GET' for r in REQUESTS[before:]):
        raise RuntimeError('Tag preflight wrote upstream')
    raw = create_release(client, token, payload(tag, initial))
    result = client.request('PATCH', REPO + '/releases/' + str(raw['id']), token=token, payload={'draft': False})
    current = read_release(client, token, raw['id'])
    actual = current_tag(client, token, tag)
    safe = result[0] in (400, 409, 422) and current['draft'] or actual == initial
    record('upstream_existing_tag_target_mismatch', 'pass' if safe else 'gap', http_status=result[0],
           requested_commit=initial, actual_tag_commit=actual, draft=current['draft'], local_preflight_rejects=True)
    drift = 'm0-drifting-tag'
    expect(client.request('POST', REPO + '/tags', token=token, payload={'tag_name': drift, 'target': initial}), {201}, 'drift fixture')
    check_tag(client, token, drift, initial)
    expect(client.request('DELETE', REPO + '/tags/' + drift, token=token), {204}, 'remove synthetic drift Tag')
    expect(client.request('POST', REPO + '/tags', token=token, payload={'tag_name': drift, 'target': changed}), {201}, 'move synthetic Tag')
    start = len(REQUESTS)
    try:
        check_tag(client, token, drift, initial)
    except ValueError:
        pass
    else:
        raise RuntimeError('Moved Tag passed the publication preflight')
    record('moved_tag_rejected_by_read_only_preflight', source_sha=initial, actual_sha=changed,
           preflight_writes=sum(r['method'] != 'GET' for r in REQUESTS[start:]))
    invalid = create_release(client, token, payload('m0-invalid-target', 'm0-target-does-not-exist'))
    result = client.request('PATCH', REPO + '/releases/' + str(invalid['id']), token=token, payload={'draft': False})
    current = read_release(client, token, invalid['id'])
    tag_sha = current_tag(client, token, invalid['tag_name'])
    safe = result[0] in (400, 404, 409, 422) and current['draft'] and tag_sha is None
    record('upstream_invalid_target_publish_readback', 'pass' if safe else 'gap', http_status=result[0],
           draft_retained=current['draft'], tag_created=tag_sha is not None, automatic_retries=0)


def association_and_deletion(client, token, main_id, removable, foreign_asset, foreign_id, owner, sha, record):
    other = expect(client.request('POST', '/api/v1/user/repos', basic=owner,
                                  payload={'name': 'release-other-fixture', 'private': True, 'auto_init': True}), {201}, 'cross-repository Release fixture')
    other_path = '/api/v1/repos/alice/' + other['name']
    foreign = expect(client.request('POST', other_path + '/releases', token=token,
                                    payload={'tag_name': 'm0-other', 'draft': True}), {201}, 'foreign Release fixture')
    for path in (asset_path(main_id, foreign_asset['id']), asset_path(foreign['id'], removable['id'], repo=other_path)):
        for method, data in [('GET', None), ('PATCH', {'name': 'm0-must-not-edit.bin'}), ('DELETE', None)]:
            expect(client.request(method, path, token=token, payload=data), {404}, 'attachment must belong to exact Release/repository')
    expect(client.request('POST', asset_path(foreign['id']) + '?name=m0-must-not-upload.bin', token=token, raw=BYTES),
           {404}, 'Release ID must belong to repository')
    download(client, token, removable, expected=BYTES)
    download(client, token, foreign_asset, expected=BYTES)
    expect(client.request('DELETE', asset_path(main_id, removable['id']), token=token), {204}, 'delete synthetic attachment')
    expect(client.request('GET', asset_path(main_id, removable['id']), token=token), {404}, 'deleted attachment metadata')
    expect(client.request('GET', removable['browser_download_url'], token=token, binary=True), {404}, 'deleted attachment bytes')
    disposable = create_release(client, token, payload('m0-delete-release', sha))
    attached = upload(client, token, disposable['id'], 'm0-delete-with-release.bin')
    publish(client, token, disposable['id'], sha)
    expect(client.request('DELETE', REPO + '/releases/' + str(disposable['id']), token=token), {204}, 'delete published Release')
    for path in (REPO + '/releases/' + str(disposable['id']), asset_path(disposable['id'], attached['id'])):
        expect(client.request('GET', path, token=token), {404}, 'deleted Release/attachment metadata')
    expect(client.request('GET', attached['browser_download_url'], token=token, binary=True), {404}, 'deleted Release attachment download')
    tag = current_tag(client, token, disposable['tag_name'])
    record('release_attachment_cross_association_and_delete_readback', removed_release=disposable['id'],
           tag_survives_release_delete=tag is not None, surviving_tag_commit=tag)


def role_checks(client, owner, token, bob_token, published_id, asset, draft_id, record):
    expect(client.request('PUT', REPO + '/collaborators/bob', basic=owner, payload={'permission': 'read'}), {204}, 'downgrade Release collaborator')
    permission = expect(client.request('GET', REPO + '/collaborators/bob/permission', basic=owner), {200}, 'read back repository reader role')
    if permission.get('permission') != 'read':
        raise RuntimeError('Release reader role did not take effect')
    expect(client.request('GET', REPO + '/releases/' + str(published_id), token=bob_token), {200}, 'reader may see published Release')
    download(client, bob_token, asset, expected=BYTES)
    expect(client.request('GET', REPO + '/releases/' + str(draft_id), token=bob_token), {404}, 'reader cannot see draft')
    draft = expect(client.request('GET', REPO + '/releases/' + str(draft_id), token=token), {200}, 'owner draft attachment fixture')
    for row in draft['assets']:
        value = asset_view(row, tag=draft['tag_name'])
        for path in (value['browser_download_url'], '/attachments/' + value['uuid']):
            expect(client.request('GET', path, token=bob_token, binary=True), {404}, 'repository reader cannot download draft via either route')
    before = read_release(client, token, published_id)
    for method, path, data in [('PATCH', REPO + '/releases/' + str(published_id), {'body': 'must not edit'}),
                               ('DELETE', REPO + '/releases/' + str(published_id), None),
                               ('DELETE', asset_path(published_id, asset['id']), None)]:
        expect(client.request(method, path, token=bob_token, payload=data), {403}, 'repository reader cannot manage Release')
    expect(client.request('POST', asset_path(published_id) + '?name=m0-reader-denied.bin', token=bob_token, raw=BYTES), {403}, 'reader cannot upload')
    if read_release(client, token, published_id) != before:
        raise RuntimeError('Reader mutation changed Release')
    expect(client.request('DELETE', REPO + '/collaborators/bob', basic=owner), {204}, 'revoke Release collaborator')
    for method, path, data in [('GET', REPO + '/releases', None), ('GET', REPO + '/releases/' + str(published_id), None),
                               ('PATCH', REPO + '/releases/' + str(published_id), {'body': 'must not edit'})]:
        expect(client.request(method, path, token=bob_token, payload=data), {403, 404}, 'revoked Release collaborator')
    expect(client.request('GET', asset['browser_download_url'], token=bob_token, binary=True), {403, 404}, 'revoked direct attachment')
    if read_release(client, token, published_id) != before:
        raise RuntimeError('Revoked collaborator changed Release')
    record('release_reader_role_and_revoked_collaborator_boundaries')


def timeout_create(client, token, author_id, sha, forward, record):
    wanted = payload('m0-timeout-' + secrets.token_hex(6), sha)
    transport = fault_call(client, token, 'release_create', REPO + '/releases', wanted, forward=forward)
    if forward and transport['upstream_status'] != 201:
        raise RuntimeError('Committed create response-loss fixture did not return upstream 201')
    start = len(REQUESTS)
    outcome = reconcile_release(client, token, wanted, author_id)
    if outcome['state'] != ('observed' if forward else 'unknown') or any(v['method'] != 'GET' for v in REQUESTS[start:]):
        raise RuntimeError('Release create reconciliation wrote or misclassified the result')
    record('release_create_response_loss_' + ('committed' if forward else 'not_forwarded'), **transport, reconciliation=outcome)


def timeout_publish(client, token, sha, forward, record):
    target = create_release(client, token, payload('m0-publish-timeout-' + secrets.token_hex(5), sha))
    transport = fault_call(client, token, 'release_publish', REPO + '/releases/' + str(target['id']), {'draft': False}, forward=forward)
    if forward and transport['upstream_status'] != 200:
        raise RuntimeError('Committed publish response-loss fixture did not return upstream 200')
    start = len(REQUESTS)
    current = read_release(client, token, target['id'])
    tag = current_tag(client, token, target['tag_name'])
    observed = not current['draft'] and tag == sha
    if observed != forward or any(v['method'] != 'GET' for v in REQUESTS[start:]):
        raise RuntimeError('Publication reconciliation wrote or misclassified the result')
    record('release_publish_response_loss_' + ('committed' if forward else 'not_forwarded'), **transport,
           reconciliation={'state': 'observed' if observed else 'unknown', 'draft': current['draft'], 'tag_commit': tag})


def timeout_asset(client, token, release_id, forward, record, *, partial=False):
    name = 'm0-asset-timeout-' + secrets.token_hex(5) + '.bin'
    transport = fault_call(client, token, 'release_asset', asset_path(release_id) + '?name=' + name, BYTES,
                           forward=forward, partial_bytes=len(BYTES) // 2 if partial else None)
    if forward and not partial and transport['upstream_status'] != 201:
        raise RuntimeError('Committed attachment response loss did not return upstream 201')
    start = len(REQUESTS)
    outcome = reconcile_asset(client, token, release_id, name, BYTES)
    expected = 'observed' if forward and not partial else 'unknown'
    if outcome['state'] != expected or any(v['method'] != 'GET' for v in REQUESTS[start:]):
        raise RuntimeError('Attachment reconciliation wrote or misclassified the result')
    status = 'gap' if partial and outcome['matches'] else 'pass'
    record('release_partial_attachment_disconnect' if partial else 'release_asset_response_loss_' + ('committed' if forward else 'not_forwarded'),
           status, **transport, reconciliation=outcome)
