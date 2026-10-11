"""Blender action writer for the pure figatree decoder/pose sampler."""
import math

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

try:
    from . import figatree_decode as D, figatree_import as I, wbspace as W
except ImportError:
    import figatree_decode as D
    import figatree_import as I
    import wbspace as W


def _error(a, b):
    return max(abs(a[r][c] - b[r][c]) for r in range(4) for c in range(4))


def _matrix(values, mode):
    loc, rotation, scale = values
    q = Quaternion(rotation).normalized() if mode == "QUATERNION" else Euler(rotation, mode).to_quaternion()
    return Matrix.LocRotScale(Vector(loc), q, Vector(scale))


def _sample(arm, sampler, clip, tolerance):
    """Linear pose keys, adaptively checked at quarter/half/three-quarter times.

    Rotation changes of basis are nonlinear even for linear HSD Euler curves.
    Key boundaries plus a half-frame grid retain motion; refinement checks
    matrix error in continuous spans. A short CONSTANT interval immediately
    before a jump avoids smoothing CON/KEY steps. Blender's native near-key
    snapping still limits fractional-frame precision at those boundaries.
    """
    times = set(I.sample_times(clip))
    cache = {}
    modes = {pb.name: pb.rotation_mode for pb in arm.pose.bones}
    rotation_tracks = [(track, sampler.rest[i].rotation[track.type-1])
                       for i, joint in enumerate(clip.joints) for track in joint if track.type in (1, 2, 3)]

    def matrices(t):
        if t not in cache:
            bases = sampler.bases(clip, t)
            # PoseSampler resolves Blender-only ancestors in their bind pose.
            # Key them too, so switching actions cannot retain a prior pose.
            cache[t] = {name: Matrix(bases.get(name, I.IDENTITY)) for name in modes}
            for name, matrix in cache[t].items():
                if arm.data.bones[name].use_connect and matrix.translation.length > tolerance:
                    raise D.FigatreeError(f"{clip.name}, bone {name}: connected bones cannot represent this translation; disconnect it before importing")
        return cache[t]

    constant = set()
    boundaries = {t for joint in clip.joints for track in joint for t in track.key_times() if 0 < t <= clip.frames}
    for t in sorted(boundaries):
        # Blender stores key times as float32; the left key must be distinct.
        epsilon = max(5e-5, t * 2e-7)
        left = max(0., t - epsilon)
        near = matrices(max(0., t - 1e-8))
        right = matrices(t)
        if any(_error(near[name], right[name]) > tolerance for name in modes):
            times.add(left)
            constant.add(left)

    for _ in range(13):
        ordered = sorted(times)
        rows, previous = {}, {}
        for t in ordered:
            row = {}
            for name, matrix in matrices(t).items():
                loc, quat, scale = matrix.decompose()
                mode = modes[name]
                if mode == "QUATERNION":
                    if name in previous and previous[name].dot(quat) < 0:
                        quat = -quat
                    rotation = quat
                else:
                    rotation = quat.to_euler(mode, previous[name]) if name in previous else quat.to_euler(mode)
                previous[name] = rotation
                values = (tuple(loc), tuple(rotation), tuple(scale))
                if _error(matrix, _matrix(values, mode)) > tolerance:
                    raise D.FigatreeError(f"{clip.name}, bone {name}: pose requires shear; this bind frame cannot represent it as SRT keys")
                row[name] = values
            rows[t] = row
        refine = []
        for a, b in zip(ordered, ordered[1:]):
            if a in constant:
                continue
            # Matrices alone alias whole turns at regularly spaced probes.
            # Bound the unwrapped source angles as well, retaining rapid spins.
            probes = [a + (b-a)*u for u in (0, .25, .5, .75, 1)]
            if any(max(values) - min(values) > math.pi/4
                   for track, default in rotation_tracks
                   for values in [[track.evaluate(t, default) for t in probes]]):
                refine.append((a+b)*.5)
                continue
            for u in (.25, .5, .75):
                t = a + (b-a)*u
                exact = matrices(t)
                for name, mode in modes.items():
                    lerped = tuple(tuple(x*(1-u) + y*u for x, y in zip(v0, v1))
                                   for v0, v1 in zip(rows[a][name], rows[b][name]))
                    if _error(_matrix(lerped, mode), exact[name]) > tolerance * .5:
                        refine.append((a+b)*.5)
                        break
                else:
                    continue
                break
        if not refine:
            return ordered, rows, constant
        times.update(refine)
        if len(times) > 200_000:
            break
    raise D.FigatreeError(f"{clip.name}: cannot meet pose tolerance {tolerance:g} within the sample budget")


