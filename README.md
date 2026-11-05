# claude-skills

Personal, versioned Claude Code skills, installed **globally** (`~/.claude/skills`) by symlink. Language: English (see `CONVENTIONS.md`).

## Skills

| Skill | Purpose | Invocation |
|---|---|---|
| `repo-context` | Resolve and remember the active GitHub repository (gh-compatible) | auto |
| `skill-learning` | Log usage and corrections, draft reviewed skill improvements | auto / on request |
| `issue-lifecycle` | Error → GitHub issue → journal → fix → closure | auto |
| `dev-traceability` | Traceable development aligned with ISO 27001 / ISO 9001 / 12207 / ITIL / SOC 2 | auto |
| `security-audit` | Application security audit (read-only) | auto |
| `payment-reconciliation` | Diagnose payment transactions, reconciliation checks | auto |
| `amounts-check` | XOF integer amounts, fees, rounding | auto |
| `docker-cleanup` | Safe Docker cleanup, never volumes | auto |
| `incident-response` | Incident handling, evidence, notification drafts | manual |
| `secrets-hygiene` | Audit and rotate secrets without reading values | manual |
| `backup-restore` | Backups, restore tests, RPO/RTO | manual |

## Install
```bash
./install.sh            # symlink every skills/<name> into ~/.claude/skills
./install.sh doctor     # check gh, python3, links and conventions
```
Requires `git`, `python3` (≥ 3.9, standard library only) and, for GitHub features, `gh` logged in (`gh auth login`).

## How the skills stay aware of the project
`repo-context` runs `gh repo view` in the current directory (falling back to the git remote, then to the last remembered repository), checks authentication and permission, and stores a small secret-free record per repository in `~/.claude/skill-state/`. Other skills call `ctx.py repo` and pass `--repo` explicitly, so they never act on the wrong repository.

## Language
Skill files are English. The language of what they **publish on GitHub** is chosen per repository: `ctx.py lang set fr` (or `--global`, `--commit` for commit messages). Unset means the skill asks once.

## How the skills improve
Each skill ends with `learn.py log <skill> ok|partial|failed`. `skill-learning` summarises the local history, drafts the smallest change backed by repeated evidence on an `improve/…` branch, and waits for review. Nothing is pushed or merged automatically.

## Develop
```bash
python3 -m unittest discover -s tests
```
Contribution rules and release process: `CONVENTIONS.md`, `CHANGELOG.md`.
