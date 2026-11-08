# SPDX-License-Identifier: LicenseRef-claude-gh-skills-1.1
# Copyright 2026 Aymard Kouakou - see NOTICE
"""Label-based tracking (no GitHub Project, no `project` scope)."""
import contextlib
import importlib.util
import io
import json
import os
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("project_labels", ROOT / "skills" / "project-tracking" / "project.py")
project = importlib.util.module_from_spec(spec)
spec.loader.exec_module(project)

NO_SCOPE = "Token scopes: 'gist', 'repo'"


def issue(n, labels=(), parent=None, subs=0):
    return {"number": n, "title": f"t{n}", "labels": {"nodes": [{"name": x} for x in labels]},
            "parent": {"number": parent} if parent else None, "subIssues": {"totalCount": subs}, "projectItems": {"nodes": []}}


def pr(n, labels=()):
    return {"number": n, "title": f"pr{n}", "labels": {"nodes": [{"name": x} for x in labels]}, "projectItems": {"nodes": []}}


class Helpers(unittest.TestCase):
    def test_label_helpers(self):
        self.assertTrue(project.has_label(issue(1, ["Tracked"]), "tracked"))
        self.assertFalse(project.has_label({"number": 2}, "tracked"))
        unlabelled, no_epic = project.classify_labels([issue(1, ["tracked"], parent=9), issue(2), issue(3, ["epic"]), issue(4, ["tracked"])])
        self.assertEqual([i["number"] for i in unlabelled], [2, 3])
        self.assertEqual([i["number"] for i in no_epic], [2, 4])

    def test_labels_mode_sources(self):
        with mock.patch.dict(os.environ, {"CLAUDE_SKILL_PROJECT": "labels"}):
            self.assertTrue(project.labels_mode())
        with mock.patch.dict(os.environ, {"CLAUDE_SKILL_PROJECT": "acme/2"}):
            self.assertFalse(project.labels_mode())
        with mock.patch.dict(os.environ):
            os.environ.pop("CLAUDE_SKILL_PROJECT", None)
            show = lambda note: (0, json.dumps({"notes": {"project": note}}), "")  # noqa: E731
            with mock.patch.object(project, "ctx", return_value=show("labels")):
                self.assertTrue(project.labels_mode())
            with mock.patch.object(project, "ctx", return_value=show("acme/2")):
                self.assertFalse(project.labels_mode())
            with mock.patch.object(project, "ctx", return_value=(0, "not json", "")):
                self.assertFalse(project.labels_mode())
            with mock.patch.object(project, "ctx", return_value=(2, "", "")):
                self.assertFalse(project.labels_mode())

    def test_add_label_creates_then_edits(self):
        calls = []
        with mock.patch.object(project, "run", side_effect=lambda a, **k: (calls.append(a) or (0, "", ""))):
            self.assertEqual(project.add_label(project.Ref(("acme", "app", 7))), (True, ""))
            self.assertEqual(project.add_label(project.Ref(("acme", "app", 8)), pull=True), (True, ""))
        self.assertEqual(calls[0][:3], ["gh", "label", "create"])
        self.assertEqual(calls[1][:3], ["gh", "issue", "edit"])
        self.assertEqual(calls[3][:3], ["gh", "pr", "edit"])
        with mock.patch.object(project, "run", return_value=(1, "", "boom")):
            self.assertEqual(project.add_label(project.Ref(("acme", "app", 7))), (False, "boom"))


