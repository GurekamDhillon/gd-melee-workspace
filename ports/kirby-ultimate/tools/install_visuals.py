#!/usr/bin/env python3
"""Install selected Ultimate-derived visuals into the existing Kirby LAB mod.

Inputs are already converted Melee HSD archives. The private source model and
NUANMB animation bytes are never copied into the repository by this tool.
The costume must retain vanilla Kirby's joint tree. Each animation manifest
entry names a single figatree subarchive with the target row's public symbol.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/mex_port"))
sys.path.insert(0, str(ROOT / "experiment/brawl-kirby/tools/anim"))
import mex_hsd  # noqa: E402
import figatree  # noqa: E402


BASE = ROOT / "experiment/brawl-kirby/disc"
JOINT_SYMBOL = "PlyKirby5K_Share_joint"
MATANIM_SYMBOL = "PlyKirby5K_Share_matanim_joint"
MOTION_ROWS = 479


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def joint_signature(raw: bytes) -> list[tuple[int, tuple[float, ...]]]:
    """Read the fighter's DFS joint topology and rest transforms."""
    ar = mex_hsd.Archive(raw)
    names = {name for name, _ in ar.publics}
    if JOINT_SYMBOL not in names or MATANIM_SYMBOL not in names:
        raise ValueError("costume is missing Kirby's joint or matanim public symbol")
    result: list[tuple[int, tuple[float, ...]]] = []
    visited: set[int] = set()

    def walk(offset: int, parent: int) -> None:
        while offset:
            if offset in visited or offset + 0x40 > ar.data_size:
                raise ValueError("costume has an invalid or cyclic JOBJ tree")
            visited.add(offset)
            index = len(result)
            values = struct.unpack_from(">9f", ar.data, offset + 0x14)
            result.append((parent, values))
            child = ar.u32(offset + 8) if offset + 8 in ar.reloc_set else 0
            sibling = ar.u32(offset + 0xC) if offset + 0xC in ar.reloc_set else 0
            if child:
                walk(child, index)
            offset = sibling

    walk(ar.public(JOINT_SYMBOL), -1)
    return result


def validate_costume(raw: bytes, baseline: bytes) -> None:
    actual, expected = joint_signature(raw), joint_signature(baseline)
    if len(actual) != 46 or len(expected) != 46:
        raise ValueError("costume must use vanilla Kirby's 46-joint tree")
    for index, ((parent, values), (old_parent, old_values)) in enumerate(zip(actual, expected)):
        if parent != old_parent or any(abs(a - b) > 1e-4 for a, b in zip(values, old_values)):
            raise ValueError(f"costume joint {index} differs from vanilla Kirby's rest tree")


def motion_table(ar: mex_hsd.Archive) -> int:
    fd = ar.public("ftDataKirby")
    if fd + 0xC not in ar.reloc_set:
        raise ValueError("PlKb.dat lacks its motion table relocation")
    table = ar.u32(fd + 0xC)
    if table + MOTION_ROWS * 0x18 > ar.data_size:
        raise ValueError("PlKb.dat motion table is truncated")
    return table


def row_symbol(ar: mex_hsd.Archive, table: int, row: int) -> str:
    field = table + row * 0x18
    if field not in ar.reloc_set:
        raise ValueError(f"motion row {row} has no animation symbol")
    offset = ar.u32(field)
    if offset >= ar.data_size:
        raise ValueError(f"motion row {row} symbol pointer is invalid")
    return bytes(ar.data[offset:]).split(b"\0", 1)[0].decode("ascii")


