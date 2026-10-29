"""Mutation tests for governance failures; fixtures never initialize Git."""
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('check_repo', SOURCE / 'scripts/check-repo.py')
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


class GovernanceFailures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='radishforge-governance-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        files, _ = CHECK.inventory(SOURCE)
        for name in files:
            source = SOURCE / name
            if source.is_file() and not source.is_symlink():
                dest = self.root / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, dest)

    def errors(self):
        return CHECK.check(self.root)[0]

    def test_valid_repository_without_git(self):
        errors, summary = CHECK.check(self.root)
        self.assertEqual(errors, [])
        self.assertIn('NOT RUN', summary)

    def test_missing_required_file(self):
        (self.root / 'SECURITY.md').unlink()
        self.assertTrue(any('Missing required file: SECURITY.md' in e for e in self.errors()))

    def test_collaboration_drift(self):
        p = self.root / 'CLAUDE.md'
        p.write_text(p.read_text() + '\n未同步约束。\n')
        self.assertTrue(any('differ below' in e for e in self.errors()))

    def test_text_and_broken_link(self):
        (self.root / 'invalid.md').write_bytes(b'\xef\xbb\xbf[missing](no-such-file.md)\r\n')
        errors = self.errors()
        self.assertTrue(any('BOM, CR' in e for e in errors))
        self.assertTrue(any('no-such-file.md' in e for e in errors))

    def test_policy_weakening(self):
        p = self.root / '.github/rulesets/master-protection-ci.json'
        p.write_text(p.read_text().replace('Candidate Quality', 'Unrelated Check'))
        self.assertTrue(any('CI gate policy drift' in e for e in self.errors()))

    def test_unexpected_active_template(self):
        p = self.root / '.github/rulesets/master-protection.json'
        p.write_text(p.read_text().replace('"disabled"', '"active"'))
        self.assertTrue(any('disabled staging' in e for e in self.errors()))

    def test_invalid_json(self):
        (self.root / 'bad.json').write_text('{broken}\n')
        self.assertTrue(any('invalid JSON' in e for e in self.errors()))

    def test_git_range_without_git_is_failure(self):
        errors, _ = CHECK.check(self.root, 'HEAD~1')
        self.assertTrue(any('--base-ref requires' in e for e in errors))


if __name__ == '__main__':
    unittest.main()
