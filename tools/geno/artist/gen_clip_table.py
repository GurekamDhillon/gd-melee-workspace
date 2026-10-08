"""gen_clip_table.py - regenerate data/clip_table.json (maintainers only; the importer reads the JSON, not this).

    python -m tools.geno.artist.gen_clip_table [--art ports/vanilla-original] [--game DIR]

Joins four sources into one table of the engine's 351 motion rows, so an artist never has to author or read the Courier's
manifest: the engine row names (ports/vanilla-original/data/motion_rows.json, names only), the Courier's alias/placeholder
choices (which rows may share which clip), the Courier's clip flags (loop, root motion, walk/run reference speeds) and the
Striker move scripts' timing (first hitbox frame, script length). Tiers and generic fallbacks are decided here.
"""
import argparse, json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))

# Clips a prototype must author. Every other row falls back (see generic_fallback()) and is reported as a placeholder.
PROTOTYPE = ["Wait", "WalkMiddle", "Run", "JumpF", "JumpAerialF", "Fall", "Guard", "Attack11", "Catch", "CatchWait", "ThrowF"]
# Recommended with the prototype: the rows a first play session reaches within seconds.
RECOMMENDED = ["Landing", "Turn", "KneeBend", "GuardOn", "GuardOff", "Squat", "SquatWait", "DamageN1", "DamageFlyN", "EscapeF", "EscapeB", "EscapeN",
               "AttackDash", "AttackS3S", "AttackHi3", "AttackLw3", "AttackAirN", "AttackAirF", "ThrowB", "ThrowHi", "ThrowLw", "CatchAttack", "Dash"]
# Striker move script -> engine row it plays on (rows 295..302 are the eight Special rows).
STRIKER = {"jab1": "Attack11", "jab2": "Attack12", "jab3": "Attack13", "dash_attack": "AttackDash", "ftilt": "AttackS3S", "ftilt_up": "AttackS3Hi",
           "ftilt_down": "AttackS3Lw", "utilt": "AttackHi3", "dtilt": "AttackLw3", "fsmash": "AttackS4S", "fsmash_up": "AttackS4Hi",
           "fsmash_down": "AttackS4Lw", "usmash": "AttackHi4", "dsmash": "AttackLw4", "nair": "AttackAirN", "fair": "AttackAirF", "bair": "AttackAirB",
           "uair": "AttackAirHi", "dair": "AttackAirLw", "grab": "Catch", "dash_grab": "CatchDash", "pummel": "CatchAttack", "fthrow": "ThrowF",
           "bthrow": "ThrowB", "uthrow": "ThrowHi", "dthrow": "ThrowLw", "n_charge": "SpecialN", "n_release": "SpecialAirN", "s_lunge": "SpecialS",
           "rise": "SpecialHi", "counter": "SpecialLw", "counter_strike": "SpecialAirLw"}
# Courier clip names that are not row names but are the clips its special rows play; an artist may use the row names instead.
COURIER_CLIP_ROWS = {"NCharge": "SpecialN", "SLunge": "SpecialS", "Rise": "SpecialHi", "Counter": "SpecialLw"}


