---
name: repo-context
description: Connect to and remember the active GitHub repository (fully gh-compatible) - resolves owner/repo, host, default branch, visibility, permission and auth state from the current directory, caches labels and learned per-repo facts. Use before any `gh` command or whenever another skill needs the project's repository ("quel dépôt", "repo actif", "connecte-toi au dépôt"). Not for general git questions.
---

# Active repository context

Every skill that touches GitHub resolves the repository **first**, through this skill, then passes it explicitly with `--repo`. This avoids acting on the wrong repository (submodules, forks, multiple clones, several accounts).

## Commands
```bash
${CLAUDE_SKILL_DIR}/ctx.py resolve          # JSON: repo, host, default_branch, private, permission, authenticated, source, notes
${CLAUDE_SKILL_DIR}/ctx.py repo             # plain "[HOST/]OWNER/REPO", ready for: gh <cmd> --repo "$(…)"
${CLAUDE_SKILL_DIR}/ctx.py labels [--refresh]
${CLAUDE_SKILL_DIR}/ctx.py note KEY VALUE   # remember a verified fact about this repository
${CLAUDE_SKILL_DIR}/ctx.py lang [--commit]  # language of GitHub output; exit 3 if not chosen yet
${CLAUDE_SKILL_DIR}/ctx.py lang set CODE [--global] [--commit]
${CLAUDE_SKILL_DIR}/ctx.py show | list | forget [OWNER/REPO]
```

## How the repository is found (in order)
1. `--repo` or `GH_REPO` (explicit choice).
2. `gh repo view` in the current directory (honours `gh repo set-default`, forks, several remotes, GitHub Enterprise hosts).
3. The `origin` git remote (https, ssh and scp-style URLs).
4. The last remembered repository, flagged `source: remembered` with a warning.

## Rules
- `ctx.py repo` **refuses (exit 5)** when the repository is only `remembered` or `explicit-unverified`, so scripts such as `journal.sh` can never write to a repository that `gh` did not confirm. Use `--allow-unverified` for read-only purposes only.
- Read `source` and `authenticated`. If `source` is `remembered` or `explicit-unverified`, or `authenticated` is false, **ask the user** before any write (issue, comment, PR, merge, label). Never run `gh auth login`, `gh auth switch` or `gh auth refresh` without being asked.
- Always pass `--repo "$(${CLAUDE_SKILL_DIR}/ctx.py repo)"` to `gh` commands that accept it. For several repositories (monorepo + submodules), resolve each one separately.
- Check `permission` before writing (`READ` cannot open PRs or push).
- **Memory is local and secret-free**: `~/.claude/skill-state/repos/*.json` (override with `CLAUDE_SKILL_STATE`). It stores repository names, default branch, cached labels and short verified notes (for example "PRs go develop → sandbox → main", "labels: type:*, priority:*"). Never store tokens, passwords or personal data; `note` refuses secret-looking text.
- The GitHub Project driving the repository is stored as note `project` = `OWNER/NUMBER`; `project-tracking` only suggests a candidate and the user confirms it (`project.py use`), then states it every time.
- Use `note` only for facts you verified in this repository (workflow rules, label scheme, CI job names, merge style). Do not store opinions.
- `forget` removes a repository from memory on request.

## Profile and language (details in `references/`)
- `ctx.py resolve` returns `kind` (personal or organization, public/private/internal, fork, archived, `writable`, `rules`): read it and apply `rules`; `writable: false` means stop. See `references/profile.md`.
- What is published on GitHub is written in the language the user chose for the repository. **Unset (`ctx.py lang` exits 3) is a hard stop: ask the user to confirm, never default or infer.** See `references/language.md`.

## Failure modes
- `gh` not installed or not authenticated: say so and stop; give the user the command to run (`gh auth login`), do not work around it.
- Exit code 2 and "No repository found": ask the user for `OWNER/REPO` or to open the project directory.

## Learning
After using this skill as part of another skill's run, the calling skill logs the outcome (see `skill-learning`).
