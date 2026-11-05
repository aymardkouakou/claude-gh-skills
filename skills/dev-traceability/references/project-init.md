# Initialise traceability in a project

Offer it to the user, never impose it; do not commit or push without a request. Read CLAUDE.md and CONTRIBUTING first to respect the existing flow.

## 1. Files to create
```
docs/traceability/
  README.md                 # scope, roles, target standards
  RTM.md                    # requirement ↔ issue ↔ PR ↔ test matrix
  change-register.md        # see the change-management skill, references/change-register.md
.github/PULL_REQUEST_TEMPLATE.md
.github/ISSUE_TEMPLATE/bug.yml, feature.yml
```

### RTM.md
```markdown
| Requirement | Issue | PR | Test(s) | Status |
|---|---|---|---|---|
| REQ-001 | #12 | #15 | tests/test_xxx.py::test_yyy | verified 2026-11-05 |
```

### PULL_REQUEST_TEMPLATE.md
```markdown
## Context
Refs #<n> · Requirement: <ID>

## Changes
-

## Risks and rollback
Change type: standard | normal | major · Rollback:

## Checks
- [ ] Definition of done respected (dev-traceability skill, references/definition-of-done.md)
- [ ] Targeted tests green (run link) · Independent review requested from:
- [ ] No secret or personal data

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

## 2. Controls enforced by the platform (GitHub)
Branch protection or rulesets, signed commits, `CODEOWNERS`, Environments with approval, secret scanning: audit and apply them with the `repo-hardening` skill (read-only by default, one setting at a time, on the user's request).

## 3. Minimal CI
- a job running `check-refs.sh origin/<default>..HEAD` that fails when a commit lacks `Refs #`;
- secret scanning and dependency audit;
- CI logs kept for the project's retention period.

## 4. Cadence
- Monthly review of the change register and the RTM (gaps, emergency changes without review).
- Quarterly export of evidence (PRs, runs, register) into the project's audit folder.
