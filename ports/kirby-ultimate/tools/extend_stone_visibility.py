#!/usr/bin/env python3
"""Add Ultimate Kirby's sixth Stone visibility state to a Kirby fighter archive.

The paired costumes must have DObj 42 (high detail) and 43 (low detail).
Only model zero's state arrays in the high, low, and metal visibility lookups
are extended. The 479 existing motion rows and ftcmd pointers stay byte-identical.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/mex_port"))
from mex_hsd import Archive  # noqa: E402


def _pack(ar: Archive, data: bytearray, relocs: set[int]) -> bytes:
    entries = sorted(relocs)
    body = bytes(data) + b"".join(struct.pack(">I", at) for at in entries) + ar.raw[ar.o_public:]
    header = struct.pack(">5I", 0x20 + len(body), len(data), len(entries),
                         ar.nb_public, ar.nb_extern) + ar.raw[0x14:0x20]
    return header + body


def extend(fighter: bytes) -> bytes:
    ar = Archive(fighter)
    root = ar.public("ftDataKirby")
    parts = ar.u32(root + 8)
    if root + 8 not in ar.reloc_set or ar.u32(parts) != 2 or parts + 4 not in ar.reloc_set:
        raise ValueError("expected Kirby's two-model fighter visibility descriptor")
    table = ar.u32(parts + 4)
    expected = {
        0: (30, 42),    # normal high detail
        1: (41, 43),    # normal low detail
        3: (30, 42),    # metal high detail
    }
    data = bytearray(ar.data)
    relocs = set(ar.reloc_offsets)

    def append(payload: bytes, align: int = 4) -> int:
        while len(data) % align:
            data.append(0)
        offset = len(data)
        data.extend(payload)
        return offset

    for column, (old_last, extra_dobj) in expected.items():
        site = table + 4 * column
        if site not in ar.reloc_set:
            raise ValueError(f"missing Kirby visibility column {column}")
        lookup = ar.u32(site)
        count = ar.u32(lookup)
        states = ar.u32(lookup + 4)
        if count != 7 or lookup + 4 not in ar.reloc_set:
            raise ValueError(f"visibility column {column} is not the seven-state stock layout")
        old = ar.data[states:states + count * 8]
        if len(old) != count * 8 or states + (count - 1) * 8 + 4 not in ar.reloc_set:
            raise ValueError(f"visibility column {column} has a truncated state array")
        final_count = ar.u32(states + (count - 1) * 8)
        final_indices = ar.u32(states + (count - 1) * 8 + 4)
        if final_count != 1 or ar.data[final_indices] != old_last:
            raise ValueError(f"visibility column {column} has unexpected last Stone state")
        dobj_index = append(bytes((extra_dobj,)), 1)
        new_states = append(old + struct.pack(">II", 1, dobj_index))
        for state in range(count):
            old_ptr = states + state * 8 + 4
            if old_ptr in ar.reloc_set:
                relocs.add(new_states + state * 8 + 4)
        relocs.add(new_states + count * 8 + 4)
        struct.pack_into(">II", data, lookup, count + 1, new_states)

    result = _pack(ar, data, relocs)
    check = Archive(result)
    if check.public("ftDataKirby") != root:
        raise ValueError("fighter root moved unexpectedly")
    motion = ar.u32(root + 0xC)
    if result[0x20 + motion:0x20 + motion + 479 * 0x18] != fighter[
            0x20 + motion:0x20 + motion + 479 * 0x18]:
        raise ValueError("Stone visibility extension modified motion rows")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mod", type=Path, required=True,
                        help="isolated Kirby-source mod with files/PlKb.dat")
    args = parser.parse_args()
    path = args.mod / "files/PlKb.dat"
    before = path.read_bytes()
    after = extend(before)
    path.write_bytes(after)
    report = {
        "visibility_columns": {"high": 0, "low": 1, "metal": 3},
        "old_state_count": 7,
        "new_state_count": 8,
        "extra_dobjs": {"high": 42, "low": 43, "metal": 42},
        "fighter_sha256": hashlib.sha256(after).hexdigest(),
    }
    (args.mod / "stone-visibility.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    manifest = args.mod / "source-manifest.json"
    if manifest.exists():
        source = json.loads(manifest.read_text(encoding="utf-8"))
        source["stone_visibility"] = report
        manifest.write_text(json.dumps(source, indent=2, ensure_ascii=False) + "\n",
                            encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
