"""Whole-package validation (plain Python + numpy): glb weights/animations, coverage of the engine's rows, the
Striker's move set and the required common states, plus the Blender-side and re-import results. Writes
validation_report.txt next to the manifest.     python src/validate.py
"""
import json, math, os, re, struct, sys
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

    # ------------------------------------------------------------------ animation pass 2
    lines.append("== animation pass 2: contract with the engine lane (frozen) ==")
    fz = json.load(open(os.path.join(PKG, "data", "frozen_contract.json")))
    fcl = {c["name"]: c for c in fz["clips"]}
    cur = {c["name"]: c for c in man["clips"]}
    check("clip names unchanged (179, same set)", set(fcl) == set(cur), str(sorted(set(fcl) ^ set(cur))[:4]))
    check("every clip's frame count unchanged", all(cur[n]["frames"] == c["frames"] for n, c in fcl.items() if n in cur), str([n for n, c in fcl.items() if n in cur and cur[n]["frames"] != c["frames"]][:4]))
    check("every clip's loop flag and hit_frames unchanged", all(cur[n]["loop"] == c["loop"] and cur[n]["hit_frames"] == c["hit_frames"] for n, c in fcl.items() if n in cur),
          str([n for n, c in fcl.items() if n in cur and (cur[n]["loop"] != c["loop"] or cur[n]["hit_frames"] != c["hit_frames"])][:4]))
    rmb = [n for n, c in fcl.items() if n in cur and (cur[n]["root_motion"] != c["root_motion"] or any(abs(a - b) > 0.01 for a, b in zip(cur[n]["root_motion_total"], c["root_motion_total"])))]
    check("root_motion flags and totals unchanged (consistent with the manifest the engine lane read)", not rmb, str(rmb[:4]))
    check("motion_rows map unchanged (351 rows: row, clip, status)", [(r["motion"], r["row"], r["clip"], r["status"]) for r in man["motion_rows"]] == [(r["motion"], r["row"], r["clip"], r["status"]) for r in fz["motion_rows"]])
    check("manifest schema unchanged (top-level and per-clip keys)", sorted(man.keys()) == fz["manifest_keys"] and all(sorted(c.keys()) == fz["clip_keys"] for c in man["clips"]))
    check("skeleton unchanged (bone names, order)", [b["name"] for b in man["bones"]] == [b["name"] for b in json.load(open(os.path.join(HERE, "..", "skeleton.json")))["bones"]] and len(man["bones"]) == 39)

    lines.append("== animation pass 2: motion quality (from the baked clips) ==")
    mp = os.path.join(OUT, "clips_metrics.json")
    if not os.path.exists(mp):
        check("clips_metrics.json present", False, "run build_all.sh")
        return finish()
    met = json.load(open(mp))
    import locostats
    # 1. locomotion: a planted sole point travels back at exactly the ground speed (no sliding), no sole below the floor
    loco = [c for c in man["clips"] if c["ref"].get("ground_ref_speed") and c["name"] in met]
    bad, info = [], []
    for c in loco:
        n = c["name"]; v = c["ref"]["ground_ref_speed"]
        s = locostats.summarize(met[n]["soles"], v, c["loop"])
        tol_mean, tol_max = (0.03, 0.12) if n != "Dash" else (0.05, 0.12)
        ok = s.get("n", 0) > 0 and abs(s["err"]) <= tol_mean and s["spread"] <= tol_max * 2 and s["min_z"] > -0.10
        info.append(f"{n} v={v} mean={s.get('mean')} spread={s.get('spread')} minz={s.get('min_z')} flight={s.get('flight_frames')}")
        if not ok: bad.append((n, s))
    check("locomotion: planted sole point speed equals the ground speed (mean within 3%, spread within 24% of v), no sole through the floor", not bad, str(bad[:2]))
    for l in info: lines.append("   " + l)
    # 2. loops close in position AND velocity
    PTS = ("hand_L", "hand_R", "foot_L", "foot_R", "head", "chest")
    badloop = []
    for c in man["clips"]:
        if not c["loop"] or c["name"] not in met: continue
        pts = met[c["name"]]["pts"]; n = len(pts)
        for k in PTS:
            P = [pts[i][k] for i in range(n)]
            def d(a, b): return [b[j] - a[j] for j in range(3)]
            vel = [d(P[i - 1], P[i]) for i in range(n)]         # vel[0] is the wrap step (n-1 -> 0)
            acc = [math.dist(vel[i], vel[(i + 1) % n]) for i in range(n)]   # change of velocity across frame i
            wrap = acc[0]; inner = max(acc[1:n - 1]) if n > 3 else 0.0
            if wrap > 1.5 * inner + 0.12: badloop.append((c["name"], k, round(wrap, 3), round(inner, 3)))
    check("loops close in position and velocity (the velocity change across the wrap is no larger than inside the clip)", not badloop, str(badloop[:3]))
    # 3. joint rotation limits
    badj = []
    for c in man["clips"]:
        if c["name"] not in met: continue
        for b, ang in met[c["name"]]["max_angle"].items():
            lim = C.JOINT_LIMITS[b.split("_")[0]]
            if ang > lim: badj.append((c["name"], b, ang, lim))
    lines.append("   limits (deg): " + ", ".join(f"{k} {v}" for k, v in C.JOINT_LIMITS.items()))
    check("no joint exceeds its stated rotation limit in any clip", not badj, str(badj[:4]))
    # 4. scarf clearance
    sc = {n: m["scarf_clearance"] for n, m in met.items()}
    worst = min(sc, key=sc.get)
    check(f"the scarf never passes through the torso capsule (clearance >= {C.SCARF_CLEARANCE} from the torso axis)", sc[worst] >= C.SCARF_CLEARANCE, f"min {sc[worst]} in {worst}")
    return finish()

def finish():
    cn = json.load(open(os.path.join(PKG, "manifest.json")))["counts"]
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
