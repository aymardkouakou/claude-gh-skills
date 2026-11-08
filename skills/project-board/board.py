#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-claude-gh-skills-1.1
# Copyright 2026 Aymard Kouakou - see NOTICE
"""board.py: standard fields, views, reports and items for the repository's GitHub Project (follow-up optimisation).

Standard library + gh only. Same safety rules as project.py (user-confirmed Project, writable repository, host honoured).

Usage:
  board.py fields   [--repo R]                              list the Project fields and their options (read-only)
  board.py setup    [--repo R] [--apply]                    create the missing standard fields (dry-run unless --apply)
  board.py views    [--repo R] [--apply]                    create the missing standard views (dry-run unless --apply)
  board.py report   [--repo R] [--post] [--status S] [--with-titles]
                                                            follow-up metrics; --post publishes a Project status update
                                                            (counts only; titles only if --with-titles and nothing can leak)
  board.py report   --html FILE [--with-titles] [--status S]
                                                            also write a static, self-contained HTML page (no script, no
                                                            external resource); titles follow the same publication rule
  board.py set      REF --field NAME --value V [--pr]       set a field value on an issue or pull request item
  board.py draft    TITLE [--body TEXT]                     add a draft item to the Project
  board.py drafts   [--repo R]                              list draft items
  board.py convert  ITEM_ID [--repo R]                      turn a draft item into an issue of the repository
  board.py tasklist EPIC [--apply] [--create] [--allow-cross-repo]
                                                            turn `- [ ] #n` task lists of an epic into sub-issues
                                                            (--create also makes issues from plain `- [ ] text` lines;
                                                            references to other repositories need --allow-cross-repo)

The API cannot set a view's grouping or sorting, nor enable the built-in workflows: `views` prints those manual steps.
Exit codes as project.py: 0 ok, 1 differences found (dry run), 2 error, 3 project undetermined, 4 missing scope.
"""
import argparse
import html
import importlib.util
import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

_PROJECT_PY = Path(__file__).resolve().parent.parent / "project-tracking" / "project.py"
if not _PROJECT_PY.is_file():
    sys.exit(f"board.py needs the project-tracking skill (expected {_PROJECT_PY}): install the whole plugin or run ./install.sh")
_spec = importlib.util.spec_from_file_location("project", _PROJECT_PY)
project = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(project)

COLORS = {"High": "RED", "Medium": "YELLOW", "Low": "GREEN", "Bug": "RED", "Feature": "BLUE", "Chore": "GRAY",
          "Docs": "PURPLE", "Security": "ORANGE"}
STANDARD_FIELDS = [
    {"name": "Priority", "type": "SINGLE_SELECT", "options": ["High", "Medium", "Low"]},
    {"name": "Kind", "type": "SINGLE_SELECT", "options": ["Bug", "Feature", "Chore", "Docs", "Security"]},
    {"name": "Estimate", "type": "NUMBER"},
    {"name": "Target date", "type": "DATE"},
    {"name": "Iteration", "type": "ITERATION"},
]
ITERATION_DAYS = 14
STALE_DAYS = 30
# name, layout, filter, fields the filter needs, manual settings the API cannot apply
STANDARD_VIEWS = [
    ("Board", "board", "is:open", [], "columns by Status are the default; sort by Priority"),
    ("Backlog", "table", "is:open status:Todo", [], "sort by Priority, then Created"),
    ("Current iteration", "board", "iteration:@current", ["Iteration"], "columns by Status"),
    ("Roadmap", "roadmap", "is:open", ["Target date"], "dates: Target date; group by Parent issue"),
    ("Epics", "table", "label:epic", [], "show Sub-issues progress; sort by Updated"),
    ("By epic", "table", "is:open -label:epic", [], "group by Parent issue"),
    ("Without epic", "table", "is:issue is:open no:parent-issue -label:epic", [], "none"),
    ("My work", "table", "assignee:@me is:open", [], "group by Status"),
    ("Needs triage", "table", "is:open no:priority", ["Priority"], "sort by Created"),
    ("In review", "table", "is:pr is:open", [], "show Reviewers and Linked pull requests"),
    ("Blocked", "table", "label:blocked is:open", [], "sort by Updated"),
    ("Bugs", "table", "label:bug is:open", [], "sort by Priority"),
    ("Security", "table", "label:security is:open", [], "sort by Priority"),
    ("Stale", "table", f"is:open updated:<@today-{STALE_DAYS}d", [], "sort by Updated (oldest first)"),
    ("Done", "table", "status:Done", [], "sort by Closed (newest first)"),
]
WORKFLOWS_HINT = ("Built-in workflows cannot be enabled through the API; in the Project, Workflows: enable "
                  "'Item added to project' (Status Todo), 'Item closed' and 'Pull request merged' (Status Done), "
                  "'Auto-add to project' for this repository, and 'Auto-archive items'.")


