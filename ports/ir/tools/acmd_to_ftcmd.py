#!/usr/bin/env python3
"""acmd_to_ftcmd.py - an Ultimate fighter's move scripts (acmd_parse.py output) as Melee ftcmd.

    from acmd_to_ftcmd import translate
    words, report = translate(script_row, joint_of_bone, fighter_scale)

A semantic translation (the port feels like the fighter; Melee's mechanics win):
  frame(n) / wait(n)      AsyncWait n / SyncWait n. Both engines count animation frames and a
                          command after the wait runs on frame n+1, so the numbers carry over.
  ATTACK                  Melee hitbox (spawn_hitbox_0..4, melee/src/melee/lb/types.h): slot = id,
                          bone = the fighter's own joint (joint_of_bone), damage, angle (361 is the
                          Sakurai angle in both), knockback growth / base / fixed copied 1:1 (the
                          knockback formula has the same shape and constants in both games), size
                          and offset in the fighter's own units (its skeleton is Ultimate's).
                          Offsets are written z / y / x as the decomp names the fields - checked in
                          game with gd.hitboxes, not assumed.
  CATCH                   Melee catch-element hitbox. Ultimate's optional second capsule point is
                          ignored, as it is for ATTACK; the first point supplies the sphere offset.
  AttackModule::clear_all ClearHitboxes.
  GrabModule::clear_all   ClearHitboxes.
  FT_MOTION_RATE r        SetTimerAnim (the animation rate command).
  cancel_frame            IASA at that frame (Melee's interruptible flag).
Ultimate-only mechanics are dropped and counted (hitlag and SDI multipliers, shieldstun, rehit,
flinchless, direct/indirect, reflect/absorb flags): Melee's rules apply. Commands under a branch on
game state keep only the path that plays by default ('holds' False on a flag test = the flag is off
at the start of a move); the others are reported.
"""
import struct

ELEM = {"collision_attr_normal": 0, "collision_attr_fire": 1, "collision_attr_elec": 2,
        "collision_attr_cutup": 3, "collision_attr_coin": 4, "collision_attr_ice": 5,
        "collision_attr_sleep": 6, "collision_attr_bury": 8, "collision_attr_purple": 13,
        "collision_attr_flower": 15, "collision_attr_magic": 0, "collision_attr_stab": 3}
# Melee hit sound kind by element (Slash for cutting attacks, else Punch-like)
SFX_KIND = {3: 3}
# Ultimate const_value_table offsets in the decompiled ACMD calls: GA also appears on ATTACK.
CATCH_SITUATIONS = {"0x4b54": (True, True), "0xe7cc": (True, False), "0xe7d0": (False, True),
                    "COLLISION_SITUATION_MASK_GA": (True, True),
                    "COLLISION_SITUATION_MASK_G": (True, False),
                    "COLLISION_SITUATION_MASK_A": (False, True)}


def s16(v):
    return int(round(v * 256)) & 0xFFFF


def hitbox_words(slot, joint, dmg, size, x, y, z, ang, kbg, fkb, bkb, elem, shield, gnd=True, air=True):
    w0 = (11 << 26) | ((slot & 7) << 23) | (joint << 11) | min(int(round(dmg)), 1023)
    # In game (gd.hitboxes ox/oy/oz, alpha 2026-09-26): word 1's low half is read as the bone-local X
    # offset and word 2 as Y (high) / Z (low) - not z / y<<16|x as the decomp names the fields.
    w1 = (min(int(round(size * 256)), 0xFFFF) << 16) | s16(x)
    w2 = (s16(y) << 16) | s16(z)
    w3 = ((int(ang) & 0x1FF) << 23) | ((int(kbg) & 0x1FF) << 14) | ((int(fkb) & 0x1FF) << 5)
    w4 = ((int(bkb) & 0x1FF) << 23) | ((elem & 0x1F) << 18) | ((int(shield) & 0xFF) << 10) | \
         (1 << 7) | (SFX_KIND.get(elem, 1) << 2) | (int(gnd) << 1) | int(air)
    return [w0, w1, w2, w3, w4]


