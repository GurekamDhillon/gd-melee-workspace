#!/usr/bin/env python3
"""trail_magic_geno.py - Sora's (trail) neutral special, Magic (Firaga -> Blizzaga -> Thundaga), as a
Geno profile: Geno states for the casts, Geno articles for the spells (melee docs/geno.md 19).

    python ports/ir/tools/trail_magic_geno.py [--acmd _build/tmp/ir/trail.acmd.json]
        [--attach PlWf.dat] [--scale 1.0] -o <mods dir>/<mod id>

Reads OUR OWN dump: the acmd rows (acmd_parse.py) and fighter/trail/param/vl.prc, decoded with the
upstream ParamXML + ParamLabels.csv. Writes <out>/geno.json and <out>/mod.json and prints a report of
every number and where it came from. Nothing it writes is committed (derived from the game).

What maps 1:1 (semantic port; Melee's mechanics win):
  - ATTACK on a weapon -> an article hitbox: damage, angle, kbg, fkb (-> Melee's weight-set kb, as
    acmd_to_ftcmd.py), bkb, size, element; the offset scaled by --scale. Re-issued ATTACKs on one id
    are entries of one hitbox slot (the victim list stays). Hitlag / SDI multipliers, shield setoff,
    rumble: dropped (Melee's rules), counted in the report.
  - Weapon params (vl.prc): fire speed / life, ice speed / brake / stable speed, thunder speed /
    generate frame / length, fire and ice spawn offsets, the air hop (hop_add_speed_x / _y).
  - The cast scripts' clip frames. Every cast part is its own Geno state on its own common host row
    (CAST below) and plays Sora's real clip (d00specialn1start / n1 / n1end / n12 / n2 / n3 and the
    air versions): the installer is given the row -> clip map (<out>/clips.json, and overlay_sources.json
    "row_clips" for trail_specials_geno.py's --magic merge). Overlay scripts count CLIP frames, and
    FT_MOTION_RATE r (also the FT_START_ADJUST_MOTION_FRAME[_REVISED] spellings of it) is PUT
    ANIM_RATE 1/r: r is game frames per clip frame (Sora's jab, rate 0.5 over clip frames 1-6 and its
    first hit on frame 8, is a 6-frame jab that way and a 13-frame one the other way).
  - The cycle: LA int 0 moves to the next spell when a cast is ENTERED (the real change_magic runs
    when a cast status is left, whatever the reason: the same thing seen from the next press); the
    special picks its state by LA int 0 ("specials": {"n": {"select": "la_i:0", ...}}).
  - Firaga's chain: FiragaFire polls for a press (stick |x| < 0.6, |y| < 0.5: common.prc
    special_stick_x / _y) during clip frames 0-13 (work flag 0x52e0); at the end of the shot it goes
    to FiragaRepeat (special_n12) and back to FiragaFire, else to FiragaEnd.
  - Air casts hop (hop_add_speed_y up, hop_add_speed_x * facing), once per cast.
  - Projectile life: ice shards are removed at their weapon script's frame 13 (the last shard 15),
    fire at its param life 40; fire and ice vanish on stage contact.
INFERRED / BEST-FIT / UNKNOWN (not in the scripts or params; say so, tune in game):
  - Thundaga's cloud positions (CLOUD_SPAWNS) and cloud life; the bolt's life (length / |speed|);
    "fall" = grounded cast / "fallair" = aerial cast.
  - BEST-FIT: the reduced-hitstun fireball (trail_fire game_fly2) is every fireball after the first of a
    chain; its hitstun bonus 1 / -1 / -3 cannot go below 0 here (stun is 0..255): 1 / 0 / 0.
  - BEST-FIT: the press is the special button held now and not at the start of the shot (the engine
    polls once per clip frame, and a slow-motion clip frame lasts several game frames); the hop is
    read from param_special_n struct 0 for all three spells (the other structs are 0); no chain
    limit (none is visible in the status loop); magic_window_frame (10) is read by no decompiled
    trail function: unused.
  - NOT applied: the start_* / control_* damping params of param_special_n (their wiring is INFERRED
    from the names), KineticModule::change_kinetic, work flags with no Melee consumer.
  - The 0-damage ATTACKs in the casts (specialn1start f16, specialn2 f22) ARE ported (HBFLAGS 7).
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
sys.path.insert(0, HERE)
from acmd_to_ftcmd import (ELEM, hitbox_words, validate_attack, CATCH_SITUATIONS,
                           hit_extras, clear_rehit, attack_spheres, attack_flags,
                           reaction_stun_args)  # noqa: E402
from acmd_loss import LossGuard, write_losses, verify_acmd_source  # noqa: E402

MODEL = {"Fire": "Fire", "Ice": "Ice", "Cloud": "Cloud", "Bolt": "Bolt"}  # trail_magic_models.py
CLOUD_SPAWNS = [[15, 32], [26, 32], [37, 32]]   # INFERRED: strikes 1-3, [forward, up]
CLOUD_LIFE = 30                     # INFERRED
DESPAWN = {"hit": True, "shield": True, "stage": True, "clank": True}   # geno.md 19.2 (the engine default, explicit)

# The casts: (state, host row, Sora clip, game script suffix, air). Common rows (< 341), so the map
# holds for every host: the ItemScope rows and their "Empty" twins, which nothing plays in a match.
CAST = [
    ("Firaga", 149, "d00specialn1start", "1start", False),
    ("FiragaFire", 150, "d00specialn1", "1", False),
    ("FiragaEnd", 151, "d00specialn1end", "1end", False),
    ("FiragaRepeat", 152, "d00specialn12", "12", False),
    ("Blizzaga", 157, "d00specialn2", "2", False),
    ("Thundaga", 158, "d00specialn3", "3", False),
    ("FiragaAir", 153, "d00specialairn1start", "1start", True),
    ("FiragaFireAir", 154, "d00specialairn1", "1", True),
    ("FiragaEndAir", 155, "d00specialairn1end", "1end", True),
    ("FiragaRepeatAir", 156, "d00specialairn12", "12", True),
    ("BlizzagaAir", 161, "d00specialairn2", "2", True),
    ("ThundagaAir", 162, "d00specialairn3", "3", True),
]
CAST_ROW = {c[0]: c[1] for c in CAST}
CAST_CLIP = {c[0]: c[2] for c in CAST}
# clip lengths (fighter/trail/motion/body/c00/d00special*.nuanmb; main() checks them against the files)
CLIP_FRAMES = {"d00specialn1start": 18, "d00specialn1": 15, "d00specialn1end": 30, "d00specialn12": 31,
               "d00specialn2": 63, "d00specialn3": 90, "d00specialairn1start": 18, "d00specialairn1": 15,
               "d00specialairn1end": 30, "d00specialairn12": 31, "d00specialairn2": 63, "d00specialairn3": 90}
# the three-spell names older consumers (trail_fx_bindings.py) know: each spell's first state
SUB = {"Firaga": 149, "FiragaAir": 153, "Blizzaga": 157, "BlizzagaAir": 161, "Thundaga": 158,
       "ThundagaAir": 162}

LA_CYCLE, LA_CHAIN, LA_HOP = 0, 8, 9   # LA int: the cycle (0: the specials generator's contract), shots in a chain, hopped
LAI, RAI, LAF, RAF = 0, 1, 2, 3
V_FACING, V_VEL_X, V_VEL_Y, V_STICK_X, V_STICK_Y, V_HELD, V_ANIM_RATE = 0x01, 0x02, 0x03, 0x08, 0x09, 0x13, 0x1B
EQ, NE, LT, LE, GT, GE, BIT, NOBIT = range(8)
BTN_SPECIAL_BIT = 1                 # Geno button mask bit 1 = SPECIAL (docs/geno.md 15.3)
# common.prc special_stick_x / _y (_build/tmp/trail-fidelity/common-prc.xml lines 195-196): the repeat's stick guard
SPECIAL_STICK_X, SPECIAL_STICK_Y = 0.6, 0.5
REMOVE_EVENT = "0x199c462b5d"       # notify_event_msc_cmd: the weapon removes itself
RATE_CMDS = ("FT_MOTION_RATE", "FT_START_ADJUST_MOTION_FRAME_REVISED_arg1", "FT_START_ADJUST_MOTION_FRAME_arg1")

GENO_OP = 59
def w0(sub, ln, low=0):
    return (GENO_OP << 26) | ((sub & 63) << 20) | ((ln & 15) << 16) | (low & 0xFFFF)
def fb(x):
    return struct.unpack(">I", struct.pack(">f", float(x)))[0]
def var(bank, i):
    return (bank << 6) | i
SYNC = lambda n: (1 << 26) | int(n)                                  # SyncWait n clip frames
CALL_SPAWN = lambda arg: [w0(0x20, 3), 5, arg & 0xFFFFFFFF]          # CALL geno.article.spawn
SET_LA0 = lambda v: [w0(0x01, 2, LA_CYCLE << 8), v]                  # LA int 0 = v
CHG_WAIT = [w0(0x30, 2, 0x04), 14]                                   # CHG ALWAYS ONCE -> Wait
CLEAR_HITS = [16 << 26]
IASA = [23 << 26]
def SET(v, imm): return [w0(0x01, 2, v << 8), imm & 0xFFFFFFFF]
def ADDF(v, x): return [w0(0x02, 2, v << 8), fb(x)]
def ADDV(v, b): return [w0(0x02, 2, (v << 8) | 0x80), b]
def MULF(v, x): return [w0(0x04, 2, v << 8), fb(x)]
def GET(v, val): return [w0(0x08, 2, v << 8), val]
def PUTF(val, x): return [w0(0x09, 3), val, fb(x)]
def PUTV(val, v): return [w0(0x09, 3, 0x80), val, v]
def IF(v, cmp, b, skip): return [w0(0x10, 3, (v << 8) | (cmp << 4)), b & 0xFFFFFFFF, skip]
def IFV(val, cmp, b, skip): return [w0(0x12, 4, cmp << 4), val, b & 0xFFFFFFFF, skip]
def CHG(target): return [w0(0x30, 2, 0x04), target]                  # ALWAYS ONCE
def GENO(n): return (2 << 28) | n
SET_LOOP = lambda n: (3 << 26) | int(n)
EXEC_LOOP = 4 << 26
def spawn_arg(article, variant=0, angle=0):
    return (article & 0xFF) | ((variant & 0xFF) << 8) | ((int(angle) & 0xFFFF) << 16)
def hx(words):
    return ["0x%08X" % (w & 0xFFFFFFFF) for w in words]


def anim_rate(r):
    """Engine ANIM_RATE (speed) for an Ultimate FT_MOTION_RATE r (game frames per clip frame)."""
    if not isinstance(r, (int, float)) or isinstance(r, bool) or not math.isfinite(r) or r <= 0:
        raise ValueError("baked motion rate must be finite and positive")
    return 1.0 / r


def rate_events(row):
    """[(clip frame, FT_MOTION_RATE r)]: FT_MOTION_RATE and the FT_START_ADJUST_MOTION_FRAME[_REVISED]
    commands that restore it (the air n1end row spells the same 0.5 @ f11 / 1 @ f15 as FT_MOTION_RATE)."""
    out = []
    for c in row["commands"]:
        if c["cmd"] in RATE_CMDS:
            if c.get("when") or len(c.get("args", [])) != 1 or not isinstance(c["args"][0], (int, float)):
                raise ValueError(f"{row.get('script')} frame {c['frame']:g}: {c['cmd']} arguments unresolved")
            anim_rate(c["args"][0])
            out.append((int(c["frame"]), c["args"][0]))
    return sorted(out)


class Timeline:
    """Overlay words in clip frames: events by frame (rates first), SyncWaits between them up to `total`.

    `poll` = (end, words): the words also run once per clip frame in [0, end), after that frame's events. A
    run of polling frames is one counted ftcmd loop (SetLoop n, the poll and a 1-frame wait, ExecLoop): the registry's
    JSON reader holds only 2048 values for the whole file, so an unrolled window would not fit."""
    def __init__(self):
        self.ev = []

    def at(self, f, words, order=5):
        self.ev.append((int(round(f)), order, len(self.ev), list(words)))

    def words(self, total, tail, poll=None):
        by = {}
        for f, _, _, w in sorted(self.ev):
            by.setdefault(f, []).extend(w)
        pend, pwords = poll if poll else (0, [])
        marks = sorted(set(by) | {0})
        out, now = [], 0
        for k, a in enumerate(marks):
            if a > now:
                out.append(SYNC(a - now))
                now = a
            out.extend(by.get(a, []))
            nxt = marks[k + 1] if k + 1 < len(marks) else max(total, a)
            stop = min(nxt, pend)
            run = stop - now
            if run >= 2:                            # the polling frames from this event on: one counted loop
                out.extend([SET_LOOP(run)] + pwords + [SYNC(1), EXEC_LOOP])
                now = stop
            elif run == 1:
                out.extend(pwords + [SYNC(1)])
                now = stop
        if total > now:
            out.append(SYNC(total - now))
        return out + tail + [0]


def params():
    with tempfile.TemporaryDirectory() as t:
        out = os.path.join(t, "vl.xml")
        subprocess.run([PARAMXML, "-d", VL, "-l", LABELS, "-o", out], check=True, capture_output=True)
        root = ET.parse(out).getroot()
    got = {}
    for lst in root.iter("list"):
        name = lst.get("hash")
        sts = lst.findall("struct")
        if name in ("param_special_n", "param_fire", "param_ice", "param_thunder") and sts:
            for i, st in enumerate(sts[:2]):
                got[name + ("" if i == 0 else "_%d" % i)] = {c.get("hash"): float(c.text) for c in st
                                                            if c.text is not None}
    return got


def game_time(row):
    """anim frame -> game frame, through the script's FT_MOTION_RATE segments."""
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


