---
name: security-audit
description: Application security audit before a release or as a periodic review - route authentication and authorization, default secrets, exposed ports, webhook signatures, sensitive-data access, logging, input validation, dependencies, monitoring. Use for "audit sécurité", "revue d'accès", "avant la prod". Read-only; GitHub repository settings belong to repo-hardening, an exposed secret to secrets-hygiene, an ongoing incident to incident-response.
---

# Security audit

Read-only by default. No active test on a shared environment without approval. Never display a secret value: cite `file:line` only. Read the project's security procedures first (CLAUDE.md, `procedures/`, `docs/`); "known findings" from an earlier audit must be **re-verified in the code** before being asserted.

## Checks
1. **Authentication and authorization**: list every route with its auth dependency; access control enforced **server-side** on each request (a user never reads another user's data, even by editing the request); roles and least privilege; progressive lockout after failures; error messages that do not reveal whether an account exists; no OTP or secret returned in a response.
2. **Secrets**: default values in `.env.example`, scripts, compose files, inventory CSVs; mandatory variables (`${VAR:?}`); no secret in the repository or logs.
3. **Network exposure**: published ports without `127.0.0.1` (gateway admin, databases, monitoring, object storage), firewall, HTTPS/HSTS, CORS.
4. **Webhooks and callbacks**: signature verified on every call, constant-time comparison, replay protection with timestamp, idempotency, logging without sensitive data.
5. **Sensitive data** (identity, phone, payment): reads and downloads logged, ownership checks, short-lived presigned URLs, masking in exports and logs.
6. **Input validation**: server-side, parameterised queries only, rate limiting, payload size limits.
7. **Logging**: audit of sensitive actions (who, what, when, before/after), integrity chain, no PII or secret in logs.
8. **Dependencies and CI**: vulnerability audit, scans blocking or informative (say which), up-to-date images, security updates.
9. **Monitoring**: real alerts (rules and recipient), business metrics, backups whose restoration has been tested.
10. **Money** (only if the project handles it): integer amounts, idempotency, atomic debit/credit, reversal instead of edit.

Commands for each check: `${CLAUDE_SKILL_DIR}/references/checklist.md`. Hard-coded credentials: `${CLAUDE_SKILL_DIR}/../secrets-hygiene/scan_secrets.py` (never prints values).

## Report
Table: check, result (**compliant / gap / not verified**), evidence (`path:line`), severity (critical/high/medium), action. Distinguish "verified now" from "taken from a document". Line numbers drift: re-read the code before asserting. Gaps are tracked (see Tracking) and, before a release, critical ones block the change record (`change-management`). Repository settings (branch protection, secret scanning, workflow permissions): `repo-hardening`.

## Never
Silent fixes, active tests without approval, secrets in the output, "compliant" for something only documented.

## Tracking
Every gap becomes an issue, critical first (`issue-lifecycle`), attached to the Project and a security epic (`project-tracking`, Kind = Security). The issue states the check, `path:line` evidence and the action, never a secret value or exploit detail. Later commits carry `Refs #<n>`.

## End of task
Log the run: `${CLAUDE_SKILL_DIR}/../skill-learning/learn.py log security-audit ok|partial|failed [--note …]`.