def plan_fields(existing_names, standard=STANDARD_FIELDS):
    """Standard fields not yet in the Project (case-insensitive)."""
    have = {n.lower() for n in existing_names}
    return [f for f in standard if f["name"].lower() not in have]


def plan_views(existing_names, field_names, standard=STANDARD_VIEWS):
    """(to_create, skipped) where skipped explains why a view cannot be created yet."""
    have, fields = {n.lower() for n in existing_names}, {n.lower() for n in field_names}
    create, skipped = [], []
    for v in standard:
        if v[0].lower() in have:
            continue
        missing = [f for f in v[3] if f.lower() not in fields]
        (skipped.append((v[0], missing)) if missing else create.append(v))
    return create, skipped


def option_input(name):
    return {"name": name, "color": COLORS.get(name, "GRAY"), "description": name}


def field_mutation(project_id, spec, start=None):
    """GraphQL (query, variables) creating one standard field."""
    q = ("mutation($i:CreateProjectV2FieldInput!){createProjectV2Field(input:$i){projectV2Field{... on ProjectV2FieldCommon{name}}}}")
    v = {"projectId": project_id, "name": spec["name"], "dataType": spec["type"]}
    if spec["type"] == "SINGLE_SELECT":
        v["singleSelectOptions"] = [option_input(o) for o in spec["options"]]
    if spec["type"] == "ITERATION":
        v["iterationConfiguration"] = {"startDate": (start or next_monday()).isoformat(), "duration": ITERATION_DAYS, "iterations": []}
    return q, {"i": v}


def next_monday(today=None):
    today = today or date.today()
    return today + timedelta(days=(7 - today.weekday()) % 7 or 7)


def parse_time(text):
    return datetime.fromisoformat(text.replace("Z", "+00:00")) if text else None


def metrics(items, updated=None, progress=None, now=None, stale_days=STALE_DAYS):
    """Follow-up numbers from `gh project item-list` items (lower-cased custom field keys).

    updated: {issue/PR number: datetime of last update}; progress: {epic number: (completed, total)} (item-list has neither)."""
    updated, progress = updated or {}, progress or {}
    now = now or datetime.now(timezone.utc)
    by_status, m = {}, {"total": len(items), "open": 0, "prs": 0, "drafts": 0, "no_assignee": 0, "no_priority": 0,
                        "blocked": 0, "stale": 0, "epics": []}
    for it in items:
        status = it.get("status") or "No status"
        by_status[status] = by_status.get(status, 0) + 1
        content, labels = it.get("content") or {}, [l.lower() for l in it.get("labels") or []]
        kind = content.get("type")
        m["drafts"] += kind == "DraftIssue"
        m["prs"] += kind == "PullRequest" and status != "Done"
        if status == "Done":
            continue
        m["open"] += 1
        m["no_assignee"] += not it.get("assignees")
        m["no_priority"] += not it.get("priority")
        m["blocked"] += "blocked" in labels
        last = updated.get(content.get("number"))
        m["stale"] += bool(last and (now - last).days >= stale_days)
        if "epic" in labels:
            done, total = progress.get(content.get("number"), (0, 0))
            m["epics"].append({"title": it.get("title", ""), "number": content.get("number"), "done": done, "total": total})
    m["by_status"] = by_status
    return m


