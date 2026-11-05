import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("ctx", ROOT / "skills" / "repo-context" / "ctx.py")
ctx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ctx)


class ParseRemote(unittest.TestCase):
    def test_formats(self):
        cases = {
            "https://github.com/acme/app.git": ("github.com", "acme", "app"),
            "https://github.com/acme/app": ("github.com", "acme", "app"),
            "git@github.com:acme/app.git": ("github.com", "acme", "app"),
            "ssh://git@github.com/acme/app.git": ("github.com", "acme", "app"),
            "ssh://git@ghe.example.com:22/acme/app.git": ("ghe.example.com", "acme", "app"),
            "https://user@github.com/acme/my.repo.git": ("github.com", "acme", "my.repo"),
        }
        for url, (h, o, r) in cases.items():
            p = ctx.parse_remote(url)
            self.assertEqual((p["host"], p["owner"], p["repo"]), (h, o, r), url)

    def test_invalid(self):
        self.assertIsNone(ctx.parse_remote(""))
        self.assertIsNone(ctx.parse_remote("not a url"))

    def test_full_name(self):
        self.assertEqual(ctx.full_name("github.com", "a", "b"), "a/b")
        self.assertEqual(ctx.full_name("ghe.corp", "a", "b"), "ghe.corp/a/b")


