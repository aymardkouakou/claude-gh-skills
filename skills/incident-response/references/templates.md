# Incident templates

Technical identifiers only: no personal data, no secret.

## Register entry (`incidents/<YYYY-MM-DD>-<id>.md`)
```
Id: <YYYY-MM-DD>-<n>        Severity: P1-P4
Detected (UTC): <time>      Declared by: <role>
Nature: <leak | fraud | outage | other>
Services and operations touched: <list>
Users affected: <number or unknown>     Personal / payment data: <yes | no | unknown>
Evidence folder: ~/incidents/<id> (mode 700, sha256 recorded)
Status: open | contained | recovered | closed
```

## Timeline (one line per event)
`<UTC time> | <Detection | Action | Decision | Recovery> | <what, by whom> | <command or reference>`

## Notification draft (never sent by Claude)
```
To: <authority or party from the project's procedure>
Deadline: <from the procedure, or "not defined - ask the owner">
What happened: <facts, UTC times>
Data and people concerned: <categories and counts, no identities>
Measures taken: <containment, rotation>
Contact: <role, not a personal address>
```

## Blameless post-mortem
Summary - Impact - Timeline - Root cause (5 whys) - What went well - What went badly - Actions (owner, due date, issue number) - Emergency change record (`change-management`, review within 48 h).
