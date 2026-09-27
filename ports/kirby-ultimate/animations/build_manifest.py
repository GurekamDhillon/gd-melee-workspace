"""Resolve the Kirby motion clips used by the LAB proof against the local Ultimate IR.

Only names, source digests, decoded frame counts, and intended Melee motion rows
are emitted. Animation data stays in the ignored, private Ultimate extraction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

import yaml


# Ultimate motion filename, Melee Kirby motion rows, and mapping note. The side B
# clip is a candidate for both host actions; Ultimate's full start/hold/release
# status graph cannot be represented by Melee's two hammer rows alone.
SELECTED = (
    ("a00wait1", (2,), "name_match"),
    ("a01walkslow", (7,), "name_match"),
    ("a01walkmiddle", (8,), "name_match"),
    ("a01walkfast", (9,), "name_match"),
    ("a02dash", (12,), "name_match"),
    ("a02run", (13,), "name_match"),
    ("a03jumpf", (16,), "name_match"),
    ("a03jumpb", (17,), "name_match"),
    ("a03jumpaerialf", (295, 300), "shared_metal_jump_visual"),
    ("a03jumpaerialf2", (296, 301), "shared_metal_jump_visual"),
    ("a03jumpaerialf3", (297, 302), "shared_metal_jump_visual"),
    ("a03jumpaerialf4", (298, 303), "shared_metal_jump_visual"),
    ("a03jumpaerialf5", (299, 304), "shared_metal_jump_visual"),
    ("a04fall", (20,), "name_match"),
    ("a05squat", (30,), "name_match"),
    ("a05squatwait", (31,), "name_match"),
    ("a05squatwait2", (32,), "name_match"),
    ("a05squatrv", (34,), "name_match"),
    ("c00attack11", (46,), "ultimate_normal_attack"),
    ("c00attack12", (47,), "ultimate_normal_attack"),
    ("c00attackend", (51,), "ultimate_rapid_jab_end"),
    ("c00attackdash", (52,), "ultimate_normal_attack"),
    ("c01attacks3hi", (53,), "ultimate_normal_attack_variant"),
    ("c01attacks3s", (55,), "ultimate_normal_attack"),
    ("c01attacks3lw", (57,), "ultimate_normal_attack_variant"),
    ("c02attackhi3", (58,), "ultimate_normal_attack"),
    ("c02attacklw3", (59,), "ultimate_normal_attack"),
    ("c03attacks4s", (62,), "ultimate_normal_attack"),
    ("c03attacks4hi", (60,), "ultimate_normal_attack_variant"),
    ("c03attacks4lw", (64,), "ultimate_normal_attack_variant"),
    ("c04attackhi4", (66,), "ultimate_normal_attack"),
    ("c04attacklw4", (67,), "ultimate_normal_attack"),
    ("c05attackairn", (68,), "ultimate_normal_attack"),
    ("c05attackairf", (69,), "ultimate_normal_attack"),
    ("c05attackairb", (70,), "ultimate_normal_attack"),
    ("c05attackairhi", (71,), "ultimate_normal_attack"),
    ("c05attackairlw", (72,), "ultimate_normal_attack"),
    ("f03downattacku", (187,), "ultimate_ground_recovery_attack"),
    ("f04downattackd", (195,), "ultimate_ground_recovery_attack"),
    ("g02cliffattack", (221, 222), "ultimate_shared_cliff_attack"),
    ("e00catch", (242,), "ultimate_standing_grab"),
    ("e00catchdash", (243,), "ultimate_dash_grab"),
    ("e00catchattack", (245,), "ultimate_pummel"),
    ("e01throwf", (247,), "ultimate_throw"),
    ("e01throwb", (248,), "ultimate_throw"),
    ("e01throwhi", (249,), "ultimate_throw"),
    ("e01throwlw", (250,), "ultimate_throw"),
    ("d01specials", (322,), "ultimate_ground_side_b_release"),
    ("d01specialairs", (323,), "ultimate_aerial_side_b_release"),
    ("d02specialhi", (324,), "ultimate_ground_up_b_phase_1"),
    ("d02specialhi2", (325,), "ultimate_ground_up_b_phase_2"),
    ("d02specialhi3", (326, 330), "ultimate_up_b_shared_phase_3"),
    ("d02specialhi4", (327, 331), "ultimate_up_b_shared_phase_4"),
    ("d02specialairhi", (328,), "ultimate_aerial_up_b_phase_1"),
    ("d02specialairhi2", (329,), "ultimate_aerial_up_b_phase_2"),
)

# Remaining stock Kirby actions with a directly corresponding Ultimate c00
# motion. Multiple Melee rows sometimes share one Ultimate clip where Melee
# splits a directional or speed variant that Ultimate does not.
ADDITIONAL = (
    ("g00walldamage", (0, 212), "shared_wall_damage"),
    ("a04damagefall", (1, 29, 137, 287), "shared_damage_fall"),
    ("a00wait2", (3,), "name_match"),
    ("a00waititem", (6,), "name_match"),
    ("a01turn", (10,), "name_match"),
    ("a02turnrun", (11,), "name_match"),
    ("a02runbraker", (14,), "right_run_brake_for_shared_row"),
    ("a05landinglight", (15, 35), "light_landing_for_shared_row"),
    ("a05landingheavy", (36,), "heavy_landing"),
    ("a04fallf", (21,), "name_match"),
    ("a04fallb", (22,), "name_match"),
    ("a04fallaerial", (23,), "name_match"),
    ("a04fallaerialf", (24,), "name_match"),
    ("a04fallaerialb", (25,), "name_match"),
    ("a04fallspecial", (26, 27, 28), "shared_special_fall"),
    ("a05squatwaititem", (33,), "name_match"),
    ("b00guardon", (37,), "name_match"),
    ("b00guard", (38,), "name_match"),
    ("b00guardoff", (39,), "name_match"),
    ("b01guarddamage", (40,), "name_match"),
    ("b02escapen", (41,), "name_match"),
    ("b02escapef", (42,), "name_match"),
    ("b02escapeb", (43,), "name_match"),
    ("b02escapeair", (44,), "name_match"),
    ("b02rebound", (45,), "name_match"),
    ("c00attack100start", (49,), "ultimate_rapid_jab_start"),
    ("c00attack100", (50,), "ultimate_rapid_jab_loop"),
    ("c05landingairn", (73,), "name_match"),
    ("c05landingairf", (74,), "name_match"),
    ("c05landingairb", (75,), "name_match"),
    ("c05landingairhi", (76,), "name_match"),
    ("c05landingairlw", (77,), "name_match"),
    ("f00damagehi1", (165,), "name_match"),
    ("f00damagehi2", (166,), "name_match"),
    ("f00damagehi3", (167,), "name_match"),
    ("f00damagen1", (168,), "name_match"),
    ("f00damagen2", (169,), "name_match"),
    ("f00damagen3", (170,), "name_match"),
    ("f00damagelw1", (171,), "name_match"),
    ("f00damagelw2", (172,), "name_match"),
    ("f00damagelw3", (173,), "name_match"),
    ("f01damageair1", (174,), "name_match"),
    ("f01damageair2", (175,), "name_match"),
    ("f01damageair3", (176,), "name_match"),
    ("f01damageflyhi", (177,), "name_match"),
    ("f01damageflyn", (178,), "name_match"),
    ("f01damageflylw", (179,), "name_match"),
    ("f01damageflytop", (180, 286), "shared_damage_fly_top"),
    ("f01damageflyroll", (181,), "name_match"),
    ("f03downboundu", (183, 288), "shared_down_bound"),
    ("f03downwaitu", (184,), "name_match"),
    ("f03downdamageu", (185,), "name_match"),
    ("f03downstandu", (186, 290), "shared_down_stand"),
    ("f03downforwardu", (188,), "name_match"),
    ("f03downbacku", (189,), "name_match"),
    ("f03downspotu", (190,), "name_match"),
    ("f04downboundd", (191, 289), "shared_down_bound"),
    ("f04downwaitd", (192,), "name_match"),
    ("f04downdamaged", (193,), "name_match"),
    ("f04downstandd", (194, 291), "shared_down_stand"),
    ("f04downforwardd", (196,), "name_match"),
    ("f04downbackd", (197,), "name_match"),
    ("f05passive", (199,), "name_match"),
    ("f05passivestandf", (200,), "name_match"),
    ("f05passivestandb", (201,), "name_match"),
    ("f05passivewall", (202,), "name_match"),
    ("f05passivewalljump", (203,), "name_match"),
    ("f05passiveceil", (204,), "name_match"),
    ("f06furafura", (205,), "name_match"),
    ("g00pass", (209,), "name_match"),
    ("g00ottotto", (210,), "name_match"),
    ("g00ottottowait", (211,), "name_match"),
    ("g00stopwall", (213,), "name_match"),
    ("g00stopceil", (214,), "name_match"),
    ("g00missfoot", (215,), "name_match"),
    ("g01cliffcatch", (216,), "name_match"),
    ("g01cliffwait", (217,), "name_match"),
    ("g02cliffclimb", (219, 220), "shared_ledge_climb_speed"),
    ("g02cliffescape", (223, 224), "shared_ledge_escape_speed"),
    ("g02cliffjump1", (225, 227), "shared_ledge_jump_speed_phase_1"),
    ("g02cliffjump2", (226, 228), "shared_ledge_jump_speed_phase_2"),
    ("e00catchwait", (244,), "name_match"),
    ("e00catchcut", (246,), "name_match"),
    ("e02capturepulledhi", (251,), "name_match"),
    ("e02capturewaithi", (252,), "name_match"),
    ("e02capturedamagehi", (253,), "name_match"),
    ("e03capturepulledlw", (254,), "name_match"),
    ("e03capturewaitlw", (255,), "name_match"),
    ("e03capturedamagelw", (256,), "name_match"),
    ("e03capturecut", (257,), "name_match"),
    ("e03capturejump", (258,), "name_match"),
    ("d00specialnstart", (305,), "ultimate_ground_inhale_start"),
    ("d00specialnloop", (306,), "ultimate_ground_inhale_loop"),
    ("d00specialnend", (307,), "ultimate_ground_inhale_end"),
    ("d00specialnswallow", (308,), "ultimate_inhale_capture"),
    ("d00specialneat", (309,), "ultimate_ground_eat"),
    ("d00eatwait", (310,), "name_match"),
    ("d00eatwalkslow", (311,), "name_match"),
    ("d00eatwalkmiddle", (312,), "name_match"),
    ("d00eatwalkfast", (313,), "name_match"),
    ("d00eatjump1", (314,), "name_match"),
    ("d00eatjump2", (315,), "name_match"),
    ("d00eatlanding", (316,), "name_match"),
    ("d00eatturn", (317,), "name_match"),
    ("d00specialndrink", (318,), "name_match"),
    ("d00specialnspit", (319,), "name_match"),
    ("d00specialairnstart", (320,), "ultimate_air_inhale_start"),
    ("d00specialairnloop", (321,), "ultimate_air_inhale_loop"),
    ("d03speciallw1", (332,), "ultimate_ground_stone_start"),
    ("d03speciallw2", (333,), "ultimate_ground_stone_hold"),
    ("d03specialairlw1", (335,), "ultimate_air_stone_start"),
    ("d03specialairlw2", (336,), "ultimate_air_stone_hold"),
)

# Item handling is shared with Melee's native item status graph. Repeated rows
# are the same animation played while holding a different item class; the
# installer still keeps each Melee row's public symbol and stock root curve.
ITEMS = (
    ("h00lightget", (78,), "item_name_match"),
    ("h01lightthrowf", (79, 96), "shared_light_throw"),
    ("h01lightthrowb", (80, 97), "shared_light_throw"),
    ("h01lightthrowhi", (81, 98), "shared_light_throw"),
    ("h01lightthrowlw", (82, 99), "shared_light_throw"),
    ("h01lightthrowdash", (83,), "item_name_match"),
    ("h01lightthrowdrop", (84,), "item_name_match"),
    ("h02lightthrowairf", (85, 100), "shared_air_light_throw"),
    ("h02lightthrowairb", (86, 101), "shared_air_light_throw"),
    ("h02lightthrowairhi", (87, 102), "shared_air_light_throw"),
    ("h02lightthrowairlw", (88, 103), "shared_air_light_throw"),
    ("h03heavyget", (89,), "item_name_match"),
    ("h03heavywalk", (90, 91), "shared_heavy_walk_speed"),
    ("h03heavythrowf", (92, 104), "shared_heavy_throw"),
    ("h03heavythrowb", (93, 105), "shared_heavy_throw"),
    ("h03heavythrowhi", (94, 106), "shared_heavy_throw"),
    ("h03heavythrowlw", (95, 107), "shared_heavy_throw"),
    ("h04swing1", (108, 112, 116, 120, 124, 128), "shared_item_swing"),
    ("h04swing3", (109, 113, 117, 121, 125, 129), "shared_item_swing"),
    ("h04swing4", (110, 114, 118, 122, 126, 130), "shared_item_swing"),
    ("h04swingdash", (111, 115, 119, 123, 127, 131), "shared_item_swing"),
    ("h05itemhammerwait", (132,), "item_name_match"),
    ("h05itemhammermove", (133,), "item_name_match"),
    ("h11itemshoot", (138, 140, 142), "shared_item_shoot"),
    ("h11itemshootair", (139, 141, 143), "shared_item_shoot"),
    ("h07itemscrew", (144,), "item_name_match"),
    ("h07itemscrewfall", (145,), "item_screw_aerial_fall"),
    ("h12itemscopestart", (149, 157), "shared_item_scope"),
    ("h12itemscoperapid", (150, 158), "shared_item_scope"),
    ("h12itemscopefire", (151, 159), "shared_item_scope"),
    ("h12itemscopeend", (152, 160), "shared_item_scope"),
    ("h12itemscopeairstart", (153, 161), "shared_item_scope"),
    ("h12itemscopeairrapid", (154, 162), "shared_item_scope"),
    ("h12itemscopeairfire", (155, 163), "shared_item_scope"),
    ("h12itemscopeairend", (156, 164), "shared_item_scope"),
)

PRESENTATION = (
    ("f07sleepstart", (206,), "ultimate_sleep_start"),
    ("f07sleeploop", (207,), "ultimate_sleep_loop"),
    ("f07sleepend", (208,), "ultimate_sleep_end"),
    ("j00entryr", (238,), "ultimate_entry_right_for_shared_entry"),
    ("j01appealsr", (239, 240), "ultimate_side_taunt_right_for_shared_taunts"),
)


def build(root: Path) -> dict:
    ir_path = root / "experiment/character-ir/instances/kirby.ultimate.ir.json"
    ir = json.loads(ir_path.read_text(encoding="utf-8"))
    by_id = {clip["id"]: clip for clip in ir["assets"]["animations"]["clips"]}
    melee_path = root / "experiment/brawl-kirby/analysis/melee_kirby.json"
    melee_rows = {row["index"]: row for row in json.loads(
        melee_path.read_text(encoding="utf-8"))["motion_table"]}
    motion_path = root / "experiment/tooling/ultimate/workspace/extracted/fighter/kirby/motion/body/c00/motion_list.bin"
    yamlist = root / "experiment/tooling/ultimate/apps/yamlist/yamlist.exe"
    labels = root / "experiment/tooling/ultimate/references/motion-labels.txt"
    with tempfile.TemporaryDirectory(prefix="kirby-motion-") as temporary:
        decoded_path = Path(temporary) / "motion.yml"
        proc = subprocess.run([str(yamlist), "-l", str(labels), "-o", str(decoded_path),
                               "disasm", str(motion_path)], capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"motion_list.bin decode failed: {proc.stderr[-500:]}")
        motion_list = yaml.safe_load(decoded_path.read_text(encoding="utf-8"))["list"]
    motion_by_file = {}
    for status, row in motion_list.items():
        for animation in row.get("animations", []):
            motion_by_file.setdefault(animation["name"], []).append({
                "status": status,
                "game_script": row.get("game_script"),
                "loop": row.get("flags", {}).get("loop"),
                "move": row.get("flags", {}).get("move"),
                "blend_frames": row.get("blend_frames"),
                "cancel_frame": row.get("extra", {}).get("cancel_frame"),
            })
    clips = []
    for stem, rows, confidence in SELECTED + ADDITIONAL + ITEMS + PRESENTATION:
        clip_id = f"clip:motion.body.c00.{stem}"
        record = by_id[clip_id]
        source = root / "experiment/tooling/ultimate/workspace/extracted" / record["file"].removeprefix("file:")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        if record["size"] != source.stat().st_size:
            raise ValueError(f"IR file size differs from source: {source}")
        if not record.get("frames") or "tracks" not in record:
            raise ValueError(f"IR clip lacks decoded metadata: {clip_id}")
        source_statuses = motion_by_file.get(source.name)
        if not source_statuses:
            raise ValueError(f"Ultimate motion_list.bin has no entry for {source.name}")
        symbols = []
        for row in rows:
            if row not in melee_rows:
                raise ValueError(f"Melee motion row missing: {row}")
            symbol = melee_rows[row]["figatree"]
            prefix, suffix = "PlyKirby5K_Share_ACTION_", "_figatree"
            if not symbol or not symbol.startswith(prefix) or not symbol.endswith(suffix):
                raise ValueError(f"Melee motion row {row} has no Kirby animation symbol")
            symbols.append(symbol[len(prefix):-len(suffix)])
        clips.append({
            "ir_clip_id": clip_id,
            "ultimate_file": source.relative_to(root).as_posix(),
            "sha256": digest,
            "bytes": record["size"],
            "final_frame_index": record["frames"],
            "track_nodes_by_group": record["tracks"]["per_channel"],
            "melee_motion_rows": list(rows),
            "melee_motion_names": symbols,
            "mapping": confidence,
            "ultimate_motion_entries": source_statuses,
        })
    return {
        "source": "Ultimate 13.0.2 private extraction, c00 Kirby body motions",
        "ir": ir_path.relative_to(root).as_posix(),
        "ultimate_motion_list": motion_path.relative_to(root).as_posix(),
        "ultimate_motion_list_sha256": hashlib.sha256(motion_path.read_bytes()).hexdigest(),
        "target": "Melee Kirby PlKbAJ.dat motion rows",
        "clips": clips,
        "limits": [
            "This JSON records source clip IDs, hashes, durations, and row mappings; build output HSD animation bytes stay in ignored build directories.",
            "The source-world-scaled converter maps 26 Ultimate bones to Melee Kirby's 46-joint rig. Facial, visibility, and material channels remain separate from the body FigaTrees.",
            "LAB sampled idle, walk, run, five aerial jumps, Inhale, Stone, and Final Cutter on the 272-row predecessor pack; the five added metal-jump rows use the same source clips and require their own status QA.",
            "Ultimate Kirby has no c00 Stone exit animation. Melee rows 334 and 337 retain stock exits; PlyTaro victim animations use a separate 52-joint rig and remain outside this Kirby body mapping.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--out", type=Path, default=Path(__file__).with_name("manifest.json"))
    args = parser.parse_args()
    manifest = build(args.root)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"indexed {len(manifest['clips'])} selected Ultimate Kirby clips -> {args.out}")


if __name__ == "__main__":
    main()
