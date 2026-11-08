#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-claude-gh-skills-1.0
# Copyright 2026 Aymard Kouakou - see NOTICE
"""repo-context: resolve and remember the active GitHub repository (fully gh-compatible).

Standard library only. Never prints or stores tokens, passwords or any secret.

Usage:
  ctx.py resolve [--repo OWNER/REPO] [--no-touch]   JSON about the active repository
  ctx.py repo    [--repo OWNER/REPO]                plain "[HOST/]OWNER/REPO" for `gh --repo`; exit 5 if gh did not confirm it
  ctx.py labels  [--refresh]                        labels of the active repository (cached)
  ctx.py note KEY VALUE                             remember a learned fact about the active repository
  ctx.py lang [--commit]                            language for GitHub output (issues, PRs, comments); exit 3 if unset
  ctx.py lang set CODE [--global] [--commit]        choose it (per repository, or --global); CODE like en, fr, pt-BR
  ctx.py show | list | forget [OWNER/REPO]
State directory: $CLAUDE_SKILL_STATE or ~/.claude/skill-state (local, never versioned).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

STATE = Path(os.environ.get("CLAUDE_SKILL_STATE", str(Path.home() / ".claude" / "skill-state")))
REPOS = STATE / "repos"
LAST = STATE / "last.json"

SECRET_PATTERNS = [
    r"ghp_[A-Za-z0-9]{20}", r"github_pat_", r"gho_[A-Za-z0-9]{20}", r"whsec_[A-Za-z0-9+/=]{10}", r"xox[bap]-",
    r"AKIA[0-9A-Z]{12}", r"-----BEGIN [A-Z ]*PRIVATE", r"Bearer\s+eyJ", r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}",
    r"(?i)(password|passwd|secret|token|api[_-]?key)[\"' ]*[:=][\"' ]*[^\s\"'<*]{8,}",
]
REMOTE_RE = re.compile(
    r"^(?:(?:https?|ssh|git)://)?(?:[^@/\s]+@)?(?P<host>[^/:\s]+)(?::\d+)?[/:](?P<owner>[^/\s]+)/(?P<repo>[^/\s]+?)(?:\.git)?/?$"
)


def looks_secret(text):
    return any(re.search(p, text) for p in SECRET_PATTERNS)


def parse_remote(url):
    """Parse an https/ssh/scp-style git remote into host, owner, repo (or None)."""
    m = REMOTE_RE.match((url or "").strip())
    return m.groupdict() if m else None


def run(args, cwd=None, timeout=20):
    try:
        p = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return 127, "", args[0] + " not found"
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def full_name(host, owner, repo):
    base = f"{owner}/{repo}"
    return base if host in (None, "", "github.com") else f"{host}/{base}"


def key_of(host, owner, repo):
    return re.sub(r"[^A-Za-z0-9_.-]", "_", f"{host}__{owner}__{repo}")


def load(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def save(path, data):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)


def detect(explicit, cwd):
    """Return (info, source). Order: explicit/GH_REPO -> gh in cwd -> git remote -> remembered."""
    explicit = explicit or os.environ.get("GH_REPO")
    fields = "nameWithOwner,url,isPrivate,defaultBranchRef,viewerPermission,hasIssuesEnabled,isFork,visibility,isInOrganization,isArchived,hasProjectsEnabled"
    args = ["gh", "repo", "view"] + ([explicit] if explicit else []) + ["--json", fields]
    rc, out, err = run(args, cwd)
    if rc == 0:
        try:
            d = json.loads(out)
            host = urlparse(d["url"]).hostname or "github.com"
            owner, repo = d["nameWithOwner"].split("/", 1)
            return {
                "host": host, "owner": owner, "repo": repo, "url": d["url"], "private": d.get("isPrivate"),
                "default_branch": (d.get("defaultBranchRef") or {}).get("name"), "permission": d.get("viewerPermission"),
                "issues_enabled": d.get("hasIssuesEnabled"), "fork": d.get("isFork"),
                "visibility": (d.get("visibility") or "").lower() or None, "in_org": d.get("isInOrganization"),
                "archived": d.get("isArchived"), "projects_enabled": d.get("hasProjectsEnabled"),
            }, ("explicit" if explicit else "gh")
        except (ValueError, KeyError):
            pass
    if explicit:
        p = parse_remote(explicit) if "/" in explicit else None
        if p:
            return {"host": p["host"], "owner": p["owner"], "repo": p["repo"]}, "explicit-unverified"
        parts = explicit.split("/")
        if len(parts) == 2:
            return {"host": "github.com", "owner": parts[0], "repo": parts[1]}, "explicit-unverified"
    rc, out, _ = run(["git", "remote", "get-url", "origin"], cwd)
    if rc == 0:
        p = parse_remote(out)
        if p:
            return {"host": p["host"], "owner": p["owner"], "repo": p["repo"]}, "git-remote"
    last = load(LAST)
    if last and load(REPOS / (last.get("key", "") + ".json")):
        rec = load(REPOS / (last["key"] + ".json"))
        return {"host": rec["host"], "owner": rec["owner"], "repo": rec["repo"],
                "default_branch": rec.get("default_branch"), "private": rec.get("private")}, "remembered"
    return None, None


def auth_state(host):
    rc, _, _ = run(["gh", "auth", "status", "--hostname", host])
    return rc == 0


def classify_repo(rec):
    """Repository profile and the rules that follow from it (gh best practices). Unknown facts stay None."""
    vis = rec.get("visibility") or (None if rec.get("private") is None else ("private" if rec["private"] else "public"))
    in_org = rec.get("in_org")
    perm = rec.get("permission")
    rules = []
    if in_org is False:
        rules.append("Personal repository: Projects and sub-issues belong to the user account; issue types and org-level "
                     "Projects do not exist; solo account, so the reviewer-different-from-author control needs a second human or a documented exception.")
    elif in_org:
        rules.append("Organization repository: prefer the organization Project (`gh project --owner ORG`), issue types and rulesets; "
                     "enforce review and CODEOWNERS.")
    if vis == "public":
        rules.append("Public: everything written (issues, comments, logs) is world-readable and indexed; mask more strictly, "
                     "never post vulnerability details (use a private security advisory).")
    elif vis == "internal":
        rules.append("Internal: visible to the whole enterprise; treat as semi-public, no customer data.")
    elif vis == "private":
        rules.append("Private: branch protection and rulesets may need a paid plan; verify with the API before promising enforcement.")
    if rec.get("fork"):
        rules.append("Fork: issues are usually disabled and PRs target upstream; pass --repo explicitly and confirm the target before any write.")
    if rec.get("archived"):
        rules.append("Archived: read-only, do not write anything.")
    if rec.get("issues_enabled") is False:
        rules.append("Issues are disabled on this repository: ask before enabling them or choosing another repository.")
    if rec.get("projects_enabled") is False:
        rules.append("Repository-level Projects are disabled; owner-level Projects v2 still work, verify before attaching.")
    if perm in ("READ", "TRIAGE"):
        rules.append(f"Permission {perm}: cannot push or merge" + ("; can label and triage issues." if perm == "TRIAGE" else "; comment only."))
    owner_type = None if in_org is None else ("organization" if in_org else "personal")
    return {"owner_type": owner_type, "visibility": vis, "fork": bool(rec.get("fork")), "archived": bool(rec.get("archived")),
            "writable": not rec.get("archived") and perm not in ("READ", None) and rec.get("issues_enabled") is not False,
            "rules": rules}


def resolve(explicit=None, cwd=None, touch=True):
    cwd = cwd or os.getcwd()
    info, source = detect(explicit, cwd)
    if not info:
        return None
    key = key_of(info["host"], info["owner"], info["repo"])
    rec = load(REPOS / (key + ".json")) or {"first_seen": int(time.time()), "uses": 0, "notes": {}, "labels": [], "paths": []}
    for k in ("host", "owner", "repo", "url", "private", "default_branch", "permission", "issues_enabled", "fork",
              "visibility", "in_org", "archived", "projects_enabled"):
        if info.get(k) is not None:
            rec[k] = info[k]
    if touch:
        rec["last_seen"] = int(time.time())
        rec["uses"] = rec.get("uses", 0) + 1
        paths = [p for p in rec.get("paths", []) if p != cwd]
        rec["paths"] = ([cwd] + paths)[:5]
        save(REPOS / (key + ".json"), rec)
        save(LAST, {"key": key, "repo": full_name(info["host"], info["owner"], info["repo"]), "path": cwd, "ts": int(time.time())})
    out = {
        "repo": f'{info["owner"]}/{info["repo"]}', "host": info["host"], "full": full_name(info["host"], info["owner"], info["repo"]),
        "url": rec.get("url"), "private": rec.get("private"), "default_branch": rec.get("default_branch"),
        "permission": rec.get("permission"), "authenticated": auth_state(info["host"]), "source": source,
        "uses": rec.get("uses"), "notes": rec.get("notes", {}), "cached_labels": len(rec.get("labels", [])),
        "kind": classify_repo(rec),
        "language": get_language(rec), "commit_language": get_language(rec, commit=True),
    }
    if out["language"] is None:
        out["language_hint"] = "Not set: ask the user once which language to use on GitHub, then run `ctx.py lang set CODE`."
    if out["kind"]["owner_type"] is None:
        out["kind_hint"] = "Repository type unknown (gh did not confirm it): do not assume personal or organization."
    if source in ("remembered", "explicit-unverified"):
        out["warning"] = "Repository not confirmed by gh in this directory: ask the user to confirm before any write."
    return out


UNVERIFIED = ("remembered", "explicit-unverified")
LANG_RE = re.compile(r"^[a-z]{2,3}(-[A-Z]{2})?$")
CONFIG = STATE / "config.json"


def get_language(rec, commit=False):
    """Resolve the GitHub output language: env > repository setting > global config > (commit only) 'en' > None."""
    key = "commit_language" if commit else "language"
    env = os.environ.get("CLAUDE_SKILL_COMMIT_LANG" if commit else "CLAUDE_SKILL_LANG")
    for candidate in (env, ((rec or {}).get("settings") or {}).get(key), (load(CONFIG) or {}).get(key)):
        if candidate and LANG_RE.match(candidate):
            return candidate
    return "en" if commit else None


def active_record():
    last = load(LAST)
    if not last:
        return None, None
    return last["key"], load(REPOS / (last["key"] + ".json"))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ctx.py", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("resolve", "repo"):
        s = sub.add_parser(name)
        s.add_argument("--repo")
        s.add_argument("--no-touch", action="store_true")
        if name == "repo":
            s.add_argument("--allow-unverified", action="store_true",
                           help="print the repository even if gh did not confirm it (never use before a write)")
    s = sub.add_parser("labels")
    s.add_argument("--refresh", action="store_true")
    s = sub.add_parser("note")
    s.add_argument("key")
    s.add_argument("value")
    s = sub.add_parser("lang")
    s.add_argument("action", nargs="?", choices=["set"])
    s.add_argument("code", nargs="?")
    s.add_argument("--global", dest="glob", action="store_true")
    s.add_argument("--commit", action="store_true")
    sub.add_parser("show")
    sub.add_parser("list")
    s = sub.add_parser("forget")
    s.add_argument("repo", nargs="?")
    a = ap.parse_args(argv)

    if a.cmd in ("resolve", "repo"):
        r = resolve(a.repo, touch=not a.no_touch)
        if not r:
            print(json.dumps({"error": "No repository found: not in a git repo with a GitHub remote and nothing remembered. "
                                       "Run inside the project or pass --repo OWNER/REPO."}), file=sys.stderr)
            return 2
        if a.cmd == "repo" and r["source"] in UNVERIFIED and not a.allow_unverified:
            print(f'REFUSED: repository "{r["full"]}" is only {r["source"]} (not confirmed by gh in this directory). '
                  "Confirm with the user and pass --repo OWNER/REPO, or use --allow-unverified for read-only use.", file=sys.stderr)
            return 5
        print(r["full"] if a.cmd == "repo" else json.dumps(r, indent=2, ensure_ascii=False))
        return 0
    key, rec = active_record()
    if a.cmd == "list":
        for p in sorted(REPOS.glob("*.json")):
            d = load(p) or {}
            print(f'{full_name(d.get("host"), d.get("owner"), d.get("repo"))}\tuses={d.get("uses", 0)}\tlast_seen={d.get("last_seen")}')
        return 0
    if a.cmd == "forget":
        if a.repo:
            owner, repo = a.repo.split("/")[-2:]
            host = a.repo.split("/")[0] if a.repo.count("/") == 2 else "github.com"
            target = REPOS / (key_of(host, owner, repo) + ".json")
        else:
            target = REPOS / ((key or "") + ".json")
        if target.exists():
            target.unlink()
            print("forgotten:", target.stem)
        if LAST.exists() and (load(LAST) or {}).get("key") == target.stem:
            LAST.unlink()
        return 0
    if a.cmd == "lang":
        setting = "commit_language" if a.commit else "language"
        if a.action == "set":
            if not a.code or not LANG_RE.match(a.code):
                print("Invalid language code (examples: en, fr, pt-BR).", file=sys.stderr)
                return 2
            if a.glob:
                cfg = load(CONFIG) or {}
                cfg[setting] = a.code
                save(CONFIG, cfg)
            else:
                if not rec:
                    print("No active repository yet: run `ctx.py resolve` first, or use --global.", file=sys.stderr)
                    return 2
                rec.setdefault("settings", {})[setting] = a.code
                save(REPOS / (key + ".json"), rec)
            print(f"{setting} = {a.code} ({'global' if a.glob else 'repository'})")
            return 0
        code = get_language(rec, commit=a.commit)
        if code is None:
            print("unset", file=sys.stderr)
            return 3
        print(code)
        return 0
    if not rec:
        print("No active repository yet: run `ctx.py resolve` first.", file=sys.stderr)
        return 2
    if a.cmd == "show":
        print(json.dumps(rec, indent=2, ensure_ascii=False))
        return 0
    if a.cmd == "note":
        if looks_secret(a.value) or looks_secret(a.key):
            print("REFUSED: the text looks like a secret.", file=sys.stderr)
            return 3
        rec.setdefault("notes", {})[a.key[:60]] = a.value[:300]
        save(REPOS / (key + ".json"), rec)
        print("noted:", a.key)
        return 0
    if a.cmd == "labels":
        if a.refresh or not rec.get("labels"):
            rc, out, err = run(["gh", "label", "list", "--repo", full_name(rec["host"], rec["owner"], rec["repo"]),
                                "--json", "name", "--limit", "200"], timeout=30)
            if rc != 0:
                print("gh label list failed: " + err[:200], file=sys.stderr)
                return rc
            rec["labels"] = sorted(x["name"] for x in json.loads(out))
            save(REPOS / (key + ".json"), rec)
        print("\n".join(rec.get("labels", [])))
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
