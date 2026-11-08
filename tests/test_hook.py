# SPDX-License-Identifier: LicenseRef-claude-gh-skills-1.0
# Copyright 2026 Aymard Kouakou - see NOTICE
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "hooks" / "require_issue_ref.py"


class RequireIssueRef(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.state = base / "state"
        (self.state / "repos").mkdir(parents=True)
        self.repo = base / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        subprocess.run(["git", "remote", "add", "origin", "https://github.com/acme/app.git"], cwd=self.repo, check=True)

    def track(self, project="acme/1"):
        (self.state / "repos" / "github.com__acme__app.json").write_text(json.dumps({"notes": {"project": project}}))

    def run_hook(self, command, cwd=None, raw=None):
        env = dict(os.environ, CLAUDE_SKILL_STATE=str(self.state))
        payload = raw if raw is not None else json.dumps({"tool_input": {"command": command}, "cwd": str(cwd or self.repo)})
        return subprocess.run(["python3", "-I", str(HOOK)], input=payload, env=env, capture_output=True, text=True)

    def test_denies_commit_without_reference_when_tracked(self):
        self.track()
        p = self.run_hook('git commit -m "feat: x"')
        self.assertEqual(p.returncode, 2)
        self.assertIn("no issue reference", p.stderr)

    def test_accepts_reference_forms(self):
        self.track()
        for msg in ("feat: x\n\nRefs #12", "fix: y Fixes #3", "docs: z Closes acme/other#9", "chore: q\n\nNo-Issue: typo"):
            self.assertEqual(self.run_hook(f"git commit -m '{msg}'").returncode, 0, msg)

    def test_untracked_repository_is_untouched(self):
        self.assertEqual(self.run_hook('git commit -m "feat: x"').returncode, 0)

    def test_other_commands_and_uninspectable_commits_pass(self):
        self.track()
        for cmd in ("git status", "git push", "git commit", "git commit -F msg.txt", "echo commit -m x", 'git log -m "git commit"'):
            self.assertEqual(self.run_hook(cmd).returncode, 0, cmd)

    def test_fails_open_on_bad_input_and_no_remote(self):
        self.track()
        self.assertEqual(self.run_hook("", raw="not json").returncode, 0)
        bare = Path(self.tmp.name) / "bare"
        bare.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=bare, check=True)
        self.assertEqual(self.run_hook('git commit -m "x"', cwd=bare).returncode, 0)

    def test_flag_variants_are_inspected(self):
        self.track()
        for cmd in ('git commit -am "x"', 'git commit --message="x"', 'git -C . commit -m "x"'):
            self.assertEqual(self.run_hook(cmd).returncode, 2, cmd)


if __name__ == "__main__":
    unittest.main()
