#!/bin/bash
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Aymard Kouakou - see NOTICE
# Append a timestamped (UTC) entry to an issue journal: journal.sh <issue#> <type> <text-file> [owner/repo]
# Types: Observation | Hypothesis | Test | Result | Decision | Action | Interaction | "Method error" | Retrospective
# (legacy French names are accepted). The entry label is rendered in the repository's GitHub language
# (ctx.py lang; override with CLAUDE_SKILL_LANG); unknown languages fall back to English.
# Without a repository: the active one (repo-context). Refuses to publish text that looks like a secret.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
if [ $# -lt 3 ] || [ $# -gt 4 ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
  echo "Usage: journal.sh <issue#> <type> <text-file> [owner/repo]" >&2
  echo "Types: Observation | Hypothesis | Test | Result | Decision | Action | Interaction | \"Method error\" | Retrospective" >&2
  [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ] && exit 0; exit 2
fi
n=$1; type=$2; file=$3; repo=${4:-}
case "$type" in
  Hypothèse) type="Hypothesis";; Résultat) type="Result";; Décision) type="Decision";;
  "Erreur de méthode") type="Method error";; Rétrospective) type="Retrospective";;
esac
case "$type" in Observation|Hypothesis|Test|Result|Decision|Action|Interaction|"Method error"|Retrospective) ;; *) echo "unknown type: $type" >&2; exit 2;; esac
[ -f "$file" ] || { echo "file not found: $file" >&2; exit 2; }
if ! python3 -I "$here/text_guard.py" "$file"; then
  echo "REFUSED: the text looks like a secret. Redact it and retry." >&2; exit 3
fi
ctx="$here/../repo-context/ctx.py"
if [ -z "$repo" ]; then
  repo=$(python3 -I "$ctx" repo) || { echo "No active repository: pass owner/repo." >&2; exit 4; }
fi
lang=$(python3 -I "$ctx" lang 2>/dev/null) || {
  echo "REFUSED: no GitHub language chosen for this repository. Ask the user to confirm it, then run: ctx.py lang set CODE" >&2; exit 3; }
label=$(python3 -I - "$here/labels.json" "$lang" "$type" <<'PY'
import json, sys
path, lang, typ = sys.argv[1:4]
try:
    print(json.load(open(path, encoding="utf-8")).get(lang, {}).get(typ, typ))
except (OSError, ValueError):
    print(typ)
PY
)
body=$(mktemp); trap 'rm -f "$body"' EXIT
{ printf '### %s UTC — %s\n\n' "$(date -u '+%Y-%m-%d %H:%M')" "$label"; cat "$file"; } > "$body"
gh issue comment "$n" --repo "$repo" --body-file "$body"
