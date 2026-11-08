# SPDX-License-Identifier: LicenseRef-claude-gh-skills-1.1
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
spec = importlib.util.spec_from_file_location("scan_secrets", ROOT / "skills" / "secrets-hygiene" / "scan_secrets.py")
ss = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ss)

AWS = "AKIA" + "B" * 16
GH = "ghp_" + "c" * 36
CRED = 'db_password = "' + "Zq8" + "w9" * 5 + '"'


def rules(text):
    return [r for _, r in ss.scan_text(text)]


class Rules(unittest.TestCase):
    def test_detects_each_family(self):
        self.assertEqual(rules(AWS), ["aws-access-key-id"])
        self.assertEqual(rules("t=" + GH), ["github-token"])
        self.assertEqual(rules("github_pat_" + "a" * 60), ["github-fine-grained-token"])
        self.assertEqual(rules("xoxb-" + "1" * 12), ["slack-token"])
        self.assertEqual(rules("sk_live_" + "a" * 20), ["stripe-live-key"])
        self.assertEqual(rules("-----BEGIN RSA PRIVATE KEY-----"), ["private-key-block"])  # secret-scan: ignore
        self.assertEqual(rules("postgres://app:Zq8wxyz1@db/x"), ["credential-in-url"])  # secret-scan: ignore
        self.assertEqual(rules(CRED), ["hard-coded-credential"])

    def test_ignores_placeholders_and_marked_lines(self):
        for t in ['password = "changeme123"', 'token: "${TOKEN_VALUE}"', 'api_key = "your-api-key-here"',
                  "postgres://user:<password>@db/x", AWS + "  # secret-scan: ignore", "no secret here"]:
            self.assertEqual(rules(t), [], t)

    def test_line_numbers(self):
        self.assertEqual(list(ss.scan_text("ok\n" + AWS)), [(2, "aws-access-key-id")])

    def test_values_are_never_printed(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "a.py").write_text(CRED + "\n" + AWS + "\n")
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                self.assertEqual(ss.main([d]), 1)
            self.assertIn("a.py:1: hard-coded-credential", out.getvalue())
            self.assertNotIn("Zq8", out.getvalue() + err.getvalue())
            self.assertNotIn(AWS, out.getvalue() + err.getvalue())


class Scan(unittest.TestCase):
    def test_walk_fallback_skips_noise_and_flags_file_names(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / ".env").write_text("A=1\n")
            (p / ".env.example").write_text("A=1\n")
            (p / "node_modules").mkdir()
            (p / "node_modules" / "x.js").write_text(AWS)
            (p / "bin.dat").write_bytes(b"\0" + AWS.encode())
            (p / "big.txt").write_text(AWS + " " * ss.MAX_BYTES)
            (p / "ok.txt").write_text("nothing\n")
            found = {(f["path"], f["rule"]) for f in ss.scan(d)}
            self.assertEqual(found, {(".env", "suspicious-file-name")})

    def test_unreadable_file_is_skipped(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "a.txt").write_text(AWS)
            with mock.patch("builtins.open", side_effect=OSError):
                self.assertEqual(ss.scan(d), [])

    def test_git_tracked_files_only(self):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(["git", "init", "-q", d], check=True)
            Path(d, "tracked.txt").write_text(AWS)
            Path(d, "untracked.txt").write_text(AWS)
            subprocess.run(["git", "-C", d, "add", "tracked.txt"], check=True)
            self.assertEqual([f["path"] for f in ss.scan(d)], ["tracked.txt"])

    def test_missing_git_falls_back_to_walk(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "a.txt").write_text(AWS)
            with mock.patch.object(subprocess, "run", side_effect=OSError):
                self.assertEqual(len(ss.scan(d)), 1)


class Main(unittest.TestCase):
    def test_json_and_exit_zero(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "a.txt").write_text(AWS)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(ss.main([d, "--json", "--exit-zero"]), 0)
            self.assertEqual(json.loads(out.getvalue())[0]["rule"], "aws-access-key-id")

    def test_clean_tree_exits_zero(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "a.txt").write_text("fine\n")
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(ss.main([d]), 0)


if __name__ == "__main__":
    unittest.main()
