#!/usr/bin/env python3
"""Run the fixed M0 G24–G26 retention slice on an empty, locally owned batch."""
import base64
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
import re
import secrets
import sys
import time
from urllib.parse import urljoin, urlsplit

from m0_local import ROOT, RUNTIME, compose, state, write_private
from m0_oauth import Client, Forms, REQUESTS, expect
from m0_oci import team
from m0_registry import (ACCEPT, OCI_MANIFEST, ORG, ORIGIN, challenge, create_pat, fixture, location, mint,
                         put_manifest, read_blob, read_manifest, sha, upload_blob)
from m0_scope import PROFILE_PATH

BUILD_ALT = 'm0-build-alt'
RELEASE = 'm0-release-org'
RELEASE_IMAGE = RELEASE + '/m0-probe'
RELEASE_REPO = '/api/v1/repos/' + RELEASE + '/m0-private-source'
PRUNE_TAG = 'm0-prune-control'
DENIED = {401, 403, 404}
REPORT = RUNTIME / 'oci-retention-results.json'


def ordinary_users(owner, client):
    output = compose(owner, 'exec', '-T', 'forge', 'gitea', '--config', '/etc/gitea/app.ini', 'admin', 'user',
                     'create', '--username', 'm0-admin', '--email', 'admin-forge@example.test', '--random-password',
                     '--random-password-length', '32', '--must-change-password=false', '--admin').stdout.decode()
    match = re.search(r"generated random password is '(.*)'", output)
    if not match:
        raise RuntimeError('Bootstrap password format differed; output withheld')
    users = {'admin': ('m0-admin', match.group(1))}
    for name in ('alice', 'bob', 'carol', 'dave'):
        password = secrets.token_urlsafe(32)
        row = expect(client.request('POST', '/api/v1/admin/users', basic=users['admin'], payload={
            'username': name, 'email': name + '@example.test', 'password': password,
            'must_change_password': False, 'send_notify': False}), {201}, 'create ordinary fixture account')
        if row.get('is_admin') is not False or row.get('login') != name:
            raise RuntimeError('Unexpected fixture account identity or privilege')
        users[name] = (name, password)
    return users


def team_member(client, owner, organization, role, units, username):
    values = team(client, owner, role, units, organization=organization)
    path = '/api/v1/teams/' + str(values['id']) + '/members/' + username
    expect(client.request('PUT', path, basic=owner), {204}, 'assign fixture team membership')
    expect(client.request('GET', path, basic=owner), {200}, 'read back fixture team membership')
    return values


def prepare_organizations(client, users):
    organizations = {}
    for namespace, owner in ((ORG, users['dave']), (BUILD_ALT, users['dave']), (RELEASE, users['alice'])):
        expect(client.request('POST', '/api/v1/orgs', basic=owner,
                              payload={'username': namespace, 'visibility': 'private'}),
               {201}, 'create private fixture organization')
        row = expect(client.request('GET', '/api/v1/orgs/' + namespace, basic=owner),
                     {200}, 'read back fixture organization')
        if row['username'] != namespace or row['visibility'] != 'private':
            raise RuntimeError('Fixture organization is not private')
        organizations[namespace] = {'id': row['id'], 'visibility': row['visibility']}
    for namespace in (ORG, BUILD_ALT):
        result = team_member(client, users['dave'], namespace, 'm0-build-writer', {'repo.packages': 'write'}, 'bob')
        organizations[namespace]['bob_team_units'] = result['units_map']
    deploy_team = team_member(client, users['alice'], RELEASE, 'm0-deploy-reader', {'repo.packages': 'read'}, 'carol')
    organizations[RELEASE]['carol_team_units'] = deploy_team['units_map']
    repo = expect(client.request('POST', '/api/v1/orgs/' + RELEASE + '/repos', basic=users['alice'],
                                 payload={'name': 'm0-private-source', 'private': True, 'auto_init': True}),
                  {201}, 'create source fixture')
    expect(client.request('PUT', RELEASE_REPO + '/collaborators/bob', basic=users['alice'],
                          payload={'permission': 'read'}), {204}, 'assign external source collaborator')
    external_membership = client.request('GET', '/api/v1/orgs/' + RELEASE + '/members/bob', basic=users['alice'])
    expect(external_membership, {404}, 'confirm collaborator is not an organization member')
    external_repo = expect(client.request('GET', RELEASE_REPO, basic=users['bob']), {200}, 'external source visibility')
    if external_repo['id'] != repo['id'] or not external_repo['private']:
        raise RuntimeError('Source fixture identity or private visibility differs')
    organizations[RELEASE].update(source_repo_id=repo['id'], bob_source_read=200,
                                  bob_organization_membership=external_membership[0])
    return organizations, repo


