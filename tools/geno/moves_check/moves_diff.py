#!/usr/bin/env python3
"""moves_diff.py - compare two moves_check runs record by record (the old m-ex port against its define).

    python tools/geno/moves_check/moves_diff.py <old melee-pc.log> <new melee-pc.log> [--json out.json] [--tol 0.002]

Both logs hold `MOVECHK {json}` lines (moves_check.lua / moves_check_sora.lua). The records are joined by move name and compared field
by field: the motion names seen, the live hitbox window, every hitbox group (bone, damage, angle, growth, base knockback, size, first
and last live action frame), whether the move connected, the damage dealt, the launch vector, the victim's state, the landing lag, a
counter's cases, and every article (first frame, life, start offset, speed) with the damage it does standing 10 and 24 units away.
`place` (an absolute position) is not compared. A float matches within --tol (relative 0.2 percent by default, 0.005 absolute).
Exit 0: every record in both logs is identical; 1: at least one difference or a move missing from one log.
"""
import argparse
import json
import re
import sys

SKIP = {"place"}


def load(path):
    recs = {}
    fighter = None
    parts = {}
    done = None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if "MOVECHK FAIL" in line:
                raise ValueError(f"{path}: scenario failed: {line.strip()}")
            completion = re.search(r"MOVECHK DONE (\d+)", line)
            if completion:
                if done is not None:
                    raise ValueError(f"{path}: multiple completion markers")
                done = int(completion.group(1))
            pm = re.search(r"MOVECHKPART (\S+) (\d+) (\d+) (.*)$", line)
            if pm:
                parts.setdefault(pm.group(1), {})[int(pm.group(2))] = pm.group(4).rstrip(chr(13) + chr(10))
                if len(parts[pm.group(1)]) == int(pm.group(3)):
                    r = json.loads("".join(parts[pm.group(1)][i] for i in range(1, int(pm.group(3)) + 1)))
                    recs[r["name"]] = r
                    del parts[pm.group(1)]
                continue
            m = re.search(r"MOVECHK (FIGHTER|DONE|FAIL|START)?\s*(\{.*\})?", line)
            if not m or "MOVECHK" not in line:
                continue
            if m.group(1) == "FIGHTER" and m.group(2):
                fighter = json.loads(m.group(2))
            elif m.group(1) is None and m.group(2):
                r = json.loads(m.group(2))
                recs[r["name"]] = r
    if not recs or done != len(recs) or parts:
        raise ValueError(f"{path}: incomplete run (records={len(recs)}, DONE={done}, unfinished parts={len(parts)})")
    return recs, fighter


def same(a, b, tol, path, out):
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            if k in SKIP:
                continue
            if k not in a:
                out.append("%s.%s: only in new (%s)" % (path, k, json.dumps(b[k])[:80]))
            elif k not in b:
                out.append("%s.%s: only in old (%s)" % (path, k, json.dumps(a[k])[:80]))
            else:
                same(a[k], b[k], tol, "%s.%s" % (path, k), out)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            out.append("%s: length %d vs %d (%s | %s)" % (path, len(a), len(b), json.dumps(a)[:80], json.dumps(b)[:80]))
        for i, (x, y) in enumerate(zip(a, b)):
            same(x, y, tol, "%s[%d]" % (path, i), out)
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool) and not isinstance(b, bool):
        if abs(a - b) > max(0.005, tol * max(abs(a), abs(b))):
            out.append("%s: %s vs %s" % (path, a, b))
    elif a != b:
        out.append("%s: %s vs %s" % (path, json.dumps(a)[:80], json.dumps(b)[:80]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old")
    ap.add_argument("new")
    ap.add_argument("--json")
    ap.add_argument("--tol", type=float, default=0.002)
    a = ap.parse_args()
    try:
        old, fo = load(a.old)
        new, fn = load(a.new)
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        return 1
    names = list(old) + [n for n in new if n not in old]
    bad = 0
    report = {}
    for n in names:
        if n not in old or n not in new:
            print("%-16s MISSING in %s" % (n, "old" if n not in old else "new"))
            bad += 1
            report[n] = ["missing in " + ("old" if n not in old else "new")]
            continue
        d = []
        same(old[n], new[n], a.tol, n, d)
        report[n] = d
        if d:
            bad += 1
            print("%-16s DIFF (%d)" % (n, len(d)))
            for x in d[:12]:
                print("    " + x)
        else:
            print("%-16s same" % n)
    print("moves compared: %d, identical: %d, different or missing: %d" % (len(names), len(names) - bad, bad))
    if fo and fn:
        ao, an = fo.get("attrs") or {}, fn.get("attrs") or {}
        ks = sorted(k for k in set(ao) & set(an) if isinstance(ao[k], (int, float)) and abs(ao[k] - an[k]) > max(0.005, a.tol * abs(ao[k])))
        print("attributes read back (gd.attrs): %d shared, %d differ%s" % (len(set(ao) & set(an)), len(ks),
              (": " + ", ".join("%s %s->%s" % (k, ao[k], an[k]) for k in ks[:20])) if ks else ""))
    if a.json:
        json.dump(report, open(a.json, "w"), indent=1)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
