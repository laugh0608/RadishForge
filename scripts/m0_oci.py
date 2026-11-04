"""Real isolated OCI protocol, organization permissions and unknown-write evidence."""
import base64
import json
import secrets

from m0_local import write_private, RUNTIME
from m0_oauth import Client, REQUESTS, authorize, expect
from m0_registry import (ACCEPT, IMAGE, ORG, OCI_MANIFEST, SOURCE_BYTES, body_json, challenge, create_pat,
                         fixture, json_bytes, location, mint, put_manifest, read_blob, read_manifest,
                         remember, sha, start_upload, upload_blob)
from m0_oci_client import real_client_checks
from m0_response_loss import FAULT_ORIGIN, ResponseLoss

ROOT = '/v2/' + IMAGE


def team(client, owner, name, units, *, ident=None):
    path = '/api/v1/orgs/' + ORG + '/teams' if ident is None else '/api/v1/teams/' + str(ident)
    row = expect(client.request('POST' if ident is None else 'PATCH', path, basic=owner,
                                payload={'name': name, 'permission': 'read', 'units_map': units,
                                         'includes_all_repositories': False, 'can_create_org_repo': False}),
                 {201} if ident is None else {200}, 'set exact team unit permissions')
    value = expect(client.request('GET', '/api/v1/teams/' + str(row['id']), basic=owner), {200}, 'team permissions readback')
    if value.get('name') != name or value.get('units_map') != units or value.get('permission') not in ('read', 'none'):
        raise RuntimeError('Team fixture did not preserve exact intended unit permissions')
    return value


def organization_fixture(client, users, record):
    alice = users['alice']
    org = expect(client.request('POST', '/api/v1/orgs', basic=alice,
                                payload={'username': ORG, 'full_name': 'M0 isolated private OCI', 'visibility': 'private'}), {201}, 'create private task organization')
    value = expect(client.request('GET', '/api/v1/orgs/' + ORG, basic=alice), {200}, 'private organization readback')
    if org.get('username') != ORG or value.get('visibility') != 'private':
        raise RuntimeError('Organization fixture is not private')
    repo = expect(client.request('POST', '/api/v1/orgs/' + ORG + '/repos', basic=alice,
                                 payload={'name': 'm0-private-source', 'private': True, 'auto_init': True}), {201}, 'private organization source repository')
    path = '/api/v1/repos/' + ORG + '/' + repo['name']
    changed = expect(client.request('POST', path + '/contents/m0-source.txt', basic=alice,
                                    payload={'content': base64.b64encode(SOURCE_BYTES).decode(), 'message': 'test: pin isolated OCI source'}), {201}, 'OCI source commit')
    source_sha = changed['commit']['sha']
    code = team(client, alice, 'm0-code-only', {'repo.code': 'read'})
    writer = team(client, alice, 'm0-package-writer', {'repo.packages': 'write'})
    for value, username in [(code, 'carol'), (writer, 'bob')]:
        expect(client.request('PUT', '/api/v1/teams/' + str(value['id']) + '/members/' + username, basic=alice), {204}, 'add ordinary team member')
        expect(client.request('GET', '/api/v1/teams/' + str(value['id']) + '/members/' + username, basic=alice), {200}, 'team membership readback')
    expect(client.request('PUT', '/api/v1/teams/' + str(code['id']) + '/repos/' + ORG + '/' + repo['name'], basic=alice), {204}, 'code-only repository association')
    expect(client.request('PUT', path + '/collaborators/dave', basic=alice, payload={'permission': 'read'}), {204}, 'external repository collaborator')
    expect(client.request('GET', '/api/v1/orgs/' + ORG + '/members/dave', basic=alice), {404}, 'repository collaborator is not an org member')
    if expect(client.request('GET', path, basic=users['dave']), {200}, 'external collaborator repository read')['id'] != repo['id']:
        raise RuntimeError('External repository collaborator fixture differs')
    record('private_organization_teams_and_source_fixture', organization_id=org['id'], repository_id=repo['id'],
           source_sha=source_sha, package_team_units=writer['units_map'], code_team_units=code['units_map'],
           outsider_repository_read_status=200, outsider_org_membership_status=404)
    return source_sha, writer, repo


