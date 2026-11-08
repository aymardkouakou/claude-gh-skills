#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-claude-gh-skills-1.0
# Copyright 2026 Aymard Kouakou - see NOTICE
"""Check that every installed skill finds the sibling skills it requires (see dependencies.json).

Usage: check_deps.py [--dir SKILLS_DIR]   (default: ~/.claude/skills when it exists, else this repository's skills/)
Exit 1 when a required sibling is missing; optional ones are only reported. Read-only, standard library only.
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def check(skills_dir, deps):
    """Return (missing required, missing optional) as lists of 'skill needs sibling' strings."""
    present = {p.name for p in skills_dir.iterdir() if (p / "SKILL.md").exists()} if skills_dir.is_dir() else set()
    required, optional = [], []
    for skill in sorted(present & set(deps)):
        required += [f"{skill} needs {d}" for d in deps[skill]["requires"] if d not in present]
        optional += [f"{skill} can use {d}" for d in deps[skill]["optional"] if d not in present]
    return required, optional


def main(argv=None, home=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir")
    args = ap.parse_args(argv)
    default = (home or Path.home()) / ".claude" / "skills"
    skills_dir = Path(args.dir) if args.dir else (default if default.is_dir() else ROOT / "skills")
    deps = json.loads((ROOT / "dependencies.json").read_text(encoding="utf-8"))
    deps.pop("_comment", None)
    required, optional = check(skills_dir, deps)
    for line in required:
        print(f"MISSING  {line}: install the whole plugin or run ./install.sh (skills call each other)")
    for line in optional:
        print(f"optional {line} (not installed; the step is skipped)")
    if not required:
        print(f"Required dependencies satisfied in {skills_dir}")
    return 1 if required else 0


if __name__ == "__main__":
    sys.exit(main())
