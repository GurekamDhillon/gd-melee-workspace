#!/usr/bin/env python3
"""Rank a shortlist of files against a task with Jev (TypeSafe): one noul per candidate, one call.

Usage:
    set -a; . ./.env; set +a
    python3 tools/jev/rerank_files.py --task "finish X: fix A, rebuild, test B" \
        --candidates shortlist.tsv [--root DIR] [--top N]

`shortlist.tsv` lines are `path<TAB>description` (`#` comments and blank lines ignored). The
description is the evidence the model judges - make it factual (what the file is, one line).
Paths are checked against `--root` (default: cwd); missing files are skipped.
Writes `jev-rerank.json` + `jev-rerank.md` next to the candidates file.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-latest"


def load_candidates(path: Path) -> list[tuple[str, str]]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "\t" in line:
            p, desc = line.split("\t", 1)
        else:
            p, desc = line, ""
        out.append((p.strip(), desc.strip()))
    return out


def build_questions(task: str, cands: list[tuple[str, str]]) -> dict:
    q = {}
    for i, (path, desc) in enumerate(cands):
        q[f"cand_{i:02d}"] = {
            "type": "noul",
            "instructions": (
                f"Task: {task}\n"
                f"Candidate file: {path} - {desc}.\n"
                "Is this candidate file likely needed (to read or to edit) to finish the task?"
            ),
            "criteria": {
                "true": "The task's remaining work plausibly touches this file or needs its content",
                "false": "Not needed for the task; its content does not bear on the task",
            },
        }
    return q


def ask(key: str, state: dict, questions: dict) -> dict:
    body = json.dumps({"state": state, "model": MODEL, "questions": questions}).encode()
    req = urllib.request.Request(API, data=body, headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code in (429, 529) and attempt < 3:
                time.sleep(2 ** attempt)
                continue
            raise
    raise RuntimeError("unreachable")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task", required=True)
    ap.add_argument("--candidates", required=True, type=Path)
    ap.add_argument("--root", type=Path, default=Path.cwd())
    ap.add_argument("--top", type=int, default=0, help="print only the top N")
    args = ap.parse_args()

    key = os.environ.get("TYPESAFE_API_KEY")
    if not key:
        sys.exit("TYPESAFE_API_KEY is not set - source the workspace .env first: set -a; . ./.env; set +a")

    cands = load_candidates(args.candidates)
    kept, missing = [], []
    for p, d in cands:
        (kept if (args.root / p).exists() else missing).append((p, d))
    if missing:
        print("skipped (missing):", ", ".join(p for p, _ in missing))
    if not kept:
        sys.exit("no candidates exist under " + str(args.root))

    questions = build_questions(args.task, kept)
    state = {"task": args.task, "candidates": {f"cand_{i:02d}": f"{p} - {d}" for i, (p, d) in enumerate(kept)}}
    resp = ask(key, state, questions)

    scored = []
    for i, (path, desc) in enumerate(kept):
        a = resp["answers"][f"cand_{i:02d}"]
        scored.append((a["noul"], path, desc))
    scored.sort(reverse=True)
    if args.top:
        scored = scored[: args.top]

    print(f"\n{'noul':6s} file")
    for noul, path, desc in scored:
        print(f"{noul:5.3f}  {path:56s} {desc[:80]}")
    print(f"\n{len(kept)} candidates, 1 call · {resp['usage']['input_tokens']:,} in / {resp['usage']['output_tokens']:,} out tokens")

    out_json = args.candidates.with_name("jev-rerank.json")
    out_md = args.candidates.with_name("jev-rerank.md")
    out_json.write_text(json.dumps(
        {"task": args.task, "ranking": [{"file": p, "noul": n, "desc": d} for n, p, d in scored]}, indent=2))
    lines = ["# Jev rerank", "", f"Task: {args.task}", "", "| noul | file | why it might matter |", "|---|---|---|"]
    for noul, path, desc in scored:
        lines.append(f"| {noul:.3f} | {path} | {desc} |")
    out_md.write_text("\n".join(lines) + "\n")
    print("wrote:", out_md)


if __name__ == "__main__":
    main()
