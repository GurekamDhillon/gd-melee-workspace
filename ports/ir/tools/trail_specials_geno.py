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
  Melee's rules: hitlag / SDI multipliers, shield setoff, force reaction. The counter's damage IS
  ported (Sora's own move property): the countered hit x attack_mul 1.5, clamped 9..30 (Geno HBDMG).
  INFERRED (tune in game; printed): the lock-on range 50 (the SEARCH box radius), its angle clamp
  (MAX_LOCK_DEG) and the stick aim without a target (STICK_DEG); the rise profile (constant
  deceleration jump_accel_y reaching jump_distance); the 8-frame hover between dashes.
Default ON (--no-... to drop): --sonic-hit-branch saves ATTACK_CONNECTED_PREV (engine value 0x3C) in the between-dash
hover, then selects both follow-up hitbox sets from that saved value; --counter-backward adds
backward counter attacks after lock-on reverses facing; and
--counter-rebound adds the rebound clips as unreachable states (the status trigger is absent from
the dump). The 7-frame counter turn clips are recorded for the installer but have no Geno state.
Ultimate hitbox ids 4-5 share Melee's four live slots through acmd_to_ftcmd's remapper.
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
from acmd_to_ftcmd import ELEM, hitbox_words, default_path, needs_hitbox_remap, remap_hitboxes, apply_autolink, carry_hit_commands  # noqa: E402

LOCK_RANGE = 50         # the SEARCH box radius in game_specialssearch (a sphere approximates it)
MAX_LOCK_DEG = 40       # INFERRED: steepest locked-on dash
STICK_DEG = 25          # INFERRED: stick up / down without a target
# ---- Sonic Blade steering (echo, from _research/ultimate-sonic-blade-steering.md) ----------------
# Confirmed (vl.prc param_special_s, checked against our own decode): search_stick 0.25 (a stick-vector
# length threshold), attack_up_angle_min/max 40/140 (the heading range that gets attack_up_speed_mul
# 0.85). The heading is the stick's polar angle (the note's reading of the status code, Astra-assisted).
# BEST-FIT (not in the data; tune here): the steepest heading up / down, whether the stick may turn Sora.
STEER_MAX_UP = 60       # BEST-FIT: degrees above the horizontal
STEER_MAX_DOWN = 60     # BEST-FIT: degrees below (never down on the ground: Geno's rule)
STEER_TURN = True       # BEST-FIT: a stick pointing behind turns Sora (the note: set_lr when the aim is behind)
HOOK_AIM_STICK = 7      # geno.aim_stick (melee docs/geno.md 19.12)
V_MOVE_I0, V_MOVE_I2 = 0x28, 0x2A


def steer_words(S):
    """The steering step, run where the lock-on runs (search_frame in SStart, attack_turn_frame in the
    hover): a locked-on target wins (geno.lockon's MOVE_I0 = 1); otherwise the stick's polar heading
    past search_stick, else the previous dash's saved heading (MOVE_I2), else level."""
    arg = (int(round(S["search_stick"] * 100)) & 0xFF) | ((STEER_MAX_UP & 0xFF) << 8) |           ((STEER_MAX_DOWN & 0xFF) << 16) | ((1 if STEER_TURN else 0) << 24)
    call = CALL(HOOK_AIM_STICK, arg)
    return IFV(V_MOVE_I0, EQ, 0, len(call)) + call


def steer_up_mul_test(S):
    """Heading inside attack_up_angle_min..max (40-140 deg) <=> up component above sin(40 deg)."""
    return fb(math.sin(math.radians(S["attack_up_angle_min"])))
# ---- end of steering --------------------------------------------------------------------------------

HOVER = 8               # d01specialsstart2's length: the pause between dashes (clip frames)

# Geno ids (docs/geno.md 15-19; pc/geno/geno.h)
GENO_OP = 59
LAI, RAI, LAF, RAF = 0, 1, 2, 3
V_AIR, V_FACING, V_VEL_X, V_VEL_Y, V_GROUND_VEL, V_FWD_VEL = 0x00, 0x01, 0x02, 0x03, 0x04, 0x05
V_ANIM_FRAME, V_PRESSED, V_ANIM_RATE = 0x0D, 0x14, 0x1B
V_MOVE_F0, V_MOVE_F1, V_HIT_DAMAGE = 0x20, 0x21, 0x35
V_ATTACK_CONNECTED_PREV = 0x3C  # last action's hit; copy in the hover before the next dash
EQ, NE, LT, LE, GT, GE, BIT, NOBIT = range(8)
C_ALWAYS = 0
BTN_SPECIAL_BIT = 1
BTN_ATTACK = 1
HOOK_SPAWN, HOOK_LOCKON = 5, 6
MS_WAIT, MS_FALLSPECIAL = 14, 35
DASH_N = 1              # LA int 1: dashes done (LA int 0 is the magic cycle, beta's)
SONIC_PREV_N = 2        # LA int 2: previous dash's connection across hover -> next dash
# _research/ultimate-trail-status.md §3: vl.prc 0x1A41A10288 boosts dash speed when the copied flag is true.
SONIC_DASH_ENHANCE_MUL = 1.15


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
def SETF(v, x): return [w0(0x01, 2, v << 8), fb(x)]
def HBDMG(mask, v): return [w0(0x3A, 2, ((mask & 0xFF) << 8) | 0x80), v]   # v5.3
def GET(v, val): return [w0(0x08, 2, v << 8), val]
def PUTF(val, x): return [w0(0x09, 3), val, fb(x)]
def PUTI(val, x): return [w0(0x09, 3), val, x]
def PUTV(val, v): return [w0(0x09, 3, 0x80), val, v]
def IFV(val, cmp, b, skip, b_var=False): return [w0(0x12, 4, (cmp << 4) | (0x80 if b_var else 0)), val, b & 0xFFFFFFFF, skip]
def CALL(h, arg): return [w0(0x20, 3), h, arg & 0xFFFFFFFF]
def CHG(target, cond=C_ALWAYS): return [w0(0x30, 2, (cond << 8) | 0x04), target]   # ONCE
def GENO(n): return (2 << 28) | n
ORIG = [w0(0x13, 1)]
INTANGIBLE, NORMAL = [(26 << 26) | 2], [(26 << 26) | 0]   # body collision state (ftColl_8007B62C)
CLEAR, IASA = [16 << 26], [23 << 26]


def combo_chain_check(target, first, last, button=BTN_ATTACK):
    """Persistent fresh-press transition, limited to an inclusive animation-frame window.

    CHG permits three conditions: PRESSED, FRAME >= first, ANIM_FRAME <= last.
    This also works as an ORIG prefix on an existing common-action script.
    Forward stick is checked by the common AttackS3 entry; follow-ups use A alone.
    """
    if first > last:
        raise ValueError("combo window opens after it closes")
    return ([w0(0x30, 3, 4 << 8), GENO(target), button]
            + [w0(0x31, 2, 8 << 8), first]
            + [w0(0x31, 3, (9 << 8) | (LE << 4)), V_ANIM_FRAME, fb(last)])


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
              "LwStartAir": 325, "LwAttackAir": 326, "LwAttackBack": 310, "LwAttackBackAir": 311,
              "LwRebound": 312, "LwReboundAir": 313, "S3Combo2": 315, "S3Combo3": 316},
    "kirby": {"SStart": 322, "SStart2": 323, "SDash1": 324, "SDash2": 325, "SDash3": 326, "SEnd": 327,
              "SEndAir": 328, "Hi": 329, "HiAir": 330, "LwStart": 332, "LwAttack": 338,
              "LwStartAir": 335, "LwAttackAir": 339, "LwAttackBack": 340, "LwAttackBackAir": 341,
              "LwRebound": 342, "LwReboundAir": 343, "S3Combo2": 333, "S3Combo3": 334},
}
CLIPS = {"SStart": "d01specialsstart", "SStart2": "d01specialsstart2", "SDash1": "d01specials1",
         "SDash2": "d01specials2", "SDash3": "d01specials2", "SEnd": "d01specialsend",
         "SEndAir": "d01specialairsend", "Hi": "d02specialhi", "HiAir": "d02specialairhi",
         "LwStart": "d03speciallwstart", "LwStartAir": "d03specialairlwstart", "LwAttack": "d03speciallw",
         "LwAttackAir": "d03specialairlw", "LwAttackBack": "d03speciallwbackward",
         "LwAttackBackAir": "d03specialairlwbackward", "LwRebound": "d03speciallwrebound",
         "LwReboundAir": "d03specialairlwrebound", "S3Combo2": "c00attack12",
         "S3Combo3": "c01attacks33"}   # declaration order (= state numbers)