def audit_magic_row(row, *, article=False):
    guard = LossGuard(f"{row.get('agent', 'trail')}/{row.get('script', '<unnamed magic>')}")
    script = row.get("script", "")
    for c in row["commands"]:
        cmd, frame, args = c["cmd"], c["frame"], c.get("args", [])
        if c.get("when"):
            guard.omit(frame, "case", "branch:" + cmd, f"{cmd} conditional path {c['when']!r}")
        if cmd in ("frame", "wait", "FT_MOTION_RATE"):
            if c.get("unresolved_frame") or len(args) != 1 or not isinstance(args[0], (int, float)):
                raise ValueError(f"{script} frame {frame:g}: {cmd} argument unresolved")
        elif cmd in RATE_CMDS and not article:   # converted: a clip-rate change (rate_events)
            if c.get("unresolved_frame") or len(args) != 1 or not isinstance(args[0], (int, float)):
                raise ValueError(f"{script} frame {frame:g}: {cmd} argument unresolved")
        elif cmd == "ATTACK":
            n = c.get("named")
            if n is None:
                raise ValueError(f"{script} frame {frame:g}: ATTACK arguments unresolved")
            validate_attack(n, guard, frame, article=article)
            if article and n["id"] >= 4:
                raise ValueError(f"{script} frame {frame:g}: hitbox id {n['id']} exceeds four article hitbox slots")
        elif cmd == "AttackModule::set_add_reaction_frame_revised":
            reaction_stun_args(c, f"{row.get('agent', 'trail')}/{script}")
        elif article:
            guard.omit(frame, "command", cmd, f"weapon {cmd} arguments {args!r}")
        elif cmd == "ArticleModule::generate_article":
            expect = ({"const": "0xf3ec"} if script.endswith("n1") else
                      {"const": "0xf3f8"} if script.endswith("n2") else
                      {"const": "0x52fc"} if script.endswith("n3") else None)
            if args != [expect]:
                raise ValueError(f"{script} frame {frame:g}: article type {args!r} not converted")
        elif cmd == "WorkModule::set_float" and script.endswith("n2"):
            if len(args) != 2 or args[1] != {"const": "0xf3f4"} or not isinstance(args[0], (int, float)):
                raise ValueError(f"{script} frame {frame:g}: ice angle {args!r} not converted")
        elif cmd == "WorkModule::set_int" and script.endswith("n3"):
            if len(args) != 2 or args[1] != {"const": "0x52f4"} or not isinstance(args[0], int):
                raise ValueError(f"{script} frame {frame:g}: thunder strike index {args!r} not converted")
        elif cmd == "WorkModule::on_flag" and script.endswith("n2") and args == [{"const": "0xf400"}]:
            pass  # final shard variant
        elif cmd == "AttackModule::clear" and script.endswith("n2") and args == [0]:
            pass
        else:
            guard.omit(frame, "command", cmd, f"{cmd} arguments {args!r}")
    return guard.losses


