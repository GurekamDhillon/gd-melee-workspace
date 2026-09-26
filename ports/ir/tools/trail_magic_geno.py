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
from acmd_to_ftcmd import ELEM, hitbox_words  # noqa: E402

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


def hitboxes_of(row, scale, report, name):
    """A weapon's game script -> article hitbox entries (slot = ATTACK id; each ends where the next
    on its slot starts)."""
    hits = []
    for c in row["commands"]:
        if c["cmd"] != "ATTACK" or not c.get("named"):
            continue
        n = c["named"]
        e = {"slot": n["id"] & 3, "damage": n["damage"], "size": round(n["size"] * scale, 3),
             "offset": [round(n["z"] * scale, 3), round(n["y"] * scale, 3), round(n["x"] * scale, 3)],
             "angle": n["angle"], "kbg": n["kbg"], "wkb": n["fkb"], "bkb": n["bkb"],
             "element": ELEM.get(n.get("effect"), 0), "start": int(c["frame"]) + 1, "end": 0}
        for h in hits:
            if h["slot"] == e["slot"] and h["end"] == 0:
                h["end"] = e["start"] - 1
        hits.append(e)
        report.append("%s ATTACK f%d: %.1f%% angle %d kbg %d fkb %d bkb %d size %.1f %s" % (
            name, c["frame"], n["damage"], n["angle"], n["kbg"], n["fkb"], n["bkb"], n["size"], n.get("effect")))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--acmd", default=os.path.join(ROOT, "_build", "tmp", "ir", "trail.acmd.json"))
    ap.add_argument("--attach", default="PlWf.dat")
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--no-models", action="store_true", help="invisible articles (no trail_magic_models.py files)")
    ap.add_argument("--vfx-effects", help="trail_vfx_melee.py's vfx_effects.json (v2: per-generator frame and joint)")
    ap.add_argument("--vfx", type=int, default=0, help="Firaga carries the slot's generators 6000..6000+N-1 "
                    "(trail_vfx_melee.py --slot) and the FireCore model, instead of the placeholder flame")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args()
    rows = json.load(open(a.acmd, encoding="utf-8"))
    game = {(r["agent"], r["script"]): r for r in rows if r["kind"] == "game"}
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
        arts.append(d)
        return len(arts) - 1
    fire_hits = hitboxes_of(game[("trail_fire", "game_fly")], S, rep, "fire")
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
    ice_hits = hitboxes_of(game[("trail_ice", "game_fly")], S, rep, "ice")
    ice = {"lifetime": ICE_LIFE, "velocity": [pi["speed"], 0], "accel": -pi["brake"],
           "min_speed": pi["stable_speed"], "max_live": 8,
           "spawns": [[P["param_special_n_1"]["ice_offset_x"] * S, P["param_special_n_1"]["ice_offset_y"] * S]]}
    # the ice offsets live in param_special_n's second struct (the Blizzaga row)
    A_ICE = art(dict(ice, name="Ice", hitboxes=ice_hits))
    ice_last = hitboxes_of(game[("trail_ice", "0xc00a3e2ad")], S, rep, "ice (last shard)")
    A_ICE_LAST = art(dict(ice, name="IceLast", hitboxes=ice_last))
    life_bolt = int(round(pt["length"] / abs(pt["speed"])))
    bolt = {"lifetime": life_bolt, "velocity": [0, pt["speed"]], "max_live": 4,
            "despawn": {"hit": False, "stage": True}}
    A_BOLT = art(dict(bolt, name="Bolt", hitboxes=hitboxes_of(game[("trail_thunder", "game_fall")], S, rep, "bolt (fall)")))
    A_BOLT3 = art(dict(bolt, name="BoltLast", hitboxes=hitboxes_of(game[("trail_thunder", "0xdbd48edf3")], S, rep, "bolt 3 (fall)")))
    A_BOLTA = art(dict(bolt, name="BoltAir", hitboxes=hitboxes_of(game[("trail_thunder", "game_fallair")], S, rep, "bolt (fallair)")))
    A_BOLTA3 = art(dict(bolt, name="BoltAirLast", hitboxes=hitboxes_of(game[("trail_thunder", "0x10983531cc")], S, rep, "bolt 3 (fallair)")))
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
        ev = [(t0, CALL_SPAWN(spawn_arg(A_FIRE)) + SET_LA0(1))]
        cast("Firaga" + sfx, pre + "1start/1/1end", ev, t0 + t1 + t2, air)
        # Blizzaga: 8 shards (the last one the strong script), the body hitbox f40-41
        r2 = game[("trail", pre + "2")]
        t = game_time(r2)
        ev, angle, last = [], 0, False
        for c in r2["commands"]:
            if c["cmd"] == "WorkModule::set_float" and isinstance(c["args"][0], (int, float)):
                angle = c["args"][0]
            elif c["cmd"] == "WorkModule::on_flag" and c["args"] and c["args"][0].get("const") == "0xf400":
                last = True
            elif c["cmd"] == "ArticleModule::generate_article":
                ev.append((t(c["frame"]), CALL_SPAWN(spawn_arg(A_ICE_LAST if last else A_ICE, 0, angle))))
            elif c["cmd"] == "ATTACK" and c["named"]["damage"] > 0:
                n = c["named"]
                z = (n["z"] + (n["z2"] if n["z2"] is not None else n["z"])) / 2
                ev.append((t(c["frame"]), hitbox_words(n["id"], 0, n["damage"], n["size"] * S, n["x"] * S,
                                                      n["y"] * S, z * S, n["angle"], n["kbg"], n["fkb"],
                                                      n["bkb"], 0, 0)))
                rep.append("blizzaga body ATTACK f%d: %.1f%% angle %d kbg %d bkb %d" % (c["frame"], n["damage"], n["angle"], n["kbg"], n["bkb"]))
            elif c["cmd"] == "AttackModule::clear" and ev:
                ev.append((t(c["frame"]), CLEAR_HITS))
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
    with open(os.path.join(a.out, "mod.json"), "w", encoding="utf-8") as f:
        json.dump({"id": os.path.basename(os.path.normpath(a.out)), "name": "Sora magic (Geno stand-in)",
                   "version": "0.1.0", "kind": "misc",
                   "description": "Sora's neutral special (Firaga / Blizzaga / Thundaga) on a stand-in fighter, from trail_magic_geno.py."}, f, indent=1)
    print("\n".join(rep))
    print("wrote", os.path.join(a.out, "geno.json"), "-", len(states), "states,", len(arts), "articles")


if __name__ == "__main__":
    main()
