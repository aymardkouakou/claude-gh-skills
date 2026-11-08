# SPDX-License-Identifier: LicenseRef-claude-gh-skills-1.0
# Copyright 2026 Aymard Kouakou - see NOTICE
"""portfolio.py (multi-repository report) and audit_org.py (multi-repository protections)."""
import contextlib
import importlib.util
import io
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent


def load(rel, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "skills" / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pf = load("project-board/portfolio.py", "portfolio")
ao = load("repo-hardening/audit_org.py", "audit_org")


def issue(n, labels=(), parent=None):
    return {"number": n, "labels": {"nodes": [{"name": x} for x in labels]}, "parent": {"number": parent} if parent else None,
            "subIssues": {"totalCount": 0}}


def out_of(fn, *a, **k):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = fn(*a, **k)
    return code, out.getvalue(), err.getvalue()


class Portfolio(unittest.TestCase):
    REPOS = [{"name": "b", "isArchived": False, "isFork": False, "visibility": "PRIVATE"},
             {"name": "a", "isArchived": False, "isFork": False, "visibility": "PUBLIC"},
             {"name": "old", "isArchived": True, "isFork": False, "visibility": "PUBLIC"},
             {"name": "fk", "isArchived": False, "isFork": True, "visibility": "PUBLIC"}]

    def test_list_repos_filters(self):
        ok = (0, json.dumps(self.REPOS), "")
        with mock.patch.object(pf.project, "run", return_value=ok):
            self.assertEqual([r["name"] for r in pf.list_repos("o")], ["a", "b"])
            self.assertEqual([r["name"] for r in pf.list_repos("o", archived=True, forks=True)], ["a", "b", "fk", "old"])
            self.assertEqual([r["name"] for r in pf.list_repos("o", public_only=True)], ["a"])
            self.assertEqual([r["name"] for r in pf.list_repos("o", only={"b"})], ["b"])
        with mock.patch.object(pf.project, "run", return_value=(0, "", "")):
            self.assertEqual(pf.list_repos("o"), [])
        with mock.patch.object(pf.project, "run", return_value=(1, "", "no access")):
            with self.assertRaises(RuntimeError):
                pf.list_repos("o")

    def test_gather_and_summarize(self):
        issues = [issue(1, ["epic"]), issue(2), issue(3, parent=1), issue(4)]
        row = pf.gather("o", {"name": "a", "visibility": "PUBLIC"}, lambda o, n: issues, lambda o, n: [{"number": 9}],
                        lambda o, n, num: {"completed": 1, "total": 3})
        self.assertEqual((row["Open issues"], row["Open PRs"], row["Open epics"], row["Epic progress"], row["Without epic"]),
                         (4, 1, 1, "1/3", 2))
        self.assertEqual(row["Visibility"], "public")

    def test_unreadable_repository_does_not_stop_the_report(self):
        def boom(o, n):
            raise RuntimeError("403")
        row = pf.gather("o", {"name": "x"}, boom, boom, None)
        self.assertEqual(row["Open issues"], "unavailable")

    def test_totals_and_render(self):
        rows = [{"Repository": "o/a", "Visibility": "public", "Open issues": 2, "Open PRs": 1, "Open epics": 1,
                 "Epic progress": "1/2", "Without epic": 1, "_done": 1, "_total": 2},
                {"Repository": "o/b", "Visibility": "", "Open issues": "unavailable", "Open PRs": "-", "Open epics": "-",
                 "Epic progress": "-", "Without epic": "-"}]
        t = pf.totals(rows)
        self.assertEqual((t["Open issues"], t["Epic progress"], t["Repository"]), (2, "1/2", "Total (1 repositories)"))
        self.assertEqual(pf.totals([])["Epic progress"], "-")
        md, csv_text = pf.render(rows, "md"), pf.render(rows, "csv")
        self.assertIn("| o/a | public | 2 | 1 | 1 | 1/2 | 1 |", md)
        self.assertTrue(csv_text.startswith("Repository,Visibility,Open issues"))

    def test_main(self):
        lister = lambda owner, only, arch, forks, pub: [{"name": "a", "visibility": "PUBLIC"}]  # noqa: E731
        gatherer = lambda owner, r: {"Repository": "o/a", "Visibility": "public", "Open issues": 0, "Open PRs": 0,  # noqa: E731
                                      "Open epics": 0, "Epic progress": "-", "Without epic": 0, "_done": 0, "_total": 0}
        code, out, _ = out_of(pf.main, ["o", "--repos", "a", "--format", "csv"], lister, gatherer)
        self.assertEqual(code, 0)
        self.assertIn("o/a", out)
        self.assertEqual(out_of(pf.main, ["o"], lambda *a: [], gatherer)[0], 2)
        def fail(*a):
            raise RuntimeError("nope")
        code, _, err = out_of(pf.main, ["o"], fail, gatherer)
        self.assertEqual(code, 2)
        self.assertIn("nope", err)


def api_for(data):
    return lambda path: ("ok", data[path]) if path in data else ("na", None)


class AuditOrg(unittest.TestCase):
    REPO = {"default_branch": "main", "security_and_analysis": {"secret_scanning": {"status": "enabled"},
                                                                  "secret_scanning_push_protection": {"status": "disabled"}}}

    def test_ruleset_covered_repository(self):
        rules = [{"type": "pull_request"}, {"type": "non_fast_forward"}, {"type": "deletion"}]
        row = ao.audit_repo("o", "r", api_for({"repos/o/r": self.REPO, "repos/o/r/rules/branches/main": rules}))
        self.assertEqual([row[c] for c in ao.COLUMNS[2:]], ["ok", "ok", "ok", "ok", "gap"])

    def test_classic_protection_fallback_and_gaps(self):
        prot = {"required_pull_request_reviews": {"required_approving_review_count": 1}, "allow_force_pushes": {"enabled": True}, "allow_deletions": {"enabled": False}}
        row = ao.audit_repo("o", "r", api_for({"repos/o/r": self.REPO, "repos/o/r/rules/branches/main": [],
                                               "repos/o/r/branches/main/protection": prot}))
        self.assertEqual([row[c] for c in ao.COLUMNS[2:5]], ["ok", "gap", "ok"])
        api = lambda path: (("missing", None) if path.endswith("/protection") else api_for(  # noqa: E731
            {"repos/o/r": self.REPO, "repos/o/r/rules/branches/main": []})(path))
        row = ao.audit_repo("o", "r", api)
        self.assertEqual([row[c] for c in ao.COLUMNS[2:5]], ["gap", "gap", "gap"])
        row = ao.audit_repo("o", "r", api_for({"repos/o/r": self.REPO, "repos/o/r/rules/branches/main": []}))
        self.assertEqual([row[c] for c in ao.COLUMNS[2:5]], ["n/a", "n/a", "n/a"])

    def test_unverifiable_is_not_a_gap(self):
        row = ao.audit_repo("o", "r", api_for({"repos/o/r": {"default_branch": "dev"}}))
        self.assertEqual(row["Default branch"], "dev")
        self.assertEqual([row[c] for c in ao.COLUMNS[2:]], ["n/a"] * 5)
        row = ao.audit_repo("o", "r", api_for({}))
        self.assertEqual((row["Default branch"], row["Secret scanning"]), ("-", "n/a"))
        row = ao.audit_repo("o", "r", api_for({"repos/o/r": {"security_and_analysis": None}}))
        self.assertEqual(row["Default branch"], "main")

    def test_gh_api_wrapper(self):
        ok = SimpleNamespace(returncode=0, stdout='{"a": 1}', stderr="")
        with mock.patch.object(ao.subprocess, "run", return_value=ok):
            self.assertEqual(ao.gh_api("x"), ("ok", {"a": 1}))
        with mock.patch.object(ao.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout="", stderr="")):
            self.assertEqual(ao.gh_api("x"), ("ok", None))
        with mock.patch.object(ao.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout="{bad", stderr="")):
            self.assertEqual(ao.gh_api("x"), ("na", None))
        with mock.patch.object(ao.subprocess, "run", return_value=SimpleNamespace(returncode=1, stdout="", stderr="403")):
            self.assertEqual(ao.gh_api("x"), ("na", None))
        gone = SimpleNamespace(returncode=1, stdout="", stderr="gh: Branch not protected (HTTP 404)")
        with mock.patch.object(ao.subprocess, "run", return_value=gone):
            self.assertEqual(ao.gh_api("x"), ("missing", None))

    def test_list_repos_and_rulesets(self):
        data = json.dumps([{"name": "b", "isArchived": False, "isFork": False}, {"name": "a", "isArchived": False, "isFork": False},
                           {"name": "o", "isArchived": True, "isFork": False}, {"name": "f", "isArchived": False, "isFork": True}])
        with mock.patch.object(ao.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=data, stderr="")):
            self.assertEqual(ao.list_repos("x"), ["a", "b"])
            self.assertEqual(ao.list_repos("x", only={"b"}, archived=True), ["b"])
        with mock.patch.object(ao.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout="", stderr="")):
            self.assertEqual(ao.list_repos("x"), [])
        with mock.patch.object(ao.subprocess, "run", return_value=SimpleNamespace(returncode=1, stdout="", stderr="denied")):
            with self.assertRaises(RuntimeError):
                ao.list_repos("x")
        self.assertEqual(ao.org_rulesets("o", api_for({"orgs/o/rulesets": [{"name": "base", "enforcement": "active"}, {}]})),
                         ["base (active)", "? (?)"])
        self.assertIsNone(ao.org_rulesets("o", api_for({})))

    def test_render_and_main(self):
        row = {c: "ok" for c in ao.COLUMNS}
        self.assertIn("| ok | ok |", ao.render([row], "md"))
        self.assertTrue(ao.render([row], "csv").startswith("Repository,Default branch"))
        gap = dict(row, **{"No force-push": "gap"})
        run = lambda rs: out_of(ao.main, ["o", "--strict"], lambda *a: ["r"], lambda o, n: gap, lambda o: rs)  # noqa: E731
        code, out, err = run(["base (active)"])
        self.assertEqual(code, 1)
        self.assertIn("1 gap(s)", err)
        self.assertIn("base (active)", err)
        self.assertIn("none listed", run([])[2])
        self.assertIn("not available", run(None)[2])
        self.assertEqual(out_of(ao.main, ["o"], lambda *a: ["r"], lambda o, n: gap, lambda o: None)[0], 0)
        self.assertEqual(out_of(ao.main, ["o", "--repos", "r"], lambda *a: [], None, None)[0], 2)
        def fail(*a):
            raise RuntimeError("denied")
        self.assertEqual(out_of(ao.main, ["o"], fail, None, None)[0], 2)

    def test_template_is_valid_and_starts_in_evaluate_mode(self):
        tpl = json.loads((ROOT / "skills" / "repo-hardening" / "references" / "org-ruleset.json").read_text())
        self.assertEqual(tpl["enforcement"], "evaluate")
        self.assertEqual({r["type"] for r in tpl["rules"]}, {"deletion", "non_fast_forward", "pull_request"})


if __name__ == "__main__":
    unittest.main()
