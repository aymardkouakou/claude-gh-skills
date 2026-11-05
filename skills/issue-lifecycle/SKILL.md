---
name: issue-lifecycle
description: Full lifecycle of an error in GitHub Issues - record it, investigate with a timestamped journal, document the root cause, fix through the project's PR flow, verify, close. Use when an error takes more than one attempt to understand, touches CI, deployment, backups, security, authentication or payments, or may come back ("erreur", "bug récurrent", "ouvre une issue"). Not for a typo fixed within a minute, nor for a declared security incident (use incident-response first).
---

# Error → Issue → Investigation → Fix → Closure

The issue is the memory of the error: someone reading it a year later must understand it without asking anyone. The **body** is the living summary; the **comments** are the full journal, written when things happen, never reconstructed.

## Context first
```bash
REPO=$(~/.claude/skills/repo-context/ctx.py repo)   # then pass --repo "$REPO" to every gh command
```
Read `kind` from `ctx.py resolve` (personal/organization, public/private/internal, fork, archived) and apply its `rules`; `writable: false` means stop. If `ctx.py resolve` reports `source` other than `gh`, or `authenticated: false`, ask the user before writing anything. Reuse remembered facts (label scheme, workflow) from `notes`.

## Language of what you publish
Issue titles, bodies, journal comments and summaries are written in `$(~/.claude/skills/repo-context/ctx.py lang)` (exit code 3 = not chosen yet: ask the user once, then `ctx.py lang set CODE`). Translate the English template headings; keep error messages, commands and paths verbatim. `journal.sh` localises the entry label itself (`labels.json`).

## When to open
- **Yes**: more than one attempt to understand or fix; touches CI/deployment, backups, security, auth, payments; may recur; cause unclear.
- **No**: tool slip fixed within a minute, before any commit, with no lesson. When in doubt, open.
- **Before opening**: `gh issue list --repo "$REPO" --state all --search "<keywords>"`. Duplicate: comment (recurrence, new evidence) and reopen if closed.

## Safety rules (non-negotiable)
- No secret (password, token, key, `.env` content) and no Secret value: variable names yes, values never.
- No personal data or customer-linked amounts: mask (`a***@domain`). Mask customer IP addresses.
- Pasted logs are redacted and short (useful lines with date and source). Over 40 lines: `<details>` or a link to the run.
- Write the body to a scratch file, never inline on the command line.

## 1. Record
- **Issue repository = repository of the faulty component.** Cause spread over several repositories: one issue per repository plus a short tracking issue that lists them. Unknown cause: open where the error is observed, then `gh issue transfer`.
- Check that labels exist before using them: `~/.claude/skills/repo-context/ctx.py labels`.
```bash
gh issue create --repo "$REPO" --title "<component>: <observable symptom>" \
  --label "type:bug" --label "priority:<high|medium|low>" --body-file <file>
```
**Immediately after creation, the issue joins the Project and an epic (mandatory, never skipped):**
```bash
~/.claude/skills/issue-lifecycle/project.py attach <n> --epic <epic#> --repo "$REPO"   # prints the Project used and its source
```
Issues are driven by the repository's GitHub Project (one per repository, found automatically, always stated to the user). The epic is a parent issue labelled `epic`; members are native sub-issues. No epic fits: propose creating one or ask which to use; never leave the issue silently orphaned. Exit 3 = Project or epic undetermined (ask the user), 4 = token lacks the `project` scope (tell the user to run `gh auth refresh -s project`; never run it yourself). Catch up existing issues: `project.py orphans`, then `project.py backfill [--epic N] --apply` (dry-run by default).

Title = the symptom, not the hypothesis. Priority `high` if login, payments, backups, security or production are affected. Body template: `references/issue-template.md`.

## 2. Resolution journal (mandatory, in real time)
One entry per state change: `~/.claude/skills/issue-lifecycle/journal.sh <issue#> <type> <file> [owner/repo]` (UTC, refused automatically if the text looks like a secret; repository defaults to the active one). Types and rules: `references/journal.md`. Never bypass a refusal: redact.

## 3. Investigate
1. Observe or reproduce without guessing; for wide code searches use the `explorer` agent.
2. One journal entry per significant step, with links at the right commit (`…/blob/<sha>/<path>#L<n>`) and to runs (`gh run view <id>`).
3. Record dead ends too.
4. Root cause = verified fact, not hypothesis; if several causes add up, list all. Update the body (`gh issue edit <n> --body-file …`).

## 4. Fix
- Follow the project's PR flow (CLAUDE.md, CONTRIBUTING, `notes` from repo-context). Commits and PRs mention `Refs #<n>` (or `Refs owner/repo#<n>` across repositories). A PR into a non-default branch does not close the issue.
- A test that failed before and passes after, when possible (targeted tests); otherwise an observable verification described in the issue.
- Journal the action (PR, commits, run, deployed version). Never commit or push without the user's request.

## 5. Verify, then close
1. Verify in real conditions (replay the failing scenario) and paste the result into the issue.
2. Complete Fix, Verification, Prevention (test added, CI guard, runbook, alert, skill or CLAUDE.md update).
3. Retrospective (journal), summary comment, then:
```bash
gh issue comment <n> --repo "$REPO" --body-file <summary>
gh issue close <n> --repo "$REPO" --reason completed      # "not planned" + justification if the risk is accepted
```
4. If the error returns: `gh issue reopen <n>`, resume at step 3, no duplicate.

## Pitfalls
- `.gitignore` rules excluding names containing `secret`, `password`, `credentials`, `*.key`, `*.pem`: a file named that way stays local and breaks CI. Check `git check-ignore -v <file>` and `git diff --cached --stat`.
- Never chain "show checks" and "merge": `if gh pr checks <n> | grep -qi fail; then …; else gh pr merge <n>; fi`.
- Do not filter (`| tail`) the output of a state-changing command before checking its result.
- Destructive commands (`git reset --hard`, `git clean`, selector-based `kubectl delete`): read `git status` or the exact resource list first; prefer `git revert` or `reset --keep`; name resources explicitly.
- After a deployment, check that the component reloaded its code (log, image digest), not only the green output.

## Certifiable traceability
To fit the issue into an auditable chain (requirement → issue → PR → review → change → closure), also apply `dev-traceability` whenever a fix goes to production.

## End of task
One line per issue: number and link, state, Project and epic, cause in one sentence. No open issue without a named next action. Then log the run: `~/.claude/skills/skill-learning/learn.py log issue-lifecycle ok|partial|failed [--note …]`.
