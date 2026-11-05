# Changelog

All notable changes to this repository. Format: [Keep a Changelog](https://keepachangelog.com/), versions follow SemVer.

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
