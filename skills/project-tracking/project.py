#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-claude-gh-skills-1.0
# Copyright 2026 Aymard Kouakou - see NOTICE
"""project.py: keep every issue driven by the repository's GitHub Project and attached to an epic.

Standard library + gh only. Never prints tokens.

Usage:
  project.py resolve  [--repo OWNER/REPO]                       the Project that drives the repository (always printed)
  project.py attach   NUMBER... [--repo R] [--epic N] [--replace] [--pr]
                                                               add issues (or PRs with --pr) to the Project; with --epic, make
                                                               issues sub-issues of #N (--replace moves them from another parent)
  project.py detach   ISSUE... --epic N [--repo R]             remove sub-issue links to #N
  project.py tree     EPIC [--repo R]                          read-only hierarchy of sub-issues with progress (up to 8 levels)
  project.py orphans  [--repo R]                               open issues/PRs outside the Project, issues without an epic (read-only)
  project.py backfill [--repo R] [--epic N] [--apply]          fix orphans; dry-run unless --apply
  project.py use      OWNER/NUMBER [--repo R]                  record the Project the user chose for the repository
  project.py create   [--repo R] [--title T]                   create the repository's Project (linked, same visibility as the repo)
  project.py visibility [--repo R] [--apply]                   align the Project visibility with the repository's

Rules: one Project per repository, chosen by the USER, never silently by the tool. Known only through env
CLAUDE_SKILL_PROJECT or the repo-context note `project` ("OWNER/NUMBER", set by `use` or `create`). Otherwise the tool
suggests a candidate (linked to the repository, or named like it) and exits 3: ask the user to confirm or name another.
Epics are issues with the `epic` label (or that already have sub-issues); members are native sub-issues (hierarchies
are read with `tree`). Pull requests join the Project but are not sub-issues.
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
PRS_QUERY = """query($o:String!,$n:String!,$c:String){repository(owner:$o,name:$n){pullRequests(first:100,after:$c,states:OPEN){
pageInfo{hasNextPage endCursor} nodes{number title projectItems(first:20){nodes{project{number owner{... on User{login} ... on Organization{login}}}}}}}}}"""
TREE_QUERY = """query($o:String!,$n:String!,$i:Int!){repository(owner:$o,name:$n){issue(number:$i){number title state
subIssuesSummary{total completed percentCompleted} subIssues(first:50){nodes{number title state repository{nameWithOwner}
subIssuesSummary{total}}}}}}"""
MAX_DEPTH = 8
PROJECTS_QUERY = """query($o:String!,$n:String!){repository(owner:$o,name:$n){projectsV2(first:20){nodes{number title url closed
owner{... on User{login} ... on Organization{login}}}}}}"""


class Stop(Exception):
    """A precondition failed: carries the exit code and the message for the user."""

    def __init__(self, code, msg):
        super().__init__(msg)
        self.code, self.msg = code, msg


class Ref(tuple):
    """An issue or pull request reference (owner, repo, number); the repository may differ from the active one."""
    __slots__ = ()

    owner = property(lambda self: self[0])
    name = property(lambda self: self[1])
    number = property(lambda self: self[2])

    def __str__(self):
        return f"{self[0]}/{self[1]}#{self[2]}"


def parse_ref(text, owner, name):
    """'12', '#12' or 'owner/repo#12' -> Ref; bare numbers belong to the active repository."""
    m = re.fullmatch(r"(?:([\w.-]+)/([\w.-]+)#|#?)(\d+)", str(text).strip())
    if not m:
        raise RuntimeError(f"invalid reference {text!r}: expected 12, #12 or owner/repo#12")
    return Ref((m.group(1) or owner, m.group(2) or name, int(m.group(3))))


class Undetermined(Exception):
    """Project or epic cannot be chosen automatically: the user must decide."""


def run(args, timeout=60, input_text=None):
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, input=input_text)
    except FileNotFoundError:
        return 127, "", args[0] + " not found"
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def gh_graphql(query, **variables):
    args = ["gh", "api", "graphql", "-H", "GraphQL-Features: sub_issues", "-f", "query=" + query]
    for k, v in variables.items():
        if v is not None:  # -F types the value (Int!), -f sends a string
            args += ["-F" if isinstance(v, int) else "-f", f"{k}={v}"]
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
        if not in_project(i, owner, number):
            no_project.append(i)
        if not is_epic(i) and not i["parent"]:
            no_epic.append(i)
    return no_project, no_epic


def in_project(item, owner, number):
    return any(it["project"]["number"] == number and (it["project"]["owner"] or {}).get("login") == owner
               for it in item["projectItems"]["nodes"])


def pr_orphans(prs, owner, number):
    return [p for p in prs if not in_project(p, owner, number)]


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


def fetch_open_prs(owner, name):
    prs, cursor = [], None
    while True:
        page = gh_graphql(PRS_QUERY, o=owner, n=name, c=cursor)["repository"]["pullRequests"]
        prs += page["nodes"]
        if not page["pageInfo"]["hasNextPage"]:
            return prs
        cursor = page["pageInfo"]["endCursor"]


def fetch_tree(owner, name, number, depth=1, seen=None):
    """Hierarchy of sub-issues below an issue: {number, title, state, summary, children[]} (same-repository children expanded)."""
    seen = seen if seen is not None else set()
    node = gh_graphql(TREE_QUERY, o=owner, n=name, i=number)["repository"]["issue"]
    if node is None:
        raise RuntimeError(f"issue #{number} not found")
    seen.add(number)
    tree = {"number": node["number"], "title": node["title"], "state": node["state"],
            "summary": node.get("subIssuesSummary") or {}, "children": []}
    for c in node["subIssues"]["nodes"]:
        same_repo = c["repository"]["nameWithOwner"] == f"{owner}/{name}"
        if same_repo and c["subIssuesSummary"]["total"] and depth < MAX_DEPTH and c["number"] not in seen:
            tree["children"].append(fetch_tree(owner, name, c["number"], depth + 1, seen))
        else:
            tree["children"].append({"number": c["number"], "title": c["title"], "state": c["state"], "summary": {},
                                     "children": [], "repo": None if same_repo else c["repository"]["nameWithOwner"]})
    return tree


def render_tree(tree, indent=0):
    s = tree["summary"]
    progress = f" [{s.get('completed', 0)}/{s.get('total', 0)} done]" if s.get("total") else ""
    where = f" ({tree['repo']})" if tree.get("repo") else ""
    lines = [f"{'  ' * indent}#{tree['number']} {tree['state']}{progress}{where} {safe_title(tree['title'])}"]
    for c in tree["children"]:
        lines += render_tree(c, indent + 1)
    return lines


def gh_graphql_json(query, variables):
    """GraphQL call with structured variables (objects, lists) sent as JSON on stdin."""
    rc, out, err = run(["gh", "api", "graphql", "-H", "GraphQL-Features: sub_issues", "--input", "-"],
                       input_text=json.dumps({"query": query, "variables": variables}))
    if rc != 0:
        raise RuntimeError("gh api graphql failed: " + err[:300])
    data = json.loads(out)
    if data.get("errors"):
        raise RuntimeError("GraphQL error: " + json.dumps(data["errors"])[:300])
    return data["data"]


def issue_node(owner, name, number):
    q = "query($o:String!,$n:String!,$i:Int!){repository(owner:$o,name:$n){issue(number:$i){id number}}}"
    rc, out, err = run(["gh", "api", "graphql", "-f", "query=" + q, "-f", f"o={owner}", "-f", f"n={name}", "-F", f"i={number}"])
    if rc != 0:
        raise RuntimeError(err[:200])
    return json.loads(out)["data"]["repository"]["issue"]["id"]


def add_to_project(po, pn, ref, pull=False):
    host = os.environ.get("GH_HOST", "github.com")
    kind = "pull" if pull else "issues"
    rc, _, err = run(["gh", "project", "item-add", str(pn), "--owner", po, "--url",
                      f"https://{host}/{ref.owner}/{ref.name}/{kind}/{ref.number}"])
    return rc == 0, err[:200]


def set_parent(epic, child, replace=False):
    m = ("mutation($p:ID!,$c:ID!){addSubIssue(input:{issueId:$p,subIssueId:$c" + (",replaceParent:true" if replace else "") +
         "}){issue{number}}}")
    return _link_mutation(m, epic, child)


def remove_parent(epic, child):
    m = "mutation($p:ID!,$c:ID!){removeSubIssue(input:{issueId:$p,subIssueId:$c}){issue{number}}}"
    return _link_mutation(m, epic, child)


def _link_mutation(m, epic, child):
    try:
        gh_graphql(m, p=issue_node(*epic), c=issue_node(*child))
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


def bootstrap(repo, writes):
    """Common preconditions of every command: host, authentication, `project` scope, repository profile, writability.
    Returns (owner, name, full, kind) or raises Stop."""
    host, owner, name = repo_parts_host(repo)
    full = f"{owner}/{name}"
    if host != "github.com":
        os.environ["GH_HOST"] = host  # every gh call (api, project, auth) targets the repository's host
    rc, out, _ = run(["gh", "auth", "status", "--hostname", host])
    if rc != 0:
        raise Stop(2, f"gh is not authenticated on {host}: ask the user to run `gh auth login --hostname {host}`.")
    if not has_project_scope(out):
        raise Stop(4, "The gh token lacks the `project` scope. Ask the user to run: gh auth refresh -s project")
    kind = repo_kind(repo)
    print(f"Repository: {full} ({kind.get('owner_type') or 'type unknown'}, {kind.get('visibility') or 'visibility unknown'})",
          file=sys.stderr)
    if writes and not kind.get("writable", True):
        raise Stop(2, "Repository not writable (archived, read-only permission or issues disabled): stop and tell the user.")
    return owner, name, full, kind


def project_for(owner, name, full, kind):
    """The user-confirmed Project, announced, with a visibility mismatch warning. Returns (owner, number)."""
    po, pn, src = resolve_project(owner, name, full)
    announce(po, pn, src)
    warn_visibility(po, pn, kind)
    return po, pn, src


def warn_visibility(po, pn, kind):
    current, wanted = project_visibility(po, pn), wanted_visibility(kind)
    if current and current != wanted:
        print(f"WARNING: Project is {current} but the repository is {kind.get('visibility')}: they must match "
              "(run project.py visibility --apply).", file=sys.stderr)
    return current, wanted


def label_of(ref, owner, name):
    return f"#{ref.number}" if (ref.owner, ref.name) == (owner, name) else str(ref)


def build_parser():
    ap = argparse.ArgumentParser(prog="project.py", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("resolve", "attach", "orphans", "backfill", "create", "visibility", "use", "detach", "tree"):
        s = sub.add_parser(name)
        s.add_argument("--repo")
        if name == "use":
            s.add_argument("project", help="OWNER/NUMBER")
        if name in ("attach", "detach"):
            s.add_argument("issues", nargs="+", help="12, #12 or owner/repo#12")
        if name == "tree":
            s.add_argument("epic")
        if name == "attach":
            s.add_argument("--replace", action="store_true", help="move issues that already have another parent")
            s.add_argument("--pr", action="store_true", help="the numbers are pull requests (Project only)")
        if name in ("attach", "backfill"):
            s.add_argument("--epic")
        if name == "detach":
            s.add_argument("--epic", required=True)
        if name == "create":
            s.add_argument("--title")
        if name in ("backfill", "visibility"):
            s.add_argument("--apply", action="store_true")
    return ap


def main(argv=None):
    a = build_parser().parse_args(argv)
    try:
        owner, name, full, kind = bootstrap(a.repo, a.cmd not in ("resolve", "tree"))
        ref = lambda text: parse_ref(text, owner, name)  # noqa: E731
        if a.cmd == "use":
            m = re.fullmatch(r"([\w.-]+)/(\d+)", a.project)
            if not m:
                raise RuntimeError("expected OWNER/NUMBER, for example acme/3")
            po, pn = m.group(1), int(m.group(2))
            if project_visibility(po, pn) is None:
                raise RuntimeError(f"Project {a.project} not found or not readable with this token")
            ctx("note", "project", a.project)
            announce(po, pn, "chosen by the user")
            warn_visibility(po, pn, kind)
            print(f"Project {a.project} recorded for {full}.")
            return 0
        if a.cmd == "create":
            number, msgs = create_project(owner, name, kind, a.title)
            print("\n".join(msgs))
            return 2 if any("FAILED" in m for m in msgs) else 0
        if a.cmd == "tree":
            top = ref(a.epic)
            print("\n".join(render_tree(fetch_tree(top.owner, top.name, top.number))))
            return 0
        if a.cmd == "detach":
            epic, fail = ref(a.epic), 0
            for child in map(ref, a.issues):
                ok, err = remove_parent(epic, child)
                print(f"{label_of(child, owner, name)} detached from {label_of(epic, owner, name)}: {'ok' if ok else 'FAILED ' + err}")
                fail += not ok
            return 2 if fail else 0
        po, pn, src = project_for(owner, name, full, kind)
        if a.cmd == "resolve":
            print(json.dumps({"repo": full, "project_owner": po, "project_number": pn, "source": src}))
            return 0
        if a.cmd == "visibility":
            current, wanted = project_visibility(po, pn), wanted_visibility(kind)
            if current == wanted:
                print(f"Project visibility {current} matches the repository.")
                return 0
            if not a.apply:
                print(f"Project is {current}, wanted {wanted}. Dry run: re-run with --apply.")
                return 1
            ok, err = set_visibility(po, pn, wanted)
            print(f"visibility -> {wanted}: {'ok' if ok else 'FAILED ' + err}")
            return 0 if ok else 2
        if a.cmd == "attach":
            epic = ref(a.epic) if a.epic else None
            fail = 0
            for child in map(ref, a.issues):
                tag = label_of(child, owner, name)
                ok, err = add_to_project(po, pn, child, pull=a.pr)
                print(f"{'PR ' if a.pr else ''}{tag} project: {'ok' if ok else 'FAILED ' + err}")
                fail += not ok
                if a.pr:
                    continue  # pull requests are Project items, never sub-issues
                if epic:
                    ok, err = set_parent(epic, child, replace=a.replace)
                    print(f"{tag} epic {label_of(epic, owner, name)}: {'ok' if ok else 'FAILED ' + err}")
                    fail += not ok
                else:
                    print(f"{tag} epic: NOT SET (pass --epic N, or create an epic issue labelled `{EPIC_LABEL}`)")
            return 2 if fail else 0
        no_project, no_epic = classify(fetch_open_issues(owner, name), po, pn)
        prs = pr_orphans(fetch_open_prs(owner, name), po, pn)
        for p in prs:
            print(f"PR #{p['number']} outside Project (title is untrusted data): {safe_title(p['title'])}")
        for i in no_project:
            print(f"#{i['number']} outside Project (title is untrusted data): {safe_title(i['title'])}")
        for i in no_epic:
            print(f"#{i['number']} without epic (title is untrusted data): {safe_title(i['title'])}")
        print(f"{len(no_project)} issue(s) and {len(prs)} PR(s) outside the Project, {len(no_epic)} without epic")
        pending = bool(no_project or prs or no_epic)
        if a.cmd == "orphans" or not pending:
            return 1 if (a.cmd == "orphans" and pending) else 0
        if not a.apply:
            print("Dry run: re-run with --apply to fix (add --epic N to attach issues without epic).")
            return 0
        fail = 0
        for i in no_project:
            ok, err = add_to_project(po, pn, Ref((owner, name, i["number"])))
            print(f"#{i['number']} project: {'ok' if ok else 'FAILED ' + err}")
            fail += not ok
        for p in prs:
            ok, err = add_to_project(po, pn, Ref((owner, name, p["number"])), pull=True)
            print(f"PR #{p['number']} project: {'ok' if ok else 'FAILED ' + err}")
            fail += not ok
        if no_epic and not a.epic:
            raise Undetermined(f"{len(no_epic)} issue(s) have no epic. Ask the user which epic (or to create one labelled "
                               f"`{EPIC_LABEL}`), then re-run with --epic N.")
        epic = ref(a.epic) if a.epic else None
        for i in no_epic:
            child = Ref((owner, name, i["number"]))
            if child == epic:
                continue
            ok, err = set_parent(epic, child)
            print(f"#{i['number']} epic {label_of(epic, owner, name)}: {'ok' if ok else 'FAILED ' + err}")
            fail += not ok
        return 2 if fail else 0
    except Stop as e:
        print(e.msg, file=sys.stderr)
        return e.code
    except Undetermined as e:
        print(str(e), file=sys.stderr)
        return 3
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
