"""Shared real OAuth transport and reviewed grants for M0 probes only."""
import base64
import hashlib
from html.parser import HTMLParser
import http.cookiejar
import json
import secrets
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request

from m0_local import RUNTIME, command, write_private
from m0_scope import load_contract, scope_for

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
    def __init__(self, origin, browser_session=False):
        self.origin = origin
        self.browser_session = browser_session

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if newurl.startswith(CALLBACK + '?'):
            return None  # Capture the protocol callback without opening another service.
        parsed = urllib.parse.urlsplit(newurl)
        if f'{parsed.scheme}://{parsed.netloc}' != self.origin:
            raise RuntimeError('Unexpected cross-origin redirect')
        if not self.browser_session:
            return None  # API redirects are evidence, not a successful login page.
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
        handlers = [urllib.request.HTTPSHandler(context=context), Redirects(base, browser_session)]
        if browser_session:
            handlers.append(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.opener = urllib.request.build_opener(*handlers)

    def request(self, method, path, *, payload=None, form=None, token=None, basic=None, timeout=15):
        if type(timeout) not in (int, float) or not 0 < timeout <= 15:
            raise ValueError('Probe timeout must be positive and at most 15 seconds')
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
            try:
                result = self.opener.open(req, timeout=timeout)
            except urllib.error.HTTPError as exc:
                result = exc
            with result:
                raw = result.read(2_000_001)
                if len(raw) > 2_000_000:
                    raise RuntimeError('Response exceeds probe size limit')
                kind = result.headers.get('Content-Type', '')
                content = json.loads(raw) if raw and 'json' in kind else raw.decode(errors='replace')
                REQUESTS.append({'origin': self.base, 'method': method,
                                 'path': urllib.parse.urlsplit(url).path, 'status': result.code,
                                 'content_type': kind.split(';')[0], 'body_type': type(content).__name__,
                                 'final_path': urllib.parse.urlsplit(result.url).path})
                return result.code, content, result.headers.get('Location'), result.url
        except (OSError, urllib.error.URLError) as exc:
            REQUESTS.append({'origin': self.base, 'method': method,
                             'path': urllib.parse.urlsplit(url).path, 'status': None,
                             'outcome': 'unknown', 'error_type': type(exc).__name__})
            raise


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


def register(purpose, client, user, name, requested=None):
    contract = load_contract()
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

def introspection_metadata(result):
    """401 alone cannot distinguish caller authentication from token rejection."""
    status, info, _, _ = result
    if status == 401:
        raise GrantRejected(status, 'introspection_unauthorized_unattributed')
    if status != 200:
        reason = 'introspection_unavailable' if status >= 500 else 'introspection_rejected'
        raise GrantRejected(status, reason)
    if not isinstance(info, dict):
        raise GrantRejected(status, 'invalid_introspection_metadata', type(info).__name__)
    if type(info.get('active')) is not bool:
        raise GrantRejected(status, 'invalid_active_metadata')
    if info['active'] is not True:
        raise GrantRejected(status, 'token_not_active')
    if (not isinstance(info.get('sub'), str) or not info['sub'].isascii()
            or not info['sub'].isdecimal() or int(info['sub']) <= 0):
        raise GrantRejected(status, 'invalid_subject_metadata')
    if not isinstance(info.get('scope'), str) or not info['scope']:
        raise GrantRejected(status, 'invalid_scope_metadata')
    return info


def introspect(client, app, token, *, client_secret=None):
    return client.request('POST', '/login/oauth/introspect',
                          basic=(app['client_id'], app['client_secret'] if client_secret is None else client_secret),
                          form={'token': token})


def receipt(purpose, client, app, tokens, *, subject=None):
    contract = load_contract()
    if (not isinstance(tokens, dict) or not isinstance(tokens.get('token_type'), str)
            or tokens['token_type'].lower() != 'bearer'
            or type(tokens.get('expires_in')) is not int
            or tokens['expires_in'] != contract['test_provider_settings']['ACCESS_TOKEN_EXPIRATION_TIME']
            or not isinstance(tokens.get('access_token'), str) or not tokens['access_token']
            or not isinstance(tokens.get('refresh_token'), str) or not tokens['refresh_token']):
        raise RuntimeError('Token response differs from configured test lifetime or grant type')
    try:
        info = introspection_metadata(introspect(client, app, tokens['access_token']))
        scope_for(purpose, info['scope'], origin=client.base)
        account_result = client.request('GET', '/api/v1/user', token=tokens['access_token'])
    except (OSError, urllib.error.URLError):
        raise GrantRejected(None, 'verification_result_unknown') from None
    except ValueError:
        raise GrantRejected(None, 'invalid_verification_response') from None
    if account_result[0] in (401, 403):
        raise GrantRejected(account_result[0], 'account_access_denied')
    if account_result[0] != 200:
        raise GrantRejected(account_result[0], 'account_verification_unavailable')
    account = account_result[1]
    if (not isinstance(account, dict) or type(account.get('id')) is not int
            or account['id'] <= 0 or str(account['id']) != info['sub']
            or (subject is not None and info['sub'] != subject)):
        raise GrantRejected(200, 'invalid_or_mismatched_account')
    return info

def authorize(purpose, client, user, name, requested=None):
    app, scopes = register(purpose, client, user, name, requested)
    tokens, claims, browser = authorize_registered(purpose, client, user, app, scopes)
    return app, tokens, claims, browser


def authorize_registered(purpose, client, user, app, requested=None):
    scopes = scope_for(purpose, requested, origin=client.base)
    browser = Client(client.base, browser_session=True)
    code, verifier, nonce = issue_code(browser, app, user, scopes)
    tokens = expect(exchange(client, app, code, verifier, client_secret=app['client_secret']),
                    {200}, 'confidential client code + PKCE')
    claims = jwt_claims(client, tokens['id_token'], app, nonce)
    info = expect(client.request('GET', '/login/oauth/userinfo', token=tokens['access_token']),
                  {200}, 'profile UserInfo')
    if info.get('sub') != claims['sub']:
        raise RuntimeError('Profile UserInfo subject differs from ID token')
    receipt(purpose, client, app, tokens, subject=claims['sub'])
    return tokens, claims, browser

def refresh(purpose, client, app, token, requested=None):
    scope_for(purpose, requested, origin=client.base)  # Reject widening before any HTTP request.
    return client.request('POST', '/login/oauth/access_token', form={
        'grant_type': 'refresh_token', 'client_id': app['client_id'],
        'client_secret': app['client_secret'], 'refresh_token': token})