def derive_status(m):
    """ON_TRACK / AT_RISK / OFF_TRACK from the numbers (the user can override with --status)."""
    if m["open"] and m["stale"] * 2 >= m["open"]:
        return "OFF_TRACK"
    return "AT_RISK" if (m["blocked"] or m["stale"]) else "ON_TRACK"


def render_report(m, title, titles=True):
    lines = [f"Project {title}: {m['total']} item(s), {m['open']} open, {m['prs']} open PR(s), {m['drafts']} draft(s)"]
    lines += [f"  {k}: {v}" for k, v in sorted(m["by_status"].items())]
    lines.append(f"Attention: {m['no_assignee']} unassigned, {m['no_priority']} without priority, {m['blocked']} blocked, "
                 f"{m['stale']} stale (>= {STALE_DAYS} days)")
    for e in m["epics"]:
        name = f" {project.safe_title(e['title'])}" if titles else ""
        lines.append(f"Epic #{e['number']}{name}: {e['done']}/{e['total']} done")
    return lines


STATUS_LABELS = {"ON_TRACK": "On track", "AT_RISK": "At risk", "OFF_TRACK": "Off track", "INACTIVE": "Inactive",
                 "COMPLETE": "Complete"}
HTML_STYLE = """:root{--bg:#fff;--fg:#1f2328;--muted:#656d76;--line:#d0d7de;--ok:#1a7f37;--warn:#9a6700;--bad:#cf222e;--bar:#0969da}
@media (prefers-color-scheme:dark){:root{--bg:#0d1117;--fg:#e6edf3;--muted:#8d96a0;--line:#30363d;--ok:#3fb950;--warn:#d29922;--bad:#f85149;--bar:#58a6ff}}
body{margin:0;padding:24px 16px;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif}
main{max-width:760px;margin:0 auto}h1{font-size:1.5rem;margin:0 0 4px}h2{font-size:1.1rem;margin:28px 0 8px}
.muted{color:var(--muted);font-size:.9rem}.badge{display:inline-block;padding:2px 10px;border:1px solid var(--line);border-radius:999px;font-weight:600}
.ON_TRACK,.COMPLETE{color:var(--ok)}.AT_RISK{color:var(--warn)}.OFF_TRACK{color:var(--bad)}
table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line)}
progress{width:100%;height:10px;accent-color:var(--bar)}"""


def render_html(m, title, status, titles=False, now=None):
    """A static page for the follow-up metrics. Every dynamic value is escaped; no script, no external resource."""
    e = html.escape
    now = now or datetime.now(timezone.utc)
    rows = "".join(f"<tr><td>{e(k)}</td><td>{v}</td></tr>" for k, v in sorted(m["by_status"].items()))
    attention = [("Unassigned", m["no_assignee"]), ("Without priority", m["no_priority"]), ("Blocked", m["blocked"]),
                 (f"Stale (>= {STALE_DAYS} days)", m["stale"])]
    att = "".join(f"<tr><td>{e(k)}</td><td>{v}</td></tr>" for k, v in attention)
    epics = ""
    for ep in m["epics"]:
        name = f" {e(project.safe_title(ep['title']))}" if titles else ""
        epics += (f"<p><strong>Epic #{int(ep['number'])}</strong>{name}<br><progress max=\"{int(ep['total'])}\" "
                  f"value=\"{int(ep['done'])}\"></progress><span class=\"muted\">{int(ep['done'])}/{int(ep['total'])} done</span></p>")
    return (f"<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            f"<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<meta http-equiv=\"Content-Security-Policy\" content=\"default-src 'none'; style-src 'unsafe-inline'\">"
            f"<title>Progress report</title><style>{HTML_STYLE}</style></head><body><main>"
            f"<h1>{e(title)}</h1><p><span class=\"badge {e(status)}\">{e(STATUS_LABELS.get(status, status))}</span> "
            f"<span class=\"muted\">Snapshot of {now:%Y-%m-%d %H:%M} UTC, not live data</span></p>"
            f"<p>{m['total']} item(s), {m['open']} open, {m['prs']} open PR(s), {m['drafts']} draft(s)</p>"
            f"<h2>By status</h2><table>{rows}</table><h2>Attention</h2><table>{att}</table>"
            f"<h2>Epics</h2>{epics or '<p class=\"muted\">No epic.</p>'}</main></body></html>\n")


