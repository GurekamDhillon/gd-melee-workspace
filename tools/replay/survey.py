#!/usr/bin/env python3
"""Summarise a folder of Slippi replays: versions, characters, stages, lengths, UCF toggles.

    python tools/replay/survey.py <folder> [--csv out.csv]

Reads only the Game Start event and the frame range, so it is fast on thousands of files. The
CSV (one row per replay) is what batch playback picks its runs from.
"""
from __future__ import annotations

import argparse
import collections
import csv
import struct
from pathlib import Path

# Melee external character ids (CSS order)
CHARS = ["Falcon", "DK", "Fox", "G&W", "Kirby", "Bowser", "Link", "Luigi", "Mario", "Marth",
         "Mewtwo", "Ness", "Peach", "Pikachu", "ICs", "Puff", "Samus", "Yoshi", "Zelda", "Sheik",
         "Falco", "YLink", "Doc", "Roy", "Pichu", "Ganon", "MH", "WireM", "WireF", "GBowser",
         "CH", "Sandbag", "Popo"]
STAGES = {2: "FoD", 3: "Stadium", 8: "Yoshi's", 28: "DL64", 31: "BF", 32: "FD"}


def game_start(path: Path):
    data = path.read_bytes()
    i = data.find(b"raw[$U#l")
    if i < 0:
        return None
    pos = i + 12
    if data[pos] != 0x35:
        return None
    n = data[pos + 1]
    sizes = {data[pos + 2 + k]: struct.unpack(">H", data[pos + 3 + k:pos + 5 + k])[0]
             for k in range(0, n - 1, 3)}
    c = pos + 1 + n
    info = None
    last = None
    while c < len(data):
        cmd = data[c]
        sz = sizes.get(cmd)
        if sz is None:
            break
        b = data[c:c + 1 + sz]
        if cmd == 0x36:
            info = b
        elif cmd == 0x38:
            last = struct.unpack(">i", b[1:5])[0]
        c += 1 + sz
    if info is None:
        return None
    gi = info[5:5 + 312]
    players = []
    for p in range(4):
        pl = gi[0x60 + 0x24 * p:0x60 + 0x24 * (p + 1)]
        if pl[1] != 3:
            players.append((p, pl[0], pl[1]))
    ucf = []
    if len(info) > 0x160:
        for p in range(4):
            dash = struct.unpack(">I", info[0x141 + 8 * p:0x145 + 8 * p])[0]
            shield = struct.unpack(">I", info[0x145 + 8 * p:0x149 + 8 * p])[0]
            ucf.append((dash, shield))
    return {
        "version": ".".join(str(x) for x in info[1:4]),
        "stage": struct.unpack(">H", gi[0x0E:0x10])[0],
        "players": players,
        "frames": last,
        "ucf": ucf,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder", type=Path)
    ap.add_argument("--csv", type=Path)
    args = ap.parse_args()
    files = sorted(args.folder.rglob("*.slp"))
    ver, stages, chars, ucf = (collections.Counter() for _ in range(4))
    rows = []
    bad = 0
    for f in files:
        try:
            g = game_start(f)
        except Exception:  # noqa: BLE001
            g = None
        if g is None:
            bad += 1
            continue
        ver[g["version"]] += 1
        stages[STAGES.get(g["stage"], g["stage"])] += 1
        for _, ck, _ in g["players"]:
            chars[CHARS[ck] if ck < len(CHARS) else ck] += 1
        ucf[str(sorted(set(g["ucf"])))] += 1
        rows.append([str(f), g["version"], g["stage"], len(g["players"]),
                     " ".join(str(ck) for _, ck, _ in g["players"]), g["frames"],
                     int(any(d or s for d, s in g["ucf"]))])
    print(f"{len(files)} files, {bad} unreadable")
    print("versions:", ver.most_common())
    print("stages:", stages.most_common())
    print("characters:", chars.most_common())
    print("ucf (dashback, shielddrop) sets:", ucf.most_common(5))
    lens = sorted(r[5] or 0 for r in rows)
    if lens:
        print("frames: min %d median %d max %d" % (lens[0], lens[len(lens) // 2], lens[-1]))
    if args.csv:
        with open(args.csv, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["path", "version", "stage", "nplayers", "chars", "last_frame", "ucf"])
            w.writerows(rows)


if __name__ == "__main__":
    main()
