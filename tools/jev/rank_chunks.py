#!/usr/bin/env python3
"""Rank short text chunks (research findings, options, claims) against a goal with Jev
(TypeSafe): one noul per chunk, one call.

Usage:
    set -a; . ./.env; set +a
    python3 tools/jev/rank_chunks.py --goal "Which findings should the map-editor bible load-bearing sections use?" \
        --chunks findings.tsv [--top N]

`findings.tsv` lines are `label<TAB>text` (`#` comments and blank lines ignored). The text is
the evidence the model judges - keep it a self-contained statement. Writes `rank_chunks.json` +
`rank_chunks.md` next to the chunks file.
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


def load_chunks(path: Path) -> list[tuple[str, str]]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "\t" in line:
            label, text = line.split("\t", 1)
        else:
            label, text = line, ""
        out.append((label.strip(), text.strip()))
    return out


def build_questions(goal: str, chunks: list[tuple[str, str]]) -> dict:
    q = {}
    for i, (label, text) in enumerate(chunks):
        q[f"chunk_{i:02d}"] = {
            "type": "noul",
            "instructions": (
                f"Goal: {goal}\n"
                f"Finding ({label}): {text}\n"
                "Does this finding materially inform or change the plan for the goal?"
            ),
            "criteria": {
                "true": "The finding bears directly on the goal and would change or support a concrete decision in it",
                "false": "The finding does not bear on the goal; including it would not change any decision",
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
    ap.add_argument("--goal", required=True)
    ap.add_argument("--chunks", required=True, type=Path)
    ap.add_argument("--top", type=int, default=0, help="print only the top N")
    args = ap.parse_args()

    key = os.environ.get("TYPESAFE_API_KEY")
    if not key:
        sys.exit("TYPESAFE_API_KEY is not set - source the workspace .env first: set -a; . ./.env; set +a")

    chunks = load_chunks(args.chunks)
    if not chunks:
        sys.exit("no chunks in " + str(args.chunks))

    questions = build_questions(args.goal, chunks)
    state = {"goal": args.goal, "chunks": {f"chunk_{i:02d}": t for i, (_, t) in enumerate(chunks)}}
    resp = ask(key, state, questions)

    scored = []
    for i, (label, text) in enumerate(chunks):
        a = resp["answers"][f"chunk_{i:02d}"]
        scored.append((a["noul"], label, text))
    scored.sort(reverse=True)
    if args.top:
        scored = scored[: args.top]

    print(f"\n{'noul':6s} finding")
    for noul, label, text in scored:
        print(f"{noul:5.3f}  {label:36s} {text[:90]}")
    print(f"\n{len(chunks)} chunks, 1 call · {resp['usage']['input_tokens']:,} in / {resp['usage']['output_tokens']:,} out tokens")

    out_json = args.chunks.with_name("rank_chunks.json")
    out_md = args.chunks.with_name("rank_chunks.md")
    out_json.write_text(json.dumps(
        {"goal": args.goal, "ranking": [{"label": l, "noul": n, "text": t} for n, l, t in scored]}, indent=2))
    lines = ["# Jev rank_chunks", "", f"Goal: {args.goal}", "", "| noul | finding | evidence |", "|---|---|---|"]
    for noul, label, text in scored:
        lines.append(f"| {noul:.3f} | {label} | {text} |")
    out_md.write_text("\n".join(lines) + "\n")
    print("wrote:", out_md)


if __name__ == "__main__":
    main()
