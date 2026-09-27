#!/usr/bin/env python3
"""acmd_to_ftcmd.py - an Ultimate fighter's move scripts (acmd_parse.py output) as Melee ftcmd.

    from acmd_to_ftcmd import translate
    words, report = translate(script_row, joint_of_bone, fighter_scale)

A guarded semantic translation (unsupported values fail unless reviewed):
  frame(n) / wait(n)      AsyncWait n / SyncWait n. Both engines count animation frames and a
                          command after the wait runs on frame n+1, so the numbers carry over.
  ATTACK                  Melee hitbox (spawn_hitbox_0..4, melee/src/melee/lb/types.h): id is
                          assigned to one of four live slots. Distinct linking roles take
                          priority; near-duplicate boxes are dropped before unique coverage.
                          bone = the fighter's own joint (joint_of_bone), damage, angle (361 is the
                          Sakurai angle in both), knockback growth / base / fixed normally copied
                          1:1, size
                          and offset in the fighter's own units (its skeleton is Ultimate's).
                          Offsets are written z / y / x as the decomp names the fields - checked in
                          game with gd.hitboxes, not assumed.
  CATCH                   Melee catch-element hitbox. Each capsule endpoint becomes a sphere.
  AttackModule::clear_all ClearHitboxes.
  GrabModule::clear_all   ClearHitboxes.
  FT_MOTION_RATE r        SetTimerAnim (the animation rate command).
  START_SMASH_HOLD        Melee smash charge with the host Marth's vanilla charge settings.
  cancel_frame            IASA at that frame (Melee's interruptible flag).
Repeated low-hitlag, set-weight fixed-knockback carry windows opt into Geno LINK mode 2 until
the last carry wave before a finisher. A supplied rise profile can raise only the FKB needed to
reach the next box under Melee gravity. Losses need exact entries in acmd_allowlist.json and are
recorded per move and frame. Four-slot remap losses are always recorded.
"""
import itertools
import struct
import math
from acmd_loss import LossGuard, verify_acmd_source

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

ATTACK_USED = {"id", "bone", "damage", "angle", "kbg", "fkb", "bkb", "size",
               "x", "y", "z", "x2", "y2", "z2", "shield_damage", "effect",
               "rehit", "ground_air", "disable_hitlag", "flinchless"}
# These values have no additional effect in the emitted Melee command. Every other
# present field is a semantic loss and needs an exact reviewed allowlist case.
ATTACK_NEUTRAL = {"part": (0,), "hitlag": (1, 1.0), "sdi": (1, 1.0),
                  "set_weight": (False,), "trip": (0, 0.0),
                  "reflectable": (False,), "absorbable": (False,),
                  "flinchless": (False,), "disable_hitlag": (False,),
                  "direct": (True,), "friendly_fire": (False,)}


def _number(value, field, low, high, *, integer=False):
    if (not isinstance(value, (int, float)) or isinstance(value, bool) or
            not math.isfinite(value) or value < low or value > high or
            (integer and int(value) != value)):
        raise ValueError(f"{field} {value!r} cannot be encoded in Melee ftcmd")


def validate_attack(n, guard, frame, *, article=False):
    for key in ("id", "bone", "damage", "angle", "kbg", "fkb", "bkb", "size", "x", "y", "z"):
        if key not in n:
            raise ValueError(f"ATTACK arguments missing {key}")
    _number(n["id"], "hitbox id", 0, 65535, integer=True)
    _number(n["damage"], "damage", 0, 1023)
    if article and attack_flags(n) & 3:
        raise ValueError(f"article ATTACK id {n['id']} no-hitlag/flinchless needs a Geno item feature")
    attack_flags(n)
    if not 0 <= n.get("rehit", 0) <= 255 or int(n.get("rehit", 0)) != n.get("rehit", 0):
        raise ValueError(f"ATTACK id {n['id']} rehit {n.get('rehit')!r} cannot be encoded")
    if "ground_air" in n and (n["ground_air"].get("const") if isinstance(n["ground_air"], dict)
                              else str(n["ground_air"])) not in CATCH_SITUATIONS:
        raise ValueError(f"ATTACK id {n['id']} ground_air {n['ground_air']!r} is unsupported")
    for key, high in (("angle", 368), ("kbg", 511),
                      ("fkb", 511), ("bkb", 511)):
        _number(n[key], key, 0, high, integer=True)
    if n["angle"] in (365, 366, 367, 368):
        guard.omit(frame, "case", "ATTACK.angle." + str(n["angle"]),
                   f"ATTACK id {n['id']} Ultimate angle {n['angle']} uses Geno LINK/361 approximation")
    _number(n["size"], "size", 0, 255.996)
    for key in ("x", "y", "z"):
        _number(n[key], key, -128, 127.996)
    ends = [n.get(key) for key in ("x2", "y2", "z2")]
    if any(v is not None for v in ends) and not all(v is not None for v in ends):
        raise ValueError("ATTACK capsule endpoint is incomplete")
    for key, value in zip(("x2", "y2", "z2"), ends):
        if value is not None:
            _number(value, "capsule " + key, -128, 127.996)
    effect = n.get("effect")
    if effect is not None and effect not in ELEM:
        raise ValueError(f"ATTACK effect {effect!r} has no Melee mapping")
    if effect in ("collision_attr_magic", "collision_attr_stab"):
        guard.omit(frame, "case", "ATTACK.effect." + effect,
                   f"ATTACK id {n['id']} effect {effect} is approximated in Melee")
    if "shield_damage" in n and n["shield_damage"] is not None:
        _number(n["shield_damage"], "shield_damage", -128, 127)
        if int(n["shield_damage"]) != n["shield_damage"]:
            guard.omit(frame, "case", "ATTACK.shield_damage.rounding",
                       f"ATTACK id {n['id']} shield damage {n['shield_damage']!r} rounds to integer")
    for key, value in n.items():
        if key in ATTACK_USED or (article and key in ("reflectable", "absorbable")):
            continue
        if key not in ATTACK_NEUTRAL or value not in ATTACK_NEUTRAL[key]:
            guard.omit(frame, "case", "ATTACK." + key,
                       f"ATTACK id {n['id']} argument {key}={value!r}")


def attack_flags(n):
    """Geno fighter contact flags carried by an Ultimate ATTACK spawn."""
    for key in ("disable_hitlag", "flinchless"):
        if type(n.get(key, False)) is not bool:
            raise ValueError(f"ATTACK id {n['id']} {key} {n.get(key)!r} is not Boolean")
    return (int(n.get("disable_hitlag", False)) |
            (int(n.get("flinchless", False)) << 1) |
            (4 if n["damage"] == 0 else 0))


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