def pending_loss(row, c, what, why):
    """A loss the shared acmd_allowlist.json has no entry for yet. Written, never hidden: the entry (an
    exact agent/script move) is the reviewer's to add (see the lane report)."""
    return {"move": f"{row.get('agent', 'trail')}/{row.get('script')}", "frame": c["frame"], "what": what, "why": why,
            "approved_by": None, "pending_review": "needs an exact reviewed acmd_allowlist.json entry for this move"}


def audit_repeat_row(row):
    """game_specialn12 / game_specialairn12: the clip rates are converted (rate_events); the work flag has
    no Melee consumer and, unlike the same flag on the other cast rows, is not yet a reviewed omission."""
    losses = []
    for c in row["commands"]:
        cmd, args = c["cmd"], c.get("args", [])
        if c.get("when"):
            raise ValueError(f"{row['script']} frame {c['frame']:g}: conditional {cmd} is not converted")
        if cmd == "frame":
            continue
        if cmd in RATE_CMDS:
            rate_events({"commands": [c], "script": row["script"]})
        elif cmd == "WorkModule::on_flag" and args == [{"const": "0xf3e8"}]:
            losses.append(pending_loss(row, c, f"{cmd} arguments {args!r}",
                                       "work flag with no Melee analogue; omitted on game_specialn1 / n1end already"))
        else:
            raise ValueError(f"{row['script']} frame {c['frame']:g}: {cmd} {args!r} is not converted")
    return losses


