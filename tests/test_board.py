# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Aymard Kouakou - see NOTICE
import contextlib
import importlib.util
import io
import json
import runpy
import sys
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("board", ROOT / "skills" / "project-board" / "board.py")
board = importlib.util.module_from_spec(spec)
spec.loader.exec_module(board)
project = board.project

NOW = datetime(2026, 11, 5, tzinfo=timezone.utc)
INFO = {"id": "PVT_1", "number": 2, "owner": {"login": "acme", "type": "User"}}


def item(title="t", status="Todo", number=1, kind="Issue", labels=(), assignees=None, priority=None, repo="acme/app", url=None):
    it = {"id": f"I{number}", "title": title, "status": status, "labels": list(labels),
          "content": {"type": kind, "number": number, "repository": repo, "url": url or f"https://github.com/{repo}/issues/{number}"}}
    if assignees:
        it["assignees"] = assignees
    if priority:
        it["priority"] = priority
    return it


class Planning(unittest.TestCase):
    def test_plan_fields(self):
        self.assertEqual([f["name"] for f in board.plan_fields([])], [f["name"] for f in board.STANDARD_FIELDS])
        self.assertEqual([f["name"] for f in board.plan_fields(["priority", "KIND", "Estimate"])], ["Target date", "Iteration"])

    def test_plan_views(self):
        create, skipped = board.plan_views(["board", "All items"], ["Title"])
        names = [v[0] for v in create]
        self.assertNotIn("Board", names)
        self.assertIn("Backlog", names)
        self.assertEqual({n for n, _ in skipped}, {"Current iteration", "Roadmap", "Needs triage"})
        create, skipped = board.plan_views([], ["Iteration", "Target date", "Priority"])
        self.assertEqual(skipped, [])
        self.assertEqual(len(create), len(board.STANDARD_VIEWS))

    def test_every_standard_view_is_well_formed(self):
        for name, layout, flt, needs, manual in board.STANDARD_VIEWS:
            self.assertIn(layout, ("table", "board", "roadmap"), name)
            self.assertTrue(flt and manual, name)
        self.assertEqual(len({v[0] for v in board.STANDARD_VIEWS}), len(board.STANDARD_VIEWS))

    def test_field_mutations(self):
        q, v = board.field_mutation("P", board.STANDARD_FIELDS[0])
        self.assertIn("createProjectV2Field", q)
        self.assertEqual([o["name"] for o in v["i"]["singleSelectOptions"]], ["High", "Medium", "Low"])
        self.assertEqual(v["i"]["singleSelectOptions"][0]["color"], "RED")
        _, v = board.field_mutation("P", {"name": "Estimate", "type": "NUMBER"})
        self.assertNotIn("singleSelectOptions", v["i"])
        _, v = board.field_mutation("P", {"name": "Iteration", "type": "ITERATION"}, start=date(2026, 11, 9))
        self.assertEqual(v["i"]["iterationConfiguration"], {"startDate": "2026-11-09", "duration": 14, "iterations": []})
        _, v = board.field_mutation("P", {"name": "Iteration", "type": "ITERATION"})
        self.assertGreater(date.fromisoformat(v["i"]["iterationConfiguration"]["startDate"]), date.today() - timedelta(days=1))

    def test_next_monday(self):
        self.assertEqual(board.next_monday(date(2026, 11, 5)), date(2026, 11, 9))   # Thursday
        self.assertEqual(board.next_monday(date(2026, 11, 9)), date(2026, 11, 16))  # a Monday moves a week ahead