class Main(unittest.TestCase):
    def setUp(self):
        self.issues = [issue(1, ["tracked"], parent=9), issue(2), issue(3, ["tracked"])]
        self.prs = [pr(5), pr(6, ["tracked"])]
        self.scopes = NO_SCOPE
        patches = {
            "run": mock.patch.object(project, "run", side_effect=lambda a, **k: (0, self.scopes, "")),
            "labels_mode": mock.patch.object(project, "labels_mode", return_value=True),
            "repo_parts_host": mock.patch.object(project, "repo_parts_host", return_value=("github.com", "acme", "app")),
            "repo_kind": mock.patch.object(project, "repo_kind", return_value={"writable": True}),
            "fetch_open_issues": mock.patch.object(project, "fetch_open_issues", side_effect=lambda o, n: self.issues),
            "fetch_open_prs": mock.patch.object(project, "fetch_open_prs", side_effect=lambda o, n: self.prs),
            "add_label": mock.patch.object(project, "add_label", return_value=(True, "")),
            "set_parent": mock.patch.object(project, "set_parent", return_value=(True, "")),
            "ctx": mock.patch.object(project, "ctx", return_value=(0, "", "")),
        }
        self.m = {k: p.start() for k, p in patches.items()}
        for p in patches.values():
            self.addCleanup(p.stop)

    def call(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = project.main(list(argv))
        return rc, out.getvalue(), err.getvalue()

    def test_missing_scope_is_fine_in_label_mode_and_hints_otherwise(self):
        self.assertEqual(self.call("resolve")[0], 0)
        self.m["labels_mode"].return_value = False
        rc, _, err = self.call("resolve")
        self.assertEqual(rc, 4)
        self.assertIn("project.py use labels", err)

    def test_use_labels_records_the_choice(self):
        rc, out, err = self.call("use", "labels")
        self.assertEqual(rc, 0)
        self.m["ctx"].assert_called_with("note", "project", "labels")
        self.assertIn("Tracking: labels", err)

    def test_resolve(self):
        rc, out, err = self.call("resolve")
        self.assertEqual(json.loads(out)["tracking"], "labels")
        self.assertIn("Tracking: labels (no GitHub Project)", err)

    def test_attach_labels_and_links_epic(self):
        rc, out, _ = self.call("attach", "4", "5", "--epic", "1")
        self.assertEqual(rc, 0)
        self.assertEqual(self.m["add_label"].call_count, 2)
        self.assertEqual(self.m["set_parent"].call_count, 2)
        self.assertIn("#4 label: ok", out)

    def test_attach_without_epic_pr_and_failures(self):
        rc, out, _ = self.call("attach", "4")
        self.assertIn("NOT SET", out)
        rc, out, _ = self.call("attach", "40", "--pr")
        self.assertIn("PR #40 label: ok", out)
        self.m["set_parent"].assert_not_called()
        self.m["add_label"].return_value = (False, "nope")
        self.m["set_parent"].return_value = (False, "nope")
        self.assertEqual(self.call("attach", "4", "--epic", "1")[0], 2)

    def test_orphans(self):
        rc, out, _ = self.call("orphans")
        self.assertEqual(rc, 1)
        self.assertIn("#2 without the `tracked` label", out)
        self.assertIn("PR #5 without the `tracked` label", out)
        self.assertIn("#3 without epic", out)
        self.assertIn("1 issue(s) and 1 PR(s) not labelled `tracked`, 2 without epic", out)
        self.issues, self.prs = [issue(1, ["tracked"], parent=9)], []
        self.assertEqual(self.call("orphans")[0], 0)

    def test_backfill_dry_run_apply_and_missing_epic(self):
        rc, out, _ = self.call("backfill")
        self.assertEqual(rc, 0)
        self.assertIn("Dry run", out)
        self.m["add_label"].assert_not_called()
        rc, _, err = self.call("backfill", "--apply")
        self.assertEqual(rc, 3)
        self.assertEqual(self.m["add_label"].call_count, 2)
        rc, out, _ = self.call("backfill", "--apply", "--epic", "3")
        self.assertEqual(rc, 0)
        self.assertEqual(self.m["set_parent"].call_count, 1)  # #3 is the epic itself and is skipped
        self.m["add_label"].return_value = (False, "x")
        self.assertEqual(self.call("backfill", "--apply", "--epic", "3")[0], 2)
        self.issues, self.prs = [issue(1, ["tracked"], parent=9)], []
        self.assertEqual(self.call("backfill", "--apply")[0], 0)

    def test_commands_that_need_a_project_are_refused(self):
        rc, _, err = self.call("create")
        self.assertEqual(rc, 4)
        self.assertIn("needs the `project` scope", err)
        rc, _, err = self.call("visibility")
        self.assertEqual(rc, 2)
        self.assertIn("tracks with labels", err)
        self.scopes = "Token scopes: 'project', 'repo'"
        with mock.patch.object(project, "create_project", return_value=(5, ["created Project acme/5"])):
            self.assertEqual(self.call("create")[0], 0)
        with self.assertRaises(project.Stop):
            project.project_for("acme", "app", "acme/app", {})

    def test_tree_and_detach_still_work(self):
        with mock.patch.object(project, "fetch_tree", return_value={"number": 1, "title": "t", "state": "OPEN",
                                                                     "summary": {"total": 0, "completed": 0}, "children": []}):
            self.assertEqual(self.call("tree", "1")[0], 0)


if __name__ == "__main__":
    unittest.main()
