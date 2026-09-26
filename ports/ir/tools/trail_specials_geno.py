#!/usr/bin/env python3
"""trail_specials_geno.py - Sora's (trail) physical specials as Geno states (melee docs/geno.md 16, 19):
side special Sonic Blade, up special Aerial Sweep, down special Counter Attack.

    python ports/ir/tools/trail_specials_geno.py -o <mods dir>/<mod id>
        [--acmd _build/tmp/ir/trail.acmd.json] [--attach PlUs.dat] [--host marth|kirby]
        [--magic <trail_magic_geno.py's geno.json>]

--magic is the combine step: the neutral special (lane beta's trail_magic_geno.py output, read,
never edited) goes first, these states after it (their script targets are offset by its state
count), articles and "specials" merged, one geno.json for the Sora slot.

Reads OUR OWN dump: the acmd rows (acmd_parse.py), fighter/trail/param/vl.prc (upstream ParamXML +
ParamLabels.csv) and the special clips' frame counts / Trans tracks (convert_ultimate_anim.decode).
Writes <out>/geno.json, <out>/mod.json and <out>/clips.json (subaction -> the Sora clip it should
play: for the installer), and prints every number with its source. Nothing it writes is committed.

Semantic port (Sora must feel like Ultimate's; Melee's mechanics win):
  1:1 from the dump: every hitbox (damage, angle, kbg, fkb, bkb, size, offset, bone), the frames
  (through FT_MOTION_RATE segments, beta's game_time), the clip lengths and IASA (cancel_frame),
  Sonic Blade's attack_speed_x 3.2, the -1 / -0.5 slow-down at f11, attack_num 3, start / end
  multipliers, end_frame_1-3 35/40/45, end_speed_y 1.5, landing lags (attack 20, up special 21),
  Aerial Sweep's jump_distance 55 (x0.8 in the air), jump_accel_y 0.04, jump_speed_x_mul 0.6,
  Counter Attack's window (flag on f8 - off f26), intangibility (motion list xlu), its lunge (the
  clip's Trans z per frame), speed_y 1.1 in the air.
  Melee's rules: hitlag / SDI multipliers, shield setoff, force reaction, Ultimate's counter damage
  multiplier (1.5x the countered hit, 9..30) - the counter attack hits for its script's 9 %.
  INFERRED (tune in game; printed): the lock-on range 50 (the SEARCH box radius), its angle clamp
  (MAX_LOCK_DEG) and the stick aim without a target (STICK_DEG); the rise profile (constant
  deceleration jump_accel_y reaching jump_distance); the 8-frame hover between dashes.
Not ported: Sonic Blade's 3.0 % follow-up branch (a flag test, default path = 5.2 %, as
acmd_to_ftcmd), the counter's rebound (speciallwrebound) and backward / turn variants (the attack
turns to the nearest opponent instead), Ultimate hitbox ids 4-5 (Melee has 4 hitbox slots: the up
special's two capsules between spheres 0/2 and 1/3).
"""
import argparse
import json
import math
import os
import struct
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
ULT = os.path.join(ROOT, "experiment", "tooling", "ultimate")
PARAMXML = os.path.join(ULT, "apps", "ParamXML", "ParamXML-win-x64", "ParamXML.exe")
LABELS = os.path.join(ULT, "references", "ParamLabels.csv")
VL = os.path.join(ULT, "workspace", "extracted", "fighter", "trail", "param", "vl.prc")
MOTION = os.path.join(ULT, "workspace", "extracted", "fighter", "trail", "motion", "body", "c00")
sys.path.insert(0, HERE)
from acmd_to_ftcmd import ELEM, hitbox_words, default_path  # noqa: E402

LOCK_RANGE = 50         # the SEARCH box radius in game_specialssearch (a sphere approximates it)
MAX_LOCK_DEG = 40       # INFERRED: steepest locked-on dash
STICK_DEG = 25          # INFERRED: stick up / down without a target
HOVER = 8               # d01specialsstart2's length: the pause between dashes (clip frames)