class Metrics(unittest.TestCase):
    def test_counts(self):
        items = [
            item("a", "Todo", 1, labels=["epic"], assignees=["me"], priority="High"),
            item("b", "In Progress", 2, labels=["blocked"]),
            item("c", "Done", 3),
            item("d", "Todo", 4, kind="PullRequest"),
            {"id": "D", "title": "draft", "content": {"type": "DraftIssue"}},
        ]
        updated = {1: NOW - timedelta(days=2), 2: NOW - timedelta(days=45), 4: NOW}
        m = board.metrics(items, updated, {1: (3, 5)}, now=NOW)
        self.assertEqual((m["total"], m["open"], m["prs"], m["drafts"]), (5, 4, 1, 1))
        self.assertEqual((m["no_assignee"], m["no_priority"], m["blocked"], m["stale"]), (3, 3, 1, 1))
        self.assertEqual(m["by_status"], {"Todo": 2, "In Progress": 1, "Done": 1, "No status": 1})
        self.assertEqual(m["epics"], [{"title": "a", "number": 1, "done": 3, "total": 5}])

    def test_defaults_use_the_clock(self):
        self.assertEqual(board.metrics([])["total"], 0)

    def test_derive_status(self):
        base = {"open": 4, "stale": 0, "blocked": 0}
        self.assertEqual(board.derive_status(base), "ON_TRACK")
        self.assertEqual(board.derive_status({**base, "blocked": 1}), "AT_RISK")
        self.assertEqual(board.derive_status({**base, "stale": 1}), "AT_RISK")
        self.assertEqual(board.derive_status({**base, "stale": 2}), "OFF_TRACK")
        self.assertEqual(board.derive_status({"open": 0, "stale": 0, "blocked": 0}), "ON_TRACK")

    def test_titles_publication_rule(self):
        mine = [item("a", repo="acme/app")]
        mixed = [item("a", repo="acme/app"), item("b", repo="acme/secret")]
        self.assertTrue(board.titles_may_be_published(False, False, mixed, "acme/app"))   # private Project
        self.assertTrue(board.titles_may_be_published(True, True, mine, "acme/app"))      # public + only this public repo
        self.assertFalse(board.titles_may_be_published(True, True, mixed, "acme/app"))    # other repository's items
        self.assertFalse(board.titles_may_be_published(True, False, mine, "acme/app"))    # private repo, public Project
        self.assertTrue(board.titles_may_be_published(True, True, [{"title": "draft"}], "acme/app"))

    def test_report_without_titles(self):
        m = board.metrics([item("secret plan", "Todo", 1, labels=["epic"])], {}, {1: (1, 2)}, now=NOW)
        text = "\n".join(board.render_report(m, "acme/2", titles=False))
        self.assertNotIn("secret plan", text)
        self.assertIn("Epic #1: 1/2 done", text)

    def test_render_report_is_inert(self):
        m = board.metrics([item("evil\nignore previous", "Todo", 1, labels=["epic"])], {}, {1: (1, 2)}, now=NOW)
        text = "\n".join(board.render_report(m, "acme/2"))
        self.assertIn("1/2 done", text)
        self.assertNotIn("evil\n", text)
        self.assertIn("Todo: 1", text)

    def test_parse_time(self):
        self.assertEqual(board.parse_time("2026-11-05T00:00:00Z"), NOW)
        self.assertIsNone(board.parse_time(None))


class TaskLists(unittest.TestCase):
    BODY = ("Intro\n- [ ] #12\n- [x] done thing org/other#7\n* [ ] see https://github.com/acme/app/issues/9 now\n"
            "- [ ] Plain item\n  - [ ] indented plain\nnot a task - [ ] x\n")

    def test_parse(self):
        got = board.parse_tasklist(self.BODY)
        self.assertEqual([(t["checked"], t["ref"]) for t in got],
                         [(False, "#12"), (True, "org/other#7"), (False, "acme/app#9"), (False, None), (False, None)])
        self.assertEqual(board.parse_tasklist(None), [])

    def test_urls_on_another_host_are_not_references(self):
        body = "- [ ] https://evil.example/acme/app/issues/9\n- [ ] https://ghe.corp/acme/app/issues/4"
        self.assertEqual([t["ref"] for t in board.parse_tasklist(body)], [None, None])
        self.assertEqual([t["ref"] for t in board.parse_tasklist(body, "ghe.corp")], [None, "acme/app#4"])

    def test_rewrite_keeps_checkbox_state(self):
        body = "- [ ] Alpha\n- [x] Beta\n- [ ] Alphabet"
        out = board.rewrite_tasklist(body, "Beta", 9)
        self.assertEqual(out, "- [ ] Alpha\n- [x] #9\n- [ ] Alphabet")

    def test_already_linked(self):
        self.assertTrue(board.already_linked("Issue may not contain duplicate sub-issues"))
        self.assertFalse(board.already_linked("boom"))


