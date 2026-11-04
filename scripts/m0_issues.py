"""Real M0 Issue contracts and bounded reconciliation; no workbench implementation."""
import base64
import secrets
import urllib.parse

from m0_response_loss import FAULT_ORIGIN, ResponseLoss
from m0_oauth import (Client, REQUESTS, authorize, expect, receipt, refresh)

REPO = '/api/v1/repos/alice/private-fixture'


def collect_pages(client, path, token, *, query=None, limit=50, issue_only=False):
    """Bounded reads; malformed, denied and repeating pages never become an empty list."""
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('Invalid probe page size')
    rows, pages, seen = [], [], set()
    for page in range(1, 21):
        params = dict(query or {}, page=page, limit=limit)
        result = expect(client.request('GET', path + '?' + urllib.parse.urlencode(params), token=token),
                        {200}, 'paginated repository objects')
        if not isinstance(result, list) or len(result) > limit:
            raise RuntimeError('Invalid paginated response shape or size')
        pages.append(len(result))
        for row in result:
            if not isinstance(row, dict) or type(row.get('id')) is not int or row['id'] <= 0:
                raise RuntimeError('Invalid paginated object identifier')
            if row['id'] in seen:
                raise RuntimeError('Duplicate object across pages; cannot claim complete pagination')
            if issue_only and row.get('pull_request') is not None:
                raise RuntimeError('Pull request leaked into an issues-only response')
            seen.add(row['id'])
        rows.extend(result)
        if not result:
            return rows, pages
    raise RuntimeError('Probe pagination exceeded its bounded fixture window')


def snapshot(issue):
    required = {'id', 'number', 'title', 'body', 'state', 'labels', 'assignees', 'content_version'}
    if not isinstance(issue, dict) or not required.issubset(issue):
        raise RuntimeError('Issue response is missing contract fields')
    if (any(type(issue[key]) is not int or issue[key] <= 0 for key in ('id', 'number'))
            or type(issue['content_version']) is not int or issue['content_version'] < 0
            or not isinstance(issue['title'], str) or not isinstance(issue['body'], str)
            or issue['state'] not in ('open', 'closed') or issue.get('pull_request') is not None):
        raise RuntimeError('Invalid Issue identity, state or content version')
    labels, assignees = issue['labels'], issue['assignees']
    if labels is not None and not isinstance(labels, list):
        raise RuntimeError('Invalid Issue labels')
    if assignees is not None and not isinstance(assignees, list):
        raise RuntimeError('Invalid Issue assignees')
    labels, assignees = labels or [], assignees or []  # Explicit nullable empty collections.
    if any(not isinstance(v, dict) or type(v.get('id')) is not int or v['id'] <= 0 for v in labels):
        raise RuntimeError('Invalid label identity')
    if any(not isinstance(v, dict) or not isinstance(v.get('login'), str) or not v['login'] for v in assignees):
        raise RuntimeError('Invalid assignee identity')
    milestone = issue.get('milestone')
    if milestone is not None and (not isinstance(milestone, dict) or type(milestone.get('id')) is not int or milestone['id'] <= 0):
        raise RuntimeError('Invalid milestone identity')
    return {**{k: issue[k] for k in ('id', 'number', 'title', 'body', 'state', 'content_version')},
            'labels': sorted(v['id'] for v in labels), 'assignees': sorted(v['login'] for v in assignees),
            'milestone': milestone['id'] if milestone is not None else None}


def validate_associations(catalog, payload):
    """M0 preflight from actual repository catalogs, not a product authorization layer."""
    for field in ('labels', 'assignees'):
        if field not in payload:
            continue
        values = payload[field]
        if not isinstance(values, list):
            raise ValueError('Association input must be a list')
        if field == 'labels':
            valid = all(type(v) is int and v > 0 and v in catalog[field] for v in values)
        else:
            valid = all(isinstance(v, str) and v in catalog[field] for v in values)
        if not valid or len(set(values)) != len(values):
            raise ValueError('Association is not allowed by the current repository catalog')
    if 'milestone' in payload:
        value = payload['milestone']
        if type(value) is not int or value < 0 or (value and value not in catalog['milestones']):
            raise ValueError('Milestone does not belong to this repository')


