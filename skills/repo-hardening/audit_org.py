#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-claude-gh-skills-1.1
# Copyright 2026 Aymard Kouakou - see NOTICE
"""audit_org.py: compare the default-branch rules and secret scanning of every repository of an owner. Read-only.

Usage: audit_org.py OWNER [--repos a,b] [--include-archived] [--strict] [--format md|csv]
Per repository: whether the default branch requires a pull request, blocks force-push and deletion (effective rules,
which include organization rulesets), and whether secret scanning and push protection are on. Results are
`ok`, `gap` or `n/a` (not verifiable: missing admin permission or plan limit, never counted as a gap). Organization
rulesets are listed when the owner is an organization. Nothing is changed; a ruleset template to review and apply
yourself is in references/org-ruleset.json. --strict exits 1 when a gap exists. Needs `gh`. Standard library only.
"""
import argparse
import csv
import io
import json
import subprocess
import sys

COLUMNS = ["Repository", "Default branch", "Pull request required", "No force-push", "No deletion", "Secret scanning", "Push protection"]


def gh_api(path):
    """(status, parsed JSON) - status is 'ok', 'missing' (GitHub says the branch is not protected) or 'na'
    (403/404/other failure: not verifiable); never raises."""
    done = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if done.returncode != 0:
        return ("missing" if "branch not protected" in done.stderr.lower() else "na"), None
    try:
        return "ok", json.loads(done.stdout or "null")
    except ValueError:
        return "na", None


def verdict(flag):
    return {True: "ok", False: "gap", None: "n/a"}[flag]


def branch_controls(rule_types):
    """From the effective rule types of a branch (None = unreadable) to the three branch controls."""
    if rule_types is None:
        return None, None, None
    return "pull_request" in rule_types, "non_fast_forward" in rule_types, "deletion" in rule_types


def audit_repo(owner, name, api=gh_api):
    st, repo = api(f"repos/{owner}/{name}")
    row = {"Repository": f"{owner}/{name}", "Default branch": "-"}
    if st != "ok" or not repo:
        return {**row, **{c: "n/a" for c in COLUMNS[2:]}}
    branch = repo.get("default_branch") or "main"
    row["Default branch"] = branch
    st, rules = api(f"repos/{owner}/{name}/rules/branches/{branch}")
    types = {r.get("type") for r in rules} if st == "ok" and isinstance(rules, list) else None
    pr, force, delete = branch_controls(types)
    if types is not None and not types:  # no ruleset: classic protection may still apply
        st, prot = api(f"repos/{owner}/{name}/branches/{branch}/protection")
        if st == "na":  # cannot tell (classic protection needs admin access): not a gap
            pr = force = delete = None
        elif st == "ok" and isinstance(prot, dict):
            pr = bool(prot.get("required_pull_request_reviews"))
            force = not (prot.get("allow_force_pushes") or {}).get("enabled", False)
            delete = not (prot.get("allow_deletions") or {}).get("enabled", False)
    sa = repo.get("security_and_analysis") or {}
    scan = (sa.get("secret_scanning") or {}).get("status")
    push = (sa.get("secret_scanning_push_protection") or {}).get("status")
    return {**row, "Pull request required": verdict(pr), "No force-push": verdict(force), "No deletion": verdict(delete),
            "Secret scanning": verdict(None if scan is None else scan == "enabled"),
            "Push protection": verdict(None if push is None else push == "enabled")}


def list_repos(owner, only=None, archived=False, api=gh_api):
    done = subprocess.run(["gh", "repo", "list", owner, "--limit", "200", "--json", "name,isArchived,isFork"],
                          capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError("gh repo list failed: " + done.stderr.strip()[:200])
    repos = [r["name"] for r in json.loads(done.stdout or "[]") if (archived or not r["isArchived"]) and not r["isFork"]]
    return sorted(n for n in repos if not only or n in only)


def org_rulesets(owner, api=gh_api):
    st, data = api(f"orgs/{owner}/rulesets")
    return [f"{r.get('name', '?')} ({r.get('enforcement', '?')})" for r in data] if st == "ok" and isinstance(data, list) else None


def render(rows, fmt):
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(COLUMNS)
        w.writerows([[r[c] for c in COLUMNS] for r in rows])
        return buf.getvalue()
    lines = ["| " + " | ".join(COLUMNS) + " |", "|" + "---|" * len(COLUMNS)]
    return "\n".join(lines + ["| " + " | ".join(r[c] for c in COLUMNS) + " |" for r in rows]) + "\n"


def main(argv=None, lister=list_repos, auditor=audit_repo, rulesets=org_rulesets):
    ap = argparse.ArgumentParser(description="Compare repository protections across an owner (read-only).")
    ap.add_argument("owner")
    ap.add_argument("--repos")
    ap.add_argument("--include-archived", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--format", choices=("md", "csv"), default="md")
    a = ap.parse_args(argv)
    try:
        names = lister(a.owner, set(a.repos.split(",")) if a.repos else None, a.include_archived)
    except (RuntimeError, ValueError) as exc:
        print(f"audit_org: {exc}", file=sys.stderr)
        return 2
    if not names:
        print(f"audit_org: no repository to audit for {a.owner}", file=sys.stderr)
        return 2
    rows = [auditor(a.owner, n) for n in names]
    sys.stdout.write(render(rows, a.format))
    listed = rulesets(a.owner)
    print("Organization rulesets: " + ("; ".join(listed) if listed else "none listed" if listed == [] else "not available (not an organization, or no permission)"), file=sys.stderr)
    gaps = sum(1 for r in rows for c in COLUMNS[2:] if r[c] == "gap")
    print(f"{len(rows)} repositories, {gaps} gap(s); n/a means not verifiable, not a gap", file=sys.stderr)
    return 1 if a.strict and gaps else 0


if __name__ == "__main__":
    sys.exit(main())
