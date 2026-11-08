# SPDX-License-Identifier: LicenseRef-claude-gh-skills-1.1
# Copyright 2026 Aymard Kouakou - see NOTICE
"""Structure of the behaviour evaluations: one file per skill, trigger and procedure cases."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = sorted(p.name for p in (ROOT / "skills").iterdir() if p.is_dir())


class Evals(unittest.TestCase):
    def load(self, name):
        return json.loads((ROOT / "evals" / f"{name}.json").read_text(encoding="utf-8"))

    def test_every_skill_has_an_eval_file_and_no_orphan_file(self):
        files = sorted(p.stem for p in (ROOT / "evals").glob("*.json"))
        self.assertEqual(files, SKILLS)

    def test_trigger_cases(self):
        for name in SKILLS:
            data = self.load(name)
            self.assertEqual(data["skill"], name)
            cases = data["triggers"]
            positives = [c for c in cases if c["expect"] in ("trigger", "manual")]
            negatives = [c for c in cases if c["expect"] == "no-trigger"]
            self.assertGreaterEqual(len(positives), 3, name)
            self.assertGreaterEqual(len(negatives), 2, name)
            for c in negatives:
                self.assertTrue(c["use_instead"] == "none" or c["use_instead"] in SKILLS, f"{name}: {c}")
                self.assertNotEqual(c["use_instead"], name)
            prompts = [c["prompt"] for c in cases]
            self.assertEqual(len(prompts), len(set(prompts)), f"{name}: duplicate prompt")

    def test_procedure_cases(self):
        for name in SKILLS:
            procedure = self.load(name)["procedure"]
            self.assertTrue(procedure, f"{name}: no procedure case")
            for c in procedure:
                self.assertTrue(c["prompt"] and c["must"] and c["must_not"], f"{name}: incomplete case")

    def test_manual_only_skills_are_marked(self):
        manual = {"change-management", "incident-response", "secrets-hygiene"}
        for name in SKILLS:
            text = (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            self.assertEqual("disable-model-invocation" in text, name in manual, name)
            kinds = {c["expect"] for c in self.load(name)["triggers"] if c["expect"] != "no-trigger"}
            self.assertEqual(kinds, {"manual"} if name in manual else {"trigger"}, name)
            if name in manual:
                self.assertTrue(any(c["prompt"].startswith("/") for c in self.load(name)["triggers"]), name)


if __name__ == "__main__":
    unittest.main()
