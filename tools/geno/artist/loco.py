"""loco.py - forward kinematics over a clip, and the locomotion reference speed measured from it.

The engine plays a walk or run clip at rate = ground speed / the clip's reference speed (geno.md 22.3, 22.4: `slow_walk_max`,
`mid_walk_point`, `fast_walk_min`, `run_animation_scaling`). The reference speed is how fast the planted foot moves backward, in
units per frame at rate 1.0: measure it, do not guess it.
"""
import numpy as np

from .model import AF


def _local(f, node_idx, clip, k):
    nd = f.nodes[node_idx]
    name = nd.get("name", "")
    rot = nd.get("rotation", [0, 0, 0, 1])
    tr = np.array(nd.get("translation", [0, 0, 0]), dtype=float) * f.scale
    ch = clip.chan.get((name, "rotation"))
    if ch is not None and k < len(ch[1]):
        rot = ch[1][k]
    ch = clip.chan.get((name, "translation"))
    if ch is not None and k < len(ch[1]):
        tr = ch[1][k] * f.scale
    m = np.eye(4)
    m[:3, :3] = AF.quat_to_mat(rot)
    m[:3, 3] = tr
    return m


def world_track(f, clip, bone):
    """(frames, 3) world positions of a skin bone's origin across the clip."""
    chain = []
    n = bone.node
    while n is not None:
        chain.append(n)
        n = f.parent_node.get(n)
    chain.reverse()
    out = np.zeros((clip.frames, 3))
    for k in range(clip.frames):
        m = np.eye(4)
        for n in chain:
            m = m @ _local(f, n, clip, k)
        out[k] = m[:3, 3]
    return out


def ref_speed(f, clip):
    """Planted-foot speed in units/frame at rate 1.0, or None when the clip has no usable stance phase."""
    fl, fr = f.role_bone.get("foot.L"), f.role_bone.get("foot.R")
    if not fl or not fr or clip.frames < 4:
        return None
    pl, pr = world_track(f, clip, fl), world_track(f, clip, fr)
    ymin = min(pl[:, 1].min(), pr[:, 1].min())
    sp = []
    for k in range(clip.frames - 1):
        for p in (pl, pr):
            other = pr if p is pl else pl
            if p[k, 1] <= other[k, 1] + 1e-6 and p[k, 1] < ymin + 0.35 and p[k + 1, 1] < ymin + 0.35:
                sp.append(-(p[k + 1, 2] - p[k, 2]))
    sp = [s for s in sp if s > 1e-4]
    if len(sp) < 3:
        return None
    return float(np.median(sp))
