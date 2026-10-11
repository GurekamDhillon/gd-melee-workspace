"""Authored HSD fixtures only; no game/disc inputs."""
import importlib.util
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[4]
spec = importlib.util.spec_from_file_location("figatree_export_fixture", ROOT / "ports/ir/tools/figatree.py")
F = importlib.util.module_from_spec(spec)
spec.loader.exec_module(F)


def varint(n):
    out = bytearray()
    while n > 127:
        out.append((n & 127) | 128)
        n >>= 7
    return bytes(out) + bytes([n])


def stream(keys, fv=0, fs=0):
    """Independent fixture writer: one opcode packet per key."""
    def number(v, frac):
        kind, shift = frac >> 5, frac & 31
        return struct.pack(("<f", "<h", "<H", "<b", "<B")[kind],
                           v if kind == 0 else round(v * 2 ** shift))
    out = bytearray()
    for op, value, slope, wait in keys:
        out.append(op)
        if op != 5:
            out += number(value, fv)
        if op in (4, 5):
            out += number(slope, fs)
        if wait is not None:
            out += varint(wait)
    return bytes(out)


def archive(joints, frames=4, name="PlySynthetic_Share_ACTION_Test_figatree", starts=None):
    raw = bytearray(F.build_tree_archive(name, frames, joints))
    if starts:
        dsz, nrel = struct.unpack_from(">II", raw, 4)
        root = struct.unpack_from(">I", raw, 32 + dsz + nrel * 4)[0]
        tracks = struct.unpack_from(">I", raw, 32 + root + 16)[0]
        for track, start in starts.items():
            struct.pack_into(">h", raw, 32 + tracks + track * 12 + 2, start)
    return bytes(raw)


def bank(*archives):
    out = bytearray()
    for raw in archives:
        out += raw
        out += bytes((-len(out)) % 32)
    return bytes(out)


def model(joints):
    """[(parent, rot, translation, scale, flags)] -> tiny JOBJ DAT."""
    data = bytearray(len(joints) * 64)
    relocs = []
    # Offset zero is a valid relocated pointer, distinct from an unrelocated NULL.
    for i, (parent, rot, trans, scale, flags) in enumerate(joints):
        off = i * 64
        struct.pack_into(">I", data, off + 4, flags)
        struct.pack_into(">9f", data, off + 20, *rot, *scale, *trans)
        children = [j for j, joint in enumerate(joints) if joint[0] == i]
        if children:
            struct.pack_into(">I", data, off + 8, children[0] * 64)
            relocs.append(off + 8)
        siblings = [j for j, joint in enumerate(joints) if joint[0] == parent]
        pos = siblings.index(i)
        if pos + 1 < len(siblings):
            struct.pack_into(">I", data, off + 12, siblings[pos + 1] * 64)
            relocs.append(off + 12)
    tail = b"".join(struct.pack(">I", r) for r in relocs) + struct.pack(">II", 0, 0) + b"Synthetic_Share_joint\0"
    return struct.pack(">8I", 32 + len(data) + len(tail), len(data), len(relocs), 1, 0, 0, 0, 0) + data + tail
