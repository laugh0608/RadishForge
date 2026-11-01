#!/usr/bin/env python3
"""Real local Gitea protocol probes. No app implementation or third-party packages."""
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

CALLBACK = 'http://127.0.0.1:18555/callback'
REQUESTS = []


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
    def __init__(self, base):
        self.base = base
        context = ssl.create_default_context(cafile=str(RUNTIME / 'ca.crt'))
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=context),
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()), Redirects(base))

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


def issue_code(client, app, credentials, scopes):
    verifier, nonce, oauth_state = b64(secrets.token_bytes(32)), secrets.token_urlsafe(24), secrets.token_urlsafe(24)
    query = {'client_id': app['client_id'], 'redirect_uri': CALLBACK, 'response_type': 'code',
             'scope': scopes, 'state': oauth_state, 'nonce': nonce,
             'code_challenge': b64(hashlib.sha256(verifier.encode()).digest()), 'code_challenge_method': 'S256'}
    result = client.request('GET', '/login/oauth/authorize?' + urllib.parse.urlencode(query))
    for _ in range(4):
        status, content, location, page_url = result
        if status in (302, 303) and location and location.startswith(CALLBACK + '?'):
            values = urllib.parse.parse_qs(urllib.parse.urlsplit(location).query)
            if values.get('state') != [oauth_state] or 'code' not in values:
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
        fields.setdefault('granted', 'true')
        result = client.request('POST', urllib.parse.urljoin(page_url, consent['action']), form=fields)
    raise RuntimeError('OAuth page flow exceeded four forms')


def exchange(client, app, code, verifier):
    return client.request('POST', '/login/oauth/access_token', form={
        'grant_type': 'authorization_code', 'client_id': app['client_id'],
        'redirect_uri': CALLBACK, 'code': code, 'code_verifier': verifier})


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


def main():
    owner = state()
    marker = RUNTIME / 'contract-started.json'
    if marker.exists():
        raise RuntimeError('Probe already started; reconcile prior writes before a new run')
    write_private(marker, json.dumps({'project': owner['project'], 'started': True}))
    results = []
    report = {'project': owner['project'], 'platform': 'linux/arm64', 'context': owner['context'],
              'runner_started': False, 'system_trust_changed': False, 'results': results,
              'requests': REQUESTS}

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
        browser = Client(client.base)
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
                if user.get('is_admin'):
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
        write_scope = 'openid email profile read:repository write:issue read:user'
        write_app, write_tokens, alice_claims, code, verifier = grant(forge, alice, 'm0-write', write_scope)
        record('oauth_pkce_rs256_and_claims', claims=alice_claims)
        expect(exchange(forge, write_app, code, verifier), {400, 401}, 'replayed authorization code')
        record('authorization_code_replay_rejected')
        bad_app = new_app(forge, alice, 'm0-bad-pkce')
        bad_code, _, _ = issue_code(Client(forge.base), bad_app, alice, write_scope)
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
    raise SystemExit(main())
