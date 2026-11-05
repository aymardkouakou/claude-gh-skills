# Issue body template

Fill it in as you go; anything not yet known stays "To investigate".

```markdown
## Symptom
<what is observed, exact error message, where and when (UTC)>

## Context
- Environment: local | dev | staging | prod | CI
- Component / repository: <service> — <owner/repo>
- Version / commit: <short sha> (<link>) · deployment: <run link>
- Trigger: <action that caused the error>

## Impact
<who or what is affected, since when, severity>

## Evidence (redacted)
<useful logs, HTTP codes, command outputs>

## Investigation
<timeline: hypothesis → test → result, including dead ends>

## Root cause
<to investigate>

## Fix
<to define>

## Verification
<to do>

## Prevention
<test, guard, documentation, monitoring to add>
```
