# claude-skills

**Claude Code skills for traceable, GitHub-driven development: every issue in a Project and under an epic, every change linked from requirement to deployment, plus payment-platform and security checks.**

[![release](https://img.shields.io/github/v/release/aymardkouakou/claude-skills)](https://github.com/aymardkouakou/claude-skills/releases)
![skills](https://img.shields.io/badge/skills-11-blue)
![python](https://img.shields.io/badge/python-%E2%89%A53.9%20stdlib%20only-informational)

Eleven [Agent Skills](https://docs.claude.com/en/docs/claude-code/skills) for [Claude Code](https://claude.com/claude-code), written in English, versioned, tested (100 % statement coverage of the Python helpers) and installed globally by symlink.

## Why use them

- **No orphan issues.** `issue-lifecycle` attaches each issue to the repository's GitHub Project and to an epic (native sub-issues), finds the Project automatically and always says which one it used. `project.py backfill` repairs existing issues.
- **Auditable changes.** `dev-traceability` enforces requirement → issue → commit → PR → review → tests → deployment → verification, with a change register and traceability matrix mapped to ISO/IEC 27001, ISO 9001, ISO/IEC/IEEE 12207, ITIL 4 and SOC 2 (evidence, not certification).
- **Never the wrong repository.** `repo-context` resolves the repo through `gh`, classifies it (personal or organization, public / private / internal, fork, archived, writable) and the other skills adapt to that profile.
- **Safe by default.** No secret in output, writes refused on unverified or read-only repositories, destructive operations always confirmed.
- **They get better.** `skill-learning` logs outcomes locally and drafts reviewed improvements.

## Skills

| Skill | Use it when you want to… | Also triggers on (French) |
|---|---|---|
| [`repo-context`](skills/repo-context/SKILL.md) | resolve and remember the active GitHub repository and its profile | "quel dépôt", "repo actif" |
| [`issue-lifecycle`](skills/issue-lifecycle/SKILL.md) | record an error as an issue, keep a timestamped journal, fix, verify, close; attach to Project and epic | "ouvre une issue", "bug récurrent" |
| [`dev-traceability`](skills/dev-traceability/SKILL.md) | deliver a feature, fix or release with a full evidence chain | "matrice de traçabilité", "registre des changements" |
| [`skill-learning`](skills/skill-learning/SKILL.md) | review how skills were used and improve them | "améliore les skills" |
| [`security-audit`](skills/security-audit/SKILL.md) | audit an application before a release (read-only) | "audit sécurité", "avant la prod" |
| [`secrets-hygiene`](skills/secrets-hygiene/SKILL.md) | audit and rotate secrets without reading their values | "rotation des secrets" |
| [`incident-response`](skills/incident-response/SKILL.md) | handle an incident: qualification, containment, evidence, notifications | "incident", "panne en production" |
| [`backup-restore`](skills/backup-restore/SKILL.md) | back up, verify and restore data; RPO/RTO | "restaure", "test de restauration" |
| [`payment-reconciliation`](skills/payment-reconciliation/SKILL.md) | diagnose a stuck or mismatched mobile-money transaction | "transaction à vérifier", "écart" |
| [`amounts-check`](skills/amounts-check/SKILL.md) | compute and verify XOF integer amounts, fees and rounding | "vérifie ce calcul" |
| [`docker-cleanup`](skills/docker-cleanup/SKILL.md) | clean images and build cache after a task, never volumes | "nettoie docker" |

`incident-response`, `secrets-hygiene` and `backup-restore` change shared systems and are manual-invocation only.

## Quick start

```bash
git clone https://github.com/aymardkouakou/claude-skills.git
cd claude-skills
./install.sh            # symlinks every skills/<name> into ~/.claude/skills
./install.sh doctor     # checks git, python3, gh, links, SKILL.md names and tests
```

Requirements: `git`, `python3` ≥ 3.9 (standard library only) and, for GitHub features, `gh` logged in. To attach issues to Projects the token needs the `project` scope: `gh auth refresh -s project`.

Install **all** skills: they call each other by path (`~/.claude/skills/<name>/…`), for example `issue-lifecycle` uses `repo-context`.

Update with `git pull && ./install.sh`; remove with `./install.sh uninstall`.

## Try it

```text
> ouvre une issue pour ce bug de webhook et rattache-la au projet      # issue-lifecycle
> quel dépôt est actif ?                                               # repo-context
> prépare l'audit de cette release                                     # dev-traceability
```

```bash
~/.claude/skills/issue-lifecycle/project.py resolve     # which Project drives this repository
~/.claude/skills/issue-lifecycle/project.py orphans     # open issues outside the Project or without an epic
~/.claude/skills/issue-lifecycle/project.py backfill --epic 12 --apply
```

## How it works

- **Repository awareness.** `repo-context` runs `gh repo view`, falls back to the git remote, then to the last remembered repository, and keeps a small secret-free record per repository in `~/.claude/skill-state/`. Skills pass `--repo` explicitly.
- **Language.** Skill files are English. The language of what they publish on GitHub is chosen per repository: `ctx.py lang set fr` (`--global`, `--commit` for commit messages). Unset means the skill asks once.
- **Learning.** Each skill ends with `learn.py log <skill> ok|partial|failed`; improvements go on `improve/…` branches and wait for review. Nothing is pushed or merged automatically.

## Develop and contribute

```bash
python3 -m unittest discover -s tests
```

Conventions (structure, frontmatter, English-only rule, safety rules): [`CONVENTIONS.md`](CONVENTIONS.md). Release history: [`CHANGELOG.md`](CHANGELOG.md). Issues and ideas are welcome.

## Scope and limits

These skills encode one team's practices, written for Claude Code. The compliance mapping helps prepare evidence; it certifies nothing. Payment skills target XOF mobile-money platforms (1 EUR = 676 XOF).
