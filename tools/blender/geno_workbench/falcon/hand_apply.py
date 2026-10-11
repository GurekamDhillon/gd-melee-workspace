"""Hand-animated retail Falcon clips: hand file -> figatree archives appended to the package's animation bank.

Falcon's animations are retail figatrees inside the package's bank file (GnFalconAJ.dat, a local, disc-derived copy). A hand clip
replaces the rotation (and translation) tracks of the joints the artist moved and keeps every other track of the retail clip
byte for byte. The rebuilt clip is appended to the end of the bank and the plan's bank entry for that clip is pointed at it, so
nothing already in the bank moves and the rebuild is repeatable: it always starts from the pristine bank length recorded in the
plan (plan["bank"]["bytes"] before this step) and truncates what a previous rebuild appended.

The hand file lives in the (local, generated) project: <project>/anim/hand.json. For retail rigs hand_bake stores the final pose of
the moved bones under "abs" (rotations are in the joint-local frame the figatree uses: measured identical to the Blender export
for Falcon, joint for joint), which is what this module encodes. Nothing here is committed; the file contains retail-derived values.

    apply_hand(project_dir, package_files_dir, plan) -> report (a list of dicts); mutates plan["bank"] in place
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[4]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.geno.artist.blender import hand_layer as HL  # noqa: E402
from tools.geno.artist.model import AF  # noqa: E402  (figatree encoder: AF.F, AF._unwrap_euler, AF._encode_channel, AF.FRAC_ROT)

ROT_TYPES = (1, 2, 3)
LOC_TYPES = (5, 6, 7)
HAND_FILE = "anim/hand.json"


def parse_raw(raw):
    """Archive bytes -> (symbol, tree_type, flags, frames, joints) where joints is a list of lists of dict(ty, body, fv, fs, start)."""
    fsz, dsz, nrel, npub, next_ = struct.unpack_from(">5I", raw, 0)
    data = raw[0x20:0x20 + dsz]
    po = 0x20 + dsz + nrel * 4
    doff, soff = struct.unpack_from(">2I", raw, po)
    so = po + npub * 8 + next_ * 8 + soff
    symbol = raw[so:raw.index(b"\0", so)].decode()
    typ, flags, frames, nodes, tracks = struct.unpack_from(">IIfII", data, doff)
    counts, p = [], nodes
    while data[p] != 0xFF:
        counts.append(data[p])
        p += 1
    joints, ti = [], 0
    for c in counts:
        tr = []
        for _ in range(c):
            e = tracks + ti * 12
            ti += 1
            ln, start, ty, fv, fs, ad = struct.unpack_from(">HHBBBxI", data, e)
            tr.append(dict(ty=ty, body=bytes(data[ad:ad + ln]), fv=fv, fs=fs, start=start))
        joints.append(tr)
    return symbol, typ, flags, frames, joints


def build_archive(symbol, frames, joints, tree_type=1, flags=0):
    """Like figatree.build_tree_archive but keeps each track's start frame (retail tracks can start late)."""
    data = bytearray()
    relocs = []

    def align(n):
        while len(data) % n:
            data.append(0)

    ads = []
    for tr in joints:
        for t in tr:
            ads.append(len(data))
            data += t["body"]
    align(4)
    tracks_off, i = len(data), 0
    for tr in joints:
        for t in tr:
            data += struct.pack(">HHBBBxI", len(t["body"]), t["start"], t["ty"], t["fv"], t["fs"], ads[i])
            relocs.append(tracks_off + i * 12 + 8)
            i += 1
    nodes_off = len(data)
    data += bytes(len(tr) for tr in joints) + b"\xff"
    align(4)
    tree_off = len(data)
    data += struct.pack(">IIfII", tree_type, flags, float(frames), nodes_off, tracks_off)
    relocs += [tree_off + 12, tree_off + 16]
    align(4)
    dsz = len(data)
    rel = b"".join(struct.pack(">I", r) for r in relocs)
    pub = struct.pack(">II", tree_off, 0)
    body = bytes(data) + rel + pub + symbol.encode() + b"\0"
    return struct.pack(">8I", 0x20 + len(body), dsz, len(relocs), 1, 0, 0, 0, 0) + body


def _fit(a, n):
    a = np.asarray(a, float)
    return a[:n] if len(a) >= n else np.concatenate([a, np.repeat(a[-1:], n - len(a), axis=0)])


