# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Aymard Kouakou - see NOTICE
"""Repository conventions: English-only skills, frontmatter, no secrets or addresses."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = sorted(p for p in (ROOT / "skills").iterdir() if p.is_dir())
FRENCH_WORDS = re.compile(r"\b(les|des|une|pour|dans|avec|est|sont|vous|jamais|toujours|sans|être|faire|cette|aux)\b", re.I)
IPV4 = re.compile(r"\b(?!127\.|0\.|10\.|192\.168\.)\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")


def split(text):
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    return (m.group(1), m.group(2)) if m else (None, text)


class Conventions(unittest.TestCase):
    def test_every_skill_has_valid_frontmatter(self):
        for d in SKILLS:
            fm, _ = split((d / "SKILL.md").read_text(encoding="utf-8"))
            self.assertIsNotNone(fm, d.name)
            self.assertRegex(fm, rf"(?m)^name: {re.escape(d.name)}$", d.name)
            self.assertRegex(fm, r"(?m)^description: .{60,}", d.name)

    def test_markdown_is_english(self):
        for d in SKILLS:
            for f in [*d.rglob("*.md")]:
                _, body = split(f.read_text(encoding="utf-8"))
                body = re.sub(r"`[^`]*`|```.*?```", "", body, flags=re.S)
                hits = FRENCH_WORDS.findall(body)
                self.assertLessEqual(len(hits), 2, f"{f.relative_to(ROOT)} looks French: {hits[:6]}")

    def test_scripts_have_english_messages(self):
        for f in (ROOT / "skills").rglob("*"):
            if f.suffix in (".py", ".sh"):
                hits = FRENCH_WORDS.findall(f.read_text(encoding="utf-8"))
                self.assertLessEqual(len(hits), 1, f"{f.relative_to(ROOT)}: {hits[:6]}")

    def test_no_public_ip_or_secret_like_values(self):
        for f in (ROOT / "skills").rglob("*"):
            if f.is_file() and f.suffix in (".md", ".py", ".sh"):
                t = f.read_text(encoding="utf-8")
                self.assertIsNone(IPV4.search(t), f"IP address in {f.relative_to(ROOT)}")
                self.assertIsNone(re.search(r"ghp_[A-Za-z0-9]{20}|AKIA[0-9A-Z]{12}|-----BEGIN [A-Z ]*PRIVATE", t), f.name)

    def test_manual_skills_are_the_risky_ones(self):
        for name in ("incident-response", "secrets-hygiene"):
            fm, _ = split((ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8"))
            self.assertIn("disable-model-invocation: true", fm, name)

    def test_gh_skills_use_repo_context(self):
        for name in ("issue-lifecycle", "dev-traceability"):
            self.assertIn("repo-context", (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8"), name)

    def test_every_skill_logs_learning(self):
        for d in SKILLS:
            if d.name in ("skill-learning", "repo-context"):
                continue
            self.assertIn("skill-learning/learn.py log", (d / "SKILL.md").read_text(encoding="utf-8"), d.name)


class Distribution(unittest.TestCase):
    """Skills must work both symlinked into ~/.claude/skills and installed as a plugin."""

    def test_no_hardcoded_install_path_in_skill_files(self):
        for d in SKILLS:
            text = (d / "SKILL.md").read_text(encoding="utf-8")
            self.assertNotIn("~/.claude/skills", text, f"{d.name}: use ${{CLAUDE_SKILL_DIR}} instead")

    def test_script_references_resolve(self):
        for d in SKILLS:
            text = (d / "SKILL.md").read_text(encoding="utf-8")
            for m in re.finditer(r"\$\{CLAUDE_SKILL_DIR\}/((?:\.\./[a-z-]+/)?[\w./-]+)", text):
                target = (d / m.group(1)).resolve()
                self.assertTrue(target.exists(), f"{d.name}: {m.group(0)} does not exist")

    def test_plugin_manifests_are_consistent(self):
        import json
        plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
        market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())
        entry = market["plugins"][0]
        self.assertEqual((entry["name"], entry["version"]), (plugin["name"], plugin["version"]))
        self.assertFalse(plugin["name"].startswith(("claude", "anthropic")), "reserved plugin name prefix")
        latest = re.search(r"^## \[(\d+\.\d+\.\d+)\]", (ROOT / "CHANGELOG.md").read_text(), re.M).group(1)
        self.assertEqual(plugin["version"], latest, "plugin.json version must match the latest CHANGELOG release")
        self.assertEqual(plugin["license"], "Apache-2.0")
        self.assertTrue((ROOT / "NOTICE").exists() and (ROOT / "LICENSE").exists())


if __name__ == "__main__":
    unittest.main()