def throw_words(idx, dmg, ang, kbg, fkb, bkb, elem):
    """set_throw_hitbox_0..2 (lb/types.h): idx 0 = the throw, 1 = the grab release."""
    w0 = (34 << 26) | ((idx & 7) << 23) | min(int(round(dmg)), 0x7FFFFF)
    w1 = ((int(ang) & 0x1FF) << 23) | ((int(kbg) & 0x1FF) << 14) | ((int(fkb) & 0x1FF) << 5)
    w2 = ((int(bkb) & 0x1FF) << 23) | ((elem & 0xF) << 19)
    return [w0, w1, w2]


# ATTACK_ABS kinds (const_value_table offsets, named by where they appear: every throw script sets
# one of each at frame 0, the first with the throw's own numbers, the second the grab release)
ABS_THROW, ABS_CATCH = "0x396c", "0xe7a0"
THROW_RELEASE = 20 << 26          # Marth's throws release with op 20 (0x50000000), then ClearHitboxes


def default_path(when):
    """True if a command runs on the path a move takes by default (every flag test false)."""
    for c in when:
        if "is_flag" in c["test"] or "uVar" in c["test"]:
            if c["holds"]:
                return False
    return True


def translate(row, joint_of_bone, scale=1.0):
    words, frame = [], 0.0
    rep = {"hitboxes": 0, "dropped_ultimate_only": 0, "other_path_commands": 0, "unmapped_bones": set(),
           "unknown": {}}
    cancel = (row.get("motion") or {}).get("cancel_frame") or 0
    events = []
    catch_only = False
    for c in row["commands"]:
        if not default_path(c.get("when", [])):
            rep["other_path_commands"] += 1
            continue
        cmd = c["cmd"]
        if cmd in ("frame", "wait") and not c.get("unresolved_frame"):
            events.append((c["frame"], "time", None))
        elif cmd in ("ATTACK", "ATTACK_IGNORE_THROW") and c.get("named"):
            # ATTACK_IGNORE_THROW hits bystanders, not the thrown opponent: in Melee a thrower's
            # ordinary hitbox does not hit its thrown opponent, so it is an ordinary hitbox
            n = c["named"]
            if not isinstance(n["id"], int):
                continue
            bone = n["bone"]
            j = joint_of_bone.get(bone)
            if j is None:
                rep["unmapped_bones"].add(str(bone)); j = joint_of_bone.get("top", 0)
            shield = n.get("shield_damage") if isinstance(n.get("shield_damage"), (int, float)) else 0
            elem = ELEM.get(n.get("effect"), 0)
            hw = hitbox_words(
                n["id"], j, n["damage"], n["size"] * scale, n["x"] * scale, n["y"] * scale, n["z"] * scale,
                n["angle"], n["kbg"], n["fkb"], n["bkb"], elem, shield)
            if catch_only:                               # Melee's only_hit_grabbed (spawn_hitbox_0)
                hw[0] |= 1 << 19
            events.append((c["frame"], "hit", hw))
            rep["hitboxes"] += 1
            rep["dropped_ultimate_only"] += 1           # hitlag/SDI multipliers etc. on this hitbox
        elif cmd == "CATCH" and c.get("named"):
            n = c["named"]
            if not isinstance(n["id"], int) or not 0 <= n["id"] < 4:
                rep["unknown"]["CATCH id " + str(n["id"])] = rep["unknown"].get("CATCH id " + str(n["id"]), 0) + 1
                continue
            situation = n["situation"]
            key = situation.get("const") if isinstance(situation, dict) else str(situation)
            flags = CATCH_SITUATIONS.get(key)
            if flags is None:
                label = "CATCH situation " + str(situation)
                rep["unknown"][label] = rep["unknown"].get(label, 0) + 1
                continue
            bone = n["bone"]
            j = joint_of_bone.get(bone)
            if j is None:
                rep["unmapped_bones"].add(str(bone)); j = joint_of_bone.get("top", 0)
            # Marth's vanilla Catch script (PlMs.dat: 0x6560/0x6574/0x6588) uses damage 0,
            # angle 361, KBG 100, element 8, item interaction and clank, sound kind 2.
            # Melee boxes are spheres. Ultimate's grab box is a capsule reaching x2/y2/z2 (Sora's
            # stand grab: z 4.6 -> 8.6), and most of the reach is in that far end, so a second
            # sphere of the same size sits there in slot id + 2 (grabs use only ids 0-1).
            ends = [(n["id"], n["x"], n["y"], n["z"])]
            if n.get("x2") is not None and n["id"] < 2 and (n["x2"], n["y2"], n["z2"]) != (n["x"], n["y"], n["z"]):
                ends.append((n["id"] + 2, n["x2"], n["y2"], n["z2"]))
            for slot, x, y, z in ends:
                hw = hitbox_words(slot, j, 0, n["size"] * scale, x * scale, y * scale, z * scale,
                                  361, 100, 0, 0, 8, 0, *flags)
                hw[3] |= 0x12
                hw[4] = (hw[4] & ~(0x1F << 2)) | (2 << 2)
                events.append((c["frame"], "hit", hw))
                rep["hitboxes"] += 1
            rep["grab_boxes"] = rep.get("grab_boxes", 0) + 1
        elif cmd.endswith("clear_all") or cmd == "AttackModule::clear_all":
            events.append((c["frame"], "clear", [16 << 26]))
        elif cmd == "AttackModule::clear" and c["args"] and isinstance(c["args"][0], int):
            # RemoveHitbox: the engine reads the id from the low 26 bits (alpha, 2026-09-26: the id at
            # <<23 wrote fp->x914[huge] in AttackLw4)
            events.append((c["frame"], "clear", [(15 << 26) | (c["args"][0] & 0x3FFFFFF)]))
        elif cmd == "ATTACK_ABS" and len(c["args"]) >= 7 and isinstance(c["args"][0], dict):
            kind = c["args"][0].get("const")
            a_ = c["args"]
            idx = 0 if kind == ABS_THROW else 1 if kind == ABS_CATCH else None
            if idx is None:
                rep["unknown"]["ATTACK_ABS " + str(kind)] = rep["unknown"].get("ATTACK_ABS " + str(kind), 0) + 1
            else:
                elem = ELEM.get(next((x for x in a_ if isinstance(x, str) and x.startswith("collision_attr")), ""), 0)
                events.append((c["frame"], "hit", throw_words(idx, a_[2], a_[3], a_[4], a_[5], a_[6], elem)))
                rep["throw_hitboxes"] = rep.get("throw_hitboxes", 0) + 1
        elif cmd == "ATK_HIT_ABS":
            events.append((c["frame"], "clear", [THROW_RELEASE]))
            rep["throw_release_frame"] = c["frame"]
        elif cmd == "AttackModule::set_catch_only_all":
            catch_only = bool(c["args"] and c["args"][0] is True)
        elif cmd == "REVERSE_LR":
            rep["dropped_ultimate_only"] += 1           # Melee's back-throw logic turns the fighter
        elif cmd == "WorkModule::on_flag" and c["args"] and c["args"][0] == {"const": "0x720"}:
            # const_value_table + 0x720: the first flag a jab sets after its hitboxes (Sora's jab 1
            # frame 20, jab 2 frame 16), i.e. the combo window opening - Melee's JabCombo. Named by
            # its place in the jab scripts, not yet from the executable's constant table. The flag
            # two frames later (0x72c, Ultimate's no-hit combo allowance) has no Melee counterpart.
            events.append((c["frame"], "clear", [29 << 26]))
        elif cmd == "FT_MOTION_RATE" and c["args"]:
            # Melee's scripts have no animation-rate command (a state's C code sets
            # fp->frame_speed_mul); flow op 8 is "wait forever" (lbcommand.c Command_08) and stalled
            # every move with a rate before its hitboxes. Geno's PUT on engine value ANIM_RATE
            # (0x1B; geno.md engine values, opcode 59 sub 0x09) sets the rate through
            # ftAnim_8006F0FC, and the script timers already scale by frame_speed_mul, so the
            # animation and the script slow together, as FT_MOTION_RATE does. Needs the Geno exe
            # and ANIM_RATE writable (lane echo, 2026-09-26).
            r = c["args"][0]
            if isinstance(r, (int, float)):
                bits = struct.unpack(">I", struct.pack(">f", float(r)))[0]
                put = (59 << 26) | (0x09 << 20) | (3 << 16)
                events.append((c["frame"], "rate", [put, 0x1B, bits]))
        else:
            rep["unknown"][cmd] = rep["unknown"].get(cmd, 0) + 1
    if cancel:
        events.append((float(cancel), "iasa", [23 << 26]))
    events.sort(key=lambda e: (e[0], {"time": 0, "rate": 1, "clear": 2, "hit": 3, "iasa": 4}[e[1]]))
    for f, kind, w in events:
        if kind == "time":
            continue
        if f > frame:
            words.append((2 << 26) | int(round(f)))        # AsyncWait f
            frame = f
        words += w
    words.append(0)                                      # End
    rep["unmapped_bones"] = sorted(rep["unmapped_bones"])
    rep["cancel_frame"] = cancel
    return words, rep


