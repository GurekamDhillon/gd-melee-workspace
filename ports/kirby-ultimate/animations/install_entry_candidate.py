"""Stage the Ultimate Kirby 120-frame entry in a separate additive LAB mod.

The source is a previously validated 489-row Hammer mod.  This appends only
motion row 489, raises the additive m-ex animation count to 490, and adds one
Geno state.  Disc-derived data remains in the ignored output directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/mex_port"))
sys.path.insert(0, str(ROOT / "experiment/brawl-kirby/tools/anim"))
import mex_hsd  # noqa: E402
import figatree  # noqa: E402

ROW = 489
SYMBOL = "PlyKirby5K_Share_ACTION_UltimateEntry_figatree"


def repack(ar: mex_hsd.Archive, data: bytearray, relocs: set[int]) -> bytes:
    while len(data) % 4:
        data.append(0)
    ordered = sorted(relocs)
    body = bytes(data) + b"".join(struct.pack(">I", at) for at in ordered) + ar.raw[ar.o_public:]
    header = (struct.pack(">5I", 0x20 + len(body), len(data), len(ordered),
                          ar.nb_public, ar.nb_extern) + ar.raw[0x14:0x20])
    return header + body


def append_entry(fighter: bytes, animation: bytes, clip: bytes) -> tuple[bytes, bytes]:
    ar = mex_hsd.Archive(fighter)
    fd = ar.public("ftDataKirby")
    table, index = ar.u32(fd + 0xC), ar.u32(fd + 0x10)
    if (fd + 0xC not in ar.reloc_set or fd + 0x10 not in ar.reloc_set or
            table + ROW * 0x18 > ar.data_size or index + ROW * 2 > ar.data_size):
        raise ValueError("fighter does not contain the verified 489-row motion tables")
    parsed, tree = figatree.parse_archive(clip)
    if parsed != SYMBOL or tree["frames"] != 120 or len(tree["joints"]) != 46:
        raise ValueError("Entry clip must be 120 frames on Kirby's 46-joint skeleton")
    data, aj = bytearray(ar.data), bytearray(animation)
    relocs = set(ar.reloc_offsets)

    def append(raw: bytes | bytearray, alignment: int = 0x20) -> int:
        while len(data) % alignment:
            data.append(0)
        at = len(data)
        data.extend(raw)
        return at

    while len(aj) % 0x20:
        aj.append(0xFF)
    aj_at = len(aj)
    aj.extend(clip)
    sym_at = append(SYMBOL.encode("ascii") + b"\0", 1)
    # Stock Entry's ftcmd row 238 contains only End; its item/trophy work is
    # done by the generic host callback, which our dedicated route bypasses.
    source = table + 238 * 0x18
    words = list(struct.unpack_from(">6I", ar.data, source))
    if ar.u32(words[3]) != 0 or words[4] != 4:
        raise ValueError("stock Entry script template is no longer an empty End")
    words[:3] = [sym_at, aj_at, len(clip)]
    rows = bytearray(ar.data[table:table + ROW * 0x18])
    rows.extend(struct.pack(">6I", *words))
    new_table = append(rows)
    for at in ar.reloc_offsets:
        if table <= at < table + ROW * 0x18:
            relocs.add(new_table + at - table)
    for word in (0, 3, 4, 5):
        if word == 0 or source + 4 * word in ar.reloc_set:
            relocs.add(new_table + ROW * 0x18 + 4 * word)
    struct.pack_into(">I", data, fd + 0xC, new_table)

    indexes = bytearray(ar.data[index:index + ROW * 2])
    indexes.extend(ar.data[index + 238 * 2:index + 238 * 2 + 2])
    struct.pack_into(">I", data, fd + 0x10, append(indexes))
    result = repack(ar, data, relocs)
    loaded = mex_hsd.Archive(result)
    new_row = loaded.u32(loaded.public("ftDataKirby") + 0xC) + ROW * 0x18
    if loaded.u32(new_row + 4) != aj_at or loaded.u32(new_row + 8) != len(clip):
        raise ValueError("Entry row did not survive HSD archive round trip")
    return result, bytes(aj)


def raise_mxdt_count(raw: bytes) -> bytes:
    ar = mex_hsd.Archive(raw)
    data = bytearray(ar.data)
    root = ar.public("mexData")
    fighter = ar.u32(root + 8)
    counts = ar.u32(fighter + 8 * 4)
    field = counts + 8 * 59 + 4  # additive Kirby is internal fighter 59
    if ar.u32(field) != 489:
        raise ValueError("m-ex additive Kirby count is not the expected 489")
    struct.pack_into(">I", data, field, 490)
    return repack(ar, data, set(ar.reloc_offsets))


def install(source: Path, entry_manifest: Path, out: Path) -> dict:
    if out.exists():
        raise ValueError("Entry output must be a new directory")
    entry = json.loads(entry_manifest.read_text(encoding="utf-8"))["animations"][0]
    clip = (entry_manifest.parent / entry["file"]).read_bytes()
    if entry["row"] != ROW or entry["symbol"] != SYMBOL or hashlib.sha256(clip).hexdigest() != entry["sha256"]:
        raise ValueError("Entry source manifest/clip mismatch")
    shutil.copytree(source, out)
    files = out / "files"
    fighter_path, aj_path, mxdt_path = (files / name for name in ("PlUk.dat", "PlUkAJ.dat", "MxDt.dat"))
    fighter, aj = append_entry(fighter_path.read_bytes(), aj_path.read_bytes(), clip)
    fighter_path.write_bytes(fighter)
    aj_path.write_bytes(aj)
    mxdt_path.write_bytes(raise_mxdt_count(mxdt_path.read_bytes()))
    profile_path = out / "geno.json"
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    states = profile["fighters"][0]["states"]
    if len(states) != 7 or states[6]["name"] != "HammerWalk":
        raise ValueError("Entry state index 7 is not free")
    states.append({"name": "UltimateEntry", "behavior": "geno.ground",
                   "subaction": ROW, "like": "motion:323", "next": "auto",
                   "anim": "ultimate.entry", "iasa": "none", "phys": "none",
                   "coll": "ultimate.entry"})
    profile_path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
    report = {"row": ROW, "symbol": SYMBOL, "frames": 120,
              "clip_sha256": hashlib.sha256(clip).hexdigest(),
              "fighter_sha256": hashlib.sha256(fighter).hexdigest(),
              "animation_sha256": hashlib.sha256(aj).hexdigest(),
              "mxdt_sha256": hashlib.sha256(mxdt_path.read_bytes()).hexdigest()}
    (out / "ultimate-entry.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--entry", type=Path, default=ROOT / "_build/tmp/ultimate-kirby-entry-clip/install-manifest.json")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(install(args.source, args.entry, args.out), indent=2))


if __name__ == "__main__":
    main()
