#!/usr/bin/env python3
"""Real local Gitea protocol probes. No app implementation or third-party packages."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import re
import secrets
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

from m0_local import RUNTIME, command, compose, state, write_private
from m0_scope import PROFILE_PATH, ProfileError, load_contract, scope_for
from m0_oauth import (CALLBACK, REQUESTS, AuthorizationRejected, GrantRejected, Client,
                     expect, issue_code, exchange, jwt_claims, register, receipt, authorize, refresh, introspect)


def profile_checks(owner, forge, idp, credentials, record):
    contract = load_contract()
    alice, bob = credentials['forge']['alice'], credentials['forge']['bob']
    idp_alice = credentials['idp']['alice']
    path = '/api/v1/repos/alice/private-fixture'

    rejected = []
    cases = [
        ('default_oidc', 'identity', idp, 'openid email profile'),
        ('unknown_scope', 'identity', idp, 'openid m0-unknown-scope'),
        ('all_scope', 'identity', idp, 'all'),
        ('missing_public_only', 'identity', idp, scope_for('identity').replace('public-only ', '')),
        ('admin_scope', 'identity', idp, scope_for('identity') + ' read:admin'),
        ('read_to_write', 'resource_read', forge, scope_for('issue_write')),
        ('wrong_issuer', 'identity', forge, None),
        ('empty_scope', 'identity', idp, ''),
    ]
    before = len(REQUESTS)
    for name, purpose, client, requested in cases:
        try:
            register(purpose, client, idp_alice, 'must-not-register', requested)
        except ProfileError:
            rejected.append(name)
        else:
            raise RuntimeError('An unapproved authorization request reached registration')
    if len(REQUESTS) != before:
        raise RuntimeError('Rejected scope combinations caused a network request')
    record('scope_guard_rejects_before_network', rejected=rejected, network_requests=0)

    identity_app, identity, identity_claims, _ = authorize('identity', idp, idp_alice, 'm0-profile-identity')
    expect(idp.request('POST', '/api/v1/user/repos', basic=idp_alice,
                       payload={'name': 'identity-private-fixture', 'private': True, 'auto_init': True}),
           {201}, 'identity negative fixture')
    identity_path = '/api/v1/repos/alice/identity-private-fixture'
    expect(idp.request('GET', identity_path, token=identity['access_token']), {403}, 'identity private read')
    expect(idp.request('POST', identity_path + '/issues', token=identity['access_token'],
                       payload={'title': 'must be rejected'}), {403}, 'identity private write')
    expect(forge.request('GET', path, token=identity['access_token']), {401}, 'foreign issuer resource token')
    record('identity_profile_userinfo_without_private_access', scopes=scope_for('identity'),
           issuer=identity_claims['iss'], userinfo_status=200, private_status=403)

    read_app, read_tokens, _, read_browser = authorize('resource_read', forge, alice, 'm0-profile-read')
    write_app, write_tokens, _, write_browser = authorize('issue_write', forge, alice, 'm0-profile-write')
    if len({identity_app['client_id'], read_app['client_id'], write_app['client_id']}) != 3:
        raise RuntimeError('Identity and resource client registrations were not separated')
    record('separate_confidential_clients_and_exact_granted_scopes', profiles=['identity', 'resource_read', 'issue_write'])
    expect(forge.request('GET', path, token=read_tokens['access_token']), {200}, 'resource read')
    expect(forge.request('POST', path + '/issues', token=read_tokens['access_token'],
                         payload={'title': 'must be rejected'}), {403}, 'read profile write')
    issue = expect(forge.request('POST', path + '/issues', token=write_tokens['access_token'],
                                payload={'title': 'M0 profile issue'}), {201}, 'write profile issue')
    expect(forge.request('POST', '/api/v1/user/repos', token=write_tokens['access_token'],
                         payload={'name': 'must-not-create'}), {403}, 'issue profile repository creation')
    record('read_and_issue_write_profiles_have_distinct_permissions', issue_number=issue['number'])

    deny_app, deny_scopes = register('resource_read', forge, alice, 'm0-profile-denied')
    before = len(REQUESTS)
    try:
        issue_code(Client(forge.base, browser_session=True), deny_app, alice, deny_scopes, approve=False)
    except AuthorizationRejected as exc:
        if exc.error != 'access_denied':
            raise RuntimeError('Consent denial returned a different OAuth error') from None
    else:
        raise RuntimeError('Denied consent still issued an authorization code')
    if any(r['path'].endswith('/access_token') for r in REQUESTS[before:]):
        raise RuntimeError('Denied authorization was exchanged for a token')
    record('consent_denial_returns_no_code_or_token')

    code, verifier, _ = issue_code(write_browser, write_app, alice, scope_for('issue_write'))
    expect(exchange(forge, write_app, code, verifier, client_secret='deliberately-wrong-fixture-secret'),
           {400, 401}, 'wrong confidential client secret')
    record('confidential_client_secret_required')
    invalid_redirect = read_browser.request('GET', '/login/oauth/authorize?' + urllib.parse.urlencode({
        'client_id': read_app['client_id'], 'response_type': 'code',
        'scope': scope_for('resource_read'), 'redirect_uri': CALLBACK + '/unregistered',
        'state': secrets.token_urlsafe(24)}))
    expect(invalid_redirect, {400}, 'unregistered callback')
    record('unregistered_redirect_rejected')

    # Replay a correctly signed refresh token against a different valid client.
    cross = forge.request('POST', '/login/oauth/access_token', form={
        'grant_type': 'refresh_token', 'client_id': write_app['client_id'],
        'client_secret': write_app['client_secret'], 'refresh_token': read_tokens['refresh_token']})
    expect(cross, {400, 401}, 'cross-client refresh token')
    record('refresh_token_bound_to_client')
    before = len(REQUESTS)
    try:
        refresh('resource_read', forge, read_app, read_tokens['refresh_token'], requested='all')
    except ProfileError:
        pass
    else:
        raise RuntimeError('Refresh request accepted scope widening')
    if len(REQUESTS) != before:
        raise RuntimeError('Rejected refresh scope reached the server')
    record('refresh_scope_widening_rejected_before_network')

    renewed = expect(refresh('resource_read', forge, read_app, read_tokens['refresh_token']),
                     {200}, 'read profile refresh')
    receipt('resource_read', forge, read_app, renewed)
    if renewed['refresh_token'] == read_tokens['refresh_token']:
        raise RuntimeError('Refresh token did not rotate with invalidation enabled')
    expect(refresh('resource_read', forge, read_app, read_tokens['refresh_token']), {400, 401}, 'refresh replay')
    expect(forge.request('GET', path, token=renewed['access_token']), {200}, 'refreshed private read')
    expect(forge.request('POST', path + '/issues', token=renewed['access_token'],
                         payload={'title': 'must be rejected after refresh'}), {403}, 'refreshed read-only write')
    record('refresh_rotation_replay_rejection_and_scope_preservation')

    bob_app, bob_tokens, _, _ = authorize('issue_write', forge, bob, 'm0-profile-bob')
    expect(forge.request('GET', path, token=bob_tokens['access_token']), {403, 404}, 'cross-user private read')
    expect(forge.request('PUT', path + '/collaborators/bob', basic=alice, payload={'permission': 'write'}),
           {204}, 'grant collaborator')
    expect(forge.request('GET', path, token=bob_tokens['access_token']), {200}, 'granted collaborator read')
    expect(forge.request('DELETE', path + '/collaborators/bob', basic=alice), {204}, 'revoke collaborator')
    after_revoke = expect(refresh('issue_write', forge, bob_app, bob_tokens['refresh_token']),
                          {200}, 'refresh after resource permission revocation')
    expect(forge.request('GET', path, token=after_revoke['access_token']), {403, 404}, 'refreshed revoked read')
    expect(forge.request('POST', path + '/issues', token=after_revoke['access_token'],
                         payload={'title': 'must be rejected after revoke'}), {403, 404}, 'refreshed revoked write')
    record('refresh_does_not_restore_revoked_repository_permission')

    expect(forge.request('DELETE', f'/api/v1/user/applications/oauth2/{write_app["id"]}', basic=alice),
           {204}, 'delete resource OAuth client')
    expect(forge.request('GET', path, token=write_tokens['access_token']), {401}, 'deleted-client access token')
    expect(refresh('issue_write', forge, write_app, write_tokens['refresh_token']),
           {400, 401}, 'deleted-client refresh token')
    expect(idp.request('GET', '/login/oauth/userinfo', token=identity['access_token']), {200}, 'independent identity grant')
    record('deleted_resource_client_invalidates_access_and_refresh_without_identity_logout')

    expect(forge.request('POST', '/api/v1/user/repos', basic=bob,
                         payload={'name': 'bob-private-fixture', 'private': True, 'auto_init': True}),
           {201}, 'disabled-user fixture')
    bob_path = '/api/v1/repos/bob/bob-private-fixture'
    expect(forge.request('GET', bob_path, token=after_revoke['access_token']), {200}, 'active user own resource')
    expect(forge.request('PATCH', '/api/v1/admin/users/bob', basic=credentials['forge']['admin'],
                         payload={'prohibit_login': True}), {200}, 'disable fixture user')
    disabled_status = forge.request('GET', bob_path, token=after_revoke['access_token'])[0]
    if disabled_status not in (401, 403):
        raise RuntimeError(f'Disabled user access was not rejected: HTTP {disabled_status}')
    disabled_refresh = refresh('issue_write', forge, bob_app, after_revoke['refresh_token'])
    if disabled_refresh[0] == 200:
        disabled_tokens = disabled_refresh[1]
        expect(forge.request('GET', bob_path, token=disabled_tokens['access_token']), {401, 403}, 'disabled refreshed access')
        disabled_inspection = introspect(forge, bob_app, disabled_tokens['access_token'])
        try:
            receipt('issue_write', forge, bob_app, disabled_tokens)
        except GrantRejected as exc:
            local_status = exc.status
            local_reason = exc.reason
            metadata_type = exc.metadata_type
        else:
            raise RuntimeError('Local profile gate accepted a disabled account after refresh')
        record('disabled_user_refresh', 'gap', refresh_status=200,
               resource_status=disabled_status,
               local_receipt_rejected=True, local_rejection_http_status=local_status,
               local_rejection_reason=local_reason,
               introspection_metadata_type=metadata_type,
               introspection_status=disabled_inspection[0],
               introspection_active=(disabled_inspection[1].get('active')
                                     if isinstance(disabled_inspection[1], dict) else None),
               detail='Upstream refresh still issues a token; online credential verification rejects it locally')
        record('disabled_account_not_accepted_after_refresh', http_status=local_status, reason=local_reason)
    else:
        expect(disabled_refresh, {400, 401, 403}, 'disabled user refresh')
        record('disabled_user_access_and_refresh_rejected', access_status=disabled_status,
               refresh_status=disabled_refresh[0])

    expiry_app, expiry_tokens, _, _ = authorize('resource_read', forge, alice, 'm0-profile-expiry')
    receipt('resource_read', forge, expiry_app, expiry_tokens)
    deadline = time.monotonic() + expiry_tokens['expires_in'] + 1
    record('waiting_for_real_access_token_expiry', lifetime_seconds=expiry_tokens['expires_in'])
    while time.monotonic() <= deadline:
        time.sleep(min(1, max(0.01, deadline - time.monotonic())))
    expect(forge.request('GET', path, token=expiry_tokens['access_token']), {401}, 'expired access token')
    expired_inspection = forge.request('POST', '/login/oauth/introspect',
                                      basic=(expiry_app['client_id'], expiry_app['client_secret']),
                                      form={'token': expiry_tokens['access_token']})
    if expired_inspection[0] == 200:
        if expired_inspection[1].get('active') is not False:
            raise RuntimeError('Expired access token still introspects active')
    elif expired_inspection[0] != 401:
        raise RuntimeError(f'Unexpected expired-token introspection HTTP {expired_inspection[0]}')
    after_expiry = expect(refresh('resource_read', forge, expiry_app, expiry_tokens['refresh_token']),
                          {200}, 'refresh after access expiry')
    receipt('resource_read', forge, expiry_app, after_expiry)
    if expired_inspection[0] == 401:
        # Same client credentials work for the new token; retain the old token's protocol difference.
        record('expired_token_introspection', 'gap', expired_status=401, fresh_status=200,
               fresh_active=True, detail='Expired token gets 401 instead of 200 inactive metadata; not a client-auth failure')
    expect(forge.request('GET', path, token=after_expiry['access_token']), {200}, 'renewed read after expiry')
    expect(forge.request('POST', path + '/issues', token=after_expiry['access_token'],
                         payload={'title': 'must be rejected'}), {403}, 'renewed read-only boundary')
    record('real_access_expiry_and_scoped_refresh')


def main(mode, regctl=None):
    if mode == 'oci':
        from m0_oci_client import client_path
        if regctl is None:
            raise RuntimeError('OCI mode requires the pinned task-local --regctl binary')
        client_path(regctl)
    owner = state()
    if mode != 'discovery' and (not owner.get('auth_profile') or
                              owner.get('auth_profile_sha256') != hashlib.sha256(PROFILE_PATH.read_bytes()).hexdigest()):
        raise RuntimeError('Prepare a fresh environment with --auth-profile matching the reviewed contract')
    if mode == 'lifecycle-baseline' and not owner.get('legacy_query_auth'):
        raise RuntimeError('Historical diagnosis requires a fresh --legacy-query-auth environment')
    if mode in ('profiles', 'lifecycle', 'issues', 'releases', 'oci') and owner.get('legacy_query_auth'):
        raise RuntimeError('Controlled probes refuse the historical form-token authentication setting')
    marker = RUNTIME / 'contract-started.json'
    if marker.exists():
        raise RuntimeError('Probe already started; reconcile prior writes before a new run')
    write_private(marker, json.dumps({'project': owner['project'], 'started': True}))
    results = []
    report = {'project': owner['project'], 'platform': 'linux/arm64', 'context': owner['context'],
              'runner_started': False, 'system_trust_changed': False, 'results': results,
              'requests': REQUESTS, 'mode': mode,
              'http_transport': 'stateless API credentials; isolated browser cookie jars for login/consent only'}
    report['started_at_utc'] = datetime.now(timezone.utc).isoformat()
    report['repository_head'] = command(['git', '-C', str(RUNTIME.parent.parent), 'rev-parse', 'HEAD']).stdout.decode().strip()
    report['source_sha256'] = {name: hashlib.sha256((RUNTIME.parent.parent / name).read_bytes()).hexdigest()
                               for name in ('scripts/m0_contracts.py', 'scripts/m0_oauth.py',
                                            'scripts/m0_lifecycle.py', 'scripts/m0_local.py',
                                            'scripts/m0_scope.py', 'scripts/m0_issues.py', 'scripts/m0_response_loss.py',
                                            'scripts/m0_releases.py',
                                            'scripts/m0_registry.py', 'scripts/m0_oci.py', 'scripts/m0_oci_client.py',
                                            'tests/contracts/m0/gitea-registry-profile.json',
                                            'tests/contracts/m0/gitea-auth-profile.json',
                                            'tests/contracts/m0/compose.yaml')}
    report['effective_provider_settings'] = owner.get('effective_provider_settings')

    def record(name, status='pass', **details):
        results.append({'name': name, 'status': status, 'observed_at_utc': datetime.now(timezone.utc).isoformat(), **details})
        write_private(RUNTIME / 'results.json', json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(results[-1], ensure_ascii=False))

    def new_app(client, credentials, name):
        return expect(client.request('POST', '/api/v1/user/applications/oauth2', basic=credentials,
                                    payload={'name': name, 'redirect_uris': [CALLBACK],
                                             'confidential_client': False,
                                             'skip_secondary_authorization': False}), {201}, 'create public OAuth app')

    def grant(client, credentials, name, scopes, *, identity_only=False):
        app = new_app(client, credentials, name)
        browser = Client(client.base, browser_session=True)
        code, verifier, nonce = issue_code(browser, app, credentials, scopes)
        tokens = expect(exchange(client, app, code, verifier), {200}, 'authorization code + PKCE')
        claims = jwt_claims(client, tokens['id_token'], app, nonce)
        info_result = client.request('GET', '/login/oauth/userinfo', token=tokens['access_token'])
        if identity_only and info_result[0] != 200:
            record('identity_only_scope_userinfo', 'gap', http_status=info_result[0],
                   detail='Signed ID token succeeds; standard UserInfo is denied with openid public-only email profile')
        else:
            info = expect(info_result, {200}, 'OIDC UserInfo')
            if info.get('sub') != claims['sub']:
                raise RuntimeError('UserInfo subject differs from verified ID token subject')
            if 'email' in info:
                claims['email'] = info['email']
        return app, tokens, claims, code, verifier

    try:
        forge, idp = Client('https://localhost:18443'), Client('https://localhost:19443')
        # Deliberately untrusted CA must be rejected by the host's default TLS context.
        try:
            urllib.request.urlopen(forge.base + '/api/v1/version', timeout=5)
        except urllib.error.URLError as exc:
            if not isinstance(exc.reason, ssl.SSLCertVerificationError):
                raise RuntimeError('Unexpected failure in untrusted-CA test') from None
        else:
            raise RuntimeError('Transient CA was unexpectedly globally trusted')
        record('local_tls_requires_explicit_task_ca')
        credentials = {}
        for service, client in (('forge', forge), ('idp', idp)):
            raw = compose(owner, 'exec', '-T', service, 'gitea', '--config', '/etc/gitea/app.ini',
                          'admin', 'user', 'create', '--username', 'm0-admin', '--email',
                          f'admin-{service}@example.test', '--random-password',
                          '--random-password-length', '32', '--must-change-password=false', '--admin').stdout.decode()
            match = re.search(r"generated random password is '(.*)'", raw)
            if not match:
                raise RuntimeError('Could not capture generated bootstrap password; output withheld')
            admin = ('m0-admin', match.group(1))
            credentials[service] = {'admin': admin}
            users = (('alice', 'bob', 'carol', 'dave') if mode == 'oci' else
                     ('alice', 'bob', 'carol') if mode in ('issues', 'releases') else ('alice', 'bob'))
            for username in (users if service == 'forge' else ('alice',)):
                password = secrets.token_urlsafe(32)
                user = expect(client.request('POST', '/api/v1/admin/users', basic=admin, payload={
                    'username': username, 'email': f'{username}@example.test', 'password': password,
                    'must_change_password': False, 'send_notify': False}), {201}, 'create isolated user')
                if user.get('is_admin') is not False:
                    raise RuntimeError('Fixture user unexpectedly has admin privileges')
                credentials[service][username] = (username, password)
            write_private(RUNTIME / 'credentials.json', json.dumps(credentials))
        record('ordinary_users_and_independent_idp_created')
        alice, bob = credentials['forge']['alice'], credentials['forge']['bob']
        repo = expect(forge.request('POST', '/api/v1/user/repos', basic=alice,
                                    payload={'name': 'private-fixture', 'private': True, 'auto_init': True}),
                      {201}, 'ordinary user creates private repo')
        path = '/api/v1/repos/alice/private-fixture'
        record('ordinary_user_private_repository', repository_id=repo['id'])
        if mode == 'oci':
            from m0_oci import oci_checks
            oci_checks(owner, forge, credentials, regctl, record)
            report['completed'] = True
            report['passed_product_acceptance'] = False
            record('oci_probe_completed', scope='M0 OCI upstream and real client slice; Runner paused, no M1')
            return 2 if any(r['status'] == 'gap' for r in results) else 0
        if mode == 'releases':
            from m0_releases import release_checks
            release_checks(forge, credentials, record)
            report['completed'] = True
            report['passed_product_acceptance'] = False
            record('release_probe_completed', scope='M0 Release upstream contracts only; Runner paused, no OCI/M1')
            return 2 if any(r['status'] == 'gap' for r in results) else 0
        if mode == 'issues':
            from m0_issues import issue_checks
            issue_checks(owner, forge, credentials, record)
            report['completed'] = True
            report['passed_product_acceptance'] = False
            record('issue_probe_completed', scope='M0 Issue upstream contracts only; Runner paused, no workbench/M1')
            return 2 if any(r['status'] == 'gap' for r in results) else 0
        if mode in ('lifecycle', 'lifecycle-baseline'):
            from m0_lifecycle import lifecycle_checks
            lifecycle_checks(owner, forge, idp, credentials, record, baseline=mode.endswith('-baseline'))
            report['completed'] = True
            report['passed_product_acceptance'] = False
            report['upstream_scope_differences_fixed'] = False
            record('lifecycle_probe_completed', scope='M0 upstream lifecycle only; no product session or Runner')
            return 2 if any(r['status'] == 'gap' for r in results) else 0
        if mode == 'profiles':
            profile_checks(owner, forge, idp, credentials, record)
            report['completed'] = True
            report['passed_product_acceptance'] = False
            report['upstream_scope_differences_fixed'] = False
            record('controlled_profile_probe_completed',
                   scope='Reviewed client combinations only; original upstream scope differences remain')
            return 2 if any(r['status'] == 'gap' for r in results) else 0
        write_scope = 'openid email profile read:repository write:issue read:user'
        write_app, write_tokens, alice_claims, code, verifier = grant(forge, alice, 'm0-write', write_scope)
        record('oauth_pkce_rs256_and_claims', claims=alice_claims)
        expect(exchange(forge, write_app, code, verifier), {400, 401}, 'replayed authorization code')
        record('authorization_code_replay_rejected')
        bad_app = new_app(forge, alice, 'm0-bad-pkce')
        bad_code, _, _ = issue_code(Client(forge.base, browser_session=True), bad_app, alice, write_scope)
        expect(exchange(forge, bad_app, bad_code, secrets.token_urlsafe(48)), {400, 401}, 'wrong PKCE verifier')
        record('wrong_pkce_verifier_rejected')
        token = write_tokens['access_token']
        expect(forge.request('GET', path, token=token), {200}, 'owner private read')
        issue = expect(forge.request('POST', path + '/issues', token=token,
                                     payload={'title': 'M0 isolated issue', 'body': 'synthetic fixture'}),
                       {201}, 'owner issue creation')
        issue_path = path + '/issues/' + str(issue['number'])
        expect(forge.request('POST', issue_path + '/comments', token=token,
                             payload={'body': 'M0 synthetic comment'}), {201}, 'issue comment')
        expect(forge.request('PATCH', issue_path, token=token, payload={'state': 'closed'}), {201}, 'close issue')
        issue = expect(forge.request('GET', issue_path, token=token), {200}, 'issue readback')
        if issue['state'] != 'closed':
            raise RuntimeError('Issue readback state differs from requested state')
        record('issue_create_comment_close_readback')
        _, read_tokens, _, _, _ = grant(forge, alice, 'm0-read', 'openid read:repository read:issue read:user')
        expect(forge.request('GET', issue_path, token=read_tokens['access_token']), {200}, 'read-only read')
        expect(forge.request('POST', path + '/issues', token=read_tokens['access_token'],
                             payload={'title': 'must be rejected'}), {401, 403}, 'read-only write rejection')
        record('read_only_oauth_scope_rejects_write')
        _, bob_tokens, _, _, _ = grant(forge, bob, 'm0-bob', write_scope)
        bob_token = bob_tokens['access_token']
        expect(forge.request('GET', path, token=bob_token), {403, 404}, 'cross-user private read')
        expect(forge.request('POST', path + '/issues', token=bob_token,
                             payload={'title': 'must be rejected'}), {403, 404}, 'cross-user private write')
        record('cross_user_private_read_write_rejected')
        collaborator = path + '/collaborators/bob'
        expect(forge.request('PUT', collaborator, basic=alice, payload={'permission': 'write'}), {204}, 'grant collaborator')
        expect(forge.request('GET', path, token=bob_token), {200}, 'collaborator read')
        expect(forge.request('DELETE', collaborator, basic=alice), {204}, 'revoke collaborator')
        expect(forge.request('GET', path, token=bob_token), {403, 404}, 'revoked collaborator read')
        expect(forge.request('POST', path + '/issues', token=bob_token,
                             payload={'title': 'must be rejected after revoke'}), {403, 404}, 'revoked collaborator write')
        record('repository_permission_revocation_effective_for_existing_oauth_token')
        _, _, idp_claims, _, _ = grant(idp, credentials['idp']['alice'], 'm0-idp',
                                     'openid public-only email profile', identity_only=True)
        if alice_claims.get('email') != idp_claims.get('email') or alice_claims['iss'] == idp_claims['iss']:
            raise RuntimeError('Same-email independent-issuer fixture was not established')
        record('same_email_independent_issuer_subjects',
               identities=[{'issuer': c['iss'], 'subject': c['sub']} for c in (alice_claims, idp_claims)],
               scope='upstream identity inputs only; app account binding is not implemented')
        identity_scopes = 'openid public-only email profile read:user'
        _, identity_tokens, _, _, _ = grant(idp, credentials['idp']['alice'],
                                            'm0-identity-read-user', identity_scopes)
        expect(idp.request('POST', '/api/v1/user/repos', basic=credentials['idp']['alice'],
                           payload={'name': 'identity-private-fixture', 'private': True, 'auto_init': True}),
               {201}, 'identity private fixture')
        identity_private = idp.request('GET', '/api/v1/repos/alice/identity-private-fixture',
                                       token=identity_tokens['access_token'])
        expect(identity_private, {403, 404}, 'identity scope private resource rejection')
        record('identity_scope_explicit_read_user_variant', scope=identity_scopes,
               userinfo_status=200, private_resource_status=identity_private[0])
        _, broad, _, _, _ = grant(forge, alice, 'm0-oidc-only', 'openid email profile')
        broad_status = forge.request('GET', path, token=broad['access_token'])[0]
        if broad_status not in (200, 401, 403, 404):
            raise RuntimeError(f'Unexpected HTTP {broad_status} in identity-only resource probe')
        record('oidc_only_scope_private_resource_access', 'gap' if broad_status == 200 else 'pass',
               http_status=broad_status, expected_boundary='identity-only must not imply private-resource authorization')
        unknown_app, unknown, _, _, _ = grant(forge, alice, 'm0-unknown-scope', 'openid m0-unknown-scope')
        unknown_status = forge.request('GET', path, token=unknown['access_token'])[0]
        if unknown_status not in (200, 401, 403, 404):
            raise RuntimeError(f'Unexpected HTTP {unknown_status} in unknown-scope resource probe')
        record('unknown_scope_private_resource_access', 'gap' if unknown_status == 200 else 'pass',
               http_status=unknown_status, expected_boundary='unknown scope must not expand private-resource authorization')
        expect(forge.request('DELETE', f'/api/v1/user/applications/oauth2/{write_app["id"]}', basic=alice), {204}, 'delete OAuth app')
        revoked_status = forge.request('GET', path, token=token)[0]
        record('deleted_oauth_application_token', 'pass' if revoked_status == 401 else 'gap', http_status=revoked_status)
        report['completed'] = True
        report['passed_product_acceptance'] = False
        record('upstream_probe_completed', scope='partial IAM and Issue API only; no Runner, app UI, OCI, Release or production evidence')
        return 2 if any(r['status'] == 'gap' for r in results) else 0
    except Exception as exc:
        report['completed'] = False
        # Controlled exception messages exclude response bodies, tokens, URLs with code and cookies.
        message = str(exc) if isinstance(exc, RuntimeError) else type(exc).__name__
        record('probe_interrupted', 'fail', reason=message)
        return 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['profiles', 'discovery', 'lifecycle', 'lifecycle-baseline', 'issues', 'releases', 'oci'], default='profiles',
                        help='profiles: reviewed grants; discovery: raw scopes; lifecycle: long expiry/native consent; '
                             'lifecycle-baseline: historical form-token diagnosis; issues/releases/oci: resource contracts and response loss')
    parser.add_argument('--regctl', help='OCI only: path to the pinned task-local regctl binary')
    args = parser.parse_args()
    raise SystemExit(main(args.mode, args.regctl))