def attack_spheres(n, joint, scale=1.0, carry=False, catch_only=False, fkb=None):
    """Encode an ATTACK sphere or capsule as sphere candidates for the four Melee slots.

    Samples are one diameter apart when the eight-candidate cap permits it. Selection
    happens across all live attacks, so overlapping capsules share the four live slots.
    """
    start = tuple(n[axis] * scale for axis in ("x", "y", "z"))
    _number(n["size"] * scale, "scaled hitbox size", 0, 255.996)
    for axis, value in zip("xyz", start):
        _number(value, "scaled " + axis, -128, 127.996)
    end = tuple(n.get(axis + "2") for axis in ("x", "y", "z"))
    if any(v is not None for v in end) and not all(
            isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
            for v in end):
        raise ValueError(f"ATTACK id {n['id']}: unresolved capsule endpoint {end!r}")
    capsule = all(v is not None for v in end) and tuple(v * scale for v in end) != start
    if capsule:
        end = tuple(v * scale for v in end)
        for axis, value in zip("xyz", end):
            _number(value, "scaled capsule " + axis, -128, 127.996)
        length = math.dist(start, end)
        count = min(8, max(2, math.ceil(length / max(2 * n["size"] * scale, 0.001)) + 1))
    else:
        count = 1
    shield = n.get("shield_damage") if isinstance(n.get("shield_damage"), (int, float)) else 0
    situation = n.get("ground_air", {"const": "0x4b54"})
    situation = situation.get("const") if isinstance(situation, dict) else str(situation)
    flags = CATCH_SITUATIONS[situation]
    elem = ELEM.get(n.get("effect"), 0)
    out = []
    for i in range(count):
        t = i / (count - 1) if count > 1 else 0
        x, y, z = (a + t * (b - a) for a, b in zip(start, end if capsule else start))
        hw = hitbox_words(n["id"], joint, n["damage"], n["size"] * scale, x, y, z,
                          n["angle"], n["kbg"], n["fkb"] if fkb is None else fkb,
                          n["bkb"], elem, shield, *flags)
        if catch_only:
            hw[0] |= 1 << 19
        out.append({"words": hw, "key": ("attack", n["id"], i) if capsule else ("attack", n["id"]),
                    "source": ("attack", n["id"]), "id": n["id"], "damage": n["damage"],
                    "radius": n["size"] * scale, "carry": carry, "rehit": n.get("rehit", 0),
                    "flags": attack_flags(n),
                    **({"capsule": (start, end)} if capsule else {})})
    return out


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
# Marth PlMs.dat AttackS4/Hi4/Lw4 each uses opcode 56, 60 charge frames, rate 350,
# colour animation 119 (0xE03C015E 0x77000000); ftAction_80073008 consumes both words.
SMASH_CHARGE_WORDS = (0xE03C015E, 0x77000000)


def combo_branch_tests(row):
    """Find a conditional combo-enable path in a staged attack script.

    Ultimate can use one ACMD script for its weak first combo stage and a stronger
    standalone tilt. Only a path which both opens the combo flag and adds reaction
    frames is eligible. The caller must also have the next stage available.
    """
    paths = {tuple((w["test"], w["holds"]) for w in c.get("when", []))
             for c in row["commands"] if c["cmd"] == "WorkModule::on_flag"
             and c.get("args") == [{"const": "0x720"}] and c.get("when")}
    return {test for path in paths
            if any(c["cmd"].startswith("AttackModule::set_add_reaction_frame")
                   and tuple((w["test"], w["holds"]) for w in c.get("when", [])) == path
                   for c in row["commands"])
            for test, holds in path if holds}


def default_path(when, combo_tests=()):
    """True if a command runs on the selected flag path."""
    for c in when:
        if "is_flag" in c["test"] or "uVar" in c["test"]:
            if c["holds"] != (c["test"] in combo_tests):
                return False
    return True


def carry_windows(row, combo_tests=()):
    """Find set-knockback, low-hitlag windows that repeatedly carry a victim.

    A complete window ends at clear_all. Requiring three multi-box windows avoids
    opting an isolated launcher or a finisher into attacker-motion linking.
    """
    windows, current = [], []
    for command in row["commands"]:
        if not default_path(command.get("when", []), combo_tests):
            continue
        if command["cmd"] in ("ATTACK", "ATTACK_IGNORE_THROW") and command.get("named"):
            current.append(command)
        elif command["cmd"] == "AttackModule::clear_all":
            if current:
                windows.append(current)
                current = []
    if current:
        windows.append(current)

    def carries(window):
        return len({c["named"]["id"] for c in window}) >= 2 and all(
            isinstance((n := c["named"])["id"], int) and
            70 <= n["angle"] <= 150 and n["fkb"] > 0 and n["bkb"] == 0 and
            n.get("set_weight") is True and n.get("hitlag", 1) <= 0.5 and
            n.get("rehit", 0) == 0 for c in window)

    eligible = [window for window in windows if carries(window)]
    return (windows, eligible) if len(eligible) >= 3 else (windows, [])


def carry_hit_commands(row, combo_tests=()):
    """LINK each carry wave leading to another carry wave.

    A following non-carry finisher relies on the final wave's authored angle to
    bring the victim back. LINK would erase that vector.
    """
    windows, eligible = carry_windows(row, combo_tests)
    linked = eligible[:-1] if eligible and eligible[-1] is not windows[-1] else eligible
    return {id(c) for window in linked for c in window}


def carry_fkb_floor(row, game_time, attacker_vy, *, gravity=0.23, weight=100):
    """Compensate a repeated LINK-2 carrier for gravity before its next window.

    The caller supplies the attacker's rise profile; a plain ACMD dump cannot
    reveal status-code velocity. Target the lower half of the next source box so
    the point-victim estimate has room for Melee weight and timing differences.
    This is a minimum FKB, never a reduction, and excludes the final carry wave.
    """
    _, eligible = carry_windows(row)
    if not eligible:
        return {}

    def centre_y(c):
        n = c["named"]
        return n["y"] if n.get("y2") is None else (n["y"] + n["y2"]) / 2

    floor = {}
    for old, new in zip(eligible, eligible[1:]):
        by_id = {c["named"]["id"]: c for c in new}
        for c in old:
            n = c["named"]
            target = by_id.get(n["id"])
            if target is None:
                target = min(new, key=lambda v: abs(centre_y(v) - centre_y(c)))
            hit_frame = int(round(game_time(c["frame"])))
            next_frame = int(round(game_time(target["frame"])))
            count = next_frame - hit_frame
            if count <= 0 or n["kbg"] <= 0:
                continue
            rise = sum(attacker_vy(f) for f in range(hit_frame, next_frame))
            allowed_low = centre_y(target) - target["named"]["size"] / 2
            needed_speed = (rise + allowed_low - centre_y(c) +
                            (gravity + .051) * count * (count + 1) / 2) / count
            needed_kb = max(0, needed_speed) / .03
            w = (100 + weight) / 200
            needed_fkb = math.ceil((w * ((needed_kb - n["bkb"]) / (n["kbg"] / 100) - 18)
                                    - 1.4) / .7)
            if needed_fkb > n["fkb"]:
                floor[id(c)] = min(511, needed_fkb)
    return floor


