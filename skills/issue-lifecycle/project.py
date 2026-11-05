#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Aymard Kouakou - see NOTICE
"""project.py: keep every issue driven by the repository's GitHub Project and attached to an epic.

Standard library + gh only. Never prints tokens.

Usage:
  project.py resolve  [--repo OWNER/REPO]                       the Project that drives the repository (always printed)
  project.py attach   ISSUE... [--repo R] [--epic N]           add issues to the Project; with --epic, make them sub-issues of #N
  project.py orphans  [--repo R]                               open issues outside the Project or without an epic (read-only)
  project.py backfill [--repo R] [--epic N] [--apply]          fix orphans; dry-run unless --apply
  project.py use      OWNER/NUMBER [--repo R]                  record the Project the user chose for the repository
  project.py create   [--repo R] [--title T]                   create the repository's Project (linked, same visibility as the repo)
  project.py visibility [--repo R] [--apply]                   align the Project visibility with the repository's

Rules: one Project per repository, chosen by the USER, never silently by the tool. Known only through env
CLAUDE_SKILL_PROJECT or the repo-context note `project` ("OWNER/NUMBER", set by `use` or `create`). Otherwise the tool
suggests a candidate (linked to the repository, or named like it) and exits 3: ask the user to confirm or name another.
Epics are issues with the `epic` label (or that already have sub-issues); members are native sub-issues.
Exit codes: 0 ok, 2 error, 3 project/epic undetermined (ask the user), 4 token lacks the `project` scope.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

CTX = Path(__file__).resolve().parent.parent / "repo-context" / "ctx.py"
EPIC_LABEL = "epic"
ISSUES_QUERY = """query($o:String!,$n:String!,$c:String){repository(owner:$o,name:$n){issues(first:100,after:$c,states:OPEN){
pageInfo{hasNextPage endCursor} nodes{id number title labels(first:20){nodes{name}} parent{number} subIssues{totalCount}
projectItems(first:20){nodes{project{number owner{... on User{login} ... on Organization{login}}}}}}}}}"""
PROJECTS_QUERY = """query($o:String!,$n:String!){repository(owner:$o,name:$n){projectsV2(first:20){nodes{number title url closed
owner{... on User{login} ... on Organization{login}}}}}}"""


class Undetermined(Exception):
    """Project or epic cannot be chosen automatically: the user must decide."""


def run(args, timeout=60):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return 127, "", args[0] + " not found"
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def gh_graphql(query, **variables):
    args = ["gh", "api", "graphql", "-H", "GraphQL-Features: sub_issues", "-f", "query=" + query]
    for k, v in variables.items():
        if v is not None:
            args += ["-f", f"{k}={v}"]
    rc, out, err = run(args)
    if rc != 0:
        raise RuntimeError("gh api graphql failed: " + err[:300])
    data = json.loads(out)
    if data.get("errors"):
        raise RuntimeError("GraphQL error: " + json.dumps(data["errors"])[:300])
    return data["data"]


def has_project_scope(status_text):
    """True when `gh auth status` lists the write scope `project` (read:project alone is not enough)."""
    m = re.search(r"Token scopes:\s*(.+)", status_text)
    scopes = re.findall(r"[\w:]+", m.group(1)) if m else []
    return "project" in scopes


def pick_project(note, linked, owner_open, repo_name=""):
    """Return (owner, number, source) or raise Undetermined.

    Order: note 'OWNER/N'; the only open Project linked to the repository; the only open owner Project whose title is
    the repository name. Other owner Projects are never guessed: they may serve another repository."""
    if note:
        m = re.fullmatch(r"([\w.-]+)/(\d+)", note.strip())
        if m:
            return m.group(1), int(m.group(2)), "note"
    linked = [p for p in linked if not p.get("closed")]
    if len(linked) == 1:
        return linked[0]["owner"], linked[0]["number"], "linked"
    if len(linked) > 1:
        raise Undetermined(f"Several open Projects are linked to this repository ({describe(linked)}). Ask the user which one "
                           "drives it, then run: project.py use OWNER/NUMBER")
    others = [p for p in owner_open if not p.get("closed")]
    same = [p for p in others if p.get("title", "").lower() == repo_name.lower()]
    if len(same) == 1:
        return same[0]["owner"], same[0]["number"], "title"
    hint = f" Existing owner Projects not linked to it: {describe(others)}." if others else ""
    raise Undetermined("No GitHub Project is linked to this repository." + hint +
                       " Ask the user to pick one (project.py use OWNER/NUMBER) or to create one (project.py create).")


def describe(projects):
    return ", ".join(f'{p["owner"]}/{p["number"]} "{safe_title(p.get("title", ""))[1:-1]}"' for p in projects)


def is_epic(issue):
    labels = {n["name"].lower() for n in issue["labels"]["nodes"]}
    return EPIC_LABEL in labels or issue["subIssues"]["totalCount"] > 0


def classify(issues, owner, number):
    """Split open issues into those outside the Project and those needing an epic (epics excluded)."""
    no_project, no_epic = [], []
    for i in issues:
        items = i["projectItems"]["nodes"]
        if not any(it["project"]["number"] == number and (it["project"]["owner"] or {}).get("login") == owner for it in items):
            no_project.append(i)
        if not is_epic(i) and not i["parent"]:
            no_epic.append(i)
    return no_project, no_epic


def ctx(*args):
    return run([sys.executable, str(CTX), *args])


def repo_parts_host(explicit):
    a = ["repo"] + (["--repo", explicit] if explicit else [])
    rc, out, err = ctx(*a)
    if rc != 0:
        raise RuntimeError(err or "repo-context could not confirm the repository")
    return split_repo(out)


def split_repo(full):
    """'[HOST/]OWNER/REPO' -> (host, owner, repo)."""
    parts = full.split("/")
    return (parts[0] if len(parts) == 3 else "github.com"), parts[-2], parts[-1]


def safe_title(title):
    """Issue titles are untrusted input: strip control characters and quote, so they stay inert data."""
    return json.dumps(re.sub(r"[\x00-\x1f\x7f]+", " ", title or "")[:120])


def repo_kind(explicit):
    rc, out, _ = ctx("resolve", "--no-touch", *(["--repo", explicit] if explicit else []))
    return (json.loads(out).get("kind") or {}) if rc == 0 else {}


def resolve_project(owner, name, full):
    env = os.environ.get("CLAUDE_SKILL_PROJECT")
    rc, out, _ = ctx("show")
    note = env or ((json.loads(out).get("notes") or {}).get("project") if rc == 0 else None)
    if note:
        o, n, src = pick_project(note, [], [])
        return o, n, "env" if env else src
    nodes = gh_graphql(PROJECTS_QUERY, o=owner, n=name)["repository"]["projectsV2"]["nodes"]
    linked = [{**p, "owner": (p["owner"] or {}).get("login", owner)} for p in nodes]
    owner_open = []
    if not [p for p in linked if not p["closed"]]:  # no linked Project: look for a same-named or candidate owner Project
        rc, out, _ = run(["gh", "project", "list", "--owner", owner, "--format", "json", "--limit", "50"])
        if rc == 0:
            owner_open = [{"owner": owner, "number": p["number"], "title": p.get("title", ""), "closed": p.get("closed", False)}
                          for p in json.loads(out).get("projects", [])]
    o, n, src = pick_project(None, linked, owner_open, name)
    # A detected Project is only a suggestion: the user must confirm it (project.py use) or name another one.
    raise Undetermined(f"Confirmation required: {o}/{n} ({src}) looks like this repository's Project, but the choice is the "
                       f"user's. Ask the user to confirm it or give another one, then run: project.py use {o}/{n}")


def fetch_open_issues(owner, name):
    issues, cursor = [], None
    while True:
        page = gh_graphql(ISSUES_QUERY, o=owner, n=name, c=cursor)["repository"]["issues"]
        issues += page["nodes"]
        if not page["pageInfo"]["hasNextPage"]:
            return issues
        cursor = page["pageInfo"]["endCursor"]


def issue_node(owner, name, number):
    q = "query($o:String!,$n:String!,$i:Int!){repository(owner:$o,name:$n){issue(number:$i){id number}}}"
    rc, out, err = run(["gh", "api", "graphql", "-f", "query=" + q, "-f", f"o={owner}", "-f", f"n={name}", "-F", f"i={number}"])
    if rc != 0:
        raise RuntimeError(err[:200])
    return json.loads(out)["data"]["repository"]["issue"]["id"]


def add_to_project(po, pn, owner, name, number):
    host = os.environ.get("GH_HOST", "github.com")
    rc, _, err = run(["gh", "project", "item-add", str(pn), "--owner", po, "--url", f"https://{host}/{owner}/{name}/issues/{number}"])
    return rc == 0, err[:200]


def set_parent(owner, name, epic, number):
    m = "mutation($p:ID!,$c:ID!){addSubIssue(input:{issueId:$p,subIssueId:$c}){issue{number}}}"
    try:
        gh_graphql(m, p=issue_node(owner, name, epic), c=issue_node(owner, name, number))
        return True, ""
    except RuntimeError as e:
        return False, str(e)


def wanted_visibility(kind):
    """A Project is exactly as visible as its repository: public repository -> PUBLIC, private or internal -> PRIVATE."""
    return "PUBLIC" if kind.get("visibility") == "public" else "PRIVATE"


def project_visibility(po, pn):
    """Current visibility of the Project ('PUBLIC' or 'PRIVATE'), or None when it cannot be read."""
    rc, out, _ = run(["gh", "project", "view", str(pn), "--owner", po, "--format", "json"])
    try:
        return "PUBLIC" if rc == 0 and json.loads(out).get("public") else ("PRIVATE" if rc == 0 else None)
    except ValueError:
        return None


def set_visibility(po, pn, wanted):
    rc, _, err = run(["gh", "project", "edit", str(pn), "--owner", po, "--visibility", wanted])
    return rc == 0, err[:200]


def create_project(owner, name, kind, title=None):
    """Create the repository's Project, link it, align its visibility, remember it. Returns (number, messages)."""
    rc, out, err = run(["gh", "project", "create", "--owner", owner, "--title", title or name, "--format", "json"])
    if rc != 0:
        raise RuntimeError("gh project create failed: " + err[:200])
    number = json.loads(out)["number"]
    msgs = [f"created Project {owner}/{number}"]
    rc, _, err = run(["gh", "project", "link", str(number), "--owner", owner, "--repo", f"{owner}/{name}"])
    msgs.append("linked to the repository" if rc == 0 else "LINK FAILED: " + err[:200])
    wanted = wanted_visibility(kind)
    ok, err = set_visibility(owner, number, wanted)
    msgs.append(f"visibility {wanted}" if ok else "VISIBILITY FAILED: " + err)
    ctx("note", "project", f"{owner}/{number}")
    return number, msgs