# Melee motion row (the host's decomp name) -> the fighter's Ultimate game script. Angled tilts and
# smashes share the fighter's single script; Melee's jab rows get the fighter's jab 1-2.
ROWS = {"Attack11": "game_attack11", "Attack12": "game_attack12", "Attack13": "game_attack13", "AttackDash": "game_attackdash",
        "AttackS3Hi": "game_attacks3", "AttackS3HiS": "game_attacks3", "AttackS3": "game_attacks3",
        "AttackS3LwS": "game_attacks3", "AttackS3Lw": "game_attacks3", "AttackHi3": "game_attackhi3",
        "AttackLw3": "game_attacklw3", "AttackS4Hi": "game_attacks4", "AttackS4HiS": "game_attacks4",
        "AttackS4": "game_attacks4", "AttackS4LwS": "game_attacks4", "AttackS4Lw": "game_attacks4",
        "AttackHi4": "game_attackhi4", "AttackLw4": "game_attacklw4", "AttackAirN": "game_attackairn",
        "AttackAirF": "game_attackairf", "AttackAirB": "game_attackairb", "AttackAirHi": "game_attackairhi",
        "AttackAirLw": "game_attackairlw", "Catch": "game_catch", "CatchDash": "game_catchdash",
        "CatchAttack": "game_catchattack", "ThrowF": "game_throwf",
        "ThrowB": "game_throwb", "ThrowHi": "game_throwhi", "ThrowLw": "game_throwlw"}