def ensure_titles_publishable(po, pn, kind, items, full):
    vis = project.project_visibility(po, pn)
    if vis is None:  # fail closed: unknown visibility is treated as the most exposed case
        raise RuntimeError("refused: cannot determine the Project visibility. Publish the counts only (drop --with-titles).")
    if not titles_may_be_published(vis == "PUBLIC", kind.get("visibility") == "public", items, full):
        raise RuntimeError("refused: titles would be published on a public Project that shows items from "
                           "other or non-public repositories. Publish the counts only (drop --with-titles).")


def titles_may_be_published(project_public, repo_public, items, full):
    """Titles may go into a published status update only if no reader outside the audience of the data could see them:
    a private Project, or a public Project showing only the items of this (public) repository."""
    if not project_public:
        return True
    return bool(repo_public) and all((i.get("content") or {}).get("repository", full) == full for i in items)


def parse_tasklist(body, host="github.com"):
    """Task-list lines of an issue body -> [{checked, text, ref}] where ref is 'owner/repo#n', '#n' or None.
    Issue URLs are only understood on the repository's own host."""
    out = []
    for line in (body or "").splitlines():
        m = re.match(r"^\s*[-*]\s+\[([ xX])\]\s+(.*\S)\s*$", line)
        if not m:
            continue
        text = m.group(2)
        r = re.search(rf"https://{re.escape(host)}/([\w.-]+)/([\w.-]+)/issues/(\d+)", text)
        ref = f"{r.group(1)}/{r.group(2)}#{r.group(3)}" if r else None
        if not ref:
            r = re.search(r"(?:^|\s)((?:[\w.-]+/[\w.-]+)?#\d+)\b", text)
            ref = r.group(1) if r else None
        out.append({"checked": m.group(1) != " ", "text": text, "ref": ref})
    return out


def rewrite_tasklist(body, text, number):
    """Replace the plain task-list line `text` by a reference to the issue created from it (keeps the checkbox state)."""
    def repl(m):
        return f"{m.group(1)}#{number}" if m.group(2).strip() == text else m.group(0)
    return re.sub(r"^(\s*[-*]\s+\[[ xX]\]\s+)(.*\S)\s*$", repl, body, flags=re.M)


def already_linked(error):
    return "duplicate sub-issues" in error


# ---------------------------------------------------------------- gh helpers
def project_info(po, pn):
    rc, out, err = project.run(["gh", "project", "view", str(pn), "--owner", po, "--format", "json"])
    if rc != 0:
        raise RuntimeError("gh project view failed: " + err[:200])
    return json.loads(out)


def list_fields(po, pn):
    rc, out, err = project.run(["gh", "project", "field-list", str(pn), "--owner", po, "--format", "json", "--limit", "100"])
    if rc != 0:
        raise RuntimeError("gh project field-list failed: " + err[:200])
    return json.loads(out)["fields"]


def list_items(po, pn):
    rc, out, err = project.run(["gh", "project", "item-list", str(pn), "--owner", po, "--format", "json", "--limit", "500"])
    if rc != 0:
        raise RuntimeError("gh project item-list failed: " + err[:200])
    return json.loads(out)["items"]


def list_views(project_id):
    q = "query($i:ID!){node(id:$i){... on ProjectV2{views(first:50){nodes{id name filter layout}}}}}"
    return project.gh_graphql(q, i=project_id)["node"]["views"]["nodes"]


def create_view(info, view):
    name, layout, flt = view[0], view[1], view[2]
    owner = info["owner"]
    base = "orgs" if owner["type"] == "Organization" else "users"
    rc, _, err = project.run(["gh", "api", "-X", "POST", f"/{base}/{owner['login']}/projectsV2/{info['number']}/views",
                              "-f", f"name={name}", "-f", f"layout={layout}", "-f", f"filter={flt}"])
    return rc == 0, err[:200]


def rename_view(view_id, name):
    q = "mutation($v:ID!,$n:String!){updateProjectV2View(input:{viewId:$v,name:$n}){projectV2View{name}}}"
    try:
        project.gh_graphql(q, v=view_id, n=name)
        return True, ""
    except RuntimeError as e:
        return False, str(e)