def source_fixture(client, alice, label):
    path = RELEASE_REPO + '/contents/' + label + '.txt'
    row = expect(client.request('POST', path, basic=alice, payload={
        'content': base64.b64encode(('RadishForge M0 ' + label + '\n').encode()).decode(),
        'message': 'test: record isolated ' + label}), {201}, 'prepare exact source commit')
    source = row['commit']['sha']
    expect(client.request('GET', RELEASE_REPO + '/git/commits/' + source, basic=alice),
           {200}, 'read back exact fixture commit')
    return source, fixture(source, label)


def publish(client, token, image, tag, parts):
    config, layer, manifest = parts
    for blob in (config, layer):
        upload_blob(client, token, blob, image=image)
    return put_manifest(client, token, tag, manifest, image=image)


def verify_image(client, token, image, reference, parts):
    config, layer, manifest = parts
    digest, value, _ = read_manifest(client, token, reference, image=image, expected=manifest)
    for descriptor, blob in ((value['config'], config), (value['layers'][0], layer)):
        if (descriptor['digest'], descriptor['size']) != (sha(blob), len(blob)):
            raise RuntimeError('Fixture descriptor identity or size differs')
        read_blob(client, token, descriptor['digest'], image=image, expected=blob)
    return digest


def describe(parts):
    return {name: {'digest': sha(blob), 'size': len(blob)}
            for name, blob in zip(('config', 'layer', 'manifest'), parts)}


def denial(result, label, fixture_bytes=None):
    body = expect(result, DENIED, label)
    if (result[2] or body.headers.get('Docker-Upload-Uuid') or body.headers.get('Docker-Content-Digest')
            or (fixture_bytes and fixture_bytes in body.data)):
        raise RuntimeError(f'{label}: rejected request exposed fixture bytes or an upload receipt')
    return result[0]


def deny_pull(client, token, image, parts):
    _, layer, manifest = parts
    return {
        'manifest': denial(client.request('GET', '/v2/' + image + '/manifests/' + sha(manifest),
                                          token=token, binary=True, headers=ACCEPT), 'deny exact manifest', manifest),
        'blob': denial(client.request('GET', '/v2/' + image + '/blobs/' + sha(layer),
                                      token=token, binary=True), 'deny exact blob', layer),
    }


def upload_receipt(client, token, image):
    return client.request('POST', '/v2/' + image + '/blobs/uploads/', token=token, raw=b'', binary=True)


class NativeForm(HTMLParser):
    """Read default select/checkbox states and links from the fixed native page."""
    def __init__(self, page):
        super().__init__()
        self.select, self.values, self.links = None, {}, []
        self.feed(page)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and 'href' in attrs:
            self.links.append(attrs['href'])
        if tag == 'select':
            self.select = attrs.get('name')
        if tag == 'option' and self.select and 'selected' in attrs:
            self.values[self.select] = attrs.get('value', '')
        if tag == 'input' and attrs.get('name'):
            value = ('true' if 'checked' in attrs else 'false') if attrs.get('type') == 'checkbox' else attrs.get('value', '')
            self.values[attrs['name']] = value

    def handle_endtag(self, tag):
        if tag == 'select':
            self.select = None


