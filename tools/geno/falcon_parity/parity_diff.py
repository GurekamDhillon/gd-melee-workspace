#!/usr/bin/env python3
"""parity_diff.py - compare two falcon_parity.lua traces (retail Falcon vs the standalone Geno Falcon).

    python tools/geno/falcon_parity/parity_diff.py <retail parity.txt> <geno parity.txt> [--max N] [--show NAME]

Per scenario: identical, or the first logic frame where a field differs (with both values) and how many frames differ. A scenario
only one run has is reported. Exit status 0 when every scenario of both runs is identical, 1 otherwise.
"""
import argparse
import re
import sys
from collections import OrderedDict

FIELDS = ["motion", "action_frame", "anim_frame", "x", "y", "vx", "vy", "ground_vel", "facing", "percent", "hitlag", "hitstun",
          "kb_vx", "kb_vy", "shield", "scale", "jumps_used", "intangible", "invincible", "body_state"]


def parse(path):
    sc = OrderedDict()
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n")
        if line.startswith("PF "):
            _, name, n, rest = line.split(" ", 3)
            assert rest.startswith("| ")
            sc.setdefault(name, []).append(rest[2:])
    return sc


def side(text):
    """one fighter's field text -> dict"""
    rng = None
    if text.startswith("R"):
        rng, text = text.split(" ", 1)
    m = re.match(r"(.*?) HB\[(.*?)\] H([0-9a-f]{8})(.*)$", text)
    head, hb, hh, tail = m.groups()
    toks = head.split(" ")
    d = dict(zip(FIELDS, toks))
    d["hitboxes"] = hb
    d["hurt_hash"] = hh
    d["detail"] = tail
    if rng is not None:
        d["rng"] = rng[1:]
    return d


def compare(a, b):
    """list of (frame index, fighter, field, a value, b value) for every differing field"""
    out = []
    for i, (la, lb) in enumerate(zip(a, b)):
        if la == lb:
            continue
        for who, ta, tb in zip(("P1", "P2"), la.split(" | "), lb.split(" | ")):
            if ta == tb:
                continue
            da, db = side(ta), side(tb)
            for k in list(da):
                if da[k] != db[k]:
                    out.append((i + 1, who, k, da[k], db[k]))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("retail")
    ap.add_argument("geno")
    ap.add_argument("--max", type=int, default=3, help="differing fields to show per scenario")
    ap.add_argument("--show", help="print every difference of one scenario")
    a = ap.parse_args()
    ra, rb = parse(a.retail), parse(a.geno)
    names = list(ra) + [n for n in rb if n not in ra]
    same = diff = 0
    for n in names:
        if n not in ra or n not in rb:
            print("ONLY-IN-%s  %s" % ("GENO" if n in rb else "RETAIL", n)); diff += 1; continue
        if len(ra[n]) != len(rb[n]):
            print("LENGTH      %-28s retail %d frames, geno %d" % (n, len(ra[n]), len(rb[n]))); diff += 1; continue
        d = compare(ra[n], rb[n])
        if not d:
            same += 1
            continue
        diff += 1
        frames = sorted({x[0] for x in d})
        print("DIFFERENT   %-28s first at frame %d, %d frame(s) differ" % (n, frames[0], len(frames)))
        for fr, who, k, va, vb in (d if a.show == n else d[:a.max]):
            print("              frame %-4d %s %-12s retail=%s  geno=%s" % (fr, who, k, va[:200], vb[:200]))
    print("identical %d / %d scenarios" % (same, len(names)))
    return 0 if diff == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