def reconcile_create(client, path, token, payload, author_id):
    """A synthetic unique marker scopes this evidence; no generic upstream idempotency claim."""
    rows, pages = collect_pages(client, path + '/issues', token,
                                query={'type': 'issues', 'state': 'all'}, issue_only=True)
    matches = [v for v in rows if v.get('title') == payload['title'] and v.get('body') == payload['body']
               and isinstance(v.get('user'), dict) and v['user'].get('id') == author_id]
    if len(matches) != 1:
        return {'state': 'unknown', 'matches': len(matches), 'pages': pages}
    issue = expect(client.request('GET', path + '/issues/' + str(matches[0]['number']), token=token),
                   {200}, 'reconcile matching Issue')
    current = snapshot(issue)
    if current['title'] != payload['title'] or current['body'] != payload['body']:
        return {'state': 'unknown', 'matches': 1, 'pages': pages}
    return {'state': 'observed', 'matches': 1, 'number': current['number'], 'pages': pages}


def catalogs(client, path, token):
    labels, _ = collect_pages(client, path + '/labels', token)
    milestones, _ = collect_pages(client, path + '/milestones', token, query={'state': 'all'})
    assignees = expect(client.request('GET', path + '/assignees', token=token), {200}, 'repository assignees')
    if not isinstance(assignees, list) or any(not isinstance(v, dict) or not isinstance(v.get('login'), str) for v in assignees):
        raise RuntimeError('Invalid assignee catalog')
    return {'labels': {v['id'] for v in labels}, 'milestones': {v['id'] for v in milestones},
            'assignees': {v['login'] for v in assignees}}


def create_issue(client, token, title, *, body='M0 synthetic Issue', **associations):
    payload = dict(title=title, body=body, **associations)
    validate_associations(catalogs(client, REPO, token), payload)
    result = expect(client.request('POST', REPO + '/issues', token=token, payload=payload), {201}, 'create Issue')
    current = read_issue(client, token, result['number'])
    if current['id'] != result['id'] or current['title'] != title or current['body'] != body:
        raise RuntimeError('Created Issue readback differs from requested content')
    for field, values in associations.items():
        expected = None if field == 'milestone' and values == 0 else sorted(values) if isinstance(values, list) else values
        if current[field] != expected:
            raise RuntimeError('Created Issue association readback differs')
    return current


def read_issue(client, token, number):
    return snapshot(expect(client.request('GET', REPO + '/issues/' + str(number), token=token),
                           {200}, 'Issue readback'))


def renew(client, purpose, app, tokens):
    successor = expect(refresh(purpose, client, app, tokens['refresh_token']), {200}, 'explicit phase refresh')
    receipt(purpose, client, app, successor)
    return successor


def fixture_pr(client, owner, record):
    repo = expect(client.request('GET', REPO, basic=owner), {200}, 'PR fixture repository')
    expect(client.request('POST', REPO + '/contents/m0-pr-fixture.txt', basic=owner, payload={
        'branch': repo['default_branch'], 'new_branch': 'm0-issue-list-pr',
        'content': base64.b64encode(b'M0 isolated PR fixture\n').decode(),
        'message': 'test: create isolated Issue-list PR fixture'}), {201}, 'PR fixture branch and file')
    pr = expect(client.request('POST', REPO + '/pulls', basic=owner, payload={
        'base': repo['default_branch'], 'head': 'm0-issue-list-pr', 'title': 'M0 PR must not be an Issue'}),
        {201}, 'local synthetic pull request')
    record('local_pr_fixture_created_by_ordinary_owner', number=pr['number'], target='isolated Gitea only')
    return pr


