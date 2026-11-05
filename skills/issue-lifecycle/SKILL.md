---
name: issue-lifecycle
description: Full lifecycle of an error in GitHub Issues - record it, keep a timestamped resolution journal, document the root cause, fix through the project's PR flow, verify, close. Use when an error takes more than one attempt to understand, touches CI, deployment, security or authentication, or may come back ("erreur", "bug récurrent", "ouvre une issue", "journal de résolution"). Not for placing issues in a Project or epic (use project-tracking), a typo fixed within a minute, nor a declared security incident (use incident-response first).
---

# Error → Issue → Investigation → Fix → Closure

The issue is the memory of the error: someone reading it a year later must understand it without asking anyone. The **body** is the living summary; the **comments** are the full journal, written when things happen, never reconstructed.

## Context first
```bash
REPO=$(${CLAUDE_SKILL_DIR}/../repo-context/ctx.py repo)   # then pass --repo "$REPO" to every gh command
```
Read `kind` from `ctx.py resolve` and apply its `rules`; `writable: false` means stop. Ask the user before writing if `source` is not `gh` or `authenticated` is false. Reuse remembered facts (label scheme, workflow) from `notes`.

## Two choices belong to the user
- **Language** of what you publish: run `${CLAUDE_SKILL_DIR}/../repo-context/ctx.py lang` before writing any issue, comment or PR text. Exit 3 (unset) is a hard stop: ask the user to confirm it (propose the repository's current language), save it with `ctx.py lang set CODE`, then write. Never infer it; `journal.sh` refuses to run while it is unset.
- **Project**: resolved by `project-tracking` (`project.py resolve`); exit 3 means ask the user to confirm the candidate or name another.

## When to open
- **Yes**: more than one attempt to understand or fix; touches CI/deployment, security, auth, payments or backups; may recur; cause unclear.
- **No**: tool slip fixed within a minute, before any commit, with no lesson. When in doubt, open.
- **Before opening**: `gh issue list --repo "$REPO" --state all --search "<keywords>"`. Duplicate: comment (recurrence, new evidence) and reopen if closed.

## Safety rules (non-negotiable)
- No secret (password, token, key, `.env` content): variable names yes, values never.
- No personal data or customer-linked amounts: mask (`a***@domain`), mask customer IP addresses.
- Pasted logs are redacted and short; over 40 lines use `<details>` or a link to the run.
- Write the body to a scratch file, never inline on the command line.

## 1. Record
- **Issue repository = repository of the faulty component.** Cause spread over several repositories: one issue per repository plus a short tracking issue. Unknown cause: open where it is observed, then `gh issue transfer`.
- Labels must exist: `${CLAUDE_SKILL_DIR}/../repo-context/ctx.py labels`.
```bash
gh issue create --repo "$REPO" --title "<component>: <observable symptom>" \
  --label "type:bug" --label "priority:<high|medium|low>" --body-file <file>
${CLAUDE_SKILL_DIR}/../project-tracking/project.py attach <n> --epic <epic#> --repo "$REPO"   # mandatory, never skipped
```
Title = the symptom, not the hypothesis. Priority `high` if login, payments, backups, security or production are affected. Body template: `references/issue-template.md`. The attach step puts the issue in the Project and under an epic; no epic fits: ask the user (see `project-tracking`).

## 2. Resolution journal (mandatory, in real time)
`${CLAUDE_SKILL_DIR}/journal.sh <issue#> <type> <file> [owner/repo]`: UTC, refused if the text looks like a secret. Types and rules: `references/journal.md`. Never bypass a refusal: redact.

## 3. Investigate
Observe or reproduce without guessing (use the `explorer` agent for wide searches); one journal entry per significant step with links at the right commit and run; record dead ends; the root cause is a verified fact. Update the body with `gh issue edit <n> --body-file …`.

## 4. Fix
Follow the project's PR flow (CLAUDE.md, CONTRIBUTING, `notes`). Commits and PRs mention `Refs #<n>`. A test that failed before and passes after, or an observable verification described in the issue. Journal the action. Never commit or push without the user's request.

## 5. Verify, then close
1. Verify in real conditions (replay the failing scenario) and paste the result.
2. Complete Fix, Verification, Prevention (test, CI guard, runbook, alert, skill or CLAUDE.md update); retrospective in the journal; summary comment.
3. `gh issue close <n> --repo "$REPO" --reason completed` (or `"not planned"` with a justification when the risk is accepted).
4. If the error returns: `gh issue reopen <n>`, resume at step 3, no duplicate.

Pitfalls (ignored files, chained checks and merges, destructive commands): `references/pitfalls.md`. A fix that reaches production also follows `change-management` and `dev-traceability`.

## End of task
One line per issue: number and link, state, Project and epic, cause in one sentence. No open issue without a named next action. Log the run: `${CLAUDE_SKILL_DIR}/../skill-learning/learn.py log issue-lifecycle ok|partial|failed [--note …]`.