def carry_adjustments(row, profile):
    """Apply a measured carry profile to repeated set-weight attack windows.

    The profile is move data, while the selection, lane mirroring, and hitstun
    restoration are shared conversion rules.  A profile mismatch fails rather
    than silently changing a different attack after an ACMD update.
    """
    windows, eligible = carry_windows(row)
    strengths = profile["fkb"]
    if (len(eligible) != len(strengths) or not eligible or
            any(a is not b for a, b in zip(eligible, windows))):
        raise ValueError("carry profile does not match the source attack windows")
    if len(windows) != len(eligible) + 1:
        raise ValueError("carry profile needs one following finisher window")
    if "z_signs" in profile:
        signs = tuple(1 if all(c["named"]["z"] > 0 for c in window) else
                      -1 if all(c["named"]["z"] < 0 for c in window) else 0
                      for window in eligible)
        if signs != profile["z_signs"]:
            raise ValueError("carry profile does not match the source horizontal lanes")
    first_z = eligible[0][0]["named"]["z"]
    if first_z == 0:
        raise ValueError("carry profile needs a nonzero first horizontal lane")
    adjusted = {}
    for index, (window, strength) in enumerate(zip(eligible, strengths)):
        middle_y = (min(c["named"]["y"] for c in window) +
                    max(c["named"]["y"] for c in window)) / 2
        for c in window:
            n = c["named"]
            fkb = strength[0 if n["y"] < middle_y else 1] if isinstance(strength, tuple) else strength
            if not isinstance(fkb, int) or not 1 <= fkb <= 511:
                raise ValueError(f"carry FKB {fkb!r} is outside Melee's fixed-KB range")
            change = {"fkb": fkb, "carry": profile["link_last"] or index < len(eligible) - 1}
            if index and profile.get("radius_pad", 0):
                change["size"] = n["size"] + profile["radius_pad"]
            if profile["mirror_z"] and n["z"] * first_z < 0:
                change["z"] = -n["z"]
                if n.get("z2") is not None:
                    change["z2"] = -n["z2"]
            # SetWeight fixes Ultimate's KB calculation at weight 100.  Static
            # Melee FKB cannot reproduce that for every victim, but HBSTUN can
            # retain its reference-weight stun after lowering launch speed.
            def stun_frames(value):
                kb = ((18 + (1.4 + .7 * value)) * n["kbg"] / 100 + n["bkb"])
                return int(.4 * kb)
            change["stun"] = max(0, stun_frames(n["fkb"]) - stun_frames(fkb))
            adjusted[id(c)] = change
    finisher = max(windows[-1], key=lambda c: c["named"]["size"])
    finisher_change = {"y": profile["finisher_y"], "size": profile["finisher_size"]}
    if finisher["named"].get("y2") is not None:
        finisher_change["y2"] = profile["finisher_y"]
    adjusted[id(finisher)] = finisher_change
    return adjusted


def _hitbox_features(box):
    """Decode the geometry and knockback fields used to compare live candidates."""
    w0, w1, w2, w3, w4 = box["words"]
    signed = lambda value: value - 0x10000 if value & 0x8000 else value
    angle = (w3 >> 23) & 0x1FF
    fkb = (w3 >> 5) & 0x1FF
    return {
        "kind": box["key"][0], "joint": (w0 >> 11) & 0xFF,
        "damage": box["damage"], "radius": box["radius"],
        "angle": angle, "kbg": (w3 >> 14) & 0x1FF, "fkb": fkb,
        "bkb": (w4 >> 23) & 0x1FF,
        "pos": (signed(w1 & 0xFFFF) / 256, signed(w2 >> 16) / 256,
                signed(w2 & 0xFFFF) / 256),
        "linking": box["key"][0] == "attack" and
                   (fkb > 0 or 361 <= angle <= 368 or box.get("loop", False)),
    }


def _near_duplicate(a, b):
    """Same hit role and almost the same sphere, with conservative numeric tolerances."""
    if a["kind"] != b["kind"] or a["joint"] != b["joint"]:
        return False
    if abs(a["damage"] - b["damage"]) > 0.25:
        return False
    if 361 <= a["angle"] <= 368 or 361 <= b["angle"] <= 368:
        if a["angle"] != b["angle"]:
            return False
    else:
        angle_gap = abs(a["angle"] - b["angle"])
        if a["angle"] <= 360 and b["angle"] <= 360:
            angle_gap = min(angle_gap, 360 - angle_gap)
        if angle_gap > 20:
            return False
    if abs(a["kbg"] - b["kbg"]) > 10 or abs(a["bkb"] - b["bkb"]) > 10:
        return False
    if abs(a["fkb"] - b["fkb"]) > max(16, 0.2 * max(a["fkb"], b["fkb"])):
        return False
    distance2 = sum((x - y) ** 2 for x, y in zip(a["pos"], b["pos"]))
    return distance2 <= (0.5 * min(a["radius"], b["radius"])) ** 2


def _select_hitboxes(logical):
    """Keep one box per distinct role first; fill spare slots with duplicates."""
    if any("capsule" in box for box in logical.values()):
        return _select_capsule_spheres(logical)
    keys = sorted(logical, key=lambda key: logical[key]["order"])
    features = {key: _hitbox_features(logical[key]) for key in keys}
    groups = []
    for key in keys:
        matches = [group for group in groups if any(_near_duplicate(features[key], features[other])
                                                    for other in group)]
        if matches:
            matches[0].append(key)
            for group in matches[1:]:
                matches[0].extend(group)
                groups.remove(group)
        else:
            groups.append([key])

    def basic_rank(key):
        box, feature = logical[key], features[key]
        return (feature["linking"], box["damage"], box["radius"], -box["order"])

    representatives = [max(group, key=basic_rank) for group in groups]
    group_size = {rep: len(group) for rep, group in zip(representatives, groups)}

    def spatial_novelty(key):
        feature = features[key]
        distances = []
        for other in representatives:
            if other == key or features[other]["joint"] != feature["joint"]:
                continue
            peer = features[other]
            distance2 = sum((x - y) ** 2 for x, y in zip(feature["pos"], peer["pos"]))
            distances.append(distance2 / max((feature["radius"] + peer["radius"]) ** 2, 0.001))
        return min(distances) if distances else 1.0

    def representative_rank(key):
        box, feature = logical[key], features[key]
        return (feature["linking"], group_size[key] == 1,
                spatial_novelty(key) if feature["linking"] else 0,
                box["damage"], box["radius"], -box["order"])

    chosen = sorted(representatives, key=representative_rank, reverse=True)[:4]
    if len(chosen) < 4:
        extras = (key for key in keys if key not in representatives)
        chosen.extend(sorted(extras, key=basic_rank, reverse=True)[:4 - len(chosen)])
    if len(keys) > 4:
        targets = {(features[key]["joint"], tuple(round(v, 3) for v in features[key]["pos"]))
                   for key in keys}
        def coverage(selection):
            return sum(any(features[key]["joint"] == joint and
                           math.dist(features[key]["pos"], point) <= features[key]["radius"] + .51
                           for key in selection) for joint, point in targets)
        current = coverage(chosen)
        if current < len(targets):
            candidates = itertools.combinations(keys, 4)
            best = max(candidates, key=lambda selection: (
                coverage(selection),
                len({(features[key]["angle"], features[key]["joint"]) for key in selection}),
                sum(features[key]["damage"] for key in selection),
                -sum(logical[key]["order"] for key in selection)))
            if coverage(best) > current:
                chosen = list(best)
    return sorted(chosen, key=lambda key: logical[key]["order"])


