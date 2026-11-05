---
name: dev-traceability
description: Guarantee traceable development under a controlled lifecycle aligned with certifiable standards (ISO/IEC 27001:2022, ISO 9001, ISO/IEC/IEEE 12207, ITIL 4 change enablement, SOC 2 CC8) - requirement → issue → commit → PR → review → tests → deployment → verification, change register, traceability matrix, segregation of duties, audit evidence. Use for any feature, fix, configuration change, release or production deployment, or to "prepare the audit", "trace this change", "registre des changements", "matrice de traçabilité". Not for an isolated code question with nothing to deliver.
---

# Traceable development

Goal: every delivered change can be explained and proven, from requirement to production, without asking anyone. This skill produces the **evidence** and applies the **controls** expected by the standards in `references/standards-mapping.md`. It certifies nothing: certification belongs to an accredited body. State this limit in any report meant for an auditor.

The project's own branch and PR flow (CLAUDE.md, CONTRIBUTING, repo-context `notes`) is authoritative; this skill adds to it. Never commit or push without the user's request.

## Context
`REPO=$(${CLAUDE_SKILL_DIR}/../repo-context/ctx.py repo)`; use `--repo "$REPO"` for every `gh` call. Ask the user before any write if the repository is not confirmed by `gh`. Adapt controls to the repository profile (`ctx.py resolve` → `kind`: personal or organization, public/private/internal, fork, archived): for example a solo personal account cannot satisfy "reviewer different from author" and needs a documented exception, and a public repository gets stricter masking. Save verified workflow facts with `ctx.py note` (for example "promotion flow: develop → sandbox → main").

Language: PR descriptions, change records and reports published in the repository follow `ctx.py lang` (if unset, stop and ask the user to confirm the language before writing anything; never default); commit messages follow `ctx.py lang --commit` (default English). The skill files stay in English.

## The traceability chain (a missing link is a finding)

| # | Link | Expected evidence | Where |
|---|---|---|---|
| 1 | Requirement or need | stable identifier (`REQ-…`, `TB-…`, `SEC-…`) | specification, issue |
| 2 | Issue | purpose, acceptance criteria, risk, priority; **in the repository Project and under an epic** | GitHub Issues + Project |
| 3 | Branch and commits | Conventional Commits in English, `Refs #<n>` | git |
| 4 | Pull request | template filled: changes, risks, tests, rollback | GitHub PR |
| 5 | Review | at least one reviewer **different from the author**; security review in sensitive areas | GitHub PR |
| 6 | Tests | targeted results + CI run link; a test that failed before and passes after | CI |
| 7 | Change (deployment) | approved change record, version, environment, date | `docs/traceability/change-register.md` |
| 8 | Verification | scenario replayed in real conditions, result pasted | issue or PR |
| 9 | Closure | issue closed with summary and links | GitHub Issues |

## Flow

### When work starts
1. Identify the requirement and the issue; otherwise propose opening one (`issue-lifecycle`, `references/issue-template.md`). No change without an issue, except an emergency fix (below). Every issue is attached to the Project and an epic (`${CLAUDE_SKILL_DIR}/../issue-lifecycle/project.py attach <n> --epic <e>`); audit with `project.py orphans`, which must report nothing.
2. Check the project is initialised (`docs/traceability/` exists, PR template present). Otherwise offer `references/project-init.md`.
3. Classify the change: **standard** (low risk, repeatable, pre-approved), **normal** (review + approval), **major** (security, money, data, schema, authentication: second approver and written rollback plan).

### During development
- TDD, or at least one targeted test per changed behaviour; run only the relevant tests.
- Atomic commits, English message, `Refs #<n>`. Check: `${CLAUDE_SKILL_DIR}/check-refs.sh <base>..<head>` lists commits without an issue reference.
- No secret, token or personal data in the diff, logs or messages.
- A new dependency: tell the user and record it in the PR.

### Before the PR
1. Run the definition of done (`references/definition-of-done.md`).
2. Independent review: the `reviewer` agent (bugs, security, performance, edge cases) and, in sensitive areas, `/security-review`. Record each finding as fixed or dismissed with the reason.
3. Update the traceability matrix (`docs/traceability/RTM.md`): requirement ↔ issue ↔ PR ↔ test.

### At change time (production or any shared environment)
1. Fill an entry in `docs/traceability/change-register.md` (`references/change-register.md`): type, risk, impact, rollback plan, approver, version, evidence.
2. **Segregation of duties**: the approver is not the author; major change or production: two people. The agent prepares, a human approves. Never approve or merge on the user's behalf.
3. Deploy through the project's flow (dry-run first), then verify and record the verdict.
4. Tag the release (tag, release notes) and link record, PR and issue.

### Emergency change
Allowed only for an incident in progress (see `incident-response`). Record opened immediately, verbal approval logged, **retroactive review within 48 h**, follow-up issue mandatory, root cause documented.

## Automated controls to propose (defence in depth)
Text is not enough: propose enforcing by tooling (see `references/project-init.md`) branch protection (required review, required CI checks, no direct push, no force-push), the PR template, a CI check for `Refs #`, and a local hook that rejects secrets.

## Compliance report (on request or before an audit)
Table per control: control, target standard, result (compliant / gap / not verified), evidence (link, `path:line`), action. Distinguish "verified now" from "declared". Steering indicators (DORA): lead time, deployment frequency, change failure rate, time to restore.

## Never
Skip links 2 to 6 outside emergencies; self-approve; fabricate or backdate evidence; present a "documented" control as "applied"; put sensitive data in evidence.

## End of task
Log the run: `${CLAUDE_SKILL_DIR}/../skill-learning/learn.py log dev-traceability ok|partial|failed [--note …] [--correction …]`.