class GhHelpers(unittest.TestCase):
    def patch_run(self, rc=0, out="", err=""):
        return mock.patch.object(project, "run", return_value=(rc, out, err))

    def test_json_listing_helpers(self):
        with self.patch_run(out=json.dumps({"id": "P"})):
            self.assertEqual(board.project_info("acme", 2), {"id": "P"})
        with self.patch_run(out=json.dumps({"fields": [1]})):
            self.assertEqual(board.list_fields("acme", 2), [1])
        with self.patch_run(out=json.dumps({"items": [2]})):
            self.assertEqual(board.list_items("acme", 2), [2])
        for fn in (board.project_info, board.list_fields, board.list_items):
            with self.patch_run(rc=1, err="boom"):
                with self.assertRaises(RuntimeError):
                    fn("acme", 2)

    def test_list_views(self):
        with mock.patch.object(project, "gh_graphql", return_value={"node": {"views": {"nodes": [{"name": "x"}]}}}):
            self.assertEqual(board.list_views("P"), [{"name": "x"}])

    def test_create_view_uses_the_owner_type(self):
        with self.patch_run() as r:
            self.assertEqual(board.create_view(INFO, ("Bugs", "table", "label:bug", [], "")), (True, ""))
        args = r.call_args[0][0]
        self.assertIn("/users/acme/projectsV2/2/views", args)
        self.assertIn("filter=label:bug", args)
        org = {**INFO, "owner": {"login": "corp", "type": "Organization"}}
        with self.patch_run(rc=1, err="denied") as r:
            self.assertEqual(board.create_view(org, ("Bugs", "table", "x", [], "")), (False, "denied"))
        self.assertIn("/orgs/corp/projectsV2/2/views", r.call_args[0][0])

    def test_rename_view(self):
        with mock.patch.object(project, "gh_graphql") as g:
            self.assertEqual(board.rename_view("V", "All items"), (True, ""))
        self.assertEqual(g.call_args.kwargs, {"v": "V", "n": "All items"})
        with mock.patch.object(project, "gh_graphql", side_effect=RuntimeError("bad")):
            self.assertEqual(board.rename_view("V", "x"), (False, "bad"))

    def test_fetch_updated(self):
        def fake(args, timeout=60, input_text=None):
            return (0, json.dumps([{"number": 1 if args[1] == "issue" else 2, "updatedAt": "2026-11-05T00:00:00Z"}]), "")
        with mock.patch.object(project, "run", side_effect=fake):
            self.assertEqual(board.fetch_updated("acme/app"), {1: NOW, 2: NOW})
        with self.patch_run(rc=1, err="boom"):
            with self.assertRaises(RuntimeError):
                board.fetch_updated("acme/app")

    def test_epic_progress(self):
        items = [item("e", number=1, labels=["Epic"]), item("x", number=2), item("o", number=3, labels=["epic"], repo="acme/other")]
        with mock.patch.object(project, "fetch_tree", return_value={"summary": {"completed": 2, "total": 3}}) as t:
            self.assertEqual(board.epic_progress(items, "acme", "app"), {1: (2, 3)})
        t.assert_called_once_with("acme", "app", 1)
        with mock.patch.object(project, "fetch_tree", return_value={"summary": {}}):
            self.assertEqual(board.epic_progress(items[:1], "acme", "app"), {1: (0, 0)})

    def test_find_item(self):
        items = [item("a", number=1), item("b", number=1, repo="acme/other")]
        self.assertEqual(board.find_item(items, project.Ref(("acme", "other", 1)))["title"], "b")
        self.assertIsNone(board.find_item(items, project.Ref(("acme", "app", 9))))
        self.assertIsNone(board.find_item([{"title": "draft"}], project.Ref(("acme", "app", 1))))