def issue_checks(owner, forge, credentials, record):
    alice, bob = credentials['forge']['alice'], credentials['forge']['bob']
    expect(forge.request('PUT', REPO + '/collaborators/bob', basic=alice, payload={'permission': 'write'}),
           {204}, 'ordinary collaborator fixture')
    other = expect(forge.request('POST', '/api/v1/user/repos', basic=alice,
                                payload={'name': 'other-fixture', 'private': True, 'auto_init': True}),
                   {201}, 'other repository fixture')
    other_path = '/api/v1/repos/alice/' + other['name']
    write_app, write, claims, _ = authorize('issue_write', forge, alice, 'm0-issues-write')
    read_app, read, _, _ = authorize('resource_read', forge, alice, 'm0-issues-read')
    bob_app, bob_tokens, _, _ = authorize('issue_write', forge, bob, 'm0-issues-collaborator')
    token = write['access_token']
    empty, _ = collect_pages(forge, REPO + '/issues', token, query={'state': 'all', 'type': 'issues'}, issue_only=True)
    if empty:
        raise RuntimeError('Fresh Issue repository was not empty')
    record('issue_empty_repository_is_a_real_empty_list')
    labels = [expect(forge.request('POST', REPO + '/labels', token=token, payload={'name': name, 'color': color}),
                     {201}, 'create label as ordinary repository writer')
              for name, color in [('m0-red', '#aa0000'), ('m0-blue', '#0000aa')]]
    milestones = [expect(forge.request('POST', REPO + '/milestones', token=token, payload={'title': name}),
                         {201}, 'create milestone as ordinary repository writer') for name in ('m0-one', 'm0-two')]
    foreign_label = expect(forge.request('POST', other_path + '/labels', token=token,
                                        payload={'name': 'm0-foreign', 'color': '#00aa00'}), {201}, 'foreign label fixture')
    foreign_milestone = expect(forge.request('POST', other_path + '/milestones', token=token,
                                            payload={'title': 'm0-foreign'}), {201}, 'foreign milestone fixture')
    catalog = catalogs(forge, REPO, token)
    if not {'alice', 'bob'}.issubset(catalog['assignees']) or 'carol' in catalog['assignees']:
        raise RuntimeError('Ordinary collaborator was not assignable')
    issues = [create_issue(forge, token, 'M0 Alpha primary', labels=[labels[0]['id']], assignees=['bob'], milestone=milestones[0]['id']),
              create_issue(forge, token, 'M0 Alpha secondary', labels=[labels[1]['id']], assignees=['alice'], milestone=milestones[1]['id']),
              create_issue(forge, token, 'M0 Beta closed', labels=[labels[0]['id']], assignees=['bob'], milestone=milestones[0]['id']),
              create_issue(forge, token, 'M0 Gamma empty associations'),
              create_issue(forge, token, 'M0 Alpha owner', labels=[labels[0]['id']], assignees=['alice'], milestone=milestones[0]['id'])]
    expect(forge.request('PATCH', REPO + '/issues/' + str(issues[2]['number']), token=token, payload={'state': 'closed'}),
           {201}, 'close filter fixture')
    pr = fixture_pr(forge, alice, record)
    rows, pages = collect_pages(forge, REPO + '/issues', token, query={'state': 'all', 'type': 'issues'}, limit=2, issue_only=True)
    if {v['id'] for v in rows} != {v['id'] for v in issues} or pages != [2, 2, 1, 0]:
        raise RuntimeError('Issue pages omitted or mixed fixture objects')
    mixed, _ = collect_pages(forge, REPO + '/issues', token, query={'state': 'all'})
    if not any(v['number'] == pr['number'] and v.get('pull_request') is not None for v in mixed):
        raise RuntimeError('Mixed-list PR control missing')
    record('issue_pagination_excludes_real_pr', pages=pages, issue_numbers=[v['number'] for v in rows], pr_number=pr['number'])
    filters = [('open', {'state': 'open'}, [0, 1, 3, 4]), ('closed', {'state': 'closed'}, [2]),
               ('keyword', {'q': 'Alpha'}, [0, 1, 4]), ('label', {'labels': labels[0]['name']}, [0, 2, 4]),
               ('assignee', {'assigned_by': 'bob'}, [0, 2]), ('milestone', {'milestones': str(milestones[0]['id'])}, [0, 2, 4]),
               ('combined', {'q': 'Alpha', 'labels': labels[0]['name'], 'assigned_by': 'bob',
                             'milestones': str(milestones[0]['id'])}, [0]), ('no_matches', {'q': 'm0-never-matches-9f481'}, [])]
    for name, params, indexes in filters:
        rows, _ = collect_pages(forge, REPO + '/issues', token,
                                query=dict({'state': 'all', 'type': 'issues'}, **params), limit=2, issue_only=True)
        if {v['id'] for v in rows} != {issues[i]['id'] for i in indexes}:
            raise RuntimeError('Issue filter returned a different fixture set: ' + name)
    record('issue_filters_match_state_keyword_label_assignee_milestone_and_combination', filters=[v[0] for v in filters])
    write = renew(forge, 'issue_write', write_app, write)
    bob_tokens = renew(forge, 'issue_write', bob_app, bob_tokens)
    token = write['access_token']
    target = issues[0]['number']
    stale = read_issue(forge, token, target)
    expect(forge.request('PATCH', REPO + '/issues/' + str(target), token=bob_tokens['access_token'],
                         payload={'body': 'M0 collaborator body', 'content_version': stale['content_version']}), {201}, 'collaborator versioned edit')
    concurrent = read_issue(forge, token, target)
    if concurrent['content_version'] <= stale['content_version']:
        raise RuntimeError('Body edit did not advance content_version')
    conflict = forge.request('PATCH', REPO + '/issues/' + str(target), token=token,
                             payload={'title': 'must not overwrite', 'body': 'must not overwrite', 'content_version': stale['content_version']})
    expect(conflict, {409}, 'stale version conflict')
    if read_issue(forge, token, target) != concurrent:
        raise RuntimeError('Stale edit partially overwrote concurrent changes')
    expect(forge.request('PATCH', REPO + '/issues/' + str(target), token=token,
                         payload={'title': 'M0 edited title', 'body': 'M0 edited body', 'content_version': concurrent['content_version']}),
           {201}, 'fresh versioned edit')
    edited = read_issue(forge, token, target)
    if edited['title'] != 'M0 edited title' or edited['body'] != 'M0 edited body':
        raise RuntimeError('Issue content edit was not persisted')
    for state in ('closed', 'open'):
        expect(forge.request('PATCH', REPO + '/issues/' + str(target), token=token, payload={'state': state}), {201}, 'Issue state transition')
        if read_issue(forge, token, target)['state'] != state:
            raise RuntimeError('Close/reopen state not persisted')
    record('issue_versioned_edit_stale_conflict_close_and_reopen', number=target, conflict_status=conflict[0],
           initial_content_version=stale['content_version'], concurrent_content_version=concurrent['content_version'])
    association_operations(forge, token, issues[3]['number'], labels, milestones, record)
    write = renew(forge, 'issue_write', write_app, write)
    read = renew(forge, 'resource_read', read_app, read)
    bob_tokens = renew(forge, 'issue_write', bob_app, bob_tokens)
    invalid_associations(forge, write['access_token'], foreign_label, foreign_milestone, record, repo_owner=alice)
    permission_and_deletion(forge, credentials, write['access_token'], read['access_token'], bob_tokens['access_token'], labels, milestones, record)
    for forward in (True, False):
        write = renew(forge, 'issue_write', write_app, write)
        timeout_reconciliation(forge, write['access_token'], int(claims['sub']), forward, record)
    write = renew(forge, 'issue_write', write_app, write)
    payload = {'title': 'M0 ambiguous ' + secrets.token_hex(8), 'body': 'M0 exact synthetic marker'}
    for _ in range(2):
        expect(forge.request('POST', REPO + '/issues', token=write['access_token'], payload=payload), {201}, 'intentional ambiguous fixtures')
    ambiguous = reconcile_create(forge, REPO, write['access_token'], payload, int(claims['sub']))
    if ambiguous['state'] != 'unknown' or ambiguous['matches'] != 2:
        raise RuntimeError('Ambiguous writes were incorrectly reconciled')
    record('ambiguous_create_reconciliation_stops_without_retry', **ambiguous, automatic_retries=0)


