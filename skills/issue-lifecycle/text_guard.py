# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Aymard Kouakou - see NOTICE
"""Refuse text that looks like a secret (exit code 1): tokens, keys, passwords, private keys. Usage: text_guard.py <file>."""
import re
import sys

PATTERNS = [r"ghp_[A-Za-z0-9]{20}", r"github_pat_", r"gho_[A-Za-z0-9]{20}", r"whsec_[A-Za-z0-9+/=]{10}", r"xox[bap]-", r"AKIA[0-9A-Z]{12}",
            r"-----BEGIN [A-Z ]*PRIVATE", r"Bearer\s+eyJ", r"eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}",
            r"(?i)(password|passwd|secret|token|api[_-]?key)[\"' ]*[:=][\"' ]*[^\s\"'<*]{8,}", r"\b[0-9]{8,10}:AA[A-Za-z0-9_-]{30,}"]


def looks_secret(text):
    return any(re.search(p, text) for p in PATTERNS)


if __name__ == "__main__":
    sys.exit(1 if looks_secret(open(sys.argv[1], encoding="utf-8").read()) else 0)
