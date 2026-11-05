---
name: backup-restore
description: Back up, list, verify and restore a project's data (Docker volumes, MongoDB, PostgreSQL, files) and prepare a restore test measuring RPO and RTO. Use for "backup", "restaure", "test de restauration", "continuité d'activité", "PRA".
disable-model-invocation: true
---

# Backup and restore

Read the project's procedure first (CLAUDE.md, `docs/`, `procedures/`, `backup-*` scripts, `Makefile`): commands and RPO/RTO objectives are defined there. This outline only fixes the guardrails.

## Back up
- Always **check the real output directory** (the printed message may not reflect it) and free disk space.
- Encrypted backup, copy **off the main server**, documented retention, verified integrity (listing + size + read test).
- A backup that was never restored is not a backup: schedule periodic restore tests.

## Restore: guardrails
- **Announce and get approval** before running: a restore often stops the whole service and restarts it.
- Take a backup **right before** restoring.
- Restore **first in a local or disposable environment**, never straight into production for a test.
- Production: change record and approval by a second person (`dev-traceability`).
- Never `down -v`, `volume prune` or delete a volume to "fix" something.

## Restore test (recovery evidence)
1. Choose a data set and a backup date.
2. Restore locally; measure real time (RTO) and age of the latest recovered data (RPO); compare with the project's objectives.
3. Check integrity: counts, business invariants (sum of ledger entries is zero for money), audit chain.
4. Report: volume, date, duration, anomalies, gap to RTO/RPO; open an issue per gap (`issue-lifecycle`).

## Report gaps, do not hide them
No off-site copy, no recorded restore test, single host, scripts cited by a procedure but missing from the repository, disk nearly full (logs not rotated).

## End of task
Log the run: `${CLAUDE_SKILL_DIR}/../skill-learning/learn.py log backup-restore ok|partial|failed [--note …]`.
