#!/usr/bin/env python3
"""Diff two MELEE_XHASH_DUMP_FRAMES dumps (xh_<frame>.mem1 / .glob) from two platforms.

    xhash_diff.py dirA dirB FRAME [--max 60]

MEM1 is compared word by word (big-endian, as the game sees it) and the differing addresses are
grouped into runs; the globals are compared per symbol. Words that pointed into the image were
already masked by the game when it wrote the dump.
"""
import argparse, os, struct, sys

def read_glob(path):
    out = {}
    with open(path, 'rb') as f:
        data = f.read()
    i = 0
    while i + 4 <= len(data):
        (n,) = struct.unpack_from('<I', data, i); i += 4
        name = data[i:i+n].decode('latin1'); i += n
        (ln,) = struct.unpack_from('<I', data, i); i += 4
        out[name] = data[i:i+ln]; i += ln
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a'); ap.add_argument('b'); ap.add_argument('frame', type=int)
    ap.add_argument('--max', type=int, default=60)
    a = ap.parse_args()
    ma = open(os.path.join(a.a, f'xh_{a.frame}.mem1'), 'rb').read()
    mb = open(os.path.join(a.b, f'xh_{a.frame}.mem1'), 'rb').read()
    n = min(len(ma), len(mb))
    print(f'MEM1: {len(ma)} vs {len(mb)} bytes')
    runs = []
    i = 0
    while i < n:
        if ma[i:i+4096] == mb[i:i+4096] and i % 4096 == 0:
            i += 4096; continue
        if ma[i:i+4] != mb[i:i+4]:
            if runs and i - runs[-1][1] <= 16:
                runs[-1][1] = i + 4
            else:
                runs.append([i, i + 4])
        i += 4
    print(f'MEM1: {len(runs)} differing run(s)')
    for s, e in runs[:a.max]:
        print(f'  0x{0x80000000+s:08X}..0x{0x80000000+e:08X}  A={ma[s:e].hex()}  B={mb[s:e].hex()}' if e - s <= 32 else
              f'  0x{0x80000000+s:08X}..0x{0x80000000+e:08X}  ({e-s} bytes)')
    ga = read_glob(os.path.join(a.a, f'xh_{a.frame}.glob'))
    gb = read_glob(os.path.join(a.b, f'xh_{a.frame}.glob'))
    print(f'globals: {len(ga)} vs {len(gb)} symbols; only in A: {len(ga.keys()-gb.keys())}, only in B: {len(gb.keys()-ga.keys())}')
    bad = 0
    for k in sorted(ga.keys() & gb.keys()):
        x, y = ga[k], gb[k]
        m = min(len(x), len(y))
        if x[:m] != y[:m]:
            bad += 1
            if bad <= a.max:
                j = next(j for j in range(m) if x[j] != y[j])
                print(f'  {k}: len {len(x)} vs {len(y)}, first byte difference at +{j}: {x[j:j+8].hex()} vs {y[j:j+8].hex()}')
    print(f'globals: {bad} symbol(s) differ over their common length')
    return 0 if not runs and not bad else 1

if __name__ == '__main__':
    sys.exit(main())
