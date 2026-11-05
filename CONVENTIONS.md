# Conventions

## Language: English only (rule set by the owner)
**Every skill is written in English**: `SKILL.md`, `references/`, script messages, comments, commit messages, changelog. This applies to every skill created or edited here, including skills drafted from French sources.
- The only French allowed: **trigger keywords** quoted in the `description` (for example "rotation des secrets") so French requests still match, and proper nouns.
- Answers to the user in conversation stay in the user's language (French); only the skill files are English.
- **GitHub output language is a separate, configurable setting**: what skills publish (issues, comments, PR text, release notes) follows `repo-context` (`ctx.py lang`, per repository or global; commit messages via `--commit`, default English). Skill files never change language because of it; localised labels used by scripts live in JSON data files (for example `issue-lifecycle/labels.json`).
- `tests/test_conventions.py` fails when a skill body contains French prose.

## Structure
```
skills/<name>/SKILL.md          # required; name = directory name; description says when to use AND when not to
skills/<name>/references/       # long material loaded on demand (keep SKILL.md under ~100 lines)
skills/<name>/*.py|*.sh         # helper scripts: standard library / POSIX only, no network except gh
```

## Frontmatter
- `name` (kebab-case, equals the directory), `description` (what it does + when to use + when not to + French triggers).
- `disable-model-invocation: true` for anything that changes a shared system or is destructive (deploy, restore, rotation, incident response).

## Writing rules
- Imperative, short, verifiable steps; exact commands in code blocks.
- Skills hold **method**, not volatile findings (line numbers, current gaps, IPs, hostnames): put those in dated project reports.
- Never contain secrets, tokens, personal data or infrastructure addresses.
- Safety rules are never weakened to remove friction: find a safer way to satisfy them.
- A skill that uses GitHub resolves the repository through `repo-context` and passes `--repo` explicitly.
- A skill ends with a one-line `skill-learning` log call.

## State
Runtime memory (active repository, usage history) lives in `~/.claude/skill-state/` (override: `CLAUDE_SKILL_STATE`). It is local, secret-free and never committed.

## Versioning
- Git, Conventional Commits in English (`feat(skill): …`, `fix(skill): …`, `docs: …`), one concern per commit.
- Semantic versioning with tags `vMAJOR.MINOR.PATCH`; every change listed in `CHANGELOG.md`.
- Improvements proposed by `skill-learning` go on `improve/<skill>-<topic>` branches and are merged only after the owner's review.
- Run `python3 -m unittest discover -s tests` before every commit.
