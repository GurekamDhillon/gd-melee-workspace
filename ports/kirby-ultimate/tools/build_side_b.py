#!/usr/bin/env python3
"""Patch Ultimate Kirby's uncharged side-B hitboxes into a movement mod.

The existing mod's PlKb.dat is the destination: its movement attributes remain
intact. Melee Kirby supplies the side-special actions, clips, hammer placement,
effects, sound, and cleanup. Only ftcmd hitboxes/clears in motion rows 322/323
come from the named Ultimate IR scripts. No extracted game bytes are committed.
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
import mex_hsd  # noqa: E402

DEFAULT_IR = ROOT / "experiment/character-ir/instances/kirby.ultimate.ir.json"
DEFAULT_BASE = ROOT / "experiment/brawl-kirby/disc/PlKb.dat"
DEFAULT_MOD = ROOT / "_build/tmp/ultimate-kirby-mods/ultimate-kirby-movement"
SOURCE_IDS = {
    322: "script:kirby/specials/game_specials",
    323: "script:kirby/specialairs/game_specialairs",
}
# Opcode widths from Melee's ftAction_803C0870; see brawl-kirby/tools/melee_dump.py.
COMMAND_WORDS = [1, 1, 1, 1, 1, 2, 1, 2, 1, 1] + [
    5, 5, 1, 1, 1, 1, 1, 3, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 3, 1, 1, 1, 7, 4, 1, 1, 1, 1,
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 3, 3, 2, 1, 4,
]
assert len(COMMAND_WORDS) == 59
HITBOX_OPS = {11, 12, 13, 14, 15, 16}
ELEMENT = {"normal": 0, "fire": 1, "electric": 2, "slash": 3, "ice": 5,
           "darkness": 13, "flower": 15}


def motion_table(ar: mex_hsd.Archive) -> int:
    fd = ar.public("ftDataKirby")
    if fd + 0xC not in ar.reloc_set:
        raise ValueError("ftDataKirby has no motion-table relocation")
    return ar.u32(fd + 0xC)


def script_pointer(ar: mex_hsd.Archive, row: int) -> int:
    ptr_off = motion_table(ar) + row * 0x18 + 0xC
    if ptr_off not in ar.reloc_set:
        raise ValueError(f"motion row {row} has no script relocation")
    return ar.u32(ptr_off)


def command_at(ar: mex_hsd.Archive, offset: int) -> tuple[int, list[int]]:
    if offset + 4 > ar.data_size:
        raise ValueError(f"ftcmd pointer 0x{offset:X} outside data")
    op = ar.u32(offset) >> 26
    if op >= len(COMMAND_WORDS):
        raise ValueError(f"unknown ftcmd opcode {op} at 0x{offset:X}")
    count = COMMAND_WORDS[op]
    if offset + count * 4 > ar.data_size:
        raise ValueError(f"truncated ftcmd at 0x{offset:X}")
    return op, [ar.u32(offset + i * 4) for i in range(count)]


def flatten(ar: mex_hsd.Archive, row: int) -> list[tuple[int, int, list[int], list[int]]]:
    """Unroll Kirby's ftcmd loops while retaining source words and relocations."""
    offset, frame = script_pointer(ar, row), 0
    loops: list[list[int]] = []  # first command, repeats remaining
    events: list[tuple[int, int, list[int], list[int]]] = []
    for _ in range(2048):
        op, words = command_at(ar, offset)
        if op == 1:  # SyncWait
            frame += words[0] & 0x3FFFFFF
        elif op == 2:  # AsyncWait
            frame = max(frame, words[0] & 0x3FFFFFF)
        elif op == 3:  # SetLoop
            loops.append([offset + 4, words[0] & 0x3FFFFFF])
        elif op == 4:  # ExecLoop
            if not loops:
                raise ValueError(f"unmatched ExecLoop in row {row}")
            loops[-1][1] -= 1
            if loops[-1][1] > 0:
                offset = loops[-1][0]
                continue
            loops.pop()
        elif op in (5, 6, 7):
            raise ValueError(f"row {row} has unsupported ftcmd control opcode {op}")
        else:
            reloc_words = [i for i in range(len(words)) if offset + 4 * i in ar.reloc_set]
            events.append((frame, op, words, reloc_words))
            if op == 0:
                if loops:
                    raise ValueError(f"row {row} ends inside a loop")
                return events
        offset += 4 * len(words)
    raise ValueError(f"row {row} did not terminate within 2048 commands")


