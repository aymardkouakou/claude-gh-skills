# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Aymard Kouakou - see NOTICE
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("ctx_cli", ROOT / "skills" / "repo-context" / "ctx.py")
ctx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ctx)

VIEW = {"nameWithOwner": "acme/app", "url": "https://github.com/acme/app", "isPrivate": False, "defaultBranchRef": {"name": "main"},
        "viewerPermission": "WRITE", "hasIssuesEnabled": True, "isFork": False, "visibility": "PUBLIC", "isInOrganization": True,
        "isArchived": False, "hasProjectsEnabled": True}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        ctx.STATE, ctx.REPOS, ctx.LAST, ctx.CONFIG = base, base / "repos", base / "last.json", base / "config.json"
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("GH_REPO", None)

    def cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = ctx.main(list(argv))
        return rc, out.getvalue(), err.getvalue()


class RunWrapper(unittest.TestCase):
    def test_outcomes(self):
        ok = subprocess.CompletedProcess([], 0, stdout=" o ", stderr=" e ")
        with mock.patch.object(subprocess, "run", return_value=ok):
            self.assertEqual(ctx.run(["x"]), (0, "o", "e"))
        with mock.patch.object(subprocess, "run", side_effect=FileNotFoundError):
            self.assertEqual(ctx.run(["gh"]), (127, "", "gh not found"))
        with mock.patch.object(subprocess, "run", side_effect=subprocess.TimeoutExpired("x", 1)):
            self.assertEqual(ctx.run(["x"]), (124, "", "timeout"))


class Detect(Base):
    def test_profile_fields_from_gh(self):
        with mock.patch.object(ctx, "run", return_value=(0, json.dumps(VIEW), "")):
            info, source = ctx.detect(None, "/x")
        self.assertEqual(source, "gh")
        self.assertEqual((info["visibility"], info["in_org"], info["archived"], info["projects_enabled"]), ("public", True, False, True))

    def test_explicit_source_and_missing_visibility(self):
        view = {**VIEW}
        view.pop("visibility")
        with mock.patch.object(ctx, "run", return_value=(0, json.dumps(view), "")):
            info, source = ctx.detect("acme/app", "/x")
        self.assertEqual((source, info["visibility"]), ("explicit", None))

    def test_malformed_gh_output_falls_through(self):
        with mock.patch.object(ctx, "run", side_effect=[(0, "not json", ""), (1, "", "")]):
            self.assertEqual(ctx.detect(None, "/x"), (None, None))

    def test_explicit_unverified_url_and_pair(self):
        fail = (1, "", "no")
        with mock.patch.object(ctx, "run", return_value=fail):
            info, source = ctx.detect("https://ghe.corp/acme/app.git", "/x")
            self.assertEqual((source, info["host"], info["repo"]), ("explicit-unverified", "ghe.corp", "app"))
            info, source = ctx.detect("acme/app", "/x")
            self.assertEqual((source, info["host"]), ("explicit-unverified", "github.com"))

    def test_explicit_unusable_then_git_remote(self):
        def fake(args, cwd=None, timeout=20):
            return (0, "git@github.com:acme/app.git", "") if args[0] == "git" else (1, "", "no")
        with mock.patch.object(ctx, "run", fake):
            info, source = ctx.detect("single", "/x")
        self.assertEqual((source, info["owner"]), ("git-remote", "acme"))

    def test_unparsable_git_remote_then_remembered(self):
        ctx.save(ctx.REPOS / "github.com__a__b.json", {"host": "github.com", "owner": "a", "repo": "b", "private": True})
        ctx.save(ctx.LAST, {"key": "github.com__a__b"})
        with mock.patch.object(ctx, "run", side_effect=[(1, "", ""), (0, "???", "")]):
            info, source = ctx.detect(None, "/x")
        self.assertEqual((source, info["repo"]), ("remembered", "b"))


class Resolve(Base):
    def test_kind_is_returned_and_unknown_type_is_flagged(self):
        with mock.patch.object(ctx, "run", return_value=(0, json.dumps(VIEW), "")):
            r = ctx.resolve(cwd="/x", touch=False)
        self.assertEqual((r["kind"]["owner_type"], r["kind"]["visibility"]), ("organization", "public"))
        self.assertNotIn("kind_hint", r)
        self.assertIn("language_hint", r)
        with mock.patch.object(ctx, "run", side_effect=[(1, "", ""), (0, "https://github.com/acme/app", ""), (1, "", "")]):
            r = ctx.resolve(cwd="/x", touch=False)
        self.assertIn("kind_hint", r)
        self.assertEqual(r["kind"]["writable"], False)