STATES = list(CLIPS)
BASE_STATES = STATES[:STATES.index("LwAttackBack")]
BACK_STATES = ["LwAttackBack", "LwAttackBackAir"]
REBOUND_STATES = ["LwRebound", "LwReboundAir"]
COMBO_STATES = ["S3Combo2", "S3Combo3"]
S3_ROWS = (53, 54, 55, 56, 57)  # Marth/Kirby AttackS3 angle rows


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
    events = []
    carry_hits = carry_hit_commands(row)
    for c in row["commands"]:
        if not default_path(c.get("when", [])):
            continue
        if c["cmd"] == "ATTACK" and c.get("named"):
            n = c["named"]
            if not isinstance(n["id"], int):
                rep.append("  %s f%d: hitbox id %s dropped (Melee has 4 slots)" % (name, c["frame"], n["id"]))
                continue
            y = n["y"] if n["y2"] is None else (n["y"] + n["y2"]) / 2     # a capsule -> its middle
            z = n["z"] if n["z2"] is None else (n["z"] + n["z2"]) / 2
            j = joint_of.get(n["bone"], 0)
            words = hitbox_words(n["id"], j, n["damage"], n["size"], n["x"], y, z, n["angle"],
                                 n["kbg"], n["fkb"], n["bkb"], ELEM.get(n.get("effect"), 0), 0)
            events.append((c["frame"], "hit", {"words": words, "key": ("attack", n["id"]),
                                                "id": n["id"], "damage": n["damage"], "radius": n["size"],
                                                "carry": id(c) in carry_hits}))
            rep.append("  %s f%d (game %d): id %d %s %.1f%% angle %d kbg %d fkb %d bkb %d size %.1f" % (
                name, c["frame"], round(t(c["frame"])), n["id"], n["bone"], n["damage"], n["angle"],
                n["kbg"], n["fkb"], n["bkb"], n["size"]))
        elif c["cmd"] == "AttackModule::clear_all":
            events.append((c["frame"], "clear", CLEAR))
    if needs_hitbox_remap(events):
        details = {}
        events = remap_hitboxes(events, details)
        for drop in details.get("dropped_hitboxes", []):
            rep.append("  %s f%d: hitbox id %d dropped (%s)" %
                       (name, drop["frame"], drop["id"], drop["reason"]))
    events = apply_autolink(events)
    for frame, kind, payload in events:
        tl.at(t(frame), payload["words"] if isinstance(payload, dict) else payload,
              2 if kind == "clear" else 3)


