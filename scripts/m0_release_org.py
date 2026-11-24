"""Verify G19 organization-team role transitions using only loopback Gitea fixtures."""
import json
from urllib.parse import quote

from m0_issues import renew
from m0_oauth import authorize, expect, receipt
from m0_oci import team
from m0_releases import (BYTES, REPO as PERSONAL_REPO, asset_path, asset_view, check_tag, create_release,
                         digest, payload, publish, read_release, release_view, upload)

ORG = 'm0-release-team-org'
NAME = PERSONAL_REPO.rsplit('/', 1)[1]
REPO = '/api/v1/repos/' + ORG + '/' + NAME
WRITE = {'repo.code': 'read', 'repo.releases': 'write'}
READ = {'repo.code': 'read', 'repo.releases': 'read'}
DENIED = {403, 404}


def change_team(client, owner, label, units, member):
    value = team(client, owner, label, units, organization=ORG)
    path = '/api/v1/teams/' + str(value['id'])
    repo_path = path + '/repos/' + ORG + '/' + NAME
    expect(client.request('PUT', repo_path, basic=owner), {204}, 'assign exact repository to team')
    linked = expect(client.request('GET', repo_path, basic=owner), {200}, 'verify exact team repository')
    member_path = path + '/members/' + member
    expect(client.request('PUT', member_path, basic=owner), {204}, 'add ordinary team member')
    expect(client.request('GET', member_path, basic=owner), {200}, 'verify ordinary team membership')
    return value, member_path, linked['id']


def fixture(client, token, source, label, content, *, published=False):
    tag = 'm0-g19-org-' + label
    expect(client.request('POST', REPO + '/tags', token=token, payload={'tag_name': tag, 'target': source}),
           {201}, 'create local fixed Tag')
    check_tag(client, token, tag, source, repo=REPO)
    release = create_release(client, token, payload(tag, source), repo=REPO)
    asset = upload(client, token, release['id'], 'm0-' + label + '.bin', content, repo=REPO)
    if published:
        release = publish(client, token, release['id'], source, expected_tag=tag, repo=REPO)
    else:
        release = read_release(client, token, release['id'], repo=REPO)
    if release['draft'] == published or release['assets'] != [asset['id']]:
        raise RuntimeError('Release fixture state or attachment differs')
    return release, asset, content


def access_matrix(client, token, fixture_data, *, visibility):
    release, asset, content = fixture_data
    release_path = REPO + '/releases/' + str(release['id'])
    assets = asset_path(release['id'], repo=REPO)
    tag = quote(release['tag_name'], safe='')
    canonical = REPO.removeprefix('/api/v1/repos') + '/releases/download/' + tag
    paths = {
        'list': REPO + '/releases?draft=' + str(release['draft']).lower(),
        'by_id': release_path,
        'by_tag': REPO + '/releases/tags/' + tag,
        'asset_list': assets,
        'asset_detail': assets + '/' + str(asset['id']),
        'uuid_download': '/attachments/' + asset['uuid'],
        'tag_download': canonical + '/' + quote(asset['name'], safe=''),
    }
    statuses = {}
    for key, path in paths.items():
        response = client.request('GET', path, token=token, binary=True, max_bytes=65536)
        statuses[key] = response[0]
        body = response[1].data
        if visibility == 'denied' or (visibility == 'filtered' and key != 'list'):
            expect(response, DENIED, 'reject exact Release ' + key)
            if any(value in body for value in (content, release['body'].encode(), asset['name'].encode())):
                raise RuntimeError('Denied Release response included fixture content')
            continue
        expect(response, {200}, 'read exact Release ' + key)
        if key.endswith('_download'):
            if body != content:
                raise RuntimeError('Release download bytes differ from source')
            continue
        value = json.loads(body)
        if key == 'list':
            matches = [item for item in value if item['id'] == release['id']]
            if visibility == 'filtered':
                if matches or release['body'].encode() in body or asset['name'].encode() in body:
                    raise RuntimeError('Draft fixture appeared in a read-only team listing')
            elif len(matches) != 1 or release_view(matches[0], repo=REPO) != release:
                raise RuntimeError('Release listing did not contain the exact fixture once')
        elif key in ('by_id', 'by_tag'):
            if release_view(value, repo=REPO) != release:
                raise RuntimeError('Release details differ from fixture snapshot')
        else:
            items = value if key == 'asset_list' else [value]
            if len(items) != 1:
                raise RuntimeError('Attachment response differs from one-item fixture')
            actual = asset_view(items[0], repo=REPO, tag=release['tag_name'])
            if any(actual[field] != asset[field] for field in ('id', 'name', 'size', 'uuid')):
                raise RuntimeError('Attachment identity differs from fixture snapshot')
    return statuses


