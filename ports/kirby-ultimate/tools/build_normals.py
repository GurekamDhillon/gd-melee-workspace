#!/usr/bin/env python3
"""Translate a first set of Ultimate Kirby native normal hitboxes to Melee ftcmd.

The source is the local Kirby character IR. Melee Kirby still supplies status
control, non-hitbox script events, and animations until their separate passes
are installed. This pass deliberately leaves looped rapid jab and scripts with
host control-flow commands to a later Geno-state translation.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import struct

import build_side_b as side


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_IR = ROOT / "experiment/character-ir/instances/kirby.ultimate.ir.json"
DEFAULT_MELEE = ROOT / "experiment/brawl-kirby/analysis/melee_kirby.json"
DEFAULT_BASE = ROOT / "experiment/brawl-kirby/disc/PlKb.dat"
DEFAULT_MOD = ROOT / "_build/tmp/ultimate-kirby-mods/ultimate-kirby-movement"

# Ultimate c00 motion-list name -> Melee Kirby motion name. Both names are
# explicitly checked against their source tables before any archive mutation.
MOTIONS = {
    "attack_11": "Attack11", "attack_12": "Attack12",
    "attack_100": "Attack100Loop", "attack_100_end": "Attack100End",
    "attack_dash": "AttackDash", "attack_s3_hi": "AttackS3Hi",
    "attack_s3_s": "AttackS3S", "attack_s3_lw": "AttackS3Lw",
    "attack_hi3": "AttackHi3", "attack_lw3": "AttackLw3",
    "attack_s4_hi": "AttackS4Hi", "attack_s4_s": "AttackS4S",
    "attack_s4_lw": "AttackS4Lw", "attack_hi4": "AttackHi4",
    "attack_lw4": "AttackLw4", "attack_air_n": "AttackAirN",
    "attack_air_f": "AttackAirF", "attack_air_b": "AttackAirB",
    "attack_air_hi": "AttackAirHi", "attack_air_lw": "AttackAirLw",
    "down_attack_u": "DownAttackU", "down_attack_d": "DownAttackD",
    "cliff_attack_quick": "CliffAttackQuick", "catch_attack": "CatchAttack",
}

# Variants 53/57 and 60/64 jump to their neutral-angle ftcmd body in Melee.
# Copy that body's non-hit events, then use the selected Ultimate ACMD hitboxes.
# Rapid-jab end has an empty host script, so jab1 supplies hitbox word layout.
TEMPLATE_DONORS = {51: 46, 53: 55, 57: 55, 60: 62, 64: 62}
EVENT_DONORS = {53: 55, 57: 55, 60: 62, 64: 62}
STATIC_ROWS = (46, 47, 51, 52, 53, 55, 57, 58, 59, 60, 62, 64, 66, 67,
               68, 69, 70, 71, 72, 187, 195, 221, 222, 245)
HITBOX_OPS = side.HITBOX_OPS
COORD_SCALE = 5.0 / 4.6  # same XRot rest-height ratio as the model retarget
ROLE_JOINT = {"top": 0, "hip": 4, "haver": 44, "footl": 49, "footr": 55,
              "kneer": 55, "toer": 55}


def source_rows(ir_path: Path, melee_path: Path) -> dict[int, dict]:
    ir = json.loads(ir_path.read_text(encoding="utf-8"))
    melee = json.loads(melee_path.read_text(encoding="utf-8"))
    if ir.get("document_id") != "kirby.ultimate":
        raise ValueError("expected Kirby Ultimate IR")
    subs = {s["name"]: s for s in ir["behavior"]["subactions"]
            if s["id"].startswith("subaction:kirby.c00.")}
    scripts = {s["id"]: s for s in ir["behavior"]["scripts"]}
    rows = {r["name"]: r for r in melee["motion_table"]
            if r["category"] != "copy_ability"}
    result = {}
    for sub_name, melee_name in MOTIONS.items():
        sub = subs[sub_name]
        script_id = sub.get("scripts", {}).get("main")
        if script_id is None:
            continue
        script = scripts[script_id]
        if script["language"] != "ultimate.acmd.smashline_rust":
            raise ValueError(f"unexpected script language: {script_id}")
        row = rows[melee_name]
        result[row["index"]] = {"subaction": sub_name, "melee_name": melee_name,
                                "source_clip": sub.get("clip"), "script": script,
                                "melee_anim_frames": row["anim_frames"]}
    # Melee selects a separate slow ledge-attack row at high damage. Ultimate
    # Kirby has one cliff-attack game script, so both reachable host rows use it.
    slow = rows["CliffAttackSlow"]
    result[slow["index"]] = {**result[rows["CliffAttackQuick"]["index"]],
                             "melee_name": "CliffAttackSlow",
                             "melee_anim_frames": slow["anim_frames"]}
    return result


def templates(ar: side.mex_hsd.Archive, row: int) -> dict[int, list[int]]:
    found = {}
    for _, op, words, _ in side.flatten(ar, row):
        if op == 11:
            found.setdefault((words[0] >> 23) & 7, words)
    if not found:
        raise ValueError(f"motion row {row} has no host hitbox template")
    return found


def down_air_timeline(script: dict) -> dict:
    """Expand the public ACMD's five 3-frame pulses and finishing hit.

    The IR marks events after a Rust loop as dynamic. Inspect the readable
    game-function body before assigning times, so a changed dump fails closed.
    """
    path = (ROOT / "experiment/tooling/ultimate/scripting/SSBU-Dumped-Scripts/"
            "smashline/lua2cpp_kirby/kirby/AttackAirLw.txt")
    game = path.read_text(encoding="utf-8").split('unsafe extern "C" fn effect_attackairlw', 1)[0]
    structural = (
        r"frame\(agent\.lua_state_agent, 18\.0\);",
        r"for _ in 0\.\.5 \{",
        r"wait\(agent\.lua_state_agent, 2\.0\);",
        r"wait\(agent\.lua_state_agent, 1\.0\);",
        r"frame\(agent\.lua_state_agent, 48\.0\);",
    )
    if not all(re.search(part, game) for part in structural):
        raise ValueError("down-air loop structure changed in public ACMD source")
    hits = [e for e in script["events"] if e["op"] == "hitbox.create"]
    clears = [e for e in script["events"] if e["op"] == "hitbox.clear"]
    if len(hits) != 2 or len(clears) != 2 or game.count("macros::ATTACK(agent") != 2:
        raise ValueError("expected one repeating and one finishing down-air hitbox")
    events = []
    for frame in (18, 21, 24, 27, 30):
        for source_event, at in ((hits[0], frame), (clears[0], frame + 2)):
            event = copy.deepcopy(source_event)
            event["frame"] = at
            events.append(event)
    for source_event, at in ((hits[1], 34), (clears[1], 35)):
        event = copy.deepcopy(source_event)
        event["frame"] = at
        events.append(event)
    return {**script, "events": events, "timeline": {"static": True}}


def _s16(value: float) -> int:
    packed = round(value * 256)
    if not -32768 <= packed <= 32767:
        raise ValueError(f"hitbox offset {value} cannot fit signed 16-bit")
    return packed & 0xFFFF


def make_hitbox(hitbox: dict, template: list[int]) -> list[int]:
    """Port numeric Ultimate combat fields; retain Melee target/SFX flags."""
    slot = side.bounded_int(hitbox["slot"], "slot", 3)
    role = hitbox.get("joint_role")
    if role not in ROLE_JOINT:
        raise ValueError(f"unmapped Ultimate hitbox bone role {role!r}")
    joint = ROLE_JOINT[role]
    damage = side.bounded_int(round(float(hitbox["damage"])), "rounded damage", 1023)
    angle = side.bounded_int(hitbox["angle"], "angle", 511)
    kbg = side.bounded_int(hitbox["knockback_growth"], "KBG", 511)
    wdsk = side.bounded_int(hitbox.get("weight_dependent_set_knockback", 0), "WDSK", 511)
    bkb = side.bounded_int(hitbox["base_knockback"], "BKB", 511)
    size = side.bounded_int(round(float(hitbox["size"]) * COORD_SCALE * 256), "size*256", 65535)
    offset = hitbox.get("offset")
    if not isinstance(offset, list) or len(offset) != 3 or any(v is None for v in offset):
        raise ValueError("Ultimate hitbox needs a numeric xyz offset")
    x, y, z = (_s16(float(v) * COORD_SCALE) for v in offset)
    element = side.ELEMENT.get(hitbox.get("element", "normal"), 0)
    w0, _, _, w3, w4 = template
    return [
        (w0 & ~((7 << 23) | (0xFF << 11) | 0x3FF)) | (slot << 23) | (joint << 11) | damage,
        (size << 16) | x,
        (y << 16) | z,
        (w3 & 0x1F) | (angle << 23) | (kbg << 14) | (wdsk << 5),
        (w4 & ~((0x1FF << 23) | (0x1F << 18))) | (bkb << 23) | (element << 18),
    ]


def make_script(host_events: list, ir_script: dict,
                hitbox_templates: dict[int, list[int]]) -> tuple[list[int], list[int]]:
    ends = [f for f, op, _, _ in host_events if op == 0]
    if len(ends) != 1:
        raise ValueError("host script must have one End")
    events = []  # frame, priority, order, words, relocation word positions
    for order, (frame, op, words, relocs) in enumerate(host_events):
        if op not in HITBOX_OPS and op != 0:
            events.append((frame, 0, order, words, relocs))
    last_source = 0
    for order, event in enumerate(ir_script["events"]):
        op = event["op"]
        if op not in ("hitbox.create", "hitbox.clear", "hitbox.remove"):
            continue
        if "frame" not in event:
            raise ValueError(f"dynamic Ultimate {op} event needs a state/loop translator")
        frame = side.bounded_int(event["frame"], "Ultimate event frame", 1000)
        last_source = max(last_source, frame)
        if op == "hitbox.create":
            hitbox = event["hitbox"]
            slot = side.bounded_int(hitbox["slot"], "slot", 3)
            template = hitbox_templates.get(slot) or hitbox_templates[min(hitbox_templates)]
            words = make_hitbox(hitbox, template)
        elif op == "hitbox.clear":
            words = [16 << 26]
        else:
            raw_args = event.get("args", {}).get("arguments", [])
            if not raw_args:
                raise ValueError("hitbox.remove has no slot argument")
            slot = side.bounded_int(int(raw_args[-1]), "remove slot", 3)
            words = [(15 << 26) | slot]
        events.append((frame, 1, order, words, []))
    end_frame = max(ends[0], last_source + 1)
    events.append((end_frame, 2, 0, [0], []))
    events.sort(key=lambda e: (e[0], e[1], e[2]))
    out, relocated, now = [], [], 0
    for frame, _, _, words, relocs in events:
        if frame > now:
            out.append((2 << 26) | frame)
            now = frame
        start = len(out)
        out.extend(words)
        relocated.extend(start + i for i in relocs)
    if not out or out[-1] != 0:
        raise ValueError("generated normal script has no End")
    return out, sorted(set(relocated))


def _linear_hitboxes(words: list[int]) -> list[tuple[int, int]]:
    result, frame, at = [], 0, 0
    while at < len(words):
        op = words[at] >> 26
        length = side.COMMAND_WORDS[op]
        if op == 1:
            frame += words[at] & 0x3FFFFFF
        elif op == 2:
            frame = max(frame, words[at] & 0x3FFFFFF)
        elif op == 11:
            result.append((frame, words[at] & 0x3FF))
        at += length
        if op == 0:
            break
    return result


def compiled_hitbox_frames(words: list[int]) -> list[int]:
    return sorted({frame for frame, _ in _linear_hitboxes(words)})


def compiled_hitbox_damages(words: list[int]) -> list[int]:
    return [damage for _, damage in _linear_hitboxes(words)]


def patch_archive(raw: bytes, vanilla: bytes, sources: dict[int, dict]) -> tuple[bytes, list[int]]:
    ar, base = side.mex_hsd.Archive(raw), side.mex_hsd.Archive(vanilla)
    if ar.public("ftDataKirby") != base.public("ftDataKirby"):
        raise ValueError("expected vanilla Kirby ftData layout")
    data, relocations, changed = bytearray(ar.data), set(ar.reloc_offsets), []
    table = side.motion_table(ar)
    for row, source in sorted(sources.items()):
        host_row = row if side.script_pointer(ar, row) != side.script_pointer(base, row) else EVENT_DONORS.get(row, row)
        source_script = down_air_timeline(source["script"]) if row == 72 else source["script"]
        script, rel_words = make_script(side.flatten(ar, host_row), source_script,
                                        templates(base, TEMPLATE_DONORS.get(row, row)))
        if side.linear_words(ar, row) == script:
            continue
        while len(data) % 0x20:
            data.append(0)
        at = len(data)
        data.extend(struct.pack(">%dI" % len(script), *script))
        relocations.update(at + 4 * index for index in rel_words)
        struct.pack_into(">I", data, table + row * 0x18 + 0xC, at)
        changed.append(row)
    if not changed:
        return raw, []
    relocs = sorted(relocations)
    body = bytes(data) + b"".join(struct.pack(">I", offset) for offset in relocs) + ar.raw[ar.o_public:]
    header = struct.pack(">5I", 0x20 + len(body), len(data), len(relocs),
                         ar.nb_public, ar.nb_extern) + ar.raw[0x14:0x20]
    return header + body, changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ir", type=Path, default=DEFAULT_IR)
    parser.add_argument("--melee", type=Path, default=DEFAULT_MELEE)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--mod", type=Path, default=DEFAULT_MOD)
    parser.add_argument("--rows", type=int, nargs="*", default=list(STATIC_ROWS))
    args = parser.parse_args()
    ir_bytes = args.ir.read_bytes()
    sources = source_rows(args.ir, args.melee)
    selected = {row: sources[row] for row in args.rows}
    target = args.mod / "files/PlKb.dat"
    base_bytes = args.base.read_bytes()
    current = target.read_bytes() if target.is_file() else base_bytes
    output, changed = patch_archive(current, base_bytes, selected)
    if changed or not target.is_file():
        target.write_bytes(output)
    manifest_path = args.mod / "source-manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["native_normals"] = {
            "ir_sha256": hashlib.sha256(ir_bytes).hexdigest(),
            "rows": [{"row": row, "melee_name": source["melee_name"],
                      "ultimate_subaction": source["subaction"],
                      "ultimate_script": source["script"]["id"]}
                     for row, source in sorted(selected.items())],
            "translation": "Ultimate hitbox combat fields/xyz scaled by 5/4.6; Melee status and non-hitbox events retained; fractional damage rounded",
            "deferred": "rapid-jab loop, special hitbox flags/autolink, throw logic, animation timing, and source NRO revision verification",
        }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"native normal rows {changed or 'already current'}: {target}")


if __name__ == "__main__":
    main()
