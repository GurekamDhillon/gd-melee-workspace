#!/usr/bin/env python3
"""Derive MELEE_XHASH_SKIP ranges from dumps of a Windows and a Linux run: the MEM1 words that differ
(audio engine blocks, OS thread contexts), coalesced. Use once per scene to calibrate the 'mem' column;
anything that differs outside the ranges afterwards is NOT known-benign.

    xhash_skip.py dirA dirB FRAME [FRAME ...] [--gap 4096] [--pad 64]
"""
import argparse, os, sys

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a'); ap.add_argument('b'); ap.add_argument('frames', nargs='+', type=int)
    ap.add_argument('--gap', type=int, default=4096); ap.add_argument('--pad', type=int, default=64)
    a = ap.parse_args()
    diffs = []
    for f in a.frames:
        x = open(os.path.join(a.a, f'xh_{f}.mem1'), 'rb').read()
        y = open(os.path.join(a.b, f'xh_{f}.mem1'), 'rb').read()
        i = 0
        n = min(len(x), len(y))
        while i < n:
            if i % 4096 == 0 and x[i:i+4096] == y[i:i+4096]:
                i += 4096; continue
            if x[i:i+4] != y[i:i+4]:
                diffs.append(i)
            i += 4
    diffs = sorted(set(diffs))
    ranges = []
    for d in diffs:
        if ranges and d - ranges[-1][1] <= a.gap:
            ranges[-1][1] = d + 4
        else:
            ranges.append([d, d + 4])
    out = ','.join('%x-%x' % (0x80000000 + max(0, s - a.pad), 0x80000000 + e + a.pad) for s, e in ranges)
    print(len(diffs), 'differing words in', len(ranges), 'range(s)', file=sys.stderr)
    print(out)

if __name__ == '__main__':
    main()