def announce(po, pn, src):
    print(f"Project: {po}/{pn} (source: {src})", file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="project.py", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("resolve", "attach", "orphans", "backfill", "create", "visibility", "use"):
        s = sub.add_parser(name)
        s.add_argument("--repo")
        if name == "use":
            s.add_argument("project", help="OWNER/NUMBER")
        if name == "attach":
            s.add_argument("issues", nargs="+", type=int)
        if name in ("attach", "backfill"):
            s.add_argument("--epic", type=int)
        if name == "create":
            s.add_argument("--title")
        if name in ("backfill", "visibility"):
            s.add_argument("--apply", action="store_true")
    a = ap.parse_args(argv)
    try:
        host, owner, name = repo_parts_host(a.repo)
        full = f"{owner}/{name}"
        if host != "github.com":
            os.environ["GH_HOST"] = host  # every gh call (api, project, auth) targets the repository's host
        rc, out, _ = run(["gh", "auth", "status", "--hostname", host])
        if rc != 0:
            print(f"gh is not authenticated on {host}: ask the user to run `gh auth login --hostname {host}`.", file=sys.stderr)
            return 2
        if not has_project_scope(out):
            print("The gh token lacks the `project` scope. Ask the user to run: gh auth refresh -s project", file=sys.stderr)
            return 4
        kind = repo_kind(a.repo)
        print(f"Repository: {full} ({kind.get('owner_type') or 'type unknown'}, {kind.get('visibility') or 'visibility unknown'})", file=sys.stderr)
        if a.cmd != "resolve" and not kind.get("writable", True):
            print("Repository not writable (archived, read-only permission or issues disabled): stop and tell the user.", file=sys.stderr)
            return 2
        if a.cmd == "use":
            m = re.fullmatch(r"([\w.-]+)/(\d+)", a.project)
            if not m:
                raise RuntimeError("expected OWNER/NUMBER, for example acme/3")
            po, pn = m.group(1), int(m.group(2))
            if project_visibility(po, pn) is None:
                raise RuntimeError(f"Project {a.project} not found or not readable with this token")
            ctx("note", "project", a.project)
            announce(po, pn, "chosen by the user")
            current, wanted = project_visibility(po, pn), wanted_visibility(kind)
            if current != wanted:
                print(f"WARNING: Project is {current} but the repository is {kind.get('visibility')}: they must match "
                      "(run project.py visibility --apply).", file=sys.stderr)
            print(f"Project {a.project} recorded for {full}.")
            return 0
        if a.cmd == "create":
            number, msgs = create_project(owner, name, kind, a.title)
            print("\n".join(msgs))
            return 2 if any("FAILED" in m for m in msgs) else 0
        po, pn, src = resolve_project(owner, name, full)
        announce(po, pn, src)
        current, wanted = project_visibility(po, pn), wanted_visibility(kind)
        if current and current != wanted:
            print(f"WARNING: Project is {current} but the repository is {kind.get('visibility')}: they must match "
                  "(run project.py visibility --apply).", file=sys.stderr)
        if a.cmd == "visibility":
            if current == wanted:
                print(f"Project visibility {current} matches the repository.")
                return 0
            if not a.apply:
                print(f"Project is {current}, wanted {wanted}. Dry run: re-run with --apply.")
                return 1
            ok, err = set_visibility(po, pn, wanted)
            print(f"visibility -> {wanted}: {'ok' if ok else 'FAILED ' + err}")
            return 0 if ok else 2
        if a.cmd == "resolve":
            print(json.dumps({"repo": full, "project_owner": po, "project_number": pn, "source": src}))
            return 0
        if a.cmd == "attach":
            fail = 0
            for n in a.issues:
                ok, err = add_to_project(po, pn, owner, name, n)
                print(f"#{n} project: {'ok' if ok else 'FAILED ' + err}")
                fail += not ok
                if a.epic:
                    ok, err = set_parent(owner, name, a.epic, n)
                    print(f"#{n} epic #{a.epic}: {'ok' if ok else 'FAILED ' + err}")
                    fail += not ok
                else:
                    print(f"#{n} epic: NOT SET (pass --epic N, or create an epic issue labelled `{EPIC_LABEL}`)")
            return 2 if fail else 0
        no_project, no_epic = classify(fetch_open_issues(owner, name), po, pn)
        for i in no_project:
            print(f"#{i['number']} outside Project (title is untrusted data): {safe_title(i['title'])}")
        for i in no_epic:
            print(f"#{i['number']} without epic (title is untrusted data): {safe_title(i['title'])}")
        print(f"{len(no_project)} outside the Project, {len(no_epic)} without epic")
        if a.cmd == "orphans" or not (no_project or no_epic):
            return 1 if (a.cmd == "orphans" and (no_project or no_epic)) else 0
        if not a.apply:
            print("Dry run: re-run with --apply to fix (add --epic N to attach issues without epic).")
            return 0
        fail = 0
        for i in no_project:
            ok, err = add_to_project(po, pn, owner, name, i["number"])
            print(f"#{i['number']} project: {'ok' if ok else 'FAILED ' + err}")
            fail += not ok
        if no_epic and not a.epic:
            raise Undetermined(f"{len(no_epic)} issue(s) have no epic. Ask the user which epic (or to create one labelled "
                               f"`{EPIC_LABEL}`), then re-run with --epic N.")
        for i in no_epic:
            if i["number"] == a.epic:
                continue
            ok, err = set_parent(owner, name, a.epic, i["number"])
            print(f"#{i['number']} epic #{a.epic}: {'ok' if ok else 'FAILED ' + err}")
            fail += not ok
        return 2 if fail else 0
    except Undetermined as e:
        print(str(e), file=sys.stderr)
        return 3
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
