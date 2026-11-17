"""Verify persistence of ordinary self-revocation across a task-only Gitea restart."""
from html.parser import HTMLParser
import re
import time
from urllib.parse import urljoin, urlsplit

from m0_issues import renew
from m0_local import compose, docker, verify_provider_settings
from m0_oauth import Client, Forms, authorize, authorize_registered, expect, introspect

ORIGIN = 'https://localhost:18443'
SETTINGS = '/user/settings/applications'


class GrantButtons(HTMLParser):
    def __init__(self, page):
        super().__init__()
        self.routes = []
        self.feed(page)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'button' and values.get('data-modal-confirm') == '#revoke-gitea-oauth2-grant':
            self.routes.append(values.get('data-url', ''))


def grant_button(browser, app):
    result = browser.request('GET', SETTINGS)
    page = expect(result, {200}, 'open native authorization settings')
    if urlsplit(result[3]).path != SETTINGS:
        raise RuntimeError('Native settings require the intended signed-in fixture session')
    prefix = SETTINGS + '/oauth2/' + str(app['id']) + '/revoke/'
    matches = [path for path in GrantButtons(page).routes if re.fullmatch(re.escape(prefix) + r'[1-9][0-9]*', path)]
    if len(matches) > 1:
        raise RuntimeError('Ambiguous authorization settings fixture')
    return matches[0] if matches else None


def sign_in(account):
    browser = Client(ORIGIN, browser_session=True)
    result = browser.request('GET', '/user/login')
    page = expect(result, {200}, 'read native login form')
    form, = (form for form in Forms(page).forms if 'password' in form['fields'])
    action = urljoin(result[3], form['action'])
    if action != ORIGIN + '/user/login':
        raise RuntimeError('Native login left the fixed fixture origin or path')
    expect(browser.request('POST', action, form={**form['fields'], 'user_name': account[0], 'password': account[1]}),
           {200}, 'sign in for independent settings readback')
    return browser


def restart_times(owner):
    services = {}
    for service in ('forge', 'idp', 'postgres'):
        container = compose(owner, 'ps', '-q', service).stdout.decode().strip()
        if not re.fullmatch(r'[a-f0-9]{12,64}', container):
            raise RuntimeError('Task service did not resolve to one running container')
        started = docker(owner, 'inspect', '--format', '{{.State.StartedAt}}', container).stdout.decode().strip()
        services[service] = (container, started)
    return services


def revoked_reads(forge, app, token, repo):
    meta = introspect(forge, app, token)
    if expect(meta, {200}, 'inspect revoked credential') != {'active': False}:
        raise RuntimeError('Revoked credential is still reported active')
    access = forge.request('GET', repo, token=token)
    expect(access, {401, 403}, 'deny resource after native self-revocation')
    return {'introspection_status': meta[0], 'active': False, 'private_repo_status': access[0]}


def consent_restart_checks(owner, forge, users, record):
    if forge.base != ORIGIN or owner['context'] != 'orbstack':
        raise RuntimeError('Expected the fixed OrbStack fixture')
    alice, bob = users['alice'], users['bob']
    name = 'm0-consent-restart'
    bob_repo = '/api/v1/repos/bob/' + name
    expect(forge.request('POST', '/api/v1/user/repos', basic=bob,
                         payload={'name': name, 'private': True, 'auto_init': True}),
           {201}, 'create private resource for the revocation fixture')
    app, alice_grant, _, _ = authorize('resource_read', forge, alice, 'm0-restart-shared')
    bob_grant, _, target_browser = authorize_registered('resource_read', forge, bob, app)
    control, control_grant, _, _ = authorize('resource_read', forge, bob, 'm0-restart-independent')
    target = grant_button(target_browser, app)
    if not target or not grant_button(target_browser, control):
        raise RuntimeError('The target and independent authorization are not both listed for fixture user Bob')
    before = restart_times(owner)
    bob_grant = renew(forge, 'resource_read', app, bob_grant)
    issued = time.monotonic()
    token = bob_grant['access_token']
    expect(forge.request('GET', bob_repo, token=token), {200}, 'read Bob private resource before self-revocation')
    target_browser.opener.addheaders.append(('Origin', ORIGIN))
    result = target_browser.request('POST', target, form={})
    expect(result, {200}, 'submit selected native self-revocation action')
    if grant_button(target_browser, app) or not grant_button(target_browser, control):
        raise RuntimeError('Unexpected authorization settings after native self-revocation')
    record('consent_restart_self_revocation_before_restart', native_status=result[0],
           revoked_grant_listed=False, independent_grant_listed=True, **revoked_reads(forge, app, token, bob_repo))

    compose(owner, 'restart', '--timeout', '7', 'forge', timeout=25)
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        try:
            status = forge.request('GET', '/api/healthz', timeout=2)[0]
            if status == 200:
                break
        except OSError:
            pass
        time.sleep(0.25)
    else:
        raise RuntimeError('Task Gitea did not become ready after restart')
    age = time.monotonic() - issued
    if age >= 25:
        raise RuntimeError('Restart took too long to separate revocation from natural access expiry')
    denied = revoked_reads(forge, app, token, bob_repo)
    after = restart_times(owner)
    if (after['forge'][0] != before['forge'][0] or after['forge'][1] == before['forge'][1]
            or after['idp'] != before['idp'] or after['postgres'] != before['postgres']):
        raise RuntimeError('Task restart did not affect exactly the expected resource Gitea')
    settings = owner['effective_provider_settings']
    verify_provider_settings(owner)
    if owner['effective_provider_settings'] != settings:
        raise RuntimeError('Restart changed the verified provider configuration')
    record('consent_restart_only_forge_and_revocation_persisted', access_age_seconds=round(age, 3),
           forge_started_before=before['forge'][1], forge_started_after=after['forge'][1],
           idp_restarted=False, postgres_restarted=False, **denied)

    bob_settings = sign_in(bob)
    if grant_button(bob_settings, app) or not grant_button(bob_settings, control):
        raise RuntimeError('Unexpected grant listing in a fresh Bob session after restart')
    if not grant_button(sign_in(alice), app):
        raise RuntimeError('Alice authorization absent after Bob self-revocation')
    alice_grant = renew(forge, 'resource_read', app, alice_grant)
    control_grant = renew(forge, 'resource_read', control, control_grant)
    expect(forge.request('GET', '/api/v1/repos/alice/private-fixture', token=alice_grant['access_token']),
           {200}, 'read Alice resource with her unaffected shared-app grant')
    expect(forge.request('GET', bob_repo, token=control_grant['access_token']),
           {200}, 'read Bob resource with his unaffected separate grant')
    record('consent_restart_independent_grants_survived', alice_same_app_repo_status=200,
           bob_other_app_repo_status=200, bob_revoked_grant_listed=False)
