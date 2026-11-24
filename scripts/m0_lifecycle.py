"""Lifecycle contracts against isolated real Gitea; no product sessions."""
from concurrent.futures import ThreadPoolExecutor
import json
import threading
import time

from m0_local import RUNTIME, write_private
from m0_scope import load_contract
from m0_oauth import (Client, GrantRejected, authorize, authorize_registered, expect,
                      introspect, receipt, refresh)


def rejection(purpose, client, app, tokens):
    try:
        receipt(purpose, client, app, tokens)
    except GrantRejected as exc:
        return {'status': exc.status, 'reason': exc.reason, 'metadata_type': exc.metadata_type}
    raise RuntimeError('Credential gate unexpectedly accepted a rejected fixture')


def diagnostics(forge, credentials, record, *, legacy):
    """Fresh controlled fixtures reproduce the two historical differences."""
    alice, bob = credentials['forge']['alice'], credentials['forge']['bob']
    path = '/api/v1/repos/alice/private-fixture'
    app, tokens, _, _ = authorize('resource_read', forge, alice, 'm0-lifecycle-expired-access')
    deadline = time.monotonic() + tokens['expires_in'] + 2
    disabled_app, disabled, _, _ = authorize('issue_write', forge, bob, 'm0-lifecycle-disabled')
    expect(forge.request('POST', '/api/v1/user/repos', basic=bob,
                         payload={'name': 'bob-private-fixture', 'private': True, 'auto_init': True}),
           {201}, 'disabled account repository')
    bob_path = '/api/v1/repos/bob/bob-private-fixture'
    expect(forge.request('PATCH', '/api/v1/admin/users/bob', basic=credentials['forge']['admin'],
                         payload={'prohibit_login': True}), {200}, 'disable isolated user')
    disabled_refresh = refresh('issue_write', forge, disabled_app, disabled['refresh_token'])
    expect(disabled_refresh, {200}, 'historical disabled refresh')
    new = disabled_refresh[1]
    inspected = introspect(forge, disabled_app, new['access_token'])
    resource = forge.request('GET', bob_path, token=new['access_token'])
    expect(resource, {401, 403}, 'disabled resource access')
    stopped = rejection('issue_write', forge, disabled_app, new)
    if legacy:
        if inspected[0] != 200 or not isinstance(inspected[1], str):
            raise RuntimeError('Historical disabled introspection did not reproduce')
    else:
        if inspected[0] != 200 or not isinstance(inspected[1], dict):
            raise RuntimeError('Header-only introspection did not return metadata')
        if stopped['reason'] != 'account_access_denied':
            raise RuntimeError('Disabled credentials were not rejected by online account verification')
    record('disabled_account_refresh_diagnostic', 'gap', refresh_status=200,
           introspection_status=inspected[0], metadata_type=type(inspected[1]).__name__,
           introspection_active=inspected[1].get('active') if isinstance(inspected[1], dict) else None,
           final_path=inspected[3].split('?', 1)[0].removeprefix(forge.base),
           resource_status=resource[0], local_rejection=stopped,
           resolution='historical_reproduction' if legacy else 'reject_with_online_account_check')
    expect(forge.request('PATCH', '/api/v1/admin/users/bob', basic=credentials['forge']['admin'],
                         payload={'prohibit_login': False}), {200}, 'restore isolated user')
    receipt('issue_write', forge, disabled_app, new)
    expect(forge.request('GET', bob_path, token=new['access_token']), {200}, 'restored account access')
    record('account_restoration_reactivates_existing_grant',
           scope='Gitea grant persists; RadishForge must require fresh explicit authorization after local unbind')
    record('waiting_for_access_expiry', seconds=max(0, round(deadline-time.monotonic())))
    while time.monotonic() < deadline:
        time.sleep(min(1, max(0, deadline-time.monotonic())))
    expect(forge.request('GET', path, token=tokens['access_token']), {401}, 'expired resource access')
    expired = introspect(forge, app, tokens['access_token'])
    wrong = introspect(forge, app, tokens['access_token'], client_secret='wrong-isolated-client-secret')
    new_tokens = expect(refresh('resource_read', forge, app, tokens['refresh_token']), {200}, 'fresh control')
    fresh = introspect(forge, app, new_tokens['access_token'])
    receipt('resource_read', forge, app, new_tokens)
    if legacy:
        if expired[0] != 401:
            raise RuntimeError('Historical expired introspection did not reproduce')
    elif expired[0] != 200 or expired[1] != {'active': False}:
        raise RuntimeError('Expired token did not return inactive metadata under header-only authentication')
    expect(wrong, {401}, 'wrong introspection client secret')
    record('expired_access_introspection_diagnostic', 'gap' if legacy else 'pass', expired_status=expired[0],
           expired_metadata_type=type(expired[1]).__name__, wrong_secret_status=wrong[0],
           fresh_status=fresh[0], fresh_active=fresh[1].get('active'),
           local_rejection=rejection('resource_read', forge, app, tokens))
    if not legacy:
        # The same client must distinguish a bad caller secret from invalid target tokens.
        unknown = introspect(forge, app, 'synthetic-invalid-token')
        foreign_app, foreign_tokens, _, _ = authorize('resource_read', forge, alice, 'm0-foreign-introspection')
        foreign = introspect(forge, foreign_app, new_tokens['access_token'])
        for response in (unknown, foreign):
            if response[0] != 200 or response[1] != {'active': False}:
                raise RuntimeError('Invalid or foreign-client token metadata was not inactive')
        record('introspection_invalid_foreign_and_client_auth_controls', invalid_status=unknown[0],
               foreign_status=foreign[0], wrong_secret_status=wrong[0], valid_status=fresh[0])


