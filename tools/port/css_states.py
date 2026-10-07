"""Audit of every character-select and stage-select state in the game sources.

    python tools/port/css_states.py --check     # compare with css_states_expected.json
    python tools/port/css_states.py --table     # Markdown rows for the plan and the retirement list
    python tools/port/css_states.py --write     # rewrite the expected file (a reviewed change only)

A state is a GameModeState initialiser whose scene block starts with GS_CSS or GS_SSS. For each we record the file, the
enter-data symbol, and the CSSMatchType the mode stores (the first number passed as the second argument of gm_801B06B0,
or an assignment to match_type, or 'VS' when the state shares gmVsMelee_CssData).
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
GAME = os.environ.get("GW_MELEE") or os.path.join(ROOT, "melee")
GM = os.path.join(GAME, "src", "melee", "gm")
EXPECTED = os.path.join(HERE, "css_states_expected.json")

SCENE = re.compile(r"\{\s*[\w-]+\s*,\s*\w+\s*,\s*\w+\s*,\s*(\w+)\s*,\s*(\w+)\s*,\s*\{\s*(GS_CSS|GS_SSS)\s*,\s*&?(\w+)\s*,", re.S)
MATCH = re.compile(r"gm_801B06B0\(\s*[^,]+,\s*(0x[0-9A-Fa-f]+|\d+)\s*[,U]")
ASSIGN = re.compile(r"match_type\s*=\s*(0x[0-9A-Fa-f]+|\d+)\s*;")


def scan():
    rows = []
    for name in sorted(os.listdir(GM)):
        if not name.endswith(".c") or name.startswith("gmfrontend"):
            continue
        path = os.path.join(GM, name)
        with open(path, encoding="utf-8", errors="replace") as f:
            text = f.read()
        if "GS_CSS" not in text and "GS_SSS" not in text:
            continue
        if name in ("gm_1A3F.c", "gmscdata.c"):          # a switch case and the scene table, not mode states
            continue
        found = SCENE.findall(text)
        if not found:
            continue
        mt = [int(m, 0) for m in MATCH.findall(text)] + [int(m, 0) for m in ASSIGN.findall(text)]
        for enter, exit_, kind, sym in found:
            rows.append(dict(file=name, scene=kind, data=sym, on_enter=enter, on_exit=exit_, match_types=sorted(set(mt))))
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--table", action="store_true")
    g.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    rows = scan()
    if a.table:
        print("| file | scene | enter data | on_enter | on_exit | match_type(s) |\n|---|---|---|---|---|---|")
        for r in rows:
            print("| %s | %s | %s | %s | %s | %s |" % (r["file"], r["scene"], r["data"], r["on_enter"], r["on_exit"], ", ".join("0x%X" % m for m in r["match_types"]) or "VS family"))
        return 0
    if a.write:
        with open(EXPECTED, "w", newline="\n") as f:
            json.dump(rows, f, indent=1, sort_keys=True)
            f.write("\n")
        print("wrote %d states" % len(rows))
        return 0
    with open(EXPECTED) as f:
        want = json.load(f)
    if rows != want:
        print("css_states: the game sources changed: %d states now, %d expected" % (len(rows), len(want)))
        return 1
    print("css_states: %d states match the expected file" % len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
