# SPDX-License-Identifier: LicenseRef-claude-gh-skills-1.1
# Copyright 2026 Aymard Kouakou - see NOTICE
"""PreToolUse hook for repositories that adopted tracking (repo-context remembers a Project for them).

Denied (exit 2 + stderr, the message goes back to Claude):
- `git commit -m ...` and `gh pr create|edit --body ...` without an issue reference
  (Refs|Fixes|Closes|Resolves [owner/repo]#n, or a documented exception `No-Issue: <reason>`);
- `git push` that forces (`--force`, `-f`, `--force-with-lease`, `+refspec`, `--mirror`) to main or master.
Asked (the user confirms): `gh issue close N` when no local commit mentions #N and the command cites no commit or PR.
Fail-open: anything that cannot be inspected (no -m or --body, unknown repository, unreadable state, any error)
lets the command through. Standard library only.
"""
import importlib.util
import json
import re
import shlex
import sys
from pathlib import Path

REF = re.compile(r"(Refs|Fixes|Closes|Resolves)[: ]+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)?#[0-9]+")
EXCEPTION = re.compile(r"^No-Issue:\s*\S+", re.M)
COMMIT = re.compile(r"(?:^|[;&|(]|&&)\s*git\s+(?:-\S+\s+(?:[^-\s]\S*\s+)?)*commit\b")
PR = re.compile(r"(?:^|[;&|(]|&&)\s*gh\s+pr\s+(?:create|edit)\b")
BODY = re.compile(r"(?:^|\s)(?:-b|--body)(?:\s|=|['\"])")
PUSH = re.compile(r"(?:^|[;&|(]|&&)\s*git\s+(?:-\S+\s+(?:[^-\s]\S*\s+)?)*push\b")
CLOSE = re.compile(r"(?:^|[;&|(]|&&)\s*gh\s+issue\s+close\b")
PROTECTED = {"main", "master"}
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


def words(command, pattern):
    """Tokens that follow the first `pattern` match, cut at the next shell operator; None when absent or unparsable."""
    m = pattern.search(command)
    if not m:
        return None
    try:
        lex = shlex.shlex(command[m.end():], posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        lex.commenters = ""
        out = []
        for tok in lex:
            if tok in ("&&", "||", ";", "|", "&", "(", ")"):
                break
            out.append(tok)
        return out
    except ValueError:
        return None


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


def check_pr(command, cwd):
    if not PR.search(command) or not BODY.search(command):
        return None
    if REF.search(command) or EXCEPTION.search(command) or not tracked(cwd):
        return None
    return ("Pull request blocked: the body has no issue reference. Add `Refs #<n>` or `Fixes #<n>` to --body "
            "(or a `No-Issue: <reason>` line).")


def current_branch(cwd):
    rc, out, _ = load_ctx().run(["git", "symbolic-ref", "--short", "-q", "HEAD"], cwd)
    return out.strip() if rc == 0 else ""


def check_push(command, cwd):
    args = words(command, PUSH)
    if args is None:
        return None
    flags = [a for a in args if a.startswith("-")]
    positional = [a for a in args if not a.startswith("-")]
    refspecs = positional[1:]
    forced = any(f in ("--force", "-f", "--force-with-lease", "--mirror") or f.startswith("--force-with-lease=")
                 or (f.startswith("-") and not f.startswith("--") and "f" in f[1:]) for f in flags)
    forced = forced or any(r.startswith("+") for r in refspecs)
    if not forced or not tracked(cwd):
        return None
    targets = [r.lstrip("+").split(":")[-1].replace("refs/heads/", "") for r in refspecs] or [current_branch(cwd)]
    if "--mirror" in flags or any(t in PROTECTED for t in targets):
        return ("Force-push blocked: it would rewrite main or master. Push a branch and open a pull request instead; "
                "if history really must be rewritten, ask the owner to run the command.")
    return None


def check_close(command, cwd):
    args = words(command, CLOSE)
    if not args or not tracked(cwd):
        return None
    numbers = [a.lstrip("#") for a in args if re.fullmatch(r"#?[0-9]+", a)]
    if not numbers:
        return None
    if re.search(r"\b[0-9a-f]{7,40}\b|#[0-9]+|/pull/[0-9]+", " ".join(a for a in args if not re.fullmatch(r"#?[0-9]+", a))):
        return None
    n = numbers[0]
    rc, out, _ = load_ctx().run(["git", "log", "--all", "-1", "--format=%h", "-E", f"--grep=#{n}([^0-9]|$)"], cwd)
    if rc == 0 and out.strip():
        return None
    return (f"Closing #{n}: no commit mentions it. Link the change first (commit with `Fixes #{n}` or a comment citing the "
            "commit or pull request), or confirm that closing without one is intended.")


def evaluate(command, cwd):
    """Return ('deny'|'ask', message) or None."""
    for fn in (check, check_pr, check_push):
        msg = fn(command, cwd)
        if msg:
            return "deny", msg
    msg = check_close(command, cwd)
    return ("ask", msg) if msg else None


def main():
    try:
        data = json.load(sys.stdin)
        verdict = evaluate(data.get("tool_input", {}).get("command", ""), data.get("cwd") or ".")
    except Exception:
        return 0
    if not verdict:
        return 0
    kind, msg = verdict
    if kind == "ask":
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                                 "permissionDecisionReason": msg}}))
        return 0
    print(msg, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
