# SPDX-License-Identifier: LicenseRef-claude-gh-skills-1.0
# Copyright 2026 Aymard Kouakou - see NOTICE
import contextlib
import importlib.util
import io
import json
import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("eval_run", ROOT / "evals" / "run.py")
er = importlib.util.module_from_spec(spec)
spec.loader.exec_module(er)


def stream(*skills):
    lines = ["not json", json.dumps({"type": "system"})]
    for s in skills:
        lines.append(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "text", "text": "x"}, {"type": "tool_use", "name": "Skill", "input": {"skill": s}},
            {"type": "tool_use", "name": "Bash", "input": {}}]}}))
    return "\n".join(lines)


def fake(skills=(), exc=None):
    def runner(cmd, **kw):
        if exc:
            raise exc
        return SimpleNamespace(stdout=stream(*skills))
    return runner


def run_main(argv, runner=None):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = er.main(argv, runner or fake())
    return code, out.getvalue()


class Runner(unittest.TestCase):
    def test_invoked_skills_strips_plugin_prefix(self):
        self.assertEqual(er.invoked_skills(stream("traceable-dev:repo-context", "issue-lifecycle")),
                         {"repo-context", "issue-lifecycle"})

    def test_grade(self):
        self.assertTrue(er.grade({"expect": "trigger"}, "a", {"a"}))
        self.assertFalse(er.grade({"expect": "trigger"}, "a", set()))
        self.assertTrue(er.grade({"expect": "no-trigger"}, "a", {"b"}))
        self.assertFalse(er.grade({"expect": "no-trigger"}, "a", {"a"}))

    def test_command_is_bounded_and_isolated(self):
        cmd = er.build_command("hi", "haiku", 0.3)
        for flag in ("--max-budget-usd", "--max-turns", "--no-session-persistence", "--plugin-dir"):
            self.assertIn(flag, cmd)
        self.assertEqual(cmd[cmd.index("--permission-mode") + 1], "plan")

    def test_dry_run_executes_nothing(self):
        def boom(*a, **k):
            raise AssertionError("must not run")
        code, out = run_main(["--skill", "repo-context", "--procedure"], boom)
        self.assertEqual(code, 0)
        self.assertIn("[dry] repo-context: trigger", out)
        self.assertIn("[review] repo-context", out)

    def test_run_reports_pass_and_fail(self):
        code, out = run_main(["--run", "--skill", "repo-context"], fake(["repo-context"]))
        self.assertEqual(code, 1)
        self.assertIn("PASS repo-context: trigger", out)
        self.assertIn("FAIL repo-context: no-trigger", out)

    def test_run_failure_is_a_fail_not_a_crash(self):
        code, out = run_main(["--run", "--skill", "repo-context"], fake(exc=subprocess.TimeoutExpired("c", 1)))
        self.assertEqual(code, 1)
        self.assertIn("run failed: TimeoutExpired", out)
        code, _ = run_main(["--run", "--skill", "repo-context"], fake(exc=OSError()))
        self.assertEqual(code, 1)

    def test_all_pass(self):
        code, out = run_main(["--run", "--skill", "incident-response"], fake(["incident-response"]))
        self.assertIn("failed", out)

    def test_unknown_skill(self):
        code, _ = run_main(["--skill", "nope"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
