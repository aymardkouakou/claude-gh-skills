# Change register

Project file: `docs/traceability/change-register.md`. One line per change delivered to a shared environment; never delete or rewrite a line (a correction is added).

| ID | Date (UTC) | Type | Risk | Summary | Issue / PR | Version | Env. | Rollback | Author | Approver | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|
| CHG-2026-001 | 2026-11-05 14:10 | normal | medium | … | #12 / #15 | v1.4.2 | prod | revert PR #15 | A | B | OK |

## Change record (detailed body, linked from the line)

```markdown
## CHG-<year>-<NNN> — <title>
- Type: standard | normal | major | emergency
- Risk: low | medium | high — justification:
- Impact: services, data, users concerned, planned window
- Requirements / issues / PRs: …
- Tests and evidence: CI run link, scenario replayed
- Rollback plan: exact command or procedure, estimated duration
- Author: … · Approver (≠ author): … · Approval date:
- Deployment: command, version, environment, start / end time
- Post-deployment verification: observed result
- Verdict: OK | rolled back | incident (link)
- Emergency only: retroactive review due on … (≤ 48 h), done on …
```

## Rules
- Sequential identifier per year, no gaps; a gap is reported.
- The verdict is the one observed after deployment, not the command's exit status.
- No personal data, no secret.
