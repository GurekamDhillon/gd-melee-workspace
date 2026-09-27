#!/usr/bin/env python3
"""Transfer Ultimate Kirby's aerial Stone hitbox into the native Melee status.

Melee's Stone status already has the Ultimate IR's hold, cancel, slope, slide,
and fall-cap parameters. Its aerial active state owns the correct activation
boundary; this pass changes only that state's single hitbox payload. The
ground hitboxes at frame 14 and then calls absolute frame(2) before clearing.
The exact 13.0.2 NRO confirms this ordering; its hitboxes do not persist to a
later frame. Native Melee row 332 likewise has no ftcmd hitbox.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

import build_normals as normals
import build_side_b as side

ROOT = Path(__file__).resolve().parents[3]
IR = ROOT / "experiment/character-ir/instances/kirby.ultimate.ir.json"
BASE = ROOT / "experiment/brawl-kirby/disc/PlKb.dat"
MOD = ROOT / "_build/tmp/ultimate-kirby-mods/ultimate-kirby-movement"
GROUND = "script:kirby/speciallw/game_speciallw"
AIR = "script:kirby/specialairlw/game_specialairlw"
AIR_ROW = 336
GROUND_ROW = 332
NRO = ROOT / "experiment/tooling/ultimate/workspace/extracted/prebuilt/nro/release/lua2cpp_kirby.nro"
NRO_SHA256 = "0d73bec6963f8e49d2008fcbb697dab36012e2536c2817f22ed986c308c69a63"


def _script(ir: dict, identifier: str) -> dict:
    if ir.get("document_id") != "kirby.ultimate":
        raise ValueError("expected kirby.ultimate IR")
    scripts = [s for s in ir["behavior"]["scripts"] if s["id"] == identifier]
    if len(scripts) != 1 or scripts[0]["language"] != "ultimate.acmd.smashline_rust":
        raise ValueError(f"missing or unsupported Stone source {identifier}")
    return scripts[0]


def ground_timeline(ir: dict) -> list[tuple[int, str]]:
    """Reject the raw public dump's nonmonotonic absolute frame labels."""
    script = _script(ir, GROUND)
    events = [(side.bounded_int(e["frame"], "Stone event frame", 1000), e["op"])
              for e in script["events"] if e["op"] in ("hitbox.create", "hitbox.clear")]
    if not any(op == "hitbox.create" for _, op in events):
        raise ValueError("ground Stone has no source hitbox")
    last = -1
    for frame, op in events:
        if frame < last:
            raise ValueError(f"ground Stone clear at source frame {frame} follows hitboxes at frame {last}; "
                             "absolute/relative timing is unresolved")
        last = frame
    return events


def ground_resolution(ir: dict, nro_path: Path, fighter: bytes) -> dict:
    """Resolve the ground script only for the inspected 13.0.2 NRO and row 332."""
    script = _script(ir, GROUND)
    events = [e for e in script["events"] if e["op"].startswith("hitbox.")]
    if [(e["frame"], e["op"]) for e in events] != [
        (14, "hitbox.create"), (14, "hitbox.create"), (2, "hitbox.clear")
    ] or [(e["hitbox"]["slot"], e["hitbox"]["damage"]) for e in events[:2]] != [
        (0, 14), (1, 14)
    ]:
        raise ValueError("ground Stone source no longer matches inspected 14/2 control flow")
    if not nro_path.is_file() or hashlib.sha256(nro_path.read_bytes()).hexdigest() != NRO_SHA256:
        raise ValueError("ground Stone needs the exact inspected Ultimate 13.0.2 Kirby NRO")
    ar = side.mex_hsd.Archive(fighter)
    if any(op == 11 for _, op, _, _ in side.flatten(ar, GROUND_ROW)):
        raise ValueError("ground Stone host row unexpectedly contains a ftcmd hitbox")
    return {
        "source_absolute_frames": [14, 14, 2],
        "effective_clear_frame": 14,
        "persistent_hitbox_frames": 0,
        "host_motion_row": GROUND_ROW,
        "nro_sha256": NRO_SHA256,
        "nro_calls": {"frame_5": "0x710048639c", "frame_14": "0x710048645c",
                      "attack_helper": "0x7100485690", "frame_2": "0x7100485ec0",
                      "clear_all": "0x7100485f20"},
        "semantics": "Absolute frame(2) follows frame(14) in the same coroutine; no later active frame.",
    }


