# claude-gh-skills

**Claude Code skills for traceable, GitHub-driven development: every issue in a Project and under an epic, every change linked from requirement to deployment, plus security audit, secrets hygiene and incident response.**

[![release](https://img.shields.io/github/v/release/aymardkouakou/claude-gh-skills)](https://github.com/aymardkouakou/claude-gh-skills/releases)
![skills](https://img.shields.io/badge/skills-7-blue)
[![license](https://img.shields.io/github/license/aymardkouakou/claude-gh-skills)](LICENSE)
![python](https://img.shields.io/badge/python-%E2%89%A53.9%20stdlib%20only-informational)

Seven [Agent Skills](https://docs.claude.com/en/docs/claude-code/skills) for [Claude Code](https://claude.com/claude-code), written in English, versioned, tested (100 % statement coverage of the Python helpers) and installed globally by symlink.

## Why use them

- **No orphan issues.** `issue-lifecycle` attaches each issue to the repository's GitHub Project and to an epic (native sub-issues). The Project and the GitHub language are **your choice**: the skill suggests a candidate, asks you to confirm, and always says which one it uses. A Project is created as visible as its repository. `project.py backfill` repairs existing issues.
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

`incident-response` and `secrets-hygiene` change shared systems and are manual-invocation only.

## Quick start

```bash
git clone https://github.com/aymardkouakou/claude-gh-skills.git
cd claude-gh-skills
./install.sh            # symlinks every skills/<name> into ~/.claude/skills
./install.sh doctor     # checks git, python3, gh, links, SKILL.md names and tests
```

Requirements: `git`, `python3` ≥ 3.9 (standard library only) and, for GitHub features, `gh` logged in. To attach issues to Projects the token needs the `project` scope: `gh auth refresh -s project`.

Install **all** skills: they call each other through sibling directories (`${CLAUDE_SKILL_DIR}/../<name>/`), for example `issue-lifecycle` uses `repo-context`.

### As a Claude Code plugin
```text
/plugin marketplace add aymardkouakou/claude-gh-skills
/plugin install traceable-dev@aymardkouakou-skills
```
Skills are then namespaced (`/traceable-dev:issue-lifecycle`). The manifests pass `claude plugin validate`; the install itself has not been exercised end to end.

Update with `git pull && ./install.sh`; remove with `./install.sh uninstall`.

## Try it

```text
> ouvre une issue pour ce bug de webhook et rattache-la au projet      # issue-lifecycle
> quel dépôt est actif ?                                               # repo-context
> prépare l'audit de cette release                                     # dev-traceability
```

```bash
~/.claude/skills/issue-lifecycle/project.py resolve     # which Project drives this repository (asks you to confirm a candidate)
~/.claude/skills/issue-lifecycle/project.py use OWNER/N  # record your choice
~/.claude/skills/issue-lifecycle/project.py create       # new Project, linked, same visibility as the repo
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

Conventions (structure, frontmatter, English-only rule, safety rules): [`CONVENTIONS.md`](CONVENTIONS.md). Release history: [`CHANGELOG.md`](CHANGELOG.md). See also [`CONTRIBUTING.md`](CONTRIBUTING.md) and [`SECURITY.md`](SECURITY.md).

## License

[Apache-2.0](LICENSE) © 2026 [Aymard Kouakou](https://github.com/aymardkouakou). Reuse, modification and redistribution are free, **provided the [`NOTICE`](NOTICE) file and the copyright notice are kept** and significant changes are stated: the original author is always credited.

## Scope and limits

These skills encode one team's practices, written for Claude Code. The compliance mapping helps prepare evidence; it certifies nothing.

The payment, Docker and backup skills of earlier releases (`amounts-check`, `payment-reconciliation`, `docker-cleanup`, `backup-restore`) were removed in 0.5.0 to keep this repository about GitHub operations; they remain in the git history and at tag `v0.4.0`.