def fetch_updated(full):
    """{number: last update} of the open issues and pull requests of the repository."""
    out = {}
    for kind in ("issue", "pr"):
        rc, text, err = project.run(["gh", kind, "list", "--repo", full, "--state", "open", "--limit", "500",
                                     "--json", "number,updatedAt"])
        if rc != 0:
            raise RuntimeError(f"gh {kind} list failed: " + err[:200])
        out.update({x["number"]: parse_time(x["updatedAt"]) for x in json.loads(text)})
    return out


def epic_progress(items, owner, name):
    """{epic number: (completed, total)} from the sub-issue summaries of the epic items of this repository."""
    out = {}
    for it in items:
        c = it.get("content") or {}
        if "epic" in [l.lower() for l in it.get("labels") or []] and c.get("repository") == f"{owner}/{name}":
            summary = project.fetch_tree(owner, name, c["number"])["summary"]
            out[c["number"]] = (summary.get("completed", 0), summary.get("total", 0))
    return out


def find_item(items, ref):
    url_part = f"/{ref.owner}/{ref.name}/"
    for it in items:
        c = it.get("content") or {}
        if c.get("number") == ref.number and url_part in (c.get("url") or ""):
            return it
    return None


def edit_item(info, item_id, field, value):
    """Set a field value; returns (ok, message). Field is a dict from field-list."""
    base = ["gh", "project", "item-edit", "--id", item_id, "--project-id", info["id"], "--field-id", field["id"]]
    ftype = field["type"]
    if ftype == "ProjectV2SingleSelectField":
        opt = next((o for o in field.get("options", []) if o["name"].lower() == value.lower()), None)
        if not opt:
            return False, "unknown option; choose one of: " + ", ".join(o["name"] for o in field.get("options", []))
        args = base + ["--single-select-option-id", opt["id"]]
    elif ftype == "ProjectV2IterationField":
        it = next((i for i in (field.get("configuration") or {}).get("iterations", []) if i["title"].lower() == value.lower()), None)
        if not it:
            return False, "unknown iteration"
        args = base + ["--iteration-id", it["id"]]
    elif field["name"].lower() == "estimate" or ftype == "ProjectV2NumberField":
        args = base + ["--number", value]
    elif "date" in field["name"].lower():
        args = base + ["--date", value]
    else:
        args = base + ["--text", value]
    rc, _, err = project.run(args)
    return rc == 0, err[:200]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="board.py", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("fields", "setup", "views", "report", "set", "draft", "drafts", "convert", "tasklist"):
        s = sub.add_parser(name)
        s.add_argument("--repo")
        if name in ("setup", "views", "tasklist"):
            s.add_argument("--apply", action="store_true")
        if name == "report":
            s.add_argument("--post", action="store_true")
            s.add_argument("--status", choices=["INACTIVE", "ON_TRACK", "AT_RISK", "OFF_TRACK", "COMPLETE"])
            s.add_argument("--with-titles", action="store_true", help="include epic titles in the published update or page")
            s.add_argument("--html", metavar="FILE", help="also write a static HTML page (counts only unless --with-titles)")
        if name == "set":
            s.add_argument("ref")
            s.add_argument("--field", required=True)
            s.add_argument("--value", required=True)
            s.add_argument("--pr", action="store_true")
        if name == "draft":
            s.add_argument("title")
            s.add_argument("--body", default="")
        if name == "convert":
            s.add_argument("item_id")
        if name == "tasklist":
            s.add_argument("epic")
            s.add_argument("--create", action="store_true")
            s.add_argument("--allow-cross-repo", action="store_true", help="also follow references to other repositories")
    a = ap.parse_args(argv)
    readonly = a.cmd in ("fields", "report", "drafts") and not getattr(a, "post", False)
    try:
        owner, name, full, kind = project.bootstrap(a.repo, writes=not readonly)
        po, pn, _ = project.project_for(owner, name, full, kind)
        info = project_info(po, pn)
        if a.cmd == "fields":
            for f in list_fields(po, pn):
                opts = ", ".join(o["name"] for o in f.get("options", []))
                print(f"{f['name']} ({f['type'].replace('ProjectV2', '').replace('Field', '') or 'Field'})" + (f": {opts}" if opts else ""))
            return 0
        if a.cmd == "setup":
            todo = plan_fields([f["name"] for f in list_fields(po, pn)])
            if not todo:
                print("All standard fields exist.")
                return 0
            fail = 0
            for spec in todo:
                if not a.apply:
                    print(f"would create field {spec['name']} ({spec['type']})")
                    continue
                try:
                    project.gh_graphql_json(*field_mutation(info["id"], spec))
                    print(f"created field {spec['name']}")
                except RuntimeError as e:
                    print(f"field {spec['name']} FAILED {e}")
                    fail += 1
            if not a.apply:
                print("Dry run: re-run with --apply.")
                return 1
            return 2 if fail else 0
        if a.cmd == "views":
            existing = list_views(info["id"])
            fields = [f["name"] for f in list_fields(po, pn)]
            create, skipped = plan_views([v["name"] for v in existing], fields)
            default = next((v for v in existing if v["name"] == "View 1" and not v["filter"]), None)
            fail = 0
            if default and a.apply:
                ok, err = rename_view(default["id"], "All items")
                print(f"renamed 'View 1' -> 'All items': {'ok' if ok else 'FAILED ' + err}")
                fail += not ok
            for v in create:
                if not a.apply:
                    print(f"would create view {v[0]} ({v[1]}, filter: {v[2]})")
                    continue
                ok, err = create_view(info, v)
                print(f"view {v[0]}: {'created' if ok else 'FAILED ' + err}   manual: {v[4]}")
                fail += not ok
            for n, missing in skipped:
                print(f"view {n}: skipped, needs field(s) {', '.join(missing)} (run board.py setup --apply)")
            print(WORKFLOWS_HINT)
            if not a.apply and create:
                print("Dry run: re-run with --apply.")
                return 1
            return 2 if fail else 0
        if a.cmd == "report":
            items = list_items(po, pn)
            m = metrics(items, fetch_updated(full), epic_progress(items, owner, name))
            print("\n".join(render_report(m, f"{po}/{pn}")))
            if a.html:
                if a.with_titles:
                    ensure_titles_publishable(po, pn, kind, items, full)
                Path(a.html).write_text(render_html(m, f"{po}/{pn}", a.status or derive_status(m), a.with_titles), encoding="utf-8")
                print(f"page written: {a.html} (a snapshot: publish it yourself, for example with GitHub Pages)")
            if a.post:
                status = a.status or derive_status(m)
                if a.with_titles:
                    ensure_titles_publishable(po, pn, kind, items, full)
                lines = render_report(m, f"{po}/{pn}", titles=a.with_titles)
                q = ("mutation($i:CreateProjectV2StatusUpdateInput!){createProjectV2StatusUpdate(input:$i){statusUpdate{id}}}")
                project.gh_graphql_json(q, {"i": {"projectId": info["id"], "status": status, "body": "\n".join(lines)}})
                print(f"status update posted: {status}")
            return 0
        if a.cmd == "set":
            ref = project.parse_ref(a.ref, owner, name)
            item = find_item(list_items(po, pn), ref)
            if not item:
                raise RuntimeError(f"{ref} is not in the Project (run project.py attach {'--pr ' if a.pr else ''}first)")
            field = next((f for f in list_fields(po, pn) if f["name"].lower() == a.field.lower()), None)
            if not field:
                raise RuntimeError(f"unknown field {a.field!r} (see board.py fields)")
            ok, err = edit_item(info, item["id"], field, a.value)
            print(f"{ref} {field['name']} = {a.value}: {'ok' if ok else 'FAILED ' + err}")
            return 0 if ok else 2
        if a.cmd == "draft":
            rc, out, err = project.run(["gh", "project", "item-create", str(pn), "--owner", po, "--title", a.title,
                                        "--body", a.body, "--format", "json"])
            if rc != 0:
                raise RuntimeError("gh project item-create failed: " + err[:200])
            print(f"draft item created: {json.loads(out).get('id')}")
            return 0
        if a.cmd == "drafts":
            drafts = [i for i in list_items(po, pn) if (i.get("content") or {}).get("type") == "DraftIssue"]
            for d in drafts:
                print(f"{d['id']} {project.safe_title(d.get('title', ''))}")
            print(f"{len(drafts)} draft item(s)")
            return 0
        if a.cmd == "convert":
            rc, out, err = project.run(["gh", "repo", "view", full, "--json", "id", "--jq", ".id"])
            if rc != 0:
                raise RuntimeError("cannot read the repository id: " + err[:200])
            q = ("mutation($i:ID!,$r:ID!){convertProjectV2DraftIssueItemToIssue(input:{itemId:$i,repositoryId:$r})"
                 "{item{content{... on Issue{number url}}}}}")
            data = project.gh_graphql(q, i=a.item_id, r=out)
            print("converted: " + str(data["convertProjectV2DraftIssueItemToIssue"]["item"]["content"].get("url")))
            return 0
        if a.cmd == "tasklist":
            epic = project.parse_ref(a.epic, owner, name)
            rc, out, err = project.run(["gh", "issue", "view", str(epic.number), "--repo", f"{epic.owner}/{epic.name}",
                                        "--json", "body", "--jq", ".body"])
            if rc != 0:
                raise RuntimeError("cannot read the epic: " + err[:200])
            todo = parse_tasklist(out, os.environ.get("GH_HOST", "github.com"))
            if not todo:
                print("No task list in the epic body.")
                return 0
            fail = 0
            for t in todo:
                tag = project.safe_title(t["text"])
                if t["ref"]:
                    child = project.parse_ref(t["ref"], epic.owner, epic.name)
                    if (child.owner, child.name) != (epic.owner, epic.name) and not a.allow_cross_repo:
                        print(f"skipped {child}: another repository (list text is untrusted; use --allow-cross-repo after checking it)")
                        continue
                    if not a.apply:
                        print(f"would link {child} as sub-issue of {epic}  {tag}")
                        continue
                    ok, err = project.set_parent(epic, child)
                    if not ok and already_linked(err):
                        print(f"{child} already a sub-issue of {epic}")
                        continue
                    print(f"{child} sub-issue of {epic}: {'ok' if ok else 'FAILED ' + err}")
                    fail += not ok
                elif a.create:
                    if not a.apply:
                        print(f"would create an issue from {tag} and link it to {epic}")
                        continue
                    rc, url, err = project.run(["gh", "issue", "create", "--repo", f"{epic.owner}/{epic.name}",
                                                "--title", t["text"][:200], "--body", str(epic)])
                    if rc != 0:
                        print(f"create {tag} FAILED {err[:200]}")
                        fail += 1
                        continue
                    child = project.Ref((epic.owner, epic.name, int(url.rstrip("/").rsplit("/", 1)[1])))
                    ok, err = project.set_parent(epic, child)
                    ok2, err2 = project.add_to_project(po, pn, child)
                    print(f"{child} created, sub-issue: {'ok' if ok else 'FAILED ' + err}, project: {'ok' if ok2 else 'FAILED ' + err2}"
                          + ("; it is checked in the list: close it yourself if the work is done" if t["checked"] else ""))
                    fail += (not ok) + (not ok2)
                    new_body = rewrite_tasklist(out, t["text"], child.number)  # makes a re-run idempotent
                    rc, _, err = project.run(["gh", "issue", "edit", str(epic.number), "--repo", f"{epic.owner}/{epic.name}",
                                              "--body-file", "-"], input_text=new_body)
                    if rc != 0:
                        print(f"epic body not updated ({err[:100]}): a re-run would create {tag} again")
                        fail += 1
                    out = new_body
                else:
                    print(f"skipped plain item {tag} (use --create to make an issue from it)")
            if not a.apply:
                print("Dry run: re-run with --apply.")
                return 1
            return 2 if fail else 0
    except project.Stop as e:
        print(e.msg, file=sys.stderr)
        return e.code
    except project.Undetermined as e:
        print(str(e), file=sys.stderr)
        return 3
    except RuntimeError as e:
        print(str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