def association_operations(client, token, number, labels, milestones, record):
    path = REPO + '/issues/' + str(number)
    for method, payload, expected in [('POST', {'labels': [labels[0]['id']]}, [labels[0]['id']]),
                                      ('POST', {'labels': [labels[1]['id']]}, sorted(v['id'] for v in labels)),
                                      ('PUT', {'labels': [labels[1]['id']]}, [labels[1]['id']])]:
        validate_associations(catalogs(client, REPO, token), payload)
        expect(client.request(method, path + '/labels', token=token, payload=payload), {200}, 'label add/replace')
        if read_issue(client, token, number)['labels'] != expected:
            raise RuntimeError('Label mutation readback mismatch')
    expect(client.request('DELETE', path + '/labels/' + str(labels[1]['id']), token=token), {204}, 'remove one label')
    expect(client.request('POST', path + '/labels', token=token, payload={'labels': [labels[0]['id']]}), {200}, 'label clear fixture')
    expect(client.request('DELETE', path + '/labels', token=token), {204}, 'clear all labels')
    if read_issue(client, token, number)['labels']:
        raise RuntimeError('Labels not cleared')
    for method, payload, expected in [('POST', {'assignees': ['alice', 'bob']}, ['alice', 'bob']),
                                      ('DELETE', {'assignees': ['bob']}, ['alice'])]:
        validate_associations(catalogs(client, REPO, token), payload)
        expect(client.request(method, path + '/assignees', token=token, payload=payload), {201} if method == 'POST' else {200}, 'assignee add/remove')
        if read_issue(client, token, number)['assignees'] != expected:
            raise RuntimeError('Assignee mutation readback mismatch')
    for values, expected in [(['bob'], ['bob']), ([], [])]:
        expect(client.request('PATCH', path, token=token, payload={'assignees': values}), {201}, 'replace/clear assignees')
        if read_issue(client, token, number)['assignees'] != expected:
            raise RuntimeError('Assignees not replaced/cleared')
    for milestone in [milestones[0]['id'], milestones[1]['id'], 0]:
        validate_associations(catalogs(client, REPO, token), {'milestone': milestone})
        expect(client.request('PATCH', path, token=token, payload={'milestone': milestone}), {201}, 'assign/clear milestone')
        if read_issue(client, token, number)['milestone'] != (milestone or None):
            raise RuntimeError('Milestone readback mismatch')
    record('issue_label_assignee_milestone_add_replace_remove_clear', number=number)
    expect(client.request('PATCH', REPO + '/labels/' + str(labels[1]['id']), token=token,
                          payload={'name': 'm0-blue-edited', 'color': '#0000bb'}), {200}, 'edit repository label')
    label = expect(client.request('GET', REPO + '/labels/' + str(labels[1]['id']), token=token), {200}, 'edited label readback')
    if label['name'] != 'm0-blue-edited' or label['color'].lstrip('#') != '0000bb':
        raise RuntimeError('Label management edit not persisted')
    for state in ('closed', 'open'):
        expect(client.request('PATCH', REPO + '/milestones/' + str(milestones[1]['id']), token=token,
                              payload={'title': 'm0-two-edited', 'state': state}), {200}, 'edit milestone metadata')
        milestone = expect(client.request('GET', REPO + '/milestones/' + str(milestones[1]['id']), token=token),
                           {200}, 'edited milestone readback')
        rows, _ = collect_pages(client, REPO + '/milestones', token, query={'state': state})
        if (milestone['state'] != state or milestone['title'] != 'm0-two-edited'
                or milestones[1]['id'] not in {v['id'] for v in rows}):
            raise RuntimeError('Milestone metadata/state filter readback mismatch')
    record('repository_writer_label_edit_and_milestone_edit_close_reopen', role='ordinary repository owner')


