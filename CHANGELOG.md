# Changelog

All notable changes to this repository. Format: [Keep a Changelog](https://keepachangelog.com/), versions follow SemVer.

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
