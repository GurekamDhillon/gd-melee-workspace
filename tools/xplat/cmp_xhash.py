#!/usr/bin/env python3
"""Compare two MELEE_XHASH_LOG csvs (frame,rb,mem,glob): the first divergent frame per column.

    cmp_xhash.py win.csv linux.csv [--cols rb,mem,glob]

Exit 0 if every shared frame agrees on the selected columns (default: all) and at least
--min-frames frames are shared, else 1.
"""
import argparse, csv, sys

def load(path):
    rows = {}
    with open(path, newline='') as f:
        for r in csv.DictReader(f):
            rows[int(r['frame'])] = r
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a'); ap.add_argument('b')
    ap.add_argument('--cols', default='rb,mem,glob')
    ap.add_argument('--min-frames', type=int, default=1)
    a = ap.parse_args()
    A, B = load(a.a), load(a.b)
    shared = sorted(A.keys() & B.keys())
    cols = a.cols.split(',')
    bad = 0
    print(f'{a.a}: {len(A)} frames, {a.b}: {len(B)} frames, shared {len(shared)}'
          + (f' ({shared[0]}..{shared[-1]})' if shared else ''))
    for c in cols:
        diffs = [f for f in shared if A[f][c] != B[f][c]]
        if diffs:
            bad += 1
            print(f'  {c:5s}: {len(diffs)} differing frame(s), first {diffs[0]} ({A[diffs[0]][c]} vs {B[diffs[0]][c]})')
        else:
            print(f'  {c:5s}: identical over {len(shared)} frames')
    ok = bad == 0 and len(shared) >= a.min_frames
    print('RESULT:', 'IDENTICAL' if ok else 'DIVERGED')
    return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(main())
