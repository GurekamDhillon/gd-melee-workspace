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
  AttackModule::clear_all ClearHitboxes.
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


def s16(v):
    return int(round(v * 256)) & 0xFFFF


def hitbox_words(slot, joint, dmg, size, x, y, z, ang, kbg, fkb, bkb, elem, shield, gnd=True, air=True):
    w0 = (11 << 26) | ((slot & 7) << 23) | (joint << 11) | min(int(round(dmg)), 1023)
    w1 = (min(int(round(size * 256)), 0xFFFF) << 16) | s16(z)
    w2 = (s16(y) << 16) | s16(x)
    w3 = ((int(ang) & 0x1FF) << 23) | ((int(kbg) & 0x1FF) << 14) | ((int(fkb) & 0x1FF) << 5)
    w4 = ((int(bkb) & 0x1FF) << 23) | ((elem & 0x1F) << 18) | ((int(shield) & 0xFF) << 10) | \
         (1 << 7) | (SFX_KIND.get(elem, 1) << 2) | (int(gnd) << 1) | int(air)
    return [w0, w1, w2, w3, w4]


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
    for c in row["commands"]:
        if not default_path(c.get("when", [])):
            rep["other_path_commands"] += 1
            continue
        cmd = c["cmd"]
        if cmd in ("frame", "wait") and not c.get("unresolved_frame"):
            events.append((c["frame"], "time", None))
        elif cmd in ("ATTACK",) and c.get("named"):
            n = c["named"]
            if not isinstance(n["id"], int):
                continue
            bone = n["bone"]
            j = joint_of_bone.get(bone)
            if j is None:
                rep["unmapped_bones"].add(str(bone)); j = joint_of_bone.get("top", 0)
            shield = n.get("shield_damage") if isinstance(n.get("shield_damage"), (int, float)) else 0
            elem = ELEM.get(n.get("effect"), 0)
            events.append((c["frame"], "hit", hitbox_words(
                n["id"], j, n["damage"], n["size"] * scale, n["x"] * scale, n["y"] * scale, n["z"] * scale,
                n["angle"], n["kbg"], n["fkb"], n["bkb"], elem, shield)))
            rep["hitboxes"] += 1
            rep["dropped_ultimate_only"] += 1           # hitlag/SDI multipliers etc. on this hitbox
        elif cmd.endswith("clear_all") or cmd == "AttackModule::clear_all":
            events.append((c["frame"], "clear", [16 << 26]))
        elif cmd == "AttackModule::clear" and c["args"] and isinstance(c["args"][0], int):
            events.append((c["frame"], "clear", [(15 << 26) | ((c["args"][0] & 7) << 23)]))   # RemoveHitbox id
        elif cmd == "WorkModule::on_flag" and c["args"] and c["args"][0] == {"const": "0x720"}:
            # const_value_table + 0x720: the first flag a jab sets after its hitboxes (Sora's jab 1
            # frame 20, jab 2 frame 16), i.e. the combo window opening - Melee's JabCombo. Named by
            # its place in the jab scripts, not yet from the executable's constant table. The flag
            # two frames later (0x72c, Ultimate's no-hit combo allowance) has no Melee counterpart.
            events.append((c["frame"], "clear", [29 << 26]))
        elif cmd == "FT_MOTION_RATE" and c["args"]:
            r = c["args"][0]
            if isinstance(r, (int, float)):
                bits = struct.unpack(">I", struct.pack(">f", float(r)))[0]
                events.append((c["frame"], "rate", [(8 << 26), bits]))
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
        "AttackAirLw": "game_attackairlw"}


def main():
    import argparse, json, os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import plan_parts
    from convert_ultimate_anim import INSTANCES
    ap = argparse.ArgumentParser()
    ap.add_argument("fighter"); ap.add_argument("acmd_json"); ap.add_argument("-o", "--out")
    a = ap.parse_args()
    plan = plan_parts.plan(json.load(open(os.path.join(INSTANCES, f"{a.fighter}.ultimate-body.ir.json"), encoding="utf-8")))
    joint_of = {j["name"].lower(): i for i, j in enumerate(plan["joints"])}
    joint_of["top"] = 0
    rows = [r for r in json.load(open(a.acmd_json)) if r["kind"] == "game" and r["owner"] == "fighter"
            and not r["share"] and r["agent"] == a.fighter]
    by_script = {r["script"]: r for r in rows}
    host = json.load(open(os.path.join(INSTANCES, "kirby.melee.ir.json"), encoding="utf-8"))["behavior"]["subactions"]
    out = {"fighter": a.fighter, "rows": {}, "report": {}}
    for s in host:
        script = ROWS.get(s["name"])
        if script and script in by_script:
            words, rep = translate(by_script[script], joint_of)
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
