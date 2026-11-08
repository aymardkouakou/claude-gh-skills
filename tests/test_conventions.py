# SPDX-License-Identifier: LicenseRef-claude-gh-skills-1.0
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
        for name in ("incident-response", "secrets-hygiene", "change-management"):
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

    def test_finding_skills_have_a_tracking_section(self):
        for name in ("security-audit", "repo-hardening", "secrets-hygiene", "change-management", "incident-response", "skill-learning"):
            text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            self.assertRegex(text, r"(?m)^## (\d\. )?Tracking$", name)
            self.assertIn("issue-lifecycle", text, name)
            self.assertIn("project-tracking", text, name)


class Granularity(unittest.TestCase):
    """One responsibility per skill: short SKILL.md, long material in references/, triggers in the description."""

    def test_skill_files_stay_short(self):
        for d in SKILLS:
            lines = (d / "SKILL.md").read_text(encoding="utf-8").count("\n")
            self.assertLessEqual(lines, 70, f"{d.name}: {lines} lines, move detail to references/")

    def test_description_says_when_to_use_and_when_not(self):
        for d in SKILLS:
            fm, _ = split((d / "SKILL.md").read_text(encoding="utf-8"))
            desc = re.search(r"(?m)^description: (.+)$", fm).group(1)
            self.assertRegex(desc, r"Use (for|when|before|after)", f"{d.name}: no trigger sentence")
            self.assertRegex(desc, r"(?i)\b(not for|belongs? to|belong to|use [a-z-]+ first|read-only)\b", f"{d.name}: no boundary")
            self.assertLessEqual(len(desc), 900, f"{d.name}: description too long")

    def test_scripts_live_with_their_skill_and_documented_paths_exist(self):
        for rel in ("project-tracking/project.py", "project-board/board.py", "issue-lifecycle/journal.sh",
                    "dev-traceability/check-refs.sh", "repo-context/ctx.py", "skill-learning/learn.py"):
            self.assertTrue((ROOT / "skills" / rel).exists(), rel)
        self.assertFalse((ROOT / "skills" / "issue-lifecycle" / "project.py").exists())


class DocumentationFirst(unittest.TestCase):
    """The README and the process documents stay in step with the skills (owner's rule: docs before commit and release)."""

    def test_readme_lists_every_skill_and_no_removed_one(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for d in SKILLS:
            self.assertIn(f"skills/{d.name}/SKILL.md", readme, f"README does not link {d.name}")
        table = re.findall(r"\]\(skills/([a-z-]+)/SKILL\.md\)", readme)
        self.assertEqual(sorted(set(table)), sorted(d.name for d in SKILLS))
        count = {"Eleven": 11, "Ten": 10, "Twelve": 12, "Nine": 9, "Seven": 7}
        word = re.search(r"^(\w+) \[Agent Skills\]", readme, re.M).group(1)
        self.assertEqual(count.get(word), len(SKILLS), f"README says {word} skills, there are {len(SKILLS)}")
        self.assertIn(f"skills-{len(SKILLS)}-blue", readme)

    def test_documented_script_paths_exist(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for m in re.finditer(r"~/\.claude/skills/([a-z-]+)/([\w.-]+)", readme):
            self.assertTrue((ROOT / "skills" / m.group(1) / m.group(2)).exists(), m.group(0))

    def test_process_documents_state_the_rule(self):
        self.assertIn("Documentation first", (ROOT / "CONVENTIONS.md").read_text(encoding="utf-8"))
        self.assertIn("documentation", (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8").lower())

    def test_changelog_has_a_section_for_every_manifest_version(self):
        import json
        version = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())["version"]
        self.assertIn(f"## [{version}]", (ROOT / "CHANGELOG.md").read_text(encoding="utf-8"))


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
        self.assertEqual(plugin["license"], "SEE LICENSE IN LICENSE")
        self.assertTrue((ROOT / "NOTICE").exists() and (ROOT / "LICENSE").exists())


if __name__ == "__main__":
    unittest.main()