# Geno ids (docs/geno.md 15-19; pc/geno/geno.h)
GENO_OP = 59
LAI, RAI, LAF, RAF = 0, 1, 2, 3
V_AIR, V_FACING, V_VEL_X, V_VEL_Y, V_GROUND_VEL, V_FWD_VEL = 0x00, 0x01, 0x02, 0x03, 0x04, 0x05
V_PRESSED, V_MOVE_F0, V_MOVE_F1 = 0x14, 0x20, 0x21
EQ, NE, LT, LE, GT, GE, BIT, NOBIT = range(8)
C_ALWAYS = 0
BTN_SPECIAL_BIT = 1
HOOK_SPAWN, HOOK_LOCKON = 5, 6
MS_WAIT, MS_FALLSPECIAL = 14, 35
DASH_N = 1              # LA int 1: dashes done (LA int 0 is the magic cycle, beta's)


def fb(x):
    return struct.unpack(">I", struct.pack(">f", float(x)))[0]


def var(bank, i):
    return (bank << 6) | i


def w0(sub, ln, low=0):
    return (GENO_OP << 26) | ((sub & 63) << 20) | ((ln & 15) << 16) | (low & 0xFFFF)


def SYNC(n): return [(1 << 26) | int(n)]
def SET(v, imm): return [w0(0x01, 2, v << 8), imm & 0xFFFFFFFF]
def ADDF(v, x): return [w0(0x02, 2, v << 8), fb(x)]
def MULF(v, x): return [w0(0x04, 2, v << 8), fb(x)]
def MULV(v, b): return [w0(0x04, 2, (v << 8) | 0x80), b]
def SETBIT(v, b): return [w0(0x05, 2, v << 8), b]
def IF(v, cmp, b, skip): return [w0(0x10, 3, (v << 8) | (cmp << 4)), b & 0xFFFFFFFF, skip]
def GET(v, val): return [w0(0x08, 2, v << 8), val]
def PUTF(val, x): return [w0(0x09, 3), val, fb(x)]
def PUTI(val, x): return [w0(0x09, 3), val, x]
def PUTV(val, v): return [w0(0x09, 3, 0x80), val, v]
def IFV(val, cmp, b, skip): return [w0(0x12, 4, cmp << 4), val, b & 0xFFFFFFFF, skip]
def CALL(h, arg): return [w0(0x20, 3), h, arg & 0xFFFFFFFF]
def CHG(target, cond=C_ALWAYS): return [w0(0x30, 2, (cond << 8) | 0x04), target]   # ONCE
def GENO(n): return (2 << 28) | n
INTANGIBLE, NORMAL = [(26 << 26) | 2], [(26 << 26) | 0]   # body collision state (ftColl_8007B62C)
CLEAR, IASA = [16 << 26], [23 << 26]


def hx(words):
    return ["0x%08X" % (w & 0xFFFFFFFF) for w in words]


def lockon_arg(rng, max_deg, stick_deg):
    return (int(rng) & 0xFFFF) | ((int(max_deg) & 0xFF) << 16) | ((int(stick_deg) & 0xFF) << 24)


def params():
    with tempfile.TemporaryDirectory() as t:
        out = os.path.join(t, "vl.xml")
        subprocess.run([PARAMXML, "-d", VL, "-l", LABELS, "-o", out], check=True, capture_output=True)
        root = ET.parse(out).getroot()
    got = {}
    for lst in root.iter("list"):
        name = lst.get("hash")
        sts = lst.findall("struct")
        if name in ("param_special_s", "param_special_hi", "param_special_lw") and sts:
            d = {}
            for c in sts[0]:
                try:
                    d[c.get("hash")] = float(c.text)
                except (TypeError, ValueError):
                    d[c.get("hash")] = c.text
            got[name] = d
    return got


def clip_info(name):
    """frames, per-frame Trans z (forward) deltas of a Sora clip (our dump)."""
    import convert_ultimate_anim as cua
    a = cua.decode(os.path.join(MOTION, name + ".nuanmb"))
    frames = int(round(a["final_frame_index"])) + 1
    g = next(g for g in a["groups"] if g["group_type"] == "Transform")
    nd = {n["name"]: n for n in g["nodes"]}
    z = [0.0]
    if "Trans" in nd:
        z = [v["translation"]["z"] for v in nd["Trans"]["tracks"][0]["values"]["Transform"]]
    dz = [(z[i + 1] - z[i]) if i + 1 < len(z) else 0.0 for i in range(frames)]
    return frames, dz


