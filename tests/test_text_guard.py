# SPDX-License-Identifier: LicenseRef-claude-gh-skills-1.1
# Copyright 2026 Aymard Kouakou - see NOTICE
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("text_guard", ROOT / "skills" / "issue-lifecycle" / "text_guard.py")
tg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tg)


class TextGuard(unittest.TestCase):
    def test_flags_secrets(self):
        for t in ["password=SuperSecret12345", "token: abcdefgh12345678", "ghp_" + "a" * 20, "-----BEGIN RSA PRIVATE KEY-----",  # secret-scan: ignore
                  "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9", "AKIA" + "A" * 12]:
            self.assertTrue(tg.looks_secret(t), t)

    def test_accepts_normal_text(self):
        for t in ["Kong route /webhooks refused (400)", "variable DB_PASSWORD is mandatory", "CI run 123 failed at step build"]:
            self.assertFalse(tg.looks_secret(t), t)


if __name__ == "__main__":
    unittest.main()