def oci_checks(owner, client, credentials, regctl, record):
    users = credentials['forge']; alice = users['alice']
    source, writer_team, repo = organization_fixture(client, users, record)
    receipt = challenge(client)
    pats = {name: create_pat(client, users[user], purpose, 'm0-oci-' + name) for name, user, purpose in (
        ('owner_write', 'alice', 'write'), ('owner_read', 'alice', 'read'), ('writer', 'bob', 'write'),
        ('reader', 'bob', 'read'), ('code_member', 'carol', 'write'), ('outsider', 'dave', 'read'))}
    tokens, meta = {}, {}
    for key, pat in pats.items():
        tokens[key], meta[key] = mint(client, pat)
    remember({'pats': pats, 'registry_tokens': tokens})
    record('registry_challenge_scoped_pat_exchange_and_declared_lifetime', challenge=receipt,
           purposes={k:pat['scopes'] for k, pat in pats.items()}, receipts=meta,
           expiry_wait_executed=False, authentication='ordinary scoped PAT in Basic exchange, Registry Bearer for data')
    config, layer, manifest = fixture(source, 'm0-main')
    for data, chunked in [(config, False), (layer, True)]:
        digest = upload_blob(client, tokens['writer'], data, chunked=chunked)
        head = expect(client.request('HEAD', ROOT + '/blobs/' + digest, token=tokens['reader'], binary=True), {200}, 'blob HEAD by Digest')
        if head.headers.get('Docker-Content-Digest') != digest:
            raise RuntimeError('HEAD blob did not confirm its Digest')
        read_blob(client, tokens['reader'], digest, expected=data)
    main_digest = put_manifest(client, tokens['writer'], 'm0-current', manifest)
    for candidate in ('owner_write', 'owner_read', 'writer', 'reader'):
        read_manifest(client, tokens[candidate], main_digest, expected=manifest)
    record('oci_blob_chunk_range_manifest_and_fixed_digest_pull', manifest_digest=main_digest,
           config_digest=sha(config), layer_digest=sha(layer), source_sha=source,
           raw_manifest_bytes=len(manifest), raw_layer_bytes=len(layer))
    for key in ('owner_read', 'reader'):
        expect(client.request('POST', ROOT + '/blobs/uploads/', token=tokens[key], raw=b'', binary=True), {401, 403}, 'read PAT cannot upload even with writer/owner role')
    for key in ('outsider', None):
        token = tokens[key] if key else None
        for path in (ROOT + '/manifests/' + main_digest, ROOT + '/blobs/' + sha(layer)):
            expect(client.request('GET', path, token=token, binary=True, headers=ACCEPT), {401, 403, 404}, 'private organization direct pull denied')
    # Organization membership is a separate possible read baseline; repo.packages:none is not assumed to revoke membership.
    member = client.request('GET', ROOT + '/manifests/' + main_digest, token=tokens['code_member'], binary=True, headers=ACCEPT)
    expect(member, {200, 401, 403, 404}, 'observe code-only organization member read policy')
    if member[0] == 200:
        read_manifest(client, tokens['code_member'], main_digest, expected=manifest)
    expect(client.request('POST', ROOT + '/blobs/uploads/', token=tokens['code_member'], raw=b'', binary=True), {401, 403}, 'code-only team cannot write package')
    record('private_org_pat_role_and_outsider_direct_pull_boundaries', readonly_upload_denied=True,
           code_member_pull_status=member[0], code_member_package_unit='none', code_member_upload_denied=True,
           repository_collaborator_pull_denied=True, anonymous_pull_denied=True)
    # A package link is not an ACL. The outsider retains repository read permission throughout.
    encoded = IMAGE.split('/', 1)[1]
    expect(client.request('POST', '/api/v1/packages/' + ORG + '/container/' + encoded + '/-/link/' + repo['name'], basic=alice), {201}, 'associate package with private repository')
    package = expect(client.request('GET', '/api/v1/packages/' + ORG + '/container/' + encoded + '/m0-current', basic=alice), {200}, 'linked package readback')
    if package.get('repository', {}).get('id') != repo['id']:
        raise RuntimeError('Package repository link differs')
    expect(client.request('GET', ROOT + '/manifests/' + main_digest, token=tokens['outsider'], binary=True, headers=ACCEPT), {401, 403, 404}, 'private repository link must not grant package access')
    record('private_repository_link_does_not_grant_package_access', linked_repository_id=repo['id'])
    # Private/public package-owner boundaries are independent from linked repository privacy.
    personal = IMAGE.replace(ORG, 'alice', 1)
    upload_blob(client, tokens['owner_write'], config, image=personal)
    upload_blob(client, tokens['owner_write'], layer, image=personal)
    public_digest = put_manifest(client, tokens['owner_write'], 'm0-personal', manifest, image=personal)
    expect(client.request('POST', '/api/v1/packages/alice/container/m0-probe/-/link/private-fixture', basic=alice), {201}, 'personal package private repository association')
    personal_result = client.request('GET', '/v2/' + personal + '/manifests/' + public_digest,
                                     token=tokens['outsider'], binary=True, headers=ACCEPT)
    expect(personal_result, {200, 401, 403, 404}, 'observe owner visibility independent from linked private repo')
    if personal_result[0] == 200:
        read_manifest(client, tokens['outsider'], public_digest, image=personal, expected=manifest)
    account = expect(client.request('GET', '/api/v1/user', basic=alice), {200}, 'personal package owner visibility readback')
    record('public_personal_owner_linked_private_repo_does_not_define_package_privacy',
           'gap' if personal_result[0] == 200 else 'pass', other_user_pull_status=personal_result[0],
           link_is_not_acl=True, owner_visibility=account.get('visibility'), linked_repository_private=True)
    # A pull-only Registry query cannot be relied on as a scope restriction when the PAT is write-capable.
    pull_token, pull_meta = mint(client, pats['owner_write'], actions='pull')
    remember({'pats': pats, 'registry_tokens': dict(tokens, pull_requested=pull_token)})
    scope_result = client.request('POST', ROOT + '/blobs/uploads/', token=pull_token, raw=b'', binary=True)
    expect(scope_result, {202, 401, 403}, 'observe requested pull-only Registry action boundary')
    if scope_result[0] == 202:
        delete_upload(client, tokens['owner_write'], location(scope_result[2]))
    record('registry_requested_pull_action_is_not_a_pat_scope_reduction', 'gap' if scope_result[0] == 202 else 'pass',
           requested_actions='pull', actual_pat_scope=pull_meta['scope'], upload_status=scope_result[0])
    # Wrong resource purpose remains rejected, including a valid OAuth resource token.
    _, release_grant, _, _ = authorize('release_write', client, alice, 'm0-oci-wrong-oauth-purpose')
    expect(client.request('GET', '/v2/token', token=release_grant['access_token'], binary=True), {401, 403}, 'ordinary OAuth Bearer is not a Registry Token')
    wrong = expect(client.request('POST', '/api/v1/users/alice/tokens', basic=alice,
                                  payload={'name': 'm0-wrong-repo-scope', 'scopes': ['read:repository']}), {201}, 'wrong-purpose PAT fixture')
    expect(client.request('GET', '/v2/token', basic=('alice', wrong['sha1']), binary=True), {401, 403}, 'repository PAT cannot exchange for package Token')
    record('oauth_bearer_and_non_package_pat_do_not_authorize_registry')
    real_client_checks(owner, client, regctl, pats['owner_write'], tokens['owner_write'], source, record)
    tag_changes(client, tokens['owner_write'], source, manifest, main_digest, record)
    denied_and_deleted(client, tokens['owner_write'], config, manifest, record)
    revocation_checks(client, users, writer_team, pats, tokens, main_digest, manifest, record)
    # Real fault scenarios use a healthy owner and exactly one transport attempt each.
    for forward in (True, False):
        fault_start(client, tokens['owner_write'], forward, record)
        fault_chunk(client, tokens['owner_write'], forward, record)
        fault_commit(client, tokens['owner_write'], forward, record)
        fault_manifest(client, tokens['owner_write'], source, forward, record)
    fault_commit(client, tokens['owner_write'], True, record, partial=True)
    record('oci_slice_has_no_workflow_run_or_product_publication', runner_run_id=None, product_acceptance=False)