def invalid_associations(client, token, foreign_label, foreign_milestone, record, *, repo_owner):
    catalog = catalogs(client, REPO, token)
    invalid = [('foreign_label', {'labels': [foreign_label['id']]}), ('missing_label', {'labels': [9223372036854770000]}),
               ('fractional_label', {'labels': [min(catalog['labels']) + 0.5]}),
               ('foreign_milestone', {'milestone': foreign_milestone['id']}),
               ('missing_milestone', {'milestone': 9223372036854770000}), ('missing_assignee', {'assignees': ['m0-user-does-not-exist']}),
               ('unassignable_assignee', {'assignees': ['carol']})]
    before_requests = len(REQUESTS)
    for _, payload in invalid:
        try:
            validate_associations(catalog, payload)
        except ValueError:
            pass
        else:
            raise RuntimeError('Invalid association passed the M0 repository preflight')
    if len(REQUESTS) != before_requests:
        raise RuntimeError('Rejected association caused a network request')
    record('invalid_issue_associations_rejected_before_network', cases=[name for name, _ in invalid], network_requests=0)
    for name, payload in invalid:
        issue = create_issue(client, token, 'M0 invalid input ' + name)
        path = REPO + '/issues/' + str(issue['number'])
        if 'labels' in payload:
            result = client.request('POST', path + '/labels', token=token, payload=payload)
        elif name == 'unassignable_assignee':
            result = client.request('POST', path + '/assignees', token=token, payload=payload)
        else:
            result = client.request('PATCH', path, token=token, payload=payload)
        current = read_issue(client, token, issue['number'])
        changed = [field for field in current if current[field] != issue[field]]
        rejected = result[0] in (400, 403, 404, 409, 422) and not changed
        record('upstream_invalid_association_' + name, 'pass' if rejected else 'gap',
               http_status=result[0], changed_fields=changed, local_preflight_rejects=True)
    issue = create_issue(client, token, 'M0 compound invalid edit')
    result = client.request('PATCH', REPO + '/issues/' + str(issue['number']), token=token,
                            payload={'title': 'M0 partial title must be observed', 'milestone': foreign_milestone['id']})
    current = read_issue(client, token, issue['number'])
    changed = [field for field in current if current[field] != issue[field]]
    record('upstream_compound_invalid_edit_readback', 'pass' if result[0] in (400, 403, 404, 422) and not changed else 'gap',
           http_status=result[0], changed_fields=changed, automatic_retries=0)
    # Keep deliberately invalid creates in separate repositories so their possible
    # bad state cannot contaminate positive-path or reconciliation evidence.
    for name, associations in [('foreign_label', {'labels': [foreign_label['id']]}),
                                ('foreign_milestone', {'milestone': foreign_milestone['id']}),
                                ('unassignable_assignee', {'assignees': ['carol']})]:
        repository = 'invalid-create-' + name.replace('_', '-')
        expect(client.request('POST', '/api/v1/user/repos', basic=repo_owner,
                              payload={'name': repository, 'private': True, 'auto_init': True}), {201}, 'isolated invalid-create fixture')
        path = '/api/v1/repos/alice/' + repository + '/issues'
        payload = dict(title='M0 invalid create ' + name, body='M0 raw invalid input fixture', **associations)
        result = client.request('POST', path, token=token, payload=payload)
        readback = client.request('GET', path + '?state=all&type=issues', token=token)
        count, attached_labels, attached_milestone = None, None, None
        if readback[0] == 200 and isinstance(readback[1], list):
            matches = [v for v in readback[1] if v.get('title') == payload['title']]
            count = len(matches)
            if count == 1:
                detail = expect(client.request('GET', path + '/' + str(matches[0]['number']), token=token),
                                {200}, 'invalid-create association readback')
                current = snapshot(detail)
                attached_labels, attached_milestone = current['labels'], current['milestone']
        rejected = result[0] in (400, 403, 404, 422) and count == 0
        record('upstream_invalid_create_' + name, 'pass' if rejected else 'gap', http_status=result[0],
               readback_status=readback[0], visible_matching_issues=count, attached_label_ids=attached_labels,
               attached_milestone_id=attached_milestone, local_preflight_rejects=True)
    for name, params in [('foreign_label', {'labels': foreign_label['name']}),
                          ('foreign_milestone', {'milestones': str(foreign_milestone['id'])})]:
        result = client.request('GET', REPO + '/issues?' + urllib.parse.urlencode(
            dict({'state': 'all', 'type': 'issues'}, **params)), token=token)
        count = len(result[1]) if result[0] == 200 and isinstance(result[1], list) else None
        empty_or_rejected = result[0] in (400, 404, 422) or count == 0
        record('upstream_unknown_filter_' + name, 'pass' if empty_or_rejected else 'gap',
               http_status=result[0], returned_issues=count, expected='empty or explicit rejection; never broaden filter')