class Rules(unittest.TestCase):
    def rules(self, **rec):
        return " | ".join(ctx.classify_repo(rec)["rules"])

    def test_every_rule_fires(self):
        self.assertIn("Organization repository", self.rules(in_org=True))
        self.assertIn("Internal", self.rules(visibility="internal"))
        self.assertIn("Private", self.rules(visibility="private"))
        self.assertIn("Fork", self.rules(fork=True))
        self.assertIn("Archived", self.rules(archived=True))
        self.assertIn("Issues are disabled", self.rules(issues_enabled=False))
        self.assertIn("Projects are disabled", self.rules(projects_enabled=False))
        self.assertIn("comment only", self.rules(permission="READ"))
        self.assertIn("can label and triage", self.rules(permission="TRIAGE"))

    def test_nothing_to_say_for_a_plain_writable_repo(self):
        self.assertEqual(ctx.classify_repo({"permission": "WRITE", "visibility": "public"})["rules"][0][:6], "Public")


class Cli(Base):
    def seed(self):
        with mock.patch.object(ctx, "run", return_value=(0, json.dumps(VIEW), "")):
            return self.cli("resolve")

    def test_resolve_and_repo(self):
        with mock.patch.object(ctx, "run", return_value=(0, json.dumps(VIEW), "")):
            rc, out, _ = self.cli("resolve")
            self.assertEqual((rc, json.loads(out)["kind"]["owner_type"]), (0, "organization"))
            self.assertEqual(self.cli("repo")[1].strip(), "acme/app")
            self.assertEqual(self.cli("repo", "--no-touch")[0], 0)

    def test_no_repository(self):
        with mock.patch.object(ctx, "run", return_value=(1, "", "")):
            rc, _, err = self.cli("resolve")
        self.assertEqual(rc, 2)
        self.assertIn("No repository found", err)

    def test_unverified_repo_refused_unless_allowed(self):
        ctx.save(ctx.REPOS / "github.com__a__b.json", {"host": "github.com", "owner": "a", "repo": "b"})
        ctx.save(ctx.LAST, {"key": "github.com__a__b"})
        with mock.patch.object(ctx, "run", return_value=(1, "", "")):
            self.assertEqual(self.cli("repo")[0], 5)
            self.assertEqual(self.cli("repo", "--allow-unverified")[1].strip(), "a/b")

    def test_commands_need_an_active_repository(self):
        for cmd in (("show",), ("note", "k", "v"), ("labels",)):
            self.assertEqual(self.cli(*cmd)[0], 2, cmd)
        self.assertEqual(self.cli("lang", "set", "fr")[0], 2)

    def test_show_note_and_secret_refusal(self):
        self.seed()
        self.assertEqual(self.cli("note", "project", "acme/3")[0], 0)
        self.assertEqual(json.loads(self.cli("show")[1])["notes"]["project"], "acme/3")
        self.assertEqual(self.cli("note", "k", "password=SuperSecret12345")[0], 3)

    def test_labels_cache_refresh_and_failure(self):
        self.seed()
        labels = json.dumps([{"name": "epic"}, {"name": "bug"}])
        with mock.patch.object(ctx, "run", return_value=(0, labels, "")) as r:
            self.assertEqual(self.cli("labels")[1].split(), ["bug", "epic"])
            self.cli("labels")
            self.assertEqual(r.call_count, 1)  # cached
            self.cli("labels", "--refresh")
            self.assertEqual(r.call_count, 2)
        with mock.patch.object(ctx, "run", return_value=(4, "", "denied")):
            self.assertEqual(self.cli("labels", "--refresh")[0], 4)

    def test_list_and_forget(self):
        self.seed()
        rc, out, _ = self.cli("list")
        self.assertIn("acme/app", out)
        self.assertEqual(self.cli("forget", "acme/app")[0], 0)
        self.assertEqual(self.cli("list")[1], "")
        self.assertEqual(self.cli("forget", "ghe.corp/x/y")[0], 0)  # unknown target: nothing to remove

    def test_forget_active_repository(self):
        self.seed()
        rc, out, _ = self.cli("forget")
        self.assertIn("forgotten", out)
        self.assertFalse(ctx.LAST.exists())

    def test_active_record_without_last(self):
        self.assertEqual(ctx.active_record(), (None, None))

    def test_lang_global_and_repository(self):
        self.seed()
        self.assertEqual(self.cli("lang", "set", "fr", "--global")[0], 0)
        self.assertEqual(self.cli("lang")[1].strip(), "fr")
        self.assertEqual(self.cli("lang", "set", "en", "--commit")[0], 0)
        self.assertEqual(self.cli("lang", "--commit")[1].strip(), "en")
        self.assertEqual(self.cli("lang", "set")[0], 2)

    def test_unknown_dispatch_returns_1(self):
        self.seed()
        with mock.patch.object(ctx.argparse.ArgumentParser, "parse_args", return_value=mock.Mock(cmd="other")):
            self.assertEqual(ctx.main([]), 1)


if __name__ == "__main__":
    unittest.main()