def delete_upload(client, token, path):
    expect(client.request('DELETE', location(path), token=token, binary=True), {204}, 'delete owned known upload')


def tag_changes(client, token, source, manifest, digest, record):
    _, _, original_manifest = fixture(source, 'm0-retention-original')
    original_digest = put_manifest(client, token, 'm0-moving', original_manifest)
    _, _, other = fixture(source, 'm0-moved-tag')
    newer = put_manifest(client, token, 'm0-moving', other)
    if original_digest == newer:
        raise RuntimeError('Tag movement fixture did not create a different manifest Digest')
    actual, _, _ = read_manifest(client, token, 'm0-moving', expected=other)
    if actual != newer:
        raise RuntimeError('Moved Tag content differs from its new Digest')
    old = client.request('GET', ROOT + '/manifests/' + original_digest, token=token, binary=True, headers=ACCEPT)
    expect(old, {200, 404}, 'observe untagged original manifest retention')
    if old[0] == 200:
        read_manifest(client, token, original_digest, expected=original_manifest)
    # Keep the main permission fixture intact; a missing object cannot prove that an ACL denied access.
    read_manifest(client, token, digest, expected=manifest)
    record('overwriting_last_tag_original_digest_retention', 'gap' if old[0] == 404 else 'pass',
           original_digest=original_digest, original_digest_status=old[0], moved_tag_digest=newer,
           permission_fixture_digest=digest, missing_digest_never_resolved_through_latest=True)


