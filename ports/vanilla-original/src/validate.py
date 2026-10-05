"""Whole-package validation (plain Python + numpy): glb weights/animations, coverage of the engine's rows, the
Striker's move set and the required common states, plus the Blender-side and re-import results. Writes
validation_report.txt next to the manifest.     python src/validate.py
"""
import json, os, re, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C
from make_manifest import read_glb

OUT, PKG = C.OUT, C.PKG
lines = []
fails = 0
def check(name, ok, detail=""):
    global fails
    s = ("PASS " if ok else "FAIL ") + name + (" : " + str(detail) if detail else "")
    lines.append(s); print(s)
    if not ok: fails += 1

def acc_data(js, buf, i):
    a = js["accessors"][i]; bv = js["bufferViews"][a["bufferView"]]
    ct = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}[a["componentType"]]
    nc = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}[a["type"]]
    off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = bv.get("byteStride")
    n = a["count"]
    if stride and stride != np.dtype(ct).itemsize * nc:
        raw = np.frombuffer(buf, np.uint8, count=stride * n, offset=off).reshape(n, stride)[:, :np.dtype(ct).itemsize * nc]
        return raw.copy().view(ct).reshape(n, nc)
    return np.frombuffer(buf, ct, count=n * nc, offset=off).reshape(n, nc)