def sonic_branch_hit_events(tl, row, joint_of, rep, name):
    """Keep both frame-3 flag branches; value 0 means no previous dash hit."""
    branches = {3.0: [], 5.2: []}
    for c in row["commands"]:
        if c["cmd"] != "ATTACK" or c["frame"] != 3 or not c.get("named") or not c.get("when"):
            continue
        n = c["named"]
        if n["damage"] not in branches or n["id"] not in (0, 1, 2):
            raise ValueError("unexpected Sonic Blade follow-up branch: %s" % c)
        if len(c["when"]) != 1 or c["when"][0]["holds"] != (n["damage"] == 3.0):
            raise ValueError("Sonic Blade flag branch no longer matches the dump: %s" % c)
        y = n["y"] if n["y2"] is None else (n["y"] + n["y2"]) / 2
        z = n["z"] if n["z2"] is None else (n["z"] + n["z2"]) / 2
        branches[n["damage"]].append((n["id"], hitbox_words(n["id"], joint_of.get(n["bone"], 0),
            n["damage"], n["size"], n["x"], y, z, n["angle"], n["kbg"], n["fkb"],
            n["bkb"], ELEM.get(n.get("effect"), 0), 0)))
        rep.append("  %s f3: connected=%d id %d %.1f%% angle %d kbg %d bkb %d" % (
            name, n["damage"] == 5.2, n["id"], n["damage"], n["angle"], n["kbg"], n["bkb"]))
    if any(sorted(i for i, _ in branch) != [0, 1, 2] for branch in branches.values()):
        raise ValueError("Sonic Blade follow-up must have three hitboxes in each branch")
    weak = sum((words for _, words in sorted(branches[3.0])), [])
    strong = sum((words for _, words in sorted(branches[5.2])), [])
    # IF skips only when its test fails: disconnected -> 3.0%, connected -> 5.2%.
    prev = var(LAI, SONIC_PREV_N)
    tl.at(3, IF(prev, EQ, 0, len(weak)) + weak
          + IF(prev, EQ, 1, len(strong)) + strong, 3)
    nonbranch = dict(row, commands=[c for c in row["commands"] if not (
        c["cmd"] == "ATTACK" and c["frame"] == 3 and c.get("when"))])
    hit_events(tl, nonbranch, lambda f: f, joint_of, rep, name)