def main():
    import argparse, json, os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import plan_parts
    from convert_ultimate_anim import INSTANCES
    ap = argparse.ArgumentParser()
    ap.add_argument("fighter"); ap.add_argument("acmd_json"); ap.add_argument("-o", "--out")
    ap.add_argument("--host", default="kirby", help="the Melee host fighter whose rows receive the scripts")
    a = ap.parse_args()
    plan = plan_parts.plan(json.load(open(os.path.join(INSTANCES, f"{a.fighter}.ultimate-body.ir.json"), encoding="utf-8")))
    joint_of = {j["name"].lower(): i for i, j in enumerate(plan["joints"])}
    joint_of["top"] = 0
    rows = [r for r in json.load(open(a.acmd_json)) if r["kind"] == "game" and r["owner"] == "fighter"
            and not r["share"] and r["agent"] == a.fighter]
    by_script = {r["script"]: r for r in rows}
    host = json.load(open(os.path.join(INSTANCES, f"{a.host}.melee.ir.json"), encoding="utf-8"))["behavior"]["subactions"]
    out = {"fighter": a.fighter, "rows": {}, "report": {}}
    for s in host:
        script = ROWS.get(s["name"])
        if script and script in by_script:
            words, rep = translate(by_script[script], joint_of)
            if s["name"] in ("Catch", "CatchDash"):
                # Keep the host's script if any grab box could not be parsed or encoded.
                count = sum(1 for c in by_script[script]["commands"]
                            if c["cmd"] == "CATCH" and default_path(c.get("when", [])))
                if not count or rep.get("grab_boxes", 0) != count:
                    continue
            out["rows"][s["index"]["value"]] = {"name": s["name"], "script": script, "words": words,
                                                "clip": (by_script[script].get("motion") or {}).get("clip")}
            out["report"][s["name"]] = {k: v for k, v in rep.items() if v}
    print(f"{len(out['rows'])} rows translated from {len(set(r['script'] for r in out['rows'].values()))} scripts")
    for n, r in out["report"].items():
        print(f"  {n:12} hitboxes {r.get('hitboxes', 0):3}  cancel {r.get('cancel_frame')}")
    if a.out:
        json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
