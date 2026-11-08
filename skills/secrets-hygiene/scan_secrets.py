#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-claude-gh-skills-1.1
# Copyright 2026 Aymard Kouakou - see NOTICE
"""Read-only scan for hard-coded credentials. Reports `path:line: rule` and NEVER prints a matched value.

Usage: scan_secrets.py [PATH] [--json] [--exit-zero]
Scans files tracked by git (or every file under PATH outside a repository). A line containing
`secret-scan: ignore` is skipped. Exit status 1 when something is found, unless --exit-zero.
"""
import argparse
import json
import os
import re
import subprocess
import sys

MAX_BYTES = 1_000_000
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
RULES = [
    ("aws-access-key-id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    ("github-fine-grained-token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{50,}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("stripe-live-key", re.compile(r"\b[sr]k_live_[A-Za-z0-9]{16,}\b")),
    ("private-key-block", re.compile(r"-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----")),
    ("credential-in-url", re.compile(r"\b[a-z][a-z0-9+.-]*://[^/\s:@]+:[^/\s:@${<]{4,}@")),
    ("hard-coded-credential", re.compile(
        r"(?i)\b[\w.-]*(?:password|passwd|secret|token|api[_-]?key)[\w.-]*\s*[:=]\s*[\"']([^\"'\s]{8,})[\"']")),
]
PLACEHOLDER = re.compile(r"(?i)change.?me|example|your[_-]|xxx|<[^>]+>|\$\{|\{\{|placeholder|dummy|test|\*{3,}|todo")
SUSPECT_NAMES = re.compile(r"(?i)(^|/)(\.env(\.[\w-]+)?|secrets?\.[\w.]+|credentials(\.[\w]+)?|[^/]*\.(pem|key|p12|pfx))$")
SAFE_NAMES = re.compile(r"(?i)\.(example|sample|template|dist)$")


def list_files(root):
    try:
        out = subprocess.run(["git", "-C", root, "ls-files", "-z"], capture_output=True, check=True).stdout
        return [os.path.join(root, p) for p in out.decode("utf-8", "replace").split("\0") if p]
    except (OSError, subprocess.CalledProcessError):
        found = []
        for base, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            found += [os.path.join(base, f) for f in files]
        return found


def scan_text(text):
    """Yield (line number, rule) without ever yielding the matched value."""
    for number, line in enumerate(text.splitlines(), 1):
        if "secret-scan: ignore" in line:
            continue
        for rule, pattern in RULES:
            m = pattern.search(line)
            if not m:
                continue
            value = m.group(1) if pattern.groups else m.group(0)
            if rule in ("hard-coded-credential", "credential-in-url") and PLACEHOLDER.search(value + line[m.start():m.end()]):
                continue
            yield number, rule


def scan(root):
    findings = []
    for path in list_files(root):
        rel = os.path.relpath(path, root)
        if SUSPECT_NAMES.search(rel) and not SAFE_NAMES.search(rel):
            findings.append({"path": rel, "line": 0, "rule": "suspicious-file-name"})
        try:
            if os.path.getsize(path) > MAX_BYTES:
                continue
            with open(path, "rb") as fh:
                raw = fh.read()
        except OSError:
            continue
        if b"\0" in raw:
            continue
        for number, rule in scan_text(raw.decode("utf-8", "replace")):
            findings.append({"path": rel, "line": number, "rule": rule})
    return findings


def main(argv=None):
    ap = argparse.ArgumentParser(description="Read-only credential scan; never prints values.")
    ap.add_argument("path", nargs="?", default=".")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--exit-zero", action="store_true")
    args = ap.parse_args(argv)
    findings = scan(args.path)
    if args.json:
        print(json.dumps(findings, indent=2))
    else:
        for f in findings:
            print(f"{f['path']}:{f['line']}: {f['rule']}")
        print(f"{len(findings)} finding(s); values are never printed", file=sys.stderr)
    return 0 if args.exit_zero or not findings else 1


if __name__ == "__main__":
    sys.exit(main())