class Memory(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        ctx.STATE, ctx.REPOS, ctx.LAST = base, base / "repos", base / "last.json"

    def tearDown(self):
        self.tmp.cleanup()

    def fake_run(self, args, cwd=None, timeout=20):
        if args[:3] == ["gh", "repo", "view"]:
            return 0, json.dumps({"nameWithOwner": "acme/app", "url": "https://github.com/acme/app", "isPrivate": True,
                                  "defaultBranchRef": {"name": "main"}, "viewerPermission": "WRITE"}), ""
        if args[:3] == ["gh", "auth", "status"]:
            return 0, "", ""
        return 1, "", "nope"

    def test_resolve_remembers_and_counts(self):
        with mock.patch.object(ctx, "run", self.fake_run), mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("GH_REPO", None)
            a = ctx.resolve(cwd="/tmp/x")
            b = ctx.resolve(cwd="/tmp/x")
        self.assertEqual((a["full"], a["default_branch"], a["permission"], a["source"]), ("acme/app", "main", "WRITE", "gh"))
        self.assertTrue(a["authenticated"])
        self.assertEqual(b["uses"], 2)
        self.assertEqual(json.loads(ctx.LAST.read_text())["repo"], "acme/app")

    def test_falls_back_to_remembered_with_warning(self):
        with mock.patch.object(ctx, "run", self.fake_run):
            os.environ.pop("GH_REPO", None)
            ctx.resolve(cwd="/tmp/x")
        with mock.patch.object(ctx, "run", lambda *a, **k: (1, "", "fail")):
            r = ctx.resolve(cwd="/tmp/elsewhere", touch=False)
        self.assertEqual(r["source"], "remembered")
        self.assertIn("warning", r)

    def test_no_repo_returns_none(self):
        with mock.patch.object(ctx, "run", lambda *a, **k: (1, "", "fail")):
            os.environ.pop("GH_REPO", None)
            self.assertIsNone(ctx.resolve(cwd="/tmp/none"))

    def test_note_refuses_secrets(self):
        self.assertTrue(ctx.looks_secret("password=SuperSecret12345"))
        self.assertTrue(ctx.looks_secret("ghp_" + "a" * 20))
        self.assertFalse(ctx.looks_secret("PRs go develop to sandbox to main"))


class Classify(unittest.TestCase):
    def test_personal_private(self):
        k = ctx.classify_repo({"visibility": "private", "in_org": False, "permission": "ADMIN"})
        self.assertEqual((k["owner_type"], k["visibility"], k["writable"]), ("personal", "private", True))
        self.assertTrue(any("Personal" in r for r in k["rules"]))

    def test_org_public(self):
        k = ctx.classify_repo({"visibility": "public", "in_org": True, "permission": "WRITE"})
        self.assertEqual(k["owner_type"], "organization")
        self.assertTrue(any("world-readable" in r for r in k["rules"]))

    def test_not_writable(self):
        self.assertFalse(ctx.classify_repo({"in_org": False, "archived": True, "permission": "ADMIN"})["writable"])
        self.assertFalse(ctx.classify_repo({"in_org": True, "permission": "READ"})["writable"])
        self.assertFalse(ctx.classify_repo({"in_org": True, "permission": "WRITE", "issues_enabled": False})["writable"])

    def test_unknown_is_not_guessed(self):
        k = ctx.classify_repo({})
        self.assertIsNone(k["owner_type"])
        self.assertFalse(k["writable"])

    def test_legacy_private_flag(self):
        self.assertEqual(ctx.classify_repo({"private": True})["visibility"], "private")


if __name__ == "__main__":
    unittest.main()


class Language(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        ctx.STATE, ctx.REPOS, ctx.LAST, ctx.CONFIG = base, base / "repos", base / "last.json", base / "config.json"
        for k in ("CLAUDE_SKILL_LANG", "CLAUDE_SKILL_COMMIT_LANG"):
            os.environ.pop(k, None)

    def tearDown(self):
        self.tmp.cleanup()

    def test_resolution_order(self):
        rec = {"settings": {"language": "fr"}}
        self.assertIsNone(ctx.get_language({}))
        self.assertEqual(ctx.get_language({}, commit=True), "en")
        ctx.save(ctx.CONFIG, {"language": "es", "commit_language": "fr"})
        self.assertEqual(ctx.get_language({}), "es")
        self.assertEqual(ctx.get_language(rec), "fr")           # repository beats global
        self.assertEqual(ctx.get_language(rec, commit=True), "fr")
        with mock.patch.dict(os.environ, {"CLAUDE_SKILL_LANG": "pt-BR"}):
            self.assertEqual(ctx.get_language(rec), "pt-BR")    # env beats everything

    def test_rejects_invalid_codes(self):
        self.assertFalse(ctx.LANG_RE.match("french"))
        self.assertFalse(ctx.LANG_RE.match("FR"))
        self.assertTrue(ctx.LANG_RE.match("pt-BR"))

    def test_cli_set_and_get(self):
        key = "github.com__a__b"
        ctx.save(ctx.REPOS / (key + ".json"), {"host": "github.com", "owner": "a", "repo": "b"})
        ctx.save(ctx.LAST, {"key": key})
        self.assertEqual(ctx.main(["lang"]), 3)                 # unset
        self.assertEqual(ctx.main(["lang", "set", "fr"]), 0)
        self.assertEqual(ctx.main(["lang"]), 0)
        self.assertEqual(ctx.load(ctx.REPOS / (key + ".json"))["settings"]["language"], "fr")
        self.assertEqual(ctx.main(["lang", "set", "xx1"]), 2)


class UnverifiedRepoIsRefused(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        ctx.STATE, ctx.REPOS, ctx.LAST, ctx.CONFIG = base, base / "repos", base / "last.json", base / "config.json"
        os.environ.pop("GH_REPO", None)

    def tearDown(self):
        self.tmp.cleanup()

    def test_repo_command_refuses_remembered(self):
        ctx.save(ctx.REPOS / "github.com__a__b.json", {"host": "github.com", "owner": "a", "repo": "b"})
        ctx.save(ctx.LAST, {"key": "github.com__a__b"})
        with mock.patch.object(ctx, "run", lambda *a, **k: (1, "", "fail")):
            self.assertEqual(ctx.main(["repo", "--no-touch"]), 5)
            self.assertEqual(ctx.main(["repo", "--no-touch", "--allow-unverified"]), 0)

    def test_repo_command_accepts_gh_confirmed(self):
        def fake(args, cwd=None, timeout=20):
            if args[:3] == ["gh", "repo", "view"]:
                return 0, json.dumps({"nameWithOwner": "a/b", "url": "https://github.com/a/b"}), ""
            return 0, "", ""
        with mock.patch.object(ctx, "run", fake):
            self.assertEqual(ctx.main(["repo", "--no-touch"]), 0)
