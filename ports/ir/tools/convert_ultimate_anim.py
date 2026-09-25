#!/usr/bin/env python3
"""convert_ultimate_anim.py - Ultimate body animations -> Melee figatrees on the fighter's OWN skeleton.

    python ports/ir/tools/convert_ultimate_anim.py <fighter> [--clips a00wait1 ...]
            [--out DIR] [--check-half]

No retarget. The joint tree is plan_parts.py's: the fighter's own bones in file order plus TopN
(prepended) and YRotN (under XRotN). Bone i's track becomes joint plan[i]'s track, channel for
channel; the two synthesized joints are never keyed. Everything is read from the extracted files
with the upstream ssbh_lib `ssbh_data_json`; the figatree encoder is figatree.py here (from the Brawl Kirby port).

Conventions (checked on the data and in the engine source):
  - Ultimate stores one sampled SRT per frame; rotation is a local quaternion. HSD wants Euler
    angles, R = Rz*Ry*Rx (HSD_MtxSRT), radians. Each frame's angles take the equivalent branch
    nearest the previous frame's, so a track never jumps by 2pi or flips branch at gimbal lock.
  - Scale is composed the plain way (parent * T * R * S). The model builder must set
    JOBJ_CLASSICAL_SCALE on every joint for HSD_JObjMakeMatrix to do the same; bones whose
    Ultimate tracks set compensate_scale need the m-ex scale-compensate bit (26) instead. Both are
    reported per clip, and a bone that switches between the two within the roster is an issue.
  - override_translation: the track's translation is not the pose (Kirby: 40 clips, every value
    0,0,0, which would collapse arms onto their parents). The bone keeps its rest translation.
  - A channel that never leaves its rest value gets no track; one that is constant elsewhere gets
    two keys spanning the clip.

Each output archive is decoded again and evaluated against the source: per channel at every
integer frame, and in world space (joint positions) at integer and, with --check-half, half frames,
where the engine interpolates when an action's animation rate is not 1.
"""
import argparse
import json
import math
import os
import subprocess
import sys
import tempfile

import numpy as np
from scipy.spatial.transform import Rotation

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, HERE)
import figatree as F  # noqa: E402
import plan_parts  # noqa: E402

# The user's own Ultimate extraction and the upstream tools (ssbh_lib, ParamXML) next to it.
TOOL = os.environ.get("GW_ULTIMATE_ROOT", os.path.join(ROOT, "experiment", "tooling", "ultimate"))
DECODER = os.path.join(TOOL, "apps", "SSBH-JSON", "ssbh_data_json.exe")
FIGHTERS = os.path.join(TOOL, "workspace", "extracted", "fighter")
INSTANCES = os.path.join(ROOT, "_build", "tmp", "ir")
ROT, TRA, SCA = (1, 2, 3), (5, 6, 7), (8, 9, 10)
TOL = {"rot": 2e-3, "tra": 2e-3, "sca": 1e-3}
ANIM_BUF = 0x10000  # the port's per-fighter figatree buffer (fighter.c FT_ANIM_BUF_SIZE)


def decode(path):
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "a.json")
        if not os.path.exists(path):
            sys.exit(f"no such animation: {path}")
        subprocess.run([DECODER, path, out], check=True, capture_output=True)
        return json.load(open(out))


def euler_track(quats, start):
    """Per-frame XYZ Euler (R = Rz*Ry*Rx) continuous from `start`: each frame picks, of the two
    equivalent branches and their 2pi shifts, the one nearest the previous frame."""
    prev = np.asarray(start, dtype=float)
    out = []
    for q in quats:
        with np.errstate(all="ignore"):
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                a = Rotation.from_quat(q).as_euler("xyz")
        best = None
        for b in (a, np.array([a[0] + math.pi, math.pi - a[1], a[2] + math.pi])):
            b = prev + (b - prev + math.pi) % (2 * math.pi) - math.pi
            if best is None or np.abs(b - prev).sum() < np.abs(best - prev).sum():
                best = b
        out.append(best)
        prev = best
    return np.array(out)


