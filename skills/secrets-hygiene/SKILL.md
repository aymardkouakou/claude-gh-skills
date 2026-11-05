---
name: secrets-hygiene
description: Audit, generate, rotate and roll back a project's technical secrets and accounts (database passwords, API keys, tokens, webhook secrets) without ever reading or displaying a value. Use for "rotation des secrets", "mot de passe par défaut", "secret exposé", "ajoute un compte au registre", "rollback des secrets".
disable-model-invocation: true
---

# Accounts and secrets

## Absolute rules
- **No value is read, displayed or copied.** Never open `*.env`, `secrets.env*`, services' `.env*`, nor display a Secret (`kubectl get secret -o yaml`, `docker inspect`, `docker compose config` expose them). Tool output must contain only names, states, lengths and dates.
- The user enters values in the vault (GitHub Environments, secret manager): tell them the secret **name** and where to enter it, never ask for the value. If a value is pasted into the conversation, do not reuse it and advise changing it.
- Rotation on a shared system or production: prior confirmation, prior backup (`backup-restore`), change record (`dev-traceability`).
- Exposed secret (commit, log, issue, screenshot): treat as compromised, rotate, then purge; deleting is not enough.

## Flow
1. Use the project's tooling if it exists (CLAUDE.md, `scripts/`, `./<cli> secrets …`). Otherwise keep an inventory `accounts.md` **without values** (id, service, account, variable, origin, rotation period, last rotation).
2. **Audit**: states `OK / DEFAULT / WEAK / MISSING / EXTERNAL / UNTRACKED`; only OK and EXTERNAL are acceptable.
3. **Generate** with `--dry-run` first, then for real. Enough length and entropy, never a default value.
4. **Apply**: the value changes in the vault **and** in the service (databases keep the old password in their volumes: `ALTER USER`, admin API). A secret shared between clients is rotated together.
5. **Verify** service health, then regenerate the inventory.
6. **Rollback**: keep the previous version until verification.
7. **Scan before any PR**: look for hard-coded credentials in tracked files; file names containing `secret`, `password`, `credentials`, `*.key`, `*.pem` are often ignored by `.gitignore` (`git check-ignore -v`).

## Pitfalls
- Rotating a session key or a webhook secret invalidates sessions or requires warning the third party (Wave, operators).
- Concurrent rotation lock: remove it only after checking that no rotation is running.
- Production: refuse the deployment while a secret is default or weak.

## End of task
Log the run: `${CLAUDE_SKILL_DIR}/../skill-learning/learn.py log secrets-hygiene ok|partial|failed [--note …]`.
