# Security policy

## Reporting a vulnerability
Please report privately through GitHub: **Security → Report a vulnerability** on this repository
(<https://github.com/aymardkouakou/claude-gh-skills/security/advisories/new>). Do not open a public issue for a vulnerability.
You will get an acknowledgement as soon as possible; there is no formal SLA for this personal project.

## Scope
Skills are instructions plus small helper scripts that run `gh`, `git` and `python3` on your machine with your credentials.
Relevant reports include: a script that could write to the wrong repository or host, leak a secret or personal data,
run attacker-controlled text as a command (for example through an issue title), or weaken a documented safety rule.

## Design guarantees
- Helper scripts use only the Python standard library and `gh`; no network access other than through `gh`.
- Secrets are never stored: local state (`~/.claude/skill-state`) holds repository names, labels and short notes, and notes
  that look like secrets are refused.
- Issue titles and other repository text are treated as untrusted data.
- Writes are refused on unverified, archived, read-only or issue-less repositories.
