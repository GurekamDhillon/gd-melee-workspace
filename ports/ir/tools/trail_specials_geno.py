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
  Sonic Blade follows the status code (_research/ultimate-sonic-blade-spec-2026-10-03.md): dash 1
  straight and never aimed; SEARCH (search_frame 9: a target inside the SEARCH sphere's radius 50
  locks and the stick is then ignored, else the last stick sample >= search_stick aims, the full
  circle, no clamp); TURN (8-frame level / up / down clip, facing = the aim's side unless within 20
  degrees of vertical); dashes 2 and 3 always airborne at 3.2 x 0.92^n, x0.85 aimed 40-140 degrees
  without a target, x1.15 "powered" (special latched and not stick-aimed, which also selects the 5.2 %
  hitboxes); the chain continues on stick deflection at a dash's last frame or the special latched in
  its window; END plays in exactly end_frame_1/2/3 game frames with the status's own brake / gravity.
  NOT ported (outside the status script or needing assets): the aim cursor and lock marker, the
  35-frame head-on contact counter, the last-dash ledge assist, ledge grabs during a dash, the 0.98
  factor (its counter has no writer in the script), the start status's own timing.
  BEST-FIT: add_speed at frame 11 is taken off the dash speed along its heading; SEARCH and TURN
  hover (no gravity); the target point is the opponent's position (the real point is not in our data).
  INFERRED: the Aerial Sweep rise profile (constant deceleration jump_accel_y reaching jump_distance).
Default ON (--no-... to drop): --sonic-hit-branch emits both follow-up hitbox sets, selected by the powered flag; --counter-backward adds
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
from acmd_to_ftcmd import (attack_spheres, default_path, needs_hitbox_remap, remap_hitboxes,
                           apply_autolink, carry_hit_commands, carry_fkb_floor, validate_attack,
                           hit_extras, clear_rehit, reaction_stun_args,
                           force_reaction_args)  # noqa: E402
from acmd_loss import LossGuard, write_losses, verify_acmd_source  # noqa: E402

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

# ---- Sonic Blade as the status code runs it (_research/ultimate-sonic-blade-spec-2026-10-03.md) ----
# Dash 1 is never aimed. Between dashes: SEARCH (search_frame game frames: a target in range locks and
# then the stick is ignored, else the last stick sample past search_stick is the aim, the full circle)
# then TURN (the 8-frame turn clip: level / up / down by the aim), then the dash along the aim.
HOOK_DASH_SEARCH, HOOK_DASH_AIM, HOOK_BRAKE = 8, 9, 10   # geno.dash.search / geno.dash.aim / geno.brake (v5.4)
V_STICK_LEN = 0x3D
V_STICK_X = 0x08
SIDE_CANCEL_STICK = 0.5   # BEST-FIT: the side-special stick test of Aerial Sweep's cancel window
V_MOVE_I3, V_MOVE_I4 = 0x2B, 0x2C
V_MOVE_F5, V_MOVE_F6, V_MOVE_F7 = 0x25, 0x26, 0x27      # phys "brake": brake, gravity, vertical clamp

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
# LA int 2: the dash is "powered" (work flag 0xe648 = special latched and NOT aimed with the stick; a
# locked target counts as not stick): speed x 0x1A41A10288 (1.15) and the 5.2 % hitbox set. Nothing in
# the status code reads whether a dash connected; the old "previous dash hit" reading was wrong.
SONIC_POWER_N = SONIC_PREV_N = 2
LATCH_N = 3             # LA int 3: special pressed inside the dash's window (work flag 0xe650)


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
    if any(not isinstance(rate, (int, float)) or isinstance(rate, bool) or
           not math.isfinite(rate) or rate <= 0 for _, rate in rates):
        raise ValueError("baked motion rate must be finite and positive")

    def t(f):
        g, cur, last = 0.0, 1.0, 0.0
        for fr, r in rates:
            if fr >= f:
                break
            g += (fr - last) * cur   # r = game frames per clip frame
            last, cur = fr, r
        return g + (f - last) * cur
    return t


