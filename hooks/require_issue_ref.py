# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Aymard Kouakou - see NOTICE
"""PreToolUse hook: block `git commit -m ...` without an issue reference in repositories that adopted tracking.

A repository adopted tracking when repo-context remembers a Project for it (`project.py use`). Accepted references:
Refs|Fixes|Closes|Resolves [owner/repo]#n, or a documented exception `No-Issue: <reason>`. Fail-open: anything that
cannot be inspected (no -m, unknown repository, unreadable state, any error) lets the commit through.
Exit 2 + stderr = denied (the message goes back to Claude). Standard library only.
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

REF = re.compile(r"(Refs|Fixes|Closes|Resolves)[: ]+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)?#[0-9]+")
EXCEPTION = re.compile(r"^No-Issue:\s*\S+", re.M)
COMMIT = re.compile(r"(?:^|[;&|(]|&&)\s*git\s+(?:-\S+\s+(?:[^-\s]\S*\s+)?)*commit\b")
MESSAGE = re.compile(r"(?:^|\s)(?:-[a-zA-Z]*m|--message)(?:\s|=|['\"])")


def load_ctx():
    path = Path(__file__).resolve().parent.parent / "skills" / "repo-context" / "ctx.py"
    spec = importlib.util.spec_from_file_location("ctx", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def tracked(cwd):
    ctx = load_ctx()
    rc, out, _ = ctx.run(["git", "remote", "get-url", "origin"], cwd)
    if rc != 0:
        return False
    p = ctx.parse_remote(out.strip())
    if not p:
        return False
    rec = ctx.load(ctx.REPOS / (ctx.key_of(p["host"], p["owner"], p["repo"]) + ".json"))
    return bool(rec and rec.get("notes", {}).get("project"))


def check(command, cwd):
    """Return an error message when the commit must be denied, else None."""
    if not COMMIT.search(command) or not MESSAGE.search(command):
        return None
    if REF.search(command) or EXCEPTION.search(command):
        return None
    if not tracked(cwd):
        return None
    return ("Commit blocked: no issue reference. This repository tracks its work in a GitHub Project. Add `Refs #<n>` "
            "(or `Fixes #<n>`) to the commit message; create the issue first with the issue-lifecycle skill and attach it "
            "with project-tracking. For a documented exception add a `No-Issue: <reason>` line.")


def main():
    try:
        data = json.load(sys.stdin)
        msg = check(data.get("tool_input", {}).get("command", ""), data.get("cwd") or ".")
    except Exception:
        return 0
    if msg:
        print(msg, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
