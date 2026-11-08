# SPDX-License-Identifier: LicenseRef-claude-gh-skills-1.0
# Copyright 2026 Aymard Kouakou - see NOTICE
import contextlib
import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("release", ROOT / "scripts" / "release.py")
rl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rl)

CHANGELOG = "# Changelog\n\n## [Unreleased]\n\n### Added\n- thing\n\n## [0.1.0] - 2026-01-01\n\n### Added\n- first\n"


class Pure(unittest.TestCase):
    def test_newer(self):
        self.assertTrue(rl.newer("0.10.0", "0.9.9"))
        self.assertFalse(rl.newer("0.9.0", "0.9.0"))
        self.assertFalse(rl.newer("1.0", "0.9.0"))

    def test_changelog_helpers(self):
        self.assertEqual(rl.unreleased_body(CHANGELOG), "### Added\n- thing")
        self.assertEqual(rl.unreleased_body("# x"), "")
        out = rl.release_changelog(CHANGELOG, "0.2.0", "2026-02-02")
        self.assertIn("## [Unreleased]\n\n## [0.2.0] - 2026-02-02\n\n### Added\n- thing", out)
        self.assertEqual(rl.section(out, "0.2.0"), "### Added\n- thing")
        self.assertEqual(rl.section(out, "0.1.0"), "### Added\n- first")
        self.assertEqual(rl.section(out, "9.9.9"), "")

    def test_sh_returns_code_and_output(self):
        fake = lambda *a, **k: SimpleNamespace(returncode=3, stdout=" out \n", stderr=None)
        self.assertEqual(rl.sh(["x"], runner=fake), (3, "out", ""))


class Release(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / ".claude-plugin").mkdir()
        for name in ("plugin.json", "marketplace.json"):
            (self.root / ".claude-plugin" / name).write_text(json.dumps({"name": "x", "version": "0.1.0"}, indent=2) + "\n")
        (self.root / "CHANGELOG.md").write_text(CHANGELOG)
        self.git("init", "-q", "-b", "main")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "init")
        self.calls = []

    def git(self, *args):
        return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=self.root,
                              capture_output=True, text=True, check=True).stdout.strip()

    def run_cmd(self, argv, ok=True, record=False):
        """Real git, fake tests/validate/push/gh."""
        def run(cmd, cwd=None, runner=None):
            if cmd[0] == "git" and cmd[1] in ("commit", "tag"):
                return rl.sh(["git", "-c", "user.name=t", "-c", "user.email=t@t", *cmd[1:]], self.root)
            if cmd[0] in ("gh",) or cmd[1:3] == ["-m", "unittest"] or cmd[:2] == ["claude", "plugin"] or cmd[1] == "push":
                self.calls.append(cmd)
                return (0 if ok else 1), "", "boom"
            return rl.sh(cmd, self.root)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = rl.main(argv, root=self.root, run=run, today="2026-02-02")
        return code, out.getvalue(), err.getvalue()

    def test_dry_run_changes_nothing(self):
        code, out, _ = self.run_cmd(["0.2.0"])
        self.assertEqual(code, 0)
        self.assertIn("dry run", out)
        self.assertEqual(rl.current_version(self.root), "0.1.0")
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_apply_bumps_commits_and_tags(self):
        code, out, _ = self.run_cmd(["v0.2.0", "--apply", "--refs", "#5", "6"])
        self.assertEqual(code, 0)
        for rel in rl.MANIFESTS:
            self.assertEqual(json.loads((self.root / rel).read_text())["version"], "0.2.0")
        self.assertIn("## [0.2.0] - 2026-02-02", (self.root / "CHANGELOG.md").read_text())
        self.assertIn("Refs #5\nRefs #6", self.git("log", "-1", "--format=%B"))
        self.assertEqual(self.git("tag"), "v0.2.0")
        self.assertEqual(len(self.calls), 2)
        self.assertNotIn("gh", [c[0] for c in self.calls])

    def test_apply_without_refs_documents_the_exception(self):
        self.run_cmd(["0.2.0", "--apply"])
        self.assertIn("No-Issue: release bump", self.git("log", "-1", "--format=%B"))

    def test_push_publishes_with_changelog_notes(self):
        code, out, _ = self.run_cmd(["0.2.0", "--apply", "--push"])
        self.assertEqual(code, 0)
        self.assertIn("published", out)
        release = [c for c in self.calls if c[0] == "gh"][0]
        self.assertEqual(release[-1], "### Added\n- thing")

    def test_refusals(self):
        for argv, text in ((["abc"], "not MAJOR"), (["0.1.0"], "not newer")):
            code, _, err = self.run_cmd(argv)
            self.assertEqual(code, 1)
            self.assertIn(text, err)
        (self.root / "dirty.txt").write_text("x")
        code, _, err = self.run_cmd(["0.2.0"])
        self.assertIn("not clean", err)
        (self.root / "dirty.txt").unlink()
        self.git("checkout", "-q", "-b", "topic")
        self.assertIn("not on main", self.run_cmd(["0.2.0"])[2])
        self.git("checkout", "-q", "main")
        self.git("tag", "v0.2.0")
        self.assertIn("already exists", self.run_cmd(["0.2.0"])[2])
        self.git("tag", "-d", "v0.2.0")
        (self.root / "CHANGELOG.md").write_text("## [Unreleased]\n\n## [0.1.0] - x\n")
        self.git("commit", "-q", "-am", "empty")
        self.assertIn("is empty", self.run_cmd(["0.2.0"])[2])

    def test_push_requires_apply(self):
        self.assertEqual(self.run_cmd(["0.2.0", "--push"])[0], 2)

    def test_failing_checks_refuse_before_any_edit(self):
        code, _, err = self.run_cmd(["0.2.0", "--apply"], ok=False)
        self.assertEqual(code, 1)
        self.assertIn("tests fail", err)
        self.assertIn("validate fails", err)
        self.assertEqual(rl.current_version(self.root), "0.1.0")

    def test_failing_push_or_git_step_is_reported(self):
        code, _, err = self.run_cmd(["0.2.0", "--apply", "--push"], ok=True)
        self.assertEqual(code, 0)
        self.git("reset", "-q", "--hard", "HEAD~1")
        self.git("tag", "-d", "v0.2.0")
        failing_step = ["commit"]

        def failing(cmd, cwd=None, runner=None):
            if cmd[1] in failing_step:
                return 1, "", "denied"
            if cmd[0] in ("gh",) or cmd[1:3] == ["-m", "unittest"] or cmd[:2] == ["claude", "plugin"]:
                return 0, "", ""
            return rl.sh(cmd, self.root)
        for extra, step in (([], "commit"), (["--push"], "push")):
            failing_step[0] = step
            err = io.StringIO()
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                self.assertEqual(rl.main(["0.3.0", "--apply", *extra], root=self.root, run=failing), 1)
            self.assertIn(f"failed: {'git ' + step}", err.getvalue())
            self.git("reset", "-q", "--hard", "HEAD~1" if step == "push" else "HEAD")
            if step == "push":
                self.git("tag", "-d", "v0.3.0")


if __name__ == "__main__":
    unittest.main()