def refresh_boundaries(forge, credentials, record):
    alice = credentials['forge']['alice']
    path = '/api/v1/repos/alice/private-fixture'
    app, tokens, _, _ = authorize('resource_read', forge, alice, 'm0-refresh-concurrent')
    barrier = threading.Barrier(2)

    def attempt():
        client = Client(forge.base)
        barrier.wait(timeout=10)
        return refresh('resource_read', client, app, tokens['refresh_token'])

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(attempt) for _ in range(2)]
        responses = [f.result(timeout=30) for f in futures]
    statuses = [r[0] for r in responses]
    if statuses.count(200) != 1 or any(s not in (200, 400, 401) for s in statuses):
        record('concurrent_refresh_single_winner', 'gap', statuses=statuses)
        raise RuntimeError('Concurrent refresh did not produce exactly one usable successor')
    winner = next(r[1] for r in responses if r[0] == 200)
    receipt('resource_read', forge, app, winner)
    expect(forge.request('GET', path, token=winner['access_token']), {200}, 'winner private read')
    expect(forge.request('POST', path + '/issues', token=winner['access_token'],
                         payload={'title': 'must be rejected after concurrent refresh'}), {403}, 'winner write rejection')
    expect(refresh('resource_read', forge, app, tokens['refresh_token']), {400, 401}, 'concurrent loser replay')
    successor = expect(refresh('resource_read', forge, app, winner['refresh_token']), {200}, 'winner successor refresh')
    receipt('resource_read', forge, app, successor)
    expect(refresh('resource_read', forge, app, winner['refresh_token']), {400, 401}, 'successor replay')
    record('concurrent_refresh_single_winner_and_replay', statuses=statuses,
           private_read_status=200, private_write_status=403, next_refresh_status=200)


