#!/usr/bin/env python3
"""Install Ultimate Kirby's eight-pulse rapid jab in Melee motion row 50.

Melee ftcmd stores whole-percent damage. Eight 0.2% Ultimate pulses are encoded
with two 1% pulses per 16-frame cycle (the nearest whole-percent cycle total).
Zero-damage pulses retain the source hitbox cadence and knockback fields.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import struct

import build_normals as normal
import build_side_b as side


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_IR = normal.DEFAULT_IR
DEFAULT_BASE = normal.DEFAULT_BASE
DEFAULT_MOD = normal.DEFAULT_MOD
SOURCE_ID = "script:kirby/attack100/game_attack100"
SOURCE_TEXT = (ROOT / "experiment/tooling/ultimate/scripting/SSBU-Dumped-Scripts/"
               "smashline/lua2cpp_kirby/kirby/Attack100.txt")
PULSE_FRAMES = tuple(range(0, 16, 2))
PULSE_DAMAGE = (0, 0, 1, 0, 0, 0, 0, 1)


def source_hitbox(ir_path: Path) -> dict:
    ir = json.loads(ir_path.read_text(encoding="utf-8"))
    if ir.get("document_id") != "kirby.ultimate":
        raise ValueError("expected Kirby Ultimate IR")
    scripts = {s["id"]: s for s in ir["behavior"]["scripts"]}
    script = scripts[SOURCE_ID]
    creates = [e for e in script["events"] if e["op"] == "hitbox.create"]
    clears = [e for e in script["events"] if e["op"] == "hitbox.clear"]
    if len(creates) != 8 or len(clears) != 8:
        raise ValueError("Ultimate rapid jab needs eight create/clear pairs")
    first = creates[0]["hitbox"]
    if any(e["hitbox"] != first for e in creates) or first["damage"] != 0.2:
        raise ValueError("Ultimate rapid-jab pulse fields changed")
    game = SOURCE_TEXT.read_text(encoding="utf-8").split(
        'unsafe extern "C" fn effect_attack100', 1)[0]
    frames = [int(n) for n in re.findall(r"frame\(agent\.lua_state_agent, (\d+)\.0\);", game)]
    if (frames != list(range(2, 17, 2)) or
            game.count("macros::ATTACK(agent") != 8 or
            game.count("AttackModule::clear_all(agent.module_accessor)") != 8 or
            game.count("wait(agent.lua_state_agent, 1.0)") != 8 or
            game.count("macros::wait_loop_clear(agent)") != 1 or
            "Some(0.0), Some(5.5), Some(9.0)" not in game):
        raise ValueError("public Ultimate rapid-jab loop structure changed")
    return first


def host_templates(base: side.mex_hsd.Archive) -> tuple[list[int], list[int]]:
    """Use the two stock Kirby punch spheres as Melee field templates."""
    at = side.script_pointer(base, 50)
    for _ in range(16):
        op, words = side.command_at(base, at)
        if op == 5:
            sub = words[1]
            hit0, words0 = side.command_at(base, sub)
            hit1, words1 = side.command_at(base, sub + len(words0) * 4)
            if hit0 != 11 or hit1 != 11:
                raise ValueError("stock rapid-jab subroutine has no two hitboxes")
            return words0, words1
        at += len(words) * 4
    raise ValueError("stock rapid-jab subroutine was not found")


def make_loop(base: side.mex_hsd.Archive, hitbox: dict) -> tuple[list[int], int]:
    templates = host_templates(base)
    commands: list[tuple[int, int, list[int]]] = []
    for pulse, frame in enumerate(PULSE_FRAMES):
        for slot, z in ((0, 15.0), (1, 9.0)):
            box = copy.deepcopy(hitbox)
            box["slot"] = slot
            box["damage"] = PULSE_DAMAGE[pulse]
            box["offset"] = [0.0, 5.5, z]
            commands.append((frame, 1, normal.make_hitbox(box, templates[slot])))
        commands.append((frame + 1, 2, [16 << 26]))
        # Melee's rapid-jab Anim callback consumes this flag to decide whether
        # a released attack button should enter Attack100End.
        commands.append((frame + 1, 3, [20 << 26]))
    # The stock ftcmd uses WaitForAnimation before its self-goto. Without
    # this yield, the goto replays frame-zero commands indefinitely inside
    # the frame-16 interpreter tick.
    commands.append((16, 4, [8 << 26]))
    commands.append((16, 5, [7 << 26, 0]))
    commands.sort(key=lambda item: (item[0], item[1]))
    words: list[int] = []
    now = 0
    goto_index = -1
    for frame, _, cmd in commands:
        if frame > now:
            words.append((2 << 26) | frame)
            now = frame
        if cmd[0] >> 26 == 7:
            goto_index = len(words) + 1
        words.extend(cmd)
    if goto_index < 0 or words[-2] >> 26 != 7:
        raise ValueError("generated rapid-jab loop has no trailing goto")
    return words, goto_index


def read_loop(ar: side.mex_hsd.Archive, at: int) -> list[int]:
    words = []
    for _ in range(128):
        op, cmd = side.command_at(ar, at)
        words.extend(cmd)
        if op == 7:
            return words
        at += len(cmd) * 4
    raise ValueError("rapid-jab loop did not reach goto")


def decode_loop(words: list[int]) -> list[tuple[int, int, int]]:
    result = []
    frame = 0
    index = 0
    while index < len(words):
        op = words[index] >> 26
        count = side.COMMAND_WORDS[op]
        if op == 2:
            frame = max(frame, words[index] & 0x3FFFFFF)
        elif op in (11, 16, 20, 7):
            result.append((frame, op, words[index] & 0x3FF if op == 11 else 0))
        index += count
        if op == 7:
            break
    return result


def patch_archive(raw: bytes, vanilla: bytes, hitbox: dict) -> tuple[bytes, bool]:
    ar, base = side.mex_hsd.Archive(raw), side.mex_hsd.Archive(vanilla)
    if ar.public("ftDataKirby") != base.public("ftDataKirby"):
        raise ValueError("expected vanilla Kirby ftData layout")
    words, goto_index = make_loop(base, hitbox)
    current_at = side.script_pointer(ar, 50)
    expected_here = words.copy()
    expected_here[goto_index] = current_at
    if read_loop(ar, current_at) == expected_here:
        return raw, False
    data = bytearray(ar.data)
    while len(data) % 0x20:
        data.append(0)
    at = len(data)
    words[goto_index] = at
    data.extend(struct.pack(">%dI" % len(words), *words))
    table = side.motion_table(ar)
    struct.pack_into(">I", data, table + 50 * 0x18 + 0xC, at)
    relocs = sorted(set(ar.reloc_offsets) | {at + goto_index * 4})
    body = bytes(data) + b"".join(struct.pack(">I", offset) for offset in relocs) + ar.raw[ar.o_public:]
    header = struct.pack(">5I", 0x20 + len(body), len(data), len(relocs),
                         ar.nb_public, ar.nb_extern) + ar.raw[0x14:0x20]
    return header + body, True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ir", type=Path, default=DEFAULT_IR)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--mod", type=Path, default=DEFAULT_MOD)
    args = parser.parse_args()
    hitbox = source_hitbox(args.ir)
    target = args.mod / "files/PlKb.dat"
    vanilla = args.base.read_bytes()
    current = target.read_bytes() if target.exists() else vanilla
    output, changed = patch_archive(current, vanilla, hitbox)
    if changed or not target.exists():
        target.write_bytes(output)
    manifest_path = args.mod / "source-manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["rapid_jab"] = {
            "source_script": SOURCE_ID,
            "ir_sha256": hashlib.sha256(args.ir.read_bytes()).hexdigest(),
            "row": 50,
            "pulse_frames": list(PULSE_FRAMES),
            "source_damage_per_pulse": 0.2,
            "melee_damage_per_pulse": list(PULSE_DAMAGE),
            "damage_policy": "nearest whole-percent 16-frame cycle total; zero-damage hitboxes preserve pulse timing",
            "source_revision": "public ACMD, not yet binary-matched to local Ultimate 13.0.2 NRO",
        }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"rapid-jab loop row 50 {'updated' if changed else 'already current'}: {target}")


if __name__ == "__main__":
    main()
