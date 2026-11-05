# Definition of done (tick in the PR)

## Traceability
- [ ] Requirement identified and issue linked (`Refs #<n>`)
- [ ] Atomic commits, Conventional Commits in English
- [ ] Traceability matrix updated (`docs/traceability/RTM.md`)

## Quality
- [ ] Targeted test added or changed; it fails without the fix and passes with it
- [ ] Relevant tests and linter green (CI run link)
- [ ] Independent review done (reviewer ≠ author); findings fixed or dismissed with a reason
- [ ] Edge cases and errors handled (timeouts, intermediate statuses, invalid input)

## Security
- [ ] No secret, token or personal data in the diff, logs or messages
- [ ] Input validated server-side, parameterised queries only
- [ ] Access control verified server-side for every new route
- [ ] New dependencies reported and justified
- [ ] Sensitive area (auth, money, data): security review done

## Money (payment projects)
- [ ] XOF amounts as integers, conversion 1 EUR = 676 XOF, explicit and tested rounding
- [ ] Callbacks and webhooks idempotent, signature verified, logged without sensitive data

## Delivery
- [ ] Rollback plan written
- [ ] Change record created and approved (except standard changes)
- [ ] Documentation updated (README, ADR, runbook)
- [ ] Real verification after deployment, result recorded
