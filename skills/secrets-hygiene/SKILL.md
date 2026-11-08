---
name: secrets-hygiene
description: Audit, generate, rotate and roll back a project's technical secrets and accounts (database passwords, API keys, tokens, webhook secrets) without ever reading or displaying a value. Use for "rotation des secrets", "mot de passe par défaut", "secret exposé", "ajoute un compte au registre", "rollback des secrets". Not for reading or showing a secret value (never done), nor for repository scanning settings (use repo-hardening).
disable-model-invocation: true
---

# Accounts and secrets

## Absolute rules
- **No value is read, displayed or copied.** Never open `*.env`, `secrets.env*`, services' `.env*`, nor display a Secret (`kubectl get secret -o yaml`, `docker inspect`, `docker compose config` expose them). Tool output must contain only names, states, lengths and dates.
- GitHub: list names only (`gh secret list --repo "$REPO"`, `gh variable list`); never `gh secret` with a value on the command line (it lands in shell history) and never display one. Secret scanning and push protection: `repo-hardening`.
- The user enters values in the vault (GitHub Environments, secret manager): tell them the secret **name** and where to enter it, never ask for the value. If a value is pasted into the conversation, do not reuse it and advise changing it.
- Rotation on a shared system or production: prior confirmation, prior backup of what the secret protects, change record (`change-management`).
- Exposed secret (commit, log, issue, screenshot): treat as compromised, rotate, then purge; deleting is not enough.

## Flow
1. Use the project's tooling if it exists (CLAUDE.md, `scripts/`, `./<cli> secrets …`). Otherwise keep an inventory `accounts.md` **without values** (id, service, account, variable, origin, rotation period, last rotation).
2. **Audit**: states `OK / DEFAULT / WEAK / MISSING / EXTERNAL / UNTRACKED`; only OK and EXTERNAL are acceptable.
3. **Generate** with `--dry-run` first, then for real. Enough length and entropy, never a default value.
4. **Apply**: the value changes in the vault **and** in the service (databases keep the old password in their volumes: `ALTER USER`, admin API). A secret shared between clients is rotated together.
5. **Verify** service health, then regenerate the inventory.
6. **Rollback**: keep the previous version until verification.
7. **Scan before any PR**: run `${CLAUDE_SKILL_DIR}/scan_secrets.py` (read-only, prints `path:line: rule`, never a value) for hard-coded credentials in tracked files; inventory template: `${CLAUDE_SKILL_DIR}/references/inventory.md`; file names containing `secret`, `password`, `credentials`, `*.key`, `*.pem` are often ignored by `.gitignore` (`git check-ignore -v`).

## Pitfalls
- Rotating a session key or a webhook secret invalidates sessions or requires warning the third party (payment or API providers, partners).
- Concurrent rotation lock: remove it only after checking that no rotation is running.
- Production: refuse the deployment while a secret is default or weak.

## Tracking
A suspected exposure, rotation or rollback is tracked: one issue per secret (`issue-lifecycle`) attached to the Project (`project-tracking`, Kind = Security). Names, dates and steps only; never a value, even partial. Log each step in the journal and close after verification.

## End of task
Log the run: `${CLAUDE_SKILL_DIR}/../skill-learning/learn.py log secrets-hygiene ok|partial|failed [--note …]`.
