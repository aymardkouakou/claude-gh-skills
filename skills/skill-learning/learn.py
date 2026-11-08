#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-claude-gh-skills-1.0
# Copyright 2026 Aymard Kouakou - see NOTICE
"""skill-learning: record how skills are used and turn the history into improvement briefs.

Standard library only. Local file only (~/.claude/skill-state/usage.jsonl). Never records secrets,
personal data or full conversations: short notes, outcome and the user's corrections, redacted.

Usage:
  learn.py log SKILL OUTCOME [--note TEXT] [--correction TEXT]   OUTCOME: ok | partial | failed
  learn.py summary [--skill NAME] [--days N]
  learn.py propose [--skill NAME] [--days N]                      Markdown brief of evidence for improving skills
  learn.py clear --yes
"""
import argparse
import collections
import json
import os
import re
import sys
import time
from pathlib import Path

STATE = Path(os.environ.get("CLAUDE_SKILL_STATE", str(Path.home() / ".claude" / "skill-state")))
USAGE = STATE / "usage.jsonl"
LAST = STATE / "last.json"
MAX_BYTES = 1_000_000
OUTCOMES = ("ok", "partial", "failed")

SECRET_PATTERNS = [
    r"ghp_[A-Za-z0-9]{20}", r"github_pat_", r"gho_[A-Za-z0-9]{20}", r"whsec_[A-Za-z0-9+/=]{10}", r"xox[bap]-",
    r"AKIA[0-9A-Z]{12}", r"-----BEGIN [A-Z ]*PRIVATE", r"Bearer\s+eyJ", r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}",
    r"(?i)(password|passwd|secret|token|api[_-]?key)[\"' ]*[:=][\"' ]*[^\s\"'<*]{8,}",
]
PII_PATTERNS = [r"[\w.+-]+@[\w-]+\.[\w.-]+", r"\+?\d[\d .-]{8,}\d"]


def looks_secret(text):
    return any(re.search(p, text) for p in SECRET_PATTERNS)


def redact(text):
    for p in PII_PATTERNS:
        text = re.sub(p, "[redacted]", text)
    return text.strip()[:300]


def active_repo():
    try:
        return json.loads(LAST.read_text(encoding="utf-8")).get("repo")
    except (OSError, ValueError):
        return None


def rotate():
    if USAGE.exists() and USAGE.stat().st_size > MAX_BYTES:
        lines = USAGE.read_text(encoding="utf-8").splitlines()
        USAGE.write_text("\n".join(lines[len(lines) // 2:]) + "\n", encoding="utf-8")


def log(skill, outcome, note="", correction="", now=None):
    if outcome not in OUTCOMES:
        raise ValueError("outcome must be one of " + ", ".join(OUTCOMES))
    if looks_secret(note) or looks_secret(correction):
        raise PermissionError("REFUSED: the text looks like a secret")
    entry = {"ts": int(now or time.time()), "skill": skill, "outcome": outcome, "repo": active_repo(),
             "note": redact(note), "correction": redact(correction)}
    STATE.mkdir(parents=True, exist_ok=True)
    rotate()
    with USAGE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def read(skill=None, days=None, now=None):
    if not USAGE.exists():
        return []
    cutoff = (now or time.time()) - days * 86400 if days else 0
    out = []
    for line in USAGE.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("ts", 0) >= cutoff and (not skill or e.get("skill") == skill):
            out.append(e)
    return out


def summarize(entries):
    by = collections.defaultdict(lambda: collections.Counter())
    for e in entries:
        by[e["skill"]][e["outcome"]] += 1
    rows = []
    for s, c in sorted(by.items()):
        total = sum(c.values())
        rows.append({"skill": s, "runs": total, "ok": c["ok"], "partial": c["partial"], "failed": c["failed"],
                     "success_rate": round(100 * c["ok"] / total) if total else 0})
    return rows


def brief(entries):
    lines = ["# Skill improvement brief", "", "Evidence from local usage history. Propose changes; never apply without user approval.", ""]
    rows = summarize(entries)
    if not rows:
        return "\n".join(lines + ["No usage recorded yet."])
    lines += ["| Skill | Runs | OK | Partial | Failed | Success |", "|---|---|---|---|---|---|"]
    lines += [f'| {r["skill"]} | {r["runs"]} | {r["ok"]} | {r["partial"]} | {r["failed"]} | {r["success_rate"]}% |' for r in rows]
    for r in rows:
        ev = [e for e in entries if e["skill"] == r["skill"] and (e["outcome"] != "ok" or e["correction"])]
        if not ev:
            continue
        lines += ["", f'## {r["skill"]}']
        corr = collections.Counter(e["correction"] for e in ev if e["correction"])
        notes = collections.Counter(e["note"] for e in ev if e["note"] and e["outcome"] != "ok")
        for text, n in corr.most_common(5):
            lines.append(f"- User correction ({n}x): {text}")
        for text, n in notes.most_common(5):
            lines.append(f"- Friction ({n}x): {text}")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="learn.py", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("log")
    s.add_argument("skill")
    s.add_argument("outcome", choices=OUTCOMES)
    s.add_argument("--note", default="")
    s.add_argument("--correction", default="")
    for name in ("summary", "propose"):
        s = sub.add_parser(name)
        s.add_argument("--skill")
        s.add_argument("--days", type=int)
    s = sub.add_parser("clear")
    s.add_argument("--yes", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "log":
        try:
            print(json.dumps(log(a.skill, a.outcome, a.note, a.correction), ensure_ascii=False))
        except PermissionError as e:
            print(e, file=sys.stderr)
            return 3
        return 0
    if a.cmd == "summary":
        print(json.dumps(summarize(read(a.skill, a.days)), indent=2))
        return 0
    if a.cmd == "propose":
        print(brief(read(a.skill, a.days)))
        return 0
    if a.cmd == "clear":
        if not a.yes:
            print("Refusing without --yes", file=sys.stderr)
            return 2
        USAGE.unlink(missing_ok=True)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
