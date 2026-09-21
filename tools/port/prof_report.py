#!/usr/bin/env python3
"""Resolve a MELEE_PROFILE_SAMPLE run's melee-pc.samples into a flat function profile.

    MELEE_PROFILE_SAMPLE=15 tools/port/run.sh prof ...     # sample from 15 s in
    python tools/port/prof_report.py _build/runs/prof/melee-pc.samples [--map melee-pc.map] [-n 40]

The samples file is `count module offset` per distinct EIP (see gw_sample_thread in shim_vi.c).
Offsets in melee-pc.exe resolve to the enclosing function of the link map (the one next to the
samples file by default, which run.sh copies alongside the exe). Other modules are reported
per module. "idle" is time the frame thread spent parked in the OS (frame pacing's Sleep and the
render worker hand-off) - it is shown but excluded from the "busy" percentages.
"""
import argparse
import bisect
import collections
import os
import re

IDLE_MODULES = {"ntdll.dll", "KERNELBASE.dll", "kernel32.dll", "win32u.dll"}


def load_map(path):
    base = 0x400000
    syms = []
    pat = re.compile(r"^\s*[0-9a-f]{4}:[0-9a-f]{8}\s+(\S+)\s+([0-9a-f]{8})\s+f?\s*\S*", re.I)
    for line in open(path, encoding="latin-1"):
        m = re.search(r"Preferred load address is ([0-9a-f]+)", line, re.I)
        if m:
            base = int(m.group(1), 16)
            continue
        m = pat.match(line)
        if m and " f " in line:
            syms.append((int(m.group(2), 16) - base, m.group(1)))
    syms.sort()
    return [a for a, _ in syms], [n for _, n in syms]


def resolve(mod, off, addrs, names):
    if mod.lower() == "melee-pc.exe":
        i = bisect.bisect_right(addrs, off) - 1
        return names[i] if i >= 0 else "?"
    return "[%s]" % mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("samples")
    ap.add_argument("--map")
    ap.add_argument("-n", type=int, default=25)
    ap.add_argument("--min-busy", type=float, default=2.0,
                    help="skip threads busy less than this %% of their samples")
    args = ap.parse_args()
    mp = args.map or os.path.join(os.path.dirname(args.samples), "melee-pc.map")
    addrs, names = load_map(mp)

    tids = {}
    rows = collections.defaultdict(list)  # thread -> [(count, mod, off)]
    waits = collections.defaultdict(collections.Counter)  # thread -> {exe caller off: idle samples}
    for line in open(args.samples):
        if line.startswith("#"):
            m = re.match(r"# thread (\d+) tid (\d+) total (\d+)", line)
            if m:
                tids[int(m.group(1))] = int(m.group(2))
            continue
        parts = line.split()
        if len(parts) == 3:  # single-thread format
            parts = ["0"] + parts
        if len(parts) == 4:  # no caller column
            parts.append("0")
        t, count, mod, off, caller = parts
        rows[int(t)].append((int(count), mod, int(off, 16)))
        waits[int(t)][int(caller, 16)] += int(count) if mod in IDLE_MODULES else 0

    for t in sorted(rows):
        total = sum(c for c, _, _ in rows[t])
        idle = sum(c for c, m, _ in rows[t] if m in IDLE_MODULES)
        busy = total - idle
        pct = 100.0 * busy / max(1, total)
        if pct < args.min_busy:
            continue
        by_fn = collections.Counter()
        by_mod = collections.Counter()
        for c, mod, off in rows[t]:
            if mod in IDLE_MODULES:
                continue
            by_mod[mod] += c
            by_fn[resolve(mod, off, addrs, names)] += c
        label = "game (frame) thread" if t == 0 else "thread %d" % t
        print("\n==== %s  tid %s: %d samples, busy %.1f%%" % (label, tids.get(t, "?"), total, pct))
        print("  modules: " + ", ".join("%s %.1f%%" % (m, 100.0 * c / max(1, busy))
                                        for m, c in by_mod.most_common(6)))
        for fn, c in by_fn.most_common(args.n):
            print("  %6.2f%%  %7d  %s" % (100.0 * c / max(1, busy), c, fn))
        wait_fn = collections.Counter()
        for off, c in waits[t].items():
            if c:
                wait_fn[resolve("melee-pc.exe", off, addrs, names) if off else "(no exe caller)"] += c
        if wait_fn:
            print("  -- idle samples by nearest melee-pc.exe caller (%% of idle):")
            for fn, c in wait_fn.most_common(8):
                print("  %6.2f%%  %7d  %s" % (100.0 * c / max(1, idle), c, fn))


if __name__ == "__main__":
    main()