# Host subactions the states take over (the host's own special rows: a Geno profile replaces the
# host's specials, so nothing else plays them). Order = STATES below.
HOSTS = {
    "marth": {"SStart": 303, "SStart2": 304, "SDash1": 305, "SDash2": 306, "SDash3": 307, "SEnd": 308,
              "SEndAir": 309, "Hi": 321, "HiAir": 322, "LwStart": 323, "LwAttack": 324,
              "LwStartAir": 325, "LwAttackAir": 326, "LwAttackBack": 310, "LwAttackBackAir": 311,
              "LwRebound": 312, "LwReboundAir": 313, "S3Combo2": 315, "S3Combo3": 316,
              "SSearch": 314, "STurnUp": 317, "STurnDown": 318},
    "kirby": {"SStart": 322, "SStart2": 323, "SDash1": 324, "SDash2": 325, "SDash3": 326, "SEnd": 327,
              "SEndAir": 328, "Hi": 329, "HiAir": 330, "LwStart": 332, "LwAttack": 338,
              "LwStartAir": 335, "LwAttackAir": 339, "LwAttackBack": 340, "LwAttackBackAir": 341,
              "LwRebound": 342, "LwReboundAir": 343, "S3Combo2": 333, "S3Combo3": 334,
              "SSearch": 344, "STurnUp": 345, "STurnDown": 346},   # kirby rows: not checked against a host table
}
CLIPS = {"SStart": "d01specialsstart", "SStart2": "d01specialsstart2", "SDash1": "d01specials1",
         "SDash2": "d01specials2", "SDash3": "d01specials2", "SEnd": "d01specialsend",
         "SEndAir": "d01specialairsend", "Hi": "d02specialhi", "HiAir": "d02specialairhi",
         "LwStart": "d03speciallwstart", "LwStartAir": "d03specialairlwstart", "LwAttack": "d03speciallw",
         "LwAttackAir": "d03specialairlw", "LwAttackBack": "d03speciallwbackward",
         "LwAttackBackAir": "d03specialairlwbackward", "LwRebound": "d03speciallwrebound",
         "LwReboundAir": "d03specialairlwrebound", "S3Combo2": "c00attack12",
         "S3Combo3": "c01attacks33",
         # Sonic Blade's aim window and the aimed turn clips (SStart2 is the level turn). Last, so the
         # numbers of every earlier state stay what installed profiles and tests know.
         "SSearch": "d01specialssearch", "STurnUp": "d01specialsup",
         "STurnDown": "d01specialsdown"}   # declaration order (= state numbers)
STATES = list(CLIPS)
BASE_STATES = STATES[:STATES.index("LwAttackBack")]
BACK_STATES = ["LwAttackBack", "LwAttackBackAir"]
REBOUND_STATES = ["LwRebound", "LwReboundAir"]
COMBO_STATES = ["S3Combo2", "S3Combo3"]
SIDE_EXTRA_STATES = ["SSearch", "STurnUp", "STurnDown"]
# The grab pull-in. Melee's CatchPull (213) and CatchDashPull (215) carry the Catch clip on, so a
# successful grab looked like a whiff; Ultimate has a pull clip of its own. It goes on a spare host
# row with an empty script and the profile's "motion_anims" (geno.md, v5.4) points both states at it.
PULL_ROWS = {"marth": 319, "kirby": 347}   # kirby row: not checked against a host table
PULL_CLIP = "e00catchpull"
PULL_MOTIONS = (213, 215)
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


def audit_special_row(row, joint_of, *, sonic_hit_branch=True, allowlist=None):
    """Fail on every source command/argument the hand-written state does not encode."""
    guard = LossGuard(f"{row.get('agent', 'trail')}/{row.get('script', '<unnamed special>')}", allowlist)
    script = row.get("script", "")
    for c in row["commands"]:
        cmd, frame, args = c["cmd"], c["frame"], c.get("args", [])
        if c.get("when") and not default_path(c["when"]):
            branch_encoded = (sonic_hit_branch and script in ("game_specials2", "game_specials3")
                              and cmd == "ATTACK" and frame == 3)
            if not branch_encoded:
                guard.omit(frame, "case", "branch:" + cmd,
                           f"{cmd} on unselected condition {c['when']!r}")
                continue
        if cmd in ("frame", "wait"):
            if c.get("unresolved_frame") or len(args) != 1 or not isinstance(args[0], (int, float)):
                raise ValueError(f"{script} frame {frame:g}: {cmd} timing unresolved")
        elif cmd == "ATTACK":
            n = c.get("named")
            if n is None:
                raise ValueError(f"{script} frame {frame:g}: ATTACK arguments unresolved")
            validate_attack(n, guard, frame)
            if n["bone"] not in joint_of:
                raise ValueError(f"{script} frame {frame:g}: ATTACK bone {n['bone']!r} unmapped")
        elif cmd == "AttackModule::set_add_reaction_frame_revised":
            reaction_stun_args(c, f"trail/{script}")
        elif cmd == "AttackModule::set_force_reaction":
            force_reaction_args(c, f"trail/{script}")
        elif cmd == "AttackModule::clear_all":
            if args:
                guard.omit(frame, "case", "AttackModule::clear_all.args", f"clear arguments {args!r}")
        elif cmd == "FT_MOTION_RATE" and script in ("game_specialhi", "game_specialairhi", "game_attacks32"):
            if len(args) != 1 or not isinstance(args[0], (int, float)) or args[0] <= 0:
                raise ValueError(f"{script} frame {frame:g}: FT_MOTION_RATE arguments {args!r} unresolved")
        elif cmd == "KineticModule::add_speed" and script in ("game_specials1", "game_specials2", "game_specials3"):
            if len(args) != 3 or not isinstance(args[0], (int, float)) or args[1:] != [0, 0.0]:
                raise ValueError(f"{script} frame {frame:g}: add_speed vector {args!r} is not converted")
        elif cmd in ("WorkModule::on_flag", "WorkModule::off_flag") and len(args) == 1 and (
                (script in ("game_specials1", "game_specials2", "game_specials3") and args[0] == {"const": "0xe65c"}) or
                (script in ("game_specialhi", "game_specialairhi") and args[0] in ({"const": "0xe610"}, {"const": "0xe600"})) or
                (script in ("game_speciallwstart", "game_specialairlwstart") and args[0] == {"const": "0xe61c"}) or
                (script == "game_attacks32" and args[0] == {"const": "0x720"})):
            pass
        else:
            guard.omit(frame, "command", cmd, f"{cmd} arguments {args!r}")
    return guard.losses