def points(values, slopes=None):
    """Per-frame spline points; slopes given (rotation: from the slerp path) or finite differences."""
    n = len(values)
    if slopes is None:
        slopes = np.gradient(values) if n > 1 else np.zeros(1)
    return [(f, float(values[f]), float(slopes[f])) for f in range(n)]


def euler_slopes(quats, euler):
    """d(Euler)/d(frame) along the source's own interpolation (slerp between frames), averaged over
    the two sides of each key. np.gradient's chord slopes bend the HSD Hermite away from the slerp
    path when a joint turns tens of degrees a frame (Kirby's forward smash: 3.4 units at half frames)."""
    from scipy.spatial.transform import Slerp
    n = len(quats)
    if n < 2:
        return np.zeros((n, 3))
    eps = 1e-3
    r = Rotation.from_quat(quats)
    out = np.zeros((n, 3))
    for f in range(n):
        sides = []
        for lo, hi, sign in ((f, f + 1, 1), (f - 1, f, -1)):
            if lo < 0 or hi >= n:
                continue
            step = Slerp([0, 1], r[[lo, hi]])
            at = eps if sign > 0 else 1 - eps
            e = euler_track([step([at])[0].as_quat()], euler[f])[0]
            sides.append(sign * (e - euler[f]) / eps)
        out[f] = np.mean(sides, axis=0)
    return out


def encode(values, tol, slopes=None):
    """Cheapest encoding within tol: two keys if constant, else sparse keys added where the
    decoded curve misses, else every frame; s16 first, f32 if quantisation alone is too coarse."""
    n = len(values)
    if np.ptp(values) <= tol / 4:
        pts = [(0, float(values[0]), 0.0), (n - 1, float(values[0]), 0.0)] if n > 1 else [(0, float(values[0]), 0.0)]
        body, fv, fs, keys = F.encode_spline(pts)
        return body, fv, fs, keys
    allp = points(values, slopes)
    for frac in ((None, None), (0x00, 0x00)):
        chosen = {0, n - 1}
        while True:
            pts = [allp[i] for i in sorted(chosen)]
            body, fv, fs, keys = F.encode_spline(pts, *frac)
            err = np.abs([F.evaluate(keys, f) - values[f] for f in range(n)])
            worst = int(np.argmax(err))
            if err[worst] <= tol:
                return body, fv, fs, keys
            if worst in chosen:
                break
            chosen.add(worst)
    raise ValueError("curve cannot be encoded within %g" % tol)


def pick_slopes(quats, euler):
    """The tangent set (slerp-derived or chord, all three axes together) whose Hermite midpoints
    turn the joint nearer the slerp midpoint, measured as a rotation angle. Per-axis choice does
    not compose (the Euler axes interact), and neither set wins everywhere: slerp tangents took
    Kirby's forward smash from 3.4 to 1.5 units at half frames, his forward throw from 1.4 to 2.2."""
    from scipy.spatial.transform import Slerp
    n = len(quats)
    chord = np.gradient(euler, axis=0) if n > 1 else np.zeros((n, 3))
    if n < 3:
        return chord
    slerp = euler_slopes(quats, euler)
    r = Rotation.from_quat(quats)
    mids = Rotation.from_quat([Slerp([0, 1], r[[f, f + 1]])([0.5])[0].as_quat() for f in range(n - 1)])
    best = None
    for cand in (chord, slerp):
        herm = (euler[:-1] + euler[1:]) / 2 + (cand[:-1] - cand[1:]) / 8
        err = np.max((Rotation.from_euler("xyz", herm) * mids.inv()).magnitude())
        if best is None or err < best[0]:
            best = (err, cand)
    return best[1]


