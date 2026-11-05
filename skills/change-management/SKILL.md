---
name: change-management
description: Control a change delivered to a shared or production environment - change record and register, risk class, approval with segregation of duties, deployment and verification, release tagging, emergency change with retroactive review. Use for "déploiement en production", "mise en prod", "registre des changements", "change d'urgence", "approuve le changement", "release". Pair with dev-traceability for the evidence chain up to the merged change. Not for an incident in progress (use incident-response first).
disable-model-invocation: true
---

# Change management

Goal: every change that reaches a shared environment has a record, an approver who is not its author, a rollback plan and an observed verdict. This skill certifies nothing; it produces evidence (`dev-traceability` has the mapping to ISO/IEC 27001, ISO 9001, ITIL 4, SOC 2).

The project's own deployment flow (CLAUDE.md, CONTRIBUTING, repo-context `notes`) is authoritative. Never commit, push, deploy, approve or merge on the user's behalf.

## Context
```bash
REPO=$(${CLAUDE_SKILL_DIR}/../repo-context/ctx.py repo)
```
Record language: `ctx.py lang`; unset means stop and ask the user to confirm it. A solo personal account cannot satisfy "approver ≠ author": document the exception instead of faking an approver.

## 1. Classify
**standard** (low risk, repeatable, pre-approved), **normal** (review + approval), **major** (security, money, data, schema, authentication: second approver and written rollback plan).

## 2. Record
Add a line to `docs/traceability/change-register.md` and fill the detailed record (`references/change-register.md`): type, risk, impact, rollback plan, approver, version, evidence. Identifiers are sequential per year; a gap is reported.

## 3. Approve
The approver is not the author; major or production: two people. You prepare, a human approves.

## 4. Deploy and verify
1. Dry run first, then deploy through the project's flow.
2. Verify in real conditions; the verdict is what is observed, not the command's exit status (check that the component reloaded its code: log, image digest).
3. Tag the release (tag, release notes) and link record, PR and issue.

## Emergency change
Only for an incident in progress (`incident-response`). Record opened immediately, verbal approval logged, **retroactive review within 48 h**, follow-up issue mandatory, root cause documented.

## Never
Self-approve; backdate or fabricate a record; put personal data or a secret in a record; deploy a major change without a rollback plan.

## End of task
Log the run: `${CLAUDE_SKILL_DIR}/../skill-learning/learn.py log change-management ok|partial|failed [--note …]`.
