# SPDX-License-Identifier: LicenseRef-claude-gh-skills-1.0
# Copyright 2026 Aymard Kouakou - see NOTICE
import contextlib
import importlib.util
import io
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("rtm", ROOT / "skills" / "dev-traceability" / "rtm.py")
rtm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rtm)

REPO = "acme/app"
LOG = ("\x1eaaa1111\x1ffeat: x\n\nRefs #1\x1f\nsrc/a.py\ntests/test_a.py\n"
       "\x1ebbb2222\x1ffix: y\n\nFixes acme/app#2, Refs other/repo#1\x1f\nsrc/b.py\n"
       "\x1eccc3333\x1fdocs: z\x1f\nREADME.md\n\x1e   \n")
ISSUES = [
    {"number": 3, "title": "=cmd|' /C calc'!A0", "state": "OPEN", "body": "REQ-7 and SEC-2", "labels": []},
    {"number": 1, "title": "Add a", "state": "CLOSED", "body": "", "labels": [{"name": "enhancement"}]},
    {"number": 2, "title": "Fix b", "state": "CLOSED", "body": None, "labels": None},
    {"number": 4, "title": "Epic", "state": "OPEN", "body": "", "labels": [{"name": "Epic"}]},
    {"number": 5, "title": "Dropped", "state": "CLOSED", "stateReason": "NOT_PLANNED", "body": "", "labels": []},
]
PRS = [
    {"number": 10, "title": "p", "state": "MERGED", "body": "Refs #2", "author": {"login": "dev"},
     "reviews": [{"state": "APPROVED", "author": {"login": "dev"}}], "files": [{"path": "tests/test_b.py"}],
     "closingIssuesReferences": [{"number": 1}]},
    {"number": 11, "title": "q", "state": "OPEN", "body": None, "author": None, "reviews": None, "files": None,
     "closingIssuesReferences": None},
]


def by_issue(rows):
    return {r["Issue"].split()[0]: r for r in rows}


class Build(unittest.TestCase):
    def test_parse_log_ignores_foreign_repositories(self):
        parsed = rtm.parse_log(LOG, REPO)
        self.assertEqual([(s, n) for s, n, _ in parsed], [("aaa1111", [1]), ("bbb2222", [2]), ("ccc3333", [])])
        self.assertEqual(parsed[0][2], ["src/a.py", "tests/test_a.py"])

    def test_rows(self):
        rows = by_issue(rtm.build(ISSUES, PRS, LOG, REPO))
        self.assertEqual(sorted(rows), ["#1", "#2", "#3"])
        self.assertEqual(rows["#1"]["Commits"], "aaa1111")
        self.assertEqual(rows["#1"]["Tests"], "2 file(s)")
        self.assertEqual(rows["#1"]["Review"], "none")
        self.assertEqual(rows["#1"]["Gaps"], "no independent review")
        self.assertEqual(rows["#2"]["Pull requests"], "#10")
        self.assertEqual(rows["#3"]["Requirement"], "REQ-7, SEC-2")
        self.assertEqual(rows["#3"]["Gaps"], "no commit; no test change; no pull request")

    def test_independent_review_and_solo(self):
        prs = [dict(PRS[0], reviews=[{"state": "APPROVED", "author": {"login": "other"}}])]
        row = by_issue(rtm.build(ISSUES, prs, LOG, REPO))["#1"]
        self.assertEqual((row["Review"], row["Gaps"]), ("independent", "-"))
        solo = by_issue(rtm.build(ISSUES, PRS, LOG, REPO, solo=True))
        self.assertEqual(solo["#2"]["Gaps"], "-")
        self.assertEqual(solo["#3"]["Gaps"], "no commit; no test change")


class Render(unittest.TestCase):
    def test_markdown_escapes_untrusted_text(self):
        out = rtm.render(rtm.build(ISSUES, PRS, LOG, REPO), "md")
        self.assertIn("#3 =cmd\\|' /C calc'!A0", out)
        self.assertEqual(out.splitlines()[1], "|" + "---|" * 8)

    def test_csv_neutralises_formulas(self):
        out = rtm.render(rtm.build(ISSUES, PRS, LOG, REPO), "csv")
        self.assertTrue(out.startswith("Requirement,Issue,State"))
        self.assertEqual(rtm.cell("=1+1"), "'=1+1")
        self.assertEqual(rtm.cell("@x"), "'@x")
        self.assertEqual(rtm.cell("-"), "-")
        self.assertEqual(rtm.cell("-x"), "'-x")
        self.assertEqual(rtm.cell("a\nb"), "a b")


class Main(unittest.TestCase):
    def call(self, argv, fetcher=None):
        out, err = io.StringIO(), io.StringIO()
        fetcher = fetcher or (lambda repo, rng: (ISSUES, PRS, LOG))
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = rtm.main(argv, fetcher)
        return code, out.getvalue(), err.getvalue()

    def test_strict_fails_only_on_closed_gaps(self):
        code, out, err = self.call(["--repo", REPO])
        self.assertEqual(code, 0)
        self.assertIn("not a certification", err)
        self.assertEqual(self.call(["--repo", REPO, "--strict"])[0], 1)
        self.assertEqual(self.call(["--repo", REPO, "--strict", "--solo", "--format", "csv"])[0], 0)

    def test_errors_are_reported(self):
        def boom(repo, rng):
            raise RuntimeError("gh: not logged in")
        code, _, err = self.call(["--repo", REPO], boom)
        self.assertEqual(code, 2)
        self.assertIn("not logged in", err)

    def test_repo_defaults_to_gh(self):
        with mock.patch.object(rtm, "run", return_value="acme/app\n"):
            self.assertEqual(self.call([])[0], 0)


class Fetch(unittest.TestCase):
    def test_run_and_fetch(self):
        ok = SimpleNamespace(returncode=0, stdout="[]", stderr="")
        with mock.patch.object(rtm.subprocess, "run", return_value=ok) as m:
            self.assertEqual(rtm.fetch(REPO, "v1..HEAD"), ([], [], "[]"))
            self.assertIn("v1..HEAD", m.call_args_list[-1][0][0])
        empty = SimpleNamespace(returncode=0, stdout="", stderr="")
        with mock.patch.object(rtm.subprocess, "run", return_value=empty):
            self.assertEqual(rtm.gh_json(REPO, "issue", "number"), [])
        bad = SimpleNamespace(returncode=1, stdout="", stderr="no auth")
        with mock.patch.object(rtm.subprocess, "run", return_value=bad):
            with self.assertRaises(RuntimeError):
                rtm.run(["gh"])


if __name__ == "__main__":
    unittest.main()
