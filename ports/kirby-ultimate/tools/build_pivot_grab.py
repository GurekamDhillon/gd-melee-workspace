#!/usr/bin/env python3
"""Append Ultimate Kirby's pivot grab as a distinct Melee motion row.

The converted CatchTurn FigaTree is supplied separately. Existing Kirby rows,
scripts, and AJ bytes are preserved; the caller must also raise the m-ex
animation count for the new fighter from 479 to 480 and bind the Geno hook.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

import build_grabs
import build_side_b as side


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiment/brawl-kirby/tools/anim"))
import figatree  # noqa: E402
DEFAULT_IR = ROOT / "experiment/character-ir/instances/kirby.ultimate.ir.json"
ROW = 479
SYMBOL = "PlyKirby5K_Share_ACTION_CatchTurn_figatree"
SCALE = 5.0 / 4.6


def _number(value: str) -> float:
    match = re.fullmatch(r"(?:Some\()?(-?\d+(?:\.\d+)?)\)?", value)
    if match is None:
        raise ValueError(f"unsupported Ultimate grab coordinate {value!r}")
    return float(match.group(1))


def source_grab(path: Path) -> list[dict]:
    ir = json.loads(path.read_text(encoding="utf-8"))
    if ir.get("document_id") != "kirby.ultimate":
        raise ValueError("expected Ultimate Kirby IR")
    script = next((s for s in ir["behavior"]["scripts"]
                   if s["id"] == "script:kirby/catchturn/game_catchturn"), None)
    if script is None or script.get("timeline", {}).get("static") is not True:
        raise ValueError("CatchTurn needs one static source timeline")
    events = script["events"]
    hits = [e for e in events if e["op"] == "grab.box"]
    clears = [e for e in events if e["op"] == "engine.grab_clear_all"]
    if len(hits) != 2 or len(clears) != 1 or any(e.get("frame") != 10 for e in hits) or clears[0].get("frame") != 12:
        raise ValueError("CatchTurn 10..12 grab window changed")
    boxes = []
    for event in hits:
        args = event["args"]["arguments"]
        if len(args) != 12 or args[2] != 'Hash40::new("top")' or args[10] != "*FIGHTER_STATUS_KIND_CAPTURE_PULLED":
            raise ValueError("CatchTurn source grab layout changed")
        situation = {"*COLLISION_SITUATION_MASK_G": "ground",
                     "*COLLISION_SITUATION_MASK_A": "air"}.get(args[11])
        if situation is None:
            raise ValueError("CatchTurn needs ground and air grab boxes")
        boxes.append({"situation": situation, "radius": _number(args[3]),
                      "start": tuple(_number(x) for x in args[4:7]),
                      "end": tuple(_number(x) for x in args[7:10])})
    if [box["situation"] for box in boxes] != ["ground", "air"]:
        raise ValueError("CatchTurn situation order changed")
    return boxes


def _signed256(value: float) -> int:
    n = round(value * SCALE * 256)
    if not -32768 <= n <= 32767:
        raise ValueError("CatchTurn grab offset exceeds HSD signed16")
    return n & 0xFFFF


def _spheres(boxes: list[dict], templates: list[list[int]]) -> list[list[int]]:
    if len(templates) != 4:
        raise ValueError("Melee CatchDash needs four grab sphere templates")
    result = []
    for box_index, box in enumerate(boxes):
        start, end = box["start"], box["end"]
        if any(abs(start[i] - end[i]) > 0.001 for i in (0, 1)) or start[0] != 0 or start[2] >= 0 or end[2] >= 0:
            raise ValueError("CatchTurn capsule is no longer horizontal behind Kirby")
        length = abs(end[2] - start[2])
        # Melee's four hitbox slots cannot encode both Ultimate capsules.
        # Two enlarged spheres per situation cover each source segment end to end.
        radius = box["radius"] + length / 4
        size = round(radius * SCALE * 256)
        if not 0 < size <= 0xFFFF:
            raise ValueError("CatchTurn grab sphere radius is out of range")
        for sphere_index, fraction in enumerate((0.25, 0.75)):
            slot = 2 * box_index + sphere_index
            z = -(start[2] + (end[2] - start[2]) * fraction)
            y = start[1]
            w0, _, _, w3, w4 = templates[slot]
            # The Geno entry flips facing to the reverse input. Source-negative Z
            # thus becomes positive Z in Melee's new facing for the same world side.
            w0 = (w0 & ~((7 << 23) | (0xFF << 11))) | (slot << 23)
            w1 = (size << 16) | _signed256(z)
            w2 = (_signed256(y) << 16) | _signed256(0)
            w4 = (w4 & ~3) | (2 if box["situation"] == "ground" else 1)
            result.append([w0, w1, w2, w3, w4])
    return result


def _script(ar: side.mex_hsd.Archive, boxes: list[dict]) -> tuple[list[int], list[int]]:
    events = side.flatten(ar, 243)
    templates = [words for _, op, words, _ in events if op == 11]
    spheres = iter(_spheres(boxes, templates))
    adapted = [(frame, op, next(spheres) if op == 11 else words, relocs)
               for frame, op, words, relocs in events]
    return build_grabs.retime_script(adapted, {"active": 10, "clear": 12})


def append_pivot(fighter: bytes, animation: bytes, clip: bytes,
                 boxes: list[dict]) -> tuple[bytes, bytes]:
    ar = side.mex_hsd.Archive(fighter)
    clip_ar = side.mex_hsd.Archive(clip)
    if clip_ar.file_size != len(clip) or clip_ar.nb_public != 1 or clip_ar.publics[0][0] != SYMBOL:
        raise ValueError(f"CatchTurn clip must expose {SYMBOL}")
    parsed_symbol, tree = figatree.parse_archive(clip)
    if parsed_symbol != SYMBOL or len(tree["joints"]) != 46 or not 12 < tree["frames"] < 100:
        raise ValueError("CatchTurn must be a short 46-joint Kirby FigaTree")
    fd = ar.public("ftDataKirby")
    table = side.motion_table(ar)
    if table + ROW * 0x18 > ar.data_size or fd + 0x10 not in ar.reloc_set:
        raise ValueError("Kirby needs 479 standard rows and an x10 index table")
    x10 = ar.u32(fd + 0x10)
    if x10 + ROW * 2 > ar.data_size:
        raise ValueError("Kirby's x10 index table is truncated")
    script, script_relocs = _script(ar, boxes)
    data = bytearray(ar.data)
    relocs = set(ar.reloc_offsets)

    def append(payload: bytes, alignment: int = 0x20) -> int:
        while len(data) % alignment:
            data.append(0)
        at = len(data)
        data.extend(payload)
        return at

    sym = append(SYMBOL.encode("ascii") + b"\0", 1)
    script_at = append(struct.pack(">%dI" % len(script), *script))
    relocs.update(script_at + 4 * i for i in script_relocs)
    aj = bytearray(animation)
    while len(aj) % 0x20:
        aj.append(0)
    aj_at = len(aj)
    aj.extend(clip)

    rows = bytearray(ar.data[table:table + ROW * 0x18])
    rows.extend(struct.pack(">6I", sym, aj_at, len(clip), script_at,
                            ar.u32(table + 243 * 0x18 + 0x10), 0))
    new_table = append(rows)
    for at in ar.reloc_offsets:
        if table <= at < table + ROW * 0x18:
            relocs.add(new_table + at - table)
    relocs.update((new_table + ROW * 0x18, new_table + ROW * 0x18 + 0xC))
    struct.pack_into(">I", data, fd + 0xC, new_table)
    new_x10 = append(ar.data[x10:x10 + ROW * 2] + b"\0\0")
    struct.pack_into(">I", data, fd + 0x10, new_x10)
    entries = sorted(relocs)
    body = bytes(data) + b"".join(struct.pack(">I", at) for at in entries) + ar.raw[ar.o_public:]
    header = (struct.pack(">5I", 0x20 + len(body), len(data), len(entries), ar.nb_public,
                          ar.nb_extern) + ar.raw[0x14:0x20])
    result = header + body
    side.mex_hsd.Archive(result).public("ftDataKirby")
    return result, bytes(aj)


def add_pivot_profile(profile: dict) -> dict:
    fighters = profile.get("fighters")
    if not isinstance(fighters, list) or len(fighters) != 1:
        raise ValueError("pivot grab needs one Kirby Geno fighter profile")
    entry = fighters[0]
    states = entry.get("states")
    if not isinstance(states, list) or any(state.get("name") == "PivotGrab" for state in states):
        raise ValueError("pivot grab needs a new Geno state")
    index = len(states)
    states.append({"name": "PivotGrab", "behavior": "geno.ground", "subaction": ROW,
                   "like": "motion:214", "anim": "like", "iasa": "like",
                   "phys": "like", "coll": "like"})
    hooks = entry.setdefault("hooks", {})
    hooks.setdefault("on_frame", []).append(f"geno.kirby.pivot_grab:{index}")
    return profile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mod", type=Path, required=True,
                        help="separate Kirby-source mod to extend; output files are updated in place")
    parser.add_argument("--clip", type=Path, required=True)
    parser.add_argument("--ir", type=Path, default=DEFAULT_IR)
    args = parser.parse_args()
    if (args.mod / "pivot-grab.json").exists():
        raise ValueError("this source mod already has a pivot-grab row")
    files = args.mod / "files"
    profile_path = args.mod / "geno.json"
    profile = add_pivot_profile(json.loads(profile_path.read_text(encoding="utf-8")))
    fighter, aj = append_pivot((files / "PlKb.dat").read_bytes(),
                               (files / "PlKbAJ.dat").read_bytes(),
                               args.clip.read_bytes(), source_grab(args.ir))
    (files / "PlKb.dat").write_bytes(fighter)
    (files / "PlKbAJ.dat").write_bytes(aj)
    profile_path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
    report = {"row": ROW, "symbol": SYMBOL, "source_script": "script:kirby/catchturn/game_catchturn",
              "clip_sha256": hashlib.sha256(args.clip.read_bytes()).hexdigest(),
              "fighter_sha256": hashlib.sha256(fighter).hexdigest(),
              "animation_sha256": hashlib.sha256(aj).hexdigest(),
              "grab_window": [10, 12], "geometry": "two Melee spheres per Ultimate capsule"}
    (args.mod / "pivot-grab.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
