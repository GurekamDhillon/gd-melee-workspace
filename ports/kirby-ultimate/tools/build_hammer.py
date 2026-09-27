#!/usr/bin/env python3
"""Add native Ultimate Kirby Hammer charge states to an isolated movement pack.

Rows 4/5/18 are empty in vanilla Kirby's 479-row motion table. This pass uses
them for a harmless hold animation and charged ground/air release payloads.
The Geno host behaviour supplies charge, hold walk, and release selection; the
existing Melee status route still supplies ordinary uncharged side-B outside
this profile. This is an incremental native mechanics prototype: Hammer article
creation and Ultimate start/turn/jump/landing transitions remain separate work.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct

import build_side_b as side_b

ROOT = Path(__file__).resolve().parents[3]
IR = ROOT / "experiment/character-ir/instances/kirby.ultimate.ir.json"
MOD = ROOT / "_build/tmp/ultimate-kirby-mods/ultimate-kirby-movement"
ROWS = {4: 6, 5: 322, 18: 323}
MAX_IDS = {5: "script:kirby/specialsmax/game_specialsmax",
           18: "script:kirby/specialairsmax/game_specialairsmax"}


def empty_row(ar: side_b.mex_hsd.Archive, table: int, row: int) -> bool:
    words = struct.unpack_from(">6I", ar.data, table + row * 0x18)
    return words[:4] == (0, 0, 0, 0) and words[5] == 0 and words[4] != 0


def patch_fighter(raw: bytes, vanilla: bytes, scripts: dict[int, dict]) -> tuple[bytes, list[int]]:
    ar, base = side_b.mex_hsd.Archive(raw), side_b.mex_hsd.Archive(vanilla)
    table = side_b.motion_table(ar)
    if table != side_b.motion_table(base):
        raise ValueError("Hammer builder needs Kirby's original 479-row motion table")
    data = bytearray(ar.data)
    relocs = set(ar.reloc_offsets)
    changed = []
    for row, source in ROWS.items():
        if not empty_row(base, side_b.motion_table(base), row):
            raise ValueError(f"vanilla Kirby row {row} is not empty")
        target = table + row * 0x18
        origin = table + source * 0x18
        if not empty_row(ar, table, row):
            # Reruns may update the charged payload when upstream side B changes,
            # but may not overwrite another author’s use of these reserved rows.
            if (ar.u32(target) != ar.u32(origin) or
                ar.u32(target + 4) != ar.u32(origin + 4) or
                ar.u32(target + 8) != ar.u32(origin + 8)):
                raise ValueError(f"motion row {row} is already occupied")
        data[target:target + 0x18] = ar.data[origin:origin + 0x18]
        for word in range(6):
            dst, src = target + 4 * word, origin + 4 * word
            if src in ar.reloc_set:
                relocs.add(dst)
            else:
                relocs.discard(dst)
        if row in MAX_IDS:
            host = side_b.flatten(ar, source)
            templates = side_b.template_hitboxes(base, source)
            words, script_relocs = side_b.make_script(host, scripts[row], templates)
            if (not empty_row(ar, table, row) and
                    side_b.linear_words(ar, row) == words):
                pointer = ar.u32(target + 0xC)
            else:
                while len(data) % 0x20:
                    data.append(0)
                pointer = len(data)
                data.extend(struct.pack(">%dI" % len(words), *words))
                relocs.update(pointer + 4 * index for index in script_relocs)
                changed.append(row)
            struct.pack_into(">I", data, target + 0xC, pointer)
            relocs.add(target + 0xC)
        elif empty_row(ar, table, row):
            changed.append(row)
    if not changed:
        return raw, []
    while len(data) % 4:
        data.append(0)
    ordered = sorted(relocs)
    body = bytes(data) + b"".join(struct.pack(">I", offset) for offset in ordered) + ar.raw[ar.o_public:]
    header = (struct.pack(">5I", 0x20 + len(body), len(data), len(ordered), ar.nb_public, ar.nb_extern)
              + ar.raw[0x14:0x20])
    return header + body, changed


def hammer_params(ir: dict) -> dict[str, float]:
    fields = {item["engine_name"]: item["value"]
              for item in ir["behavior"]["attributes"]["special"]["fields"]}
    return {name: float(fields[name]) for name in ("hold_max_f", "charge_speed", "hold_walk_speed_x")}


def patch_profile(profile: dict, ir: dict) -> dict:
    fighters = profile.get("fighters", [])
    if len(fighters) != 1 or fighters[0].get("attach") not in ("kirby", "PlKb.dat"):
        raise ValueError("Hammer builder needs one Kirby Geno fighter profile")
    fighter = fighters[0]
    if fighter.get("states") or fighter.get("specials"):
        raise ValueError("Hammer builder needs a profile without prior Geno states/specials")
    fighter["hammer"] = hammer_params(ir)
    fighter["states"] = [
        {"name": "HammerHold", "behavior": "geno.hammer.hold", "subaction": 4,
         "like": "motion:14", "next": "geno:HammerWeak", "charged_next": "geno:HammerMax"},
        {"name": "HammerWeak", "behavior": "geno.ground", "subaction": 322,
         "like": "motion:383", "next": "auto"},
        {"name": "HammerMax", "behavior": "geno.ground", "subaction": 5,
         "like": "motion:383", "next": "auto"},
        {"name": "HammerHoldAir", "behavior": "geno.hammer.hold", "subaction": 4,
         "like": "motion:29", "next": "geno:HammerWeakAir", "charged_next": "geno:HammerMaxAir"},
        {"name": "HammerWeakAir", "behavior": "geno.air", "subaction": 323,
         "like": "motion:384", "next": "auto"},
        {"name": "HammerMaxAir", "behavior": "geno.air", "subaction": 18,
         "like": "motion:384", "next": "auto"},
    ]
    fighter["specials"] = {"s": "geno:HammerHold", "air_s": "geno:HammerHoldAir"}
    return profile


def install(mod: Path, ir_path: Path, vanilla_path: Path) -> list[int]:
    ir_bytes = ir_path.read_bytes()
    ir = json.loads(ir_bytes)
    if ir.get("document_id") != "kirby.ultimate":
        raise ValueError("expected Ultimate Kirby IR")
    by_id = {script["id"]: script for script in ir["behavior"]["scripts"]}
    scripts = {row: by_id[id_] for row, id_ in MAX_IDS.items()}
    fighter_path = mod / "files/PlKb.dat"
    profile_path = mod / "geno.json"
    original = fighter_path.read_bytes()
    updated, changed = patch_fighter(original, vanilla_path.read_bytes(), scripts)
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    marker = mod / "hammer-build.json"
    if marker.is_file() and profile["fighters"][0].get("states"):
        prior = json.loads(marker.read_text(encoding="utf-8"))
        if (not changed and prior.get("fighter_sha256") == hashlib.sha256(updated).hexdigest()
                and prior.get("ir_sha256") == hashlib.sha256(ir_bytes).hexdigest()):
            return []
    updated_profile = patch_profile(profile, ir)
    fighter_path.write_bytes(updated)
    profile_path.write_text(json.dumps(updated_profile, indent=2) + "\n", encoding="utf-8")
    marker.write_text(json.dumps({"ir_sha256": hashlib.sha256(ir_bytes).hexdigest(),
                                  "fighter_sha256": hashlib.sha256(updated).hexdigest(),
                                  "rows": {"hold": 4, "weak": 322, "max": 5,
                                           "hold_air": 4, "weak_air": 323, "max_air": 18}},
                                 indent=2) + "\n", encoding="utf-8")
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mod", type=Path, default=MOD)
    parser.add_argument("--ir", type=Path, default=IR)
    parser.add_argument("--vanilla", type=Path, default=side_b.DEFAULT_BASE)
    args = parser.parse_args()
    print(f"Hammer rows {install(args.mod, args.ir, args.vanilla)}: {args.mod}")


if __name__ == "__main__":
    main()