def organization_release_checks(client, users, record):
    alice, bob, carol = (users[name] for name in ('alice', 'bob', 'carol'))
    expect(client.request('POST', '/api/v1/orgs', basic=alice,
                          payload={'username': ORG, 'visibility': 'private'}), {201}, 'create local private organization')
    org = expect(client.request('GET', '/api/v1/orgs/' + ORG, basic=alice), {200}, 'verify private organization')
    repo = expect(client.request('POST', '/api/v1/orgs/' + ORG + '/repos', basic=alice,
                                 payload={'name': NAME, 'private': True, 'auto_init': True}),
                  {201}, 'create organization Release repository')
    repo_readback = expect(client.request('GET', REPO, basic=alice), {200}, 'verify private Release repository')
    if (org['visibility'] != 'private' or not repo_readback['private']
            or repo_readback['id'] != repo['id'] or repo_readback['full_name'] != ORG + '/' + NAME):
        raise RuntimeError('Unexpected organization or repository fixture identity or visibility')
    writer_team, member, writer_repo = change_team(client, alice, 'm0-release-writer', WRITE, 'bob')
    reader_team, reader_member, reader_repo = change_team(client, alice, 'm0-release-reader', READ, 'carol')
    if writer_repo != repo['id'] or reader_repo != repo['id']:
        raise RuntimeError('Team repository differs from the isolated fixture')
    source = expect(client.request('GET', REPO + '/git/commits/' + quote(repo['default_branch'], safe=''),
                                   basic=alice), {200}, 'read exact synthetic source commit')['sha']
    record('release_org_roles_verified', organization_id=org['id'], repository_id=repo['id'], source_sha=source,
           writer_team_id=writer_team['id'], writer_units=writer_team['units_map'],
           reader_team_id=reader_team['id'], reader_units=reader_team['units_map'])
    owner_app, owner_grant, _, _ = authorize('release_write', client, alice, 'm0-g19-org-owner')
    app, grant, writer, _ = authorize('release_write', client, bob, 'm0-g19-org-writer')
    reader_app, reader_grant, reader, _ = authorize('resource_read', client, carol, 'm0-g19-org-reader')
    owner_token = owner_grant['access_token']
    draft = fixture(client, owner_token, source, 'draft', BYTES)
    published = fixture(client, owner_token, source, 'published',
                        b'RadishForge G19 org public-state control\n', published=True)
    for label, (release, asset, content) in (('draft', draft), ('published', published)):
        record('release_org_fixture_' + label, release_id=release['id'], tag=release['tag_name'], draft=release['draft'],
               source_sha=source, attachment_id=asset['id'], attachment_bytes=len(content), attachment_sha256=digest(content))
    # Refresh once before the matrix, then keep each actor on the same access token across all transitions.
    reader_grant = renew(client, 'resource_read', reader_app, reader_grant)
    grant = renew(client, 'release_write', app, grant)
    writer_token, reader_token = grant['access_token'], reader_grant['access_token']
    for phase in ('write', 'read', 'removed'):
        writer_info = receipt('release_write', client, app, grant, subject=writer['sub'])
        reader_info = receipt('resource_read', client, reader_app, reader_grant, subject=reader['sub'])
        role_state = client.request('GET', member, basic=alice)
        expect(role_state, {404} if phase == 'removed' else {200}, 'verify writer team membership for matrix')
        expect(client.request('GET', reader_member, basic=alice), {200}, 'verify independent reader membership')
        repo_access = client.request('GET', REPO, token=writer_token)
        expect(repo_access, DENIED if phase == 'removed' else {200}, 'verify current repository access for matrix')
        writer_draft = access_matrix(client, writer_token, draft,
                                     visibility={'write': 'visible', 'read': 'filtered', 'removed': 'denied'}[phase])
        writer_published = access_matrix(client, writer_token, published,
                                         visibility='denied' if phase == 'removed' else 'visible')
        reader_draft = access_matrix(client, reader_token, draft, visibility='filtered')
        reader_published = access_matrix(client, reader_token, published, visibility='visible')
        receipt('release_write', client, app, grant, subject=writer['sub'])
        receipt('resource_read', client, reader_app, reader_grant, subject=reader['sub'])
        record('release_org_team_' + phase, team_membership_status=role_state[0],
               repository_status=repo_access[0], writer_active=writer_info['active'], reader_active=reader_info['active'],
               writer_scope=writer_info['scope'], reader_scope=reader_info['scope'],
               same_access_tokens_across_phases=True, writer_draft=writer_draft, writer_published=writer_published,
               reader_draft=reader_draft, reader_published=reader_published)
        if phase == 'write':
            updated = team(client, alice, writer_team['name'], READ, ident=writer_team['id'], organization=ORG)
            if updated['id'] != writer_team['id']:
                raise RuntimeError('Team downgrade affected a different team')
            record('release_org_team_units_downgraded', team_id=updated['id'], units=updated['units_map'])
        elif phase == 'read':
            expect(client.request('DELETE', member, basic=alice), {204}, 'remove former writer from exact repository team')
    owner_token = renew(client, 'release_write', owner_app, owner_grant)['access_token']
    for data in (draft, published):
        check_tag(client, owner_token, data[0]['tag_name'], source, repo=REPO)
        access_matrix(client, owner_token, data, visibility='visible')
    record('release_org_fixtures_still_present', unchanged_tag_sha=source, unchanged_release_and_attachment_bytes=True)
