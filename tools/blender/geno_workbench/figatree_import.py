"""Animation-to-rig pose conversion, independent of bpy and the exporter.

FObj channels replace absolute model-local SRT, whereas Blender pose channels
are deltas in each bone's bind frame. Rest offsets bridge those frames. The
model hierarchy (including synthesized or unmapped parents) remains intact.
"""
from __future__ import annotations

import math

try:
    from . import figatree_decode as D, rigmap, wbspace as W
except ImportError:
    import figatree_decode as D
    import rigmap
    import wbspace as W

IDENTITY = ((1., 0., 0., 0.), (0., 1., 0., 0.), (0., 0., 1., 0.), (0., 0., 0., 1.))
CHANNELS = {1: ("rotation", 0), 2: ("rotation", 1), 3: ("rotation", 2),
            5: ("translation", 0), 6: ("translation", 1), 7: ("translation", 2),
            8: ("scale", 0), 9: ("scale", 1), 10: ("scale", 2)}


def srt_matrix(rotation, translation, scale):
    """HSD's Euler local matrix T @ Rz @ Ry @ Rx @ S (radians)."""
    sx, sy, sz = (math.sin(v) for v in rotation)
    cx, cy, cz = (math.cos(v) for v in rotation)
    x, y, z = scale
    return ((cz*cy*x, (cz*sy*sx - sz*cx)*y, (cz*sy*cx + sz*sx)*z, translation[0]),
            (sz*cy*x, (sz*sy*sx + cz*cx)*y, (sz*sy*cx - cz*sx)*z, translation[1]),
            (-sy*x, cy*sx*y, cy*cx*z, translation[2]),
            (0., 0., 0., 1.))


def world_matrices(rest, animation=None, frame=0):
    """Compose all model joints, with HSD parent-scale compensation.

    Classical joints (bit 3) inherit the parent's compensation vector; other
    joints accumulate scale. Bit 26 implements the PC m-ex local-scale fix.
    """
    if animation is not None and len(animation.joints) > len(rest):
        raise D.FigatreeError(f"{animation.name}: more animation joints than the model")
    worlds, accumulated, scales = [], [], []
    for i, joint in enumerate(rest):
        parent = joint.parent
        if parent is not None and not 0 <= parent < i:
            raise D.FigatreeError(f"joint {i}: model hierarchy must be depth first")
        if joint.flags & (1 << 17):
            raise D.FigatreeError(f"joint {i}: quaternion JOBJ rest is unsupported")
        values = {"rotation": list(joint.rotation), "translation": list(joint.translation), "scale": list(joint.scale)}
        if animation is not None and i < len(animation.joints):
            for track in animation.joints[i]:
                if track.type not in CHANNELS:
                    raise D.FigatreeError(f"{animation.name}, joint {i}: unsupported joint channel {track.type}")
                prop, axis = CHANNELS[track.type]
                values[prop][axis] = track.evaluate(frame, values[prop][axis])
        scale = values["scale"]
        scales.append(scale)
        ps = accumulated[parent] if parent is not None else None
        accumulated.append(ps if joint.flags & 8 else tuple(
            scale[k] * (ps[k] if ps else 1) for k in range(3)))
        trans = values["translation"]
        mex = bool(joint.flags & (1 << 26) and parent is not None)
        if mex:
            trans = [trans[k] * scales[parent][k] for k in range(3)]
        local = srt_matrix(values["rotation"], trans, scale)
        if ps is not None:
            if any(abs(s) < 1e-12 for s in ps):
                raise D.FigatreeError(f"joint {i}: zero parent compensation scale")
            local = tuple(tuple(local[r][c] * ps[c] / ps[r] if c < 3 else local[r][c]
                                for c in range(4)) for r in range(3)) + (local[3],)
        if mex:
            if any(abs(s) < 1e-12 for s in scales[parent]):
                raise D.FigatreeError(f"joint {i}: zero m-ex parent scale")
            local = tuple(tuple(v / scales[parent][r] for v in local[r]) for r in range(3)) + (local[3],)
        worlds.append(W.mul(worlds[parent], local) if parent is not None else local)
    return worlds