def removal_frame(row):
    """The weapon script frame of its removal event (the shard / fireball vanishes): its lifetime."""
    frames = [c["frame"] for c in row["commands"]
              if c["cmd"] == "UNPARSED_CALL" and len(c.get("args", [])) >= 2 and c["args"][1] == REMOVE_EVENT]
    if len(frames) != 1 or int(frames[0]) != frames[0] or frames[0] <= 0:
        raise ValueError(f"{row.get('script')}: expected one weapon removal event, found {frames!r}")
    return int(frames[0])


def variant_hits(base_row, variant_row, base_hits, name, losses):
    """A weapon's variant script (trail_fire game_fly2) that differs from the audited base only in its
    reaction-stun bonuses: the base's hitboxes with the variant's stun. A bonus below 0 (Ultimate shortens
    hitstun) cannot be written (0..255): clamped to 0, recorded."""
    def rest(r):
        return [(c["frame"], c["cmd"], c.get("args"), c.get("named"), c.get("when")) for c in r["commands"]
                if c["cmd"] != "AttackModule::set_add_reaction_frame_revised"]
    if rest(base_row) != rest(variant_row):
        raise ValueError(f"{variant_row.get('script')} differs from {base_row.get('script')} beyond its reaction stun")
    stun = {}
    for c in variant_row["commands"]:
        if c["cmd"] != "AttackModule::set_add_reaction_frame_revised":
            continue
        a = c.get("args", [])
        if (len(a) != 3 or type(a[0]) is not int or type(a[1]) is not int or not -255 <= a[1] <= 255
                or a[2] is not False):
            raise ValueError(f"{variant_row.get('script')} frame {c['frame']:g}: stun {a!r} cannot be encoded")
        stun[(int(c["frame"]), a[0])] = (a[1], c)
        if a[1] < 0:
            losses.append(pending_loss(variant_row, c, f"set_add_reaction_frame_revised {a!r} is negative",
                                       "hitstun bonus below 0 is not representable (HBSTUN / article stun are 0..255): 0"))
    out = []
    for h in base_hits:
        key = (h["start"] - 1, h["source_id"])
        if key not in stun:
            raise ValueError(f"{variant_row.get('script')}: no reaction stun for {name} hitbox {key}")
        e = json.loads(json.dumps(h))
        e["stun"] = max(0, stun[key][0])
        out.append(e)
    return out


def hitboxes_of(row, scale, report, name, losses=None):
    """A weapon's game script -> article entries with distinct slots for simultaneous source IDs.

    Replacements reuse their ID's slots; capsule samples share the four-slot article budget.
    """
    audited = audit_magic_row(row, article=True)
    if losses is not None:
        losses.extend(audited)
    hits = []
    guard = LossGuard(f"{row.get('agent', 'trail')}/{row.get('script', name)}")
    for c in row["commands"]:
        if c["cmd"] == "AttackModule::set_add_reaction_frame_revised":
            source_id, frames = reaction_stun_args(c, guard.move)
            active = [h for h in hits if h["source_id"] == source_id and h["end"] == 0]
            if not active:
                raise ValueError(f"{guard.move} frame {c['frame']:g}: "
                                 f"reaction stun targets inactive article ATTACK id {source_id}")
            for h in active:
                h["stun"] = frames
            continue
        if c["cmd"] != "ATTACK":
            continue
        if not c.get("named"):
            raise ValueError(f"{name} frame {c['frame']:g}: ATTACK arguments unresolved")
        n = c["named"]
        validate_attack(n, guard, c["frame"], article=True)
        if n["id"] >= 4:
            raise ValueError(f"{name} frame {c['frame']:g}: hitbox id {n['id']} exceeds four article hitbox slots")
        end = [n.get(key) for key in ("x2", "y2", "z2")]
        capsule = all(v is not None for v in end) and end != [n["x"], n["y"], n["z"]]
        length = sum((end[i] - n[k]) ** 2 for i, k in enumerate(("x", "y", "z"))) ** .5 if capsule else 0
        count = min(4, max(2, __import__('math').ceil(length / max(2 * n["size"], .001)) + 1)) if capsule else 1
        if capsule and length > 2 * n["size"] * (count - 1) + 1:
            raise ValueError(f"{guard.move} frame {c['frame']:g}: article capsule cannot fit four spheres")
        flags = CATCH_SITUATIONS[(n.get("ground_air") or {"const": "0x4b54"}).get("const")]
        reflect = n.get("reflectable", True)
        absorb = n.get("absorbable", True)
        if int(n["damage"]) != n["damage"]:
            guard.omit(c["frame"], "case", "article.ATTACK.damage.rounding",
                       f"article ATTACK id {n['id']} damage {n['damage']!r} rounds in Geno item hitbox setup")
        previous = [h for h in hits if h["source_id"] == n["id"] and h["end"] == 0]
        occupied = {h["slot"] for h in hits if h["end"] == 0 and h["source_id"] != n["id"]}
        available = list(dict.fromkeys(h["slot"] for h in previous))
        available += [slot for slot in range(4) if slot not in occupied and slot not in available]
        if count > len(available):
            raise ValueError(f"{guard.move} frame {c['frame']:g}: simultaneous article attacks exceed four hitbox slots")
        for h in previous:
            if h["start"] == int(c["frame"]) + 1:
                # Reissued before this frame can run: no lifetime at all. end=0 would mean
                # forever, leaving old capsule samples active after a frame-zero replacement.
                hits.remove(h)
            else:
                h["end"] = int(c["frame"])
        for i in range(count):
            t = i / (count - 1) if capsule else 0
            xyz = [n[k] + t * (end[j] - n[k]) if capsule else n[k]
                   for j, k in enumerate(("x", "y", "z"))]
            e = {"slot": available[i], "source_id": n["id"], "damage": round(n["damage"]), "stun": 0,
                 "size": round(n["size"] * scale, 3),
                 "offset": [round(xyz[j] * scale, 3) for j in (2, 1, 0)],
                 "angle": n["angle"], "kbg": n["kbg"], "wkb": n["fkb"], "bkb": n["bkb"],
                 "shield_damage": round(n.get("shield_damage") or 0),
                 "element": ELEM.get(n.get("effect"), 0), "start": int(c["frame"]) + 1,
                 "end": 0, "hits": {"ground": flags[0], "air": flags[1],
                                     "reflect": reflect, "absorb": absorb}}
            hits.append(e)
        report.append("%s ATTACK f%d: %.1f%% angle %d kbg %d fkb %d bkb %d size %.1f %s" % (
            name, c["frame"], n["damage"], n["angle"], n["kbg"], n["fkb"], n["bkb"], n["size"], n.get("effect")))
    if guard.losses:
        report.append(f"{name}: {len(guard.losses)} reviewed article losses")
        if losses is not None:
            losses.extend(guard.losses)
    return hits