def hit_events(tl, row, t, joint_of, rep, name, carry_motion=None, losses=None, audit=True,
               allowlist=None):
    """A game script's ATTACK / clear_all -> Melee hitboxes on the timeline (game frames)."""
    if audit:
        audited_losses = audit_special_row(row, joint_of, allowlist=allowlist)
        if losses is not None:
            losses.extend(audited_losses)
    events = []
    guard = LossGuard(f"{row.get('agent', 'trail')}/{row.get('script', name)}", allowlist)
    carry_hits = carry_hit_commands(row)
    carry_floors = carry_fkb_floor(row, *carry_motion) if carry_motion else {}
    for c in row["commands"]:
        if not default_path(c.get("when", [])):
            continue
        if c["cmd"] == "ATTACK" and c.get("named"):
            n = c["named"]
            validate_attack(n, guard, c["frame"])
            if n["bone"] not in joint_of:
                raise ValueError(f"{name} frame {c['frame']:g}: ATTACK bone {n['bone']!r} unmapped")
            j = joint_of[n["bone"]]
            samples = attack_spheres(n, j, carry=id(c) in carry_hits,
                                     fkb=carry_floors.get(id(c), n["fkb"]))
            payload = dict(samples[0])
            if len(samples) > 1:
                payload["samples"] = samples
            events.append((c["frame"], "hit", payload))
            rep.append("  %s f%d (game %d): id %d %s %.1f%% angle %d kbg %d fkb %d bkb %d size %.1f" % (
                name, c["frame"], round(t(c["frame"])), n["id"], n["bone"], n["damage"], n["angle"],
                n["kbg"], n["fkb"], n["bkb"], n["size"]))
        elif c["cmd"] == "AttackModule::clear_all":
            events.append((c["frame"], "clear", CLEAR))
        elif c["cmd"] == "AttackModule::set_add_reaction_frame_revised":
            source_id, frames = reaction_stun_args(c, guard.move)
            events.append((c["frame"], "stun", {"id": source_id, "frames": frames}))
        elif c["cmd"] == "AttackModule::set_force_reaction":
            source_id, enabled = force_reaction_args(c, guard.move)
            events.append((c["frame"], "force", {"id": source_id, "enabled": enabled}))
    if needs_hitbox_remap(events):
        details = {}
        events = remap_hitboxes(events, details)
        for drop in details.get("dropped_hitboxes", []):
            rep.append("  %s f%d: hitbox id %d dropped (%s)" %
                       (name, drop["frame"], drop["id"], drop["reason"]))
            guard.remap(drop["frame"], drop)
    if losses is not None:
        losses.extend(guard.losses)
    events = apply_autolink(events)
    for frame, kind, payload in events:
        encoded = payload["words"] if isinstance(payload, dict) else payload
        if kind == "hit" and isinstance(payload, dict):
            encoded = encoded + hit_extras(payload)
        elif kind == "clear":
            encoded = encoded + clear_rehit(encoded)
        # Keep source order among hitbox commands, including an ATTACK followed by clear.
        tl.at(t(frame), encoded, 3)


