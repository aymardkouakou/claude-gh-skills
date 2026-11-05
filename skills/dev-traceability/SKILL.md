---
name: dev-traceability
description: Guarantee a traceable path from requirement to merged change - requirement → issue → commit → PR → review → tests, traceability matrix (RTM), definition of done, compliance report aligned with ISO/IEC 27001:2022, ISO 9001, ISO/IEC/IEEE 12207, ITIL 4 and SOC 2. Use for any feature or fix, or to "prépare l'audit", "trace this change", "matrice de traçabilité". Deployment and change records belong to change-management. Not for an isolated code question with nothing to deliver.
---

# Traceable development

Goal: every change can be explained and proven, from requirement to merge, without asking anyone. This skill produces **evidence** and applies **controls** mapped in `references/standards-mapping.md`. It certifies nothing: certification belongs to an accredited body; say so in any report meant for an auditor.

The project's own branch and PR flow (CLAUDE.md, CONTRIBUTING, repo-context `notes`) is authoritative. Never commit or push without the user's request.

## Context
```bash
REPO=$(${CLAUDE_SKILL_DIR}/../repo-context/ctx.py repo)   # --repo "$REPO" on every gh call
```
Adapt controls to `ctx.py resolve` → `kind`: a solo personal account cannot satisfy "reviewer different from author" and needs a documented exception; a public repository gets stricter masking. Published text follows `ctx.py lang` (unset: stop and ask the user to confirm it, never default); commit messages follow `ctx.py lang --commit` (default English).

## The chain (a missing link is a finding)
| # | Link | Expected evidence |
|---|---|---|
| 1 | Requirement | stable identifier (`REQ-…`, `SEC-…`) |
| 2 | Issue | purpose, acceptance criteria, risk, priority; in the Project and under an epic (`project-tracking`) |
| 3 | Branch and commits | Conventional Commits in English, `Refs #<n>` |
| 4 | Pull request | template filled: changes, risks, tests, rollback |
| 5 | Review | a reviewer **different from the author**; security review in sensitive areas |
| 6 | Tests | targeted results + CI run link; a test that failed before and passes after |
| 7 to 9 | Change, verification, closure | `change-management` and `issue-lifecycle` |

## Flow
**Start.** Identify the requirement and the issue; none: propose `issue-lifecycle`. No change without an issue except an emergency fix (`change-management`). Check `docs/traceability/` and the PR template exist, else offer `references/project-init.md`.

**During.** TDD or at least one targeted test per changed behaviour. Atomic commits with `Refs #<n>`; `${CLAUDE_SKILL_DIR}/check-refs.sh <base>..<head>` lists commits without a reference. No secret or personal data. Tell the user about any new dependency and record it in the PR.

**Before the PR.** Run `references/definition-of-done.md`; independent review with the `reviewer` agent (and `/security-review` in sensitive areas), each finding fixed or dismissed with the reason; update `docs/traceability/RTM.md` (requirement ↔ issue ↔ PR ↔ test).

**Audit.** Control table and indicators: `references/compliance-report.md`.

Platform controls (branch protection, secret scanning, CODEOWNERS, templates): `repo-hardening`.

## Never
Skip links 2 to 6 outside emergencies; self-approve; fabricate or backdate evidence; present a "documented" control as "applied"; put sensitive data in evidence.

## End of task
Log the run: `${CLAUDE_SKILL_DIR}/../skill-learning/learn.py log dev-traceability ok|partial|failed [--note …] [--correction …]`.