def _select_capsule_spheres(logical):
    """Cover the live capsule centre lines while retaining distinct attack roles.

    Four slots are small enough to evaluate combinations directly. The coverage score
    uses points on the original segment, not on its candidate spheres, so it rewards
    middle and tip coverage even when several capsules overlap at the hilt.
    """
    keys = sorted(logical, key=lambda key: logical[key]["order"])
    if len(keys) <= 4:
        return keys
    features = {key: _hitbox_features(logical[key]) for key in keys}
    targets = []
    tips = []
    seen = set()
    for key in keys:
        box = logical[key]
        source = box.get("source", key)
        if source in seen:
            continue
        seen.add(source)
        if "capsule" in box:
            start, end = box["capsule"]
            tips.append((features[key]["joint"], end))
            length = math.dist(start, end)
            for i in range(33):
                t = i / 32
                targets.append((features[key]["joint"],
                                tuple(a + t * (b - a) for a, b in zip(start, end)), length / 33))
        else:
            targets.append((features[key]["joint"], features[key]["pos"], 2 * box["radius"]))

    def score(chosen):
        sources = {logical[key].get("source", key) for key in chosen}
        linking = {logical[key].get("source", key) for key in chosen if features[key]["linking"]}
        coverage = sum(weight for joint, point, weight in targets if any(
            features[key]["joint"] == joint and
            math.dist(features[key]["pos"], point) <= logical[key]["radius"] + 0.002
            for key in chosen))
        tip_coverage = sum(any(features[key]["joint"] == joint and
                               math.dist(features[key]["pos"], point) <= logical[key]["radius"] + 0.002
                               for key in chosen) for joint, point in tips)
        return (len(linking), len(sources), tip_coverage, round(coverage, 6),
                sum(logical[key]["damage"] for key in chosen),
                -sum(logical[key]["order"] for key in chosen))

    if len(keys) > 20:
        # Limit combinatorial work for a pathological many-capsule script.
        chosen = []
        for _ in range(4):
            chosen.append(max((key for key in keys if key not in chosen),
                              key=lambda key: score((*chosen, key))))
    else:
        chosen = max(itertools.combinations(keys, 4), key=score)
    return sorted(chosen, key=lambda key: logical[key]["order"])


def remap_hitboxes(events, rep):
    """Allocate four ftcmd slots, preserving each live source ID across replacements.

    All emitted boxes use hit group zero. Melee copies that group's victim list to a newly
    enabled slot; replacing the same live slot does not reset it. Dropped Ultimate boxes
    remain logical candidates and can return when a slot opens or priorities change.
    """
    logical = {}   # source key -> latest encoded hitbox and first-spawn order
    resident = {}  # source key -> Melee slot
    source_stun = {}  # Ultimate attack id -> current extra hitstun
    source_force = {}  # Ultimate attack id -> persistent force-reaction bit
    with_stun = any(kind == "stun" for _, kind, _ in events)
    with_flags = any(kind == "force" or (kind == "hit" and isinstance(payload, dict) and
                                        payload.get("flags", 0)) for _, kind, payload in events)
    result = []
    wave = 0
    hit_waves = {}
    for order, (_, kind, payload) in enumerate(events):
        if kind == "clear" and payload == [16 << 26]:
            wave += 1
        elif kind == "hit" and isinstance(payload, dict) and payload["key"][0] == "attack":
            hit_waves.setdefault(payload["key"], []).append((order, wave, payload["damage"]))
    loop_orders = set()
    for occurrences in hit_waves.values():
        for i, (order, phase, damage) in enumerate(occurrences):
            for other_order, other_phase, other_damage in occurrences[i + 1:]:
                if phase != other_phase and abs(damage - other_damage) <= 0.25:
                    loop_orders.update((order, other_order))

    def emit_hit(frame, key, slot):
        hw = logical[key]["words"].copy()
        hw[0] = (hw[0] & ~(7 << 23)) | (slot << 23)
        result.append((frame, "hit", {"words": hw, "carry": logical[key].get("carry", False),
                                      "damage": logical[key]["damage"],
                                      "rehit": logical[key].get("rehit", 0),
                                      "source": logical[key].get("source", key),
                                      "flags": logical[key].get("flags", 0) |
                                               source_force.get(logical[key]["id"], 0),
                                      "emit_flags": with_flags,
                                      **({"stun": source_stun.get(logical[key]["id"], 0)}
                                         if with_stun else {})}))

    def drop(frame, key, reason, selected):
        box = logical[key]
        feature = _hitbox_features(box)
        rep.setdefault("dropped_hitboxes", []).append({
            "frame": frame, "id": box["id"], "damage": box["damage"],
            "radius": box["radius"], "reason": reason,
            "sample": key, "joint": feature["joint"], "position": feature["pos"]})

    def reconcile(frame, changed_keys=()):
        winners = _select_hitboxes(logical)
        selected = set(winners)
        leaving = [key for key in resident if key not in selected]
        entering = [key for key in winners if key not in resident]
        for key in leaving:
            if key in logical:
                drop(frame, key, "lower-priority replacement" if key in changed_keys else
                     "replaced by higher-priority hitbox", selected)
        for key in changed_keys:
            if key not in selected and key not in leaving:
                drop(frame, key, "four-slot limit", selected)

        # If a clear removes the last resident while a dropped box is waiting, a same-group
        # replacement retains its victim list. Otherwise the new box inherits that list from
        # another enabled member of the group after the old slot is cleared.
        handoff = leaving and entering and len(resident) == len(leaving) == 1
        handoff_slot = resident[leaving[0]] if handoff else None
        for key in leaving:
            slot = resident.pop(key)
            if not handoff:
                result.append((frame, "clear", [(15 << 26) | slot]))
        for key in entering:
            free = [slot for slot in range(4) if slot not in resident.values()]
            preferred = logical[key]["id"]
            slot = handoff_slot if handoff else preferred if preferred in free else free[0]
            resident[key] = slot
            emit_hit(frame, key, slot)
            handoff = False
        for key in changed_keys:
            if key in selected and key not in entering:
                emit_hit(frame, key, resident[key])

    for order, (frame, kind, payload) in enumerate(events):
        if kind == "hit" and isinstance(payload, dict):
            key = payload["key"]
            source = payload.get("source", key)
            samples = payload.get("samples", [payload])
            old = {k: box for k, box in logical.items() if box.get("source", k) == source}
            if old:
                source_stun[payload["id"]] = 0  # replacement ATTACK resets its prior bonus
            for old_key in old:
                logical.pop(old_key)
            for i, sample in enumerate(samples):
                sample_key = sample["key"]
                first_order = old[sample_key]["order"] if sample_key in old else order + i / 100
                logical[sample_key] = {**sample, "order": first_order, "loop": order in loop_orders}
            reconcile(frame, tuple(sample["key"] for sample in samples))
        elif kind == "clear" and isinstance(payload, dict):
            for source in payload["keys"]:
                if source[0] == "attack":
                    source_stun.pop(source[1], None)
                    source_force.pop(source[1], None)
                for old_key in list(logical):
                    if logical[old_key].get("source", old_key) == source:
                        logical.pop(old_key)
            reconcile(frame)
        elif kind == "stun":
            source_id, frames = payload["id"], payload["frames"]
            active = [key for key, box in logical.items() if box["id"] == source_id]
            if not active:
                rep.setdefault("pending_reaction_stun", []).append(
                    {"frame": frame, "id": source_id, "frames": frames})
            source_stun[source_id] = frames
            mask = sum(1 << resident[key] for key in active if key in resident)
            if mask:
                result.append((frame, "stun", hbstun(mask, frames)))
        elif kind == "force":
            source_id, enabled = payload["id"], payload["enabled"]
            source_force[source_id] = 8 if enabled else 0
            active = [key for key, box in logical.items() if box["id"] == source_id]
            by_flags = {}
            for key in active:
                if key in resident:
                    flags = logical[key].get("flags", 0) | source_force[source_id]
                    by_flags[flags] = by_flags.get(flags, 0) | (1 << resident[key])
            for flags, mask in by_flags.items():
                result.append((frame, "force", hbflags(mask, flags)))
        else:
            result.append((frame, kind, payload))
            if kind == "clear" and payload == [16 << 26]:
                logical.clear()
                resident.clear()
                source_stun.clear()
                source_force.clear()
    return result


