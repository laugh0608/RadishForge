#!/usr/bin/env python3
"""Real local Gitea protocol probes. No app implementation or third-party packages."""
import argparse
import base64
import hashlib
from html.parser import HTMLParser
import http.cookiejar
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

CALLBACK = load_contract()['client_registration']['redirect_uris'][0]
REQUESTS = []


class AuthorizationRejected(RuntimeError):
    def __init__(self, error):
        super().__init__('OAuth authorization rejected')
        self.error = error if error in ('access_denied', 'invalid_scope', 'invalid_request') else 'other_error'


class GrantRejected(RuntimeError):
    def __init__(self, status, reason, metadata_type=None):
        super().__init__('Credential cannot establish an active upstream account')
        self.status = status
        self.reason = reason
        self.metadata_type = metadata_type


def b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode()


def unb64(value):
    return base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))


class Redirects(urllib.request.HTTPRedirectHandler):
    def __init__(self, origin):
        self.origin = origin

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if newurl.startswith(CALLBACK + '?'):
            return None  # Capture the protocol callback without opening another service.
        parsed = urllib.parse.urlsplit(newurl)
        if f'{parsed.scheme}://{parsed.netloc}' != self.origin:
            raise RuntimeError('Unexpected cross-origin redirect')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Forms(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.forms, self.current = [], None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'form':
            self.current = {'action': attrs.get('action', ''), 'fields': {}, 'buttons': []}
            self.forms.append(self.current)
        elif self.current is not None and tag in ('input', 'button') and attrs.get('name'):
            if tag == 'button' or attrs.get('type') == 'submit':
                self.current['buttons'].append((attrs['name'], attrs.get('value', '')))
            else:
                self.current['fields'][attrs['name']] = attrs.get('value', '')

    def handle_endtag(self, tag):
        if tag == 'form':
            self.current = None


class Client:
    def __init__(self, base, *, browser_session=False):
        self.base = base
        context = ssl.create_default_context(cafile=str(RUNTIME / 'ca.crt'))
        handlers = [urllib.request.HTTPSHandler(context=context), Redirects(base)]
        if browser_session:
            handlers.append(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.opener = urllib.request.build_opener(*handlers)

    def request(self, method, path, *, payload=None, form=None, token=None, basic=None):
        url = urllib.parse.urljoin(self.base + '/', path)
        origin = urllib.parse.urlsplit(url)
        if f'{origin.scheme}://{origin.netloc}' != self.base:
            raise RuntimeError('Refusing to send request outside the registered test origin')
        headers = {'User-Agent': 'RadishForge-M0-contract-probe'}
        body = None
        if payload is not None:
            body = json.dumps(payload).encode()
            headers['Content-Type'] = 'application/json'
        if form is not None:
            body = urllib.parse.urlencode(form).encode()
            headers['Content-Type'] = 'application/x-www-form-urlencoded'
        if token:
            headers['Authorization'] = 'Bearer ' + token
        if basic:
            headers['Authorization'] = 'Basic ' + base64.b64encode(':'.join(basic).encode()).decode()
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            result = self.opener.open(req, timeout=15)
        except urllib.error.HTTPError as exc:
            result = exc
        with result:
            raw = result.read(2_000_001)
            if len(raw) > 2_000_000:
                raise RuntimeError('Response exceeds probe size limit')
            kind = result.headers.get('Content-Type', '')
            content = json.loads(raw) if raw and 'json' in kind else raw.decode(errors='replace')
            REQUESTS.append({'origin': self.base, 'method': method,
                             'path': urllib.parse.urlsplit(url).path, 'status': result.code})
            return result.code, content, result.headers.get('Location'), result.url


def expect(result, statuses, label):
    status, body, _, _ = result
    if status not in statuses:
        raise RuntimeError(f'{label}: expected HTTP {sorted(statuses)}, got {status}; body withheld')
    return body


def issue_code(client, app, credentials, scopes, *, approve=True):
    verifier, nonce, oauth_state = b64(secrets.token_bytes(32)), secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    query = {'client_id': app['client_id'], 'redirect_uri': CALLBACK, 'response_type': 'code',
             'scope': scopes, 'state': oauth_state, 'nonce': nonce,
             'code_challenge': b64(hashlib.sha256(verifier.encode()).digest()), 'code_challenge_method': 'S256'}
    result = client.request('GET', '/login/oauth/authorize?' + urllib.parse.urlencode(query))
    for _ in range(4):
        status, content, location, page_url = result
        if status in (302, 303) and location and location.startswith(CALLBACK + '?'):
            values = urllib.parse.parse_qs(urllib.parse.urlsplit(location).query)
            if values.get('state') != [oauth_state]:
                raise RuntimeError('OAuth callback state does not match the transaction')
            if 'error' in values:
                raise AuthorizationRejected(values['error'][0])
            if 'code' not in values:
                raise RuntimeError('OAuth callback missing code or matching state')
            return values['code'][0], verifier, nonce
        if status != 200 or not isinstance(content, str):
            raise RuntimeError(f'OAuth browser protocol did not reach consent/callback: HTTP {status}')
        forms = Forms(content).forms
        login = next((f for f in forms if 'password' in f['fields']), None)
        if login:
            fields = dict(login['fields'], user_name=credentials[0], password=credentials[1])
            result = client.request('POST', urllib.parse.urljoin(page_url, login['action']), form=fields)
            continue
        consent = next((f for f in forms if 'grant' in f['action'] or 'client_id' in f['fields']), None)
        if not consent:
            # Names are safe to inspect; never print form values or authorization URLs.
            names = [sorted(f['fields']) for f in forms]
            raise RuntimeError(f'OAuth consent form not recognized; field names={names}')
        fields = dict(consent['fields'])
        for name, value in consent['buttons']:
            if value in ('true', '1', 'authorize', 'approve'):
                fields[name] = value
                break
        fields['granted'] = 'true' if approve else 'false'
        result = client.request('POST', urllib.parse.urljoin(page_url, consent['action']), form=fields)
    raise RuntimeError('OAuth page flow exceeded four forms')


def exchange(client, app, code, verifier, *, client_secret=None):
    form = {
        'grant_type': 'authorization_code', 'client_id': app['client_id'],
        'redirect_uri': CALLBACK, 'code': code, 'code_verifier': verifier}
    if client_secret is not None:
        form['client_secret'] = client_secret
    return client.request('POST', '/login/oauth/access_token', form=form)


def der(tag, raw):
    size = len(raw)
    length = bytes([size]) if size < 128 else bytes([0x80 + (size.bit_length() + 7) // 8]) + size.to_bytes((size.bit_length() + 7) // 8, 'big')
    return bytes([tag]) + length + raw


def jwt_claims(client, token, app, nonce):
    parts = token.split('.')
    if len(parts) != 3:
        raise RuntimeError('Invalid JWT shape')
    header, claims = [json.loads(unb64(p)) for p in parts[:2]]
    if header.get('alg') != 'RS256':
        raise RuntimeError('Unexpected ID token signing algorithm')
    discovery = expect(client.request('GET', '/.well-known/openid-configuration'), {200}, 'discovery')
    if discovery['issuer'].rstrip('/') != client.base:
        raise RuntimeError('Discovery issuer differs from registered test origin')
    keys = expect(client.request('GET', discovery['jwks_uri']), {200}, 'JWKS')['keys']
    key = next(k for k in keys if k.get('kid') == header.get('kid') and k.get('kty') == 'RSA')
    numbers = []
    for name in ('n', 'e'):
        value = unb64(key[name])
        if value[0] & 0x80:
            value = b'\x00' + value
        numbers.append(der(2, value))
    public = der(0x30, b''.join(numbers))
    command(['openssl', 'rsa', '-RSAPublicKey_in', '-inform', 'DER', '-pubout',
             '-out', str(RUNTIME / 'jwt-public.pem')], data=public)
    write_private(RUNTIME / 'jwt.sig', unb64(parts[2]))
    command(['openssl', 'dgst', '-sha256', '-verify', str(RUNTIME / 'jwt-public.pem'),
             '-signature', str(RUNTIME / 'jwt.sig')], data='.'.join(parts[:2]).encode())
    audience = claims.get('aud')
    audiences = audience if isinstance(audience, list) else [audience]
    if (claims.get('iss') != discovery['issuer'] or app['client_id'] not in audiences
            or claims.get('nonce') != nonce or not claims.get('sub')
            or not isinstance(claims.get('exp'), (int, float)) or claims['exp'] <= time.time()
            or claims.get('iat', 0) > time.time() + 30
            or ('azp' in claims and claims['azp'] != app['client_id'])
            or (len(audiences) > 1 and claims.get('azp') != app['client_id'])):
        raise RuntimeError('ID token claims validation failed')
    return {k: claims[k] for k in ('iss', 'sub', 'aud', 'email') if k in claims}


def profile_checks(owner, forge, idp, credentials, record):
    contract = load_contract()
    alice, bob = credentials['forge']['alice'], credentials['forge']['bob']
    idp_alice = credentials['idp']['alice']
    path = '/api/v1/repos/alice/private-fixture'

    def register(purpose, client, user, name, requested=None):
        scopes = scope_for(purpose, requested, origin=client.base)
        registration = dict(contract['client_registration'], name=name)
        app = expect(client.request('POST', '/api/v1/user/applications/oauth2', basic=user,
                                    payload=registration), {201}, 'register confidential client')
        if not isinstance(app.get('client_secret'), str) or not app['client_secret']:
            raise RuntimeError('Confidential client secret was not returned on creation')
        readback = expect(client.request('GET', f'/api/v1/user/applications/oauth2/{app["id"]}',
                                        basic=user), {200}, 'read back client registration')
        for key, value in contract['client_registration'].items():
            if readback.get(key) != value:
                raise RuntimeError(f'Registered client configuration differs: {key}')
        return app, scopes

    def introspect(client, app, token):
        return expect(client.request('POST', '/login/oauth/introspect',
                                     basic=(app['client_id'], app['client_secret']),
                                     form={'token': token}), {200}, 'token introspection')

    def receipt(purpose, client, app, tokens):
        if (tokens.get('token_type', '').lower() != 'bearer'
                or tokens.get('expires_in') != contract['test_provider_settings']['ACCESS_TOKEN_EXPIRATION_TIME']
                or not isinstance(tokens.get('access_token'), str)
                or not isinstance(tokens.get('refresh_token'), str)):
            raise RuntimeError('Token response differs from configured test lifetime or grant type')
        info = introspect(client, app, tokens['access_token'])
        if not isinstance(info, dict):
            raise GrantRejected(200, 'invalid_introspection_metadata', type(info).__name__)
        if info.get('active') is not True:
            raise GrantRejected(200, 'token_not_active')
        scope_for(purpose, info.get('scope', ''), origin=client.base)
        account_result = client.request('GET', '/api/v1/user', token=tokens['access_token'])
        if account_result[0] in (401, 403):
            raise GrantRejected(account_result[0], 'account_access_denied')
        account = expect(account_result, {200}, 'active upstream account')
        if not isinstance(account, dict) or str(account.get('id')) != info.get('sub'):
            raise GrantRejected(200, 'invalid_or_mismatched_account')
        return info

    def authorize(purpose, client, user, name, requested=None):
        app, scopes = register(purpose, client, user, name, requested)
        browser = Client(client.base, browser_session=True)
        code, verifier, nonce = issue_code(browser, app, user, scopes)
        tokens = expect(exchange(client, app, code, verifier, client_secret=app['client_secret']),
                        {200}, 'confidential client code + PKCE')
        claims = jwt_claims(client, tokens['id_token'], app, nonce)
        info = expect(client.request('GET', '/login/oauth/userinfo', token=tokens['access_token']),
                      {200}, 'profile UserInfo')
        if info.get('sub') != claims['sub']:
            raise RuntimeError('Profile UserInfo subject differs from ID token')
        receipt(purpose, client, app, tokens)
        return app, tokens, claims, browser

    def refresh(purpose, client, app, token, requested=None):
        scope_for(purpose, requested, origin=client.base)  # Reject widening before any HTTP request.
        return client.request('POST', '/login/oauth/access_token', form={
            'grant_type': 'refresh_token', 'client_id': app['client_id'],
            'client_secret': app['client_secret'], 'refresh_token': token})

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
    record('separate_confidential_clients_and_exact_granted_scopes', profiles=list(contract['profiles']))
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


def main(mode):
    owner = state()
    if mode == 'profiles' and (not owner.get('auth_profile') or
                              owner.get('auth_profile_sha256') != hashlib.sha256(PROFILE_PATH.read_bytes()).hexdigest()):
        raise RuntimeError('Prepare a fresh environment with --auth-profile matching the reviewed contract')
    marker = RUNTIME / 'contract-started.json'
    if marker.exists():
        raise RuntimeError('Probe already started; reconcile prior writes before a new run')
    write_private(marker, json.dumps({'project': owner['project'], 'started': True}))
    results = []
    report = {'project': owner['project'], 'platform': 'linux/arm64', 'context': owner['context'],
              'runner_started': False, 'system_trust_changed': False, 'results': results,
              'requests': REQUESTS, 'mode': mode,
              'http_transport': 'stateless API credentials; isolated browser cookie jars for login/consent only'}

    def record(name, status='pass', **details):
        results.append({'name': name, 'status': status, **details})
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
            for username in (('alice', 'bob') if service == 'forge' else ('alice',)):
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
    parser.add_argument('--mode', choices=['profiles', 'discovery'], default='profiles',
                        help='profiles validates reviewed combinations; discovery reproduces raw upstream differences')
    raise SystemExit(main(parser.parse_args().mode))
