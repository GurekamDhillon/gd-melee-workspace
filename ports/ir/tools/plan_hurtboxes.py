#!/usr/bin/env python3
"""plan_hurtboxes.py - a fighter's hurtbox capsules (ftData x30) from its OWN skinned mesh.

    python ports/ir/tools/plan_hurtboxes.py <fighter> [--check a00wait1 a02run ...] [-o out.json]

General, not fighter-specific. The body is cut into the segments Melee's own fighters use for hurtboxes
(head, bust, waist, hip, upper arm, forearm+hand, thigh, shin, foot each side: 14 of the engine's 15),
named by common part (plan_parts.py), so any skeleton with the core roles gets the same layout:

  1. each vertex of the mesh visible at rest (export_ultimate_mesh.py; Visibility groups off in the
     face clip's frame 0 are left out) goes to its heaviest joint, then up the tree to the first
     segment joint. Anything under a Have joint (held items, Sora's keyblade) is left out: a weapon
     is not hurtable in Melee.
  2. per segment, in the segment joint's rest space: axis = principal direction of the vertices,
     ends at the 3rd / 97th percentile along it, radius = COVER percentile of the distances to that
     segment; the ends are pulled in by the radius (a capsule's caps reach past its ends).
  3. height (ftHurtboxInit.height: 0 low, 1 mid, 2 high) by segment, as vanilla fighters set it:
     legs low, torso/hip/upper arms mid, head/forearms high... except that Melee uses it for the
     hit-lag/damage animation choice only (DamageHi/N/Lw), so body thirds by rest centre decide.

--check poses the skinned mesh with clips (upstream decode, helper bones baked as the converter
does) and reports the share of vertices inside some capsule, at rest and per clip, plus how far
the worst uncovered vertex lies outside. Output is data describing disc files: _build/tmp only.
"""
import argparse
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import convert_ultimate_anim as CA  # noqa: E402
import export_ultimate_mesh as EM  # noqa: E402
import plan_parts  # noqa: E402

# segment name -> common part of its joint; order is the x30 order
SEGMENTS = ["HeadN", "BustN", "WaistN", "HipN",
            "LShoulderJ", "LArmJ", "RShoulderJ", "RArmJ",
            "LLegJ", "LKneeJ", "RLegJ", "RKneeJ", "LFootJ", "RFootJ"]
EXCLUDE_UNDER = ["LHaveN", "RHaveN"]
COVER = 92          # radius percentile: hurtboxes hug the body, a few spikes (hair, cloth) stick out


def visible_groups(fighter, clip):
    """Visibility names shown at frame 0 of `clip` over the base layer (a00defaulteyelid)."""
    motion = os.path.join(CA.FIGHTERS, fighter, "motion", "body", "c00")
    vis = {}
    for c in ("a00defaulteyelid", clip):
        p = os.path.join(motion, c + ".nuanmb")
        if not os.path.exists(p):
            continue
        for g in CA.decode(p)["groups"]:
            if g["group_type"] == "Visibility":
                for n in g["nodes"]:
                    v = n["tracks"][0]["values"]; v = next(iter(v.values())) if isinstance(v, dict) else v
                    vis[n["name"]] = bool(v[0])
    return vis


def rest_vertices(mesh, vis):
    """Unique (position, weights) of the DObjs visible at rest. A VIS group with no track counts as
    shown (Ultimate's default)."""
    seen, P, Wt = set(), [], []
    for d in mesh["dobjs"]:
        if d["group"] is not None and not vis.get(d["group"], True):
            continue
        for t in d["tris"]:
            for v in t:
                k = tuple(round(x, 4) for x in v["p"])
                if k in seen:
                    continue
                seen.add(k); P.append(v["p"]); Wt.append(v["w"])
    return np.array(P), Wt


def plan(fighter, face_clip="a00wait1", mesh=None):
    ir = json.load(open(os.path.join(CA.INSTANCES, f"{fighter}.ultimate-body.ir.json"), encoding="utf-8"))
    pl = plan_parts.plan(ir); rest = CA.rest_of(ir); J = pl["joints"]
    W = EM.world_rest(pl, rest)
    mesh = mesh or EM.export(fighter, "c00", max_tex=4)
    P, Wt = rest_vertices(mesh, visible_groups(fighter, face_clip))
    p2j = dict(zip(plan_parts.COMMON, pl["parts"]["part_to_joint"]))
    seg_joint = {s: p2j[s] for s in SEGMENTS if p2j.get(s, 255) != 255}
    missing = [s for s in SEGMENTS if s not in seg_joint]
    joint_seg = {j: s for s, j in seg_joint.items()}
    excl = {p2j[e] for e in EXCLUDE_UNDER if p2j.get(e, 255) != 255}

    def segment_of(j):
        k = j
        while k is not None:
            if k in excl:
                return None
            if k in joint_seg:
                return joint_seg[k]
            k = J[k]["parent"]
        return "HipN" if "HipN" in seg_joint else next(iter(seg_joint))

    owner = [segment_of(max(w, key=lambda x: x[1])[0]) for w in Wt]
    keep = [i for i, s in enumerate(owner) if s is not None]
    heights = P[keep, 1]; lo, hi = np.percentile(heights, 2), np.percentile(heights, 98)
    caps = []
    for s in SEGMENTS:
        if s not in seg_joint:
            continue
        idx = [i for i in keep if owner[i] == s]
        if len(idx) < 4:
            continue
        j = seg_joint[s]
        inv = np.linalg.inv(W[j])
        loc = (inv[:3, :3] @ P[idx].T).T + inv[:3, 3]
        c = loc.mean(0)
        _, _, vt = np.linalg.svd(loc - c, full_matrices=False)
        ax = vt[0]
        t = (loc - c) @ ax
        t0, t1 = np.percentile(t, 3), np.percentile(t, 97)
        a, b = c + ax * t0, c + ax * t1
        half = (t1 - t0) / 2
        pull = 0.0
        for _ in range(4):                      # pull the ends in by the radius, refit the radius
            r = float(np.percentile(seg_dist(loc, a + ax * pull, b - ax * pull), COVER))
            pull = min(r, half) * 0.5 + pull * 0.5   # a ball when the segment is shorter than it is wide
        a, b = a + ax * pull, b - ax * pull
        r = float(np.percentile(seg_dist(loc, a, b), COVER))
        centre_y = float((W[j] @ np.append(c, 1))[1])
        h = 0 if centre_y < lo + (hi - lo) / 3 else 1 if centre_y < lo + 2 * (hi - lo) / 3 else 2
        caps.append({"segment": s, "joint": j, "joint_name": J[j]["name"], "a": a.tolist(), "b": b.tolist(),
                     "radius": r, "height": h, "grabbable": 1, "vertices": len(idx)})
    return {"fighter": fighter, "capsules": caps, "missing_segments": missing,
            "vertices": len(P), "excluded_held": len(P) - len(keep)}, (pl, rest, W, P, Wt, keep)


