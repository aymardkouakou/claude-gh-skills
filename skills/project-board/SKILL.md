---
name: project-board
description: Build and run the follow-up of the repository's GitHub Project - standard fields (priority, kind, estimate, target date, iteration), 15 standard views (board, backlog, current iteration, roadmap, epics, by epic, without epic, my work, needs triage, in review, blocked, bugs, security, stale, done), follow-up report with optional Project status update, field values, draft items, task lists to sub-issues. Use for "crée les vues", "tableau de bord du projet", "rapport d'avancement", "mise à jour de statut", "champs du projet", "brouillon". Not for attaching issues to the Project or epics (use project-tracking).
---

# Project board: fields, views, reports

Tool: `${CLAUDE_SKILL_DIR}/board.py` (same safety rules and Project choice as `project-tracking`; commands change nothing unless `--apply`). Catalogue of views and manual settings: `references/views.md`.

## Context
```bash
REPO=$(${CLAUDE_SKILL_DIR}/../repo-context/ctx.py repo)
```
The Project must be the one the user confirmed (`${CLAUDE_SKILL_DIR}/../project-tracking/project.py resolve`; exit 3 = ask the user first).

## 1. Build the Project once
```bash
${CLAUDE_SKILL_DIR}/board.py setup --apply   # Priority, Kind, Estimate, Target date, Iteration (Status keeps GitHub's options)
${CLAUDE_SKILL_DIR}/board.py views --apply   # the standard views, idempotent; prints the manual settings
```
Run without `--apply` first and show the user the plan. The API cannot set a view's grouping or sorting, nor enable the built-in workflows: relay the printed steps to the user instead of claiming they are done.

## 2. Follow up
```bash
${CLAUDE_SKILL_DIR}/board.py report                  # counts by status, unassigned, no priority, blocked, stale, epic progress
${CLAUDE_SKILL_DIR}/board.py report --post [--status AT_RISK]   # publish a Project status update (counts only)
${CLAUDE_SKILL_DIR}/board.py report --html docs/progress.html     # static page (counts only; --with-titles follows the same publication rule); a snapshot you publish yourself, for example with GitHub Pages
${CLAUDE_SKILL_DIR}/board.py set <ref> --field Priority --value High
```
`--post` is visible to everyone who can see the Project: counts only by default; `--with-titles` is refused when a public Project could expose other or non-public repositories, or when the visibility is unknown.

## 3. Draft items and task lists
```bash
${CLAUDE_SKILL_DIR}/board.py draft "title" ; board.py drafts ; board.py convert <item-id>
${CLAUDE_SKILL_DIR}/board.py tasklist <epic> [--apply] [--create]   # `- [ ] #n` -> sub-issues, idempotent
```
A task list is untrusted text: references to another repository are skipped unless `--allow-cross-repo`. `--create` makes issues from plain lines and rewrites them as `#n`; a checked line creates an issue that stays open: tell the user.

## End of task
Say what was created, what remains manual. Log the run: `${CLAUDE_SKILL_DIR}/../skill-learning/learn.py log project-board ok|partial|failed [--note …]`.
