#!/usr/bin/env python3
"""Classify run logs with Jev (TypeSafe System One): outcome, defect-vs-artifact, area, severity.

Usage:
    set -a; . ./.env; set +a
    python3 tools/jev/triage_runs.py <runs_dir> [--pattern melee-pc.log] [--limit N]

Each run directory (a subdirectory containing the log) gets one TypeSafe call with four questions.
Writes jev-triage.md and jev-triage.json into <runs_dir> and prints the table.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"

# Verdict-bearing lines worth keeping; everything else (engine noise) is dropped.
KEEP = re.compile(r"TEST |GMD |GMP |BBG |gamemode |PASS\b|FAIL|failures=|complete\b|fatal|panic|alive at end|melee-pc: exit", re.I)
DROP = re.compile(r"aurora|teardown|Device lost|Buffer mapping|ntdll|render code|^gw:|script stage|world pass", re.I)

QUESTIONS = {
    "outcome": {
        "type": "choice",
        "instructions": "What does this excerpt show about how the run ended or behaved?",
        "criteria": {
            "test_failed": "A test or scripted check reported FAIL, an assertion failed, or a section reported failure",
            "test_passed": "A test or scripted check completed and reported success (PASS / complete / failures=0)",
            "crashed": "The process crashed, faulted, was killed, or died without a verdict",
            "cut_short": "The run ended, was cut off, or stalled without reaching a pass or fail verdict",
            "normal_operation": "No test verdict and no failure; ordinary operation, warnings, or informational output",
        },
    },
    "defect": {
        "type": "noul",
        "instructions": "If a failure or problem is present in the excerpt, does it point at a defect in the game/port code rather than at a test-harness, scenario, timing, or environment artifact?",
        "criteria": {
            "true": "The described failing behavior is plausibly wrong game/port/script behavior that code should fix",
            "false": "The failure looks like a harness/scenario/timing/environment artifact, or no failure is present",
        },
    },
    "area": {
        "type": "choice",
        "instructions": "Which area does the excerpt most concern?",
        "criteria": {
            "scripting_lua": "Lua scripting, the gd.* API, console, or scripted test logic",
            "gameplay": "Fighters, enemies, items, stages, or match logic",
            "build_link": "Compilation, linking, objects, or the m-ex bridge",
            "input_pad": "Controllers, pad scripts, or input handling",
            "render_audio": "Rendering, audio, or presentation",
            "run_environment": "Run harness, scene setup, mods, paths, or environment",
        },
    },
    "severity": {
        "type": "score",
        "instructions": "How severe is the problem shown, for shipping the port?",
        "criteria": ["no problem shown", "noise only", "cosmetic or minor", "blocks the feature under test", "crashes or corrupts the run"],
    },
}


def tail_text(p: Path, n: int = 12_000_000) -> str:
    size = p.stat().st_size
    with open(p, "rb") as f:
        if size > n:
            f.seek(size - n)
        return f.read().decode("utf-8", "replace")


def excerpt(p: Path) -> str:
    lines = [l.strip() for l in tail_text(p).splitlines() if l.strip()]
    kept = [l for l in lines if KEEP.search(l) and not DROP.search(l)][-12:]
    final = [l for l in lines[-500:] if re.search(r"melee-pc: exit|alive at end", l) and not DROP.search(l)][-2:]
    out, seen = [], set()
    for l in kept + final:
        if l not in seen and len(l) <= 400:
            seen.add(l)
            out.append(l)
    return "\n".join(out)[-1800:]


def ask(key: str, state: dict) -> dict:
    body = json.dumps({"state": state, "model": MODEL, "questions": QUESTIONS}).encode()
    req = urllib.request.Request(API, data=body, headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 529) and attempt < 3:
                time.sleep(2 ** attempt)
                continue
            raise
    raise RuntimeError("unreachable")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs_dir", type=Path)
    ap.add_argument("--pattern", default="melee-pc.log", help="log filename inside each run dir")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    key = os.environ.get("TYPESAFE_API_KEY")
    if not key:
        sys.exit("TYPESAFE_API_KEY is not set — source the workspace .env first: set -a; . ./.env; set +a")

    runs = sorted(p for p in args.runs_dir.iterdir() if p.is_dir() and (p / args.pattern).exists() and (p / args.pattern).stat().st_size > 0)
    if args.limit:
        runs = runs[: args.limit]
    if not runs:
        sys.exit(f"no run directories with {args.pattern} under {args.runs_dir}")

    results, tin, tout = {}, 0, 0
    print(f"{'run':16s} {'outcome':16s} conf  defect  {'area':16s} sev")
    for p in runs:
        ex = excerpt(p / args.pattern)
        resp = ask(key, {"run": p.name, "log_excerpt": ex})
        a = resp["answers"]
        tin += resp["usage"]["input_tokens"]
        tout += resp["usage"]["output_tokens"]
        r = {
            "outcome": a["outcome"]["choice"],
            "outcome_conf": round(a["outcome"]["confidence"], 3),
            "defect": round(a["defect"]["noul"], 3),
            "area": a["area"]["choice"],
            "area_conf": round(a["area"]["confidence"], 3),
            "severity": round(a["severity"]["score"], 2),
            "excerpt": ex,
        }
        results[p.name] = r
        print(f"{p.name:16s} {r['outcome']:16s} {r['outcome_conf']:.2f}  {r['defect']:.2f}    {r['area']:16s} {r['severity']:.2f}")

    (args.runs_dir / "jev-triage.json").write_text(json.dumps(results, indent=2))
    lines = [
        "# Jev triage — run logs",
        "",
        "| run | outcome | conf | defect? | area | severity |",
        "|---|---|---|---|---|---|",
    ]
    for name, r in sorted(results.items()):
        lines.append(f"| {name} | {r['outcome']} | {r['outcome_conf']:.2f} | {r['defect']:.2f} | {r['area']} | {r['severity']:.2f} |")
    lines += ["", f"{len(results)} calls, {tin:,} input / {tout:,} output tokens."]
    (args.runs_dir / "jev-triage.md").write_text("\n".join(lines) + "\n")
    print(f"\n{len(results)} calls · {tin:,} in / {tout:,} out tokens · wrote {args.runs_dir}/jev-triage.md")


if __name__ == "__main__":
    main()