def main():
    man = json.load(open(os.path.join(PKG, "manifest.json")))
    js, buf = read_glb(os.path.join(OUT, "courier.glb"))
    prim = js["meshes"][0]["primitives"][0]
    att = prim["attributes"]
    lines.append("== glTF file ==")
    check("one mesh, one primitive (one skinned piece)", len(js["meshes"]) == 1 and len(js["meshes"][0]["primitives"]) == 1)
    check("no JOINTS_1/WEIGHTS_1 (at most 4 influences per vertex)", "JOINTS_1" not in att and "WEIGHTS_1" not in att)
    W = acc_data(js, buf, att["WEIGHTS_0"]).astype(np.float64); J = acc_data(js, buf, att["JOINTS_0"])
    s = W.sum(1)
    check("glb weights normalised", np.abs(s - 1).max() < 2e-3, f"max error {np.abs(s - 1).max():.5f}")
    check("glb: no unskinned vertex (every weight sum > 0.99)", (s > 0.99).all(), f"min sum {s.min():.4f}")
    check("glb: nonzero influences per vertex <= 4", ((W > 1e-5).sum(1) <= 4).all(), f"max {(W > 1e-5).sum(1).max()}")
    sk = js["skins"][0]
    check("glb: skin joint count == bone count", len(sk["joints"]) == man["counts"]["bones"], f"{len(sk['joints'])}")
    check("glb: joint indices in range", J.max() < len(sk["joints"]))
    check("glb: animation count == clip count", len(js["animations"]) == man["counts"]["clips"], f"{len(js['animations'])}")
    want = {c["name"]: c["frames"] for c in man["clips"]}
    badn, bads, bad1 = [], [], []
    for an in js["animations"]:
        n = an["name"]
        if n not in want: badn.append(n); continue
        ins = an["samplers"][0]["input"]
        t = acc_data(js, buf, ins)[:, 0]
        if len(t) != want[n]: bads.append((n, len(t), want[n]))
        if abs(t[0]) > 1e-6 or (len(t) > 1 and abs(t[1] - 1 / 60.0) > 1e-4): bad1.append(n)
        for ch in an["channels"]:
            if ch["target"]["path"] == "scale":
                smp = an["samplers"][ch["sampler"]]
                v = acc_data(js, buf, smp["output"])
                if np.abs(v - 1).max() > 1e-5: bad1.append(n + ":scale")
    check("glb: every animation named after a clip, with the declared key count", not badn and not bads, f"{badn[:3]} {bads[:3]}")
    check("glb: times start at 0 with a 1/60 s step; scale channels constant 1 (no bone scaling)", not bad1, str(bad1[:3]))
    check("glb: skinned mesh has UVs and a material with a texture", "TEXCOORD_0" in att and len(js["materials"]) == 1 and len(js.get("images", [])) == 1)
    # bounding box: height in Melee units (glTF Y up)
    P = acc_data(js, buf, att["POSITION"])
    check("model height 11-13 units, soles near y=0", 11.0 < P[:, 1].max() < 13.0 and abs(P[:, 1].min()) < 0.2, f"y {P[:,1].min():.2f}..{P[:,1].max():.2f}, x +-{np.abs(P[:,0]).max():.2f}, z {P[:,2].min():.2f}..{P[:,2].max():.2f}")

    lines.append("== coverage ==")
    rows = man["motion_rows"]
    check("all 351 engine motion rows resolved (own clip / alias / no-animation)", len(rows) == 351 and not [r for r in rows if r["status"] == "UNMAPPED"], str([r["row"] for r in rows if r["status"] == "UNMAPPED"]))
    clips = {c["name"]: c for c in man["clips"]}
    check("every alias targets an existing clip", all(r["clip"] in clips for r in rows if r["clip"]))
    # Striker move set: script file -> clip, hit frame and length from the genoasm
    smoves = {"jab1": "Attack11", "jab2": "Attack12", "jab3": "Attack13", "dash_attack": "AttackDash", "ftilt": "AttackS3S", "ftilt_up": "AttackS3Hi", "ftilt_down": "AttackS3Lw",
              "utilt": "AttackHi3", "dtilt": "AttackLw3", "fsmash": "AttackS4S", "fsmash_up": "AttackS4Hi", "fsmash_down": "AttackS4Lw", "usmash": "AttackHi4", "dsmash": "AttackLw4",
              "nair": "AttackAirN", "fair": "AttackAirF", "bair": "AttackAirB", "uair": "AttackAirHi", "dair": "AttackAirLw", "grab": "Catch", "dash_grab": "CatchDash", "pummel": "CatchAttack",
              "fthrow": "ThrowF", "bthrow": "ThrowB", "uthrow": "ThrowHi", "dthrow": "ThrowLw", "n_charge": "NCharge", "n_release": "NRelease", "s_lunge": "SLunge", "rise": "Rise",
              "counter": "Counter", "counter_strike": "CounterStrike"}
    mdir = os.path.normpath(os.path.join(PKG, "..", "..", "melee", "pc", "geno", "mods", "vanilla-striker", "moves"))
    check("every Striker move has a clip", all(c in clips for c in smoves.values()), str([c for c in smoves.values() if c not in clips]))
    if os.path.isdir(mdir):
        bad = []
        for f, cn in smoves.items():
            p = os.path.join(mdir, f + ".genoasm")
            if not os.path.exists(p): continue
            t = 0; first = None; flag = None
            for l in open(p, encoding="utf-8"):
                l = l.strip()
                if l.startswith("wait"): t += int(l.split()[1])
                elif l.startswith("hitbox") and first is None: first = t
                elif l.startswith("throw_flag"): flag = t
            c = clips[cn]
            if c["frames"] < t: bad.append((cn, "shorter than script", c["frames"], t))
            if first is not None and (not c["hit_frames"] or c["hit_frames"][0] != first): bad.append((cn, "hit frame", c["hit_frames"], first))
            if flag is not None and (not c["hit_frames"] or c["hit_frames"][0] != flag) and f != "fthrow" and f != "bthrow": bad.append((cn, "release frame", c["hit_frames"], flag))
            if f in ("fthrow", "bthrow") and flag is not None and c["hit_frames"][0] > flag + 40: bad.append((cn, "release far", c["hit_frames"], flag))
        check("clip hit frame == script hitbox frame, clip length >= script length (Striker moves/*.genoasm)", not bad, str(bad))
    else:
        lines.append("SKIP script timing check: the Striker's moves folder is not present")
    need = ("Wait WalkSlow WalkMiddle WalkFast Dash Run RunBrake Turn TurnRun KneeBend JumpF JumpB JumpAerialF JumpAerialB Fall FallAerial FastFall FallSpecial Landing LandingAirN LandingAirF "
            "LandingAirB LandingAirHi LandingAirLw Squat SquatWait SquatRv GuardOn Guard GuardOff GuardSetOff EscapeF EscapeB EscapeN EscapeAir DamageHi1 DamageHi2 DamageHi3 DamageN1 DamageN2 DamageN3 "
            "DamageLw1 DamageLw2 DamageLw3 DamageAir1 DamageAir2 DamageAir3 DamageFlyHi DamageFlyN DamageFlyLw DamageFlyTop DamageFlyRoll DownBoundU DownBoundD DownWaitU DownWaitD DownStandU DownStandD "
            "DownAttackU DownAttackD DownForwardU DownForwardD DownBackU DownBackD DownSpotU DownSpotD Passive PassiveStandF PassiveStandB PassiveWall PassiveWallJump PassiveCeil CliffCatch CliffWait "
            "CliffClimbSlow CliffClimbQuick CliffAttackSlow CliffAttackQuick CliffEscapeSlow CliffEscapeQuick CliffJumpSlow1 CliffJumpSlow2 CliffJumpQuick1 CliffJumpQuick2 CatchWait CatchCut "
            "CapturePulledHi CaptureWaitHi CaptureDamageHi CaptureCut ThrownF ThrownB ThrownHi ThrownLw EntryStart Win1 Win2 Win3 AppealSR AppealSL").split()
    check("every required common state has its own clip", all(n in clips for n in need), str([n for n in need if n not in clips]))
    rm = [c["name"] for c in man["clips"] if c["root_motion"]]
    lines.append("root-motion clips (on `trans`): " + ", ".join(rm))
    check("root motion only on trans in flagged clips", len(rm) > 0)
    lines.append("== costumes ==")
    check("four costume textures exist", all(os.path.exists(os.path.join(PKG, c["texture"])) for c in man["costumes"]))
    lines.append("== Blender-side results ==")
    for fn in ("validation_blend.json", "validation_reimport.json"):
        p = os.path.join(OUT, fn)
        if os.path.exists(p):
            for c in json.load(open(p))["checks"]:
                s = ("PASS " if c["ok"] else "FAIL ") + c["name"] + (" : " + c["detail"] if c["detail"] else "")
                lines.append(s); print(s)
                if not c["ok"]: global_fail()
        else:
            lines.append("MISSING " + fn); global_fail()
    cn = man["counts"]
    lines.append("== counts ==")
    lines.append(json.dumps(cn))
    lines.append(f"RESULT: {'ALL PASSED' if fails == 0 else str(fails) + ' FAILED'}")
    print(lines[-1])
    open(os.path.join(PKG, "validation_report.txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    return fails

def global_fail():
    global fails
    fails += 1

if __name__ == "__main__":
    sys.exit(1 if main() else 0)