def joint_index(bone):
    if not bone.startswith("JOBJ_"):
        raise ValueError(f"hand clip bone '{bone}' is not a Falcon JOBJ_<n> joint")
    return int(bone[5:])


def rebuild_clip(raw, clip):
    """Retail figatree archive + hand clip -> (new archive bytes, report dict)."""
    symbol, typ, flags, frames, joints = parse_raw(raw)
    n = int(round(frames)) + 1
    if "abs" not in clip:
        raise ValueError("this hand clip has no 'abs' poses: bake it from the Falcon rig (retail rigs store absolute poses)")
    replaced, notes = [], []
    if clip["frames"] != n:
        notes.append(f"authored {clip['frames']} frames, retail clip has {n}: {'last pose held' if clip['frames'] < n else 'cropped'}")
    for bone, ch in clip["abs"].items():
        ji = joint_index(bone)
        if ji >= len(joints):
            raise ValueError(f"{bone}: the retail clip has only {len(joints)} joints")
        if "rot" in ch:
            eul = AF._unwrap_euler(_fit(ch["rot"], n))
            new = []
            for k, ty in enumerate(ROT_TYPES):
                body, fv, fs = AF._encode_channel(eul[:, k], AF.FRAC_ROT)
                new.append(dict(ty=ty, body=body, fv=fv, fs=fs, start=0))
            _splice(joints[ji], ROT_TYPES, new)
        if "loc" in ch:
            v = _fit(ch["loc"], n)
            new = []
            for k, ty in enumerate(LOC_TYPES):
                body, fv, fs = AF._encode_channel(v[:, k], None)
                new.append(dict(ty=ty, body=body, fv=fv, fs=fs, start=0))
            _splice(joints[ji], LOC_TYPES, new)
        replaced.append(bone)
    return build_archive(symbol, frames, joints, typ, flags), {"replaced": sorted(replaced), "frames": n, "notes": notes}


def _splice(tracks, types, new):
    """Put `new` where the joint's old tracks of these types were (keeps the retail order), appending any that were absent."""
    slots = [i for i, t in enumerate(tracks) if t["ty"] in types]
    kept = [t for t in tracks if t["ty"] not in types]
    if not slots:
        tracks[:] = kept + new
        return
    first = slots[0]
    before = [t for i, t in enumerate(tracks) if i < first and t["ty"] not in types]
    after = [t for i, t in enumerate(tracks) if i > first and t["ty"] not in types]
    tracks[:] = before + new + after


def apply_hand(project, bank_path, plan):
    """Rewrite the bank file and plan["bank"] from <project>/anim/hand.json. With no hand file the bank is restored to its pristine length."""
    bank_path = Path(bank_path)
    hand_file = Path(project) / HAND_FILE
    if "bytes" not in plan.get("bank", {}) or not bank_path.is_file():
        if hand_file.is_file():
            raise ValueError("hand clips need the retail animation bank: this package has none (plan.bank / bank file missing)")
        return []                                   # a package without a bank (a test fixture) has nothing to restore
    pristine = int(plan["bank"]["bytes"])
    data = bank_path.read_bytes()
    if len(data) < pristine:
        raise ValueError(f"bank {bank_path.name} is shorter ({len(data)}) than the plan says ({pristine})")
    data = data[:pristine]
    hand = HL.load(hand_file)
    out, report = bytearray(data), []
    if hand:
        for row, clip in sorted(hand["clips"].items()):
            info = plan["bank"]["clips"].get(row)
            if info is None:
                report.append({"row": row, "skipped": "no retail clip of that name in the bank"})
                continue
            raw = data[info["offset"]:info["offset"] + info["bytes"]]
            new, rep = rebuild_clip(raw, clip)
            while len(out) % 0x20:
                out.append(0)
            plan["bank"]["clips"][row] = dict(info, offset=len(out), bytes=len(new))
            out += new
            report.append(dict(rep, row=row, bytes=len(new)))
    if len(out) != len(bank_path.read_bytes()) or bytes(out) != bank_path.read_bytes():
        tmp = bank_path.with_suffix(bank_path.suffix + ".tmp")
        tmp.write_bytes(bytes(out))
        tmp.replace(bank_path)                      # replace, never truncate: a running game may hold the old file
    plan["bank"]["bytes"] = len(out)
    plan["bank"]["pristine_bytes"] = pristine
    return report