def permission_and_deletion(client, credentials, token, read_token, bob_token, labels, milestones, record):
    alice, bob = credentials['forge']['alice'], credentials['forge']['bob']
    issue = create_issue(client, token, 'M0 read-only scope boundary')
    path = REPO + '/issues/' + str(issue['number'])
    if snapshot(expect(client.request('GET', path, token=read_token), {200}, 'read-scope Issue detail')) != issue:
        raise RuntimeError('Read-scope Issue detail differs from writer view')
    rows, _ = collect_pages(client, REPO + '/issues', read_token, query={'state': 'all', 'type': 'issues'}, issue_only=True)
    if issue['id'] not in {v['id'] for v in rows}:
        raise RuntimeError('Read-scope Issue list omitted fixture')
    for method, suffix, payload in [('POST', '/labels', {'labels': [labels[0]['id']]}),
                                     ('POST', '/assignees', {'assignees': ['bob']}),
                                     ('PATCH', '', {'title': 'must not edit', 'milestone': milestones[0]['id']}),
                                     ('DELETE', '', None)]:
        expect(client.request(method, path + suffix, token=read_token, payload=payload), {403}, 'read-only Issue mutation')
    if read_issue(client, token, issue['number']) != issue:
        raise RuntimeError('Read-only scope caused Issue mutation')
    expect(client.request('DELETE', path, token=bob_token), {403}, 'writer is not repository admin')
    expect(client.request('PUT', REPO + '/collaborators/bob', basic=alice, payload={'permission': 'read'}),
           {204}, 'downgrade ordinary collaborator')
    permission = expect(client.request('GET', REPO + '/collaborators/bob/permission', basic=alice),
                        {200}, 'read back collaborator permission')
    if permission.get('permission') != 'read':
        raise RuntimeError('Reader role fixture did not take effect')
    expect(client.request('GET', path, token=bob_token), {200}, 'reader may read Issue')
    for method, suffix, payload in [('PATCH', '', {'body': 'must not alter another author Issue'}),
                                     ('POST', '/labels', {'labels': [labels[0]['id']]}),
                                     ('POST', '/assignees', {'assignees': ['alice']}), ('DELETE', '', None)]:
        expect(client.request(method, path + suffix, token=bob_token, payload=payload), {403}, 'reader cannot manage another author Issue')
    if read_issue(client, token, issue['number']) != issue:
        raise RuntimeError('Read-role user altered another author Issue')
    reader_payload = {'title': 'M0 reader own Issue', 'body': 'M0 reader legitimate text',
                      'labels': [labels[0]['id']], 'milestone': milestones[0]['id'], 'assignees': ['alice']}
    reader_created = expect(client.request('POST', REPO + '/issues', token=bob_token, payload=reader_payload),
                            {201}, 'reader may create own Issue')
    current = read_issue(client, token, reader_created['number'])
    if current['title'] != reader_payload['title'] or current['body'] != reader_payload['body']:
        raise RuntimeError('Reader own Issue content was not persisted')
    metadata_ignored = not current['labels'] and not current['assignees'] and current['milestone'] is None
    record('reader_create_metadata_permission_is_not_implied_by_scope', 'gap',
           http_status=201, role='read', actual_label_ids=current['labels'], actual_assignees=current['assignees'],
           actual_milestone_id=current['milestone'], forbidden_metadata_ignored=metadata_ignored,
           expected='reject forbidden metadata or require explicit omission, not silent partial success')
    if not metadata_ignored:
        raise RuntimeError('Read-role user unexpectedly assigned forbidden metadata')
    record('reader_role_and_writer_delete_boundaries', reader_can_read=True, reader_can_create_own_issue=True,
           other_author_edit_status=403, metadata_manage_status=403, writer_delete_status=403)
    expect(client.request('POST', '/api/v1/user/repos', basic=bob,
                          payload={'name': 'bob-private-fixture', 'private': True, 'auto_init': True}), {201}, 'other-user private repository')
    foreign = '/api/v1/repos/bob/bob-private-fixture'
    for method, suffix, payload in [('GET', '/issues', None), ('POST', '/issues', {'title': 'must not create'}),
                                     ('GET', '/labels', None), ('GET', '/milestones', None), ('GET', '/assignees', None)]:
        expect(client.request(method, foreign + suffix, token=token, payload=payload), {403, 404}, 'cross-user private resource')
    expect(client.request('DELETE', REPO + '/collaborators/bob', basic=alice), {204}, 'revoke collaborator')
    for method, suffix, payload in [('GET', '/issues', None), ('GET', '/issues/' + str(issue['number']), None),
                                     ('PATCH', '/issues/' + str(issue['number']), {'title': 'must not edit after revoke'}),
                                     ('POST', '/issues/' + str(issue['number']) + '/labels', {'labels': [labels[0]['id']]})]:
        expect(client.request(method, REPO + suffix, token=bob_token, payload=payload), {403, 404}, 'revoked collaborator Issue access')
    if read_issue(client, token, issue['number']) != issue:
        raise RuntimeError('Revoked collaborator altered Issue')
    record('issue_read_only_cross_user_and_revoked_collaborator_rejected', number=issue['number'])
    deleted = create_issue(client, token, 'M0 deleted Issue')
    deleted_path = REPO + '/issues/' + str(deleted['number'])
    expect(client.request('DELETE', deleted_path, token=token), {204}, 'delete own Issue as repository owner')
    for method, payload in [('GET', None), ('PATCH', {'title': 'must not resurrect deleted Issue'})]:
        expect(client.request(method, deleted_path, token=token, payload=payload), {404}, 'deleted Issue remains missing')
    label = expect(client.request('POST', REPO + '/labels', token=token, payload={'name': 'm0-delete-label', 'color': '#aaaa00'}), {201}, 'deletable label')
    milestone = expect(client.request('POST', REPO + '/milestones', token=token, payload={'title': 'm0-delete-milestone'}), {201}, 'deletable milestone')
    related = create_issue(client, token, 'M0 deleted metadata', labels=[label['id']], milestone=milestone['id'])
    expect(client.request('DELETE', REPO + '/labels/' + str(label['id']), token=token), {204}, 'delete label')
    expect(client.request('DELETE', REPO + '/milestones/' + str(milestone['id']), token=token), {204}, 'delete milestone')
    current = read_issue(client, token, related['number'])
    if current['labels'] or current['milestone'] is not None:
        raise RuntimeError('Deleted metadata still attached to Issue')
    for suffix in ('/labels/' + str(label['id']), '/milestones/' + str(milestone['id'])):
        expect(client.request('GET', REPO + suffix, token=token), {404}, 'deleted metadata lookup')
    gone = expect(client.request('POST', '/api/v1/user/repos', basic=alice,
                                 payload={'name': 'delete-fixture', 'private': True, 'auto_init': True}), {201}, 'deletable repository')
    gone_path = '/api/v1/repos/alice/' + gone['name']
    gone_issue = expect(client.request('POST', gone_path + '/issues', token=token, payload={'title': 'M0 deleted repository Issue'}), {201}, 'Issue in deletable repository')
    expect(client.request('DELETE', gone_path, basic=alice), {204}, 'ordinary owner deletes synthetic repository')
    expect(client.request('GET', gone_path + '/issues/' + str(gone_issue['number']), token=token), {404}, 'deleted repository Issue lookup')
    record('deleted_issue_label_milestone_and_repository_are_not_cached_as_valid', deleted_issue=deleted['number'])


