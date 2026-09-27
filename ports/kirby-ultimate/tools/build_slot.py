#!/usr/bin/env python3
"""Stage Ultimate Kirby in an explicitly chosen ACE m-ex fighter slot.

This builds a separate, unmounted mod. Every ACE slot is occupied once the
Brawl Kirby and Meta Knight ports are present; the caller must name the row
and the fighter it intentionally replaces. Source fighter files should already
have the movement, attack, and animation passes applied.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/mex_port"))
sys.path.insert(0, str(ROOT / "experiment/brawl-kirby/tools"))
from mex_hsd import Archive  # noqa: E402
import texanim_keys  # noqa: E402

COLORS = ("Nr", "Ye", "Bu", "Re", "Gr", "Wh", "Or", "Bk")
SOURCE_PL = "PlKb.dat"
TARGET_PL = "PlUk.dat"
TARGET_AJ = "PlUkAJ.dat"


def u32(data: bytes | bytearray, offset: int) -> int:
    return struct.unpack_from(">I", data, offset)[0]


def cstring(data: bytes | bytearray, offset: int) -> str:
    if offset <= 0 or offset >= len(data):
        raise ValueError(f"invalid string pointer 0x{offset:X}")
    return bytes(data[offset:data.index(0, offset)]).decode("ascii")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def row_info(raw: bytes, internal: int, external: int) -> tuple[str, str]:
    ar = Archive(raw)
    ft = ar.u32(ar.public("mexData") + 8)
    names = ar.u32(ft)
    pl = ar.u32(ft + 4)
    return cstring(ar.data, ar.u32(names + 4 * external)), cstring(ar.data, ar.u32(pl + 8 * internal))


def archive_bytes(ar: Archive, data: bytearray, relocations: set[int]) -> bytes:
    while len(data) % 4:
        data.append(0)
    rel = sorted(relocations)
    body = bytes(data) + b"".join(struct.pack(">I", offset) for offset in rel) + ar.raw[ar.o_public:]
    return (struct.pack(">5I", 0x20 + len(body), len(data), len(rel), ar.nb_public, ar.nb_extern)
            + ar.raw[0x14:0x20] + body)


def own_anim_and_costumes(raw: bytes, internal: int, external: int) -> bytes:
    """Give the Kirby clone its own AJ and eight costume files/symbols."""
    ar = Archive(raw)
    data = bytearray(ar.data)
    relocs = set(ar.reloc_offsets)
    ft = u32(data, ar.public("mexData") + 8)

    def append_string(value: str) -> int:
        at = len(data)
        data.extend(value.encode("ascii") + b"\0")
        return at

    anim = u32(data, ft + 0x1C)
    at = append_string(TARGET_AJ)
    struct.pack_into(">I", data, anim + 4 * internal, at)
    relocs.add(anim + 4 * internal)

    while len(data) % 4:
        data.append(0)
    rows = []
    for i, color in enumerate(COLORS):
        # Additional colours share a safe retail Kirby copy-hat visibility row.
        # The game-side Kirby copy-hat tables are six rows, even for an 8-costume m-ex fighter.
        stem = "PlyKirby5K" + (color if i in range(1, 6) else "") + "_Share"
        values = (append_string(f"PlUk{color}.dat"),
                  append_string(stem + "_joint"),
                  append_string(stem + "_matanim_joint"))
        rows.append((*values, i if i < 6 else i - 6))

    while len(data) % 4:
        data.append(0)
    table = len(data)
    for row in rows:
        at = len(data)
        data.extend(struct.pack(">4I", *row))
        relocs.update((at, at + 4, at + 8))
    cost = u32(data, ft + 0x14)
    struct.pack_into(">I", data, cost + 4 * internal, table)
    relocs.add(cost + 4 * internal)
    info = u32(data, ft + 0x10)
    data[info + 4 * external] = len(COLORS)
    result = archive_bytes(ar, data, relocs)
    check = Archive(result)
    check_ft = check.u32(check.public("mexData") + 8)
    check_table = check.u32(check.u32(check_ft + 0x14) + 4 * internal)
    assert check.data[check.u32(check_ft + 0x10) + 4 * external] == 8
    assert all(cstring(check.data, check.u32(check_table + 16 * i)) == f"PlUk{color}.dat"
               for i, color in enumerate(COLORS))
    return result


def extra_color_ui(files: Path, internal: int, external: int) -> None:
    """Give c06/c07 valid portrait and stock placeholders keyed in m-ex's UI atlases."""
    path = files / "MnSlChr.usd"
    ar = Archive(path.read_bytes())
    data = bytearray(ar.data)
    select = ar.public("mexSelectChr")
    stride = u32(data, select + 0x10)
    csp = u32(data, u32(data, select + 0xC) + 8)
    texanim_keys.copy_frames(data, csp, [(external + 6 * stride, 4),
                                          (external + 7 * stride, 4 + stride)])
    path.write_bytes(archive_bytes(ar, data, set(ar.reloc_offsets)))

    path = files / "IfAll.usd"
    ar = Archive(path.read_bytes())
    data = bytearray(ar.data)
    stc = ar.public("Stc_icns")
    reserved, stride = struct.unpack_from(">HH", data, stc)
    stock = u32(data, u32(data, u32(data, stc + 4) + 8) + 8)
    texanim_keys.copy_frames(data, stock,
                             [(reserved + 6 * stride + internal, reserved + 4),
                              (reserved + 7 * stride + internal, reserved + stride + 4)])
    path.write_bytes(archive_bytes(ar, data, set(ar.reloc_offsets)))


