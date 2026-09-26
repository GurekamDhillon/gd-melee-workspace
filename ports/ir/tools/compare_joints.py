#!/usr/bin/env python3
"""compare_joints.py - joint positions the GAME computed vs the source animation's own pose.

    python ports/ir/tools/compare_joints.py <fighter> <melee-pc.log>

The joint-probe mod (ports/ir/tools/joint-probe) logs, every few frames, port 1's animation symbol,
animation frame and every joint's world position. For each sample this rebuilds the same frame from
the Ultimate clip itself (upstream ssbh_lib decode, the fighter's own skeleton, synthesized joints
at rest) and fits a similarity transform (position, rotation, uniform scale: the fighter's place,
facing and model scale, which legitimately differ) between the two joint sets. The residual per
joint is what the conversion, the model and the engine got wrong together. This is the check that
does not grade the converter against itself.
"""
import argparse
import json
import math
import os
import re
import sys
from collections import defaultdict

import numpy as np
from scipy.spatial.transform import Rotation, Slerp

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import convert_ultimate_anim as CA  # noqa: E402
import plan_parts  # noqa: E402

CHUNK = re.compile(r"JPC (\d+) (\S+)$")
END = re.compile(r"JPE (\S+) (-?[\d.]+) (-?\d+) (\d+)")
LINE = re.compile(r"JP(F?) (\S+) (-?[\d.]+) (-?\d+) (.+)$")


def source_pose(anim, plan, rest, frame):
    """World positions of every plan joint at `frame` (fractional: slerp / lerp between samples)."""
    nodes = {n["name"]: n for g in anim["groups"] if g["group_type"] == "Transform" for n in g["nodes"]}
    world = []
    lo = int(math.floor(frame)); a = frame - lo
    for j in plan["joints"]:
        m = np.eye(4)
        if not j["synthesized"]:
            rt, rr, rs, _ = rest[j["name"]]
            node = nodes.get(j["name"])
            if node is None:
                t, r, s = rt, rr, rs
            else:
                tr = node["tracks"][0]; v = tr["values"]["Transform"]
                i0, i1 = min(lo, len(v) - 1), min(lo + 1, len(v) - 1)
                g = lambda x, k: np.array([x[k][c] for c in "xyz"])
                t = g(v[i0], "translation") * (1 - a) + g(v[i1], "translation") * a
                s = g(v[i0], "scale") * (1 - a) + g(v[i1], "scale") * a
                q = Rotation.from_quat([[v[i][ "rotation"][c] for c in "xyzw"] for i in (i0, i1)])
                r = Slerp([0, 1], q)([a])[0]
                if tr["transform_flags"]["override_translation"]:
                    t = rt
            m[:3, :3] = r.as_matrix() @ np.diag(s); m[:3, 3] = t
        world.append(world[j["parent"]] @ m if j["parent"] is not None else m)
    return np.array([w[:3, 3] for w in world])