def needs_hitbox_remap(events):
    """Leave ordinary four-ID rows on the original byte-for-byte encoding path."""
    active = set()
    for _, kind, payload in events:
        if kind in ("stun", "force"):
            return True
        if kind == "hit" and isinstance(payload, dict):
            if len(payload.get("samples", ())) > 1:
                return True
            if payload["id"] >= 4:
                return True
            active.add(payload["key"])
            if len(active) > 4:
                return True
        elif kind == "clear" and isinstance(payload, dict):
            active.difference_update(payload["keys"])
        elif kind == "clear" and payload == [16 << 26]:
            active.clear()
    return False


def apply_autolink(events):
    """Translate special angles and carry windows after Melee slot allocation.

    Geno LINK 1 follows attacker momentum while keeping Melee knockback. LINK 2 also
    floors launch speed at attacker speed. Neither can pull toward a hitbox centre or
    a target vector; 368 uses a low-FKB 361 fallback instead. Link state belongs to
    the slot, so clear it when that slot is reused or removed.
    """
    modes = [0] * 4
    result = []

    def link(mask, mode):
        return [(59 << 26) | (0x39 << 20) | (2 << 16) | (mask << 8), mode]

    for frame, kind, payload in events:
        words = payload.get("words", []) if isinstance(payload, dict) else payload
        if not isinstance(words, list) or not words:
            result.append((frame, kind, payload))
            continue
        original_words = words
        extra = []
        if kind == "hit" and words[0] >> 26 == 11:
            slot = (words[0] >> 23) & 7
            angle = (words[3] >> 23) & 0x1FF
            if angle in (365, 366, 367, 368):
                words = words.copy()
                words[3] = (words[3] & ~(0x1FF << 23)) | (361 << 23)
                if angle == 368:
                    words[3] = (words[3] & ~(0x1FF << 5)) | (20 << 5)
                mode = 1 if angle == 365 else 2 if angle in (366, 367) else 0
                if mode or modes[slot]:
                    extra = link(1 << slot, mode)
                modes[slot] = mode
            elif isinstance(payload, dict) and payload.get("carry"):
                extra = link(1 << slot, 2)
                modes[slot] = 2
            elif modes[slot]:
                extra = link(1 << slot, 0)
                modes[slot] = 0
        elif kind == "clear" and words[0] >> 26 == 16:
            mask = sum((1 << slot) for slot, mode in enumerate(modes) if mode)
            if mask:
                extra = link(mask, 0)
                modes = [0] * 4
        elif kind == "clear" and words[0] >> 26 == 15:
            slot = words[0] & 0x3FFFFFF
            if slot < 4 and modes[slot]:
                extra = link(1 << slot, 0)
                modes[slot] = 0
        if extra or words is not original_words:
            words = words + extra
            payload = dict(payload, words=words) if isinstance(payload, dict) else words
        result.append((frame, kind, payload))
    return result


def hit_extras(payload):
    """Geno float damage and per-slot rehit follow the native hitbox spawn."""
    encoded = payload["words"]
    slot = (encoded[0] >> 23) & 7
    if slot >= 4:
        raise ValueError(f"fighter hitbox slot {slot} exceeds Geno limit")
    out = []
    if int(payload["damage"]) != payload["damage"]:
        out += [(59 << 26) | (0x3A << 20) | (2 << 16) | (1 << (slot + 8)),
                struct.unpack(">I", struct.pack(">f", payload["damage"]))[0]]
    out += [(59 << 26) | (0x38 << 20) | (2 << 16) | (1 << (slot + 8)), payload.get("rehit", 0)]
    if "stun" in payload:
        out += hbstun(1 << slot, payload["stun"])
    if (payload.get("source", (None,))[0] == "attack" and
            (payload.get("flags", 0) or payload.get("emit_flags"))):
        out += hbflags(1 << slot, payload.get("flags", 0))
    return out


def hbstun(mask, frames):
    """Geno HBSTUN immediate: mask of Melee hitbox slots, then extra frames."""
    if not 0 <= mask <= 15 or not 0 <= frames <= 255 or int(frames) != frames:
        raise ValueError(f"HBSTUN mask {mask!r} or frames {frames!r} cannot be encoded")
    return [0xEFB20000 | (mask << 8), int(frames)]


def hbflags(mask, flags):
    """Geno HBFLAGS immediate: mask of Melee hitbox slots, then contact flags."""
    if not 0 <= mask <= 15 or not 0 <= flags <= 15 or int(flags) != flags:
        raise ValueError(f"HBFLAGS mask {mask!r} or flags {flags!r} cannot be encoded")
    return [0xEFC20000 | (mask << 8), int(flags)]


def reaction_stun_args(command, move):
    """Validate the observed Ultimate (source id, extra frames, revised flag) form."""
    args = command.get("args", [])
    if (len(args) != 3 or type(args[0]) is not int or not 0 <= args[0] <= 65535 or
            type(args[1]) is not int or not 0 <= args[1] <= 255 or args[2] is not False):
        raise ValueError(f"{move} frame {command['frame']:g}: "
                         f"AttackModule::set_add_reaction_frame_revised {args!r} cannot be encoded")
    return args[0], args[1]