def _fcurves(action, arm):
    if hasattr(action, "slots"):
        slot = action.slots.new("OBJECT", arm.name)
        layer = action.layers.new("Figatree")
        strip = layer.strips.new(type="KEYFRAME")
        return strip.channelbag(slot, ensure=True).fcurves, "group_name"
    return action.fcurves, "action_group"


def create_actions(arm, clips, rest, plan, aliases=None, tolerance=1e-4):
    """Create separate fake-user actions; preserve the rig, action and timeline.

    On failure remove only actions created by this import. Existing actions are
    never replaced; Blender assigns a numeric suffix on a name collision.
    """
    if arm is None or arm.type != "ARMATURE":
        raise D.FigatreeError("select the fighter's deform armature")
    if not math.isfinite(tolerance) or tolerance <= 0:
        raise D.FigatreeError("pose tolerance must be positive and finite")
    for pb in arm.pose.bones:
        bone = pb.bone
        if (any(not c.mute for c in pb.constraints) or bone.inherit_scale != "FULL"
                or not bone.use_inherit_rotation or not bone.use_local_location
                or pb.rotation_mode == "AXIS_ANGLE"):
            raise D.FigatreeError(f"bone {pb.name}: import onto an unconstrained rig with full transform inheritance and Euler/quaternion rotations")
    if arm.animation_data and arm.animation_data.drivers:
        raise D.FigatreeError("disable pose drivers before importing fighter animations")
    clips = list(clips)
    if not clips:
        raise D.FigatreeError("no animations selected")
    # Imported object rotation/scale establishes the asset's axes and units.
    # Scene placement must not become a joint offset (or rotate about origin).
    orientation = arm.matrix_world.copy()
    orientation.translation = (0, 0, 0)
    transform = W.mul(W.affine_inverse(tuple(tuple(row) for row in orientation)), W.C4)
    sampler = I.PoseSampler(rest, plan,
                            {b.name: tuple(tuple(row) for row in b.matrix_local) for b in arm.data.bones},
                            {b.name: b.parent.name if b.parent else None for b in arm.data.bones},
                            aliases=aliases, model_to_arm=transform)
    # Validate every joint channel before allocating any action.
    for clip in clips:
        sampler.bases(clip, 0)
    created = []
    try:
        for clip in clips:
            times, rows, constant = _sample(arm, sampler, clip, tolerance)
            # A one-frame clip needs just one key; frame 1 is archive time 0.
            action = bpy.data.actions.new(clip.name)
            created.append(action)
            action.use_fake_user = True
            action["figatree_symbol"] = clip.symbol
            action["figatree_flags"] = clip.flags
            action["figatree_first_frame"] = 1
            curves, group_kw = _fcurves(action, arm)
            for name in rows[times[0]]:
                pb = arm.pose.bones[name]
                rotation = "rotation_quaternion" if pb.rotation_mode == "QUATERNION" else "rotation_euler"
                for component, prop in enumerate(("location", rotation, "scale")):
                    width = len(rows[times[0]][name][component])
                    for axis in range(width):
                        curve = curves.new(pb.path_from_id(prop), index=axis, **{group_kw: name})
                        curve.extrapolation = "CONSTANT"
                        curve.keyframe_points.add(len(times))
                        values = [v for t in times for v in (t+1, rows[t][name][component][axis])]
                        curve.keyframe_points.foreach_set("co", values)
                        for key, t in zip(curve.keyframe_points, times):
                            key.interpolation = "CONSTANT" if t in constant else "LINEAR"
                        # Points are already ordered and use no Bezier handles.
                        # FCurve.update() deduplicates nearby frame values and
                        # would erase the distinct key immediately before a step.
            action["figatree_pose_tolerance"] = tolerance
        return created
    except Exception:
        for action in created:
            bpy.data.actions.remove(action)
        raise
