#!/usr/bin/env python3
"""First divergence per field between a replay and a (possibly still-growing) port trace.

    python tools/replay/first_div.py game.slp trace.csv [--from -123]

Unlike replay_compare.py this tolerates a trace whose last line is cut off (a run still going, or
one that crashed), compares floats at single precision (both sides are f32), and reports each
field's first divergence separately - action state, position, percent and stocks usually part
ways at different frames, and the earliest one is the bisect point.
"""
from __future__ import annotations

import argparse
import csv
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import slp  # noqa: E402


def f32(v: float) -> float:
    return struct.unpack("f", struct.pack("f", v))[0]


def post_velocities(path: Path) -> dict:
    """{(frame, player, follower): (air_x, air_y, kb_x, kb_y, ground_x)} from post-frame events
    that carry them (Slippi 3.5.0+)."""
    data = path.read_bytes()
    i = data.find(b"raw[$U#l")
    pos = i + 12
    n = data[pos + 1]
    sizes = {data[pos + 2 + k]: struct.unpack(">H", data[pos + 3 + k:pos + 5 + k])[0]
             for k in range(0, n - 1, 3)}
    c = pos + 1 + n
    out = {}
    while c < len(data):
        cmd = data[c]
        sz = sizes.get(cmd)
        if sz is None:
            break
        if cmd == 0x38 and sz >= 0x48:
            b = data[c:c + 1 + sz]
            fr = struct.unpack(">i", b[1:5])[0]
            out[(fr, b[5], bool(b[6]))] = tuple(
                struct.unpack(">f", b[o:o + 4])[0] for o in (0x35, 0x39, 0x3D, 0x41, 0x45))
        c += 1 + sz
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("replay", type=Path)
    ap.add_argument("trace", type=Path)
    ap.add_argument("--from", dest="start", type=int, default=-123)
    args = ap.parse_args()
    rec = slp.parse(args.replay)
    rows = []
    with open(args.trace, newline="") as fh:
        for row in csv.reader(fh):
            if len(row) != 10 or row[0] == "frame":
                continue
            try:
                rows.append((int(row[0]), int(row[1]), row[2] == "1", int(row[3]), int(row[4]),
                             float(row[5]), float(row[6]), float(row[7]), float(row[8]),
                             int(row[9])))
            except ValueError:
                continue  # the cut-off last line
    first = {}
    last_frame = None
    for fr, p, fol, ch, act, x, y, face, pct, stk in rows:
        if fr < args.start:
            continue
        last_frame = fr
        o = rec.post.get(fr, {}).get((p, fol))
        if o is None:
            continue
        port = {"action_state": act, "x": f32(x), "y": f32(y), "facing": f32(face),
                "percent": f32(pct), "stocks": stk}
        for field, pv in port.items():
            ov = getattr(o, field)
            if field not in first and ov != pv:
                first[field] = (fr, p, ov, pv)
    # velocities (Slippi 3.5+ post-frame 0x35..0x48) against <trace>.vel.csv, when both exist
    vel_path = Path(str(args.trace) + ".vel.csv")
    if vel_path.exists():
        post_vel = post_velocities(args.replay)
        names = ("air_x", "air_y", "kb_x", "kb_y", "ground_x")
        with open(vel_path, newline="") as fh:
            for row in csv.reader(fh):
                if len(row) != 8 or row[0] == "frame":
                    continue
                try:
                    key = (int(row[0]), int(row[1]), row[2] == "1")
                    vals = [f32(float(v)) for v in row[3:]]
                except ValueError:
                    continue
                if key[0] < args.start or key not in post_vel:
                    continue
                for j, nm in enumerate(names):
                    if nm not in first and post_vel[key][j] != vals[j]:
                        first[nm] = (key[0], key[1], post_vel[key][j], vals[j])
    print(f"port trace through frame {last_frame} (replay {rec.first_frame}..{rec.last_frame})")
    if not first:
        print("no divergence on any field")
        return 0
    for field, (fr, p, ov, pv) in sorted(first.items(), key=lambda kv: kv[1][0]):
        print(f"  {field:<13} frame {fr:>6}  player {p}: console {ov!r} port {pv!r}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
