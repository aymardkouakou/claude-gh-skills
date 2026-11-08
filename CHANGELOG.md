# Changelog

All notable changes to this repository. Format: [Keep a Changelog](https://keepachangelog.com/), versions follow SemVer.

## [Unreleased]

## [0.10.0] - 2026-11-08

### Added
- `dependencies.json` declares which sibling skills each skill requires or can optionally use, checked against the skills by a test; `scripts/check_deps.py` (also in `install.sh doctor`) reports missing siblings; `journal.sh`, `project.py` and `board.py` now stop with a message naming the missing skill instead of a traceback (#20).
- `dev-traceability/rtm.py`: generates the requirements traceability matrix (Markdown or CSV) from GitHub issues and pull requests and the git history; flags closed issues with no commit, no test change, no pull request or no independent review; `--solo`, `--strict`, `--range`; text escaped against Markdown and spreadsheet-formula injection (#21).
- `scripts/release.py VERSION [--refs N …] [--apply] [--push]`: dry run by default; refuses a dirty tree, a branch other than main, a version that is not newer, an empty Unreleased section or failing tests; then bumps both manifests, dates the changelog, commits (`Refs`/`No-Issue`), tags, and with `--push` pushes and creates the GitHub release from the changelog section. Python instead of the shell script named in #22, for testability.
- Hook guards in `hooks/require_issue_ref.py`: `gh pr create|edit --body` without a reference is denied, force-pushes to main or master are denied, `gh issue close N` asks for confirmation when no local commit mentions #N (#19).
- `secrets-hygiene/scan_secrets.py`: read-only credential scan of tracked files (`path:line: rule`, never a value, 100 % statement coverage); `references/` for `security-audit` (read-only checklist commands), `secrets-hygiene` (inventory template) and `incident-response` (register, notification and post-mortem templates) (#18).
- `evals/`: one behaviour evaluation file per skill (trigger and no-trigger prompts in English and French, procedure checks with `must` / `must_not`), structure enforced by `tests/test_evals.py`. `evals/run.py` replays the trigger prompts with `claude -p` (dry run by default, `--run` to execute, per-case `--budget`), grades whether the `Skill` tool was called, and lists the procedure checks for human review (#17).

## [0.9.0] - 2026-11-08

### Changed
- **Licence**: Apache-2.0 replaced by the claude-gh-skills Source-Available License 1.0 for versions from v0.9.0: free use, no redistribution of the work or of modified versions, changes only through contributions to this repository, attribution kept. Versions up to v0.8.0 remain under Apache-2.0. SPDX headers now `LicenseRef-claude-gh-skills-1.0`, manifests `SEE LICENSE IN LICENSE`.
- `security-audit`, `repo-hardening`, `secrets-hygiene`, `change-management`, `incident-response` and `skill-learning` gain a `Tracking` section: findings, records and approved proposals become issues attached to the Project and an epic (every gap, not only critical ones; never a secret value in issue text). Rule added to `CONVENTIONS.md`, enforced by a conventions test (196 tests).

## [0.8.0] - 2026-11-08

### Fixed
- `journal.sh`, `check-refs.sh` and `text_guard.py` print a clear `Usage:` line (exit 2) on missing arguments, and accept `--help`; an unreadable file no longer produces a traceback.
- `install.sh doctor` no longer reports missing symlinks when the `traceable-dev` plugin is installed (the two modes are exclusive).

### Added
- 11 tests (usage messages, hook, `No-Issue` exception): 195 in total.
- `hooks/` (plugin `PreToolUse` hook): `git commit -m …` is denied without `Refs|Fixes|Closes|Resolves #n` in repositories that adopted tracking (a Project is remembered by `repo-context`). A `No-Issue: <reason>` line documents an exception; `check-refs.sh` accepts it too. Fail-open when the commit cannot be inspected. Plugin install only (symlink installs have no hooks).

## [0.7.2] - 2026-11-05

### Changed
- README: tables re-aligned by the editor's Markdown formatter; the terminal install instructions (`claude plugin …`) restored after a stale editor buffer had overwritten them.
- `.gitignore`: editor Local History (`.history/`) is ignored.

## [0.7.1] - 2026-11-05

### Changed
- README: plugin install also documented with the `claude plugin` CLI for environments where `/plugin` is unavailable, and a warning not to combine it with the symlink install.

## [0.7.0] - 2026-11-05

### Added
- Process rule "documentation first" in `CONVENTIONS.md` and `CONTRIBUTING.md` (release checklist), with tests that the README lists every skill, documents existing script paths, and that the changelog covers the manifest version.
- Tests guarding granularity: `SKILL.md` of 70 lines at most, a trigger sentence and a boundary in every description.

### Changed
- **Skills split by responsibility** (eleven skills, each with a short `SKILL.md`, long material in `references/`):
  - `issue-lifecycle` keeps the error lifecycle; Project and epic handling moves to the new `project-tracking` (`project.py`), fields, views and reports to the new `project-board` (`board.py`).
  - `dev-traceability` keeps the requirement-to-merge chain; the change record, approval, deployment and emergency flow move to the new `change-management` (manual invocation); the compliance report moves to `references/`.
  - `repo-hardening` (new) takes the GitHub repository controls out of `security-audit`, which is now about applications only.
  - `repo-context` moves the profile and language details to `references/`.
- Every skill description names its triggers (English and French) and what it is *not* for, so the right skill loads.
- Scripts moved with their skills: `project.py` to `project-tracking/`, `board.py` to `project-board/` (update any hard-coded path).

### Fixed
- `dev-traceability` pointed to an issue template it did not contain.
- `board.py report --post --with-titles` fails closed when the Project visibility cannot be read.

## [0.6.1] - 2026-11-05

### Security
- `board.py tasklist`: references to another repository are skipped unless `--allow-cross-repo` is given (a task list is untrusted text and could otherwise make the tool write to a repository the user did not name); issue URLs are only understood on the repository's own host.
- `board.py report --post`: the published status update carries counts only; titles need `--with-titles` and are refused when a public Project could show items of other or non-public repositories.

## [0.6.0] - 2026-11-05

### Added
- `board.py`: standard fields (`setup`), 15 standard Project views (`views`), follow-up `report` with optional Project status update (`--post`), `set` field values, draft items (`draft`, `drafts`, `convert`), and `tasklist` (checklists to sub-issues, idempotent). Verified on a real Project.
- Cross-repository references (`owner/repo#n`) for `attach`, `detach`, `tree` and epics.
- `project.py tree EPIC` (sub-issue hierarchy with progress, up to 8 levels), `detach`, `attach --replace` (move to another parent) and `attach --pr`; open pull requests are now reported by `orphans` and added to the Project by `backfill`.
- README: table of what Projects, epics and sub-issues cover.

### Fixed
- Integer GraphQL variables are typed (`gh api -F`), found by a live test.

### Changed
- `project.py` preconditions extracted into `bootstrap` (shared with `board.py`).
- The CI badge is removed from the README until the GitHub billing lock is lifted.

## [0.5.0] - 2026-11-05

### Removed
- Skills unrelated to GitHub operations: `amounts-check`, `payment-reconciliation`, `docker-cleanup`, `backup-restore` (still available at tag `v0.4.0`). The plugin now ships seven skills.

### Changed
- Repository renamed `claude-skills` → `claude-gh-skills` (GitHub redirects the old URLs). Marketplace: `/plugin marketplace add aymardkouakou/claude-gh-skills`.
- Full review of the remaining skills: dangling references to removed skills and to `wave-payments` fixed; payment-specific wording generalised (definition of done, incident response, secrets hygiene).
- `security-audit` gains GitHub repository controls (branch protection and rulesets, secret scanning, Dependabot, CODEOWNERS, workflow permissions); `secrets-hygiene` covers GitHub secrets (names only).
- `issue-lifecycle` resolves the user-confirmed Project and language before opening anything, and creates the `epic` label when missing.
- `install.sh` prunes dangling links left by removed skills.

## [0.4.0] - 2026-11-05

### Added
- `project.py create` (Project linked to the repository, as visible as it), `visibility` (realign) and `use OWNER/NUMBER` (record the user's choice).
- Continuous integration (`.github/workflows/test.yml`: Python 3.9 and 3.12 on Linux and macOS), `SECURITY.md`, `CONTRIBUTING.md`.
- Tests for the shell helpers `journal.sh` and `check-refs.sh`; 114 tests, 100% coverage of the Python helpers.

### Changed
- **The Project is the user's choice**: `project.py` only suggests a candidate (linked to the repository, or named like it) and exits 3 until the user confirms it with `use`; it no longer records a detected Project silently.
- **The GitHub language is never defaulted**: `journal.sh` refuses (exit 3) while it is unset, and the skills require asking the user to confirm it.

### Fixed
- A repository without a linked Project could be attached to the owner's only other Project (for example another repository's board). Unrelated owner Projects are never picked.

## [0.3.0] - 2026-11-05

### Added
- Claude Code plugin and marketplace manifests (`.claude-plugin/`): `/plugin marketplace add aymardkouakou/claude-skills` then `/plugin install traceable-dev@aymardkouakou-skills` (validated with `claude plugin validate`).
- Apache-2.0 `LICENSE` and attribution `NOTICE`; SPDX and copyright headers in scripts.
- README rewritten for discoverability; repository description and topics.
- Tests guarding distribution: no hard-coded install path, script references resolve, manifests consistent with the changelog.

### Changed
- Skills reference their scripts with `${CLAUDE_SKILL_DIR}` (and `${CLAUDE_SKILL_DIR}/../<skill>/` for siblings) instead of `~/.claude/skills/<skill>/`, so they work both symlinked and as a plugin.

## [0.2.0] - 2026-11-05

### Added
- `issue-lifecycle/project.py`: every issue is driven by the repository's GitHub Project (found automatically, always announced, remembered as note `project`) and attached to an epic through native sub-issues. Commands `resolve`, `attach`, `orphans`, `backfill` (dry-run by default). Detects a token without the `project` scope. Unit tests cover 100% of `project.py` and `repo-context/ctx.py`.

### Security
- `project.py`: honours the repository host (GitHub Enterprise) for every `gh` call and issue URL; issue titles are sanitised, quoted and labelled as untrusted data before being printed.

### Changed
- `repo-context`: `resolve` returns a repository profile `kind` (personal/organization, public/private/internal, fork, archived, writable, rules) from `gh repo view`; `project.py` and the issue/traceability skills adapt to it and stop on non-writable repositories.
- `issue-lifecycle`, `dev-traceability`, `repo-context`: Project and epic attachment is a mandatory step of the issue flow and a traceability-chain control.

## [0.1.0] - 2026-11-05

### Added
- `repo-context`: resolve and remember the active GitHub repository (gh-compatible), cache labels and verified per-repository notes.
- `skill-learning`: local usage log, summaries and improvement briefs.
- `dev-traceability`: traceable development lifecycle aligned with ISO/IEC 27001, ISO 9001, ISO/IEC/IEEE 12207, ITIL 4 and SOC 2; change register, traceability matrix, definition of done, `check-refs.sh`.
- Generalised, English versions of skills derived from a payment-platform skill set: `issue-lifecycle`, `security-audit`, `payment-reconciliation`, `amounts-check`, `docker-cleanup`, `incident-response`, `secrets-hygiene`, `backup-restore`.
- `install.sh` (symlink install and `doctor`), tests including an English-only convention check.

- Configurable GitHub output language per repository (`ctx.py lang`), separate commit-message language, localised journal labels (`labels.json`).

### Security
- `ctx.py repo` exits with code 5 for repositories not confirmed by `gh` (remembered or unverified), preventing wrong-target writes from `journal.sh`.

### Changed
- Removed project-specific findings, hostnames and addresses from the source skills; skills now describe methods.
