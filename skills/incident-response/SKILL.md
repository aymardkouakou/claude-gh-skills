---
name: incident-response
description: Handle a security or operations incident - P1-P4 qualification, containment, evidence preservation, register, notification decision (drafts only), recovery, blameless post-mortem. Use for "incident", "fuite", "fraude", "panne en production", "réclamation grave". Technical follow-up of the cause then goes through issue-lifecycle.
disable-model-invocation: true
---

# Incident response

Containment actions (disable a route, block a user, revoke sessions, stop a service) change a shared system: propose them with the **exact command** and wait for the user's approval. Notifications to the regulator, customers or partners are **never sent by you**: drafts only. Read the project's incident procedure first (CLAUDE.md, `procedures/`, `docs/`); it overrides this outline.

## Flow
1. **Qualify**: severity P1 (production or money affected, leak) to P4 (minor nuisance), services and operations touched, number of users, personal or payment data involved.
2. **Record** within 30 min: detection time (UTC), nature, severity, impact, services. No register in the project: dated file `incidents/<YYYY-MM-DD>-<id>.md`, and say so.
3. **Preserve evidence before any remediation**: logs (`docker logs --since`, `kubectl logs --since`), application audit export, configuration state. Folder `~/incidents/<id>` with mode 700, hashes with `shasum -a 256`. On macOS `date -v-24H` replaces `date -d`.
4. **Contain**: propose the narrowest measure (one route, one account), export the configuration before changing it, plan the rollback. Journal every action (type Action).
5. **Decide on notification** within 4 h: legal and contractual duties of the project (regulator, data-protection authority, customers, payment partners). Deadlines come from the project's procedure: if absent, say so and do not invent them.
6. **Eradicate and recover**, then verify (service health, reconciliation checks for money).
7. **Blameless post-mortem**: timeline, root cause, actions with owner and due date, follow-up issues (`issue-lifecycle`), emergency change record with retroactive review within 48 h (`dev-traceability`).

## Rules
- No personal data or secret in drafts and registers: technical identifiers only.
- A leaked secret means immediate rotation (`secrets-hygiene`), not only deletion.
- Report gaps (emergency contacts "to be defined", no notification template) instead of filling them in.
- Resolve the repository with `${CLAUDE_SKILL_DIR}/../repo-context/ctx.py repo` before opening tracking issues.

## End of task
Log the run: `${CLAUDE_SKILL_DIR}/../skill-learning/learn.py log incident-response ok|partial|failed [--note …]`.
