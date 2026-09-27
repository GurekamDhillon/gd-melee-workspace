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
    generate frame / length, fire and ice spawn offsets.
  - The cast scripts' frames, converted to GAME frames through their FT_MOTION_RATE segments (a rate r
    makes each animation frame last r game frames), because the states play a stand-in clip at rate 1
    until Sora's own clips exist.
  - The cycle: each cast moves the fighter's LA int 0 to the next spell when it generates it; the
    special picks its state by LA int 0 ("specials": {"n": {"select": "la_i:0", ...}}).
INFERRED (not in the scripts or params; say so, tune in game):
  - ice shard lifetime (ICE_LIFE), Thundaga's cloud positions (CLOUD_SPAWNS) and cloud life,
    the bolt's life (length / |speed|), "fall" = grounded cast / "fallair" = aerial cast.
  - Firaga's re-press window (magic_window_frame 10, the specialn12 loop) is not ported: one fireball.
  - 0-damage ATTACKs in the casts (specialn1start f16, specialn2 f22) are not ported.
"""
import argparse
import json
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
ICE_LIFE = 30                       # INFERRED
CLOUD_SPAWNS = [[15, 32], [26, 32], [37, 32]]   # INFERRED: strikes 1-3, [forward, up]
CLOUD_LIFE = 30                     # INFERRED

# stand-in subactions of the host (common ItemScope clips: nothing else plays them in a match)
SUB = {"Firaga": 151, "FiragaAir": 155, "Blizzaga": 150, "BlizzagaAir": 154, "Thundaga": 149,
       "ThundagaAir": 153}

GENO_OP = 59
def w0(sub, ln, low=0):
    return (GENO_OP << 26) | ((sub & 63) << 20) | ((ln & 15) << 16) | (low & 0xFFFF)
SYNC = lambda n: (1 << 26) | int(n)                                  # SyncWait n game frames
CALL_SPAWN = lambda arg: [w0(0x20, 3), 5, arg & 0xFFFFFFFF]          # CALL geno.article.spawn
SET_LA0 = lambda v: [w0(0x01, 2, 0 << 8), v]                         # LA int 0 = v
CHG_WAIT = [w0(0x30, 2, 0x04), 14]                                   # CHG ALWAYS ONCE -> Wait
CLEAR_HITS = [16 << 26]
def spawn_arg(article, variant=0, angle=0):
    return (article & 0xFF) | ((variant & 0xFF) << 8) | ((int(angle) & 0xFFFF) << 16)
def hx(words):
    return ["0x%08X" % (w & 0xFFFFFFFF) for w in words]


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
    def t(f):
        g, cur, last = 0.0, 1.0, 0.0
        for fr, r in rates:
            if fr >= f:
                break
            g += (fr - last) * cur
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


def hitboxes_of(row, scale, report, name, losses=None):
    """A weapon's game script -> article hitbox entries (slot = ATTACK id; each ends where the next
    on its slot starts)."""
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
        for h in hits:
            if h["source_id"] == n["id"] and h["end"] == 0:
                h["end"] = int(c["frame"])
        for i in range(count):
            t = i / (count - 1) if capsule else 0
            xyz = [n[k] + t * (end[j] - n[k]) if capsule else n[k]
                   for j, k in enumerate(("x", "y", "z"))]
            e = {"slot": i, "source_id": n["id"], "damage": round(n["damage"]), "stun": 0,
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
    """The start-script sensor lives until Firaga enters its article cast phase."""
    attacks = [c for c in row["commands"] if c["cmd"] == "ATTACK"]
    if len(attacks) != 1 or attacks[0].get("named") is None:
        raise ValueError(f"{row['script']}: expected one Firaga detector ATTACK")
    n = attacks[0]["named"]
    if n["damage"] != 0 or attack_flags(n) != 7:
        raise ValueError(f"{row['script']}: Firaga detector must have HBFLAGS 7")
    t = game_time(row)
    return [(t(attacks[0]["frame"]), body_attack_words(n, scale)),
            (t(end_frame), CLEAR_HITS + clear_rehit(CLEAR_HITS))]


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
                 for air in (False, True) for suffix in ("1start", "1", "1end", "2", "3")]
    for key in article_keys + cast_keys:
        if key not in game:
            raise ValueError(f"magic ACMD source missing: {key}")
        losses.extend(audit_magic_row(game[key], article=key in article_keys))
    losses.append({"move": "Firaga", "frame": 10,
                   "what": "re-press window permits only one fireball",
                   "why": "Geno cast state currently spawns one article"})
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
            "spawns": [[sn["fire_offset_x"] * S, sn["fire_offset_y"] * S]], "max_live": 8, "hitboxes": fire_hits}
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
    ice = {"lifetime": ICE_LIFE, "velocity": [pi["speed"], 0], "accel": -pi["brake"],
           "min_speed": pi["stable_speed"], "max_live": 8,
           "spawns": [[P["param_special_n_1"]["ice_offset_x"] * S, P["param_special_n_1"]["ice_offset_y"] * S]]}
    # the ice offsets live in param_special_n's second struct (the Blizzaga row)
    A_ICE = art(dict(ice, name="Ice", hitboxes=ice_hits))
    ice_last = hitboxes_of(game[("trail_ice", "0xc00a3e2ad")], S, rep, "ice (last shard)", losses)
    A_ICE_LAST = art(dict(ice, name="IceLast", hitboxes=ice_last))
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
    rep.append("fire: speed %.2f life %d, spawn (%.1f, %.1f)" % (pf["speed"], pf["life"], sn["fire_offset_x"], sn["fire_offset_y"]))
    rep.append("ice: speed %.2f brake %.2f stable %.2f, life %d (INFERRED)" % (pi["speed"], pi["brake"], pi["stable_speed"], ICE_LIFE))
    rep.append("thunder: speed %.2f generate %d length %.0f -> bolt life %d; clouds %s (INFERRED)" % (
        pt["speed"], gen, pt["length"], life_bolt, CLOUD_SPAWNS))

    # ---- casts ----
    states, overlays = [], []
    def cast(name, script, events, total, air):
        """events: [(game_frame, words)] -> SyncWaits between them; the state ends at `total`."""
        words, now = [], 0
        for f, w in sorted(events, key=lambda e: e[0]):
            f = int(round(f))
            if f > now:
                words.append(SYNC(f - now))
                now = f
            words += w
        total = int(round(total))
        if total > now:
            words.append(SYNC(total - now))
        words += CHG_WAIT
        states.append({"name": name, "behavior": "geno.air" if air else "geno.ground", "subaction": SUB[name],
                       "anim": "hold", "phys": "air" if air else "ground"})
        overlays.append({"index": SUB[name], "words": hx(words)})
        rep.append("%s: %s, %d game frames, events at %s" % (name, script, total, [int(round(e[0])) for e in events]))

    for air in (False, True):
        sfx = "Air" if air else ""
        pre = "game_specialairn" if air else "game_specialn"
        # Firaga: start clip (18 frames) -> n1 (fireball at its f0) -> end (IASA at cancel_frame)
        r_start, r_n1, r_end = game[("trail", pre + "1start")], game[("trail", pre + "1")], game[("trail", pre + "1end")]
        t0 = game_time(r_start)(18)
        t1 = game_time(r_n1)(15)
        t2 = game_time(r_end)((r_end["motion"] or {}).get("cancel_frame") or 30)
        ev = firaga_detector_events(r_start, S, 18)
        ev.append((t0, CALL_SPAWN(spawn_arg(A_FIRE)) + SET_LA0(1)))
        cast("Firaga" + sfx, pre + "1start/1/1end", ev, t0 + t1 + t2, air)
        # Blizzaga: 8 shards (the last one the strong script), the body hitbox f40-41
        r2 = game[("trail", pre + "2")]
        t = game_time(r2)
        ev, angle, last, body_active = [], 0, False, False
        for c in r2["commands"]:
            if c["cmd"] == "WorkModule::set_float" and isinstance(c["args"][0], (int, float)):
                angle = c["args"][0]
            elif c["cmd"] == "WorkModule::on_flag" and c["args"] and c["args"][0].get("const") == "0xf400":
                last = True
            elif c["cmd"] == "ArticleModule::generate_article":
                ev.append((t(c["frame"]), CALL_SPAWN(spawn_arg(A_ICE_LAST if last else A_ICE, 0, angle))))
            elif c["cmd"] == "ATTACK":
                n = c["named"]
                guard = LossGuard(f"{r2.get('agent', 'trail')}/{r2['script']}")
                validate_attack(n, guard, c["frame"])
                if n["id"] >= 4:
                    raise ValueError(f"{r2['script']} frame {c['frame']:g}: hitbox id {n['id']} exceeds four slots")
                losses.extend(guard.losses)
                ev.append((t(c["frame"]), body_attack_words(n, S)))
                body_active = True
                rep.append("blizzaga body ATTACK f%d: %.1f%% angle %d kbg %d bkb %d" % (c["frame"], n["damage"], n["angle"], n["kbg"], n["bkb"]))
            elif c["cmd"] == "AttackModule::clear" and body_active:
                ev.append((t(c["frame"]), CLEAR_HITS + clear_rehit(CLEAR_HITS)))
                body_active = False
            elif c["cmd"] == "AttackModule::clear":
                raise ValueError(f"{r2['script']} frame {c['frame']:g}: clear has no live body hitbox")
        ev.append((ev[0][0], SET_LA0(2)))
        cast("Blizzaga" + sfx, pre + "2", ev, t((r2["motion"] or {}).get("cancel_frame") or 63), air)
        # Thundaga: clouds 1-3 (variant = strike index), the third drops the strong bolt
        r3 = game[("trail", pre + "3")]
        t = game_time(r3)
        ev, idx = [], 0
        for c in r3["commands"]:
            if c["cmd"] == "WorkModule::set_int" and isinstance(c["args"][0], int):
                idx = c["args"][0]
            elif c["cmd"] == "ArticleModule::generate_article":
                a_c = (A_CLOUDA3 if idx == 2 else A_CLOUDA) if air else (A_CLOUD3 if idx == 2 else A_CLOUD)
                ev.append((t(c["frame"]), CALL_SPAWN(spawn_arg(a_c, idx))))
        ev.append((ev[0][0], SET_LA0(0)))
        cast("Thundaga" + sfx, pre + "3", ev, t((r3["motion"] or {}).get("cancel_frame") or 70), air)

    doc = {"geno": 4, "fighters": [{
        "attach": a.attach, "name": "Sora magic (Geno v5.1 stand-in on %s)" % a.attach,
        "states": states,
        "specials": {"n": {"select": "la_i:0", "targets": ["geno:Firaga", "geno:Blizzaga", "geno:Thundaga"]},
                     "air_n": {"select": "la_i:0", "targets": ["geno:FiragaAir", "geno:BlizzagaAir", "geno:ThundagaAir"]}},
        "subactions": overlays,
        "articles": arts}]}
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "geno.json"), "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)
    magic_rows = []
    for air in (False, True):
        for name, script in (("FiragaAir" if air else "Firaga",
                              "game_specialairn1start" if air else "game_specialn1start"),
                             ("BlizzagaAir" if air else "Blizzaga",
                              "game_specialairn2" if air else "game_specialn2")):
            row = game[("trail", script)]
            magic_rows.append({"row": SUB[name], "name": name, "script": script,
                               "rates": sorted([c["frame"], c["args"][0]] for c in row["commands"]
                                               if c["cmd"] == "FT_MOTION_RATE"),
                               **({"source_end": 18} if name.startswith("Firaga") else {})})
    article_sources = [
        ("Fire", "trail_fire", "game_fly"), ("Ice", "trail_ice", "game_fly"),
        ("IceLast", "trail_ice", "0xc00a3e2ad"),
        ("Bolt", "trail_thunder", "game_fall"),
        ("BoltLast", "trail_thunder", "0xdbd48edf3"),
        ("BoltAir", "trail_thunder", "game_fallair"),
        ("BoltAirLast", "trail_thunder", "0x10983531cc")]
    manifest = {"version": 1, "rows": magic_rows,
                "articles": [{"name": name, "agent": agent, "script": script, "scale": S}
                             for name, agent, script in article_sources]}
    with open(os.path.join(a.out, "overlay_sources.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)
    with open(os.path.join(a.out, "mod.json"), "w", encoding="utf-8") as f:
        json.dump({"id": os.path.basename(os.path.normpath(a.out)), "name": "Sora magic (Geno stand-in)",
                   "version": "0.1.0", "kind": "misc",
                   "description": "Sora's neutral special (Firaga / Blizzaga / Thundaga) on a stand-in fighter, from trail_magic_geno.py."}, f, indent=1)
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