def login(account):
    browser = Client(ORIGIN, browser_session=True)
    # This fixed Gitea release checks the request origin on native form submissions.
    browser.opener.addheaders.append(('Origin', ORIGIN))
    response = browser.request('GET', '/user/login')
    page = expect(response, {200}, 'native login form')
    form, = (f for f in Forms(page).forms if 'password' in f['fields'])
    action = urljoin(response[3], form['action'])
    expect(browser.request('POST', action, form={**form['fields'], 'user_name': account[0], 'password': account[1]}),
           {200}, 'native login')
    return browser


def save_rule(browser):
    settings = '/org/' + RELEASE + '/settings/packages'
    add = settings + '/rules/add'
    page = expect(browser.request('GET', add), {200}, 'native organization rule form')
    form, = (f for f in Forms(page).forms if 'keep_pattern' in f['fields'])
    if urljoin(ORIGIN + add, form['action']) != ORIGIN + add:
        raise RuntimeError('Cleanup form action differs from the fixed organization')
    values = {'enabled': 'true', 'type': 'container', 'keep_count': '0', 'remove_days': '0',
              'keep_pattern': 'm0-retain-(a|b)', 'remove_pattern': 'm0-retain-(a|b)|' + PRUNE_TAG}
    expect(browser.request('POST', add, form=dict(values, action='save', id='0')),
           {200}, 'save exact native cleanup rule')
    listing = expect(browser.request('GET', settings), {200}, 'read back native cleanup rules')
    paths = {urlsplit(urljoin(ORIGIN + settings, href)).path for href in NativeForm(listing).links}
    rule, = (path for path in paths if re.fullmatch(re.escape(settings) + r'/rules/\d+', path))
    actual = NativeForm(expect(browser.request('GET', rule), {200}, 'native rule values')).values
    if any(actual.get(key) != value for key, value in values.items()) or actual.get('match_full_name') != 'false':
        raise RuntimeError('Cleanup rule did not preserve the requested version filters')
    preview = expect(browser.request('GET', rule + '/preview'), {200}, 'native cleanup preview')
    if not re.search(r'>\s*' + PRUNE_TAG + r'\s*<', preview) or re.search(r'>\s*m0-retain-[ab]\s*<', preview):
        raise RuntimeError('Native preview did not show the expected control and exclude both retained tags')
    return {'rule_id': int(rule.rsplit('/', 1)[1]), 'values': values, 'match_full_name': False,
            'preview_delete_tag': PRUNE_TAG, 'preview_retained_tags_excluded': True}


def cron_task(client, admin):
    tasks = expect(client.request('GET', '/api/v1/admin/cron?limit=100', basic=admin), {200}, 'read cleanup cron')
    row, = (task for task in tasks if task['name'] == 'cleanup_packages')
    return row