class EditItem(unittest.TestCase):
    def edit(self, field, value):
        with mock.patch.object(project, "run", return_value=(0, "", "")) as r:
            ok = board.edit_item(INFO, "ITEM", field, value)
        return ok, r.call_args[0][0] if r.called else None

    def test_single_select(self):
        field = {"id": "F", "name": "Priority", "type": "ProjectV2SingleSelectField", "options": [{"id": "o1", "name": "High"}]}
        ok, args = self.edit(field, "high")
        self.assertEqual(ok, (True, ""))
        self.assertEqual(args[-2:], ["--single-select-option-id", "o1"])
        ok, args = self.edit(field, "urgent")
        self.assertFalse(ok[0])
        self.assertIn("High", ok[1])
        self.assertIsNone(args)

    def test_iteration(self):
        field = {"id": "F", "name": "Iteration", "type": "ProjectV2IterationField",
                 "configuration": {"iterations": [{"id": "i1", "title": "Sprint 1"}]}}
        self.assertEqual(self.edit(field, "sprint 1")[1][-2:], ["--iteration-id", "i1"])
        self.assertEqual(self.edit(field, "nope")[0], (False, "unknown iteration"))
        self.assertFalse(self.edit({"id": "F", "name": "Iteration", "type": "ProjectV2IterationField"}, "x")[0][0])

    def test_scalars(self):
        self.assertEqual(self.edit({"id": "F", "name": "Estimate", "type": "ProjectV2Field"}, "5")[1][-2:], ["--number", "5"])
        self.assertEqual(self.edit({"id": "F", "name": "Points", "type": "ProjectV2NumberField"}, "3")[1][-2:], ["--number", "3"])
        self.assertEqual(self.edit({"id": "F", "name": "Target date", "type": "ProjectV2Field"}, "2026-12-31")[1][-2:],
                         ["--date", "2026-12-31"])
        self.assertEqual(self.edit({"id": "F", "name": "Notes", "type": "ProjectV2Field"}, "hi")[1][-2:], ["--text", "hi"])

    def test_failure_is_reported(self):
        with mock.patch.object(project, "run", return_value=(1, "", "denied")):
            self.assertEqual(board.edit_item(INFO, "I", {"id": "F", "name": "Notes", "type": "x"}, "v"), (False, "denied"))


