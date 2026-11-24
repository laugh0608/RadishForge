"""G20 draft editing on the fixed loopback Gitea fixture."""
from urllib.parse import quote

from m0_oauth import authorize, expect
from m0_releases import (BYTES, REPO, asset_path, asset_view, check_tag, create_release, download, payload,
                         read_release, release_view, upload)


def release_edit_checks(client, users, repo, record):
    alice, bob = users['alice'], users['bob']
    member = REPO + '/collaborators/bob'
    expect(client.request('PUT', member, basic=alice, payload={'permission': 'write'}),
           {204}, 'assign ordinary Release writer')
    role = expect(client.request('GET', member + '/permission', basic=alice), {200}, 'read exact writer role')
    if role.get('permission') != 'write' or not repo['private'] or repo['full_name'] != 'alice/private-fixture':
        raise RuntimeError('Unexpected repository or writer for the G20 fixture')
    source = expect(client.request('GET', REPO + '/git/commits/' + quote(repo['default_branch'], safe=''),
                                   basic=alice), {200}, 'read exact source commit')['sha']
    _, owner, owner_claims, _ = authorize('release_write', client, alice, 'm0-g20-readback')
    _, writer, writer_claims, _ = authorize('release_write', client, bob, 'm0-g20-edit')
    if writer_claims['sub'] == owner_claims['sub']:
        raise RuntimeError('G20 editing and independent readback identities were merged')
    edit_token, read_token = writer['access_token'], owner['access_token']
    tag = 'm0-g20-edit'
    expect(client.request('POST', REPO + '/tags', token=read_token,
                          payload={'tag_name': tag, 'target': source}), {201}, 'create exact local Tag')
    check_tag(client, read_token, tag, source)
    initial = create_release(client, edit_token, payload(tag, source))
    release_id = initial['id']
    asset = upload(client, edit_token, release_id, 'm0-g20-edit.bin', BYTES)
    stable = read_release(client, read_token, release_id)
    if not stable['draft'] or stable['assets'] != [asset['id']] or str(stable['author_id']) != writer_claims['sub']:
        raise RuntimeError('G20 draft fixture state, author or attachment differs')
    record('release_edit_draft_fixture', release_id=release_id, tag=tag, source_sha=source,
           writer_role=role['permission'], attachment_id=asset['id'],
           **download(client, read_token, asset, expected=BYTES))

    path = REPO + '/releases/' + str(release_id)
    cases = (
        ('omitted_body', {'name': 'M0 G20 title only'}, {'name': 'M0 G20 title only'}, 'pass'),
        ('omitted_name', {'body': 'M0 G20 body only'}, {'body': 'M0 G20 body only'}, 'pass'),
        ('empty_body_with_name', {'name': 'M0 G20 mixed title', 'body': ''},
         {'name': 'M0 G20 mixed title'}, 'gap'),
        ('empty_name_with_body', {'name': '', 'body': 'M0 G20 mixed body'},
         {'body': 'M0 G20 mixed body'}, 'gap'),
        ('null_fields_outside_schema', {'name': None, 'body': None}, {}, 'pass'),
    )
    for label, patch, updates, evidence in cases:
        before = read_release(client, read_token, release_id)
        if before != stable:
            raise RuntimeError('G20 draft changed unexpectedly between cases')
        response = client.request('PATCH', path, token=edit_token, payload=patch)
        statuses = {200, 400, 422} if label == 'null_fields_outside_schema' else {200}
        expect(response, statuses, 'edit exact draft fields')
        stable = read_release(client, read_token, release_id)
        changed = [key for key in stable if stable[key] != before[key]]
        record('release_edit_' + label, evidence, http_status=response[0], request_fields=patch,
               before={key: before[key] for key in ('name', 'body')},
               after={key: stable[key] for key in ('name', 'body')}, changed_fields=changed)
        if stable != dict(before, **updates) or (response[0] == 200 and release_view(response[1]) != stable):
            raise RuntimeError('G20 independent readback differs from the fixed-version case')
    check_tag(client, read_token, tag, source)
    final_asset = asset_view(expect(client.request('GET', asset_path(release_id, asset['id']), token=read_token),
                                   {200}, 'read attachment after edits'), tag=tag)
    if final_asset != asset:
        raise RuntimeError('G20 attachment identity, size or download URL changed')
    record('release_edit_unchanged_draft_attachment_and_tag', release_id=release_id, draft=stable['draft'],
           attachment_id=final_asset['id'], tag=tag, source_sha=source,
           **download(client, read_token, final_asset, expected=BYTES))