def parse_costumes(specs: list[str]) -> list[Path]:
    chosen: dict[int, Path] = {}
    for spec in specs:
        index, sep, path = spec.partition(":")
        if not sep or not index.isdecimal() or int(index) not in range(8):
            raise ValueError(f"costume must be INDEX:PATH (0..7): {spec}")
        if int(index) in chosen:
            raise ValueError(f"duplicate costume {index}")
        chosen[int(index)] = Path(path)
    if set(chosen) != set(range(8)):
        raise ValueError(f"all eight costumes required, missing {sorted(set(range(8)) - set(chosen))}")
    for index, path in chosen.items():
        raw = path.read_bytes()
        ar = Archive(raw)
        color = COLORS[index]
        stem = "PlyKirby5K" + (color if index in range(1, 6) else "") + "_Share"
        symbols = {name for name, _ in ar.publics}
        if {stem + "_joint", stem + "_matanim_joint"} - symbols:
            raise ValueError(f"costume {index} lacks the expected Kirby joint symbols: {path}")
    return [chosen[i] for i in range(8)]


def build(source_mod: Path, base_files: Path, output: Path, internal: int,
          external: int, expected_name: str, name: str, costumes: list[Path]) -> dict:
    if not 0 <= internal < 65 or not 0 <= external < 65:
        raise ValueError("m-ex internal and external row ids must be in 0..64")
    if (internal, external) in ((4, 4), (34, 33), (52, 51)):
        raise ValueError("destination would overwrite Kirby, Brawl Kirby, or Meta Knight")
    before_name, before_pl = row_info((base_files / "MxDt.dat").read_bytes(), internal, external)
    if before_name != expected_name:
        raise ValueError(f"destination {internal}/{external} is {before_name!r}, not {expected_name!r}")
    files = source_mod / "files"
    pl = (files / SOURCE_PL).read_bytes()
    aj = (files / "PlKbAJ.dat").read_bytes()
    Archive(pl).public("ftDataKirby")
    if not aj:
        raise ValueError("source mod has an empty PlKbAJ.dat")
    if output.resolve() == source_mod.resolve():
        raise ValueError("slot output must differ from source mod")
    if output.exists() and any(output.iterdir()):
        raise ValueError("slot output must be a new or empty directory")

    target_files = output / "files"
    target_files.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(files / SOURCE_PL, target_files / TARGET_PL)
    shutil.copyfile(files / "PlKbAJ.dat", target_files / TARGET_AJ)
    for index, path in enumerate(costumes):
        shutil.copyfile(path, target_files / f"PlUk{COLORS[index]}.dat")

    helper = ROOT / "ports/halberd/tools/mk_slot_files.py"
    result = subprocess.run(
        [sys.executable, str(helper), "--base", str(base_files), "--out", str(target_files),
         "--pl", TARGET_PL, "--name", name, "--dst-k", str(internal), "--dst-e", str(external)],
        text=True, capture_output=True, check=True,
    )
    log = json.loads(result.stdout)
    if log["row"]["replaces"] != {"name": before_name, "pl": before_pl}:
        raise ValueError("base m-ex row changed during slot staging")
    extra_color_ui(target_files, internal, external)
    mxdt = target_files / "MxDt.dat"
    mxdt.write_bytes(own_anim_and_costumes(mxdt.read_bytes(), internal, external))

    profile = json.loads((source_mod / "geno.json").read_text(encoding="utf-8"))
    fighters = profile.get("fighters", [])
    if len(fighters) != 1 or fighters[0].get("attach") not in ("kirby", SOURCE_PL):
        raise ValueError("source Geno profile must attach exactly one Kirby fighter")
    fighters[0]["attach"] = TARGET_PL
    fighters[0]["name"] = name
    (output / "geno.json").write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
    mod = {
        "id": "ultimate-kirby-slot", "name": name, "version": "0.1.0", "kind": "fighter",
        "description": (f"Ultimate Kirby staged at m-ex internal {internal}, external {external}; "
                        f"replaces {before_name}. Eight supplied Kirby costume files and the source mod's "
                        "fighter scripts, motion table, and animation archive are installed."),
        "requires": [], "conflicts": [],
    }
    (output / "mod.json").write_text(json.dumps(mod, indent=2) + "\n", encoding="utf-8")
    report = {"internal": internal, "external": external, "replaces": log["row"]["replaces"],
              "pl": TARGET_PL, "aj": TARGET_AJ,
              "costumes": [f"PlUk{color}.dat" for color in COLORS],
              "costume_sources": [
                  {"index": index, "file": f"PlUk{COLORS[index]}.dat",
                   "source": str(path.resolve()), "sha256": sha256(path)}
                  for index, path in enumerate(costumes)],
              "fighter_sha256": sha256(files / SOURCE_PL),
              "animation_sha256": sha256(files / "PlKbAJ.dat"),
              "source_mod": str(source_mod.resolve()), "base_files": str(base_files.resolve()),
              "menu_placeholders": "Kirby icon/CSP and stock art from mk_slot_files.py"}
    (output / "slot-build.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    source_manifest = source_mod / "source-manifest.json"
    if source_manifest.is_file():
        provenance = json.loads(source_manifest.read_text(encoding="utf-8"))
        provenance["m_ex_slot"] = {key: report[key] for key in
                                   ("internal", "external", "replaces", "pl", "aj", "costume_sources")}
        (output / "source-manifest.json").write_text(
            json.dumps(provenance, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-mod", type=Path, required=True)
    parser.add_argument("--base-files", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--dst-k", type=int, required=True)
    parser.add_argument("--dst-e", type=int, required=True)
    parser.add_argument("--expected-name", required=True)
    parser.add_argument("--name", default="Ultimate Kirby")
    parser.add_argument("--costume", action="append", required=True, help="INDEX:PATH, repeat for 0..7")
    args = parser.parse_args()
    costumes = parse_costumes(args.costume)
    report = build(args.source_mod, args.base_files, args.out, args.dst_k, args.dst_e,
                   args.expected_name, args.name, costumes)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
