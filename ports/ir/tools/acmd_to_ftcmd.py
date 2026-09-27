#!/usr/bin/env python3
"""acmd_to_ftcmd.py - an Ultimate fighter's move scripts (acmd_parse.py output) as Melee ftcmd.

    from acmd_to_ftcmd import translate
    words, report = translate(script_row, joint_of_bone, fighter_scale)

A semantic translation (the port feels like the fighter; Melee's mechanics win):
  frame(n) / wait(n)      AsyncWait n / SyncWait n. Both engines count animation frames and a
                          command after the wait runs on frame n+1, so the numbers carry over.
  ATTACK                  Melee hitbox (spawn_hitbox_0..4, melee/src/melee/lb/types.h): id is
                          assigned to one of four live slots. Distinct linking roles take
                          priority; near-duplicate boxes are dropped before unique coverage.
                          bone = the fighter's own joint (joint_of_bone), damage, angle (361 is the
                          Sakurai angle in both), knockback growth / base / fixed copied 1:1 (the
                          knockback formula has the same shape and constants in both games), size
                          and offset in the fighter's own units (its skeleton is Ultimate's).
                          Offsets are written z / y / x as the decomp names the fields - checked in
                          game with gd.hitboxes, not assumed.
  CATCH                   Melee catch-element hitbox. Each capsule endpoint becomes a sphere.
  AttackModule::clear_all ClearHitboxes.
  GrabModule::clear_all   ClearHitboxes.
  FT_MOTION_RATE r        SetTimerAnim (the animation rate command).
  START_SMASH_HOLD        Melee smash charge with the host Marth's vanilla charge settings.
  cancel_frame            IASA at that frame (Melee's interruptible flag).
Repeated low-hitlag, set-weight fixed-knockback carry windows opt into Geno LINK mode 2 after
their hitboxes. Ultimate-only mechanics are dropped and counted (hitlag and SDI multipliers, shieldstun, rehit,
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
# Marth PlMs.dat AttackS4/Hi4/Lw4 each uses opcode 56, 60 charge frames, rate 350,
# colour animation 119 (0xE03C015E 0x77000000); ftAction_80073008 consumes both words.
SMASH_CHARGE_WORDS = (0xE03C015E, 0x77000000)


def default_path(when):
    """True if a command runs on the path a move takes by default (every flag test false)."""
    for c in when:
        if "is_flag" in c["test"] or "uVar" in c["test"]:
            if c["holds"]:
                return False
    return True


def carry_hit_commands(row):
    """Find set-knockback, low-hitlag windows that repeatedly carry a victim.

    A complete window ends at clear_all. Requiring three multi-box windows avoids
    opting an isolated launcher or a finisher into attacker-motion linking.
    """
    windows, current = [], []
    for command in row["commands"]:
        if not default_path(command.get("when", [])):
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
    return {id(c) for window in eligible for c in window} if len(eligible) >= 3 else set()


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
    return sorted(chosen, key=lambda key: logical[key]["order"])


def remap_hitboxes(events, rep):
    """Allocate four ftcmd slots, preserving each live source ID across replacements.

    All emitted boxes use hit group zero. Melee copies that group's victim list to a newly
    enabled slot; replacing the same live slot does not reset it. Dropped Ultimate boxes
    remain logical candidates and can return when a slot opens or priorities change.
    """
    logical = {}   # source key -> latest encoded hitbox and first-spawn order
    resident = {}  # source key -> Melee slot
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
        result.append((frame, "hit", {"words": hw, "carry": True} if logical[key].get("carry") else hw))

    def drop(frame, key, reason):
        box = logical[key]
        rep.setdefault("dropped_hitboxes", []).append({
            "frame": frame, "id": box["id"], "damage": box["damage"],
            "radius": box["radius"], "reason": reason})

    def reconcile(frame, changed_key=None):
        winners = _select_hitboxes(logical)
        selected = set(winners)
        leaving = [key for key in resident if key not in selected]
        entering = [key for key in winners if key not in resident]
        for key in leaving:
            if key in logical:
                drop(frame, key, "lower-priority replacement" if key == changed_key else
                     "replaced by higher-priority hitbox")
        if changed_key is not None and changed_key not in selected and changed_key not in leaving:
            drop(frame, changed_key, "four-slot limit")

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
        if changed_key is not None and changed_key in selected and changed_key not in entering:
            emit_hit(frame, changed_key, resident[changed_key])

    for order, (frame, kind, payload) in enumerate(events):
        if kind == "hit" and isinstance(payload, dict):
            key = payload["key"]
            first_order = logical[key]["order"] if key in logical else order
            logical[key] = {**payload, "order": first_order, "loop": order in loop_orders}
            reconcile(frame, key)
        elif kind == "clear" and isinstance(payload, dict):
            for key in payload["keys"]:
                logical.pop(key, None)
            reconcile(frame)
        else:
            result.append((frame, kind, payload))
            if kind == "clear" and payload == [16 << 26]:
                logical.clear()
                resident.clear()
    return result


def needs_hitbox_remap(events):
    """Leave ordinary four-ID rows on the original byte-for-byte encoding path."""
    active = set()
    for _, kind, payload in events:
        if kind == "hit" and isinstance(payload, dict):
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


def translate(row, joint_of_bone, scale=1.0):
    words, frame = [], 0.0
    rep = {"hitboxes": 0, "dropped_ultimate_only": 0, "other_path_commands": 0, "unmapped_bones": set(),
           "unknown": {}}
    cancel = (row.get("motion") or {}).get("cancel_frame") or 0
    events = []
    carry_hits = carry_hit_commands(row)
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
            events.append((c["frame"], "hit", {"words": hw, "key": ("attack", n["id"]),
                                                 "id": n["id"], "damage": n["damage"],
                                                 "radius": n["size"] * scale,
                                                 "carry": id(c) in carry_hits}))
            rep["hitboxes"] += 1
            rep["dropped_ultimate_only"] += 1           # hitlag/SDI multipliers etc. on this hitbox
        elif cmd == "CATCH" and c.get("named"):
            n = c["named"]
            if not isinstance(n["id"], int) or n["id"] < 0:
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
            # sphere of the same size sits at the far endpoint (logical id + 2).
            ends = [(n["id"], 0, n["x"], n["y"], n["z"])]
            if n.get("x2") is not None and (n["x2"], n["y2"], n["z2"]) != (n["x"], n["y"], n["z"]):
                ends.append((n["id"] + 2, 1, n["x2"], n["y2"], n["z2"]))
            for slot, end, x, y, z in ends:
                hw = hitbox_words(slot, j, 0, n["size"] * scale, x * scale, y * scale, z * scale,
                                  361, 100, 0, 0, 8, 0, *flags)
                hw[3] |= 0x12
                hw[4] = (hw[4] & ~(0x1F << 2)) | (2 << 2)
                events.append((c["frame"], "hit", {"words": hw, "key": ("catch", n["id"], end),
                                                     "id": slot, "damage": 0,
                                                     "radius": n["size"] * scale}))
                rep["hitboxes"] += 1
            rep["grab_boxes"] = rep.get("grab_boxes", 0) + 1
        elif cmd.endswith("clear_all") or cmd == "AttackModule::clear_all":
            events.append((c["frame"], "clear", [16 << 26]))
        elif cmd == "AttackModule::clear" and c["args"] and isinstance(c["args"][0], int):
            # RemoveHitbox: the engine reads the id from the low 26 bits (alpha, 2026-09-26: the id at
            # <<23 wrote fp->x914[huge] in AttackLw4)
            events.append((c["frame"], "clear", {"keys": [("attack", c["args"][0])],
                                                   "words": [(15 << 26) | (c["args"][0] & 0x3FFFFFF)]}))
        elif cmd == "GrabModule::clear" and c.get("args") and isinstance(c["args"][0], int):
            grab_id = c["args"][0]
            events.append((c["frame"], "clear", {"keys": [("catch", grab_id, 0), ("catch", grab_id, 1)],
                                                   "words": []}))
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
        elif cmd == "START_SMASH_HOLD":
            events.append((c["frame"], "charge", SMASH_CHARGE_WORDS))
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
    events.sort(key=lambda e: (e[0], {"time": 0, "rate": 1, "charge": 1, "clear": 2, "hit": 3, "iasa": 4}[e[1]]))
    if needs_hitbox_remap(events):
        events = remap_hitboxes(events, rep)
    else:
        legacy_grab_clears = sum(kind == "clear" and isinstance(payload, dict) and not payload["words"]
                                 for _, kind, payload in events)
        if legacy_grab_clears:
            rep["unknown"]["GrabModule::clear"] = legacy_grab_clears
    events = apply_autolink(events)
    for f, kind, w in events:
        if kind == "time":
            continue
        if isinstance(w, dict) and not w["words"]:
            continue  # legacy rows never emitted GrabModule::clear
        if f > frame:
            words.append((2 << 26) | int(round(f)))        # AsyncWait f
            frame = f
        words += w["words"] if isinstance(w, dict) else w
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