def timeout_reconciliation(client, token, author_id, forward, record):
    payload = {'title': 'M0 response loss ' + secrets.token_hex(8), 'body': 'M0 isolated request marker ' + secrets.token_hex(16)}
    with ResponseLoss('issue_create', REPO + '/issues', token, payload, forward=forward) as fault:
        try:
            Client(FAULT_ORIGIN).request('POST', REPO + '/issues', token=token, payload=payload, timeout=1)
        except OSError as exc:
            error_type = type(exc).__name__
        else:
            raise RuntimeError('Fault request did not really time out')
    if fault.error_type or fault.attempts != 1 or fault.forwarded != int(forward):
        raise RuntimeError('Fault transport did not match its bounded scenario')
    if forward and fault.upstream_status != 201:
        raise RuntimeError('Response-loss scenario did not create its upstream Issue')
    before = len(REQUESTS)
    result = reconcile_create(client, REPO, token, payload, author_id)
    if any(v['method'] != 'GET' for v in REQUESTS[before:]):
        raise RuntimeError('Reconciliation attempted another write')
    if result['state'] != ('observed' if forward else 'unknown') or result['matches'] != int(forward):
        raise RuntimeError('Timeout reconciliation classified the wrong outcome')
    record('issue_timeout_after_commit_reconciled' if forward else 'issue_timeout_without_visible_write_stays_unknown',
           caller_error=error_type, request_attempts=fault.attempts, upstream_writes=fault.forwarded,
           upstream_status=fault.upstream_status, reconciliation=result, automatic_retries=0, fault_listener_stopped=True)
