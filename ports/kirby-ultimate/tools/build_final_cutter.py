#!/usr/bin/env python3
"""Stage Ultimate Final Cutter rising hitboxes in Kirby's up-B ftcmd.

Melee aerial row 329 calls ground row 325's script by a direct ftcmd pointer;
the call target is updated when row 325 is rebuilt. Melee up-B phase/status
logic and the cutter-wave article remain until their separate native passes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

import build_normals as normal
import build_side_b as side


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_IR = ROOT / "experiment/character-ir/instances/kirby.ultimate.ir.json"
DEFAULT_BASE = ROOT / "experiment/brawl-kirby/disc/PlKb.dat"
DEFAULT_MOD = ROOT / "_build/tmp/ultimate-kirby-mods/ultimate-kirby-movement"
SOURCE_IDS = {
    "ground": "script:kirby/specialhi2/game_specialhi2",
    "air": "script:kirby/specialairhi2/game_specialairhi2",
}


def source_scripts(path: Path) -> dict[str, dict]:
    ir = json.loads(path.read_text(encoding="utf-8"))
    if ir.get("document_id") != "kirby.ultimate":
        raise ValueError("expected Ultimate Kirby IR")
    scripts = {entry["id"]: entry for entry in ir["behavior"]["scripts"]}
    found = {kind: scripts[sid] for kind, sid in SOURCE_IDS.items()}
    sequences = []
    for kind, script in found.items():
        if script.get("language") != "ultimate.acmd.smashline_rust":
            raise ValueError(f"unexpected Final Cutter {kind} source language")
        events = [e for e in script["events"] if e["op"].startswith("hitbox.")]
        if len([e for e in events if e["op"] == "hitbox.create"]) != 10:
            raise ValueError(f"Ultimate Final Cutter {kind} hitbox count changed")
        sequences.append([(e.get("frame"), e["op"], e.get("hitbox")) for e in events])
    if sequences[0] != sequences[1]:
        raise ValueError("ground and air Final Cutter rising hitboxes differ")
    return found


def aerial_call_offset(archive: side.mex_hsd.Archive) -> int:
    offset = side.script_pointer(archive, 329)
    found = []
    for _ in range(128):
        op, words = side.command_at(archive, offset)
        if op == 7:
            if len(words) != 2:
                raise ValueError("unexpected aerial Final Cutter call width")
            found.append(offset + 4)
        if op == 0:
            break
        offset += 4 * len(words)
    if len(found) != 1 or found[0] not in archive.reloc_set:
        raise ValueError("expected one relocated aerial Final Cutter call")
    return found[0]


def aerial_call_target(archive: side.mex_hsd.Archive) -> int:
    return archive.u32(aerial_call_offset(archive))


def patch_archive(raw: bytes, vanilla: bytes,
                  scripts: dict[str, dict]) -> tuple[bytes, list[int]]:
    base = side.mex_hsd.Archive(vanilla)
    old = side.mex_hsd.Archive(raw)
    if aerial_call_target(old) not in (side.script_pointer(base, 325),
                                       side.script_pointer(old, 325)):
        raise ValueError("aerial Final Cutter calls an unexpected script")
    output, changed = normal.patch_archive(raw, vanilla, {325: {"script": scripts["ground"]}})
    archive = side.mex_hsd.Archive(output)
    target = side.script_pointer(archive, 325)
    call_offset = aerial_call_offset(archive)
    if archive.u32(call_offset) != target:
        data = bytearray(output)
        struct.pack_into(">I", data, 0x20 + call_offset, target)
        output = bytes(data)
        changed.append(329)
    return output, changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ir", type=Path, default=DEFAULT_IR)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--mod", type=Path, default=DEFAULT_MOD)
    args = parser.parse_args()
    scripts = source_scripts(args.ir)
    target = args.mod / "files/PlKb.dat"
    vanilla = args.base.read_bytes()
    current = target.read_bytes() if target.is_file() else vanilla
    output, changed = patch_archive(current, vanilla, scripts)
    if changed or not target.is_file():
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(output)
    manifest_path = args.mod / "source-manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["ultimate_final_cutter"] = {
            "ir_sha256": hashlib.sha256(args.ir.read_bytes()).hexdigest(),
            "source_scripts": SOURCE_IDS,
            "rows": [325, 329],
            "scope": "rising sword hitbox timeline; host state transitions and cutter-wave article remain",
        }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Ultimate Final Cutter rows {changed or 'already current'}: {target}")


if __name__ == "__main__":
    main()
