#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-claude-gh-skills-1.1
# Copyright 2026 Aymard Kouakou - see NOTICE
"""portfolio.py: multi-repository progress report for an owner (organization or user). Read-only, counts only.

Usage: portfolio.py OWNER [--repos a,b,c] [--include-archived] [--include-forks] [--public-only] [--format md|csv]
One row per repository: open issues, open pull requests, open epics, epic progress (done/total sub-issues) and issues
without an epic; then a total. Issue and repository names are never printed beyond the repository name itself.
Repository names are printed: use --public-only before sharing the report outside the audience of private repositories.
A repository that cannot be read yields an `unavailable` row instead of stopping the report.
Needs `gh` (no `project` scope). Standard library only.
"""
import argparse
import csv
import importlib.util
import io
import json
import sys
from pathlib import Path

_PATH = Path(__file__).resolve().parent.parent / "project-tracking" / "project.py"
if not _PATH.is_file():
    sys.exit(f"portfolio.py needs the project-tracking skill (expected {_PATH}): install the whole plugin or run ./install.sh")
_spec = importlib.util.spec_from_file_location("project", _PATH)
project = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(project)

COLUMNS = ["Repository", "Visibility", "Open issues", "Open PRs", "Open epics", "Epic progress", "Without epic"]


def list_repos(owner, only=None, archived=False, forks=False, public_only=False):
    rc, out, err = project.run(["gh", "repo", "list", owner, "--limit", "200", "--json", "name,isArchived,isFork,visibility"])
    if rc != 0:
        raise RuntimeError("gh repo list failed: " + err[:200])
    repos = [r for r in json.loads(out or "[]") if (archived or not r["isArchived"]) and (forks or not r["isFork"])]
    if public_only:
        repos = [r for r in repos if str(r.get("visibility", "")).lower() == "public"]
    if only:
        repos = [r for r in repos if r["name"] in only]
    return sorted(repos, key=lambda r: r["name"])


def summarize(owner, repo, issues, prs, summaries):
    """One row from the open issues, open PRs and {epic number: (done, total)} of a repository."""
    epics = [i for i in issues if project.is_epic(i)]
    done = sum(summaries.get(e["number"], (0, 0))[0] for e in epics)
    total = sum(summaries.get(e["number"], (0, 0))[1] for e in epics)
    return {"Repository": f"{owner}/{repo['name']}", "Visibility": str(repo.get("visibility", "")).lower(),
            "Open issues": len(issues), "Open PRs": len(prs), "Open epics": len(epics),
            "Epic progress": f"{done}/{total}" if total else "-",
            "Without epic": sum(1 for i in issues if not project.is_epic(i) and not i["parent"]), "_done": done, "_total": total}


def gather(owner, repo, fetch_issues=None, fetch_prs=None, fetch_summary=None):
    fetch_issues = fetch_issues or project.fetch_open_issues
    fetch_prs = fetch_prs or project.fetch_open_prs
    fetch_summary = fetch_summary or (lambda o, n, num: project.fetch_tree(o, n, num)["summary"])
    try:
        issues, prs = fetch_issues(owner, repo["name"]), fetch_prs(owner, repo["name"])
        summaries = {}
        for e in (i for i in issues if project.is_epic(i)):
            s = fetch_summary(owner, repo["name"], e["number"])
            summaries[e["number"]] = (s.get("completed", 0), s.get("total", 0))
        return summarize(owner, repo, issues, prs, summaries)
    except (RuntimeError, KeyError, ValueError):
        return {"Repository": f"{owner}/{repo['name']}", "Visibility": str(repo.get("visibility", "")).lower(),
                "Open issues": "unavailable", "Open PRs": "-", "Open epics": "-", "Epic progress": "-", "Without epic": "-"}


def totals(rows):
    ok = [r for r in rows if isinstance(r["Open issues"], int)]
    done, total = sum(r["_done"] for r in ok), sum(r["_total"] for r in ok)
    return {"Repository": f"Total ({len(ok)} repositories)", "Visibility": "", "Open issues": sum(r["Open issues"] for r in ok),
            "Open PRs": sum(r["Open PRs"] for r in ok), "Open epics": sum(r["Open epics"] for r in ok),
            "Epic progress": f"{done}/{total}" if total else "-", "Without epic": sum(r["Without epic"] for r in ok)}


def render(rows, fmt):
    rows = rows + [totals(rows)]
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(COLUMNS)
        w.writerows([[r[c] for c in COLUMNS] for r in rows])
        return buf.getvalue()
    lines = ["| " + " | ".join(COLUMNS) + " |", "|" + "---|" * len(COLUMNS)]
    lines += ["| " + " | ".join(str(r[c]) for c in COLUMNS) + " |" for r in rows]
    return "\n".join(lines) + "\n"


def main(argv=None, repo_lister=list_repos, gatherer=gather):
    ap = argparse.ArgumentParser(description="Multi-repository progress report (read-only).")
    ap.add_argument("owner")
    ap.add_argument("--repos", help="comma-separated repository names")
    ap.add_argument("--include-archived", action="store_true")
    ap.add_argument("--include-forks", action="store_true")
    ap.add_argument("--public-only", action="store_true", help="leave private and internal repositories out")
    ap.add_argument("--format", choices=("md", "csv"), default="md")
    a = ap.parse_args(argv)
    try:
        repos = repo_lister(a.owner, set(a.repos.split(",")) if a.repos else None, a.include_archived, a.include_forks, a.public_only)
    except (RuntimeError, ValueError) as exc:
        print(f"portfolio: {exc}", file=sys.stderr)
        return 2
    if not repos:
        print(f"portfolio: no repository to report for {a.owner}", file=sys.stderr)
        return 2
    sys.stdout.write(render([gatherer(a.owner, r) for r in repos], a.format))
    return 0


if __name__ == "__main__":
    sys.exit(main())
