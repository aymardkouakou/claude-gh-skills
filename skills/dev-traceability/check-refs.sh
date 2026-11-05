#!/bin/bash
# List commits in a range that carry no issue reference (#n or owner/repo#n): check-refs.sh <base>..<head>
# Exit code 1 if a reference is missing (usable in CI). Read-only.
set -euo pipefail
range=${1:?git range, e.g. origin/main..HEAD}
missing=0
while IFS=$'\t' read -r sha subject; do
  body=$(git show -s --format=%B "$sha")
  if ! printf '%s' "$body" | grep -Eq '(Refs|Fixes|Closes|Resolves)[: ]+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)?#[0-9]+'; then
    printf 'NO REFERENCE  %s  %s\n' "${sha:0:8}" "$subject"; missing=$((missing+1))
  fi
done < <(git log --no-merges --format='%H%x09%s' "$range")
if [ "$missing" -gt 0 ]; then echo "$missing commit(s) without an issue reference" >&2; exit 1; fi
echo "Every commit in $range references an issue."