def fit(src, dst):
    """Similarity transform src -> dst (Umeyama); returns the transformed src and the scale."""
    ms, md = src.mean(0), dst.mean(0)
    a, b = src - ms, dst - md
    u, sig, vt = np.linalg.svd(b.T @ a / len(src))
    d = np.eye(3); d[2, 2] = np.sign(np.linalg.det(u @ vt))
    r = u @ d @ vt
    sc = (sig * np.diag(d)).sum() / (a ** 2).sum() * len(src)
    return (sc * (r @ a.T)).T + md, sc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fighter")
    ap.add_argument("log")
    ap.add_argument("--root-kept", action="store_true", help="the mod predates root-motion stripping")
    ap.add_argument("--folded-helpers", action="store_true", help="the mod was installed with --fold-helpers")
    args = ap.parse_args()
    ir = json.load(open(os.path.join(CA.INSTANCES, f"{args.fighter}.ultimate-body.ir.json"), encoding="utf-8"))
    plan = plan_parts.plan(ir); rest = CA.rest_of(ir)
    orient = {} if args.folded_helpers else CA.helper_constraints(args.fighter)[0]
    real = [i for i, j in enumerate(plan["joints"]) if not j["synthesized"]]
    # Old (untagged "JP") lines: only joints the skin uses, which drawing computes every frame. gd.joints
    # reads each joint's LAST computed matrix, and a joint nothing needed this frame keeps an old
    # one (its "valid" flag stays set), which read as tens of units of error. "JPF" lines were read
    # with gd.joints(port, true), which brings every matrix up to date: all joints are compared.
    mesh = os.path.join(CA.ROOT, "_build", "tmp", "ultimate-mesh", f"{args.fighter}_c00.json")
    if os.path.exists(mesh):
        skinned = {w[0] for d in json.load(open(mesh))["dobjs"] for t in d["tris"] for v in t for w in v["w"]}
        skin_only = [i for i in real if i in skinned]
    else:
        skin_only = real
    motion = os.path.join(CA.FIGHTERS, args.fighter, "motion", "body", "c00")
    anims, per_clip, per_joint, samples, skipped = {}, defaultdict(list), defaultdict(list), 0, defaultdict(int)
    valid_counts = []
    chunks = {}
    root = CA.root_joint(plan)
    for line in open(args.log, encoding="utf-8", errors="replace"):
        # the log caps a line at 2047 bytes: the probe splits the joints into "JPC <first> ..." lines
        # and ends a sample with "JPE <sym> <frame> <facing> <count>"
        mc = CHUNK.search(line)
        if mc:
            chunks[int(mc.group(1))] = mc.group(2); continue
        me = END.search(line)
        if me:
            cells_ = [x for k in sorted(chunks) for x in chunks[k].split(";")]; chunks = {}
            if len(cells_) != int(me.group(4)):
                skipped["incomplete chunked sample"] += 1; continue
            line = f"JPF {me.group(1)} {me.group(2)} {me.group(3)} " + ";".join(cells_)
        m = LINE.search(line)
        if not m:
            continue
        fresh, sym, frame = m.group(1) == "F", m.group(2), float(m.group(3))
        c = re.search(r"_ACTION_(\w+?)_figatree", sym)
        drv = bool(c) and c.group(1).endswith("_drv")
        clip = re.sub(r"_drv$", "", c.group(1)) if c else None   # anim-driven variant (root kept)
        if not clip or not os.path.exists(os.path.join(motion, clip + ".nuanmb")):
            skipped[sym] += 1; continue
        cells = m.group(5).split(";")
        if len(cells) != len(plan["joints"]):
            skipped["joint count %d" % len(cells)] += 1; continue
        # joints the game did not compute this frame: "-" (probe), or exactly 0,0,0 (older logs)
        game = np.array([[float(x) for x in p.split(",")] if p != "-" else [np.nan] * 3 for p in cells])
        game[np.all(game == 0, axis=1)] = np.nan
        use = [i for i in (real if fresh else skin_only) if not np.isnan(game[i]).any()]
        if len(use) < 8:
            skipped["fewer than 8 valid joints"] += 1; continue
        if (clip, drv) not in anims:
            an = CA.decode(os.path.join(motion, clip + ".nuanmb"))
            CA.bake_helpers(an, plan, rest, orient)   # as the installer baked them
            if not drv and root and not args.root_kept:
                CA.strip_root(an, root)               # as the installer stripped it
            anims[(clip, drv)] = an
        last = anims[(clip, drv)]["final_frame_index"]
        src = source_pose(anims[(clip, drv)], plan, rest, min(max(frame, 0.0), last))
        fitted, sc = fit(src[use], game[use])
        err = np.linalg.norm(fitted - game[use], axis=1) / sc           # in source units
        per_clip[clip].append((float(err.max()), frame))
        valid_counts.append(len(use))
        for k, i in enumerate(use):
            per_joint[plan["joints"][i]["name"]].append(float(err[k]))
        samples += 1
    if not samples:
        sys.exit(f"no comparable JP lines (skipped: {dict(skipped)})")
    worst = sorted(((max(e for e, _ in v), c, max(v)[1]) for c, v in per_clip.items()), reverse=True)
    allmax = np.array([e for v in per_clip.values() for e, _ in v])
    print(f"{samples} samples, {len(per_clip)} clips; per-sample worst joint error (source units): "
          f"median {np.median(allmax):.3f}, p95 {np.percentile(allmax, 95):.3f}, max {allmax.max():.3f}")
    print(f"valid joints per sample: median {int(np.median(valid_counts))} of {len(real)}")
    print("worst clips:", [(c, round(e, 3), f) for e, c, f in worst[:8]])
    jm = sorted(((np.percentile(v, 95), n) for n, v in per_joint.items()), reverse=True)
    print("worst joints (p95):", [(n, round(e, 3)) for e, n in jm[:8]])
    if skipped:
        print("skipped:", dict(skipped))


if __name__ == "__main__":
    sys.exit(main())
