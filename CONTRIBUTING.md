# Contributing

Issues and pull requests are welcome.

1. Read [`CONVENTIONS.md`](CONVENTIONS.md): skills are written in English, stay short, hold method rather than volatile
   findings, and never weaken a safety rule.
2. Keep one concern per commit, Conventional Commits in English (`feat(skill): …`, `fix(skill): …`, `docs: …`), and
   reference the issue with `Refs #<n>`.
3. Add or update tests; helper scripts keep full statement coverage. Run `python3 -m unittest discover -s tests`
   (Python 3.9 or newer) and, for plugin changes, `claude plugin validate .`.
4. **Update the documentation first**: `README.md` (skill table, commands, limits), the affected `SKILL.md` and `references/`, then `CHANGELOG.md`; tests check that every skill is listed in the README.
5. List the change in `CHANGELOG.md`. Releases follow SemVer and keep `.claude-plugin/*.json` in step with the changelog
   (a test checks it).

By contributing you agree that your contribution is licensed under Apache-2.0 (see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE)).
