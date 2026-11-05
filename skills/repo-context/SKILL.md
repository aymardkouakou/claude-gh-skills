---
name: repo-context
description: Connect to and remember the active GitHub repository (fully gh-compatible) - resolves owner/repo, host, default branch, visibility, permission and auth state from the current directory, caches labels and learned per-repo facts. Use before any `gh` command or whenever another skill needs the project's repository ("quel dépôt", "repo actif", "connecte-toi au dépôt"). Not for general git questions.
---

# Active repository context

Every skill that touches GitHub resolves the repository **first**, through this skill, then passes it explicitly with `--repo`. This avoids acting on the wrong repository (submodules, forks, multiple clones, several accounts).

## Commands
```bash
~/.claude/skills/repo-context/ctx.py resolve          # JSON: repo, host, default_branch, private, permission, authenticated, source, notes
~/.claude/skills/repo-context/ctx.py repo             # plain "[HOST/]OWNER/REPO", ready for: gh <cmd> --repo "$(…)"
~/.claude/skills/repo-context/ctx.py labels [--refresh]
~/.claude/skills/repo-context/ctx.py note KEY VALUE   # remember a verified fact about this repository
~/.claude/skills/repo-context/ctx.py lang [--commit]  # language of GitHub output; exit 3 if not chosen yet
~/.claude/skills/repo-context/ctx.py lang set CODE [--global] [--commit]
~/.claude/skills/repo-context/ctx.py show | list | forget [OWNER/REPO]
```

## How the repository is found (in order)
1. `--repo` or `GH_REPO` (explicit choice).
2. `gh repo view` in the current directory (honours `gh repo set-default`, forks, several remotes, GitHub Enterprise hosts).
3. The `origin` git remote (https, ssh and scp-style URLs).
4. The last remembered repository, flagged `source: remembered` with a warning.

## Rules
- Read `source` and `authenticated`. If `source` is `remembered` or `explicit-unverified`, or `authenticated` is false, **ask the user** before any write (issue, comment, PR, merge, label). Never run `gh auth login`, `gh auth switch` or `gh auth refresh` without being asked.
- Always pass `--repo "$(~/.claude/skills/repo-context/ctx.py repo)"` to `gh` commands that accept it. For several repositories (monorepo + submodules), resolve each one separately.
- Check `permission` before writing (`READ` cannot open PRs or push).
- **Memory is local and secret-free**: `~/.claude/skill-state/repos/*.json` (override with `CLAUDE_SKILL_STATE`). It stores repository names, default branch, cached labels and short verified notes (for example "PRs go develop → sandbox → main", "labels: type:*, priority:*"). Never store tokens, passwords or personal data; `note` refuses secret-looking text.
- Use `note` only for facts you verified in this repository (workflow rules, label scheme, CI job names, merge style). Do not store opinions.
- `forget` removes a repository from memory on request.

## Language of GitHub output
The skills themselves are written in English, but **what is published on GitHub** (issues, journal comments, PR descriptions, release notes) is written in a language the user chooses, per repository.
- Resolution order: `CLAUDE_SKILL_LANG` (one-off override) → repository setting → global setting → unset.
- Unset: **ask the user once** ("Which language for issues and PRs in this repository?"), then save it: `ctx.py lang set fr` (this repository) or `ctx.py lang set fr --global`. Do not guess from the conversation language.
- An explicit request in the conversation ("write this issue in English") wins for that piece of text only; do not change the saved setting unless asked.
- Commit messages have their own setting: `ctx.py lang --commit` (default `en`; change with `lang set CODE --commit`).
- Write the text directly in the chosen language, translating the English templates and headings; keep identifiers, commands, paths and error messages verbatim.

## Failure modes
- `gh` not installed or not authenticated: say so and stop; give the user the command to run (`gh auth login`), do not work around it.
- Exit code 2 and "No repository found": ask the user for `OWNER/REPO` or to open the project directory.

## Learning
After using this skill as part of another skill's run, the calling skill logs the outcome (see `skill-learning`).
