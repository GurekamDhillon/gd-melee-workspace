"""Inventory of every FrontendItem table the Atlas settings pages are checked against.

    python tools/port/settings_inventory.py --check | --table | --write
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
EXPECTED = os.path.join(HERE, "settings_inventory_expected.json")
FILES = ("gmfrontend_settings.inc", "gmfrontend_controls.inc", "gmfrontend.c")
TABLE = re.compile(r"static const FrontendItem (\w+)\[\] = \{(.*?)\n\};", re.S)
ROW = re.compile(r"^\s*\{\s*FE_(ACTION|CHOICE|SLIDER|TOGGLE)\s*,", re.M)


def scan():
    out = {}
    for name in FILES:
        text = open(os.path.join(GM, name), encoding="utf-8", errors="replace").read()
        for m in TABLE.finditer(text):
            kinds = ROW.findall(m.group(2))
            out[m.group(1)] = dict(file=name, rows=len(kinds), kinds={k: kinds.count(k) for k in sorted(set(kinds))})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true")
    g.add_argument("--table", action="store_true")
    g.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)
    now = scan()
    if a.table:
        for k, v in now.items():
            print("| %s | %s | %d | %s |" % (k, v["file"], v["rows"], v["kinds"]))
        return 0
    if a.write:
        with open(EXPECTED, "w", newline="\n") as f:
            json.dump(now, f, indent=1, sort_keys=True)
            f.write("\n")
        print("wrote %d tables" % len(now))
        return 0
    with open(EXPECTED) as f:
        expected = json.load(f)
    if now != expected:
        print("settings_inventory: a settings table changed; read the diff, update the plan's page tests, then --write")
        return 1
    print("settings_inventory: %d tables match" % len(now))
    return 0


if __name__ == "__main__":
    sys.exit(main())
