#!/usr/bin/env python3
"""Port-vs-port determinism: diff two runs of the same replay.

    python tools/replay/det_diff.py <runA>/trace.csv <runB>/trace.csv [--map melee-pc.map]

Compares trace.csv, trace.csv.vel.csv, trace.csv.seed.csv and trace.csv.rand.csv (each when both
exist) over the frames both runs reached, ignoring a cut-off last line, and reports the first
differing frame per file. For the RNG draw log it also prints the draws around the first split in
both runs, callers resolved against the map, so the consumer that differs is named.
"""
from __future__ import annotations

import argparse
import bisect
import re
import sys
from pathlib import Path


def rows(path: Path, ncols: int | None = None) -> list[list[str]]:
    out = []
    lines = path.read_text(errors="replace").splitlines()
    if lines and not lines[-1].strip():
        lines = lines[:-1]
    for ln in lines[:-1] if lines else []:  # the last line may be cut off
        parts = ln.split(",")
        if parts[0] in ("frame",) or (ncols and len(parts) != ncols):
            continue
        out.append(parts)
    return out


def load_map(path: Path):
    syms = []
    pat = re.compile(r"\s*[0-9a-f]{4}:[0-9a-f]{8}\s+(\S+)\s+([0-9a-f]{8})\s")
    for ln in path.read_text(errors="replace").splitlines():
        m = pat.match(ln)
        if m:
            syms.append((int(m.group(2), 16), m.group(1)))
    syms.sort()
    keys = [a for a, _ in syms]

    def name(addr: int) -> str:
        i = bisect.bisect_right(keys, addr) - 1
        return f"{syms[i][1]}+0x{addr - syms[i][0]:X}" if i >= 0 else f"0x{addr:08X}"

    return name


def first_split(a, b):
    """Rows keyed by (frame, rest-of-key); compare in order up to the shorter run's last frame."""
    last = min(int(a[-1][0]), int(b[-1][0])) if a and b else None
    a = [r for r in a if last is not None and int(r[0]) < last]
    b = [r for r in b if last is not None and int(r[0]) < last]
    for i, (x, y) in enumerate(zip(a, b)):
        if x != y:
            return i, x, y, last
    if len(a) != len(b):
        i = min(len(a), len(b))
        return i, a[i] if i < len(a) else None, b[i] if i < len(b) else None, last
    return None, None, None, last


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("a", type=Path)
    ap.add_argument("b", type=Path)
    ap.add_argument("--map", type=Path)
    args = ap.parse_args()
    mp = args.map or args.a.parent / "melee-pc.map"
    name = load_map(mp) if mp.exists() else (lambda x: f"0x{x:08X}")
    ok = True
    for suffix, ncols in (("", 10), (".vel.csv", 8), (".seed.csv", 2), (".rand.csv", 4)):
        pa, pb = Path(str(args.a) + suffix), Path(str(args.b) + suffix)
        if not (pa.exists() and pb.exists()):
            continue
        ra, rb = rows(pa, ncols), rows(pb, ncols)
        ra = [r for r in ra if int(r[0]) >= -123]
        rb = [r for r in rb if int(r[0]) >= -123]
        i, x, y, last = first_split(ra, rb)
        label = (suffix or "trace").lstrip(".")
        if i is None:
            print(f"{label:10} identical through frame {last}")
            continue
        ok = False
        print(f"{label:10} first differs at frame {x[0] if x else y[0]}: A {x} | B {y}")
        if suffix == ".rand.csv":
            for tag, rr in (("A", ra), ("B", rb)):
                print(f"  draws around the split in {tag}:")
                for r in rr[max(0, i - 3):i + 5]:
                    print(f"    f{r[0]:>6} {name(int(r[1], 16)):<48} seed {r[2]} global {r[3]}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
