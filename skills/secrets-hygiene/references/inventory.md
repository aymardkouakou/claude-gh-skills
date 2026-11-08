# Secrets inventory (no values)

`accounts.md` template - one row per secret, never a value, not even partial:

| id | service | account / variable | origin (vault, env, CI) | rotation period | last rotation | state |
| --- | --- | --- | --- | --- | --- | --- |
| db-main | postgres | `POSTGRES_PASSWORD` | GitHub Environment `production` | 90 d | 2026-01-15 | OK |

States: `OK`, `DEFAULT` (known or example value), `WEAK` (short or guessable), `MISSING`, `EXTERNAL` (managed by a third party), `UNTRACKED` (exists but not in the inventory). Only `OK` and `EXTERNAL` are acceptable.

## Scan before a PR
`python3 ${CLAUDE_SKILL_DIR}/scan_secrets.py [PATH]` lists `path:line: rule` for tracked files (AWS, GitHub, Slack and Stripe keys, private key blocks, credentials in URLs, hard-coded credential assignments, suspicious file names such as `.env`). It never prints a value; `--json` for machines, `--exit-zero` to report without failing. Mark a reviewed false positive with the comment `secret-scan: ignore` on that line.

A clean scan is not proof: it misses custom formats and history. If a secret was ever committed, treat it as compromised and rotate it.
