#!/bin/bash
# SPDX-License-Identifier: LicenseRef-claude-gh-skills-1.1
# Copyright 2026 Aymard Kouakou - see NOTICE
# Install the skills globally by symlink, or check the setup: ./install.sh [install|doctor|uninstall]
set -euo pipefail
repo=$(cd "$(dirname "$0")" && pwd)
dest="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"
cmd="${1:-install}"

case "$cmd" in
  install)
    mkdir -p "$dest"
    for l in "$dest"/*; do   # prune links to skills removed from this repository
      if [ -L "$l" ] && [ ! -e "$l" ] && case "$(readlink "$l")" in "$repo"/skills/*|*/claude-skills/skills/*|*/claude-gh-skills/skills/*) true;; *) false;; esac; then
        rm "$l"; echo "pruned    $(basename "$l") (skill no longer in this repository)"
      fi
    done
    for d in "$repo"/skills/*/; do
      n=$(basename "$d"); t="$dest/$n"
      if [ -L "$t" ]; then ln -sfn "${d%/}" "$t"; echo "relinked  $n"
      elif [ -e "$t" ]; then echo "SKIPPED   $n: a real directory exists at $t (move it away first)"
      else ln -s "${d%/}" "$t"; echo "linked    $n"; fi
    done;;
  uninstall)
    for d in "$repo"/skills/*/; do
      n=$(basename "$d"); t="$dest/$n"
      if [ -L "$t" ] && [ "$(readlink "$t")" = "${d%/}" ]; then rm "$t"; echo "removed   $n"; fi
    done;;
  doctor)
    ok=0
    chk() { if eval "$2" >/dev/null 2>&1; then echo "OK      $1"; else echo "MISSING $1"; ok=1; fi; }
    chk "git"                  "command -v git"
    chk "python3"              "command -v python3"
    chk "gh installed"         "command -v gh"
    chk "gh authenticated"     "gh auth status"
    plugin=0; if command -v claude >/dev/null 2>&1 && claude plugin list 2>/dev/null | grep -q 'traceable-dev@'; then plugin=1; fi
    [ "$plugin" = 1 ] && echo "INFO    plugin traceable-dev installed: symlinks are not needed (the two modes are exclusive)"
    for d in "$repo"/skills/*/; do
      n=$(basename "$d")
      if [ "$plugin" = 0 ]; then chk "link $n"            "[ -L '$dest/$n' ] && [ \"\$(readlink '$dest/$n')\" = '${d%/}' ]"; fi
      chk "SKILL.md name=$n"   "grep -q '^name: $n\$' '$d/SKILL.md'"
    done
    chk "skill dependencies"   "python3 '$repo/scripts/check_deps.py' --dir \"\$([ '$plugin' = 1 ] && echo '$repo/skills' || echo '$dest')\""
    chk "tests"                "python3 -m unittest discover -s '$repo/tests'"
    exit $ok;;
  *) echo "usage: $0 [install|doctor|uninstall]" >&2; exit 2;;
esac
