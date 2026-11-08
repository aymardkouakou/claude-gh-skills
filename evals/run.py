#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-claude-gh-skills-1.1
# Copyright 2026 Aymard Kouakou - see NOTICE
"""Replay the trigger evaluations against Claude Code and grade them.

A prompt is run with `claude -p` (stream-json); the skill counts as triggered when the model calls the
`Skill` tool for it. `no-trigger` cases pass when that skill is NOT invoked. `manual` cases belong to skills that
only the user can start (`disable-model-invocation`): they document the intended prompts and are not graded.
Each prompt runs in an empty temporary directory so the model cannot read the skill files instead of invoking them.
Model behaviour varies between runs: a single failure is a signal to re-run, a repeated one to improve the description. Procedure checks are listed for human review: they are not auto-graded.

Usage: run.py [--skill NAME] [--run] [--model haiku] [--budget 0.30] [--procedure]
Without --run nothing is executed (dry run: lists the cases). Each case costs tokens; --budget caps one case.
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVALS = Path(__file__).resolve().parent


def load(skill=None):
    files = sorted(EVALS.glob("*.json"))
    data = [json.loads(f.read_text(encoding="utf-8")) for f in files]
    if skill:
        data = [d for d in data if d["skill"] == skill]
    return data


def build_command(prompt, model, budget):
    return ["claude", "-p", prompt, "--plugin-dir", str(ROOT), "--model", model, "--output-format", "stream-json",
            "--verbose", "--max-turns", "3", "--max-budget-usd", str(budget), "--no-session-persistence",
            "--permission-mode", "plan"]


def invoked_skills(stream):
    """Names of the skills called through the Skill tool in a stream-json transcript."""
    names = set()
    for line in stream.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") != "assistant":
            continue
        for block in event.get("message", {}).get("content", []):
            if block.get("type") == "tool_use" and block.get("name") == "Skill":
                names.add(str(block.get("input", {}).get("skill", "")).split(":")[-1])
    return names


def grade(case, skill, invoked):
    hit = skill in invoked
    return hit if case["expect"] == "trigger" else not hit


def run_case(prompt, model, budget, runner=subprocess.run):
    try:
        with tempfile.TemporaryDirectory() as empty:
            done = runner(build_command(prompt, model, budget), capture_output=True, text=True, timeout=300, cwd=empty)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"run failed: {type(exc).__name__}"
    return invoked_skills(done.stdout), ""


def main(argv=None, runner=subprocess.run):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--skill")
    ap.add_argument("--run", action="store_true", help="execute (costs tokens); default is a dry run")
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--budget", type=float, default=0.30)
    ap.add_argument("--procedure", action="store_true", help="also print the procedure checks for review")
    args = ap.parse_args(argv)
    data = load(args.skill)
    if not data:
        print(f"unknown skill: {args.skill}", file=sys.stderr)
        return 2
    failed = total = 0
    for d in data:
        for case in d["triggers"]:
            total += 1
            if case["expect"] == "manual":
                print(f"[manual] {d['skill']}: {case['prompt']}" if not args.run else f"SKIP {d['skill']}: manual: {case['prompt']}")
                continue
            if not args.run:
                print(f"[dry] {d['skill']}: {case['expect']}: {case['prompt']}")
                continue
            invoked, err = run_case(case["prompt"], args.model, args.budget, runner)
            ok = invoked is not None and grade(case, d["skill"], invoked)
            failed += not ok
            print(f"{'PASS' if ok else 'FAIL'} {d['skill']}: {case['expect']}: {case['prompt']}"
                  + (f"  ({err})" if err else f"  invoked={sorted(invoked)}" if not ok else ""))
        if args.procedure:
            for p in d["procedure"]:
                print(f"[review] {d['skill']}: {p['prompt']}\n  must: {'; '.join(p['must'])}\n  must not: {'; '.join(p['must_not'])}")
    print(f"{total} case(s)" + (f", {failed} failed" if args.run else " (dry run, use --run to execute)"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