class PoseSampler:
    """Fixed rest-frame conversion shared by all clips in an import.

    bone_rest maps Blender bone names to armature-space bind matrices.
    model_to_arm maps engine Y-up model space into that same armature space.
    The adapter removes the armature's imported axis rotation/scale from the
    engine-to-Blender transform, without baking scene placement into the clip.
    """
    def __init__(self, rest, plan, bone_rest, bone_parents, aliases=None,
                 model_to_arm=W.C4, require_all=True):
        self.rest = tuple(rest)
        self.bone_rest = dict(bone_rest)
        self.bone_parents = dict(bone_parents)
        self.model_to_arm = model_to_arm
        # Retail plans originally contain parent=None for every joint. Use the
        # authoritative costume tree for ordering without mutating the plan.
        joints = []
        for joint in plan.get("joints", []):
            index = int(joint["index"])
            if not 0 <= index < len(rest):
                raise D.FigatreeError(f"plan joint {index} is outside the model")
            joints.append(dict(joint, parent=rest[index].parent))
        self.jointmap = rigmap.build_joint_map({"joints": joints}, bone_rest, aliases)
        if not self.jointmap.by_index:
            raise D.FigatreeError("no model joints mapped to the rig; choose its plan and bone_aliases")
        if require_all and self.jointmap.missing_bones:
            raise D.FigatreeError(f"joints not mapped to the rig: {self.jointmap.missing_bones}; check bone_aliases")
        engine_rest = world_matrices(self.rest)
        self.offsets = {
            i: W.mul(W.affine_inverse(W.mul(model_to_arm, engine_rest[i])), bone_rest[name])
            for i, name in self.jointmap.by_index.items()
        }
        self.relative_rest = {}
        for name, matrix in self.bone_rest.items():
            parent = self.bone_parents.get(name)
            if parent is not None and parent not in self.bone_rest:
                raise D.FigatreeError(f"bone {name}: missing rig parent {parent}")
            self.relative_rest[name] = W.mul(W.affine_inverse(self.bone_rest[parent]), matrix) if parent else matrix
        # Validate even unmapped parent chains before evaluating an action.
        for name in self.bone_rest:
            seen = set()
            while name is not None:
                if name in seen:
                    raise D.FigatreeError("cycle in rig bone hierarchy")
                seen.add(name)
                name = self.bone_parents.get(name)

    def bases(self, animation, frame):
        """Every mapped bone's pose basis at a fractional archive frame."""
        worlds = world_matrices(self.rest, animation, frame)
        targets = {name: W.mul(W.mul(self.model_to_arm, worlds[i]), self.offsets[i])
                   for i, name in self.jointmap.by_index.items()}
        resolved = {}

        def pose(name):
            if name in targets:
                return targets[name]
            if name not in resolved:
                parent = self.bone_parents.get(name)
                resolved[name] = W.mul(pose(parent), self.relative_rest[name]) if parent else self.relative_rest[name]
            return resolved[name]

        out = {}
        for name, target in targets.items():
            parent = self.bone_parents.get(name)
            base = W.mul(pose(parent), self.relative_rest[name]) if parent else self.relative_rest[name]
            out[name] = W.mul(W.affine_inverse(base), target)
        return out


def sample_times(animation, step=.5):
    """Grid plus exact key/launch boundaries; fractional end frames survive."""
    if not math.isfinite(step) or step <= 0:
        raise D.FigatreeError("sampling step must be positive and finite")
    n = math.ceil(animation.frames / step)
    if n > 1_000_000:
        raise D.FigatreeError("animation duration exceeds the sample budget")
    times = {0., float(animation.frames)}
    times.update(i * step for i in range(n))
    for joint in animation.joints:
        for track in joint:
            times.update(t for t in track.key_times() if 0 <= t <= animation.frames)
    return sorted(times)