class Main(unittest.TestCase):
    def setUp(self):
        self.fields = [{"id": "F1", "name": "Priority", "type": "ProjectV2SingleSelectField", "options": [{"id": "o", "name": "High"}]},
                       {"id": "F2", "name": "Kind", "type": "ProjectV2SingleSelectField", "options": []},
                       {"id": "F3", "name": "Estimate", "type": "ProjectV2Field"}, {"id": "F4", "name": "Target date", "type": "ProjectV2Field"},
                       {"id": "F5", "name": "Iteration", "type": "ProjectV2IterationField"}, {"id": "F6", "name": "Status", "type": "ProjectV2SingleSelectField"}]
        self.items = [item("epic", number=1, labels=["epic"]), {"id": "D1", "title": "draft one", "content": {"type": "DraftIssue"}}]
        self.views = [{"id": "V0", "name": "View 1", "filter": None, "layout": "TABLE_LAYOUT"}]
        self.body = "- [ ] #3\n- [x] Plain thing\n- [ ] #4\n"
        patches = {
            "bootstrap": mock.patch.object(project, "bootstrap", return_value=("acme", "app", "acme/app", {"writable": True})),
            "project_for": mock.patch.object(project, "project_for", return_value=("acme", 2, "note")),
            "project_info": mock.patch.object(board, "project_info", return_value=INFO),
            "list_fields": mock.patch.object(board, "list_fields", side_effect=lambda o, n: self.fields),
            "list_items": mock.patch.object(board, "list_items", side_effect=lambda o, n: self.items),
            "list_views": mock.patch.object(board, "list_views", side_effect=lambda i: self.views),
            "create_view": mock.patch.object(board, "create_view", return_value=(True, "")),
            "rename_view": mock.patch.object(board, "rename_view", return_value=(True, "")),
            "fetch_updated": mock.patch.object(board, "fetch_updated", return_value={}),
            "epic_progress": mock.patch.object(board, "epic_progress", return_value={1: (1, 2)}),
            "gh_graphql": mock.patch.object(project, "gh_graphql"),
            "gh_graphql_json": mock.patch.object(project, "gh_graphql_json"),
            "set_parent": mock.patch.object(project, "set_parent", return_value=(True, "")),
            "add_to_project": mock.patch.object(project, "add_to_project", return_value=(True, "")),
            "run": mock.patch.object(project, "run", side_effect=self.fake_run),
        }
        self.m = {k: p.start() for k, p in patches.items()}
        for p in patches.values():
            self.addCleanup(p.stop)

    def fake_run(self, args, timeout=60, input_text=None):
        if args[:3] == ["gh", "issue", "view"]:
            return 0, self.body, ""
        if args[:3] == ["gh", "issue", "create"]:
            return 0, "https://github.com/acme/app/issues/21", ""
        if args[:3] == ["gh", "project", "item-create"]:
            return 0, json.dumps({"id": "NEW"}), ""
        if args[:3] == ["gh", "repo", "view"]:
            return 0, "R_1", ""
        return 0, "", ""

    def call(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = board.main(list(argv))
        return rc, out.getvalue(), err.getvalue()

    def test_fields(self):
        rc, out, _ = self.call("fields")
        self.assertEqual(rc, 0)
        self.assertIn("Priority (SingleSelect): High", out)
        self.assertIn("Estimate (Field)", out)
        self.m["bootstrap"].assert_called_once_with(None, writes=False)

    def test_setup(self):
        self.fields = self.fields[:2]
        rc, out, _ = self.call("setup")
        self.assertEqual(rc, 1)
        self.assertIn("would create field Estimate", out)
        self.m["gh_graphql_json"].assert_not_called()
        rc, out, _ = self.call("setup", "--apply")
        self.assertEqual(rc, 0)
        self.assertEqual(self.m["gh_graphql_json"].call_count, 3)
        self.m["gh_graphql_json"].side_effect = RuntimeError("reserved")
        rc, out, _ = self.call("setup", "--apply")
        self.assertEqual(rc, 2)
        self.assertIn("FAILED reserved", out)
        self.fields = list(board.STANDARD_FIELDS) and [{"name": f["name"]} for f in board.STANDARD_FIELDS]
        self.assertIn("All standard fields exist.", self.call("setup")[1])

    def test_views(self):
        saved, self.fields = self.fields, self.fields[:1]   # only Priority: Iteration/Target date views are skipped
        rc, out, _ = self.call("views")
        self.assertEqual(rc, 1)
        self.assertIn("would create view Board", out)
        self.assertIn("skipped, needs field(s) Iteration", out)
        self.assertIn("Built-in workflows cannot be enabled", out)
        self.m["create_view"].assert_not_called()
        self.fields = saved
        rc, out, _ = self.call("views", "--apply")
        self.assertEqual(rc, 0)
        self.assertIn("renamed 'View 1' -> 'All items'", out)
        self.assertIn("view Board: created   manual:", out)
        self.m["create_view"].return_value = (False, "nope")
        self.m["rename_view"].return_value = (False, "nope")
        self.assertEqual(self.call("views", "--apply")[0], 2)

    def test_views_when_everything_exists(self):
        self.views = [{"id": "V", "name": v[0], "filter": v[2], "layout": "x"} for v in board.STANDARD_VIEWS]
        self.fields = [{"name": "Iteration"}, {"name": "Target date"}, {"name": "Priority"}]
        rc, out, _ = self.call("views", "--apply")
        self.assertEqual(rc, 0)
        self.m["create_view"].assert_not_called()

    def test_report_and_post(self):
        rc, out, _ = self.call("report")
        self.assertEqual(rc, 0)
        self.assertIn("Epic #1", out)
        self.assertIn("1/2 done", out)
        self.m["bootstrap"].assert_called_with(None, writes=False)
        self.m["gh_graphql_json"].assert_not_called()
        rc, out, _ = self.call("report", "--post", "--status", "AT_RISK")
        self.assertIn("status update posted: AT_RISK", out)
        self.m["bootstrap"].assert_called_with(None, writes=True)
        variables = self.m["gh_graphql_json"].call_args[0][1]["i"]
        self.assertEqual((variables["projectId"], variables["status"]), ("PVT_1", "AT_RISK"))
        self.assertIn("Project acme/2", variables["body"])
        self.assertNotIn('"epic"', variables["body"])   # counts only by default: no titles in a published update
        rc, out, _ = self.call("report", "--post")
        self.assertIn("status update posted: ON_TRACK", out)

    def test_post_with_titles_is_refused_when_it_could_leak(self):
        self.m["bootstrap"].return_value = ("acme", "app", "acme/app", {"writable": True, "visibility": "public"})
        self.items = [item("epic", number=1, labels=["epic"], repo="acme/secret")]
        with mock.patch.object(project, "project_visibility", return_value="PUBLIC"):
            rc, _, err = self.call("report", "--post", "--with-titles")
            self.assertEqual((rc, "refused" in err), (2, True))
            self.m["gh_graphql_json"].assert_not_called()
            rc, out, _ = self.call("report", "--post")                      # counts only is always allowed
            self.assertEqual(rc, 0)
        self.items = [item("epic", number=1, labels=["epic"], repo="acme/app")]
        with mock.patch.object(project, "project_visibility", return_value="PUBLIC"):
            self.assertEqual(self.call("report", "--post", "--with-titles")[0], 0)
        self.assertIn('"epic"', self.m["gh_graphql_json"].call_args[0][1]["i"]["body"])

    def test_post_with_titles_fails_closed_when_visibility_is_unknown(self):
        with mock.patch.object(project, "project_visibility", return_value=None):
            rc, _, err = self.call("report", "--post", "--with-titles")
        self.assertEqual((rc, "cannot determine the Project visibility" in err), (2, True))
        self.m["gh_graphql_json"].assert_not_called()

    def test_set(self):
        rc, out, _ = self.call("set", "1", "--field", "priority", "--value", "High")
        self.assertEqual((rc, "Priority = High: ok" in out), (0, True))
        self.assertEqual(self.call("set", "1", "--field", "Priority", "--value", "Nope")[0], 2)
        rc, _, err = self.call("set", "9", "--field", "Priority", "--value", "High")
        self.assertEqual((rc, "not in the Project" in err), (2, True))
        rc, _, err = self.call("set", "1", "--field", "Ghost", "--value", "x", "--pr")
        self.assertEqual((rc, "unknown field" in err), (2, True))

    def test_drafts(self):
        rc, out, _ = self.call("draft", "Plan", "--body", "later")
        self.assertEqual((rc, "draft item created: NEW" in out), (0, True))
        with mock.patch.object(project, "run", return_value=(1, "", "denied")):
            self.assertEqual(self.call("draft", "Plan")[0], 2)
        rc, out, _ = self.call("drafts")
        self.assertIn('D1 "draft one"', out)
        self.assertIn("1 draft item(s)", out)

    def test_convert(self):
        self.m["gh_graphql"].return_value = {"convertProjectV2DraftIssueItemToIssue": {"item": {"content": {"url": "U"}}}}
        rc, out, _ = self.call("convert", "D1")
        self.assertEqual((rc, "converted: U" in out), (0, True))
        self.assertEqual(self.m["gh_graphql"].call_args.kwargs, {"i": "D1", "r": "R_1"})
        with mock.patch.object(project, "run", return_value=(1, "", "denied")):
            self.assertEqual(self.call("convert", "D1")[0], 2)

    def test_tasklist_dry_run_and_link(self):
        rc, out, _ = self.call("tasklist", "10")
        self.assertEqual(rc, 1)
        self.assertIn("would link acme/app#3 as sub-issue of acme/app#10", out)
        self.assertIn("skipped plain item", out)
        self.m["set_parent"].assert_not_called()
        rc, out, _ = self.call("tasklist", "10", "--apply")
        self.assertEqual(rc, 0)
        self.assertEqual(self.m["set_parent"].call_count, 2)

    def test_tasklist_cross_repository_references_need_a_flag(self):
        self.body = "- [ ] #3\n- [ ] other/repo#7\n"
        rc, out, _ = self.call("tasklist", "10", "--apply")
        self.assertEqual(rc, 0)
        self.assertIn("skipped other/repo#7: another repository", out)
        self.assertEqual(self.m["set_parent"].call_count, 1)
        self.call("tasklist", "10", "--apply", "--allow-cross-repo")
        self.assertEqual(self.m["set_parent"].call_count, 3)

    def test_tasklist_already_linked_and_failure(self):
        self.m["set_parent"].return_value = (False, "may not contain duplicate sub-issues")
        rc, out, _ = self.call("tasklist", "10", "--apply")
        self.assertEqual(rc, 0)
        self.assertIn("already a sub-issue", out)
        self.m["set_parent"].return_value = (False, "boom")
        self.assertEqual(self.call("tasklist", "10", "--apply")[0], 2)

    def test_tasklist_create(self):
        rc, out, _ = self.call("tasklist", "10", "--create")
        self.assertEqual(rc, 1)
        self.assertIn("would create an issue from", out)
        rc, out, _ = self.call("tasklist", "10", "--apply", "--create")
        self.assertEqual(rc, 0)
        self.assertIn("acme/app#21 created, sub-issue: ok, project: ok; it is checked in the list", out)
        edit = [c for c in self.m["run"].call_args_list if c.args[0][:3] == ["gh", "issue", "edit"]]
        self.assertEqual(edit[0].kwargs["input_text"], "- [ ] #3\n- [x] #21\n- [ ] #4\n")

    def test_tasklist_create_failures(self):
        self.m["set_parent"].return_value = (False, "bad")
        self.m["add_to_project"].return_value = (False, "bad")

        def run(args, timeout=60, input_text=None):
            if args[:3] == ["gh", "issue", "create"]:
                return (1, "", "denied") if self.fail_create else (0, "https://github.com/acme/app/issues/21", "")
            if args[:3] == ["gh", "issue", "edit"]:
                return 1, "", "no edit"
            return self.fake_run(args, timeout, input_text)
        with mock.patch.object(project, "run", side_effect=run):
            self.fail_create = True
            rc, out, _ = self.call("tasklist", "10", "--apply", "--create")
            self.assertEqual(rc, 2)
            self.assertIn("FAILED denied", out)
            self.fail_create = False
            rc, out, _ = self.call("tasklist", "10", "--apply", "--create")
            self.assertEqual(rc, 2)
            self.assertIn("epic body not updated", out)

    def test_tasklist_without_tasks_or_epic(self):
        self.body = "nothing here"
        self.assertIn("No task list", self.call("tasklist", "10")[1])
        with mock.patch.object(project, "run", return_value=(1, "", "gone")):
            self.assertEqual(self.call("tasklist", "10")[0], 2)

    def test_error_paths(self):
        self.m["bootstrap"].side_effect = project.Stop(4, "scope")
        self.assertEqual(self.call("fields")[0], 4)
        self.m["bootstrap"].side_effect = project.Undetermined("ask")
        self.assertEqual(self.call("fields")[0], 3)
        self.m["bootstrap"].side_effect = RuntimeError("boom")
        self.assertEqual(self.call("fields")[0], 2)


class EntryPoint(unittest.TestCase):
    def test_runs_as_a_program(self):
        with mock.patch.object(sys, "argv", ["board.py", "no-such-command"]), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as e:
                runpy.run_path(str(ROOT / "skills" / "project-board" / "board.py"), run_name="__main__")
        self.assertEqual(e.exception.code, 2)


class ProjectAdditions(unittest.TestCase):
    """Helpers added to project.py for board.py."""

    def test_gh_graphql_json(self):
        with mock.patch.object(project, "run", return_value=(0, json.dumps({"data": {"ok": 1}}), "")) as r:
            self.assertEqual(project.gh_graphql_json("q", {"a": {"b": [1]}}), {"ok": 1})
        self.assertEqual(json.loads(r.call_args.kwargs["input_text"]), {"query": "q", "variables": {"a": {"b": [1]}}})
        with mock.patch.object(project, "run", return_value=(1, "", "boom")):
            with self.assertRaises(RuntimeError):
                project.gh_graphql_json("q", {})
        with mock.patch.object(project, "run", return_value=(0, json.dumps({"errors": [{"message": "x"}]}), "")):
            with self.assertRaises(RuntimeError):
                project.gh_graphql_json("q", {})

    def test_run_passes_stdin(self):
        import subprocess
        ok = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        with mock.patch.object(subprocess, "run", return_value=ok) as r:
            project.run(["x"], input_text="body")
        self.assertEqual(r.call_args.kwargs["input"], "body")


if __name__ == "__main__":
    unittest.main()
