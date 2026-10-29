#!/usr/bin/env python3
"""Read-only governance checks. Python standard library only; no Git writes."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit

REQUIRED = (
    'README.md', 'AGENTS.md', 'CLAUDE.md', 'CONTRIBUTING.md',
    'SECURITY.md', 'CODE_OF_CONDUCT.md', '.editorconfig', '.gitattributes',
    '.gitignore', '.github/PULL_REQUEST_TEMPLATE.md',
    '.github/ISSUE_TEMPLATE/bug-report.md',
    '.github/ISSUE_TEMPLATE/change-proposal.md',
    '.github/repository-settings.json', '.github/rulesets/README.md',
    '.github/rulesets/master-protection.json',
    '.github/rulesets/master-protection-ci.json',
    'docs/governance/repository-governance.md', 'docs/governance/rulesets.md',
    'docs/governance/collaboration.md', 'docs/governance/documentation.md',
    'docs/adr/0002-repository-governance.md', 'docs/status/current.md',
    'docs/planning/tasks.md', 'docs/planning/acceptance.md',
    'scripts/README.md', 'scripts/check-repo.py',
    'scripts/tests/test_check_repo.py',
)
SKIP_DIRS = {'.git', '.local', '.codex', '.claude', '.aws', '.idea', '.vscode',
             'node_modules', '__pycache__', '.vite', 'coverage',
             'playwright-report', 'test-results'}
ROOT_OUTPUTS = {'bin', 'dist', 'build', 'runtime', 'backups', 'tmp'}
TEXT_SUFFIXES = {'.md', '.json', '.py', '.go', '.ts', '.tsx', '.js', '.jsx',
                 '.yml', '.yaml', '.sh', '.css', '.html', '.toml', '.txt'}
COMMIT = re.compile(r'^(feat|fix|docs|refactor|test|chore|ci|build|perf|revert)'
                    r'(\([a-z0-9._/-]+\))?!?: \S.*$')


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], capture_output=True)


def inventory(root):
    """Use Git's tracked + untracked set when this exact root is a repository."""
    root = root.resolve()
    try:
        probe = git(root, 'rev-parse', '--show-toplevel')
    except FileNotFoundError:
        probe = None
    if probe and probe.returncode == 0 and Path(os.fsdecode(probe.stdout).strip()).resolve() == root:
        result = git(root, 'ls-files', '--cached', '--others', '--exclude-standard', '-z')
        if result.returncode:
            raise ValueError('Git file inventory failed')
        return sorted({os.fsdecode(x) for x in result.stdout.split(b'\0') if x}), True
    if (root / '.git').exists():
        raise ValueError('A .git entry exists but Git cannot inspect this repository')
    files = []
    for current, dirs, names in os.walk(root, followlinks=False):
        base = Path(current)
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS
                   and not (base == root and d in ROOT_OUTPUTS)
                   and not (base / d).is_symlink()]
        files.extend(str((base / name).relative_to(root)) for name in names)
    return sorted(files), False


def policy_errors(root):
    errors = []
    try:
        settings = json.loads((root / '.github/repository-settings.json').read_text())
        expected = dict(default_branch='master', allow_merge_commit=True,
                        allow_rebase_merge=True, allow_squash_merge=False,
                        allow_auto_merge=False, delete_branch_on_merge=False)
        if settings != expected:
            errors.append('repository settings differ from the agreed branch/merge policy')
        stages = []
        for name in ('master-protection.json', 'master-protection-ci.json'):
            data = json.loads((root / '.github/rulesets' / name).read_text())
            stages.append(data)
            if (data['target'] != 'branch' or data['enforcement'] != 'disabled'
                    or data['bypass_actors'] != []
                    or data['conditions'] != {'ref_name': {'include': ['refs/heads/master'], 'exclude': []}}):
                errors.append(name + ': target, disabled staging, or bypass policy drift')
            rules = {r['type']: r for r in data['rules']}
            expected_types = {'deletion', 'non_fast_forward', 'pull_request'}
            if name.endswith('-ci.json'):
                expected_types.add('required_status_checks')
            if set(rules) != expected_types or len(rules) != len(data['rules']):
                errors.append(name + ': missing, duplicate, or unexpected rule')
            pr = rules['pull_request']['parameters']
            if pr != dict(allowed_merge_methods=['merge', 'rebase'],
                          dismiss_stale_reviews_on_push=True, require_code_owner_review=False,
                          require_last_push_approval=False, required_approving_review_count=0,
                          required_review_thread_resolution=True):
                errors.append(name + ': PR policy drift')
            if name.endswith('-ci.json'):
                if rules['required_status_checks']['parameters'] != dict(
                        do_not_enforce_on_create=False,
                        required_status_checks=[{'context': 'Candidate Quality'}],
                        strict_required_status_checks_policy=True):
                    errors.append(name + ': CI gate policy drift')
        base, ci = stages
        reduced = dict(ci, rules=[r for r in ci['rules'] if r['type'] != 'required_status_checks'])
        if base != reduced:
            errors.append('CI template must extend the same base ruleset')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append('Cannot validate policy: ' + str(exc))
    return errors


