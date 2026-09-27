#!/usr/bin/env python3
"""Port Ultimate Final Cutter wave combat and travel into Kirby article0.

The item-state script is separate from the fighter's ftcmd motion table. This
pass preserves the article model pointer, all other articles, and every fighter
motion row. The source's later capsule is represented by two same-group item
hit spheres at its endpoints because Melee's itemcmd has one center per sphere.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

import build_side_b as side
import build_normals as normals

ROOT = Path(__file__).resolve().parents[3]
IR = ROOT / "experiment/character-ir/instances/kirby.ultimate.ir.json"
BASE = ROOT / "experiment/brawl-kirby/disc/PlKb.dat"
MOD = ROOT / "_build/tmp/ultimate-kirby-mods/ultimate-kirby-movement"
SOURCE_ID = "script:kirby_finalcuttershot/finalcutterregular/game_finalcutterregular"
PREFIX = "ssbu.finalcuttershot."


def source_script(ir: dict) -> dict:
    if ir.get("document_id") != "kirby.ultimate":
        raise ValueError("expected Ultimate Kirby IR")
    scripts = [s for s in ir["behavior"]["scripts"] if s["id"] == SOURCE_ID]
    if len(scripts) != 1:
        raise ValueError("Final Cutter wave source script is missing or duplicated")
    return scripts[0]


def source_hitboxes(ir: dict) -> tuple[dict, dict, list[float]]:
    events = [e for e in source_script(ir)["events"] if e["op"].startswith("hitbox.")]
    if len(events) != 2 or [(e["frame"], e["op"]) for e in events] != [
        (0, "hitbox.create"), (2, "hitbox.create")
    ]:
        raise ValueError("Final Cutter wave source timeline changed")
    first, second = (e["hitbox"] for e in events)
    if [(h["slot"], h["group"], h["damage"], h["joint_role"], h["element"])
            for h in (first, second)] != [
                (0, 0, 5, "top", "slash"), (0, 0, 6, "top", "slash")
            ]:
        raise ValueError("Final Cutter wave source hitbox shape changed")
    args = second["engine"]["ssbu.switch"]["arguments"]
    if len(args) < 16:
        raise ValueError("Final Cutter wave source capsule arguments are absent")
    endpoint = []
    for value in args[13:16]:
        match = re.fullmatch(r"Some\((-?\d+(?:\.\d+)?)\)", value)
        if not match:
            raise ValueError("Final Cutter wave source capsule endpoint changed")
        endpoint.append(float(match.group(1)))
    if endpoint != [0.0, 9.0, -9.6]:
        raise ValueError("Final Cutter wave source capsule endpoint changed")
    return first, second, endpoint


def source_params(ir: dict) -> dict[str, float]:
    fields = ir["behavior"]["attributes"]["special"]["fields"]
    values = {f["key"][len(PREFIX):]: f["value"] for f in fields
              if f["key"].startswith(PREFIX)}
    expected = {"speed": 4.8, "life": 19.0, "brake": 0.28,
                "angle": 0.0, "is_penetration": 0}
    if any(values.get(key) != value for key, value in expected.items()):
        raise ValueError("Final Cutter wave source parameters changed")
    return values


def article_layout(ar: side.mex_hsd.Archive) -> tuple[int, int, int]:
    root = ar.public("ftDataKirby")
    items = ar.u32(root + 0x48)
    article = ar.u32(items)
    attr = ar.u32(article + 4)
    state = ar.u32(article + 0xC)
    if any(at not in ar.reloc_set for at in
           (root + 0x48, items, article + 4, article + 0xC, state + 0xC)):
        raise ValueError("Kirby article0 pointer chain lacks expected relocations")
    if attr == 0 or state == 0:
        raise ValueError("Kirby article0 has no attributes or item state")
    return article, attr, state


def article_script(ar: side.mex_hsd.Archive) -> list[int]:
    _, _, state = article_layout(ar)
    at = ar.u32(state + 0xC)
    words = []
    for _ in range(64):
        word = ar.u32(at)
        op = word >> 26
        size = {0: 1, 2: 1, 11: 6}.get(op)
        if size is None:
            raise ValueError(f"unexpected cutter itemcmd opcode {op}")
        words.extend(ar.u32(at + 4 * i) for i in range(size))
        at += 4 * size
        if op == 0:
            return words
    raise ValueError("cutter itemcmd never ended")


def _fixed(value: float) -> int:
    number = round(value * normals.COORD_SCALE * 256)
    if not -32768 <= number <= 32767:
        raise ValueError("Final Cutter wave coordinate overflows itemcmd")
    return number & 0xFFFF


def _bounded(value: int | float, label: str, maximum: int) -> int:
    if not isinstance(value, (int, float)) or int(value) != value or not 0 <= value <= maximum:
        raise ValueError(f"Final Cutter wave {label} out of range")
    return int(value)


def item_hitbox(hit: dict, template: list[int], slot: int, offset: list[float]) -> list[int]:
    if len(template) != 6 or len(offset) != 3:
        raise ValueError("invalid Final Cutter wave hitbox template or endpoint")
    group = _bounded(hit["group"], "group", 7)
    damage = _bounded(hit["damage"], "damage", 8191)
    angle = _bounded(hit["angle"], "angle", 511)
    kbg = _bounded(hit["knockback_growth"], "KBG", 511)
    wds = _bounded(hit.get("weight_dependent_set_knockback", 0), "WDSK", 511)
    bkb = _bounded(hit["base_knockback"], "BKB", 511)
    size = _bounded(round(float(hit["size"]) * normals.COORD_SCALE * 256), "radius*256", 65535)
    x, y, z = map(_fixed, offset)
    element = side.ELEMENT[hit["element"]]
    w0, _, _, w3, w4, w5 = template
    return [
        (w0 & ~((7 << 23) | (7 << 20) | 0x1FFF)) |
        (slot << 23) | (group << 20) | damage,
        (size << 16) | x,
        (y << 16) | z,
        (w3 & 0x1F) | (angle << 23) | (kbg << 14) | (wds << 5),
        (w4 & ~((0x1FF << 23) | (0x1F << 18))) | (bkb << 23) | (element << 18),
        # Stock cutter wave permits a repeat hit after 16 frames. Retain a
        # victim for this 19-frame projectile's full life so a later phase
        # cannot deal the same 6% hit again.
        w5 & 0x00FFFFFF,
    ]


def target_script(ir: dict, host: list[int]) -> list[int]:
    if len(host) != 7 or host[0] >> 26 != 11 or host[-1] != 0:
        raise ValueError("vanilla Final Cutter wave itemcmd is not one hitbox and End")
    first, second, endpoint = source_hitboxes(ir)
    template = host[:6]
    return (item_hitbox(first, template, 0, first["offset"]) +
            [(2 << 26) | 2] +
            item_hitbox(second, template, 0, second["offset"]) +
            item_hitbox(second, template, 1, endpoint) + [0])


def patch_fighter(raw: bytes, vanilla: bytes, ir: dict) -> tuple[bytes, bool]:
    ar, base = side.mex_hsd.Archive(raw), side.mex_hsd.Archive(vanilla)
    if ar.public("ftDataKirby") != base.public("ftDataKirby"):
        raise ValueError("Final Cutter wave needs Kirby's original fighter-data layout")
    source_params(ir)
    base_article, base_attr, _ = article_layout(base)
    article, attr, state = article_layout(ar)
    if article != base_article or attr != base_attr:
        raise ValueError("Final Cutter wave article0 attributes moved unexpectedly")
    baseline = article_script(base)
    expected = target_script(ir, baseline)
    current = article_script(ar)
    target_attrs = (4.8, 19.0, 0.28)
    attr_offsets = (0, 8, 12)
    target_bytes = tuple(struct.pack(">f", value) for value in target_attrs)
    current_bytes = tuple(bytes(ar.data[attr + i:attr + i + 4]) for i in attr_offsets)
    baseline_bytes = tuple(bytes(base.data[base_attr + i:base_attr + i + 4])
                           for i in attr_offsets)
    if current == expected and current_bytes == target_bytes:
        return raw, False
    if current != baseline or current_bytes != baseline_bytes:
        raise ValueError("Final Cutter wave article0 script or attributes were changed by another pass")

    data = bytearray(ar.data)
    for offset, value in zip(attr_offsets, target_attrs):
        struct.pack_into(">f", data, attr + offset, value)
    while len(data) % 0x20:
        data.append(0)
    script_at = len(data)
    data.extend(struct.pack(">{}I".format(len(expected)), *expected))
    struct.pack_into(">I", data, state + 0xC, script_at)
    relocs = sorted(set(ar.reloc_offsets))
    body = bytes(data) + b"".join(struct.pack(">I", offset) for offset in relocs) + ar.raw[ar.o_public:]
    header = struct.pack(">5I", 0x20 + len(body), len(data), len(relocs),
                         ar.nb_public, ar.nb_extern) + ar.raw[0x14:0x20]
    result = header + body
    check = side.mex_hsd.Archive(result)
    if article_script(check) != expected:
        raise ValueError("packed Final Cutter wave script did not round-trip")
    return result, True


def install(mod: Path, ir_path: Path = IR, base_path: Path = BASE) -> bool:
    meta_path, manifest_path = mod / "mod.json", mod / "source-manifest.json"
    fighter_path = mod / "files/PlKb.dat"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if meta.get("id") != "ultimate-kirby-movement":
        raise ValueError("Final Cutter wave builder needs Ultimate Kirby movement pack")
    ir_bytes = ir_path.read_bytes()
    ir = json.loads(ir_bytes)
    result, changed = patch_fighter(fighter_path.read_bytes(), base_path.read_bytes(), ir)
    if changed:
        fighter_path.write_bytes(result)
    if "Final Cutter wave" not in meta["name"]:
        meta["name"] += " + Final Cutter wave"
    if "wave article" not in meta["description"]:
        meta["description"] += " Ultimate Final Cutter wave article travel and hitbox phases."
    manifest["final_cutter_wave"] = {
        "article_index": 0,
        "ir_script": SOURCE_ID,
        "ir_sha256": hashlib.sha256(ir_bytes).hexdigest(),
        "travel": {"speed": 4.8, "life": 19.0, "brake": 0.28},
        "hitbox_phases": [{"frame": 0, "damage": 5, "angle": 70},
                           {"frame": 2, "damage": 6, "angle": 361}],
        "capsule_mapping": "Later Ultimate capsule uses two same-group Melee item spheres at its endpoints.",
        "rehit_policy": "Clear stock Melee item's 16-frame rehit timer so one 19-frame wave cannot strike the same victim twice.",
        "verification": "Ground and air Final Cutter spawned this item in the native slot; live item state showed the travel values and both hitbox phases. A ranged Fox collision produced one 6% item hit after the rehit fix.",
        "limits": "Opponent collision outcome, penetration behavior, and visual mesh still require live QA.",
    }
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mod", type=Path, default=MOD)
    parser.add_argument("--ir", type=Path, default=IR)
    parser.add_argument("--base", type=Path, default=BASE)
    args = parser.parse_args()
    print(f"Final Cutter wave article0 changed: {install(args.mod, args.ir, args.base)}")


if __name__ == "__main__":
    main()
