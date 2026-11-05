# Pitfalls

- `.gitignore` rules excluding names containing `secret`, `password`, `credentials`, `*.key`, `*.pem`: a file named that way stays local and breaks CI. Check `git check-ignore -v <file>` and `git diff --cached --stat`.
- Never chain "show checks" and "merge": `if gh pr checks <n> | grep -qi fail; then …; else gh pr merge <n>; fi`.
- Do not filter (`| tail`) the output of a state-changing command before checking its result.
- Destructive commands (`git reset --hard`, `git clean`, selector-based `kubectl delete`): read `git status` or the exact resource list first; prefer `git revert` or `reset --keep`; name resources explicitly.
- After a deployment, check that the component reloaded its code (log, image digest), not only the green output.