def denied_and_deleted(client, token, config, manifest, record):
    path = start_upload(client, token)
    bad = client.request('PUT', path + '?digest=sha256:' + '0' * 64, token=token, raw=config, binary=True)
    expect(bad, {400}, 'incorrect blob Digest rejected')
    expect(client.request('HEAD', ROOT + '/blobs/sha256:' + '0' * 64, token=token, binary=True), {404}, 'incorrect Digest was not committed')
    status = client.request('GET', path, token=token, binary=True)[0]
    if status == 204:
        delete_upload(client, token, path)
    elif status != 404:
        raise RuntimeError('Failed upload has an unrecognized query state')
    missing = json.loads(manifest);missing['config']['digest'] = 'sha256:' + 'f' * 64
    invalid = client.request('PUT', ROOT + '/manifests/m0-missing-blob', token=token, raw=json_bytes(missing), content_type=OCI_MANIFEST, binary=True)
    expect(invalid, {400, 404}, 'manifest referencing missing blob rejected')
    expect(client.request('GET', ROOT + '/manifests/m0-missing-blob', token=token, binary=True, headers=ACCEPT), {404}, 'invalid manifest was not published')
    disposable = dict(json.loads(manifest));disposable['annotations']['io.radishforge.m0.marker'] = 'm0-delete'
    digest = put_manifest(client, token, 'm0-delete', json_bytes(disposable))
    expect(client.request('DELETE', ROOT + '/manifests/' + digest, token=token, binary=True), {202}, 'delete owned manifest Digest')
    expect(client.request('GET', ROOT + '/manifests/' + digest, token=token, binary=True, headers=ACCEPT), {404}, 'deleted manifest Digest')
    expect(client.request('GET', ROOT + '/manifests/m0-delete', token=token, binary=True, headers=ACCEPT), {404}, 'deleted manifest tag')
    path = start_upload(client, token);delete_upload(client, token, path)
    expect(client.request('GET', path, token=token, binary=True), {404}, 'deleted upload state')
    record('invalid_blob_manifest_and_deleted_registry_resources', wrong_digest_status=bad[0], missing_blob_manifest_status=invalid[0], manifest_delete_status=202)


