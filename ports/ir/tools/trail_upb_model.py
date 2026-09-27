#!/usr/bin/env python3
"""Offline two-axis, per-moving-frame Aerial Sweep trajectory estimate.

The input is an ACMD row.  No game or disc data is loaded.  Hitlag pauses both
fighters and therefore does not advance this moving-frame timeline.  A victim
starts at the first upper hitbox centre with neutral DI/SDI and Sora has no
horizontal velocity.  Local Z is used for top-bone boxes; hand-bone finisher
centres are approximate.  The contact reach values are conservative circular
estimates of each fighter's hurtbox and are deliberately explicit.
"""
import argparse
import json
import math

from acmd_to_ftcmd import carry_adjustments, carry_fkb_floor, carry_hit_commands
from trail_specials_geno import game_time


DEFENDERS = {
    "Fox": (75, .23, 2.8, 3.5),
    "Marth": (87, .085, 2.2, 4.0),
    "Bowser": (117, .13, 1.9, 6.0),
    "Jigglypuff": (60, .064, 1.3, 4.0),
}
KB_SCALE = .03
KB_DECAY = .051


def knockback(box, fkb, weight):
    """Melee FKB branch at 1x attack/defense/stage and zero stale damage."""
    return (18 + (1.4 + .7 * fkb) / ((100 + weight) / 200)) * box["kbg"] / 100 + box["bkb"]


def simulate(row, distance, fighter, profile=None):
    """Return per-frame victim state and every predicted source window contact."""
    weight, gravity, terminal, reach = DEFENDERS[fighter]
    t = game_time(row)
    first = next(c for c in row["commands"] if c["cmd"] == "ATTACK" and c["named"]["id"] == 1)
    start = round(t(first["frame"]))
    speed0 = math.sqrt(2 * .04 * distance)
    attacker_vy = lambda frame: speed0 - .04 * (frame - start)
    changes = carry_adjustments(row, profile) if profile else {}
    floors = {} if profile else carry_fkb_floor(row, t, attacker_vy)
    linked = carry_hit_commands(row)
    windows = {}
    for c in row["commands"]:
        if c["cmd"] != "ATTACK":
            continue
        n = c["named"]
        change = changes.get(id(c), {})
        converted = {**n, **{k: v for k, v in change.items() if k in n}}
        converted["fkb"] = floors.get(id(c), converted["fkb"])
        converted["linked"] = change.get("carry", id(c) in linked)
        converted["stun_bonus"] = change.get("stun", 0)
        windows.setdefault(round(t(c["frame"])), []).append(converted)
    end = max(windows)
    victim_y = first["named"]["y"]
    victim_z = first["named"]["z"]
    sora_y = normal_vy = kb_y = kb_z = 0.0
    stun = 0
    contacts, frames = [], []
    first_wave_hit = False
    for frame in range(start, end + 1):
        relative_y = victim_y - sora_y
        window = windows.get(frame, [])
        if window and not (frame == start + 1 and first_wave_hit):
            candidates = []
            for box in window:
                d = math.hypot(relative_y - box["y"], victim_z - box["z"])
                if d <= box["size"] + reach:
                    candidates.append((box["id"], d, box))
            if frame == start:
                candidates = [c for c in candidates if c[0] == 1]
            if candidates:
                source_id, distance_to_box, box = min(candidates)
                incoming_stun = stun
                if frame == start:
                    first_wave_hit = True
                if box["fkb"]:
                    kb = knockback(box, box["fkb"], weight)
                    launch = KB_SCALE * kb
                    if box["linked"]:
                        launch = max(launch, attacker_vy(frame))
                        angle = math.pi / 2
                    else:
                        angle = math.radians(box["angle"])
                    kb_y = launch * math.sin(angle)
                    kb_z = launch * math.cos(angle)
                    normal_vy = 0.0
                    stun = int(.4 * kb) + box["stun_bonus"]
                else:
                    kb = None  # the finisher ends the trajectory being modelled
                contacts.append({"frame": frame, "id": source_id,
                                 "y": relative_y, "z": victim_z,
                                 "distance": distance_to_box, "radius": box["size"],
                                 "reach": reach, "fkb": box["fkb"], "kb": kb,
                                 "angle": 90 if box["linked"] else box["angle"],
                                 "incoming_hitstun": incoming_stun, "hitstun": stun})
        frames.append({"frame": frame, "sora_y": sora_y, "victim_y": victim_y,
                       "relative_y": relative_y, "z": victim_z,
                       "kb_y": kb_y, "kb_z": kb_z, "normal_vy": normal_vy,
                       "hitstun": stun})
        if frame == end:
            break
        magnitude = math.hypot(kb_y, kb_z)
        factor = max(0, magnitude - KB_DECAY) / magnitude if magnitude else 0
        kb_y *= factor
        kb_z *= factor
        normal_vy = max(-terminal, normal_vy - gravity)
        victim_y += normal_vy + kb_y
        victim_z += kb_z
        sora_y += attacker_vy(frame)
        stun = max(0, stun - 1)
    return {"contacts": contacts, "frames": frames}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--acmd", required=True, help="path to trail.acmd.json")
    args = ap.parse_args()
    from trail_specials_geno import UPB_CARRY_PROFILE
    rows = json.load(open(args.acmd, encoding="utf-8"))
    row = next(r for r in rows if r.get("agent") == "trail" and
               r.get("kind") == "game" and r.get("script") == "game_specialhi")
    for distance in (55, 44):
        for fighter in DEFENDERS:
            for label, profile in (("before", None), ("after", UPB_CARRY_PROFILE)):
                trace = simulate(row, distance, fighter, profile)
                print(distance, fighter, label, len(trace["contacts"]))
                for point in trace["contacts"]:
                    print("  f%d id%d y%+.2f z%+.2f d%.2f/%.2f KB%s stun%d" % (
                        point["frame"], point["id"], point["y"], point["z"],
                        point["distance"], point["radius"] + point["reach"],
                        "--" if point["kb"] is None else "%.1f" % point["kb"], point["hitstun"]))


if __name__ == "__main__":
    main()