def check(root, base_ref=None):
    root = root.resolve()
    errors = [f'Missing required file: {name}' for name in REQUIRED if not (root / name).is_file()]
    files, has_git = inventory(root)
    texts = {}
    links = 0
    for name in files:
        path = root / name
        if path.is_symlink():
            errors.append(f'{name}: symlink requires explicit governance support')
            continue
        if not path.is_file():  # A tracked file may be intentionally deleted locally.
            continue
        if path.suffix not in TEXT_SUFFIXES and path.name not in {'.editorconfig', '.gitattributes', '.gitignore'}:
            continue
        raw = path.read_bytes()
        try:
            content = raw.decode('utf-8')
        except UnicodeDecodeError:
            errors.append(f'{name}: invalid UTF-8')
            continue
        texts[name] = content
        if raw.startswith(b'\xef\xbb\xbf') or b'\r' in raw or (raw and not raw.endswith(b'\n')):
            errors.append(f'{name}: BOM, CR, or missing final newline')
        for number, line in enumerate(content.splitlines(), 1):
            # Exactly two trailing spaces are Markdown hard line breaks.
            trimmed = line.rstrip(' \t')
            if line != trimmed and not (path.suffix == '.md' and trimmed and line[len(trimmed):] == '  '):
                errors.append(f'{name}:{number}: trailing whitespace')
        if path.suffix == '.json':
            try:
                json.loads(content)
            except ValueError as exc:
                errors.append(f'{name}: invalid JSON: {exc}')
        if path.suffix == '.md':
            outside_fences = re.sub(r'^(`{3,}|~{3,}).*?^\1[^\n]*$', '', content, flags=re.M | re.S)
            for match in re.finditer(r'!?\[[^\]\n]*\]\(([^)\n]+)\)', outside_fences):
                target = match.group(1).strip().split(' "', 1)[0].strip('<>')
                parsed = urlsplit(target)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                links += 1
                dest = (path.parent / unquote(parsed.path)).resolve()
                if not dest.is_relative_to(root) or not dest.exists():
                    errors.append(f'{name}: missing or outside-root link: {target}')
    if 'AGENTS.md' in texts and 'CLAUDE.md' in texts:
        if texts['AGENTS.md'].splitlines()[1:] != texts['CLAUDE.md'].splitlines()[1:]:
            errors.append('AGENTS.md / CLAUDE.md differ below their titles')
        if len(texts['AGENTS.md'].splitlines()) > 250:
            errors.append('Root collaboration instructions exceed 250 lines')
    errors.extend(policy_errors(root))
    if has_git:
        for args in (('diff', '--check'), ('diff', '--cached', '--check')):
            result = git(root, *args)
            if result.returncode:
                errors.append('Git whitespace check failed: ' + os.fsdecode(result.stdout + result.stderr).strip())
    if base_ref:
        if not has_git:
            errors.append('--base-ref requires an initialized repository with commits')
        else:
            resolved = git(root, 'rev-parse', '--verify', '--end-of-options', base_ref + '^{commit}')
            if resolved.returncode:
                errors.append('Cannot resolve base ref; fetch sufficient history first')
            else:
                base = resolved.stdout.decode().strip()
                if git(root, 'merge-base', '--is-ancestor', base, 'HEAD').returncode:
                    errors.append('Base must be an ancestor of HEAD; choose the actual PR merge base')
                else:
                    diff = git(root, 'diff', '--check', base, 'HEAD')
                    if diff.returncode:
                        errors.append('PR range whitespace check failed: ' + os.fsdecode(diff.stdout + diff.stderr).strip())
                    commits = git(root, 'log', '--format=%h%x09%p%x09%s', base + '..HEAD')
                    if commits.returncode:
                        errors.append('Cannot inspect PR commit range')
                    else:
                        for line in commits.stdout.decode('utf-8', errors='replace').splitlines():
                            sha, parents, title = line.split('\t', 2)
                            if not COMMIT.fullmatch(title) and not (len(parents.split()) > 1 and title.startswith('Merge ')):
                                errors.append(f'{sha}: commit title is not Conventional Commits')
    return errors, f'{len(texts)} text files, {links} local file links; Git checks: ' + ('enabled' if has_git else 'NOT RUN (no repository)')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-ref', help='ancestor commit for PR range whitespace and commit-title checks')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    try:
        errors, summary = check(root, args.base_ref)
    except (OSError, ValueError) as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        return 1
    print(summary)
    for error in errors:
        print('ERROR: ' + error, file=sys.stderr)
    print('FAIL' if errors else 'PASS (local governance only)')
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