def consent_revocation(owner, forge, idp, credentials, record):
    alice, bob = credentials['forge']['alice'], credentials['forge']['bob']
    app, alice_tokens, _, _ = authorize('issue_write', forge, alice, 'm0-shared-consent')
    bob_tokens, _, _ = authorize_registered('issue_write', forge, bob, app)
    control_app, control_tokens, _, _ = authorize('resource_read', forge, bob, 'm0-bob-unrelated-grant')
    identity_app, identity_tokens, _, _ = authorize('identity', idp, credentials['idp']['alice'], 'm0-identity-control')
    write_private(RUNTIME / 'consent-target.json', json.dumps({
        'project': owner['project'], 'user': 'bob', 'application_id': app['id'],
        'application_name': 'm0-shared-consent'}))
    record('awaiting_native_consent_revocation',
           instruction='Use native Gitea settings UI as bob; no private frontend endpoint is called by this probe')
    # Operator/browser handshake refreshes immediately before the click, so rejection
    # of the old access token cannot be mistaken for its ordinary 30-second expiry.
    deadline = time.monotonic() + 1200
    while not (RUNTIME / 'consent-ui-ready.json').exists():
        if time.monotonic() >= deadline:
            raise RuntimeError('Native consent UI preparation timed out; no automatic write retry')
        time.sleep(1)
    bob_tokens = expect(refresh('issue_write', forge, app, bob_tokens['refresh_token']), {200}, 'pre-revocation refresh')
    receipt('issue_write', forge, app, bob_tokens)
    issued = time.monotonic()
    write_private(RUNTIME / 'consent-click-ready.json', json.dumps({'project': owner['project'], 'ready': True}))
    while not (RUNTIME / 'consent-ui-revoked.json').exists():
        if time.monotonic() - issued >= 25:
            raise RuntimeError('Revocation was not observed before access-token expiry; evidence would be ambiguous')
        time.sleep(0.1)
    event = json.loads((RUNTIME / 'consent-ui-revoked.json').read_text())
    if time.monotonic() - issued >= 25:
        raise RuntimeError('Revocation receipt arrived too late to distinguish revocation from token expiry')
    if event != {'project': owner['project'], 'user': 'bob', 'application_id': app['id'], 'revoked': True}:
        raise RuntimeError('Native consent revocation receipt does not match this fixture')
    path = '/api/v1/repos/bob/bob-private-fixture'
    access = forge.request('GET', path, token=bob_tokens['access_token'])
    expect(access, {401, 403}, 'single user revoked access')
    expect(forge.request('POST', path + '/issues', token=bob_tokens['access_token'],
                         payload={'title': 'must be rejected after consent revoke'}), {401, 403}, 'revoked issue write')
    revoked_refresh = refresh('issue_write', forge, app, bob_tokens['refresh_token'])
    expect(revoked_refresh, {400, 401}, 'single user revoked refresh')
    metadata = introspect(forge, app, bob_tokens['access_token'])
    if metadata[0] != 200 or metadata[1] != {'active': False}:
        raise RuntimeError('Revoked grant introspection was not inactive')
    for purpose, client, control, grant in (
        ('issue_write', forge, app, alice_tokens), ('resource_read', forge, control_app, control_tokens),
        ('identity', idp, identity_app, identity_tokens)):
        renewed = expect(refresh(purpose, client, control, grant['refresh_token']), {200}, 'unaffected grant refresh')
        receipt(purpose, client, control, renewed)
    expect(forge.request('GET', f'/api/v1/user/applications/oauth2/{app["id"]}', basic=alice), {200}, 'shared app still exists')
    fresh, _, _ = authorize_registered('issue_write', forge, bob, app)
    expect(forge.request('GET', path, token=fresh['access_token']), {200}, 'explicit reconsent access')
    expect(refresh('issue_write', forge, app, bob_tokens['refresh_token']), {400, 401}, 'old grant remains revoked after reconsent')
    record('single_user_consent_revocation_isolated_and_reconsent', access_status=access[0],
           refresh_status=revoked_refresh[0], introspection_active=False,
           observed_before_expiry_seconds=round(time.monotonic()-issued, 3),
           other_user_same_app_valid=True, same_user_other_app_valid=True,
           independent_identity_valid=True, application_preserved=True)


def lifecycle_checks(owner, forge, idp, credentials, record, *, baseline=False):
    if baseline:
        diagnostics(forge, credentials, record, legacy=True)
        return
    if owner.get('legacy_query_auth'):
        raise RuntimeError('Full lifecycle requires header-only authentication configuration')
    alice = credentials['forge']['alice']
    expiry_app, expiry_tokens, _, _ = authorize('resource_read', forge, alice, 'm0-refresh-real-expiry')
    lifetime = load_contract()['test_provider_settings']['REFRESH_TOKEN_EXPIRATION_TIME'] * 3600
    started = time.monotonic()
    expiry_deadline = started + lifetime + 2
    record('real_refresh_expiry_fixture_started', lifetime_seconds=lifetime,
           scope='This token remains unused until after real expiry; no clock manipulation')
    diagnostics(forge, credentials, record, legacy=False)
    refresh_boundaries(forge, credentials, record)
    consent_revocation(owner, forge, idp, credentials, record)
    record('waiting_for_real_refresh_expiry', remaining_seconds=max(0, round(expiry_deadline-time.monotonic())))
    while time.monotonic() < expiry_deadline:
        time.sleep(min(1, max(0, expiry_deadline-time.monotonic())))
    # A fresh grant controls provider health; the original client is checked below.
    control_app, control, _, _ = authorize('resource_read', forge, alice, 'm0-refresh-expiry-control')
    expect(refresh('resource_read', forge, control_app, control['refresh_token']), {200}, 'live refresh control')
    expired = refresh('resource_read', forge, expiry_app, expiry_tokens['refresh_token'])
    expect(expired, {400, 401}, 'real expired refresh token')
    expect(forge.request('GET', '/api/v1/repos/alice/private-fixture', token=expiry_tokens['access_token']),
           {401}, 'old access also expired')
    # Authenticate this exact original client using a new explicit authorization.
    fresh, _, _ = authorize_registered('resource_read', forge, alice, expiry_app)
    receipt('resource_read', forge, expiry_app, fresh)
    expect(refresh('resource_read', forge, expiry_app, expiry_tokens['refresh_token']), {400, 401}, 'expired token after reconsent')
    record('real_refresh_token_expiry_rejected', elapsed_seconds=round(time.monotonic()-started, 3),
           expired_refresh_status=expired[0], same_client_reauthorization_valid=True,
           expired_token_still_rejected=True)