def seg_dist(p, a, b):
    ab = b - a; L = float(ab @ ab)
    t = np.clip(((p - a) @ ab) / L, 0, 1) if L > 1e-12 else np.zeros(len(p))
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1)


def coverage(caps, worlds, P):
    """Share of points P (world) inside some capsule posed by `worlds`; worst outside distance."""
    best = np.full(len(P), np.inf)
    for c in caps:
        m = worlds[c["joint"]]
        a = m[:3, :3] @ np.array(c["a"]) + m[:3, 3]; b = m[:3, :3] @ np.array(c["b"]) + m[:3, 3]
        sc = float(np.cbrt(abs(np.linalg.det(m[:3, :3]))))
        best = np.minimum(best, seg_dist(P, a, b) - c["radius"] * sc)
    return float((best <= 1e-6).mean()), float(best.max())


def pose_worlds(anim, pl, rest, f):
    nodes = {n["name"]: n for g in anim["groups"] if g["group_type"] == "Transform" for n in g["nodes"]}
    world = []
    for j in pl["joints"]:
        m = np.eye(4)
        if not j["synthesized"]:
            t, r, s = rest[j["name"]][:3]
            nd = nodes.get(j["name"])
            if nd is not None:
                from scipy.spatial.transform import Rotation
                v = nd["tracks"][0]["values"]["Transform"]; v = v[min(f, len(v) - 1)]
                r = Rotation.from_quat([v["rotation"][a] for a in "xyzw"])
                s = np.array([v["scale"][a] for a in "xyz"])
                if not nd["tracks"][0]["transform_flags"]["override_translation"]:
                    t = np.array([v["translation"][a] for a in "xyz"])
            m = CA.srt(t, r, s)
        world.append(world[j["parent"]] @ m if j["parent"] is not None else m)
    return world


def check(fighter, res, ctx, clips, fold_helpers=False):
    pl, rest, W, P, Wt, keep = ctx
    P = P[keep]; Wt = [Wt[i] for i in keep]
    out = {"rest": dict(zip(("covered", "worst_outside"), coverage(res["capsules"], W, P)))}
    orient = {} if fold_helpers else CA.helper_constraints(fighter)[0]
    for clip in clips:
        anim = CA.decode(os.path.join(CA.FIGHTERS, fighter, "motion", "body", "c00", clip + ".nuanmb"))
        CA.bake_helpers(anim, pl, rest, orient)
        n = int(round(anim["final_frame_index"])) + 1
        cov, worst = [], 0.0
        for f in range(0, n, max(1, n // 8)):
            wd = pose_worlds(anim, pl, rest, f)
            sk = [w @ np.linalg.inv(w0) for w, w0 in zip(wd, W)]
            Q = np.zeros_like(P)
            for i, w in enumerate(Wt):
                for j, x in w:
                    Q[i] += x * (sk[j][:3, :3] @ P[i] + sk[j][:3, 3])
            c, wo = coverage(res["capsules"], wd, Q)
            cov.append(c); worst = max(worst, wo)
        out[clip] = {"covered_min": round(min(cov), 3), "covered_mean": round(float(np.mean(cov)), 3),
                     "worst_outside": round(worst, 3)}
    out["rest"] = {k: round(v, 3) for k, v in out["rest"].items()}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fighter")
    ap.add_argument("--check", nargs="*", default=["a00wait1", "a02run", "c03attacks4s", "c05attackairb", "a05squatwait"])
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    res, ctx = plan(a.fighter)
    res["check"] = check(a.fighter, res, ctx, a.check)
    W = ctx[2]
    ext = np.ptp(ctx[3][:, 1])
    res["body_height"] = round(float(ext), 3)
    out = a.out or os.path.join(CA.ROOT, "_build", "tmp", "ir", f"{a.fighter}.hurtboxes.json")
    json.dump(res, open(out, "w"), indent=1)
    for c in res["capsules"]:
        print(f"{c['segment']:11} {c['joint_name']:10} r {c['radius']:.2f} len "
              f"{np.linalg.norm(np.subtract(c['b'], c['a'])):.2f} h{c['height']} ({c['vertices']} verts)")
    print(f"missing {res['missing_segments']}; body height {res['body_height']}; held-item verts left out "
          f"{res['excluded_held']}")
    for k, v in res["check"].items():
        print(f"  {k:16} {v}")
    print("->", out)


if __name__ == "__main__":
    sys.exit(main())