def game_time(row):
    """anim frame -> game frame, through the script's FT_MOTION_RATE segments (as trail_magic_geno)."""
    rates = sorted((c["frame"], c["args"][0]) for c in row["commands"] if c["cmd"] == "FT_MOTION_RATE")

    def t(f):
        g, cur, last = 0.0, 1.0, 0.0
        for fr, r in rates:
            if fr >= f:
                break
            g += (fr - last) * cur
            last, cur = fr, r
        return g + (f - last) * cur
    return t


# Host subactions the states take over (the host's own special rows: a Geno profile replaces the
# host's specials, so nothing else plays them). Order = STATES below.
HOSTS = {
    "marth": {"SStart": 303, "SStart2": 304, "SDash1": 305, "SDash2": 306, "SDash3": 307, "SEnd": 308,
              "SEndAir": 309, "Hi": 321, "HiAir": 322, "LwStart": 323, "LwAttack": 324,
              "LwStartAir": 325, "LwAttackAir": 326},
    "kirby": {"SStart": 322, "SStart2": 323, "SDash1": 324, "SDash2": 325, "SDash3": 326, "SEnd": 327,
              "SEndAir": 328, "Hi": 329, "HiAir": 330, "LwStart": 332, "LwAttack": 338,
              "LwStartAir": 335, "LwAttackAir": 339},
}
CLIPS = {"SStart": "d01specialsstart", "SStart2": "d01specialsstart2", "SDash1": "d01specials1",
         "SDash2": "d01specials2", "SDash3": "d01specials2", "SEnd": "d01specialsend",
         "SEndAir": "d01specialairsend", "Hi": "d02specialhi", "HiAir": "d02specialairhi",
         "LwStart": "d03speciallwstart", "LwStartAir": "d03specialairlwstart", "LwAttack": "d03speciallw",
         "LwAttackAir": "d03specialairlw"}   # the order build() declares the states in (= their numbers)
STATES = list(CLIPS)


def joints_of_sora():
    import plan_parts
    from convert_ultimate_anim import INSTANCES
    plan = plan_parts.plan(json.load(open(os.path.join(INSTANCES, "trail.ultimate-body.ir.json"), encoding="utf-8")))
    j = {x["name"].lower(): i for i, x in enumerate(plan["joints"])}
    j["top"] = 0
    return j


class Timeline:
    def __init__(self):
        self.ev = []

    def at(self, f, words, order=5):
        self.ev.append((int(round(f)), order, len(self.ev), list(words)))

    def words(self, total, tail):
        out, now = [], 0
        for f, _, _, w in sorted(self.ev):
            if f > now:
                out += SYNC(f - now)
                now = f
            out += w
        if total > now:
            out += SYNC(total - now)
        return out + tail + [0]


def hit_events(tl, row, t, joint_of, rep, name):
    """A game script's ATTACK / clear_all -> Melee hitboxes on the timeline (game frames)."""
    for c in row["commands"]:
        if not default_path(c.get("when", [])):
            continue
        if c["cmd"] == "ATTACK" and c.get("named"):
            n = c["named"]
            if not isinstance(n["id"], int) or n["id"] > 3:
                rep.append("  %s f%d: hitbox id %s dropped (Melee has 4 slots)" % (name, c["frame"], n["id"]))
                continue
            y = n["y"] if n["y2"] is None else (n["y"] + n["y2"]) / 2     # a capsule -> its middle
            z = n["z"] if n["z2"] is None else (n["z"] + n["z2"]) / 2
            j = joint_of.get(n["bone"], 0)
            tl.at(t(c["frame"]), hitbox_words(n["id"], j, n["damage"], n["size"], n["x"], y, z, n["angle"],
                                              n["kbg"], n["fkb"], n["bkb"], ELEM.get(n.get("effect"), 0), 0), 3)
            rep.append("  %s f%d (game %d): id %d %s %.1f%% angle %d kbg %d fkb %d bkb %d size %.1f" % (
                name, c["frame"], round(t(c["frame"])), n["id"], n["bone"], n["damage"], n["angle"],
                n["kbg"], n["fkb"], n["bkb"], n["size"]))
        elif c["cmd"] == "AttackModule::clear_all":
            tl.at(t(c["frame"]), CLEAR, 2)


