import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("project", ROOT / "skills" / "issue-lifecycle" / "project.py")
project = importlib.util.module_from_spec(spec)
spec.loader.exec_module(project)


def issue(n, labels=(), parent=None, subs=0, projects=()):
    return {"number": n, "title": f"t{n}", "labels": {"nodes": [{"name": x} for x in labels]},
            "parent": {"number": parent} if parent else None, "subIssues": {"totalCount": subs},
            "projectItems": {"nodes": [{"project": {"number": pn, "owner": {"login": po}}} for po, pn in projects]}}


class Scopes(unittest.TestCase):
    def test_write_scope_required(self):
        self.assertTrue(project.has_project_scope("  - Token scopes: 'gist', 'project', 'repo'"))
        self.assertFalse(project.has_project_scope("  - Token scopes: 'gist', 'read:project', 'repo'"))
        self.assertFalse(project.has_project_scope("  - Token scopes: 'gist', 'repo'"))


class PickProject(unittest.TestCase):
    def test_note_wins(self):
        self.assertEqual(project.pick_project("acme/3", [{"owner": "x", "number": 9}], []), ("acme", 3, "note"))

    def test_single_linked(self):
        p = {"owner": "acme", "number": 2, "closed": False}
        self.assertEqual(project.pick_project(None, [p], []), ("acme", 2, "linked"))

    def test_closed_ignored_falls_back_to_owner(self):
        closed = {"owner": "acme", "number": 1, "closed": True}
        opened = {"owner": "acme", "number": 4, "closed": False}
        self.assertEqual(project.pick_project(None, [closed], [opened]), ("acme", 4, "owner"))

    def test_ambiguous_or_missing_asks_user(self):
        two = [{"owner": "a", "number": 1}, {"owner": "a", "number": 2}]
        with self.assertRaises(project.Undetermined):
            project.pick_project(None, two, [])
        with self.assertRaises(project.Undetermined):
            project.pick_project(None, [], [])


class Classify(unittest.TestCase):
    def test_orphans(self):
        issues = [
            issue(1, projects=[("acme", 2)], parent=10),  # fine
            issue(2, projects=[("acme", 2)]),             # no epic
            issue(3, parent=10),                          # outside project
            issue(10, labels=["epic"], projects=[("acme", 2)]),   # epic: exempt from parent rule
            issue(11, subs=2, projects=[("acme", 2)]),    # has sub-issues: treated as epic
            issue(4, projects=[("other", 2)], parent=10),  # same number, other owner: outside
        ]
        no_project, no_epic = project.classify(issues, "acme", 2)
        self.assertEqual([i["number"] for i in no_project], [3, 4])
        self.assertEqual([i["number"] for i in no_epic], [2])


if __name__ == "__main__":
    unittest.main()
