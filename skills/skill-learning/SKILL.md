---
name: skill-learning
description: Learn from how skills are actually used so they improve over time - logs the outcome of each skill run and the user's corrections to a local history, summarises success rates and recurring frictions, and drafts reviewed improvements to the skills repository. Use when the user corrects how a skill behaved, after finishing a skill run, or to "review the skills", "améliore les skills", "apprends de mes usages". Not for the content of another skill's task: it only reviews how skills behaved.
---

# Learning from usage

Skills get better from evidence, not guesses. This skill keeps a small local history and turns it into **proposed** changes that the user reviews.

## 1. Log (cheap, one line, at the end of a skill run)
```bash
${CLAUDE_SKILL_DIR}/learn.py log <skill> ok|partial|failed [--note "what was awkward"] [--correction "what the user told me to do differently"]
```
- `ok`: the skill did what was needed. `partial`: needed manual workarounds or extra steps. `failed`: unusable or wrong.
- Log a **correction** whenever the user redirects a skill's behaviour ("don't do X", "always do Y first"). Quote it briefly in the user's own meaning; no copy-paste of conversations.
- Notes are short (≤ 300 characters), redacted automatically for e-mails and phone numbers, and **refused** if they look like secrets. Never put personal data, amounts tied to a customer or secrets in a note.
- The history is local (`~/.claude/skill-state/usage.jsonl`), capped at about 1 MB, never committed, never sent anywhere.

## 2. Review (when asked, or after roughly 20 logged runs)
1. `${CLAUDE_SKILL_DIR}/learn.py summary --days 60` for success rates per skill.
2. `learn.py propose --days 60` for a Markdown brief of corrections and frictions with counts.
3. Read the affected `SKILL.md`, then draft the **smallest** change that addresses repeated evidence (≥ 2 occurrences, or one explicit user correction). Prefer a sharper rule, a missing step, a better trigger phrase or a pitfall note over adding length.
4. Apply changes **in the skills repository** (not in the installed copy, which may be a symlink or a plugin cache that updates overwrite), on a branch named `improve/<skill>-<topic>`, with a Conventional Commit message in English and an entry in `CHANGELOG.md`. Run the repository tests (`python3 -m unittest discover -s tests`).
5. Show the diff and the evidence to the user. **Never merge, push or publish without an explicit request.**

## 3. Per-repository learning
Facts that belong to one project (workflow, label scheme, CI names) are saved with `repo-context` (`ctx.py note KEY VALUE`), not in the skill text. Facts that hold for every project go into the skill through step 2.

## Rules
- Evidence first: no change based on a single ambiguous run.
- Keep every skill in English (see CONVENTIONS.md) and short; remove text when a rule is obsolete.
- Never lower a safety rule (secrets, approvals, destructive actions) because it caused friction; propose a safer way to satisfy it instead.
- The user can wipe the history with `learn.py clear --yes`.