def run(owner, record):
    api = Client(ORIGIN)
    expect(api.request('GET', '/api/healthz'), {200}, 'fixed local Gitea health')
    users = ordinary_users(owner, api)
    write_private(RUNTIME / 'oci-retention-users.json', json.dumps(users))
    provider = expect(api.request('GET', '/api/v1/version', basic=users['admin']), {200}, 'read fixed local version')
    if provider['version'] != '28.2.0':
        raise RuntimeError('Authenticated Gitea version differs from the fixed candidate')
    organizations, repo = prepare_organizations(api, users)
    record('fixture_roles_and_source_repository', organizations=organizations)
    record('registry_challenge', challenge=challenge(api))
    pats = {}
    tokens = {}
    for key, username, purpose, request_actions in (
            ('release_write', 'alice', 'write', 'pull,push'), ('deploy_read', 'carol', 'read', 'pull'),
            ('build_write', 'bob', 'write', 'pull'), ('build_read', 'bob', 'read', 'pull,push'),
            ('build_control_read', 'dave', 'read', 'pull')):
        pats[key] = create_pat(api, users[username], purpose, 'm0-retention-' + key.replace('_', '-'))
        tokens[key], metadata = mint(api, pats[key], actions=request_actions)
        record('issued_' + key, requested_actions=request_actions, metadata=metadata)
    admin = tokens['release_write']
    deploy = tokens['deploy_read']
    builder = tokens['build_write']
    _, build_parts = source_fixture(api, users['alice'], 'm0-build-source')
    for namespace in (ORG, BUILD_ALT):
        image = namespace + '/m0-probe'
        digest = publish(api, builder, image, 'm0-build-check', build_parts)
        verify_image(api, tokens['build_control_read'], image, digest, build_parts)
        verify_image(api, builder, image, digest, build_parts)
        receipt = upload_receipt(api, builder, image)
        expect(receipt, {202}, 'begin allowed empty upload with same build Bearer')
        upload = location(receipt[2], image=image)
        expect(api.request('DELETE', upload, token=builder, binary=True), {204}, 'cancel allowed empty upload')
        expect(api.request('GET', upload, token=builder, binary=True), {404}, 'read back empty upload removal')
        record('same_build_bearer_allowed', 'gap', image=image, digest=digest, read_status=200,
               upload_status=202, upload_removed_status=404,
               detail='pull query preserved write scope; the same credential works at both allowed owners')
    verify_image(api, tokens['build_read'], ORG + '/m0-probe', sha(build_parts[2]), build_parts)
    record('read_pat_cannot_upload_in_own_writer_namespace', image=ORG + '/m0-probe', read_status=200,
           upload_status=denial(upload_receipt(api, tokens['build_read'], ORG + '/m0-probe'), 'read scope upload'))

    images = {}
    backup = RUNTIME / 'oci-retention-backup'
    backup.mkdir(mode=0o700)
    for label, tag in (('a', 'm0-retain-a'), ('b', 'm0-retain-b'), ('control', PRUNE_TAG)):
        source, parts = source_fixture(api, users['alice'], 'm0-release-' + label)
        images[label] = parts
        if label in ('a', 'b'):
            for name, blob in zip(('config', 'layer', 'manifest'), parts):
                write_private(backup / (label + '-' + name), blob)
        digest = publish(api, admin, RELEASE_IMAGE, tag, parts)
        verify_image(api, deploy, RELEASE_IMAGE, digest, parts)
        verify_image(api, deploy, RELEASE_IMAGE, tag, parts)
        record('release_fixture_' + label, image=RELEASE_IMAGE, source_sha=source, tag=tag, descriptors=describe(parts))
    a, b, control = (images[key] for key in ('a', 'b', 'control'))
    a_digest = sha(a[2])
    before_link = deny_pull(api, builder, RELEASE_IMAGE, a)
    packages = '/api/v1/packages/' + RELEASE + '/container/m0-probe'
    expect(api.request('POST', packages + '/-/link/' + repo['name'], basic=users['alice']),
           {201}, 'link release package to private source')
    link = expect(api.request('GET', packages + '/m0-retain-a', basic=users['alice']), {200}, 'read back package link')
    if link.get('repository', {}).get('id') != repo['id']:
        raise RuntimeError('Package association does not match source fixture')
    record('build_bearer_denied_in_private_release_owner', image=RELEASE_IMAGE, known_digest=a_digest,
           prior_to_link=before_link, paired_source_repository_id=repo['id'], after_link=deny_pull(api, builder, RELEASE_IMAGE, a),
           upload_status=denial(upload_receipt(api, builder, RELEASE_IMAGE), 'external collaborator upload'))
    anonymous = deny_pull(api, None, RELEASE_IMAGE, a)
    record('anonymous_and_deployment_reader_boundaries', image=RELEASE_IMAGE, anonymous=anonymous,
           deploy_read_status=200, deploy_upload_status=denial(upload_receipt(api, deploy, RELEASE_IMAGE), 'deploy upload'),
           deploy_delete_status=denial(api.request('DELETE', '/v2/' + RELEASE_IMAGE + '/manifests/' + a_digest,
                                                  token=deploy, binary=True), 'deploy manifest delete'))
    verify_image(api, deploy, RELEASE_IMAGE, a_digest, a)
    put_manifest(api, admin, 'm0-active', a[2], image=RELEASE_IMAGE)
    verify_image(api, deploy, RELEASE_IMAGE, 'm0-active', a)
    put_manifest(api, admin, 'm0-active', b[2], image=RELEASE_IMAGE)
    verify_image(api, deploy, RELEASE_IMAGE, 'm0-active', b)
    verify_image(api, deploy, RELEASE_IMAGE, a_digest, a)
    browser = login(users['alice'])
    record('native_cleanup_rule_saved_and_previewed', **save_rule(browser))

    previous = cron_task(api, users['admin'])
    expect(api.request('POST', '/api/v1/admin/cron/cleanup_packages', basic=users['admin']),
           {204}, 'trigger exact cleanup once')
    deadline = time.monotonic() + 45
    while True:
        after = cron_task(api, users['admin'])
        current = api.request('GET', '/v2/' + RELEASE_IMAGE + '/manifests/' + PRUNE_TAG,
                              token=deploy, binary=True, headers=ACCEPT)
        if after['exec_times'] > previous['exec_times'] and current[0] == 404:
            break
        if time.monotonic() >= deadline:
            raise RuntimeError('Cleanup trigger did not remove the previewed control within 45 seconds')
        time.sleep(1)
    for label, parts in (('a', a), ('b', b)):
        verify_image(api, deploy, RELEASE_IMAGE, 'm0-retain-' + label, parts)
        verify_image(api, deploy, RELEASE_IMAGE, sha(parts[2]), parts)
    control_digest = api.request('GET', '/v2/' + RELEASE_IMAGE + '/manifests/' + sha(control[2]),
                                 token=deploy, binary=True, headers=ACCEPT)
    control_blob = api.request('GET', '/v2/' + RELEASE_IMAGE + '/blobs/' + sha(control[0]), token=deploy, binary=True)
    control_layer = api.request('GET', '/v2/' + RELEASE_IMAGE + '/blobs/' + sha(control[1]), token=deploy, binary=True)
    record('real_cleanup_removes_control_tag_and_keeps_release_bytes', trigger_status=204,
           previous_execution_count=previous['exec_times'], execution_count=after['exec_times'],
           prune_tag_status=current[0], prune_digest_status=control_digest[0], prune_config_status=control_blob[0],
           prune_layer_status=control_layer[0],
           retained_a=describe(a), retained_b=describe(b))

    _, sacrificial = source_fixture(api, users['alice'], 'm0-deletion-control')
    disposable = RELEASE + '/m0-delete-check'
    disposable_tag = 'm0-deletion-check'
    digest = publish(api, admin, disposable, disposable_tag, sacrificial)
    publish(api, admin, disposable, 'm0-overwrite-control', b)
    verify_image(api, deploy, disposable, 'm0-overwrite-control', b)
    registry_root = '/v2/' + disposable
    package_root = '/api/v1/packages/' + RELEASE + '/container/m0-delete-check'
    for name, method, path, raw in (
            ('registry_overwrite', 'PUT', registry_root + '/manifests/' + disposable_tag, b[2]),
            ('registry_manifest_delete', 'DELETE', registry_root + '/manifests/' + digest, None),
            ('registry_blob_delete', 'DELETE', registry_root + '/blobs/' + sha(sacrificial[0]), None)):
        result = api.request(method, path, token=builder, raw=raw,
                             content_type=OCI_MANIFEST if raw is not None else None, binary=True)
        status = denial(result, name)
        verify_image(api, deploy, disposable, disposable_tag, sacrificial)
        record(name, target=disposable, denied_status=status, independent_read_status=200)
    for name, path in (('rest_version_delete', package_root + '/' + disposable_tag), ('rest_package_delete', package_root)):
        status = denial(api.request('DELETE', path, basic=('bob', pats['build_write']['value']), binary=True), name)
        verify_image(api, deploy, disposable, disposable_tag, sacrificial)
        record(name, target=disposable, denied_status=status, independent_read_status=200)
    native_path = '/' + RELEASE + '/-/packages/container/m0-delete-check/' + disposable_tag
    reader = login(users['carol'])
    expect(reader.request('GET', native_path), {200}, 'native deploy reader can load exact package page')
    denied = reader.request('POST', native_path, form={}, binary=True)
    if denied[0] != 404 or urlsplit(denied[3]).path != native_path:
        raise RuntimeError('Native delete did not report a denial at the exact package path')
    verify_image(api, deploy, disposable, disposable_tag, sacrificial)
    record('native_deploy_reader_delete_denied', target=disposable, denied_status=denied[0], independent_read_status=200)

    restored = tuple((backup / ('a-' + name)).read_bytes() for name in ('config', 'layer', 'manifest'))
    if describe(restored) != describe(a):
        raise RuntimeError('Independent restore copy digest or size changed')
    absent_path = '/v2/' + RELEASE_IMAGE + '/manifests/' + a_digest
    expect(api.request('DELETE', absent_path, token=admin, binary=True), {202}, 'approved synthetic exception delete')
    missing = api.request('GET', absent_path, token=deploy, binary=True, headers=ACCEPT)
    expect(missing, {404}, 'original Digest missing before restore')
    verify_image(api, deploy, RELEASE_IMAGE, 'm0-retain-b', b)
    record('admin_exception_delete_and_missing_digest_stop', image=RELEASE_IMAGE, delete_status=202,
           missing_status=missing[0], original_digest=a_digest, healthy_release_digest=sha(b[2]))
    if publish(api, admin, RELEASE_IMAGE, 'm0-retain-a', restored) != a_digest:
        raise RuntimeError('Restore produced a different manifest digest')
    verify_image(api, deploy, RELEASE_IMAGE, a_digest, restored)
    verify_image(api, deploy, RELEASE_IMAGE, 'm0-retain-a', restored)
    verify_image(api, deploy, RELEASE_IMAGE, 'm0-retain-b', b)
    record('original_digest_restored_and_independently_read', image=RELEASE_IMAGE, tag='m0-retain-a',
           descriptors=describe(restored), independent_read_status=200, product_rollback_executed=False)