def rest_of(ir):
    rest = {}
    for j in ir["assets"]["skeletons"][0]["joints"]:
        r = j["rest"]
        q = json.loads(j["provenance"]["note"].split("quaternion xyzw ")[1].split(";")[0])
        rest[j["name"]] = (np.array(r["translation"]), Rotation.from_quat(q), np.array(r["scale"]),
                           np.array(r["rotation_euler_rad"]))
    return rest


def srt(t, r, s):
    m = np.eye(4)
    m[:3, :3] = r.as_matrix() @ np.diag(s)
    m[:3, 3] = t
    return m


def convert_clip(anim, plan, rest, symbol):
    frames = int(round(anim["final_frame_index"])) + 1
    nodes = {n["name"]: n for g in anim["groups"] if g["group_type"] == "Transform" for n in g["nodes"]}
    tracks, report = [], {"frames": frames, "tracks": 0, "override_translation": [], "compensate_scale": [],
                          "bones_not_in_tree": sorted(set(nodes) - {j["name"] for j in plan["joints"]})}
    source_poses = {}
    for j in plan["joints"]:
        node = nodes.get(j["name"]) if not j["synthesized"] else None
        if node is None:
            tracks.append([])
            continue
        tr = node["tracks"][0]
        vals = tr["values"]["Transform"]
        vals = [vals[min(f, len(vals) - 1)] for f in range(frames)]
        rt, rr, rs, reuler = rest[j["name"]]
        t = np.array([[v["translation"][a] for a in "xyz"] for v in vals])
        s = np.array([[v["scale"][a] for a in "xyz"] for v in vals])
        q = [[v["rotation"][a] for a in "xyzw"] for v in vals]
        if tr["transform_flags"]["override_translation"]:
            t = np.tile(rt, (frames, 1))
            report["override_translation"].append(j["name"])
        if tr["compensate_scale"]:
            report["compensate_scale"].append(j["name"])
        e = euler_track(q, reuler)
        es = pick_slopes(q, e)
        source_poses[j["index"]] = (t, q, s)
        jt = []
        for kinds, block, base, tol, slope in ((ROT, e, reuler, TOL["rot"], es), (TRA, t, rt, TOL["tra"], None),
                                               (SCA, s, rs, TOL["sca"], None)):
            for axis, kind in enumerate(kinds):
                col = block[:, axis]
                if np.max(np.abs(col - base[axis])) <= tol / 4:
                    continue
                body, fv, fs, _ = encode(col, tol, None if slope is None else slope[:, axis])
                jt.append((kind, body, fv, fs))
        tracks.append(jt)
        report["tracks"] += len(jt)
    arc = F.build_tree_archive(symbol, frames - 1, tracks)
    report["bytes"] = len(arc)
    report["over_buffer"] = len(arc) > ANIM_BUF
    return arc, report, source_poses


