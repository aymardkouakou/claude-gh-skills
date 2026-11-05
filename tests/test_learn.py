import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("learn", ROOT / "skills" / "skill-learning" / "learn.py")
learn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(learn)


class Learn(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        learn.STATE, learn.USAGE, learn.LAST = base, base / "usage.jsonl", base / "last.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_log_and_summary(self):
        learn.log("issue-lifecycle", "ok", now=1000)
        learn.log("issue-lifecycle", "partial", note="label missing", now=1001)
        learn.log("security-audit", "failed", correction="always list routes first", now=1002)
        rows = {r["skill"]: r for r in learn.summarize(learn.read())}
        self.assertEqual(rows["issue-lifecycle"]["runs"], 2)
        self.assertEqual(rows["issue-lifecycle"]["success_rate"], 50)
        self.assertEqual(rows["security-audit"]["failed"], 1)

    def test_refuses_secret_and_redacts_pii(self):
        with self.assertRaises(PermissionError):
            learn.log("x", "ok", note="token=abcdefgh12345678")
        e = learn.log("x", "partial", note="mail me at a.b@corp.com or +225 07 00 00 00 00")
        self.assertNotIn("a.b@corp.com", e["note"])
        self.assertNotIn("07 00 00 00", e["note"])

    def test_invalid_outcome(self):
        with self.assertRaises(ValueError):
            learn.log("x", "great")

    def test_days_filter_and_brief(self):
        learn.log("a", "failed", note="slow", now=1)
        learn.log("a", "failed", note="slow", now=learn.time.time())
        recent = learn.read(days=1)
        self.assertEqual(len(recent), 1)
        self.assertIn("Friction (1x): slow", learn.brief(recent))
        self.assertIn("No usage recorded", learn.brief([]))

    def test_rotation_caps_size(self):
        learn.MAX_BYTES = 2000
        for i in range(60):
            learn.log("a", "ok", note="n" * 60, now=i)
        self.assertLess(learn.USAGE.stat().st_size, 6000)


if __name__ == "__main__":
    unittest.main()