def sonic_branch_hit_events(tl, row, joint_of, rep, name, losses=None, audit=True):
    """Keep both frame-3 flag branches; LA int 2 = 1 is the powered dash (work flag 0xe648)."""
    if audit:
        audited_losses = audit_special_row(row, joint_of, sonic_hit_branch=True)
        if losses is not None:
            losses.extend(audited_losses)
    branches = {3.0: [], 5.2: []}
    for c in row["commands"]:
        if c["cmd"] != "ATTACK" or c["frame"] != 3 or not c.get("named") or not c.get("when"):
            continue
        n = c["named"]
        if n["damage"] not in branches or n["id"] not in (0, 1, 2):
            raise ValueError("unexpected Sonic Blade follow-up branch: %s" % c)
        if len(c["when"]) != 1 or c["when"][0]["holds"] != (n["damage"] == 3.0):
            raise ValueError("Sonic Blade flag branch no longer matches the dump: %s" % c)
        guard = LossGuard(f"{row.get('agent', 'trail')}/{row.get('script', name)}")
        validate_attack(n, guard, c["frame"])
        if n["bone"] not in joint_of:
            raise ValueError(f"{name} frame {c['frame']:g}: ATTACK bone {n['bone']!r} unmapped")
        samples = attack_spheres(n, joint_of[n["bone"]])
        payload = dict(samples[0])
        if len(samples) > 1:
            payload["samples"] = samples
        branches[n["damage"]].append((n["id"], payload, n))
        if losses is not None:
            losses.extend(guard.losses)
        rep.append("  %s f3: powered=%d id %d %.1f%% angle %d kbg %d bkb %d" % (
            name, n["damage"] == 5.2, n["id"], n["damage"], n["angle"], n["kbg"], n["bkb"]))
    if any(sorted(i for i, _, _ in branch) != [0, 1, 2] for branch in branches.values()):
        raise ValueError("Sonic Blade follow-up must have three hitboxes in each branch")
    geometry = ("bone", "size", "x", "y", "z", "x2", "y2", "z2")
    weak_geometry = {i: tuple(n.get(k) for k in geometry) for i, _, n in branches[3.0]}
    strong_geometry = {i: tuple(n.get(k) for k in geometry) for i, _, n in branches[5.2]}
    if weak_geometry != strong_geometry:
        raise ValueError("Sonic Blade branch geometry differs; position check needs separate branch timelines")
    def branch_words(branch):
        events = [(3, "hit", payload) for _, payload, _ in sorted(branch)]
        details = {}
        if needs_hitbox_remap(events):
            events = remap_hitboxes(events, details)
        events = apply_autolink(events)
        if losses is not None:
            guard = LossGuard(f"{row.get('agent', 'trail')}/{row.get('script', name)}")
            for drop in details.get("dropped_hitboxes", []):
                guard.remap(drop["frame"], drop)
            losses.extend(guard.losses)
        return sum((payload["words"] + hit_extras(payload) if isinstance(payload, dict) else payload
                    for _, _, payload in events), [])
    weak = branch_words(branches[3.0])
    strong = branch_words(branches[5.2])
    # IF skips only when its test fails: not powered -> 3.0%, powered -> 5.2%.
    prev = var(LAI, SONIC_PREV_N)
    tl.at(3, IF(prev, EQ, 0, len(weak)) + weak
          + IF(prev, EQ, 1, len(strong)) + strong, 3)
    nonbranch = dict(row, commands=[c for c in row["commands"] if not (
        c["cmd"] == "ATTACK" and c["frame"] == 3 and c.get("when"))])
    hit_events(tl, nonbranch, lambda f: f, joint_of, rep, name, losses=losses, audit=False)


