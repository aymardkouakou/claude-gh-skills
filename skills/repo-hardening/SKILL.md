---
name: repo-hardening
description: Audit and, on explicit request, apply the protections of a GitHub repository - default-branch protection or rulesets (required review and status checks, no force-push), secret scanning and push protection, Dependabot, CODEOWNERS, PR and issue templates, Actions permissions and pinned actions, Environments with approval - adapted to the repository type (personal or organization, public or private) and plan. Use for "protège la branche", "durcis le dépôt", "protection de branche", "secret scanning", "permissions GitHub Actions", "règles du dépôt". Read-only by default; application security belongs to security-audit.
---

# Repository hardening (GitHub)

Read-only by default. Changing a repository setting is a shared-system change: show the exact command, wait for the user's yes, then apply. Commands: `references/commands.md`.

## Context
```bash
REPO=$(${CLAUDE_SKILL_DIR}/../repo-context/ctx.py repo)
${CLAUDE_SKILL_DIR}/../repo-context/ctx.py resolve   # read "kind" and "permission" first
```
Adapt to `kind`: a personal private repository on a free plan may not offer branch protection or rulesets (report *not available*, not *gap*); a public repository gets secret scanning and push protection; an organization repository gets CODEOWNERS, required teams and Environments. Admin permission is needed to read most settings.

## Controls (report each as compliant / gap / not available / not verified, with evidence)
1. **Default branch**: pull request required, at least 1 approval from someone other than the author, required status checks, no force-push, no deletion. Rulesets or classic protection.
2. **Secrets**: secret scanning and push protection on; Actions secrets scoped to Environments, names only (`gh secret list`), never values.
3. **Dependencies**: Dependabot alerts and security updates; version updates configured.
4. **Ownership**: `CODEOWNERS` for sensitive paths (auth, payments, migrations, workflows).
5. **Templates**: pull request template (context, risks, rollback, checks), issue templates.
6. **Actions**: `permissions:` least privilege at workflow level, third-party actions pinned to a commit, no `pull_request_target` with an untrusted checkout, fork pull request approval.
7. **Environments**: `staging` and `production` with required reviewers before deployment.
8. **Traceability check**: a CI job running `${CLAUDE_SKILL_DIR}/../dev-traceability/check-refs.sh origin/<default>..HEAD`.

Several repositories of one owner: `${CLAUDE_SKILL_DIR}/audit_org.py OWNER [--repos a,b] [--strict]` compares default-branch rules (rulesets and classic protection) and secret scanning, read-only; `n/a` is not a gap. A shared baseline to review and apply yourself, first in `evaluate` mode, is `references/org-ruleset.json` (`gh api -X POST orgs/OWNER/rulesets --input …`, organization owners only, on explicit request).

## Report
Table: control, result, evidence (API field or `path:line`), action. Distinguish "verified now" from "declared". Gaps are tracked (see Tracking).

## Never
Apply a setting unasked; disable a protection to unblock a task; print a secret value; assume a plan feature exists.

## Tracking
Every gap becomes an issue (`issue-lifecycle`) attached to the Project and a hardening epic (`project-tracking`, Kind = Security or Chore). A setting applied on request is recorded in that issue (control, before, after) and the issue is closed once re-verified.

## End of task
Log the run: `${CLAUDE_SKILL_DIR}/../skill-learning/learn.py log repo-hardening ok|partial|failed [--note …]`.