def linear_words(ar: mex_hsd.Archive, row: int) -> list[int]:
    """Current contiguous script words, for a byte-stable second invocation."""
    offset = script_pointer(ar, row)
    words: list[int] = []
    for _ in range(2048):
        op, cmd = command_at(ar, offset)
        words.extend(cmd)
        if op == 0:
            return words
        offset += 4 * len(cmd)
    raise ValueError(f"row {row} script is too long")


def source_scripts(ir: dict) -> dict[int, dict]:
    if ir.get("document_id") != "kirby.ultimate":
        raise ValueError("expected the kirby.ultimate IR")
    by_id = {s["id"]: s for s in ir["behavior"]["scripts"]}
    result = {}
    for row, sid in SOURCE_IDS.items():
        script = by_id[sid]
        if script["language"] != "ultimate.acmd.smashline_rust":
            raise ValueError(f"unexpected source language for {sid}")
        result[row] = script
    return result


def template_hitboxes(ar: mex_hsd.Archive, row: int) -> dict[int, list[int]]:
    result = {}
    for _, op, words, _ in flatten(ar, row):
        if op == 11:
            slot = (words[0] >> 23) & 7
            result.setdefault(slot, words)
    if set(result) < {0, 1}:
        raise ValueError(f"vanilla row {row} lacks side-B hitbox templates 0 and 1")
    return result


def bounded_int(value: float | int, name: str, maximum: int) -> int:
    integer = int(value)
    if integer != value or not 0 <= integer <= maximum:
        raise ValueError(f"{name}={value!r} cannot fit the Melee hitbox field")
    return integer


def make_hitbox(hitbox: dict, template: list[int]) -> list[int]:
    """Keep Melee hammer joint/offset/SFX flags; transfer IR combat fields."""
    if hitbox.get("joint_role") != "top":
        raise ValueError("uncharged side-B expects top-relative Ultimate hitboxes")
    damage = bounded_int(hitbox["damage"], "damage", 1023)
    angle = bounded_int(hitbox["angle"], "angle", 511)
    kbg = bounded_int(hitbox["knockback_growth"], "KBG", 511)
    wdsk = bounded_int(hitbox["weight_dependent_set_knockback"], "WDSK", 511)
    bkb = bounded_int(hitbox["base_knockback"], "BKB", 511)
    element = ELEMENT[hitbox["element"]]
    size = bounded_int(round(float(hitbox["size"]) * 256), "size*256", 65535)
    w0, w1, w2, w3, w4 = template
    return [
        (w0 & ~0x3FF) | damage,
        (w1 & 0xFFFF) | (size << 16),
        w2,
        (w3 & 0x1F) | (angle << 23) | (kbg << 14) | (wdsk << 5),
        (w4 & ~((0x1FF << 23) | (0x1F << 18))) | (bkb << 23) | (element << 18),
    ]


def make_script(host_events, ir_script: dict, templates: dict[int, list[int]]) -> tuple[list[int], list[int]]:
    ends = [frame for frame, op, _, _ in host_events if op == 0]
    if len(ends) != 1:
        raise ValueError("expected exactly one host End command")
    end_frame = ends[0]
    events = []  # frame, priority, insertion order, words, relocated word indices
    for order, (frame, op, words, relocs) in enumerate(host_events):
        if op not in HITBOX_OPS:
            events.append((frame, 2 if op == 0 else 0, order, words, relocs))
    for order, event in enumerate(ir_script["events"]):
        frame = bounded_int(event["frame"], "IR event frame", 1000)
        if event["op"] == "hitbox.create":
            hitbox = event["hitbox"]
            slot = bounded_int(hitbox["slot"], "hitbox slot", 7)
            if slot not in templates:
                raise ValueError(f"no Melee side-B template for slot {slot}")
            words = make_hitbox(hitbox, templates[slot])
        elif event["op"] == "hitbox.clear":
            words = [16 << 26]
        else:
            # Ultimate's article removal is not translated; Melee's original
            # SetCmdVar/End sequence keeps the hammer cleanup on this host.
            continue
        if frame >= end_frame:
            raise ValueError(f"IR hitbox event at {frame} exceeds host End at {end_frame}")
        events.append((frame, 1, order, words, []))
    events.sort(key=lambda e: (e[0], e[1], e[2]))
    words_out, relocated = [], []
    frame_now = 0
    for frame, _, _, words, relocs in events:
        if frame > frame_now:
            words_out.append((2 << 26) | frame)  # AsyncWait
            frame_now = frame
        start = len(words_out)
        words_out.extend(words)
        relocated.extend(start + i for i in relocs)
    if not words_out or words_out[-1] != 0:
        raise ValueError("rebuilt side-B script has no End")
    return words_out, relocated


