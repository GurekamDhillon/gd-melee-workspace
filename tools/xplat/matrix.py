#!/usr/bin/env python3
"""The cross-platform determinism matrix: scripted offline matches, each run on the Windows build and
on the Linux build (pair.py), digests compared per frame.

    matrix.py [--only NAME,...] [--frames N] [--list]

One line per scenario. Environment as pair.py (source env_win.sh first). Results of every scenario are
kept in <repo>/_build/xplat/<name>/ ; this prints a summary and exits 1 if any scenario diverged.
"""
import argparse, os, re, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))

# name, scene, seed, frames, extra pair.py args
SCENARIOS = [
    ('fox-marth-fd',    'mode=vs;at=match;p1=fox/c0/hu/stocks99;p2=marth/c0/hu/stocks99;stage=fd;time=0', 12345, 6000, []),
    ('falco-sheik-bf-items', 'mode=vs;at=match;p1=falco/c0/hu/stocks99;p2=sheik/c0/hu/stocks99;stage=bf;items=4;time=0', 777, 6000, []),
    ('peach-puff-ys',   'mode=vs;at=match;p1=peach/c0/hu/stocks99;p2=jigglypuff/c0/hu/stocks99;stage=ys;items=2;time=0', 31337, 6000, []),
    ('ganon-falcon-ps', 'mode=vs;at=match;p1=ganondorf/c0/hu/stocks99;p2=captain/c0/hu/stocks99;stage=ps;items=3;time=0', 4242, 6000, []),
    ('ics-link-fod',    'mode=vs;at=match;p1=iceclimbers/c0/hu/stocks99;p2=link/c0/hu/stocks99;stage=fod;time=0', 9001, 6000, []),
    ('four-dl',         'mode=vs;at=match;p1=fox/c0/hu/stocks99;p2=samus/c0/hu/stocks99;p3=yoshi/c0/hu/stocks99;p4=mewtwo/c0/hu/stocks99;stage=dl;items=3;time=0', 555, 6000, ['--ports', '4']),
    ('turbo-fox-marth', 'mode=vs;at=match;p1=fox/c0/hu/stocks99;p2=marth/c0/hu/stocks99;stage=fd;turbo=on;time=0', 99, 6000, []),
    ('turbo-off-ys',    'mode=vs;at=match;p1=falcon/c0/hu/stocks99;p2=kirby/c0/hu/stocks99;stage=ys;turbo=off;time=0', 100, 4000, []),
    ('brinstar-gw-ness', 'mode=vs;at=match;p1=gamewatch/c0/hu/stocks99;p2=ness/c0/hu/stocks99;stage=brinstar;items=2;time=0', 2024, 6000, []),
    ('ace-fox-marth',   'mode=vs;at=match;p1=fox/c0/hu/stocks99;p2=marth/c0/hu/stocks99;stage=fd;time=0', 8, 4000, ['--disc', 'ace']),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default='')
    ap.add_argument('--frames', type=int, default=0)
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--prefix', default='m_')
    ap.add_argument('--pair-args', default='', help='extra pair.py args for every scenario')
    a = ap.parse_args()
    want = set(a.only.split(',')) if a.only else None
    bad = 0
    rows = []
    for name, scene, seed, frames, extra in SCENARIOS:
        if want and name not in want:
            continue
        if a.list:
            print(name, seed, frames, scene)
            continue
        if a.frames:
            frames = a.frames
        cmd = [sys.executable, os.path.join(HERE, 'pair.py'), a.prefix + name, str(frames), str(seed), scene] + extra + a.pair_args.split()
        t0 = time.time()
        r = subprocess.run(cmd, capture_output=True, text=True)
        out = r.stdout + r.stderr
        cols = dict(re.findall(r'^\s+(rb|wide|mem|glob)\s*:\s*(.*)$', out, re.M))
        res = 'IDENTICAL' if 'RESULT: IDENTICAL' in out else 'DIVERGED/ERROR'
        shared = re.search(r'shared (\d+)', out)
        rows.append((name, shared.group(1) if shared else '?', cols, res, time.time() - t0))
        print('%-24s frames %-6s rb:%s wide:%s mem:%s %s (%.0f s)' % (
            name, shared.group(1) if shared else '?', cols.get('rb', '?')[:14], cols.get('wide', '?')[:14],
            cols.get('mem', '?')[:30], res, time.time() - t0), flush=True)
        if 'rb' not in cols or cols['rb'].startswith(('0 ', '1 ', '2 ')) or 'differing' in cols.get('rb', '') or 'differing' in cols.get('wide', ''):
            bad += 1
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
