# Contributing

Issues and pull requests on this repository are the only way the skills evolve: forks are accepted only to prepare a pull request, and modified versions may not be redistributed elsewhere (see [`LICENSE`](LICENSE)).

1. Read [`CONVENTIONS.md`](CONVENTIONS.md): skills are written in English, stay short, hold method rather than volatile
   findings, and never weaken a safety rule.
2. Keep one concern per commit, Conventional Commits in English (`feat(skill): …`, `fix(skill): …`, `docs: …`), and
   reference the issue with `Refs #<n>`.
3. Add or update tests; helper scripts keep full statement coverage. Run `python3 -m unittest discover -s tests`
   (Python 3.9 or newer) and, for plugin changes, `claude plugin validate .`.
4. **Update the documentation first**: `README.md` (skill table, commands, limits), the affected `SKILL.md` and `references/`, then `CHANGELOG.md`; tests check that every skill is listed in the README.
5. A new or changed skill needs its `evals/<skill>.json` (trigger prompts, no-trigger prompts pointing to the right sibling skill, procedure checks).
6. List the change in `CHANGELOG.md`. Releases follow SemVer and keep `.claude-plugin/*.json` in step with the changelog
   (a test checks it).

By contributing you agree to section 4 of the [`LICENSE`](LICENSE): you keep your copyright and grant the author a perpetual, irrevocable licence to use and distribute your contribution as part of the work.
