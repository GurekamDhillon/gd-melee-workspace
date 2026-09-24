"""Brawl Meta Knight's PSA graphic events (character IR) -> Melee subaction-script effect commands.

Per Brawl subaction: the gfx script (and the Beam Sword / Sword Glow events of every script) is run statically - timers,
Set Loop / Execute Loop (infinite loops unrolled up to the clip length) and Goto - into (frame, event). Each event maps to:
  - MK's own effects (ef_metaknight EFLS n): a model (5000 + Melee model index = Brawl BRRES index) or one of the three
    particle effects (6000 + generator), m-ex custom ids resolved against MK's effect bank (EfBmData.dat)
  - Brawl common effects (ef_common EFLS n, both the plain 'Graphic Effect' and 'External Graphic Effect Common'):
    the closest Melee EfCoData effect, or nothing (COMMON below)
  - Sword Glow / Terminate Sword Glow: Melee's sword afterimage on/off (ftcmd 0x31) + MK's sword flare model, re-spawned
    every FLARE_LIFE frames while the glow is on (Melee has no "kill this effect" command)
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
IR_PATH = os.path.abspath(os.path.join(HERE, "..", "..", "ir", "metaknight.brawl.ir.json"))

MDL_BASE, PTCL_BASE = 5000, 6000
FLARE_BRRES = 12                   # EffMetaknightSwordFlare (EFLS 13, the Sword Glow graphic 0x0017000D)
FLARE_LIFE = 4

# ef_metaknight EFLS index -> particle generator (index in EfBmData's ptcl bank); the rest are models (EFLS -> BRRES)
PTCL_EFLS = {21: [0, 3], 22: [1], 23: [2]}          # DrillLush (spiral + sword flame), MantleStart, MantleEnd
PTCL_NAMES = {0: "DrillLushBlue spiral", 3: "DrillLush sword flame", 1: "PtcMetaknightMantleStart", 2: "PtcMetaknightMantleEnd"}
PTCL_OFFSET = {1: (0, 6, 0), 2: (0, 6, 0)}           # the mantle emitters' own Translate (0, 6, 0)

# Brawl ef_common EFLS index -> (Melee common effect id or None, why). Melee ids from the vanilla scripts' own use:
# 1011 = the start-of-move flash (every dodge / smash start), 1021 = ground smoke (floor-aligned), 1022 = run smoke,
# 1023 = dash / dodge smoke, 1024/1025 = turn / brake smoke, 1026 = jump smoke, 1031 = down / bound smoke,
# 1059 = attack dust kick (floor-aligned). Landing smoke is Melee's landing code, not a script command.
COMMON = {
    0: (None, "footstep smoke: Melee's walk rows keep their FootstepFX"),
    7: (None, "landing smoke: Melee's landing code draws it"),
    8: (None, "landing smoke: Melee's landing code draws it"),
    9: (1031, "impact ring -> down smoke"),
    10: (1023, "DashSmoke -> dash smoke"),
    11: (1031, "DownSmoke -> down smoke"),
    13: (1021, "ActionSmokeH -> ground smoke"),
    14: (None, "model effect (cape shadow) - no Melee counterpart"),
    15: (None, "model effect - no Melee counterpart"),
    16: (1011, "SmashFlash -> start flash"),
    17: (1011, "SmashFlashS -> start flash"),
    26: (1022, "RunSmoke -> run smoke"),
    27: (1026, "JumpSmoke -> jump smoke"),
    28: (1025, "TurnSmoke -> turn smoke"),
    31: (None, "CliffCatch: Melee's ledge code draws it"),
    33: (1059, "AttackSmoke -> attack dust kick"),
    36: (None, "model effect (nair spin) - the sword trail carries it"),
    39: (1021, "HorizontalSmokeA -> ground smoke"),
    40: (1021, "HorizontalSmokeB -> ground smoke"),
    41: (1031, "VerticalSmokeA -> down smoke"),
    45: (None, "Piyopiyo: Melee's dizzy state draws its own"),
    46: (None, "Piyo: Melee's dizzy state draws its own"),
    47: (None, "Sleep: Melee's sleep state draws its own"),
    49: (None, "StepJump - footstool, no Melee counterpart"),
    70: (None, "wind swirl model - the drill particles carry it"),
    95: (None, "Screw item effect - Melee's item draws its own"),
    125: (None, "SPFlash (cape flash) - MK's own mantle particles carry it"),
}
LANDING_ROWS_SKIP = ("Landing",)


def load_ir(path=IR_PATH):
    d = json.load(open(path, encoding="utf-8"))
    scripts = {s["id"]: s for s in d["behavior"]["scripts"]}

    def score(x):          # a name can repeat (AttackS3S = the three angles): take the one with MK's own effects
        sid = x["scripts"].get("gfx"); n = 0
        for e in (scripts[sid]["events"] if sid in scripts else []):
            if e["raw"]["opcode"] in GFX_OPS:
                a = (e.get("args") or {}).get("values") or [{}]
                n += 10 if isinstance(a[0], dict) and a[0].get("gfx_file") == "Meta Knight" else 1
        return n
    subs = {}
    for x in d["behavior"]["subactions"]:
        if x["name"] not in subs or score(x) > score(subs[x["name"]]): subs[x["name"]] = x
    return subs, scripts


GFX_OPS = {"0x11001000": "ext", "0x11010A00": "ext_follow", "0x11020A00": "ext_follow", "0x111A1000": "common",
           "0x111B1000": "common", "0x111C1000": "common", "0x11031400": "glow", "0x11050100": "glow_end"}


def flatten(events, frames, limit_frames=None):
    """Static run of a PSA script: [(frame, event)] for gfx/glow events. Infinite loops run until the clip ends."""
    lim = limit_frames if limit_frames is not None else frames
    by_off = {int(e["raw"]["offset"], 16): i for i, e in enumerate(events)}
    out = []; f = 0.0; i = 0; loops = []; steps = 0
    while i < len(events) and steps < 5000 and f < lim:
        steps += 1
        e = events[i]; oc = e["raw"]["opcode"]; name = e["raw"]["engine_name"]
        a = (e.get("args") or {}).get("values") or []
        if name == "Synchronous Timer": f += a[0]; i += 1; continue
        if name == "Asynchronous Timer": f = max(f, a[0]); i += 1; continue
        if name == "Set Loop": loops.append([i + 1, a[0]]); i += 1; continue
        if name == "Execute Loop":
            if loops:
                L = loops[-1]
                if L[1] == -1 or L[1] > 1:
                    if L[1] != -1: L[1] -= 1
                    i = L[0]; continue
                loops.pop()
            i += 1; continue
        if name == "Goto":
            t = int(a[0]["off"], 16) if isinstance(a[0], dict) and "off" in a[0] else None
            if t is not None and t in by_off: i = by_off[t]; continue
            break
        if oc in GFX_OPS or name == "Beam Sword Trail":
            out.append((int(f), e))
        i += 1
    return [(fr, e) for fr, e in out if fr < lim]


def plan_subaction(name, subs, scripts, efls_to_brres, clip_frames=None):
    """Brawl subaction -> [(frame, kind, dict)] Melee-side effect events (not yet encoded)."""
    x = subs.get(name)
    if x is None: return [], ["no Brawl subaction %s" % name]
    frames = int(x["engine"]["brawl.psa"].get("anim_frames") or 0) or (clip_frames or 0)
    lim = clip_frames or frames
    evs = []; notes = []
    for role in ("gfx", "main", "other"):
        sid = x["scripts"].get(role)
        if not sid or sid not in scripts: continue
        for fr, e in flatten(scripts[sid]["events"], frames, lim):
            if role != "gfx" and GFX_OPS.get(e["raw"]["opcode"]) not in ("glow", "glow_end"): continue
            evs.append((fr, e))
    out = []
    glow_on = None
    for fr, e in sorted(evs, key=lambda t: t[0]):
        kind = GFX_OPS.get(e["raw"]["opcode"]); a = (e.get("args") or {}).get("values") or []
        if kind in ("ext", "ext_follow"):
            g = a[0]; bone = a[1]; off = (a[4], a[3], a[2])            # PSA Z, Y, X -> joint-local x, y, z
            term = bool(a[-1]) if isinstance(a[-1], bool) else True
            if g.get("gfx_file") == "Meta Knight":
                n = g["efls_index"]
                if n in PTCL_EFLS:
                    for gi in PTCL_EFLS[n]:
                        o2 = tuple(a_ + b_ for a_, b_ in zip(off, PTCL_OFFSET.get(gi, (0, 0, 0))))
                        out.append((fr, "ptcl", {"gen": gi, "bone": bone, "off": o2, "destroy": term, "efls": n,
                                                 "label": "MK EFLS %d %s" % (n, PTCL_NAMES[gi])}))
                elif n in efls_to_brres:
                    out.append((fr, "model", {"brres": efls_to_brres[n], "bone": bone, "off": off, "destroy": term, "efls": n,
                                              "follow": kind == "ext_follow", "label": "MK EFLS %d model %d" % (n, efls_to_brres[n])}))
                else:
                    notes.append("f%d MK EFLS %d: not in the bank" % (fr, n))
            elif g.get("gfx_file") == "Common":
                n = g["efls_index"]; mid, why = COMMON.get(n, (None, "unmapped common %d" % n))
                if mid is None: notes.append("f%d common %d skipped: %s" % (fr, n, why)); continue
                rng = (a[11], a[10], a[9]) if len(a) > 11 and not isinstance(a[9], bool) else (0, 0, 0)
                out.append((fr, "common", {"id": mid, "bone": bone, "off": off, "rng": rng, "destroy": False,
                                           "label": "common %d -> %d (%s)" % (n, mid, why)}))
            else:
                notes.append("f%d %s effect skipped (Final Smash / other file)" % (fr, g.get("gfx_file")))
        elif kind == "common":
            n, bone = a[0], a[1]; off = (a[4], a[3], a[2]); rng = (a[11], a[10], a[9])
            if any(name.startswith(p) for p in LANDING_ROWS_SKIP) and n in (7, 8, 11):
                notes.append("f%d common %d skipped: landing row (Melee's landing code)" % (fr, n)); continue
            mid, why = COMMON.get(n, (None, "unmapped common %d" % n))
            if mid is None: notes.append("f%d common %d skipped: %s" % (fr, n, why)); continue
            out.append((fr, "common", {"id": mid, "bone": bone, "off": off, "rng": rng, "destroy": False,
                                       "label": "common %d -> %d (%s)" % (n, mid, why)}))
        elif kind == "glow":
            glow_on = fr
            out.append((fr, "trail", {"on": True, "label": "Sword Glow -> sword trail on (+ flare, bone %d)" % a[12]}))
            out.append((fr, "flare", {"bone": a[12], "label": "Sword Glow flare"}))
        elif kind == "glow_end":
            out.append((fr, "trail", {"on": False, "label": "Terminate Sword Glow -> trail off"}))
            if glow_on is not None:
                f2 = glow_on + FLARE_LIFE
                while f2 < fr:
                    out.append((f2, "flare", {"bone": 40, "label": "Sword Glow flare (re-spawn)"})); f2 += FLARE_LIFE
            glow_on = None
    if glow_on is not None:                     # glow on to the end of the clip (Brawl: until the action ends)
        f2 = glow_on + FLARE_LIFE
        while f2 < lim:
            out.append((f2, "flare", {"bone": 40, "label": "Sword Glow flare (re-spawn)"})); f2 += FLARE_LIFE
    return sorted(out, key=lambda t: t[0]), notes