def body_attack_words(n, scale):
    """Blizzaga's fighter hitbox, including zero-damage detector contact flags."""
    spheres = attack_spheres(n, 0, scale)
    if len(spheres) > 4:
        raise ValueError(f"Blizzaga body ATTACK id {n['id']} capsule exceeds four slots")
    words = []
    for slot, sphere in enumerate(spheres):
        sphere["words"][0] = (sphere["words"][0] & ~(7 << 23)) | (slot << 23)
        sphere["emit_flags"] = True  # the later body hit resets the detector's sticky flags
        words.extend(sphere["words"] + hit_extras(sphere))
    return words


def firaga_detector_events(row, scale, end_frame):
    """The start-script sensor (clip frames) lives until Firaga enters its article cast phase."""
    attacks = [c for c in row["commands"] if c["cmd"] == "ATTACK"]
    if len(attacks) != 1 or attacks[0].get("named") is None:
        raise ValueError(f"{row['script']}: expected one Firaga detector ATTACK")
    n = attacks[0]["named"]
    if n["damage"] != 0 or attack_flags(n) != 7:
        raise ValueError(f"{row['script']}: Firaga detector must have HBFLAGS 7")
    return [(attacks[0]["frame"], body_attack_words(n, scale)),
            (end_frame, CLEAR_HITS + clear_rehit(CLEAR_HITS))]   # clip frames (the states run on the real clip)


def hop_words(sn):
    """The air hop of the casts' loop helper (0x7100010fb0): vy += hop_add_speed_y, vx += hop_add_speed_x * lr."""
    return (GET(var(RAF, 0), V_VEL_Y) + ADDF(var(RAF, 0), sn["hop_add_speed_y"]) + PUTV(V_VEL_Y, var(RAF, 0))
            + GET(var(RAF, 1), V_FACING) + MULF(var(RAF, 1), sn["hop_add_speed_x"])
            + GET(var(RAF, 2), V_VEL_X) + ADDV(var(RAF, 2), var(RAF, 1)) + PUTV(V_VEL_X, var(RAF, 2)))


def press_poll():
    """One poll of the Firaga repeat window: the special button is held now and was not when the shot began
    (RA int 2 = the held mask taken at the window's start), and the stick is inside |x| < 0.6, |y| < 0.5
    (common.prc special_stick_x / _y): RA int 0 = 1 (the real status loop's repeat flag 0x52e4)."""
    conds = [lambda n: IFV(V_HELD, BIT, BTN_SPECIAL_BIT, n),
             lambda n: IF(var(RAI, 2), NOBIT, BTN_SPECIAL_BIT, n),
             lambda n: IFV(V_STICK_X, LT, fb(SPECIAL_STICK_X), n),
             lambda n: IFV(V_STICK_X, GT, fb(-SPECIAL_STICK_X), n),
             lambda n: IFV(V_STICK_Y, LT, fb(SPECIAL_STICK_Y), n),
             lambda n: IFV(V_STICK_Y, GT, fb(-SPECIAL_STICK_Y), n)]
    body = SET(var(RAI, 0), 1)
    for cond in reversed(conds):
        body = cond(len(body)) + body
    return body


def work_flag_frames(row, flag):
    on = [c["frame"] for c in row["commands"] if c["cmd"] == "WorkModule::on_flag" and c.get("args") == [{"const": flag}]]
    off = [c["frame"] for c in row["commands"] if c["cmd"] == "WorkModule::off_flag" and c.get("args") == [{"const": flag}]]
    if len(on) != 1 or len(off) != 1 or on[0] >= off[0]:
        raise ValueError(f"{row.get('script')}: expected one raise and one drop of work flag {flag}")
    return int(on[0]), int(off[0])