def air_hitbox(ir: dict) -> dict:
    script = _script(ir, AIR)
    events = [e for e in script["events"] if e["op"].startswith("hitbox.")]
    if len(events) != 2 or events[0]["op"] != "hitbox.remove" or \
            events[1]["op"] != "hitbox.create" or events[1]["frame"] != 30:
        raise ValueError("aerial Stone source combat shape changed")
    hit = events[1]["hitbox"]
    if hit["slot"] != 0 or hit["joint_role"] != "top" or hit["damage"] != 18:
        raise ValueError("aerial Stone hitbox no longer matches the checked source")
    return hit


def patch_fighter(raw: bytes, vanilla: bytes, ir: dict) -> tuple[bytes, list[int]]:
    base, ar = side.mex_hsd.Archive(vanilla), side.mex_hsd.Archive(raw)
    if ar.public("ftDataKirby") != base.public("ftDataKirby") or \
            side.motion_table(ar) != side.motion_table(base):
        raise ValueError("Stone builder needs Kirby's original fighter-data layout")
    host = side.linear_words(base, AIR_ROW)
    if len(host) != 6 or host[0] >> 26 != 11 or host[-1] != 0:
        raise ValueError("vanilla aerial Stone script is not one hitbox and End")
    expected = normals.make_hitbox(air_hitbox(ir), host[:5]) + [0]
    current = side.linear_words(ar, AIR_ROW)
    if current == expected:
        return raw, []
    if current != host:
        raise ValueError("aerial Stone script already changed by another builder")
    pointer = side.script_pointer(ar, AIR_ROW)
    out = bytearray(raw)
    struct.pack_into(">5I", out, 0x20 + pointer, *expected[:5])
    return bytes(out), [AIR_ROW]


def install(mod: Path, ir_path: Path = IR, base_path: Path = BASE) -> list[int]:
    mod_path, manifest_path = mod / "mod.json", mod / "source-manifest.json"
    target = mod / "files/PlKb.dat"
    meta = json.loads(mod_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if meta.get("id") != "ultimate-kirby-movement":
        raise ValueError("Stone builder needs the Ultimate Kirby movement pack")
    ir_bytes = ir_path.read_bytes()
    ir = json.loads(ir_bytes)
    updated, changed = patch_fighter(target.read_bytes(), base_path.read_bytes(), ir)
    # The source's nonmonotonic labels are intentionally kept in IR. The NRO
    # hash and live host row decide whether the zero-duration path is verified.
    try:
        ground = ground_resolution(ir, NRO, updated)
    except ValueError as exc:
        ground = None
        ground_reason = str(exc)
    else:
        ground_reason = None
    if changed:
        target.write_bytes(updated)
    if "Stone" not in meta["name"]:
        meta["name"] += " + Stone"
    if "aerial Stone" not in meta["description"]:
        meta["description"] += " Ultimate aerial Stone hitbox fields run on Melee's native Stone state."
    manifest["stone"] = {
        "target_motion_rows": {"air_active": AIR_ROW, "ground_start": GROUND_ROW},
        "ir_scripts": [AIR, GROUND],
        "source_ir_sha256": hashlib.sha256(ir_bytes).hexdigest(),
        "translation": "Aerial hitbox combat fields/xyz scaled by 5/4.6; native activation timing and Stone status retained.",
        "ground_resolution": ground,
        "ground_blocker": ground_reason,
        "source_revision_status": ("Version-matched Ultimate 13.0.2 NRO verified"
                                   if ground is not None else
                                   "Ground timing needs the exact inspected Ultimate 13.0.2 NRO"),
    }
    mod_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mod", type=Path, default=MOD)
    parser.add_argument("--ir", type=Path, default=IR)
    parser.add_argument("--base", type=Path, default=BASE)
    args = parser.parse_args()
    print(f"Stone rows changed: {install(args.mod, args.ir, args.base)}")


if __name__ == "__main__":
    main()