def main():
    owner = state()
    settings = owner.get('effective_provider_settings', {})
    if (owner.get('context') != 'orbstack' or owner.get('legacy_query_auth')
            or owner.get('auth_profile_sha256') != hashlib.sha256(PROFILE_PATH.read_bytes()).hexdigest()
            or set(settings) != {'forge', 'idp'}
            or any(item.get('actions_enabled') is not False for item in settings.values())):
        raise RuntimeError('Fresh prepared OrbStack batch with verified Actions-off configuration required')
    marker = RUNTIME / 'contract-started.json'
    with marker.open('x') as stream:
        marker.chmod(0o600)
        json.dump({'project': owner['project'], 'mode': 'oci-retention'}, stream)
    report = {'project': owner['project'], 'context': owner['context'], 'server': owner['server'],
              'source_sha256': {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                                for path in (ROOT / 'scripts/m0_oci_retention.py', ROOT / 'scripts/m0_oci.py',
                                             ROOT / 'scripts/m0_registry.py', ROOT / 'scripts/m0_oauth.py',
                                             ROOT / 'tests/contracts/m0/compose.yaml')},
              'provider_config_sha256': settings['forge']['config_sha256'], 'runner_started': False,
              'results': []}

    def record(name, status='pass', **details):
        result = dict(name=name, status=status, observed_at_utc=datetime.now(timezone.utc).isoformat(), **details)
        report['results'].append(result)
        report['requests'] = [
            {key: re.sub(r'/blobs/uploads/[^/]+$', '/blobs/uploads/{id}', value)
             if key in ('path', 'final_path') else value for key, value in request.items()}
            for request in REQUESTS
        ]
        write_private(REPORT, json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(result, ensure_ascii=False), flush=True)

    try:
        run(owner, record)
    except Exception as error:
        report['exit_code'] = 1
        record('oci_retention_interrupted', 'error', error_type=type(error).__name__)
        print(f'Interrupted at {sys.exc_info()[2].tb_next.tb_lineno}; diagnostic withheld from report.', file=sys.stderr)
        raise
    report['exit_code'] = 2 if any(result['status'] == 'gap' for result in report['results']) else 0
    record('oci_retention_completed', operated_days=0, runtime_origin=ORIGIN, original_gap_ids_preserved=['M0-G24', 'M0-G25'])
    return report['exit_code']


if __name__ == '__main__':
    sys.exit(main())