def generic_fallback(name):
    """Clip names to try, in order, for a row the artist did not author and the Courier did not alias."""
    chains = [
        (r"^Walk(Slow|Fast)$", ["WalkMiddle"]), (r"^(Dash|RunDirect|RunBrake)$", ["Run"]), (r"^TurnRun$", ["Turn"]),
        (r"^JumpB$", ["JumpF"]), (r"^JumpAerialB$", ["JumpAerialF"]), (r"^Fall(Aerial|Special)?[FB]$", ["Fall"]),
        (r"^FallAerial$", ["Fall"]), (r"^FallSpecial$", ["Fall"]), (r"^Guard(On|Off|SetOff|Reflect)$", ["Guard"]),
        (r"^Catch(Dash|Pull|DashPull)$", ["Catch"]), (r"^CatchAttack$", ["Catch"]), (r"^Throw(B|Hi|Lw)$", ["ThrowF"]),
        (r"^Attack1[23]$", ["Attack11"]), (r"^Attack100", ["Attack11"]), (r"^AttackS3", ["AttackS3S", "Attack11"]),
        (r"^AttackS4", ["AttackS4S", "AttackS3S", "Attack11"]), (r"^Attack(Hi|Lw)[34]$", ["Attack11"]), (r"^AttackDash$", ["Attack11"]),
        (r"^AttackAir", ["AttackAirN", "Attack11"]), (r"^LandingAir", ["Landing"]), (r"^Landing", ["Landing"]),
        (r"^Special", ["Attack11"]),
        (r"^Damage(Hi|N|Lw|Air)[123]$", ["DamageN1"]), (r"^DamageFly", ["DamageFlyN"]), (r"^Squat", ["Squat"]),
        (r"^Capture|^Thrown|^Shoulder", ["CaptureWaitHi"]),
    ]
    for pat, chain in chains:
        if re.match(pat, name):
            return [c for c in chain if c != name]
    return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--art", default=os.path.join(ROOT, "ports", "vanilla-original"))
    ap.add_argument("--game", default=os.environ.get("GW_MELEE") or os.path.join(ROOT, "melee"))
    ap.add_argument("--out", default=os.path.join(HERE, "data", "clip_table.json"))
    a = ap.parse_args()
    man = json.load(open(os.path.join(a.art, "manifest.json"), encoding="utf-8"))
    rows = json.load(open(os.path.join(a.art, "data", "motion_rows.json"), encoding="utf-8"))["rows"]
    clips = {c["name"]: c for c in man["clips"]}
    by_row = {r["row"]: r for r in man["motion_rows"]}
    sdir = os.path.join(a.game, "pc", "geno", "mods", "vanilla-striker", "moves")
    timing = {}
    for f, row in STRIKER.items():
        p = os.path.join(sdir, f + ".genoasm")
        if not os.path.exists(p):
            continue
        t = 0; first = None; flag = None
        for l in open(p, encoding="utf-8"):
            l = l.strip()
            if l.startswith("wait"): t += int(l.split()[1])
            elif l.startswith("hitbox") and first is None: first = t
            elif l.startswith("throw_flag"): flag = t
        timing[row] = {"script": f, "first_hit_frame": first, "release_frame": flag, "script_frames": t}
    src = os.path.join(a.game, "src", "melee", "ft", "kinds", "ftCommon", "forward.h")
    text = open(src, encoding="utf-8", errors="replace").read()
    i = text.index("ftCo_SM_")
    body = text[text.rfind("typedef enum", 0, i):text.index("}", i)]
    sm = [n[len("ftCo_SM_"):] for n, _ in re.findall(r"\b(ftCo_SM_\w+)\s*(=\s*[^,]+)?,", body)][1:]
    out_rows = []
    for r in rows:
        n = r["name"]
        m = by_row[n]
        clip = m.get("clip")
        entry = {"motion": r["motion"], "name": n, "retail_subaction": r["retail_subaction"]}
        if m["status"] == "no-animation":
            entry["tier"] = "none"            # the engine plays no clip for this row
        else:
            if n in PROTOTYPE: entry["tier"] = "prototype"
            elif n in RECOMMENDED: entry["tier"] = "recommended"
            elif n.startswith("Special"): entry["tier"] = "finished"
            elif m["status"] == "own": entry["tier"] = "finished"
            else: entry["tier"] = "optional"
            fb = []
            if m["status"] in ("alias", "placeholder") and clip:
                tgt = COURIER_CLIP_ROWS.get(clip, clip)
                if tgt != n:
                    fb.append(tgt)
            fb += [c for c in generic_fallback(n) if c not in fb]
            entry["fallback"] = fb
            entry["share"] = "safe" if m["status"] == "alias" else ("own" if m["status"] == "own" else "placeholder")
        c = clips.get(clip) if m["status"] == "own" else None
        if c:
            entry["loop"] = bool(c["loop"])
            if c["root_motion"]: entry["root_motion"] = True
            if c.get("ref") and c["ref"].get("ground_ref_speed"): entry["ref_speed_courier"] = c["ref"]["ground_ref_speed"]
        if n in timing: entry["timing"] = timing[n]
        out_rows.append(entry)
    for cn, rn in COURIER_CLIP_ROWS.items():
        for e in out_rows:
            if e["name"] == rn and cn in clips and clips[cn]["loop"]:
                e["loop"] = True
    doc = {"note": "generated by tools/geno/artist/gen_clip_table.py; engine row names, tiers, fallbacks, Striker timing. No disc data.",
           "prototype": PROTOTYPE, "recommended": RECOMMENDED, "rows_sm": sm, "rows": out_rows,
           "walk_run_rows": ["WalkSlow", "WalkMiddle", "WalkFast", "Run", "Dash"]}
    json.dump(doc, open(a.out, "w", encoding="utf-8", newline="\n"), indent=1)
    from collections import Counter
    print(Counter(e["tier"] for e in out_rows), "timing rows", len(timing), "sm", len(sm))


if __name__ == "__main__":
    main()
