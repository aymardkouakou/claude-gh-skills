# Resolution journal

Two layers: the **body** (living summary, always up to date) and the **comments** (full journal, written when things happen, never reconstructed).

| Type | When | Content |
|---|---|---|
| Observation | a fact is noted | command or source, useful result (redacted) |
| Hypothesis | an explanation is considered | why this one, what would confirm or refute it |
| Test | something is checked | what is run, what is expected |
| Result | the test answers | confirms / refutes, consequence for next steps |
| Decision | a choice is made | options, rejected alternatives and why, who decides |
| Action | a system is modified | what, where, risk, rollback, check done right after |
| Interaction | the user asks, decides or authorises | request summarised faithfully (short quote for an authorisation or refusal), follow-up |
| Method error | we are wrong or lose time | the error, how it was noticed, what changes |
| Retrospective | at closure | cause, why detected then, what would have prevented it, links |

`journal.sh` accepts exactly these type names: `Observation | Hypothesis | Test | Result | Decision | Action | Interaction | "Method error" | Retrospective`. Legacy French names from older journals are converted automatically.

## Rules
- **Why before what**: every Decision and Hypothesis states the reason, not only the choice.
- Record every interaction that steers the work, summarised; never paste raw conversations (secrets, personal data, noise).
- Journal the assistant's own mistakes too: an honest history beats a smooth one.
- A comment is never rewritten: a correction is added. Only the body is updated.
- `journal.sh` calls `text_guard.py`; never bypass its refusal.

```bash
journal.sh <issue#> <type> <file> [owner/repo]
# without the 4th argument: the active repository (repo-context)
```