def build(rows, P, joint_of, host, base, rep, sonic_hit_branch=False, counter_backward=False,
          counter_rebound=False, combo_chain=True, losses=None):
    game = {r["script"]: r for r in rows if r["kind"] == "game" and r["agent"] == "trail"}
    if losses is None:
        losses = []
    if not sonic_hit_branch:
        losses.append({"move": "Sonic Blade", "frame": 3,
                       "what": "connected-hit follow-up branch",
                       "why": "--no-sonic-hit-branch selects a single branch"})
    if not counter_backward:
        losses.append({"move": "Counter Attack", "frame": 0,
                       "what": "backward counter variant",
                       "why": "--no-counter-backward disables the variant"})
    if not combo_chain:
        losses.append({"move": "S3 combo", "frame": 0,
                       "what": "game_attacks32 and game_attacks33 stages",
                       "why": "--no-combo-chain disables the follow-up stages"})
    scripts = [f"game_specials{i}" for i in (1, 2, 3)] + [
        "game_specialhi", "game_specialairhi", "game_speciallwstart",
        "game_specialairlwstart", "game_speciallw", "game_specialairlw"]
    if combo_chain:
        scripts += ["game_attacks32", "game_attacks33"]
    for script in scripts:
        if script not in game:
            raise ValueError(f"special ACMD source missing: {script}")
        losses.extend(audit_special_row(game[script], joint_of,
                                        sonic_hit_branch=sonic_hit_branch))
    sub = HOSTS[host]
    active = (BASE_STATES + (BACK_STATES if counter_backward else [])
              + (REBOUND_STATES if counter_rebound else []) + (COMBO_STATES if combo_chain else [])
              + SIDE_EXTRA_STATES)
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
    decay, power_mul = S["0x15530D2D10"], S["0x1A41A10288"]            # 0.92 per dash, 1.15 powered
    dash_frames = S["attack_frame"]                                     # 12 game frames a dash
    aim_arg = (int(S["0x0DEB5675E2"]) & 0xFF) | ((int(S["attack_up_angle_min"]) & 0xFF) << 8) | (
        (int(S["attack_up_angle_max"]) & 0xFF) << 16)                   # keep facing within 20 deg of vertical; up = 40..140
    search_arg = (int(round(S["search_stick"] * 100)) & 0xFF) | ((LOCK_RANGE & 0xFFFF) << 8)
    deferred = []

    def kinetics(brake, grav=0.0, clamp=0.0, x_only=False):
        """phys "brake"'s numbers (per game frame, whatever the clip's rate)."""
        return (PUTF(V_MOVE_F5, brake) + PUTF(V_MOVE_F6, grav) + PUTF(V_MOVE_F7, clamp)
                + PUTI(V_MOVE_I4, 1 if x_only else 0))

    to_end = lambda: IFV(V_AIR, EQ, 1, 2) + CHG(GENO(idx["SEndAir"])) + CHG(GENO(idx["SEnd"]))

    # The start status lives in the main executable, not the status script (spec 13): the clip's 15
    # frames at rate 1 and the start multipliers are what we have. It never aims: dash 1 is straight.
    n_start, _ = clip_info(CLIPS["SStart"])
    tl = Timeline()
    tl.at(0, SET(var(LAI, DASH_N), 0) + SET(var(LAI, SONIC_POWER_N), 0) + SET(var(LAI, LATCH_N), 0)
          + PUTI(V_MOVE_I0, 0) + PUTI(V_MOVE_I2, 0)
          + GET(var(RAF, 0), V_GROUND_VEL) + MULF(var(RAF, 0), S["start_speed_x_mul_ground"]) + PUTV(V_GROUND_VEL, var(RAF, 0))
          + GET(var(RAF, 0), V_VEL_X) + MULF(var(RAF, 0), S["start_speed_x_mul_air"]) + PUTV(V_VEL_X, var(RAF, 0))
          + GET(var(RAF, 1), V_VEL_Y) + MULF(var(RAF, 1), S["start_speed_y_mul_air"]) + PUTV(V_VEL_Y, var(RAF, 1)))
    state("SStart", "geno.air", tl.words(n_start, CHG(GENO(idx["SDash1"]))), phys="auto", coll="both")
    rep.append("SStart: %d frames (d01specialsstart), speed x%.1f ground / x%.1f air, vy x%.1f; no aim: dash 1 is straight" % (
        n_start, S["start_speed_x_mul_ground"], S["start_speed_x_mul_air"], S["start_speed_y_mul_air"]))

    # TURN, level clip (the state keeps its old name and number). The SEARCH brake carries on.
    n_turn, _ = clip_info(CLIPS["SStart2"])
    turn_tail = IF(var(LAI, DASH_N), EQ, 1, 2) + CHG(GENO(idx["SDash2"])) + CHG(GENO(idx["SDash3"]))
    state("SStart2", "geno.air", Timeline().words(n_turn, turn_tail), phys="brake", coll="both")
    for name in ("STurnUp", "STurnDown"):
        frames, _ = clip_info(CLIPS[name])
        deferred.append((name, "geno.air", Timeline().words(frames, turn_tail), dict(phys="brake", coll="both")))
    rep.append("TURN: %d frames (d01specialsstart2 level / d01specialsup 40-140 deg / d01specialsdown 220-320 deg)" % n_turn)

    for n in (1, 2, 3):
        row = game["game_specials%d" % n]
        clip_frames, _ = clip_info(CLIPS["SDash%d" % n])
        tl = Timeline()
        v = SET(var(LAI, DASH_N), n) + PUTF(V_ANIM_RATE, clip_frames / dash_frames)   # the clip in attack_frame game frames
        if n == 1:
            # count 0: straight along the facing, never aimed, never powered here (spec 3.1)
            v += (SETF(var(RAF, 0), speed) + PUTV(V_FWD_VEL, var(RAF, 0)) + PUTF(V_VEL_Y, 0)
                  + GET(var(RAF, 2), V_FACING) + MULV(var(RAF, 2), var(RAF, 0)) + PUTV(V_GROUND_VEL, var(RAF, 2)))
            dash_speed = speed
        else:
            dash_speed = speed * decay ** (n - 1)
            v += PUTI(V_AIR, 1) + CALL(HOOK_DASH_AIM, aim_arg)             # dashes 2 and 3 always leave the ground
            v += (GET(var(RAF, 0), V_MOVE_F0) + MULF(var(RAF, 0), dash_speed)
                  + GET(var(RAF, 1), V_MOVE_F1) + MULF(var(RAF, 1), dash_speed))
            upblk = MULF(var(RAF, 0), S["attack_up_speed_mul"]) + MULF(var(RAF, 1), S["attack_up_speed_mul"])
            inner = IFV(V_MOVE_I3, EQ, 1, len(upblk)) + upblk
            v += IFV(V_MOVE_I0, EQ, 0, len(inner)) + inner                  # x0.85 aimed 40-140 deg, never with a target
            boost = MULF(var(RAF, 0), power_mul) + MULF(var(RAF, 1), power_mul)
            v += IF(var(LAI, SONIC_POWER_N), EQ, 1, len(boost)) + boost
            v += PUTV(V_VEL_X, var(RAF, 0)) + PUTV(V_VEL_Y, var(RAF, 1))    # world axes: the aim is absolute
        v += SET(var(LAI, LATCH_N), 0)
        tl.at(0, v, 0)
        if n > 1 and sonic_hit_branch:
            sonic_branch_hit_events(tl, row, joint_of, rep, "SDash%d" % n, losses=losses, audit=False)
        else:
            hit_events(tl, row, ident, joint_of, rep, "SDash%d" % n, losses=losses, audit=False)
        for c in row["commands"]:
            if c["cmd"] == "KineticModule::add_speed" and isinstance(c["args"][0], (int, float)):
                dv = float(c["args"][0])
                # BEST-FIT: the script's add_speed(-x, 0, 0) has no facing factor and the engine's frame
                # for it is not in our data; taking it off the dash speed along its own direction is the
                # one reading that slows an aimed dash the same as a level one.
                tl.at(c["frame"], CALL(HOOK_BRAKE, int(round(-dv * 1000)) & 0xFFFF), 4)
                rep.append("  SDash%d f%d: dash speed %+.1f (KineticModule::add_speed)" % (n, c["frame"], dv))
        latch = IFV(V_PRESSED, BIT, BTN_SPECIAL_BIT, 2) + SET(var(LAI, LATCH_N), 1)
        window = sorted(c["frame"] for c in row["commands"] if c["cmd"] in ("WorkModule::on_flag", "WorkModule::off_flag")
                        and c.get("args") == [{"const": "0xe65c"}])
        first, last = (int(window[0]), int(window[-1])) if len(window) == 2 else (3, clip_frames)
        for f in range(first, min(last, clip_frames)):
            tl.at(f, latch, 6)
        tail = []
        if n < int(S["attack_num"]):
            go = CHG(GENO(idx["SSearch"]))
            tail += IFV(V_STICK_LEN, GE, fb(S["search_stick"]), len(go)) + go   # stick alone continues the chain
            tail += IF(var(LAI, LATCH_N), EQ, 1, len(go)) + go                  # so does the special button alone
        tail += to_end()
        state("SDash%d" % n, "geno.air", tl.words(clip_frames, tail), phys="none", coll="both")
        rep.append("SDash%d: %d game frames at %.3f/frame (clip %d at rate %.3f)%s; special latched f%d-%d or stick >= %.2f at the end -> SEARCH" % (
            n, dash_frames, dash_speed, clip_frames, clip_frames / dash_frames,
            "" if n == 1 else ", x%.2f aimed up without a target, x%.2f powered" % (S["attack_up_speed_mul"], power_mul),
            first, last - 1, S["search_stick"]))

    # SEARCH: search_frame game frames. Entry keeps at most search_inherit_speed, then the brake.
    search_frames = int(S["search_frame"])
    tl = Timeline()
    air_k, ground_k = kinetics(S["search_brake_air"]), kinetics(S["search_brake_x"])
    tl.at(0, PUTI(V_MOVE_I0, 0) + PUTI(V_MOVE_I2, 0)
          + CALL(HOOK_BRAKE, (int(round(S["search_inherit_speed"] * 100)) & 0x7FFF) << 16)
          + IFV(V_AIR, EQ, 1, len(air_k)) + air_k + IFV(V_AIR, EQ, 0, len(ground_k)) + ground_k, 0)
    for f in range(search_frames):
        tl.at(f, CALL(HOOK_DASH_SEARCH, search_arg), 3)
    go = var(RAI, 1)
    mark = SET(go, 1)
    power = IFV(V_MOVE_I2, EQ, 0, 2) + SET(var(LAI, SONIC_POWER_N), 1)
    cont = (CALL(HOOK_DASH_AIM, aim_arg)                                   # turn now; the dash re-reads the target
            + IFV(V_MOVE_I3, EQ, 1, 2) + CHG(GENO(idx["STurnUp"]))
            + IFV(V_MOVE_I3, EQ, 2, 2) + CHG(GENO(idx["STurnDown"]))
            + CHG(GENO(idx["SStart2"])))
    tail = (SET(go, 0)
            + IFV(V_MOVE_I0, EQ, 1, len(mark)) + mark                      # a locked target
            + IFV(V_MOVE_I2, EQ, 1, len(mark)) + mark                      # a stick aim
            + IF(var(LAI, LATCH_N), EQ, 1, len(mark)) + mark               # neutral stick, special latched: straight ahead
            + SET(var(LAI, SONIC_POWER_N), 0) + IF(var(LAI, LATCH_N), EQ, 1, len(power)) + power
            + IF(go, EQ, 1, len(cont)) + cont
            + to_end())                                                    # the stick was let go and no button: the chain ends
    deferred.append(("SSearch", "geno.air", tl.words(search_frames, tail), dict(phys="brake", coll="both")))
    rep.append("SEARCH: %d game frames (d01specialssearch); speed capped at %.1f then brake %.2f ground / %.2f air; "
               "target within %d locks (stick ignored), else the last stick sample >= %.2f aims over the full circle" % (
                   search_frames, S["search_inherit_speed"], S["search_brake_x"], S["search_brake_air"], LOCK_RANGE,
                   S["search_stick"]))

    def end_rate(clip_len):
        """The END clip plays in exactly end_frame_1/2/3 game frames after 1/2/3 dashes."""
        words = PUTF(V_ANIM_RATE, clip_len / S["end_frame_3"])
        for k in (1, 2):
            put = PUTF(V_ANIM_RATE, clip_len / S["end_frame_%d" % k])
            words += IF(var(LAI, DASH_N), EQ, k, len(put)) + put
        return words

    n_end, _ = clip_info(CLIPS["SEnd"])
    tl = Timeline()
    tl.at(0, kinetics(S["end_brake_x"]) + end_rate(n_end), 0)
    state("SEnd", "geno.ground", tl.words(n_end, CHG(MS_WAIT)), phys="brake", coll="ground")
    rep.append("SEnd: d01specialsend (%d frames) in %d / %d / %d game frames after 1 / 2 / 3 dashes, ground brake %.2f" % (
        n_end, S["end_frame_1"], S["end_frame_2"], S["end_frame_3"], S["end_brake_x"]))
    n_enda, _ = clip_info(CLIPS["SEndAir"])
    tl = Timeline()
    tl.at(0, kinetics(S["end_brake_x_air"], grav=S["end_accel_y"], clamp=S["end_speed_y"], x_only=True) + end_rate(n_enda), 0)
    state("SEndAir", "geno.air", tl.words(n_enda, CHG(MS_FALLSPECIAL)), phys="brake", coll="air",
          landing_lag=int(S["attack_landing_frame"]))
    rep.append("SEndAir: d01specialairsend (%d frames) in %d / %d / %d game frames, air brake %.2f, gravity %.2f with vy "
               "within +-%.1f, then helpless; landing lag %d" % (
                   n_enda, S["end_frame_1"], S["end_frame_2"], S["end_frame_3"], S["end_brake_x_air"], S["end_accel_y"],
                   S["end_speed_y"], S["attack_landing_frame"]))

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
        hit_events(tl, row, t, joint_of, rep, name,
                   carry_motion=(t, lambda f: v0 - a * (f - g0)), losses=losses, audit=False)
        # Flag 0xe600 (ACMD f48-f70): while it is up the status loop changes to the side special when
        # that transition term passes (fidelity audit U1; status 0x710001cd10 -> change_status(+0xc4)).
        # BEST-FIT guard, the term's own test is in the main executable: special pressed with the stick
        # at least SIDE_CANCEL_STICK to one side, and Sora turns to that side.
        window = sorted(c["frame"] for c in row["commands"] if c["cmd"] in ("WorkModule::on_flag", "WorkModule::off_flag")
                        and c.get("args") == [{"const": "0xe600"}])
        if len(window) == 2:
            first, last = int(round(t(window[0]))), int(round(t(window[1])))
            right = PUTF(V_FACING, 1.0) + CHG(GENO(idx["SStart"]))
            left = PUTF(V_FACING, -1.0) + CHG(GENO(idx["SStart"]))
            sides = (IFV(V_STICK_X, GE, fb(SIDE_CANCEL_STICK), len(right)) + right
                     + IFV(V_STICK_X, LE, fb(-SIDE_CANCEL_STICK), len(left)) + left)
            for f in range(first, min(last, total)):
                tl.at(f, IFV(V_PRESSED, BIT, BTN_SPECIAL_BIT, len(sides)) + sides, 6)
            rep.append("  %s: side special with the stick >= %.1f to a side cancels into Sonic Blade, game f%d-%d (flag 0xe600)" % (
                name, SIDE_CANCEL_STICK, first, last - 1))
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
        hit_events(tl, row, ident, joint_of, rep, name, losses=losses, audit=False)
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
            hit_events(tl, row, lambda f: f, joint_of, rep, name, losses=losses, audit=False)
            cancel = (row.get("motion") or {}).get("cancel_frame")
            if cancel:
                tl.at(cancel, IASA, 7)
            state(name, "geno.anim_motion", tl.words(frames, []), anim="next", iasa="interrupt", ledge="none")
            rep.append("%s: %s on %s (%d clip frames)%s" % (
                name, script, CLIPS[name], frames,
                ", fresh A f%d-%d -> %s" % (first, last, next_name) if next_name else ""))

    for name, behavior, words, options in sorted(deferred, key=lambda d: STATES.index(d[0])):
        state(name, behavior, words, **options)
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
    rows = json.loads(verify_acmd_source(a.acmd))
    P = params()
    rep = []
    losses = []
    magic = None
    magic_manifest = {"rows": [], "articles": []}
    base = 0
    if a.magic:
        import hashlib
        from pathlib import Path
        magic_dir = Path(a.magic).parent
        audit_path, source_path = magic_dir / "conversion_losses.json", magic_dir / "overlay_sources.json"
        if not audit_path.is_file() or not source_path.is_file():
            raise ValueError("magic profile has no ACMD loss report and source map")
        magic_audit = json.loads(audit_path.read_text(encoding="utf-8"))
        magic_manifest = json.loads(source_path.read_text(encoding="utf-8"))
        proof = magic_audit.get("audit", {})
        if (proof.get("source_sha256") != hashlib.sha256(Path(a.acmd).read_bytes()).hexdigest() or
                proof.get("generator_sha256") != hashlib.sha256((Path(HERE) / "trail_magic_geno.py").read_bytes()).hexdigest() or
                proof.get("profile_sha256") != hashlib.sha256(Path(a.magic).read_bytes()).hexdigest() or
                proof.get("manifest_sha256") != hashlib.sha256(source_path.read_bytes()).hexdigest()):
            raise ValueError("magic ACMD audit is stale; regenerate the magic profile")
        losses.extend(magic_audit["losses"])
        magic = json.load(open(a.magic, encoding="utf-8"))["fighters"][0]
        base = len(magic.get("states", []))
    states, overlays, specials, clips = build(rows, P, joints_of_sora(), a.host, base, rep,
        sonic_hit_branch=a.sonic_hit_branch, counter_backward=a.counter_backward,
        counter_rebound=a.counter_rebound, combo_chain=a.combo_chain, losses=losses)
    pull_row = PULL_ROWS[a.host]
    overlays.append({"index": pull_row, "words": hx([0])})     # the host row's own script must not run
    clips[str(pull_row)] = PULL_CLIP
    fighter = {"attach": a.attach, "name": "Sora specials (Geno, host %s)" % a.host,
               "states": states, "specials": specials, "subactions": overlays,
               "motion_anims": [{"motion": m, "subaction": pull_row} for m in PULL_MOTIONS]}
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
    # The magic's cast states sit on common rows of their own; without their clips here the installer's
    # name matcher gives those rows the host's item clips (h12itemscope*).
    clip_doc["subaction_clips"].update(magic_manifest.get("row_clips", {}))
    if a.counter_backward:
        clip_doc["turn_clips"] = {str(HOSTS[a.host]["LwAttackBack"]): "d03speciallwturn",
                                  str(HOSTS[a.host]["LwAttackBackAir"]): "d03specialairlwturn"}
    with open(os.path.join(a.out, "clips.json"), "w", encoding="utf-8") as f:
        json.dump(clip_doc, f, indent=1)
    hit_sources = {"SDash1": "game_specials1", "SDash2": "game_specials2",
                   "SDash3": "game_specials3", "Hi": "game_specialhi",
                   "HiAir": "game_specialairhi", "LwAttack": "game_speciallw",
                   "LwAttackAir": "game_specialairlw", "LwAttackBack": "game_speciallw",
                   "LwAttackBackAir": "game_specialairlw", "S3Combo2": "game_attacks32",
                   "S3Combo3": "game_attacks33"}
    overlay_sources = []
    for state in states:
        name = state["name"]
        if name not in hit_sources:
            continue
        script = hit_sources[name]
        row = next(r for r in rows if r["kind"] == "game" and r["agent"] == "trail" and r["script"] == script)
        overlay_sources.append({"row": state["subaction"], "name": name, "script": script,
                                "clip": CLIPS[name], "file": f"geno/sora_sp_{state['subaction']}.txt",
                                "rates": (sorted([c["frame"], c["args"][0]] for c in row["commands"]
                                                 if c["cmd"] == "FT_MOTION_RATE")
                                          if name in ("Hi", "HiAir") else [])})
    with open(os.path.join(a.out, "overlay_sources.json"), "w", encoding="utf-8") as f:
        json.dump({"version": 1, "rows": magic_manifest.get("rows", []) + overlay_sources,
                   "articles": magic_manifest.get("articles", [])}, f, indent=1)
    import hashlib
    loss_path = os.path.join(a.out, "conversion_losses.json")
    write_losses(loss_path, {"losses": losses})
    loss_doc = json.load(open(loss_path, encoding="utf-8"))
    from pathlib import Path
    loss_doc["audit"] = {"version": 1,
                         "source_sha256": hashlib.sha256(Path(a.acmd).read_bytes()).hexdigest(),
                         "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                         "profile_sha256": hashlib.sha256(Path(a.out, "geno.json").read_bytes()).hexdigest(),
                         "manifest_sha256": hashlib.sha256(Path(a.out, "overlay_sources.json").read_bytes()).hexdigest()}
    with open(loss_path, "w", encoding="utf-8") as f:
        json.dump(loss_doc, f, indent=2)
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