def build_casts(game, S, sn, arts, rep, losses):
    """The twelve cast states (CAST) and their overlay scripts, in clip frames. arts: article name -> index."""
    index = {c[0]: i for i, c in enumerate(CAST)}
    states, overlays = [], []
    for name, row_id, clip, suffix, air in CAST:
        total = CLIP_FRAMES[clip]
        src = game[("trail", ("game_specialairn" if air else "game_specialn") + suffix)]
        kind, sfx = (name[:-3], "Air") if air else (name, "")
        tl, tail, poll, use_iasa = Timeline(), CHG_WAIT, None, False
        rates = rate_events(src)
        for f, r in rates:
            tl.at(f, PUTF(V_ANIM_RATE, anim_rate(r)), 1)
        cancel = int((src.get("motion") or {}).get("cancel_frame") or 0)
        events = []
        if kind == "Firaga":                    # n1start: detector f16, then the shot
            tl.at(0, SET_LA0(1) + SET(var(LAI, LA_CHAIN), 0) + (SET(var(LAI, LA_HOP), 0) if air else []), 0)
            for f, w in firaga_detector_events(src, S, total):
                tl.at(f, w)
                events.append(int(f))
            tail = CHG(GENO(index["FiragaFire" + sfx]))
        elif kind == "FiragaFire":              # n1: the fireball at f0, the repeat window while flag 0x52e0 is up
            spawn_f = int(next(c["frame"] for c in src["commands"] if c["cmd"] == "ArticleModule::generate_article"))
            on_f, off_f = work_flag_frames(src, "0x52e0")
            if on_f != 0 or spawn_f != 0:
                raise ValueError("the repeat window / fireball are expected at clip frame 0")
            tl.at(0, SET(var(RAI, 0), 0) + GET(var(RAI, 2), V_HELD), 0)
            one = CALL_SPAWN(spawn_arg(arts["Fire"]))
            two = CALL_SPAWN(spawn_arg(arts["FireRepeat"]))
            tl.at(spawn_f, IF(var(LAI, LA_CHAIN), EQ, 0, len(one)) + one + IF(var(LAI, LA_CHAIN), EQ, 1, len(two)) + two)
            events.append(spawn_f)
            if air:                             # once per cast: the hop helper's first-time-in-the-air test
                block = hop_words(sn) + SET(var(LAI, LA_HOP), 1)
                tl.at(0, IF(var(LAI, LA_HOP), EQ, 0, len(block)) + block, 3)
            poll = (off_f, press_poll())
            tail = (IF(var(RAI, 0), EQ, 1, 2) + CHG(GENO(index["FiragaRepeat" + sfx]))
                    + CHG(GENO(index["FiragaEnd" + sfx])))
        elif kind == "FiragaEnd":               # n1end: cancel_frame 16
            use_iasa = 0 < cancel < total
            if use_iasa:
                tl.at(cancel, IASA, 7)
        elif kind == "FiragaRepeat":            # n12: back to the fireball; the next one is the chained variant
            tl.at(0, SET(var(LAI, LA_CHAIN), 1), 0)
            tail = CHG(GENO(index["FiragaFire" + sfx]))
        elif kind == "Blizzaga":                # 8 shards (the last one the strong script), the body hitbox f40-41
            tl.at(0, SET_LA0(2), 0)
            if air:
                tl.at(0, hop_words(sn), 3)
            angle, last, body_active = 0, False, False
            for c in src["commands"]:
                if c["cmd"] == "WorkModule::set_float" and isinstance(c["args"][0], (int, float)):
                    angle = c["args"][0]
                elif c["cmd"] == "WorkModule::on_flag" and c["args"] and c["args"][0].get("const") == "0xf400":
                    last = True
                elif c["cmd"] == "ArticleModule::generate_article":
                    tl.at(c["frame"], CALL_SPAWN(spawn_arg(arts["IceLast" if last else "Ice"], 0, angle)))
                    events.append(int(c["frame"]))
                elif c["cmd"] == "ATTACK":
                    n = c["named"]
                    guard = LossGuard(f"{src.get('agent', 'trail')}/{src['script']}")
                    validate_attack(n, guard, c["frame"])
                    if n["id"] >= 4:
                        raise ValueError(f"{src['script']} frame {c['frame']:g}: hitbox id {n['id']} exceeds four slots")
                    losses.extend(guard.losses)
                    tl.at(c["frame"], body_attack_words(n, S))
                    events.append(int(c["frame"]))
                    body_active = True
                    rep.append("blizzaga body ATTACK f%d: %.1f%% angle %d kbg %d bkb %d" % (
                        c["frame"], n["damage"], n["angle"], n["kbg"], n["bkb"]))
                elif c["cmd"] == "AttackModule::clear" and body_active:
                    tl.at(c["frame"], CLEAR_HITS + clear_rehit(CLEAR_HITS))
                    body_active = False
                elif c["cmd"] == "AttackModule::clear":
                    raise ValueError(f"{src['script']} frame {c['frame']:g}: clear has no live body hitbox")
            use_iasa = 0 < cancel < total
            if use_iasa:
                tl.at(cancel, IASA, 7)
        elif kind == "Thundaga":                # clouds 1-3 (variant = strike index), the third drops the strong bolt
            tl.at(0, SET_LA0(0), 0)
            if air:
                tl.at(0, hop_words(sn), 3)
            idx = 0
            for c in src["commands"]:
                if c["cmd"] == "WorkModule::set_int" and isinstance(c["args"][0], int):
                    idx = c["args"][0]
                elif c["cmd"] == "ArticleModule::generate_article":
                    a_c = arts[("CloudAirLast" if idx == 2 else "CloudAir") if air else
                               ("CloudLast" if idx == 2 else "Cloud")]
                    tl.at(c["frame"], CALL_SPAWN(spawn_arg(a_c, idx)))
                    events.append(int(c["frame"]))
            use_iasa = 0 < cancel < total
            if use_iasa:
                tl.at(cancel, IASA, 7)
        else:
            raise ValueError(f"unknown cast state {name}")
        state = {"name": name, "behavior": "geno.air" if air else "geno.ground", "subaction": row_id,
                 "anim": "hold", "phys": "air" if air else "ground"}
        if use_iasa:
            state["iasa"] = "interrupt"
        states.append(state)
        overlays.append({"index": row_id, "words": hx(tl.words(total, tail, poll))})
        rep.append("%s: %s on row %d / %s, %d clip frames, rate PUTs %s, events at %s%s%s" % (
            name, src["script"], row_id, clip, total, [(f, round(anim_rate(r), 3)) for f, r in rates], events,
            ", IASA f%d" % cancel if use_iasa else "", ", repeat window f0-%d" % poll[0] if poll else ""))
    return states, overlays


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--acmd", default=os.path.join(ROOT, "_build", "tmp", "ir", "trail.acmd.json"))
    ap.add_argument("--attach", default="PlWf.dat")
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--no-models", action="store_true", help="invisible articles (no trail_magic_models.py files)")
    ap.add_argument("--vfx-effects", help="trail_vfx_melee.py's vfx_effects.json (v2: per-generator frame and joint)")
    ap.add_argument("--vfx", type=int, default=0, help="Firaga carries the slot's generators 6000..6000+N-1 "
                    "(trail_vfx_melee.py --slot) and the FireCore model, instead of the placeholder flame")
    ap.add_argument("--fx", action="store_true", help="bind the Geno effect packages (geno.md 20: fx/<set>/ in the "
                    "mod, from ultimate_vfx_geno.py) to every article variant, aerial and last-hit ones included")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    rows = json.loads(verify_acmd_source(a.acmd))
    game = {(r["agent"], r["script"]): r for r in rows if r["kind"] == "game"}
    losses = []
    article_keys = [("trail_fire", "game_fly"), ("trail_ice", "game_fly"),
                    ("trail_ice", "0xc00a3e2ad"), ("trail_thunder", "game_fall"),
                    ("trail_thunder", "0xdbd48edf3"), ("trail_thunder", "game_fallair"),
                    ("trail_thunder", "0x10983531cc")]
    cast_keys = [("trail", ("game_specialairn" if air else "game_specialn") + suffix)
                 for air in (False, True) for suffix in ("1start", "1", "1end", "12", "2", "3")]
    for key in article_keys + cast_keys + [("trail_fire", "game_fly2")]:
        if key not in game:
            raise ValueError(f"magic ACMD source missing: {key}")
    for key in article_keys + cast_keys:
        losses.extend(audit_repeat_row(game[key]) if key[1].endswith("n12")
                      else audit_magic_row(game[key], article=key in article_keys))
    P = params()
    sn, pf, pi, pt = P["param_special_n"], P["param_fire"], P["param_ice"], P["param_thunder"]
    rep = []
    S = a.scale

    # ---- articles (indices are stable: the cast scripts name them) ----
    arts = []
    def art(d):
        m = MODEL.get(d["name"].replace("Air", "").replace("Last", ""))
        if m and not a.no_models:
            d["model"] = {"file": "GnTrail%s.dat" % m, "symbol": "GnTrail%s_joint" % m}
        if a.fx:
            base = d["name"].replace("Air", "").replace("Last", "")
            pkg = {"Fire": "P_TrailFireBullet", "Ice": "P_TrailIceBullet", "Bolt": "P_TrailThunderBullet",
                   "Cloud": "P_TrailThunderCloud"}.get(base)
            if pkg:
                d["fx"] = pkg
        arts.append(d)
        return len(arts) - 1
    fire_hits = hitboxes_of(game[("trail_fire", "game_fly")], S, rep, "fire", losses)
    fire = {"name": "Fire", "lifetime": int(pf["life"]), "velocity": [pf["speed"], 0],
            "spawns": [[sn["fire_offset_x"] * S, sn["fire_offset_y"] * S]], "max_live": 8,
            "despawn": dict(DESPAWN), "hitboxes": fire_hits}
    if a.vfx_effects:   # route (c): trail_vfx_melee.py's effect list (id, attach frame, emit joint)
        fire["effects"] = json.load(open(a.vfx_effects))
    elif a.vfx:   # route (c) pilot v1: the slot's generators 6000.. at spawn, on the root
        fire["effects"] = list(range(6000, 6000 + a.vfx))
    else:
        fire["effect"] = 1147                 # placeholder: Mario's fireball flame
    A_FIRE = art(fire)
    if (a.vfx or a.vfx_effects) and not a.no_models:
        arts[A_FIRE]["model"] = {"file": "GnTrailFireCore.dat", "symbol": "GnTrailFireCore_joint"}
        sp = os.path.join(a.out, "firecore_spins.json")
        if os.path.exists(sp):
            arts[A_FIRE]["spins"] = json.load(open(sp))
    ice_hits = hitboxes_of(game[("trail_ice", "game_fly")], S, rep, "ice", losses)
    life_ice = removal_frame(game[("trail_ice", "game_fly")])
    life_ice_last = removal_frame(game[("trail_ice", "0xc00a3e2ad")])
    ice = {"lifetime": life_ice, "velocity": [pi["speed"], 0], "accel": -pi["brake"],
           "min_speed": pi["stable_speed"], "max_live": 8, "despawn": dict(DESPAWN),
           "spawns": [[P["param_special_n_1"]["ice_offset_x"] * S, P["param_special_n_1"]["ice_offset_y"] * S]]}
    # the ice offsets live in param_special_n's second struct (the Blizzaga row)
    A_ICE = art(dict(ice, name="Ice", hitboxes=ice_hits))
    ice_last = hitboxes_of(game[("trail_ice", "0xc00a3e2ad")], S, rep, "ice (last shard)", losses)
    A_ICE_LAST = art(dict(ice, name="IceLast", lifetime=life_ice_last, hitboxes=ice_last))
    life_bolt = int(round(pt["length"] / abs(pt["speed"])))
    bolt = {"lifetime": life_bolt, "velocity": [0, pt["speed"]], "max_live": 4,
            "despawn": {"hit": False, "stage": True}}
    A_BOLT = art(dict(bolt, name="Bolt", hitboxes=hitboxes_of(game[("trail_thunder", "game_fall")], S, rep, "bolt (fall)", losses)))
    A_BOLT3 = art(dict(bolt, name="BoltLast", hitboxes=hitboxes_of(game[("trail_thunder", "0xdbd48edf3")], S, rep, "bolt 3 (fall)", losses)))
    A_BOLTA = art(dict(bolt, name="BoltAir", hitboxes=hitboxes_of(game[("trail_thunder", "game_fallair")], S, rep, "bolt (fallair)", losses)))
    A_BOLTA3 = art(dict(bolt, name="BoltAirLast", hitboxes=hitboxes_of(game[("trail_thunder", "0x10983531cc")], S, rep, "bolt 3 (fallair)", losses)))
    gen = int(pt["generate_frame"])
    cloud = {"lifetime": CLOUD_LIFE, "spawns": CLOUD_SPAWNS, "max_live": 3}
    A_CLOUD = art(dict(cloud, name="Cloud", children=[{"article": "Bolt", "frame": gen}]))
    A_CLOUD3 = art(dict(cloud, name="CloudLast", children=[{"article": "BoltLast", "frame": gen}]))
    A_CLOUDA = art(dict(cloud, name="CloudAir", children=[{"article": "BoltAir", "frame": gen}]))
    A_CLOUDA3 = art(dict(cloud, name="CloudAirLast", children=[{"article": "BoltAirLast", "frame": gen}]))
    # the chained fireball (game_fly2): the audited game_fly hitboxes, the variant's hitstun bonuses
    fire2_hits = variant_hits(game[("trail_fire", "game_fly")], game[("trail_fire", "game_fly2")], fire_hits,
                              "fire", losses)
    arts.append(dict(arts[A_FIRE], name="FireRepeat", hitboxes=fire2_hits))   # last: earlier indices stay put
    rep.append("fire: speed %.2f life %d, spawn (%.1f, %.1f); chained shots use FireRepeat (game_fly2, stun %s)" % (
        pf["speed"], pf["life"], sn["fire_offset_x"], sn["fire_offset_y"], [h["stun"] for h in fire2_hits]))
    rep.append("ice: speed %.2f brake %.2f stable %.2f, removed at weapon frame %d (last shard %d)" % (
        pi["speed"], pi["brake"], pi["stable_speed"], life_ice, life_ice_last))
    rep.append("thunder: speed %.2f generate %d length %.0f -> bolt life %d; clouds %s (INFERRED)" % (
        pt["speed"], gen, pt["length"], life_bolt, CLOUD_SPAWNS))
    try:
        import trail_specials_geno as dump
        for clip, n in CLIP_FRAMES.items():
            if dump.clip_info(clip)[0] != n:
                raise ValueError(f"{clip}: the dump has {dump.clip_info(clip)[0]} frames, CLIP_FRAMES says {n}")
    except (ImportError, FileNotFoundError, OSError):
        rep.append("clip lengths not checked against the dump (not on this machine)")

    states, overlays = build_casts(game, S, sn, {x["name"]: i for i, x in enumerate(arts)}, rep, losses)

    doc = {"geno": 4, "fighters": [{
        "attach": a.attach, "name": "Sora magic (Geno v5.1 states on %s)" % a.attach,
        "states": states,
        "specials": {"n": {"select": "la_i:0", "targets": ["geno:Firaga", "geno:Blizzaga", "geno:Thundaga"]},
                     "air_n": {"select": "la_i:0", "targets": ["geno:FiragaAir", "geno:BlizzagaAir", "geno:ThundagaAir"]}},
        "subactions": overlays,
        "articles": arts}]}
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "geno.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)
    row_clips = {str(row): clip for _, row, clip, _, _ in CAST}
    with open(os.path.join(a.out, "clips.json"), "w", encoding="utf-8") as f:
        json.dump({"subaction_clips": row_clips}, f, indent=1)
    magic_rows = []
    for air in (False, True):
        for name, script in (("FiragaAir" if air else "Firaga",
                              "game_specialairn1start" if air else "game_specialn1start"),
                             ("BlizzagaAir" if air else "Blizzaga",
                              "game_specialairn2" if air else "game_specialn2")):
            magic_rows.append({"row": CAST_ROW[name], "name": name, "script": script,
                               "rates": [],   # the overlays count clip frames (the rate is a PUT, not a clock change)
                               **({"source_end": CLIP_FRAMES[CAST_CLIP[name]]} if name.startswith("Firaga") else {})})
    article_sources = [
        ("Fire", "trail_fire", "game_fly"), ("Ice", "trail_ice", "game_fly"),
        ("IceLast", "trail_ice", "0xc00a3e2ad"),
        ("Bolt", "trail_thunder", "game_fall"),
        ("BoltLast", "trail_thunder", "0xdbd48edf3"),
        ("BoltAir", "trail_thunder", "game_fallair"),
        ("BoltAirLast", "trail_thunder", "0x10983531cc"),
        ("FireRepeat", "trail_fire", "game_fly2")]
    manifest = {"version": 1, "rows": magic_rows, "row_clips": row_clips,
                "articles": [{"name": name, "agent": agent, "script": script, "scale": S}
                             for name, agent, script in article_sources]}
    with open(os.path.join(a.out, "overlay_sources.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    with open(os.path.join(a.out, "mod.json"), "w", encoding="utf-8") as f:
        json.dump({"id": os.path.basename(os.path.normpath(a.out)), "name": "Sora magic (Geno)",
                   "version": "0.1.0", "kind": "misc",
                   "description": "Sora's neutral special (Firaga / Blizzaga / Thundaga) on her own clips, from trail_magic_geno.py."}, f, indent=1)
    import hashlib
    from pathlib import Path
    loss_path = Path(a.out, "conversion_losses.json")
    write_losses(loss_path, {"losses": losses})
    loss_doc = json.loads(loss_path.read_text(encoding="utf-8"))
    loss_doc["audit"] = {"version": 1,
                         "source_sha256": hashlib.sha256(Path(a.acmd).read_bytes()).hexdigest(),
                         "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                         "profile_sha256": hashlib.sha256(Path(a.out, "geno.json").read_bytes()).hexdigest(),
                         "manifest_sha256": hashlib.sha256(Path(a.out, "overlay_sources.json").read_bytes()).hexdigest()}
    loss_path.write_text(json.dumps(loss_doc, indent=2) + "\n", encoding="utf-8")
    print("\n".join(rep))
    print("wrote", os.path.join(a.out, "geno.json"), "-", len(states), "states,", len(arts), "articles")


if __name__ == "__main__":
    main()