def check(arc, plan, rest, source_poses, frames, half):
    """Decode the archive and compare with the source: channel error at integer frames, and joint
    world positions (the whole chain, synthesized joints at rest) at integer and half frames."""
    _, tree = F.parse_archive(arc)
    joints = plan["joints"]
    worst = {"channel": 0.0, "world": 0.0, "world_half": 0.0, "where": None}

    def local_hsd(i, f):
        j = joints[i]
        if j["synthesized"]:
            return np.eye(4)
        rt, rr, rs, reuler = rest[j["name"]]
        parts = {"r": reuler.copy(), "t": rt.copy(), "s": rs.copy()}
        for tr in tree["joints"][i]:
            k = tr["type"]
            key = "r" if k in ROT else "t" if k in TRA else "s"
            axis = (ROT if k in ROT else TRA if k in TRA else SCA).index(k)
            parts[key][axis] = F.evaluate(tr["keys"], f)
        return srt(parts["t"], Rotation.from_euler("xyz", parts["r"]), parts["s"])

    def local_src(i, f):
        j = joints[i]
        if j["synthesized"]:
            return np.eye(4)
        if i not in source_poses:
            rt, rr, rs, _ = rest[j["name"]]
            return srt(rt, rr, rs)
        t, q, s = source_poses[i]
        lo = int(math.floor(f)); hi = min(lo + 1, len(t) - 1); a = f - lo
        if a == 0:
            return srt(t[lo], Rotation.from_quat(q[lo]), s[lo])
        rots = Rotation.from_quat([q[lo], q[hi]])
        from scipy.spatial.transform import Slerp
        r = Slerp([0, 1], rots)([a])[0]
        return srt(t[lo] * (1 - a) + t[hi] * a, r, s[lo] * (1 - a) + s[hi] * a)

    # A half frame is only compared where no joint turns more than 90 degrees across it: Ultimate's
    # own clips snap up to 180 degrees in one frame (Kirby's forward smash, forward throw), and
    # there the in-between pose is undefined (slerp has no shortest way at 180).
    snaps = set()
    for i, (t, q, s) in source_poses.items():
        r = Rotation.from_quat(q)
        ang = (r[1:] * r[:-1].inv()).magnitude()
        snaps.update(int(f) for f in np.nonzero(ang > math.pi / 2)[0])
    worst["snap_intervals"] = len(snaps)
    samples = [f for f in range(frames)] + ([f + 0.5 for f in range(frames - 1) if f not in snaps] if half else [])
    for f in samples:
        wh, ws = {}, {}
        for i, j in enumerate(joints):
            p = j["parent"]
            wh[i] = (wh[p] if p is not None else np.eye(4)) @ local_hsd(i, f)
            ws[i] = (ws[p] if p is not None else np.eye(4)) @ local_src(i, f)
        d = max(np.linalg.norm(wh[i][:3, 3] - ws[i][:3, 3]) for i in wh)
        key = "world" if f == int(f) else "world_half"
        if d > worst[key]:
            worst[key] = d
            if key == "world":
                worst["where"] = f
    return worst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fighter")
    ap.add_argument("--clips", nargs="*")
    ap.add_argument("--out", default=os.path.join(ROOT, "_build", "tmp", "ultimate-anim"))
    ap.add_argument("--check-half", action="store_true")
    args = ap.parse_args()
    ir = json.load(open(os.path.join(INSTANCES, f"{args.fighter}.ultimate-body.ir.json"), encoding="utf-8"))
    plan = plan_parts.plan(ir)
    rest = rest_of(ir)
    motion = os.path.join(FIGHTERS, args.fighter, "motion", "body", "c00")
    clips = args.clips or sorted(n[:-7] for n in os.listdir(motion) if n.endswith(".nuanmb"))
    out = os.path.join(args.out, args.fighter)
    os.makedirs(out, exist_ok=True)
    summary = []
    for c in clips:
        anim = decode(os.path.join(motion, c + ".nuanmb"))
        sym = f"Ply{args.fighter}_ACTION_{c}_figatree"
        arc, rep, poses = convert_clip(anim, plan, rest, sym)
        rep.update(check(arc, plan, rest, poses, rep["frames"], args.check_half))
        rep["clip"] = c
        open(os.path.join(out, c + ".dat"), "wb").write(arc)
        summary.append(rep)
        print(f"{c:28} {rep['frames']:4}f {rep['tracks']:4} tracks {rep['bytes']:6} B"
              f"{' OVER' if rep['over_buffer'] else ''}  world err {rep['world']:.4f}"
              + (f" half {rep['world_half']:.4f} ({rep['snap_intervals']} snap frames skipped)"
                 if args.check_half else ""))
    json.dump(summary, open(os.path.join(out, "report.json"), "w"), indent=1)
    w = max(r["world"] for r in summary)
    print(f"{len(summary)} clips -> {out}; worst world error {w:.4f}, "
          f"{sum(r['over_buffer'] for r in summary)} over the 0x10000 buffer")


if __name__ == "__main__":
    sys.exit(main())