def force_reaction_args(command, move):
    args = command.get("args", [])
    if (len(args) != 3 or type(args[0]) is not int or not 0 <= args[0] <= 65535 or
            type(args[1]) is not bool or args[2] is not False):
        raise ValueError(f"{move} frame {command['frame']:g}: "
                         f"AttackModule::set_force_reaction {args!r} cannot be encoded")
    return args[0], args[1]


def clear_rehit(words):
    mask = 0
    for word in words:
        if word >> 26 == 16:
            mask = 15
        elif word >> 26 == 15 and (word & 0x3FFFFFF) < 4:
            mask |= 1 << (word & 0x3FFFFFF)
    return ([(59 << 26) | (0x38 << 20) | (2 << 16) | (mask << 8), 0]
            if mask else [])


def translate(row, joint_of_bone, scale=1.0, *, combo=False, carry_motion=None,
              allowlist=None, hurt_joint_of_bone=None):
    words, frame = [], 0.0
    rep = {"hitboxes": 0, "other_path_commands": 0}
    script = row.get("script", "<unnamed move>")
    guard = LossGuard(f"{row['agent']}/{script}" if row.get("agent") else script, allowlist)
    cancel = (row.get("motion") or {}).get("cancel_frame") or 0
    events = []
    combo_tests = combo_branch_tests(row) if combo else set()
    carry_hits = carry_hit_commands(row, combo_tests)
    carry_floors = carry_fkb_floor(row, *carry_motion) if carry_motion else {}
    catch_only = False
    live_attacks = {}
    for c in row["commands"]:
        if not default_path(c.get("when", []), combo_tests):
            rep["other_path_commands"] += 1
            guard.omit(c["frame"], "case", "branch:" + c["cmd"],
                       f"{c['cmd']} on unselected condition {c.get('when')!r}")
            continue
        cmd = c["cmd"]
        if cmd in ("frame", "wait") and not c.get("unresolved_frame"):
            if len(c.get("args", [])) != 1 or not isinstance(c["args"][0], (int, float)):
                raise ValueError(f"{guard.move} frame {c['frame']:g}: {cmd} arguments unresolved")
            events.append((c["frame"], "time", None))
        elif cmd in ("ATTACK", "ATTACK_IGNORE_THROW") and c.get("named"):
            # ATTACK_IGNORE_THROW hits bystanders, not the thrown opponent: in Melee a thrower's
            # ordinary hitbox does not hit its thrown opponent, so it is an ordinary hitbox
            n = c["named"]
            validate_attack(n, guard, c["frame"])
            live_attacks[n["id"]] = dict(n)
            bone = n["bone"]
            j = joint_of_bone.get(bone)
            if j is None:
                raise ValueError(f"{guard.move} frame {c['frame']:g}: ATTACK bone {bone!r} is unmapped")
            samples = attack_spheres(n, j, scale, id(c) in carry_hits, catch_only,
                                     carry_floors.get(id(c), n["fkb"]))
            payload = dict(samples[0])
            if len(samples) > 1:
                payload["samples"] = samples
            events.append((c["frame"], "hit", payload))
            rep["hitboxes"] += 1
        elif cmd == "sv_module_access::attack":
            args = c.get("args", [])
            if (len(args) != 6 or args[0] != {"const": "0xe7f8"} or
                    not isinstance(args[1], int) or args[1] not in live_attacks or
                    not isinstance(args[2], str) or
                    any(not isinstance(v, (int, float)) for v in args[3:])):
                raise ValueError(f"{guard.move} frame {c['frame']:g}: sv_module_access::attack {args!r} unsupported")
            n = dict(live_attacks[args[1]], bone=args[2], x=args[3], y=args[4], z=args[5])
            n.pop("x2", None); n.pop("y2", None); n.pop("z2", None)
            live_attacks[args[1]] = n
            j = joint_of_bone.get(n["bone"])
            if j is None:
                raise ValueError(f"{guard.move} frame {c['frame']:g}: moved hitbox bone {n['bone']!r} unmapped")
            events.append((c["frame"], "hit", attack_spheres(n, j, scale)[0]))
        elif cmd == "AttackModule::set_add_reaction_frame_revised":
            source_id, frames = reaction_stun_args(c, guard.move)
            events.append((c["frame"], "stun", {"id": source_id, "frames": frames}))
        elif cmd == "AttackModule::set_force_reaction":
            source_id, enabled = force_reaction_args(c, guard.move)
            events.append((c["frame"], "force", {"id": source_id, "enabled": enabled}))
        elif cmd == "CATCH" and c.get("named"):
            n = c["named"]
            for key in ("id", "bone", "size", "x", "y", "z", "status", "situation"):
                if key not in n:
                    raise ValueError(f"{guard.move} frame {c['frame']:g}: CATCH arguments missing {key}")
            for key, value in n.items():
                if key not in {"id", "bone", "size", "x", "y", "z", "x2", "y2", "z2", "status", "situation"}:
                    guard.omit(c["frame"], "case", "CATCH." + key,
                               f"CATCH id {n['id']} argument {key}={value!r}")
            if not isinstance(n["id"], int) or n["id"] < 0:
                raise ValueError(f"{guard.move} frame {c['frame']:g}: CATCH id {n['id']!r} is invalid")
            for key in ("size", "x", "y", "z"):
                _number(n[key], "CATCH " + key, 0 if key == "size" else -128,
                        255.996 if key == "size" else 127.996)
            end_values = [n.get(key) for key in ("x2", "y2", "z2")]
            if any(v is not None for v in end_values) and not all(v is not None for v in end_values):
                raise ValueError(f"{guard.move} frame {c['frame']:g}: CATCH capsule endpoint is incomplete")
            for key, value in zip(("x2", "y2", "z2"), end_values):
                if value is not None:
                    _number(value, "CATCH capsule " + key, -128, 127.996)
            if n.get("status") not in (None, {"const": "0x80c"}):
                guard.omit(c["frame"], "case", "CATCH.status", f"CATCH status {n['status']!r}")
            situation = n["situation"]
            key = situation.get("const") if isinstance(situation, dict) else str(situation)
            flags = CATCH_SITUATIONS.get(key)
            if flags is None:
                raise ValueError(f"{guard.move} frame {c['frame']:g}: CATCH situation {situation!r} is unsupported")
            bone = n["bone"]
            j = joint_of_bone.get(bone)
            if j is None:
                raise ValueError(f"{guard.move} frame {c['frame']:g}: CATCH bone {bone!r} is unmapped")
            # Marth's vanilla Catch script (PlMs.dat: 0x6560/0x6574/0x6588) uses damage 0,
            # angle 361, KBG 100, element 8, item interaction and clank, sound kind 2.
            # Melee boxes are spheres. Ultimate's grab box is a capsule reaching x2/y2/z2 (Sora's
            # stand grab: z 4.6 -> 8.6), and most of the reach is in that far end, so a second
            # sphere of the same size sits at the far endpoint (logical id + 2).
            ends = [(n["id"], 0, n["x"], n["y"], n["z"])]
            if n.get("x2") is not None and (n["x2"], n["y2"], n["z2"]) != (n["x"], n["y"], n["z"]):
                ends.append((n["id"] + 2, 1, n["x2"], n["y2"], n["z2"]))
            for slot, end, x, y, z in ends:
                _number(n["size"] * scale, "scaled CATCH size", 0, 255.996)
                for axis, value in zip("xyz", (x * scale, y * scale, z * scale)):
                    _number(value, "scaled CATCH " + axis, -128, 127.996)
                hw = hitbox_words(slot, j, 0, n["size"] * scale, x * scale, y * scale, z * scale,
                                  361, 100, 0, 0, 8, 0, *flags)
                hw[3] |= 0x12
                hw[4] = (hw[4] & ~(0x1F << 2)) | (2 << 2)
                events.append((c["frame"], "hit", {"words": hw, "key": ("catch", n["id"], end),
                                                     "id": slot, "damage": 0,
                                                     "radius": n["size"] * scale}))
                rep["hitboxes"] += 1
            rep["grab_boxes"] = rep.get("grab_boxes", 0) + 1
        elif cmd in ("AttackModule::clear_all", "GrabModule::clear_all"):
            expected = [] if cmd.startswith("Attack") else [{"const": "0xe7d4"}]
            if c.get("args", []) not in ([], expected):
                guard.omit(c["frame"], "case", cmd + ".args", f"{cmd} arguments {c['args']!r}")
            events.append((c["frame"], "clear", [16 << 26]))
            if cmd.startswith("Attack"):
                live_attacks.clear()
        elif cmd == "AttackModule::clear" and c["args"] and isinstance(c["args"][0], int):
            if len(c["args"]) != 1 or c["args"][0] < 0:
                raise ValueError(f"{guard.move} frame {c['frame']:g}: AttackModule::clear id/arguments invalid")
            # RemoveHitbox: the engine reads the id from the low 26 bits (alpha, 2026-09-26: the id at
            # <<23 wrote fp->x914[huge] in AttackLw4)
            events.append((c["frame"], "clear", {"keys": [("attack", c["args"][0])],
                                                   "words": [(15 << 26) | (c["args"][0] & 0x3FFFFFF)]}))
            live_attacks.pop(c["args"][0], None)
        elif cmd == "GrabModule::clear" and c.get("args") and isinstance(c["args"][0], int):
            if len(c["args"]) != 1 or c["args"][0] < 0:
                raise ValueError(f"{guard.move} frame {c['frame']:g}: GrabModule::clear id/arguments invalid")
            grab_id = c["args"][0]
            events.append((c["frame"], "clear", {"keys": [("catch", grab_id, 0), ("catch", grab_id, 1)],
                                                   "words": [(15 << 26) | grab_id,
                                                             (15 << 26) | (grab_id + 2)]}))
        elif cmd == "ATTACK_ABS" and len(c["args"]) >= 7 and isinstance(c["args"][0], dict):
            kind = c["args"][0].get("const")
            a_ = c["args"]
            idx = 0 if kind == ABS_THROW else 1 if kind == ABS_CATCH else None
            if idx is None:
                raise ValueError(f"{guard.move} frame {c['frame']:g}: unsupported ATTACK_ABS kind {kind!r}")
            else:
                if not isinstance(a_[1], int) or a_[1] < 0:
                    raise ValueError(f"{guard.move} frame {c['frame']:g}: ATTACK_ABS id {a_[1]!r} is invalid")
                if a_[1] != 0:
                    guard.omit(c["frame"], "case", "ATTACK_ABS.id",
                               f"ATTACK_ABS id {a_[1]} aliases Melee's single {kind} throw slot")
                if len(a_) > 7:
                    guard.omit(c["frame"], "case", "ATTACK_ABS.extra_args",
                               f"ATTACK_ABS arguments after base knockback: {a_[7:]!r}")
                for key, value in zip(("damage", "angle", "kbg", "fkb", "bkb"), a_[2:7]):
                    _number(value, "ATTACK_ABS " + key, 0, 0x7FFFFF if key == "damage" else
                            368 if key == "angle" else 511, integer=key != "damage")
                if int(a_[2]) != a_[2]:
                    guard.omit(c["frame"], "case", "ATTACK_ABS.damage.rounding",
                               f"throw damage {a_[2]!r} rounds to Melee integer damage")
                effect = next((x for x in a_ if isinstance(x, str) and x.startswith("collision_attr")), None)
                if effect is not None and effect not in ELEM:
                    raise ValueError(f"{guard.move} frame {c['frame']:g}: ATTACK_ABS effect {effect!r} unsupported")
                if effect in ("collision_attr_magic", "collision_attr_stab"):
                    guard.omit(c["frame"], "case", "ATTACK_ABS.effect." + effect,
                               f"throw effect {effect} approximated in Melee")
                elem = ELEM.get(effect, 0)
                events.append((c["frame"], "hit", throw_words(idx, a_[2], a_[3], a_[4], a_[5], a_[6], elem)))
                rep["throw_hitboxes"] = rep.get("throw_hitboxes", 0) + 1
        elif cmd == "ATK_HIT_ABS":
            if c.get("args"):
                guard.omit(c["frame"], "case", "ATK_HIT_ABS.args",
                           f"ATK_HIT_ABS target/arguments {c['args']!r}")
            events.append((c["frame"], "clear", [THROW_RELEASE]))
            rep["throw_release_frame"] = c["frame"]
        elif cmd == "AttackModule::set_catch_only_all":
            args = c.get("args", [])
            if (len(args) not in (1, 2) or not isinstance(args[0], bool) or
                    (len(args) == 2 and args[1] is not False)):
                raise ValueError(f"{guard.move} frame {c['frame']:g}: set_catch_only_all arguments unresolved")
            catch_only = args[0]
        elif cmd == "HIT_NODE":
            args = c.get("args", [])
            states = {"0xc50": 2, "0xc90": 0, "0xcdc": 1}  # XLU, NORMAL, OFF
            if (len(args) != 2 or not isinstance(args[0], str) or
                    not isinstance(args[1], dict) or args[1].get("const") not in states):
                raise ValueError(f"{guard.move} frame {c['frame']:g}: HIT_NODE arguments {args!r} unsupported")
            bone = args[0].lower()
            joint = (hurt_joint_of_bone or joint_of_bone).get(bone)
            if joint is None:
                raise ValueError(f"{guard.move} frame {c['frame']:g}: HIT_NODE bone {bone!r} is unmapped")
            events.append((c["frame"], "hurt", [(28 << 26) | (joint << 18) |
                                                  states[args[1]["const"]]]))
        elif cmd == "REVERSE_LR":
            guard.omit(c["frame"], "command", cmd, "reverse facing")
        elif cmd == "WorkModule::on_flag" and c["args"] and c["args"][0] == {"const": "0x720"}:
            if len(c["args"]) != 1:
                guard.omit(c["frame"], "case", "WorkModule::on_flag.extra_args",
                           f"combo flag arguments {c['args']!r}")
            # const_value_table + 0x720: the first flag a jab sets after its hitboxes (Sora's jab 1
            # frame 20, jab 2 frame 16), i.e. the combo window opening - Melee's JabCombo. Named by
            # its place in the jab scripts, not yet from the executable's constant table. The flag
            # two frames later (0x72c, Ultimate's no-hit combo allowance) has no Melee counterpart.
            events.append((c["frame"], "clear", [29 << 26]))
        elif cmd == "START_SMASH_HOLD":
            if c.get("args"):
                guard.omit(c["frame"], "case", "START_SMASH_HOLD.args",
                           f"smash hold arguments {c['args']!r}")
            events.append((c["frame"], "charge", SMASH_CHARGE_WORDS))
        elif cmd == "FT_MOTION_RATE" and c["args"]:
            # Melee's scripts have no animation-rate command (a state's C code sets
            # fp->frame_speed_mul); flow op 8 is "wait forever" (lbcommand.c Command_08) and stalled
            # every move with a rate before its hitboxes. Geno's PUT on engine value ANIM_RATE
            # (0x1B; geno.md engine values, opcode 59 sub 0x09) sets the rate through
            # ftAnim_8006F0FC, and the script timers already scale by frame_speed_mul, so the
            # animation and the script slow together, as FT_MOTION_RATE does. Needs the Geno exe
            # and ANIM_RATE writable (lane echo, 2026-09-26).
            r = c["args"][-1]
            if isinstance(r, (int, float)) and not isinstance(r, bool):
                if len(c["args"]) > 1:
                    guard.omit(c["frame"], "case", "FT_MOTION_RATE.extra_args",
                               f"rate arguments before {r!r}: {c['args'][:-1]!r}")
                bits = struct.unpack(">I", struct.pack(">f", float(r)))[0]
                put = (59 << 26) | (0x09 << 20) | (3 << 16)
                events.append((c["frame"], "rate", [put, 0x1B, bits]))
            else:
                raise ValueError(f"{guard.move} frame {c['frame']:g}: FT_MOTION_RATE {r!r} is unresolved")
        else:
            guard.omit(c["frame"], "command", cmd, f"{cmd} arguments {c.get('args')!r}")
    if cancel:
        events.append((float(cancel), "iasa", [23 << 26]))
    events.sort(key=lambda e: (e[0], {"time": 0, "rate": 1, "charge": 1, "clear": 2,
                                       "hit": 3, "hurt": 3, "stun": 4, "force": 4,
                                       "iasa": 5}[e[1]]))
    if needs_hitbox_remap(events):
        events = remap_hitboxes(events, rep)
    for box in rep.get("dropped_hitboxes", []):
        guard.remap(box["frame"], box)
    events = apply_autolink(events)
    for f, kind, w in events:
        if kind == "time":
            continue
        if isinstance(w, dict) and not w["words"]:
            raise ValueError(f"{guard.move} frame {f:g}: empty converted {kind} command")
        if f > frame:
            words.append((2 << 26) | int(round(f)))        # AsyncWait f
            frame = f
        encoded = w["words"] if isinstance(w, dict) else w
        words += encoded
        if kind == "hit" and isinstance(w, dict) and encoded[0] >> 26 == 11:
            words += hit_extras(w)
        elif kind == "clear":
            words += clear_rehit(encoded)
    words.append(0)                                      # End
    rep["cancel_frame"] = cancel
    rep["losses"] = guard.losses
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
    import argparse, hashlib, json, os, sys
    from pathlib import Path
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import plan_parts
    from convert_ultimate_anim import INSTANCES
    ap = argparse.ArgumentParser()
    ap.add_argument("fighter"); ap.add_argument("acmd_json"); ap.add_argument("-o", "--out")
    ap.add_argument("--host", default="kirby", help="the Melee host fighter whose rows receive the scripts")
    a = ap.parse_args()
    source_bytes = verify_acmd_source(a.acmd_json)
    plan = plan_parts.plan(json.load(open(os.path.join(INSTANCES, f"{a.fighter}.ultimate-body.ir.json"), encoding="utf-8")))
    joint_of = {j["name"].lower(): i for i, j in enumerate(plan["joints"])}
    joint_of["top"] = 0
    import plan_hurtboxes
    hurt_bones = {plan["parts"]["part_to_joint"][plan_parts.COMMON.index(name)]
                  for name in plan_hurtboxes.SEGMENTS
                  if plan["parts"]["part_to_joint"][plan_parts.COMMON.index(name)] != 255}
    def hurt_joint(j):
        while j is not None and j not in hurt_bones:
            j = plan["joints"][j]["parent"]
        return j if j is not None else plan["parts"]["part_to_joint"][plan_parts.COMMON.index("HipN")]
    hurt_of = {name: hurt_joint(joint) for name, joint in joint_of.items()}
    rows = [r for r in json.loads(source_bytes) if r["kind"] == "game" and r["owner"] == "fighter"
            and not r["share"] and r["agent"] == a.fighter]
    by_script = {r["script"]: r for r in rows}
    host = json.load(open(os.path.join(INSTANCES, f"{a.host}.melee.ir.json"), encoding="utf-8"))["behavior"]["subactions"]
    here = os.path.dirname(os.path.abspath(__file__))
    audit_files = ("acmd_to_ftcmd.py", "acmd_loss.py", "acmd_allowlist.json")
    audit_hash = hashlib.sha256(b"".join((Path(here) / f).read_bytes()
                                         for f in audit_files)).hexdigest()
    out = {"fighter": a.fighter, "rows": {}, "report": {}, "omissions": [],
           "audit": {"version": 1, "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
                     "converter_sha256": audit_hash}}
    for s in host:
        script = ROWS.get(s["name"])
        if script and script not in by_script:
            guard = LossGuard(s["name"])
            guard.omit(0, "case", "missing_script:" + script,
                       f"host row {s['name']} has no selected Ultimate game script {script}")
            out["omissions"].extend(guard.losses)
            continue
        if script and script in by_script:
            # A staged script supplies its weak combo-enabling branch when its next
            # stage is also present. Keep the stronger branch for standalone tilts.
            words, rep = translate(by_script[script], joint_of,
                                   combo=script + "2" in by_script,
                                   hurt_joint_of_bone=hurt_of)
            if s["name"] in ("Catch", "CatchDash"):
                count = sum(1 for c in by_script[script]["commands"]
                            if c["cmd"] == "CATCH" and default_path(c.get("when", [])))
                if not count or rep.get("grab_boxes", 0) != count:
                    raise ValueError(f"{script}: {count} source grabs but {rep.get('grab_boxes', 0)} converted")
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
