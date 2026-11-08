#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-claude-gh-skills-1.0
# Copyright 2026 Aymard Kouakou - see NOTICE
"""Cut a release: bump the manifests, date the changelog, commit, tag, and optionally push and publish.

Usage: release.py VERSION [--refs N [N ...]] [--apply] [--push]
Dry run by default: prints what would change. --apply edits files, commits and tags (nothing leaves the machine).
--push (needs --apply) then pushes the branch and tag and creates the GitHub release from the changelog section.
Refuses: a dirty tree, a branch other than main, a version that is not newer, an empty Unreleased section,
failing tests, an invalid plugin. Standard library only.
"""
import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFESTS = (".claude-plugin/plugin.json", ".claude-plugin/marketplace.json")
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def sh(args, cwd=None, runner=subprocess.run):
    done = runner(args, cwd=cwd or ROOT, capture_output=True, text=True)
    return done.returncode, (done.stdout or "").strip(), (done.stderr or "").strip()


def current_version(root=ROOT):
    return json.loads((root / MANIFESTS[0]).read_text(encoding="utf-8"))["version"]


def newer(new, old):
    a, b = SEMVER.match(new), SEMVER.match(old)
    return bool(a and b) and tuple(map(int, a.groups())) > tuple(map(int, b.groups()))


def unreleased_body(changelog):
    m = re.search(r"^## \[Unreleased\]\n(.*?)(?=^## \[)", changelog, re.M | re.S)
    return m.group(1).strip() if m else ""


def release_changelog(changelog, version, today):
    return changelog.replace("## [Unreleased]\n", f"## [Unreleased]\n\n## [{version}] - {today}\n", 1)


def section(changelog, version):
    m = re.search(rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|\Z)", changelog, re.M | re.S)
    return m.group(1).strip() if m else ""


def bump_manifests(root, version):
    for rel in MANIFESTS:
        p = root / rel
        p.write_text(re.sub(r'("version":\s*")[^"]+(")', rf"\g<1>{version}\g<2>", p.read_text(encoding="utf-8")),
                     encoding="utf-8")


def preflight(version, root=ROOT, run=sh):
    """Return a list of reasons to refuse."""
    problems = []
    if not SEMVER.match(version):
        return [f"{version!r} is not MAJOR.MINOR.PATCH"]
    old = current_version(root)
    if not newer(version, old):
        problems.append(f"{version} is not newer than {old}")
    if run(["git", "status", "--porcelain"], root)[1]:
        problems.append("working tree is not clean")
    if run(["git", "rev-parse", "--abbrev-ref", "HEAD"], root)[1] != "main":
        problems.append("not on main")
    if run(["git", "rev-parse", "-q", "--verify", f"refs/tags/v{version}"], root)[0] == 0:
        problems.append(f"tag v{version} already exists")
    if not unreleased_body((root / "CHANGELOG.md").read_text(encoding="utf-8")):
        problems.append("CHANGELOG [Unreleased] is empty")
    return problems


def checks(root=ROOT, run=sh):
    problems = []
    if run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], root)[0] != 0:
        problems.append("tests fail")
    if run(["claude", "plugin", "validate", "."], root)[0] != 0:
        problems.append("claude plugin validate fails")
    return problems


def main(argv=None, root=ROOT, run=sh, today=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("version")
    ap.add_argument("--refs", nargs="*", default=[], help="issue numbers for the commit (Refs #n)")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--push", action="store_true")
    args = ap.parse_args(argv)
    version = args.version.lstrip("v")
    if args.push and not args.apply:
        print("--push needs --apply", file=sys.stderr)
        return 2
    problems = preflight(version, root, run)
    if problems:
        print("refused: " + "; ".join(problems), file=sys.stderr)
        return 1
    today = today or datetime.date.today().isoformat()
    print(f"release {current_version(root)} -> {version} ({today})")
    if not args.apply:
        print("dry run: would bump the manifests, date the changelog, commit and tag; use --apply")
        return 0
    problems = checks(root, run)
    if problems:
        print("refused: " + "; ".join(problems), file=sys.stderr)
        return 1
    bump_manifests(root, version)
    log = root / "CHANGELOG.md"
    log.write_text(release_changelog(log.read_text(encoding="utf-8"), version, today), encoding="utf-8")
    body = f"chore(release): v{version}\n\n" + "".join(f"Refs #{n.lstrip('#')}\n" for n in args.refs)
    if not args.refs:
        body += "No-Issue: release bump\n"
    steps = [["git", "add", "-A"], ["git", "commit", "-q", "-m", body], ["git", "tag", "-a", f"v{version}", "-m", f"v{version}"]]
    for step in steps:
        rc, _, err = run(step, root)
        if rc != 0:
            print(f"failed: {' '.join(step[:2])}: {err}", file=sys.stderr)
            return 1
    print(f"committed and tagged v{version}")
    if args.push:
        notes = section(log.read_text(encoding="utf-8"), version) or f"Release v{version}"
        for step in (["git", "push", "origin", "main", "--follow-tags"],
                     ["gh", "release", "create", f"v{version}", "--title", f"v{version}", "--notes", notes]):
            rc, _, err = run(step, root)
            if rc != 0:
                print(f"failed: {' '.join(step[:2])}: {err}", file=sys.stderr)
                return 1
        print(f"pushed and published v{version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
