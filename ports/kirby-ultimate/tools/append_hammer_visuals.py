#!/usr/bin/env python3
"""Append ten converted Ultimate Hammer clips to an isolated Kirby source mod.

The original 479 motion rows and their ftcmd scripts remain byte-for-byte intact.
New rows use the existing safe hold or charged-release scripts as templates. The
additive m-ex packer reads hammer-visuals.json to raise only PlUk's animation
count to 489. This tool does not install extracted game assets in the repository.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

import build_side_b as side

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiment/brawl-kirby/tools/anim"))
import figatree  # noqa: E402

FIRST = 479
COUNT = 10
SCRIPT_TEMPLATE = {
    479: 4, 480: 4, 481: 5, 482: 4, 483: 18,
    484: 4, 485: 4, 486: 4, 487: 4, 488: 4,
}
NAMES = (
    "HammerHold", "HammerWalk", "HammerMax", "HammerAirStart",
    "HammerAirMax", "HammerStart", "HammerHoldMax", "HammerTurn",
    "HammerJump", "HammerJumpSquat",
)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def clips(manifest: Path) -> list[tuple[int, str, bytes, int]]:
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    entries = doc.get("animations")
    if not isinstance(entries, list) or [e.get("row") for e in entries] != list(range(FIRST, FIRST + COUNT)):
        raise ValueError("Hammer manifest must contain ordered rows 479..488 exactly")
    result = []
    for entry, name in zip(entries, NAMES):
        row = entry["row"]
        raw = (manifest.parent / entry["file"]).read_bytes()
        symbol = f"PlyKirby5K_Share_ACTION_{name}_figatree"
        ar = side.mex_hsd.Archive(raw)
        parsed, tree = figatree.parse_archive(raw)
        if (entry.get("symbol") != symbol or ar.file_size != len(raw) or
                ar.nb_public != 1 or ar.publics[0][0] != symbol or parsed != symbol or
                len(tree["joints"]) != 46 or not 1 < tree["frames"] < 200 or
                sha(raw) != entry.get("sha256")):
            raise ValueError(f"Hammer row {row} is not the expected verified 46-joint clip")
        result.append((row, symbol, raw, tree["frames"]))
    return result


def append(fighter: bytes, animation: bytes,
           entries: list[tuple[int, str, bytes, int]]) -> tuple[bytes, bytes]:
    ar = side.mex_hsd.Archive(fighter)
    fd = ar.public("ftDataKirby")
    table = side.motion_table(ar)
    if fd + 0x10 not in ar.reloc_set or table + FIRST * 0x18 > ar.data_size:
        raise ValueError("Kirby needs its 479-row motion and index tables")
    index = ar.u32(fd + 0x10)
    if index + FIRST * 2 > ar.data_size:
        raise ValueError("Kirby motion index table is truncated")
    if [e[0] for e in entries] != list(range(FIRST, FIRST + COUNT)):
        raise ValueError("Hammer clip rows must be 479..488")
    data, aj = bytearray(ar.data), bytearray(animation)
    relocs = set(ar.reloc_offsets)

    def append_data(raw: bytes, alignment: int = 0x20) -> int:
        while len(data) % alignment:
            data.append(0)
        at = len(data)
        data.extend(raw)
        return at

    rows = bytearray(ar.data[table:table + FIRST * 0x18])
    indexes = bytearray(ar.data[index:index + FIRST * 2])
    for row, symbol, clip, _ in entries:
        template = SCRIPT_TEMPLATE[row]
        src = table + template * 0x18
        if src + 0x18 > ar.data_size or src + 0xC not in ar.reloc_set:
            raise ValueError(f"Hammer script template row {template} is invalid")
        while len(aj) % 0x20:
            aj.append(0xFF)
        aj_at = len(aj)
        aj.extend(clip)
        sym_at = append_data(symbol.encode("ascii") + b"\0", 1)
        original = list(struct.unpack_from(">6I", ar.data, src))
        original[0:3] = [sym_at, aj_at, len(clip)]
        rows.extend(struct.pack(">6I", *original))
        indexes.extend(ar.data[index + template * 2:index + template * 2 + 2])

    new_table = append_data(rows)
    for at in ar.reloc_offsets:
        if table <= at < table + FIRST * 0x18:
            relocs.add(new_table + at - table)
    for row in range(FIRST, FIRST + COUNT):
        src = table + SCRIPT_TEMPLATE[row] * 0x18
        dst = new_table + row * 0x18
        relocs.add(dst)
        for word in (3, 4, 5):
            if src + 4 * word in ar.reloc_set:
                relocs.add(dst + 4 * word)
    struct.pack_into(">I", data, fd + 0xC, new_table)
    new_index = append_data(indexes)
    struct.pack_into(">I", data, fd + 0x10, new_index)
    while len(data) % 4:
        data.append(0)
    ordered = sorted(relocs)
    body = bytes(data) + b"".join(struct.pack(">I", at) for at in ordered) + ar.raw[ar.o_public:]
    header = (struct.pack(">5I", 0x20 + len(body), len(data), len(ordered),
                          ar.nb_public, ar.nb_extern) + ar.raw[0x14:0x20])
    result = header + body
    check = side.mex_hsd.Archive(result)
    if check.u32(check.public("ftDataKirby") + 0xC) != new_table:
        raise ValueError("repacked Hammer motion table did not reload")
    return result, bytes(aj)


def update_profile(profile: dict) -> dict:
    fighters = profile.get("fighters")
    if not isinstance(fighters, list) or len(fighters) != 1:
        raise ValueError("Hammer visuals need one Kirby profile")
    states = fighters[0].get("states")
    if not isinstance(states, list) or [s.get("name") for s in states[:6]] != [
            "HammerHold", "HammerWeak", "HammerMax", "HammerHoldAir",
            "HammerWeakAir", "HammerMaxAir"]:
        raise ValueError("Hammer visuals need the six native Hammer states")
    if len(states) != 6:
        raise ValueError("Hammer visuals cannot overwrite other Geno states")
    states[0]["subaction"] = 479
    states[2]["subaction"] = 481
    states[3]["subaction"] = 482
    states[5]["subaction"] = 483
    states.append({"name": "HammerWalk", "behavior": "geno.hammer.hold",
                   "subaction": 480, "like": "motion:14", "next": "geno:HammerWeak",
                   "charged_next": "geno:HammerMax"})
    return profile


def install(mod: Path, manifest: Path) -> dict:
    if (mod / "hammer-visuals.json").exists():
        raise ValueError("Hammer visual rows are already installed")
    files = mod / "files"
    fighter_path, aj_path = files / "PlKb.dat", files / "PlKbAJ.dat"
    profile_path = mod / "geno.json"
    manifest_raw = manifest.read_bytes()
    entries = clips(manifest)
    fighter, aj = append(fighter_path.read_bytes(), aj_path.read_bytes(), entries)
    profile = update_profile(json.loads(profile_path.read_text(encoding="utf-8")))
    report = {"rows": list(range(FIRST, FIRST + COUNT)),
              "manifest_sha256": sha(manifest_raw),
              "fighter_sha256": sha(fighter), "animation_sha256": sha(aj),
              "motion_count": FIRST + COUNT}
    fighter_path.write_bytes(fighter)
    aj_path.write_bytes(aj)
    profile_path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
    (mod / "hammer-visuals.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mod", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(install(args.mod, args.manifest), indent=2))


if __name__ == "__main__":
    main()