def revocation_checks(client, users, writer, pats, tokens, digest, manifest, record):
    alice = users['alice']
    team(client, alice, writer['name'], {'repo.packages': 'read'}, ident=writer['id'])
    expect(client.request('POST', ROOT + '/blobs/uploads/', token=tokens['writer'], raw=b'', binary=True), {401, 403}, 'cached Registry Token must respect team write revocation')
    read_manifest(client, tokens['writer'], digest, expected=manifest)
    expect(client.request('DELETE', '/api/v1/orgs/' + ORG + '/members/bob', basic=alice), {204}, 'revoke organization membership')
    expect(client.request('GET', '/api/v1/orgs/' + ORG + '/members/bob', basic=alice), {404}, 'revoked org membership readback')
    expect(client.request('GET', ROOT + '/manifests/' + digest, token=tokens['writer'], binary=True, headers=ACCEPT), {401, 403, 404}, 'cached Token after private organization revocation')
    fresh, _ = mint(client, pats['writer'])
    expect(client.request('GET', ROOT + '/manifests/' + digest, token=fresh, binary=True, headers=ACCEPT), {401, 403, 404}, 'fresh Token after organization revocation')
    record('cached_registry_token_respects_team_downgrade_and_org_revocation', write_after_downgrade_denied=True,
           read_before_org_removal=True, cached_and_fresh_after_org_removal_denied=True)
    ephemeral = create_pat(client, alice, 'write', 'm0-pat-revocation')
    cached, metadata = mint(client, ephemeral)
    remember({'pats': dict(pats, revoked=ephemeral), 'registry_tokens': dict(tokens, revoked_pat_cached=cached)})
    read_manifest(client, cached, digest, expected=manifest)
    expect(client.request('DELETE', '/api/v1/users/alice/tokens/' + str(ephemeral['id']), basic=alice), {204}, 'delete one ordinary user PAT')
    fresh_result = client.request('GET', '/v2/token', basic=('alice', ephemeral['value']), binary=True)
    expect(fresh_result, {401, 403}, 'deleted PAT exchange refused')
    cached_read = client.request('GET', ROOT + '/manifests/' + digest, token=cached, binary=True, headers=ACCEPT)
    expect(cached_read, {200, 401, 403, 404}, 'observe old Registry Token after parent PAT deletion')
    cached_write = client.request('POST', ROOT + '/blobs/uploads/', token=cached, raw=b'', binary=True)
    expect(cached_write, {202, 401, 403}, 'observe cached Registry write after parent PAT deletion')
    if cached_write[0] == 202:
        delete_upload(client, tokens['owner_write'], location(cached_write[2]))
    record('deleted_pat_does_not_imply_cached_registry_token_revoked',
           'gap' if cached_read[0] == 200 or cached_write[0] == 202 else 'pass',
           new_exchange_status=fresh_result[0], cached_read_status=cached_read[0], cached_write_status=cached_write[0],
           declared_lifetime_seconds=metadata['declared_lifetime_seconds'], expiry_wait_executed=False)
    # Admin is used only to change the synthetic account control, never for package access.
    expect(client.request('PATCH', '/api/v1/admin/users/carol', basic=users['admin'], payload={'login_name': 'carol', 'prohibit_login': True}), {200}, 'disable synthetic account')
    disabled = client.request('GET', ROOT + '/manifests/' + digest, token=tokens['code_member'], binary=True, headers=ACCEPT)
    expect(disabled, {401, 403, 404}, 'cached Registry token of disabled account')
    expect(client.request('PATCH', '/api/v1/admin/users/carol', basic=users['admin'], payload={'login_name': 'carol', 'prohibit_login': False}), {200}, 'restore synthetic account')
    record('disabled_account_cached_registry_resource_denied', resource_status=disabled[0])


def fault(client, token, operation, path, data, forward, *, partial=None):
    with ResponseLoss(operation, path, token, data, forward=forward, partial_bytes=partial) as inject:
        try:
            Client(FAULT_ORIGIN).request(inject.method, path, token=token, raw=data,
                                        content_type=inject.content_type, binary=True, timeout=1)
        except OSError as error:
            error_type = type(error).__name__
        else:
            raise RuntimeError('OCI response-loss caller did not time out')
    if inject.error_type or inject.attempts != 1 or inject.forwarded != int(forward):
        raise RuntimeError('OCI fault transport differs from its bounded scenario')
    return {'caller_error': error_type, 'request_attempts': inject.attempts, 'upstream_writes': inject.forwarded,
            'upstream_status': inject.upstream_status, 'upstream_body_bytes': inject.sent_bytes,
            'automatic_retries': 0, 'fault_listener_stopped': True}


def reads_only(start):
    if any(r['method'] not in ('GET', 'HEAD') for r in REQUESTS[start:]):
        raise RuntimeError('OCI reconciliation wrote upstream')


