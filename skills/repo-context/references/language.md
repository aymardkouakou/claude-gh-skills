# Language of GitHub output
The skills themselves are written in English, but **what is published on GitHub** (issues, journal comments, PR descriptions, release notes) is written in a language the user chooses, per repository.
- Resolution order: `CLAUDE_SKILL_LANG` (one-off override) → repository setting → global setting → unset.
- Unset: **always stop and ask the user to confirm** (never default, infer or write first) ("Which language for issues and PRs in this repository?"), then save it: `ctx.py lang set fr` (this repository) or `ctx.py lang set fr --global`. Do not guess from the conversation language.
- An explicit request in the conversation ("write this issue in English") wins for that piece of text only; do not change the saved setting unless asked.
- Commit messages have their own setting: `ctx.py lang --commit` (default `en`; change with `lang set CODE --commit`).
- Write the text directly in the chosen language, translating the English templates and headings; keep identifiers, commands, paths and error messages verbatim.
