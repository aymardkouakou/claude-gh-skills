# Read-only commands

`REPO` is `owner/repo`. A 403 or 404 on a settings endpoint usually means missing admin permission or a feature not included in the plan: report *not verified* or *not available*, not *gap*.

```bash
gh api repos/$REPO --jq '{private,visibility,default_branch,archived,security_and_analysis}'
gh api repos/$REPO/branches/<default>/protection          # classic protection
gh api repos/$REPO/rulesets --jq '.[]|{name,enforcement,target}'
gh api repos/$REPO/actions/permissions                    # allowed actions, default workflow permissions
gh api repos/$REPO/actions/permissions/workflow
gh api repos/$REPO/environments --jq '.environments[]|{name,protection_rules}'
gh api repos/$REPO/vulnerability-alerts -i | head -1      # 204 = Dependabot alerts enabled
gh secret list --repo $REPO ; gh variable list --repo $REPO   # names only
test -f .github/CODEOWNERS -o -f CODEOWNERS ; ls .github/PULL_REQUEST_TEMPLATE* .github/ISSUE_TEMPLATE 2>/dev/null
grep -RnE 'uses: [^@]+@(main|master|v[0-9]+)$' .github/workflows   # unpinned third-party actions
grep -Rn 'pull_request_target' .github/workflows
```

## Applying (only on explicit request, one setting at a time)
Prefer the repository's Settings → Rules page, or `gh api -X PUT/POST` with the exact payload shown to the user first. Record the change in the change register when the repository is production-relevant (`change-management`).
