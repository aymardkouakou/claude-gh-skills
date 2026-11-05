#!/bin/bash
# Append a timestamped (UTC) entry to an issue journal: journal.sh <issue#> <type> <text-file> [owner/repo]
# Types: Observation | Hypothesis | Test | Result | Decision | Action | Interaction | "Method error" | Retrospective
# (legacy French names are accepted). The entry label is rendered in the repository's GitHub language
# (ctx.py lang; override with CLAUDE_SKILL_LANG); unknown languages fall back to English.
# Without a repository: the active one (repo-context). Refuses to publish text that looks like a secret.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
n=${1:?issue number}; type=${2:?type}; file=${3:?text file}; repo=${4:-}
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
lang=$(python3 -I "$ctx" lang 2>/dev/null || echo en)
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