def fault_start(client, token, forward, record):
    known_digest = sha(b'M0 intended upload content ' + secrets.token_bytes(8))
    info = fault(client, token, 'oci_start', ROOT + '/blobs/uploads/', b'', forward)
    if forward and info['upstream_status'] != 202:
        raise RuntimeError('Upload-start response loss did not start an upstream upload')
    start = len(REQUESTS)
    expect(client.request('HEAD', ROOT + '/blobs/' + known_digest, token=token, binary=True), {404}, 'unknown upload is not a complete blob')
    reads_only(start)
    record('oci_upload_start_response_loss_' + ('forwarded' if forward else 'not_forwarded'), **info,
           reconciliation={'state': 'unknown', 'caller_received_location': False,
                           'intended_blob_digest': known_digest, 'complete_blob_visible': False})


def fault_chunk(client, token, forward, record):
    path = start_upload(client, token)
    data = b'M0 bounded chunk ' + secrets.token_bytes(64)
    info = fault(client, token, 'oci_chunk', path, data, forward)
    if forward and info['upstream_status'] != 202:
        raise RuntimeError('Chunk response loss did not append upstream')
    start = len(REQUESTS)
    current = expect(client.request('GET', path, token=token, binary=True), {204}, 'read known upload after chunk timeout')
    actual_range = current.headers.get('Range')
    observed = actual_range == '0-' + str(len(data) - 1)
    if observed != forward:
        raise RuntimeError('Chunk reconciliation Range differs from its bounded prefix')
    reads_only(start)
    record('oci_chunk_response_loss_' + ('committed' if forward else 'not_forwarded'), **info,
           reconciliation={'state': 'observed' if observed else 'unknown', 'range': actual_range, 'only_prefix_confirmed': True})
    delete_upload(client, token, path)  # Explicit fixture cleanup after reconciliation, never automatic recovery.


def fault_commit(client, token, forward, record, *, partial=False):
    path = start_upload(client, token)
    data = b'M0 exact complete blob ' + secrets.token_bytes(512)
    digest = sha(data)
    info = fault(client, token, 'oci_blob_commit', path + '?digest=' + digest, data, forward,
                 partial=len(data) // 2 if partial else None)
    if forward and not partial and info['upstream_status'] != 201:
        raise RuntimeError('Blob commit response loss did not complete upstream')
    start = len(REQUESTS)
    result = client.request('HEAD', ROOT + '/blobs/' + digest, token=token, binary=True)
    expect(result, {200, 404}, 'query full blob after unknown commit')
    observed = result[0] == 200
    if observed:
        read_blob(client, token, digest, expected=data)
    status = client.request('GET', path, token=token, binary=True)
    expect(status, {204, 404}, 'query original upload after unknown commit')
    reads_only(start)
    if observed != (forward and not partial):
        raise RuntimeError('Blob timeout reconciliation differs from exact expected bytes')
    record('oci_blob_partial_disconnect' if partial else 'oci_blob_commit_response_loss_' + ('committed' if forward else 'not_forwarded'),
           **info, reconciliation={'state': 'observed' if observed else 'unknown', 'digest': digest,
                                    'upload_status': status[0], 'range': status[1].headers.get('Range')})
    if status[0] == 204:
        delete_upload(client, token, path)


def fault_manifest(client, token, source, forward, record):
    tag = 'm0-timeout-' + secrets.token_hex(6)
    _, _, raw = fixture(source, tag)
    digest = sha(raw)
    info = fault(client, token, 'oci_manifest', ROOT + '/manifests/' + tag, raw, forward)
    if forward and info['upstream_status'] != 201:
        raise RuntimeError('Manifest response loss did not publish upstream')
    start = len(REQUESTS)
    result = client.request('GET', ROOT + '/manifests/' + tag, token=token, binary=True, headers=ACCEPT)
    expect(result, {200, 404}, 'query exact manifest tag after timeout')
    observed = result[0] == 200
    if observed:
        read_manifest(client, token, digest, expected=raw)
        read_manifest(client, token, tag, expected=raw)
    else:
        expect(client.request('GET', ROOT + '/manifests/' + digest, token=token, binary=True, headers=ACCEPT), {404}, 'no full Digest visible after unforwarded request')
    reads_only(start)
    if observed != forward:
        raise RuntimeError('Manifest reconciliation differs from exact serialized bytes')
    record('oci_manifest_response_loss_' + ('committed' if forward else 'not_forwarded'), **info,
           reconciliation={'state': 'observed' if observed else 'unknown', 'digest': digest})
