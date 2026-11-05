# Repository profile
`ctx.py resolve` returns `kind`: `owner_type` (`personal` | `organization`), `visibility` (`public` | `private` | `internal`), `fork`, `archived`, `writable` and `rules`, derived from `gh repo view` (`visibility`, `isInOrganization`, `isArchived`, `hasIssuesEnabled`, `hasProjectsEnabled`, `viewerPermission`). Read `rules` before acting and apply them; never assume the type when it is `null`.
- Public repository: stricter masking, no vulnerability details in issues (private security advisory instead).
- Personal vs organization: Project owner, availability of issue types and rulesets, review expectations.
- Fork, archived, issues disabled or read-only permission: `writable: false` means stop and tell the user before any write.