def patch_archive(raw: bytes, vanilla: bytes, sources: dict[int, dict]) -> tuple[bytes, list[int]]:
    ar, base = mex_hsd.Archive(raw), mex_hsd.Archive(vanilla)
    if ar.public("ftDataKirby") != base.public("ftDataKirby"):
        raise ValueError("mod fighter data does not have vanilla Kirby's ftData layout")
    data = bytearray(ar.data)
    new_relocs = set(ar.reloc_offsets)
    changed = []
    table = motion_table(ar)
    for row in SOURCE_IDS:
        script, rel_words = make_script(flatten(ar, row), sources[row], template_hitboxes(base, row))
        if linear_words(ar, row) == script:
            continue
        while len(data) % 0x20:
            data.append(0)
        at = len(data)
        data.extend(struct.pack(">%dI" % len(script), *script))
        for index in rel_words:
            new_relocs.add(at + 4 * index)
        struct.pack_into(">I", data, table + row * 0x18 + 0xC, at)
        changed.append(row)
    if not changed:
        return raw, []
    relocs = sorted(new_relocs)
    tail = ar.raw[ar.o_public:]
    body = bytes(data) + b"".join(struct.pack(">I", offset) for offset in relocs) + tail
    header = struct.pack(">5I", 0x20 + len(body), len(data), len(relocs),
                         ar.nb_public, ar.nb_extern) + ar.raw[0x14:0x20]
    return header + body, changed


def update_metadata(mod_dir: Path, ir_bytes: bytes, sources: dict[int, dict]) -> None:
    mod_path = mod_dir / "mod.json"
    manifest_path = mod_dir / "source-manifest.json"
    mod = json.loads(mod_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if mod.get("id") != "ultimate-kirby-movement":
        raise ValueError("side-B builder expects the ultimate-kirby-movement pack")
    if "side B" not in mod["name"]:
        mod["name"] += " + side B"
    if "side B" not in mod["description"]:
        mod["description"] += (" Uncharged side B uses Ultimate Kirby IR hitbox damage and timing "
                               "on Melee Kirby's existing hammer actions.")
    manifest["side_b"] = {
        "target_motion_rows": {"ground": 322, "air": 323},
        "ir_scripts": list(SOURCE_IDS.values()),
        "ir_provenance": {sources[row]["id"]: sources[row].get("provenance", {})
                          for row in SOURCE_IDS},
        "source_ir_sha256": hashlib.sha256(ir_bytes).hexdigest(),
        "source_revision_status": "Public readable ACMD dump not version-matched to local Ultimate 13.0.2 NRO.",
        "translation": "Only uncharged hitbox create/clear events; Melee hammer joint/offsets, visuals, sound, state mechanics and cleanup remain.",
        "unsupported": ["Ultimate hammer article", "charged variants", "Ultimate action/state logic"],
    }
    mod_path.write_text(json.dumps(mod, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ir", type=Path, default=DEFAULT_IR)
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    parser.add_argument("--mod", type=Path, default=DEFAULT_MOD)
    args = parser.parse_args()
    target = args.mod / "files/PlKb.dat"
    ir_bytes = args.ir.read_bytes()
    sources = source_scripts(json.loads(ir_bytes))
    # Validate metadata before touching the fighter file.
    if not (args.mod / "mod.json").is_file() or not (args.mod / "source-manifest.json").is_file():
        raise FileNotFoundError("run build_movement.py first to create the mod and manifest")
    vanilla = args.base.read_bytes()
    had_payload = target.is_file()
    raw, changed = patch_archive(target.read_bytes() if had_payload else vanilla, vanilla, sources)
    if changed or not had_payload:
        target.write_bytes(raw)
    update_metadata(args.mod, ir_bytes, sources)
    print(f"side B rows {changed or 'already current'}: {target}")


if __name__ == "__main__":
    main()
