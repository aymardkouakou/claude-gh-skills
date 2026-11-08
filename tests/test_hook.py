# SPDX-License-Identifier: LicenseRef-claude-gh-skills-1.1
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

    def git(self, *args):
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=self.repo, check=True,
                       capture_output=True)

    def test_pull_request_body_needs_a_reference(self):
        self.track()
        self.assertEqual(self.run_hook('gh pr create --title t --body "Adds x"').returncode, 2)
        self.assertEqual(self.run_hook('gh pr edit 4 -b "Adds x"').returncode, 2)
        self.assertEqual(self.run_hook('gh pr create --body "Adds x\n\nRefs #12"').returncode, 0)
        self.assertEqual(self.run_hook('gh pr create --body "x\n\nNo-Issue: typo"').returncode, 0)
        for cmd in ("gh pr create --fill", "gh pr create --body-file b.md", "gh pr view 4"):
            self.assertEqual(self.run_hook(cmd).returncode, 0, cmd)
        bare = self.run_hook('gh pr create --body "x"', cwd=self.repo.parent)
        self.assertEqual(bare.returncode, 0)

    def test_force_push_to_protected_branch_is_denied(self):
        self.track()
        self.git("checkout", "-q", "-b", "main")
        for cmd in ("git push --force origin main", "git push -f", "git push --force-with-lease origin HEAD:main",
                    "git push origin +main", "git push -uf origin main", "git push --mirror origin",
                    "git push --force-with-lease=main origin main", "git status && git push -f origin refs/heads/main"):
            p = self.run_hook(cmd)
            self.assertEqual(p.returncode, 2, cmd)
            self.assertIn("Force-push blocked", p.stderr)

    def test_other_pushes_pass(self):
        self.track()
        self.git("checkout", "-q", "-b", "feature")
        for cmd in ("git push origin main", "git push", "git push -u origin feature", "git push --force origin feature",
                    "git push -f", "git push --follow-tags origin feature", 'git push -f "unterminated'):
            self.assertEqual(self.run_hook(cmd).returncode, 0, cmd)
        self.assertEqual(self.run_hook("git push -f", cwd=self.repo.parent).returncode, 0)

    def test_force_push_in_untracked_repository_is_untouched(self):
        self.git("checkout", "-q", "-b", "main")
        self.assertEqual(self.run_hook("git push -f origin main").returncode, 0)

    def test_detached_head_force_push_is_not_blocked(self):
        self.track()
        self.git("commit", "-q", "--allow-empty", "-m", "x")
        self.git("checkout", "-q", "--detach")
        self.assertEqual(self.run_hook("git push -f").returncode, 0)

    def ask(self, command):
        p = self.run_hook(command)
        self.assertEqual(p.returncode, 0, command)
        return json.loads(p.stdout)["hookSpecificOutput"] if p.stdout else None

    def test_closing_an_issue_without_a_commit_asks(self):
        self.track()
        out = self.ask("gh issue close 9")
        self.assertEqual(out["permissionDecision"], "ask")
        self.assertIn("#9", out["permissionDecisionReason"])
        self.assertIsNotNone(self.ask('gh issue close #9 --comment "done" && echo ok'))

    def test_closing_an_issue_with_a_linked_change_passes(self):
        self.track()
        self.git("commit", "-q", "--allow-empty", "-m", "feat: x\n\nRefs #9")
        self.assertIsNone(self.ask("gh issue close 9"))
        self.assertIsNotNone(self.ask("gh issue close 90"))
        self.assertIsNone(self.ask('gh issue close 91 --comment "Delivered in 5e8cc73"'))
        self.assertIsNone(self.ask('gh issue close 92 --comment "Merged in #30"'))

    def test_close_edge_cases_pass(self):
        self.track()
        self.assertIsNone(self.ask("gh issue close"))
        self.assertIsNone(self.ask("gh issue view 9"))
        self.assertIsNone(self.ask('gh issue close 9 --comment "unterminated'))
        untracked = Path(self.state / "repos" / "github.com__acme__app.json")
        untracked.unlink()
        self.assertIsNone(self.ask("gh issue close 9"))


if __name__ == "__main__":
    unittest.main()