def build(rows, P, joint_of, host, base, rep, sonic_hit_branch=False, counter_backward=False,
          counter_rebound=False, combo_chain=True):
    game = {r["script"]: r for r in rows if r["kind"] == "game" and r["agent"] == "trail"}
    sub = HOSTS[host]
    active = (BASE_STATES + (BACK_STATES if counter_backward else [])
              + (REBOUND_STATES if counter_rebound else []) + (COMBO_STATES if combo_chain else []))
    idx = {n: base + i for i, n in enumerate(active)}
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
    tl.at(0, PUTI(V_MOVE_I2, 0) + SET(var(LAI, DASH_N), 0)
          + GET(var(RAF, 0), V_GROUND_VEL) + MULF(var(RAF, 0), S["start_speed_x_mul_ground"]) + PUTV(V_GROUND_VEL, var(RAF, 0))
          + GET(var(RAF, 0), V_VEL_X) + MULF(var(RAF, 0), S["start_speed_x_mul_air"]) + PUTV(V_VEL_X, var(RAF, 0))
          + GET(var(RAF, 1), V_VEL_Y) + MULF(var(RAF, 1), S["start_speed_y_mul_air"]) + PUTV(V_VEL_Y, var(RAF, 1)))
    tl.at(S["search_frame"], CALL(HOOK_LOCKON, lock) + steer_words(S))
    state("SStart", "geno.air", tl.words(n_start, CHG(GENO(idx["SDash1"])) ), phys="auto", coll="both")
    rep.append("SStart: %d frames (d01specialsstart), speed x%.1f ground / x%.1f air, vy x%.1f; lock-on at f%d "
               "(range %d, clamp %d deg, stick %d deg: INFERRED)" % (n_start, S["start_speed_x_mul_ground"],
               S["start_speed_x_mul_air"], S["start_speed_y_mul_air"], S["search_frame"], LOCK_RANGE, MAX_LOCK_DEG, STICK_DEG))

    tl = Timeline()
    tl.at(0, (GET(var(LAI, SONIC_PREV_N), V_ATTACK_CONNECTED_PREV) if sonic_hit_branch else [])
          + PUTF(V_FWD_VEL, 0) + PUTF(V_VEL_Y, 0) + PUTF(V_GROUND_VEL, 0))
    tl.at(S["attack_turn_frame"], CALL(HOOK_LOCKON, lock) + steer_words(S))
    # LA1 = dashes done: 1 -> Dash2, else Dash3
    state("SStart2", "geno.air", tl.words(HOVER, IF(var(LAI, DASH_N), EQ, 1, 2) + CHG(GENO(idx["SDash2"]))
                                          + CHG(GENO(idx["SDash3"]))), phys="none", coll="both")
    rep.append("SStart2: %d-frame hover between dashes (d01specialsstart2), re-aim at f%d (attack_turn_frame)%s" % (
        HOVER, S["attack_turn_frame"], ", save ATTACK_CONNECTED_PREV in LA int 2 at f0" if sonic_hit_branch else ""))

    for n in (1, 2, 3):
        row = game["game_specials%d" % n]
        cancel = int((row.get("motion") or {}).get("cancel_frame") or 13)
        tl = Timeline()
        up_mul = S["attack_up_speed_mul"]
        v = (SET(var(LAI, DASH_N), n)
             + GET(var(RAF, 0), V_MOVE_F0) + MULF(var(RAF, 0), speed)
             + GET(var(RAF, 1), V_MOVE_F1) + MULF(var(RAF, 1), speed))
        upblk = MULF(var(RAF, 0), up_mul) + MULF(var(RAF, 1), up_mul)
        v += IFV(V_MOVE_F1, GT, steer_up_mul_test(S), len(upblk)) + upblk       # 40-140 deg: x0.85
        if n > 1 and sonic_hit_branch:
            boost = MULF(var(RAF, 0), SONIC_DASH_ENHANCE_MUL) + MULF(var(RAF, 1), SONIC_DASH_ENHANCE_MUL)
            v += IF(var(LAI, SONIC_PREV_N), EQ, 1, len(boost)) + boost
        v += IFV(V_MOVE_F1, GT, fb(0.05), 3) + PUTI(V_AIR, 1)                   # aimed up: lift off
        v += (PUTV(V_FWD_VEL, var(RAF, 0)) + PUTV(V_VEL_Y, var(RAF, 1))
              + GET(var(RAF, 2), V_FACING) + MULV(var(RAF, 2), var(RAF, 0)) + PUTV(V_GROUND_VEL, var(RAF, 2)))
        tl.at(0, v, 0)
        if n > 1 and sonic_hit_branch:
            sonic_branch_hit_events(tl, row, joint_of, rep, "SDash%d" % n)
        else:
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

    attacks = [("LwAttack", "game_speciallw", False), ("LwAttackAir", "game_specialairlw", True)]
    if counter_backward:
        attacks += [("LwAttackBack", "game_speciallw", False),
                    ("LwAttackBackAir", "game_specialairlw", True)]
    for name, script, air in attacks:
        row = game[script]
        mo = row.get("motion") or {}
        frames, dz = clip_info(CLIPS[name])
        tl = Timeline()
        back = name in BACK_STATES
        lead = []
        if not back:
            if counter_backward:
                lead += GET(var(RAF, 6), V_FACING)
            lead += CALL(HOOK_LOCKON, lockon_arg(0, 0, 0))
            if counter_backward:
                change = CHG(GENO(idx["LwAttackBackAir" if air else "LwAttackBack"]))
                lead += IFV(V_FACING, NE, var(RAF, 6), len(change), b_var=True) + change
        lead += PUTF(V_VEL_Y, L["speed_y"] if air else 0.0)
        tl.at(0, lead, 0)
        tl.at(mo["xlu_start"] - 1, INTANGIBLE, 1)
        tl.at(mo["xlu_end"], NORMAL, 1)
        last = None
        for f in range(frames):
            # Back: lock-on has already turned Sora to face the attacker behind him, so the backward
            # clip's retreat (Trans z < 0 in Sora's original facing) is a move TOWARD the attacker:
            # forward along the new facing, the clip's distance per frame
            v = -dz[f] if back else round(dz[f], 3)
            if back or v != last:
                tl.at(f, PUTF(V_FWD_VEL, v), 2)
                last = v
        hit_events(tl, row, ident, joint_of, rep, name)
        # Ultimate's counter damage: the countered hit x attack_mul, clamped attack_min..attack_max
        # (HIT_DAMAGE, Geno 19.3), written over the script's hitboxes each time they are (re)set
        dmg = var(RAF, 5)
        tl.at(0, GET(dmg, V_HIT_DAMAGE) + MULF(dmg, L["attack_mul"])
              + IF(dmg, LT, fb(L["attack_min"]), 2) + SETF(dmg, L["attack_min"])
              + IF(dmg, GT, fb(L["attack_max"]), 2) + SETF(dmg, L["attack_max"]), 0)
        for c in row["commands"]:
            if c["cmd"] == "ATTACK" and c.get("named") and isinstance(c["named"]["id"], int) and c["named"]["id"] < 4:
                tl.at(c["frame"], HBDMG(1 << c["named"]["id"], dmg), 4)
        rep.append("  %s: damage = countered hit x%.1f, clamped %.0f..%.0f (HBDMG)" % (
            name, L["attack_mul"], L["attack_min"], L["attack_max"]))
        if mo.get("cancel_frame"):
            tl.at(mo["cancel_frame"], IASA, 7)
        # "both": the counter can be entered mid-hitlag airborne; it lands and stays in the state
        kw = dict(phys="air_nodrift", coll="air") if air else dict(phys="none", coll="both")
        state(name, "geno.air" if air else "geno.ground", tl.words(frames, CHG(MS_WAIT)), iasa="interrupt", **kw)
        rep.append("%s: %d frames, %s, intangible %d-%d, lunge %.4f units (clip Trans z)%s, IASA %s" % (
            name, frames, "backward along new facing after lock-on" if back else "turns to nearest opponent",
            mo["xlu_start"], mo["xlu_end"], sum(dz), ", vy %.1f" % L["speed_y"] if air else "",
            mo.get("cancel_frame")))

    if counter_backward:
        for name, turn_clip in (("LwAttackBack", "d03speciallwturn"),
                                ("LwAttackBackAir", "d03specialairlwturn")):
            turn_frames, _ = clip_info(turn_clip)
            rep.append("%s: %s is a %d-frame visual lead-in in clips.json (no Geno state)" % (
                name, turn_clip, turn_frames))

    if counter_rebound:
        for name, air in (("LwRebound", False), ("LwReboundAir", True)):
            frames, _ = clip_info(CLIPS[name])
            row = game["game_specialairlwrebound" if air else "game_speciallwrebound"]
            mo = row.get("motion") or {}
            if mo.get("xlu_start") != 1 or mo.get("xlu_end", 0) < frames:
                raise ValueError("rebound clip is not intangible for its full duration")
            tl = Timeline()
            tl.at(0, INTANGIBLE)
            kw = dict(phys="air_nodrift", coll="air") if air else dict(phys="none", coll="both")
            state(name, "geno.air" if air else "geno.ground", tl.words(frames, NORMAL + CHG(MS_WAIT)), **kw)
            rep.append("%s: %d frames, intangible throughout, no hitboxes; unreachable because the "
                       "Ultimate rebound status trigger is not in the dump" % (name, frames))
        rep.append("rebound params (vl.prc): " + ", ".join(
            "%s=%s" % (key, L[key]) for key in sorted(L) if key.startswith("rebound_"))
            + "; trigger unknown")

    # ---------------- Ground attack combo chain ----------------
    if combo_chain:
        # An overlay prefix registers the check and ORIG resumes the installed game_attacks3
        # script, including its hitboxes and ModelVis. All five angle rows share that script.
        # The installed translator selects the default 7.2% branch; its ACMD combo flag is
        # conditional on the alternate 5.2% branch. Keep the installed hitboxes unchanged.
        for row_id in S3_ROWS:
            overlays.append({"index": row_id, "words": hx(combo_chain_check(idx["S3Combo2"], 29, 44) + ORIG)})
        for name, script, next_name, first, last in (
                ("S3Combo2", "game_attacks32", "S3Combo3", 18, 40),
                ("S3Combo3", "game_attacks33", None, None, None)):
            row = game[script]
            frames, _ = clip_info(CLIPS[name])
            tl = Timeline()
            if next_name:
                tl.at(0, combo_chain_check(idx[next_name], first, last), 0)
            for command in row["commands"]:
                if command["cmd"] == "FT_MOTION_RATE" and command.get("args"):
                    tl.at(command["frame"], PUTF(V_ANIM_RATE, command["args"][0]), 1)
            hit_events(tl, row, lambda f: f, joint_of, rep, name)
            cancel = (row.get("motion") or {}).get("cancel_frame")
            if cancel:
                tl.at(cancel, IASA, 7)
            state(name, "geno.anim_motion", tl.words(frames, []), anim="next", iasa="interrupt", ledge="none")
            rep.append("%s: %s on %s (%d clip frames)%s" % (
                name, script, CLIPS[name], frames,
                ", fresh A f%d-%d -> %s" % (first, last, next_name) if next_name else ""))

    assert active == [name for name in STATES if name in active]
    assert [x["name"] for x in states] == active, "state order must match STATES (script targets are numbers)"
    specials = {"s": "geno:SStart", "air_s": "geno:SStart", "hi": "geno:Hi", "air_hi": "geno:HiAir",
                "lw": "geno:LwStart", "air_lw": "geno:LwStartAir"}
    clips = {str(sub[n]): CLIPS[n] for n in active}
    return states, overlays, specials, clips


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--acmd", default=os.path.join(ROOT, "_build", "tmp", "ir", "trail.acmd.json"))
    ap.add_argument("--attach", default="PlUs.dat")
    ap.add_argument("--host", default="marth", choices=sorted(HOSTS))
    ap.add_argument("--magic", help="trail_magic_geno.py's geno.json: merge the neutral special in first")
    ap.add_argument("--sonic-hit-branch", action=argparse.BooleanOptionalAction, default=True, help="(default on) save ATTACK_CONNECTED_PREV in the hover and branch follow-up hitboxes on LA int 2; --no-sonic-hit-branch = always 5.2 %%")
    ap.add_argument("--counter-backward", action=argparse.BooleanOptionalAction, default=True, help="(default on) counter attack's backward variant when lock-on reverses facing; --no-counter-backward to drop it")
    ap.add_argument("--counter-rebound", action="store_true", help="emit the unreachable counter rebound states")
    ap.add_argument("--combo-chain", action=argparse.BooleanOptionalAction, default=True,
                    help="(default on) Sora's AttackS3 three-stage chain")
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
    states, overlays, specials, clips = build(rows, P, joints_of_sora(), a.host, base, rep,
        sonic_hit_branch=a.sonic_hit_branch, counter_backward=a.counter_backward,
        counter_rebound=a.counter_rebound, combo_chain=a.combo_chain)
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
    clip_doc = {"host": a.host, "subaction_clips": clips}
    if a.counter_backward:
        clip_doc["turn_clips"] = {str(HOSTS[a.host]["LwAttackBack"]): "d03speciallwturn",
                                  str(HOSTS[a.host]["LwAttackBackAir"]): "d03specialairlwturn"}
    with open(os.path.join(a.out, "clips.json"), "w", encoding="utf-8") as f:
        json.dump(clip_doc, f, indent=1)
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
