# SPDX-License-Identifier: LicenseRef-claude-gh-skills-1.1
# Copyright 2026 Aymard Kouakou - see NOTICE
import contextlib
import importlib.util
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SKILLS = sorted(p.name for p in (ROOT / "skills").iterdir() if p.is_dir())
DEPS = json.loads((ROOT / "dependencies.json").read_text(encoding="utf-8"))
DEPS.pop("_comment")
spec = importlib.util.spec_from_file_location("check_deps", ROOT / "scripts" / "check_deps.py")
cd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cd)
SIBLING = re.compile(r"\$\{CLAUDE_SKILL_DIR\}/\.\./([a-z-]+)")


class Declared(unittest.TestCase):
    def test_every_skill_is_declared_with_known_siblings(self):
        self.assertEqual(sorted(DEPS), SKILLS)
        for name, d in DEPS.items():
            for dep in d["requires"] + d["optional"]:
                self.assertIn(dep, SKILLS, f"{name} -> {dep}")
            self.assertFalse(set(d["requires"]) & set(d["optional"]), name)
            self.assertNotIn(name, d["requires"] + d["optional"])

    def test_documented_references_are_declared(self):
        for name in SKILLS:
            files = [ROOT / "skills" / name / "SKILL.md", *(ROOT / "skills" / name / "references").glob("*.md")]
            used = {m for f in files for m in SIBLING.findall(f.read_text(encoding="utf-8"))}
            declared = set(DEPS[name]["requires"] + DEPS[name]["optional"])
            self.assertLessEqual(used, declared, f"{name} references undeclared {used - declared}")

    def test_scripts_that_call_a_sibling_declare_it_as_required(self):
        for script, needs in (("project-tracking/project.py", "repo-context"), ("project-board/board.py", "project-tracking"),
                              ("issue-lifecycle/journal.sh", "repo-context")):
            self.assertIn(needs, DEPS[script.split("/")[0]]["requires"], script)

    def test_learning_is_never_required_and_requirements_are_acyclic(self):
        for name, d in DEPS.items():
            self.assertNotIn("skill-learning", d["requires"], name)
        def walk(n, seen):
            self.assertNotIn(n, seen, f"cycle through {n}")
            for dep in DEPS[n]["requires"]:
                walk(dep, seen | {n})
        for name in DEPS:
            walk(name, set())


class Checker(unittest.TestCase):
    def tree(self, names):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for n in names:
            (Path(tmp.name) / n).mkdir()
            (Path(tmp.name) / n / "SKILL.md").write_text("x")
        (Path(tmp.name) / "not-a-skill").mkdir()
        return Path(tmp.name)

    def test_reports_missing_required_and_optional(self):
        required, optional = cd.check(self.tree(["issue-lifecycle"]), DEPS)
        self.assertEqual(required, ["issue-lifecycle needs repo-context"])
        self.assertEqual(len(optional), 2)

    def test_complete_tree_and_foreign_skills(self):
        self.assertEqual(cd.check(self.tree(SKILLS), DEPS), ([], []))
        self.assertEqual(cd.check(self.tree(["my-own-skill"]), DEPS), ([], []))
        self.assertEqual(cd.check(Path("/nonexistent-dir"), DEPS), ([], []))

    def run_main(self, argv, **kw):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = cd.main(argv, **kw)
        return code, out.getvalue()

    def test_main_exit_codes(self):
        code, out = self.run_main(["--dir", str(self.tree(["project-board"]))])
        self.assertEqual(code, 1)
        self.assertIn("MISSING  project-board needs project-tracking", out)
        self.assertIn("optional project-board can use skill-learning", out)
        self.assertEqual(self.run_main(["--dir", str(self.tree(SKILLS))])[0], 0)

    def test_default_directory_prefers_home_then_repository(self):
        home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, home)
        self.assertIn(str(ROOT / "skills"), self.run_main([], home=home)[1])
        (home / ".claude" / "skills").mkdir(parents=True)
        self.assertIn(str(home / ".claude" / "skills"), self.run_main([], home=home)[1])


class MissingSibling(unittest.TestCase):
    """A skill copied alone must say what is missing instead of crashing."""

    def alone(self, name):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        shutil.copytree(ROOT / "skills" / name, Path(tmp.name) / name, ignore=shutil.ignore_patterns("__pycache__"))
        return Path(tmp.name) / name

    def test_journal_without_repo_context(self):
        d = self.alone("issue-lifecycle")
        (d / "note.txt").write_text("ok")
        p = subprocess.run(["bash", str(d / "journal.sh"), "1", "Observation", str(d / "note.txt"), "acme/app"],
                           capture_output=True, text=True)
        self.assertEqual(p.returncode, 5, p.stderr)
        self.assertIn("repo-context skill is missing", p.stderr)

    def test_board_without_project_tracking(self):
        p = subprocess.run([sys.executable, str(self.alone("project-board") / "board.py"), "fields"], capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("needs the project-tracking skill", p.stderr)
        self.assertNotIn("Traceback", p.stderr)

    def test_project_without_repo_context(self):
        p = subprocess.run([sys.executable, str(self.alone("project-tracking") / "project.py"), "resolve"], capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("repo-context skill is missing", p.stdout + p.stderr)
        self.assertNotIn("Traceback", p.stderr)

    def load(self, rel, name):
        spec = importlib.util.spec_from_file_location(name, ROOT / "skills" / rel)
        mod = importlib.util.module_from_spec(spec)
        return spec, mod

    def test_in_process_guards(self):
        spec, mod = self.load("project-tracking/project.py", "project_guard")
        spec.loader.exec_module(mod)
        with mock.patch.object(type(mod.CTX), "is_file", return_value=False):
            rc, _, err = mod.ctx("repo")
        self.assertEqual(rc, 127)
        self.assertIn("repo-context skill is missing", err)
        spec, board = self.load("project-board/board.py", "board_guard")
        with mock.patch.object(Path, "is_file", return_value=False):
            with self.assertRaises(SystemExit) as caught:
                spec.loader.exec_module(board)
        self.assertIn("needs the project-tracking skill", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