def animation_entries(manifest: Path, ar: mex_hsd.Archive) -> list[tuple[int, Path, bytes, str, float]]:
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    entries = doc.get("animations")
    if not isinstance(entries, list):
        raise ValueError("animation manifest needs an animations list")
    table = motion_table(ar)
    seen: set[int] = set()
    result = []
    for entry in entries:
        row = entry.get("row")
        if type(row) is not int or row < 0 or row >= MOTION_ROWS or row in seen:
            raise ValueError(f"invalid or repeated motion row: {row!r}")
        seen.add(row)
        source = manifest.parent / entry["file"]
        raw = source.read_bytes()
        expected_hash = entry.get("sha256")
        if expected_hash is not None and sha256(raw) != expected_hash.lower():
            raise ValueError(f"animation row {row} SHA-256 mismatch")
        clip = mex_hsd.Archive(raw)
        symbol = row_symbol(ar, table, row)
        if clip.file_size != len(raw) or clip.nb_public != 1 or clip.publics[0][0] != symbol:
            raise ValueError(f"animation row {row} needs public symbol {symbol}")
        parsed_symbol, tree = figatree.parse_archive(raw)
        if parsed_symbol != symbol or len(tree["joints"]) != 46 or not 0 < tree["frames"] < 1000:
            raise ValueError(f"animation row {row} is not a 46-joint Kirby figatree")
        result.append((row, source, raw, symbol, tree["frames"]))
    return sorted(result)


def retain_previous(mod: Path, report: dict) -> None:
    """Keep previously installed visuals only while their bytes still match."""
    prior_path = mod / "visual-install.json"
    if not prior_path.is_file():
        return
    prior = json.loads(prior_path.read_text(encoding="utf-8"))
    files = mod / "files"
    old_costume = prior.get("costume")
    costume_path = files / "PlKbNr.dat"
    if (report["costume"] is None and isinstance(old_costume, dict)
            and costume_path.is_file()
            and sha256(costume_path.read_bytes()) == old_costume.get("sha256")):
        report["costume"] = old_costume
    used = {entry["row"] for entry in report["animations"]}
    fighter_path, aj_path = files / "PlKb.dat", files / "PlKbAJ.dat"
    if not fighter_path.is_file() or not aj_path.is_file():
        return
    ar = mex_hsd.Archive(fighter_path.read_bytes())
    table = motion_table(ar)
    aj = aj_path.read_bytes()
    for entry in prior.get("animations", []):
        row = entry.get("row")
        if type(row) is not int or row in used or not 0 <= row < MOTION_ROWS:
            continue
        field = table + row * 0x18
        offset, size = ar.u32(field + 4), ar.u32(field + 8)
        if (offset == entry.get("offset") and size == entry.get("size")
                and offset + size <= len(aj)
                and sha256(aj[offset:offset + size]) == entry.get("sha256")):
            report["animations"].append(entry)
    report["animations"].sort(key=lambda entry: entry["row"])
    if ("animation_manifest" not in report and report["animations"]
            and isinstance(prior.get("animation_manifest"), dict)):
        report["animation_manifest"] = prior["animation_manifest"]


def update_metadata(mod: Path, report: dict) -> None:
    """Make generated pack descriptions agree with the installed files."""
    if report["costume"] is None and not report["animations"]:
        return
    mod_path = mod / "mod.json"
    if mod_path.is_file():
        data = json.loads(mod_path.read_text(encoding="utf-8"))
        if "visuals" not in data["name"]:
            data["name"] += " + visuals"
        model = "converted Ultimate c00 costume" if report["costume"] else "Melee Kirby costume"
        count = len(report["animations"])
        clips = f"{count} converted Ultimate clip{'s' if count != 1 else ''}" if count else "Melee animation clips"
        data["description"] = (f"Ultimate Kirby 13.0.2 IR movement and uncharged side-B hitboxes "
                               f"with {model} and {clips}. Melee Kirby's rig, collision body, "
                               "status logic, and hammer item remain the host.")
        mod_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    source_path = mod / "source-manifest.json"
    if source_path.is_file():
        data = json.loads(source_path.read_text(encoding="utf-8"))
        data["visuals"] = {
            **report,
            "coverage": {
                "costume": "Ultimate Kirby c00 geometry/textures on Melee Kirby's 46-joint rig"
                if report["costume"] else "Melee Kirby costume",
                "animation_rows": [entry["row"] for entry in report["animations"]],
                "unconverted_rows": "All Melee Kirby motion rows not listed above retain their existing clips.",
            },
        }
        limitations = [item for item in data.get("limitations", [])
                       if not item.startswith("No Ultimate animations, model, collision body")]
        limit = "Melee Kirby's collision body, status logic, hammer item, and 46-joint rig remain in use."
        if limit not in limitations:
            limitations.append(limit)
        data["limitations"] = limitations
        if any(entry["row"] in (322, 323) for entry in report["animations"]):
            side_b = data.get("side_b")
            if isinstance(side_b, dict):
                side_b["translation"] = (
                    "Uncharged hitbox create/clear events and listed fighter clips are converted; "
                    "Melee hammer item, offsets, sound, state mechanics, and cleanup remain."
                )
        source_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                               encoding="utf-8")


