# Changelog

All notable changes to this repository. Format: [Keep a Changelog](https://keepachangelog.com/), versions follow SemVer.

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