def build(rows, P, joint_of, host, base, rep):
    game = {r["script"]: r for r in rows if r["kind"] == "game" and r["agent"] == "trail"}
    sub = HOSTS[host]
    idx = {n: base + i for i, n in enumerate(STATES)}
    S, H, L = P["param_special_s"], P["param_special_hi"], P["param_special_lw"]
    states, overlays = [], []

    def state(name, behavior, words, **kw):
        d = {"name": name, "behavior": behavior, "subaction": sub[name], "anim": "hold"}
        d.update(kw)
        states.append(d)
        overlays.append({"index": sub[name], "words": hx(words)})

    ident = lambda f: f
    # ---------------- Sonic Blade ----------------
    speed = S["attack_speed_x"]
    lock = lockon_arg(LOCK_RANGE, MAX_LOCK_DEG, STICK_DEG)
    n_start, _ = clip_info(CLIPS["SStart"])
    tl = Timeline()
    tl.at(0, SET(var(LAI, DASH_N), 0)
          + GET(var(RAF, 0), V_GROUND_VEL) + MULF(var(RAF, 0), S["start_speed_x_mul_ground"]) + PUTV(V_GROUND_VEL, var(RAF, 0))
          + GET(var(RAF, 0), V_VEL_X) + MULF(var(RAF, 0), S["start_speed_x_mul_air"]) + PUTV(V_VEL_X, var(RAF, 0))
          + GET(var(RAF, 1), V_VEL_Y) + MULF(var(RAF, 1), S["start_speed_y_mul_air"]) + PUTV(V_VEL_Y, var(RAF, 1)))
    tl.at(S["search_frame"], CALL(HOOK_LOCKON, lock))
    state("SStart", "geno.air", tl.words(n_start, CHG(GENO(idx["SDash1"])) ), phys="auto", coll="both")
    rep.append("SStart: %d frames (d01specialsstart), speed x%.1f ground / x%.1f air, vy x%.1f; lock-on at f%d "
               "(range %d, clamp %d deg, stick %d deg: INFERRED)" % (n_start, S["start_speed_x_mul_ground"],
               S["start_speed_x_mul_air"], S["start_speed_y_mul_air"], S["search_frame"], LOCK_RANGE, MAX_LOCK_DEG, STICK_DEG))

    tl = Timeline()
    tl.at(0, PUTF(V_FWD_VEL, 0) + PUTF(V_VEL_Y, 0) + PUTF(V_GROUND_VEL, 0))
    tl.at(S["attack_turn_frame"], CALL(HOOK_LOCKON, lock))
    # LA1 = dashes done: 1 -> Dash2, else Dash3
    state("SStart2", "geno.air", tl.words(HOVER, IF(var(LAI, DASH_N), EQ, 1, 2) + CHG(GENO(idx["SDash2"]))
                                          + CHG(GENO(idx["SDash3"]))), phys="none", coll="both")
    rep.append("SStart2: %d-frame hover between dashes (d01specialsstart2), re-aim at f%d (attack_turn_frame)" % (
        HOVER, S["attack_turn_frame"]))

    for n in (1, 2, 3):
        row = game["game_specials%d" % n]
        cancel = int((row.get("motion") or {}).get("cancel_frame") or 13)
        tl = Timeline()
        up_mul = S["attack_up_speed_mul"]
        v = (SET(var(LAI, DASH_N), n)
             + GET(var(RAF, 0), V_MOVE_F0) + MULF(var(RAF, 0), speed)
             + GET(var(RAF, 1), V_MOVE_F1) + MULF(var(RAF, 1), speed))
        upblk = MULF(var(RAF, 0), up_mul) + MULF(var(RAF, 1), up_mul) + PUTI(V_AIR, 1)
        v += IFV(V_MOVE_F1, GT, fb(0.05), len(upblk)) + upblk
        v += (PUTV(V_FWD_VEL, var(RAF, 0)) + PUTV(V_VEL_Y, var(RAF, 1))
              + GET(var(RAF, 2), V_FACING) + MULV(var(RAF, 2), var(RAF, 0)) + PUTV(V_GROUND_VEL, var(RAF, 2)))
        tl.at(0, v, 0)
        hit_events(tl, row, ident, joint_of, rep, "SDash%d" % n)
        for c in row["commands"]:
            if c["cmd"] == "KineticModule::add_speed" and isinstance(c["args"][0], (int, float)):
                dv = float(c["args"][0])
                tl.at(c["frame"], GET(var(RAF, 0), V_FWD_VEL) + ADDF(var(RAF, 0), dv) + PUTV(V_FWD_VEL, var(RAF, 0))
                      + GET(var(RAF, 2), V_FACING) + MULV(var(RAF, 2), var(RAF, 0)) + PUTV(V_GROUND_VEL, var(RAF, 2)), 4)
                rep.append("  SDash%d f%d: forward speed %+.1f (KineticModule::add_speed)" % (n, c["frame"], dv))
        buf = IFV(V_PRESSED, BIT, BTN_SPECIAL_BIT, 2) + SETBIT(var(RAI, 0), 0)
        for f in range(1, cancel):
            tl.at(f, buf, 6)
        tail = []
        if n < int(S["attack_num"]):
            tail += IF(var(RAI, 0), BIT, 0, 2) + CHG(GENO(idx["SStart2"]))
        tail += IFV(V_AIR, EQ, 1, 2) + CHG(GENO(idx["SEndAir"])) + CHG(GENO(idx["SEnd"]))
        state("SDash%d" % n, "geno.air", tl.words(cancel, tail), phys="none", coll="both")
        rep.append("SDash%d: %d frames at %.1f/frame along the aim (x%.2f aimed up), B pressed f1-%d -> next dash" % (
            n, cancel, speed, up_mul, cancel - 1))

    n_end, _ = clip_info(CLIPS["SEnd"])
    body = []
    for k, e in ((1, S["end_frame_1"]), (2, S["end_frame_2"])):
        blk = SYNC(e) + IASA + SYNC(n_end - e) + CHG(MS_WAIT)
        body += IF(var(LAI, DASH_N), EQ, k, len(blk)) + blk
    e3 = S["end_frame_3"]
    body += SYNC(e3) + IASA + SYNC(n_end - e3) + CHG(MS_WAIT) + [0]
    state("SEnd", "geno.ground", body, phys="ground", coll="ground", iasa="interrupt")
    rep.append("SEnd: %d frames (d01specialsend), IASA at %d / %d / %d after 1 / 2 / 3 dashes" % (
        n_end, S["end_frame_1"], S["end_frame_2"], e3))
    n_enda, _ = clip_info(CLIPS["SEndAir"])
    tl = Timeline()
    tl.at(0, GET(var(RAF, 0), V_FWD_VEL) + MULF(var(RAF, 0), S["end_speed_x_mul_air"]) + PUTV(V_FWD_VEL, var(RAF, 0))
          + PUTF(V_VEL_Y, S["end_speed_y"]))
    state("SEndAir", "geno.air", tl.words(n_enda, CHG(MS_FALLSPECIAL)), phys="air_nodrift", coll="air",
          landing_lag=int(S["end_landing_fall_special_frame"]))
    rep.append("SEndAir: %d frames (d01specialairsend), forward x%.1f, vy %.1f, then helpless; landing lag %d" % (
        n_enda, S["end_speed_x_mul_air"], S["end_speed_y"], S["end_landing_fall_special_frame"]))

    # ---------------- Aerial Sweep ----------------
    for name, script, mul in (("Hi", "game_specialhi", 1.0), ("HiAir", "game_specialairhi", H["jump_distance_mul"])):
        row = game[script]
        t = game_time(row)
        frames, _ = clip_info(CLIPS[name])
        total = int(round(t(frames)))
        rise = next(c["frame"] for c in row["commands"] if c["cmd"] == "WorkModule::on_flag"
                    and c["args"] and c["args"][0] == {"const": "0xe610"})
        g0 = int(round(t(rise)))
        dist = H["jump_distance"] * mul
        a = H["jump_accel_y"]
        v0 = math.sqrt(2 * a * dist)
        tl = Timeline()
        tl.at(0, GET(var(RAF, 0), V_GROUND_VEL) + MULF(var(RAF, 0), H["start_speed_x_mul_ground"]) + PUTV(V_GROUND_VEL, var(RAF, 0))
              + GET(var(RAF, 1), V_VEL_Y) + MULF(var(RAF, 1), H["start_speed_y_mul_air"]) + PUTV(V_VEL_Y, var(RAF, 1)), 0)
        tl.at(g0, PUTI(V_AIR, 1) + GET(var(RAF, 0), V_VEL_X) + MULF(var(RAF, 0), H["jump_speed_x_mul"])
              + PUTV(V_VEL_X, var(RAF, 0)), 0)
        for f in range(g0, total):
            tl.at(f, PUTF(V_VEL_Y, v0 - a * (f - g0)), 1)
        hit_events(tl, row, t, joint_of, rep, name)
        state(name, "geno.air", tl.words(total, CHG(MS_FALLSPECIAL)), phys="air_drift", coll="anim_motion",
              ledge="front", landing_lag=int(H["landing_frame"]))
        rep.append("%s: %d game frames (%d clip frames through FT_MOTION_RATE), rise from game f%d: vy %.3f - %.2f/frame "
                   "(peak %.1f units at f%d: jump_distance %.0f x%.1f; profile INFERRED), vx x%.1f, then helpless; landing lag %d" % (
                       name, total, frames, g0, v0, a, dist, g0 + round(v0 / a), H["jump_distance"], mul,
                       H["jump_speed_x_mul"], H["landing_frame"]))

    # ---------------- Counter Attack ----------------
    for name, att, script, air in (("LwStart", "LwAttack", "game_speciallwstart", False),
                                   ("LwStartAir", "LwAttackAir", "game_specialairlwstart", True)):
        row = game[script]
        mo = row.get("motion") or {}
        frames, _ = clip_info(CLIPS[name])
        on = next(c["frame"] for c in row["commands"] if c["cmd"] == "WorkModule::on_flag" and c["args"][0] == {"const": "0xe61c"})
        off = next(c["frame"] for c in row["commands"] if c["cmd"] == "WorkModule::off_flag" and c["args"] and c["args"][0] == {"const": "0xe61c"})
        tl = Timeline()
        if air:
            tl.at(0, GET(var(RAF, 0), V_VEL_X) + MULF(var(RAF, 0), L["start_speed_x_mul_air"]) + PUTV(V_VEL_X, var(RAF, 0))
                  + GET(var(RAF, 1), V_VEL_Y) + MULF(var(RAF, 1), L["start_speed_y_mul_air"])
                  + ADDF(var(RAF, 1), L["start_speed_y_add_air"]) + PUTV(V_VEL_Y, var(RAF, 1)), 0)
        else:
            tl.at(0, GET(var(RAF, 0), V_GROUND_VEL) + MULF(var(RAF, 0), L["start_speed_x_mul_ground"]) + PUTV(V_GROUND_VEL, var(RAF, 0)), 0)
        if mo.get("xlu_end"):
            tl.at(mo["xlu_start"] - 1, INTANGIBLE, 1)
            tl.at(mo["xlu_end"], NORMAL, 1)
        if mo.get("cancel_frame"):
            tl.at(mo["cancel_frame"], IASA, 7)
        win = {"from": int(on) + 1, "to": int(off), "target": "geno:%d" % idx[att], "negate": True}
        kw = dict(phys="air", coll="air") if air else dict(phys="ground", coll="ground")
        state(name, "geno.air" if air else "geno.ground", tl.words(frames, CHG(MS_WAIT)), iasa="interrupt",
              counter=win, **kw)
        rep.append("%s: %d frames, counter window action frames %d-%d (flag 0xe61c f%d-f%d) -> %s, intangible %s-%s, IASA %s" % (
            name, frames, win["from"], win["to"], on, off, att, mo.get("xlu_start"), mo.get("xlu_end"), mo.get("cancel_frame")))

    for name, script, air in (("LwAttack", "game_speciallw", False), ("LwAttackAir", "game_specialairlw", True)):
        row = game[script]
        mo = row.get("motion") or {}
        frames, dz = clip_info(CLIPS[name])
        tl = Timeline()
        tl.at(0, CALL(HOOK_LOCKON, lockon_arg(0, 0, 0)) + PUTF(V_VEL_Y, L["speed_y"] if air else 0.0), 0)
        tl.at(mo["xlu_start"] - 1, INTANGIBLE, 1)
        tl.at(mo["xlu_end"], NORMAL, 1)
        last = None
        for f in range(frames):
            v = round(dz[f], 3)
            if v != last:
                tl.at(f, PUTF(V_FWD_VEL, v), 2)
                last = v
        hit_events(tl, row, ident, joint_of, rep, name)
        if mo.get("cancel_frame"):
            tl.at(mo["cancel_frame"], IASA, 7)
        # "both": the counter can be entered mid-hitlag airborne; it lands and stays in the state
        kw = dict(phys="air_nodrift", coll="air") if air else dict(phys="none", coll="both")
        state(name, "geno.air" if air else "geno.ground", tl.words(frames, CHG(MS_WAIT)), iasa="interrupt", **kw)
        rep.append("%s: %d frames, turns to the nearest opponent, intangible %d-%d, lunge %.1f units (clip Trans z)%s, IASA %s" % (
            name, frames, mo["xlu_start"], mo["xlu_end"], sum(dz), ", vy %.1f" % L["speed_y"] if air else "", mo.get("cancel_frame")))

    assert [x["name"] for x in states] == STATES, "state order must match STATES (script targets are numbers)"
    specials = {"s": "geno:SStart", "air_s": "geno:SStart", "hi": "geno:Hi", "air_hi": "geno:HiAir",
                "lw": "geno:LwStart", "air_lw": "geno:LwStartAir"}
    clips = {str(sub[n]): CLIPS[n] for n in STATES}
    return states, overlays, specials, clips


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--acmd", default=os.path.join(ROOT, "_build", "tmp", "ir", "trail.acmd.json"))
    ap.add_argument("--attach", default="PlUs.dat")
    ap.add_argument("--host", default="marth", choices=sorted(HOSTS))
    ap.add_argument("--magic", help="trail_magic_geno.py's geno.json: merge the neutral special in first")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    rows = json.load(open(a.acmd, encoding="utf-8"))
    P = params()
    rep = []
    magic = None
    base = 0
    if a.magic:
        magic = json.load(open(a.magic, encoding="utf-8"))["fighters"][0]
        base = len(magic.get("states", []))
    states, overlays, specials, clips = build(rows, P, joints_of_sora(), a.host, base, rep)
    fighter = {"attach": a.attach, "name": "Sora specials (Geno, host %s)" % a.host,
               "states": states, "specials": specials, "subactions": overlays}
    if magic:
        used = {o["index"] for o in magic.get("subactions", [])}
        clash = used & {o["index"] for o in overlays}
        if clash:
            sys.exit("subaction overlay clash with the magic profile: %s" % sorted(clash))
        fighter["name"] = "Sora (Geno: magic + physical specials, host %s)" % a.host
        fighter["states"] = magic["states"] + states
        fighter["subactions"] = magic.get("subactions", []) + overlays
        fighter["specials"] = dict(magic.get("specials", {}), **specials)
        if magic.get("articles"):
            fighter["articles"] = magic["articles"]
        rep.append("merged the magic profile: %d states first (%s), %d articles" % (
            base, ", ".join(s["name"] for s in magic["states"]), len(magic.get("articles", []))))
    doc = {"geno": 4, "fighters": [fighter]}
    os.makedirs(os.path.join(a.out, "geno"), exist_ok=True)
    # the registry's JSON reader caps its node count: these overlays (long per-frame scripts) go in
    # word files next to geno.json ("file", docs/geno.md 15.5)
    for o in overlays:
        rel = "geno/sora_sp_%d.txt" % o["index"]
        with open(os.path.join(a.out, rel), "w", encoding="utf-8") as f:
            f.write("# trail_specials_geno.py, subaction %d\n" % o["index"])
            for k in range(0, len(o["words"]), 8):
                f.write(" ".join(o["words"][k:k + 8]) + "\n")
        o.pop("words")
        o["file"] = rel
    with open(os.path.join(a.out, "geno.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)
    with open(os.path.join(a.out, "clips.json"), "w", encoding="utf-8") as f:
        json.dump({"host": a.host, "subaction_clips": clips}, f, indent=1)
    with open(os.path.join(a.out, "mod.json"), "w", encoding="utf-8") as f:
        json.dump({"id": os.path.basename(os.path.normpath(a.out)), "name": "Sora specials (Geno)",
                   "version": "0.1.0", "kind": "misc",
                   "description": "Sora's Sonic Blade / Aerial Sweep / Counter Attack (and with --magic the magic) as Geno "
                                  "states on %s, from trail_specials_geno.py." % a.attach}, f, indent=1)
    print("\n".join(rep))
    print("wrote", os.path.join(a.out, "geno.json"), "-", len(fighter["states"]), "states,",
          len(fighter["subactions"]), "overlays")


if __name__ == "__main__":
    main()