def install(mod: Path, costume: Path | None, animations: Path | None,
            baseline_costume: Path, baseline_aj: Path) -> dict:
    if costume is None and animations is None:
        raise ValueError("provide --costume and/or --animations")
    files = mod / "files"
    if not files.is_dir():
        raise ValueError(f"mod files directory does not exist: {files}")

    # Validate all inputs before changing any mod file.
    costume_bytes = None
    if costume is not None:
        costume_bytes = costume.read_bytes()
        validate_costume(costume_bytes, baseline_costume.read_bytes())
    fighter_path = files / "PlKb.dat"
    fighter_bytes = fighter_path.read_bytes() if animations is not None else None
    fighter = mex_hsd.Archive(fighter_bytes) if fighter_bytes is not None else None
    entries = animation_entries(animations, fighter) if animations is not None else []
    aj_path = files / "PlKbAJ.dat"
    base_aj = baseline_aj.read_bytes() if entries else b""
    aj_bytes = aj_path.read_bytes() if entries and aj_path.exists() else base_aj
    if entries and not aj_bytes.startswith(base_aj):
        raise ValueError("existing PlKbAJ.dat is not based on the requested baseline")

    report = {"costume": None, "animations": []}
    source_entries = {}
    if animations is not None:
        source_raw = animations.read_bytes()
        source_entries = {entry["row"]: entry
                          for entry in json.loads(source_raw)["animations"]}
        report["animation_manifest"] = {"source": str(animations.resolve()),
                                        "sha256": sha256(source_raw)}
    if costume_bytes is not None:
        report["costume"] = {"file": "PlKbNr.dat", "source": str(costume.resolve()),
                             "sha256": sha256(costume_bytes)}
    if entries:
        output_aj = bytearray(aj_bytes)
        output_pl = bytearray(fighter_bytes)
        table = motion_table(fighter)
        for row, source, raw, symbol, frames in entries:
            field = table + row * 0x18
            current_offset, current_size = fighter.u32(field + 4), fighter.u32(field + 8)
            if (current_size == len(raw) and current_offset + current_size <= len(output_aj)
                    and output_aj[current_offset:current_offset + current_size] == raw):
                offset = current_offset
            else:
                while len(output_aj) % 0x20:
                    output_aj.append(0xFF)
                offset = len(output_aj)
                output_aj.extend(raw)
                struct.pack_into(">II", output_pl, 0x20 + field + 4, offset, len(raw))
            detail = {"row": row, "symbol": symbol,
                      "source": str(source.resolve()),
                      "offset": offset, "size": len(raw),
                      "frames": frames, "sha256": sha256(raw)}
            clip_id = source_entries[row].get("ultimate_clip_id")
            if clip_id:
                detail["ultimate_clip_id"] = clip_id
            report["animations"].append(detail)

    if costume_bytes is not None:
        target = files / "PlKbNr.dat"
        if not target.exists() or target.read_bytes() != costume_bytes:
            target.write_bytes(costume_bytes)
    if entries:
        if not aj_path.exists() or aj_path.read_bytes() != output_aj:
            aj_path.write_bytes(output_aj)
        if output_pl != fighter_bytes:
            fighter_path.write_bytes(output_pl)
    retain_previous(mod, report)
    (mod / "visual-install.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    update_metadata(mod, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mod", type=Path, required=True)
    parser.add_argument("--costume", type=Path)
    parser.add_argument("--animations", type=Path, help="JSON with animations: [{row, file, sha256?}]")
    parser.add_argument("--baseline-costume", type=Path, default=BASE / "PlKbNr.dat")
    parser.add_argument("--baseline-aj", type=Path, default=BASE / "PlKbAJ.dat")
    args = parser.parse_args()
    report = install(args.mod, args.costume, args.animations,
                     args.baseline_costume, args.baseline_aj)
    print(f"installed costume={bool(report['costume'])} animations={len(report['animations'])}: {args.mod}")


if __name__ == "__main__":
    main()
