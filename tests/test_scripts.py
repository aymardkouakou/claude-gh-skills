# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Aymard Kouakou - see NOTICE
"""Shell helpers, run for real with a stubbed gh on PATH and an isolated state directory."""
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JOURNAL = ROOT / "skills" / "issue-lifecycle" / "journal.sh"
REFS = ROOT / "skills" / "dev-traceability" / "check-refs.sh"


class Journal(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        bindir = base / "bin"
        bindir.mkdir()
        gh = bindir / "gh"
        gh.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$GH_LOG"\ncat "$7" >> "$GH_LOG" 2>/dev/null\n')
        gh.chmod(gh.stat().st_mode | stat.S_IEXEC)
        self.log = base / "gh.log"
        self.env = {**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}", "GH_LOG": str(self.log),
                    "CLAUDE_SKILL_STATE": str(base / "state")}
        self.env.pop("CLAUDE_SKILL_LANG", None)
        self.text = base / "entry.txt"
        self.text.write_text("checked the logs, nothing unusual")

    def run_journal(self, type_, lang=None, text=None, repo="acme/app"):
        env = dict(self.env)
        if lang:
            env["CLAUDE_SKILL_LANG"] = lang
        if text is not None:
            self.text.write_text(text)
        return subprocess.run(["bash", str(JOURNAL), "7", type_, str(self.text), repo], env=env, capture_output=True, text=True)

    def test_posts_with_english_label(self):
        p = self.run_journal("Observation", lang="en")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("Observation", self.log.read_text())
        self.assertIn("acme/app", self.log.read_text())

    def test_localised_label(self):
        p = self.run_journal("Decision", lang="fr")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn("### Decision", self.log.read_text().replace("UTC", "").split("\n")[-3])

    def test_legacy_french_type_is_accepted(self):
        self.assertEqual(self.run_journal("Hypoth\u00e8se", lang="en").returncode, 0)

    def test_refuses_without_language(self):
        p = self.run_journal("Observation")
        self.assertEqual(p.returncode, 3)
        self.assertIn("no GitHub language", p.stderr)
        self.assertFalse(self.log.exists())

    def test_refuses_secrets_unknown_type_and_missing_file(self):
        self.assertEqual(self.run_journal("Observation", lang="en", text="password=SuperSecret12345").returncode, 3)
        self.assertFalse(self.log.exists())
        p = self.run_journal("Gossip", lang="en")
        self.assertEqual(p.returncode, 2)
        self.assertIn("unknown type", p.stderr)
        p = subprocess.run(["bash", str(JOURNAL), "7", "Observation", str(self.text) + ".nope", "acme/app"],
                           env=self.env, capture_output=True, text=True)
        self.assertEqual(p.returncode, 2)


class CheckRefs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.com")
        self.git("config", "user.name", "t")
        self.git("commit", "-q", "--allow-empty", "-m", "base")

    def git(self, *a):
        return subprocess.run(["git", *a], cwd=self.tmp.name, capture_output=True, text=True, check=True)

    def commit(self, msg):
        self.git("commit", "-q", "--allow-empty", "-m", msg)

    def check(self):
        return subprocess.run(["bash", str(REFS), "HEAD~2..HEAD"], cwd=self.tmp.name, capture_output=True, text=True)

    def test_all_referenced(self):
        self.commit("feat: a\n\nRefs #12")
        self.commit("fix: b\n\nRefs acme/app#3")
        p = self.check()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("references an issue", p.stdout)

    def test_missing_reference_fails(self):
        self.commit("feat: a\n\nRefs #12")
        self.commit("chore: no link")
        p = self.check()
        self.assertEqual(p.returncode, 1)
        self.assertIn("NO REFERENCE", p.stdout)
        self.assertIn("1 commit(s) without an issue reference", p.stderr)

    def test_documented_exception_is_accepted(self):
        self.commit("feat: a\n\nRefs #12")
        self.commit("chore: emergency\n\nNo-Issue: production hotfix, issue to follow")
        self.assertEqual(self.check().returncode, 0)


class Usage(unittest.TestCase):
    """Missing arguments print a readable usage line, not a raw bash error."""

    def run_script(self, *cmd):
        return subprocess.run(list(cmd), capture_output=True, text=True)

    def test_journal_without_arguments(self):
        p = self.run_script("bash", str(JOURNAL))
        self.assertEqual(p.returncode, 2)
        self.assertIn("Usage: journal.sh", p.stderr)
        self.assertNotIn("line ", p.stderr)

    def test_check_refs_without_arguments(self):
        p = self.run_script("bash", str(REFS))
        self.assertEqual(p.returncode, 2)
        self.assertIn("Usage: check-refs.sh", p.stderr)
        self.assertNotIn("line ", p.stderr)

    def test_help_flags_exit_zero(self):
        for script in (JOURNAL, REFS):
            self.assertEqual(self.run_script("bash", str(script), "--help").returncode, 0)

    def test_text_guard_usage_and_unreadable_file(self):
        guard = str(ROOT / "skills" / "issue-lifecycle" / "text_guard.py")
        p = self.run_script("python3", "-I", guard, "--help")
        self.assertEqual(p.returncode, 0)
        self.assertIn("Usage: text_guard.py", p.stderr)
        p = self.run_script("python3", "-I", guard, "/nonexistent/file")
        self.assertEqual(p.returncode, 2)
        self.assertNotIn("Traceback", p.stderr)


if __name__ == "__main__":
    unittest.main()
