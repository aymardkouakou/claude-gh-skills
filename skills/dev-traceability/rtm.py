#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-claude-gh-skills-1.1
# Copyright 2026 Aymard Kouakou - see NOTICE
"""Requirements traceability matrix from GitHub and git history. Read-only.

Usage: rtm.py [--repo OWNER/REPO] [--format md|csv] [--solo] [--strict] [--range BASE..HEAD]
Columns: requirement (REQ-/SEC- ids found in the issue), issue, state, commits (`Refs/Fixes #n`), pull requests
(closing references or body references), independent review (an approval by someone other than the author), changed
test files, gaps. --solo skips the pull request and review gaps (single-maintainer repository: document the exception).
Issues labelled `epic` (containers) and issues closed as not planned are left out.
--strict exits 1 when a closed issue has gaps. Standard library + gh. Titles are untrusted text and are escaped.
"""
import argparse
import csv
import io
import json
import re
import subprocess
import sys

REF = re.compile(r"(?:Refs|Fixes|Closes|Resolves)[: ]+((?:[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)?)#([0-9]+)")
REQ = re.compile(r"\b(?:REQ|SEC|NFR)-[0-9]+\b")
TEST_PATH = re.compile(r"(^|/)(tests?|__tests__|spec|specs)/|(^|/)test_[^/]*$|[._]test\.[a-z]+$|\.spec\.[a-z]+$|_test\.[a-z]+$")
COLUMNS = ["Requirement", "Issue", "State", "Commits", "Pull requests", "Review", "Tests", "Gaps"]


def run(args, cwd=None):
    done = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError((done.stderr or "command failed").strip()[:200])
    return done.stdout


def gh_json(repo, kind, fields):
    return json.loads(run(["gh", kind, "list", "--repo", repo, "--state", "all", "--limit", "1000", "--json", fields]) or "[]")


def fetch(repo, rng):
    issues = gh_json(repo, "issue", "number,title,state,stateReason,body,labels")
    prs = gh_json(repo, "pr", "number,title,state,body,author,reviews,files,closingIssuesReferences")
    log = run(["git", "log", "--no-merges", "--format=%x1e%h%x1f%B%x1f", "--name-only"] + ([rng] if rng else []))
    return issues, prs, log


def parse_log(log, repo):
    """[(sha, [issue numbers], [files])] - cross-repository references are ignored."""
    out = []
    for rec in log.split("\x1e"):
        if not rec.strip():
            continue
        sha, body, files = (rec.split("\x1f") + ["", ""])[:3]
        nums = sorted({int(n) for r, n in REF.findall(body) if not r or r.lower() == repo.lower()})
        out.append((sha.strip(), nums, [f for f in files.split("\n") if f.strip()]))
    return out


def cell(text):
    text = re.sub(r"\s+", " ", str(text)).strip().replace("|", "\\|")
    risky = text[:1] in ("=", "+", "@") or (text[:1] == "-" and len(text) > 1)
    return "'" + text if risky else text


def build(issues, prs, log, repo, solo=False):
    commits = parse_log(log, repo)
    rows = []
    for issue in sorted(issues, key=lambda i: i["number"]):
        if "epic" in {(l.get("name") or "").lower() for l in issue.get("labels") or []}:
            continue
        if str(issue.get("stateReason") or "").upper() == "NOT_PLANNED":
            continue
        n = issue["number"]
        shas = [s for s, nums, _ in commits if n in nums]
        files = {f for s, nums, fs in commits if n in nums for f in fs}
        linked = []
        for pr in prs:
            closing = {c.get("number") for c in pr.get("closingIssuesReferences") or []}
            body = {int(x) for r, x in REF.findall(pr.get("body") or "") if not r or r.lower() == repo.lower()}
            if n in closing or n in body:
                linked.append(pr)
                files |= {f.get("path", "") for f in pr.get("files") or []}
        reviewed = any(r.get("state") == "APPROVED" and (r.get("author") or {}).get("login") != (pr.get("author") or {}).get("login")
                       for pr in linked for r in pr.get("reviews") or [])
        tests = sorted(f for f in files if TEST_PATH.search(f))
        reqs = sorted(set(REQ.findall(issue["title"] + " " + (issue.get("body") or ""))))
        gaps = []
        if not shas:
            gaps.append("no commit")
        if not tests:
            gaps.append("no test change")
        if not solo:
            if not linked:
                gaps.append("no pull request")
            elif not reviewed:
                gaps.append("no independent review")
        rows.append({
            "Requirement": ", ".join(reqs) or "-", "Issue": f"#{n} {issue['title']}", "State": issue["state"].lower(),
            "Commits": ", ".join(shas) or "-", "Pull requests": ", ".join(f"#{p['number']}" for p in linked) or "-",
            "Review": ("independent" if reviewed else "none") if linked else "n/a",
            "Tests": f"{len(tests)} file(s)" if tests else "-", "Gaps": "; ".join(gaps) or "-"})
    return rows


def render(rows, fmt):
    if fmt == "csv":
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(COLUMNS)
        w.writerows([[cell(r[c]) for c in COLUMNS] for r in rows])
        return buf.getvalue()
    lines = ["| " + " | ".join(COLUMNS) + " |", "|" + "---|" * len(COLUMNS)]
    lines += ["| " + " | ".join(cell(r[c]) for c in COLUMNS) + " |" for r in rows]
    return "\n".join(lines) + "\n"


def main(argv=None, fetcher=fetch):
    ap = argparse.ArgumentParser(description="Requirements traceability matrix (read-only).")
    ap.add_argument("--repo")
    ap.add_argument("--format", choices=("md", "csv"), default="md")
    ap.add_argument("--solo", action="store_true")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--range", dest="rng", help="git range for commits, e.g. v0.9.0..HEAD")
    args = ap.parse_args(argv)
    try:
        repo = args.repo or run(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"]).strip()
        issues, prs, log = fetcher(repo, args.rng)
    except (RuntimeError, OSError, ValueError) as exc:
        print(f"rtm: {exc}", file=sys.stderr)
        return 2
    rows = build(issues, prs, log, repo, args.solo)
    sys.stdout.write(render(rows, args.format))
    gaps = [r for r in rows if r["Gaps"] != "-" and r["State"] == "closed"]
    print(f"{len(rows)} issue(s), {len(gaps)} closed with gaps; this is evidence, not a certification", file=sys.stderr)
    return 1 if args.strict and gaps else 0


if __name__ == "__main__":
    sys.exit(main())
