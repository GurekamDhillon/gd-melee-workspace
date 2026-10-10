"""Calibration and exact world-matrix preview for Blender fighter rigs.

All coordinate conversion and calibration algebra belongs to wbspace. Live
preview temporarily detaches actions and disables NLA on the armature so that
animation evaluation cannot overwrite incoming matrices. release_preview()
restores the prior animation and pose state.
"""

from contextlib import contextmanager
from dataclasses import dataclass, field
import json
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

try:
    from . import rig, rigmap, wbspace
    from .props import STRINGS
except ImportError:
    import rig
    import rigmap
    import wbspace
    from props import STRINGS


for _key, _value in {
    "fighter_action_missing": "Reference action was not found: {name}",
    "fighter_action_slot": "Cannot choose an armature slot for action: {name}",
    "fighter_plan_missing": "Choose a project with a valid plan_path before calibrating",
    "fighter_aliases_invalid": "art.bone_aliases must map joint names to bone names",
    "fighter_project_invalid": "Could not read workbench project {path}: {error}",
    "fighter_coverage": (
        "only {percent} percent of engine joints have a bone in {armature}; "
        "check the rig or add art.bone_aliases"
    ),
    "fighter_no_reference_row": "No workbench rows are available for calibration",
    "fighter_reference_failed": "Could not fetch the calibration reference frame",
    "fighter_reference_missing": "Reference frame is missing mapped joints: {joints}",
    "fighter_reference_mirrored": "Cannot calibrate mirrored reference joints: {joints}",
    "fighter_calibrating": "Calibration is already in progress",
    "fighter_calibration_failed": "Could not calibrate the fighter: {error}",
    "fighter_calibrated": (
        "calibrated {mapped} joints; missing joints {missing}; "
        "unmapped bones {unmapped}; synthesized joints {synth}"
    ),
    "fighter_scale_warning": "rig scale differs from the engine by {percent:.1f} percent",
    "fighter_head_warning": "bone head is not at the joint origin: {names}",
    "fighter_nonfinite_matrix": "Joint {joint} has a non-finite matrix",
    "fighter_singular_joint": "Joint {joint} has a singular matrix",
    "fighter_singular_armature": "The armature world matrix is singular",
    "fighter_apply_failed": "Could not apply the fighter pose: {error}",
    "fighter_verify_calibration": "Calibrate and apply a frame before verifying the pose",
    "fighter_verify_empty": "There are no comparable, non-mirrored mapped joints",
    "fighter_verify_position": "Joint {joint} has no finite three-component position",
    "fighter_verify_epsilon": "Pose verification tolerance must be finite and nonnegative",
    "fighter_stale_suffix": "stale: rebuild needed",
}.items():
    STRINGS.setdefault(_key, _value)


def _text(key, **values):
    return STRINGS[key].format(**values)


@dataclass
class ApplyReport:
    posed: int = 0
    skipped_mirrored: list[int] = field(default_factory=list)
    missing: list[int] = field(default_factory=list)


CAL = None
_CAL_ARMATURE = None
_LAST_APPLIED = None
_CALIBRATING = False
_PREVIEWS = []


def _same_armature(a, b):
    try:
        return a is not None and b is not None and a == b
    except ReferenceError:
        return False


def calibration_for(arm):
    """Return this rig's (JointMap, Calibration), never another rig's offsets."""
    if CAL is not None and _same_armature(arm, _CAL_ARMATURE):
        return CAL
    return None


def is_calibrating():
    return _CALIBRATING


def _assign_action(arm, action):
    ad = arm.animation_data_create()
    ad.action = action
    if action is None or not hasattr(ad, "action_slot"):
        return
    slots = list(getattr(action, "slots", ()))
    if not slots or ad.action_slot is not None:
        return
    compatible = [
        slot for slot in slots
        if getattr(slot, "target_id_type", "OBJECT") == "OBJECT"
    ]
    named = [
        slot for slot in compatible
        if getattr(slot, "name_display", "") == arm.name
    ]
    choices = named if len(named) == 1 else compatible
    if len(choices) != 1:
        raise RuntimeError(_text("fighter_action_slot", name=action.name))
    ad.action_slot = choices[0]


class _RigState:
    def __init__(self, arm):
        self.arm = arm
        self.bases = {
            bone.name: bone.matrix_basis.copy() for bone in arm.pose.bones
        }
        self.object_basis = arm.matrix_basis.copy()
        self.pose_position = arm.data.pose_position
        ad = arm.animation_data
        self.had_animation = ad is not None
        self.action = ad.action if ad else None
        self.slot = getattr(ad, "action_slot", None) if ad else None
        self.use_nla = ad.use_nla if ad else True

    def restore_animation(self):
        arm = self.arm
        arm.data.pose_position = self.pose_position
        if self.had_animation:
            ad = arm.animation_data_create()
            ad.action = self.action
            if self.slot is not None and self.action is not None:
                ad.action_slot = self.slot
            ad.use_nla = self.use_nla
        elif arm.animation_data is not None:
            arm.animation_data_clear()

    def restore_transforms(self):
        self.arm.matrix_basis = self.object_basis
        for name, matrix in self.bases.items():
            bone = self.arm.pose.bones.get(name)
            if bone is not None:
                bone.matrix_basis = matrix

    def restore(self):
        self.restore_animation()
        self.restore_transforms()
        bpy.context.view_layer.update()


_FAST = {}   # armature name -> (bone count, ok): the closed-form posing below needs plain bone inheritance


def _fast_ok(arm):
    """True when matrix_basis can be computed from armature-space targets without the depsgraph."""
    key = arm.name
    bones = arm.pose.bones
    cached = _FAST.get(key)
    if cached is not None and cached[0] == len(bones) and cached[1] is arm.data:
        return cached[2]
    ok = True
    for pbone in bones:
        bone = pbone.bone
        if (pbone.constraints or not bone.use_inherit_rotation
                or bone.inherit_scale != "FULL" or not bone.use_local_location
                or pbone.rotation_mode in {"AXIS_ANGLE"}):
            ok = False
            break
    _FAST[key] = (len(bones), arm.data, ok)
    return ok


def _assign_bases(arm, targets):
    """Set matrix_basis so each bone's armature-space pose equals the target, parent first.

    pose = parent_pose @ (parent_rest^-1 @ rest) @ basis, so basis follows in closed form. A parent
    that is not a target is resolved from its own basis, so no depsgraph update is needed in between.
    """
    wanted = {bone.name: matrix for bone, matrix in targets}
    memo = {}

    def pose_of(pbone):
        name = pbone.name
        if name in wanted:
            return wanted[name]
        if name in memo:
            return memo[name]
        parent = pbone.parent
        if parent is None:
            result = pbone.bone.matrix_local @ pbone.matrix_basis
        else:
            offset = parent.bone.matrix_local.inverted_safe() @ pbone.bone.matrix_local
            result = pose_of(parent) @ offset @ pbone.matrix_basis
        memo[name] = result
        return result

    for pbone, target in targets:
        parent = pbone.parent
        if parent is None:
            rest = pbone.bone.matrix_local
        else:
            offset = parent.bone.matrix_local.inverted_safe() @ pbone.bone.matrix_local
            rest = pose_of(parent) @ offset
        pbone.matrix_basis = rest.inverted_safe() @ target


def _detach_animation(arm):
    ad = arm.animation_data
    if ad is not None:
        ad.action = None
        ad.use_nla = False
    arm.data.pose_position = "POSE"


def release_preview(arm=None):
    """Restore previewed rigs; tolerate objects deleted by the user."""
    global CAL, _CAL_ARMATURE, _LAST_APPLIED
    rig._require_main_thread()
    for entry in list(_PREVIEWS):
        preview_arm, previous = entry
        if arm is not None and not _same_armature(arm, preview_arm):
            continue
        try:
            previous.restore()
        except ReferenceError:
            pass
        finally:
            _PREVIEWS.remove(entry)
    if arm is None or _same_armature(arm, _CAL_ARMATURE):
        CAL = None
        _CAL_ARMATURE = None
    if arm is None or (
        _LAST_APPLIED and _same_armature(arm, _LAST_APPLIED[0])
    ):
        _LAST_APPLIED = None


@contextmanager
def calibration_transaction():
    """Keep the previous calibration if an operator cannot complete its preview."""
    global CAL, _CAL_ARMATURE, _LAST_APPLIED
    previous = CAL, _CAL_ARMATURE, _LAST_APPLIED
    previews = list(_PREVIEWS)
    try:
        yield
    except Exception:
        for entry in list(_PREVIEWS):
            if not any(entry is old for old in previews):
                try:
                    entry[1].restore()
                except ReferenceError:
                    pass
                finally:
                    _PREVIEWS.remove(entry)
        CAL, _CAL_ARMATURE, _LAST_APPLIED = previous
        raise


def _matrix_tuple(matrix):
    return tuple(tuple(float(matrix[r][c]) for c in range(4)) for r in range(4))


def _finite_matrix(matrix, joint):
    if not all(math.isfinite(float(value)) for row in matrix for value in row):
        raise RuntimeError(_text("fighter_nonfinite_matrix", joint=joint))


def blender_rest_matrices(arm, jointmap, action_name="", frame=0):
    """Sample an action, or identity pose bases, then restore action and timeline."""
    rig._require_main_thread()
    rig.bone_names(arm)
    action = bpy.data.actions.get(action_name) if action_name else None
    if action_name and action is None:
        raise RuntimeError(_text("fighter_action_missing", name=action_name))

    state = _RigState(arm)
    scene = bpy.context.scene
    old_frame, old_subframe = scene.frame_current, scene.frame_subframe
    sample_frame = math.floor(float(frame))
    sample_subframe = float(frame) - sample_frame
    try:
        _detach_animation(arm)
        for bone in arm.pose.bones:
            bone.matrix_basis = Matrix.Identity(4)
        if action is not None:
            _assign_action(arm, action)
            arm.animation_data.use_nla = False
        scene.frame_set(sample_frame, subframe=sample_subframe)
        bpy.context.view_layer.update()
        result = {}
        for joint, name in jointmap.by_index.items():
            bone = arm.pose.bones.get(name)
            if bone is not None:
                matrix = _matrix_tuple(arm.matrix_world @ bone.matrix)
                _finite_matrix(matrix, joint)
                result[joint] = matrix
        return result
    finally:
        state.restore_animation()
        try:
            scene.frame_set(old_frame, subframe=old_subframe)
        finally:
            state.restore_transforms()
            bpy.context.view_layer.update()


def _bone_aliases(session):
    aliases = getattr(session, "bone_aliases", None)
    if isinstance(aliases, dict):  # filled by api.set_project (or set directly by tests)
        return dict(aliases)
    # Project paths are resolved by api.set_project. The scene property is the
    # specified Task 6 source when the session has no project-directory member.
    project = (
        getattr(session, "project_dir", "")
        or getattr(session, "project", "")
    )
    if not project:
        props = getattr(bpy.context.scene, "geno_wb", None)
        project = getattr(props, "project", "") if props else ""
    if not project:
        return {}
    path = Path(bpy.path.abspath(str(project))).expanduser()
    if path.name.lower() != "workbench.json":
        path = path / "workbench.json"
    try:
        with path.open("r", encoding="utf-8-sig") as source:
            config = json.load(source)
        art = config.get("art") or {}
        aliases = art.get("bone_aliases") or {}
    except (OSError, ValueError, AttributeError, TypeError) as exc:
        raise RuntimeError(_text(
            "fighter_project_invalid", path=path, error=exc
        )) from exc
    if not isinstance(aliases, dict) or not all(
        isinstance(key, str) and isinstance(value, str)
        for key, value in aliases.items()
    ):
        raise RuntimeError(STRINGS["fighter_aliases_invalid"])
    return aliases


@contextmanager
def _suspend_frame_hooks(session):
    # A successful load_row followed by a failed set_frame must not have
    # previewed an intermediate pose or updated overlays.
    hooks = getattr(session, "on_frame", None)
    saved = list(hooks) if isinstance(hooks, list) else None
    if saved is not None:
        hooks.clear()
    try:
        yield
    finally:
        if saved is not None:
            added = [hook for hook in hooks if hook not in saved]
            hooks[:] = saved + added


def _session_success(success, session):
    if not success:
        raise RuntimeError(
            getattr(session, "last_error", "")
            or getattr(session, "status", "")
            or STRINGS["fighter_reference_failed"]
        )


def calibrate(arm, session):
    """Calibrate at engine frame 1 versus action frame 0 without posing early."""
    global CAL, _CAL_ARMATURE, _LAST_APPLIED, _CALIBRATING
    rig._require_main_thread()
    if _CALIBRATING:
        raise RuntimeError(STRINGS["fighter_calibrating"])
    plan_path = getattr(session, "plan_path", "")
    if not plan_path:
        raise RuntimeError(STRINGS["fighter_plan_missing"])

    try:
        plan = rigmap.load_plan(plan_path)
        jm = rigmap.build_joint_map(
            plan, rig.bone_names(arm), aliases=_bone_aliases(session)
        )
    except (OSError, ValueError, TypeError) as exc:
        raise RuntimeError(_text("fighter_calibration_failed", error=exc)) from exc

    if jm.coverage() < 0.8 or not jm.by_index:
        raise RuntimeError(_text(
            "fighter_coverage",
            percent=f"{100.0 * jm.coverage():.1f}",
            armature=arm.name,
        ))

    # The server fills each row's clip from the plan (list_rows); rows without one are skipped here.
    rows = list(session.rows)
    matching = [
        row for row in rows
        if row.get("clip") and bpy.data.actions.get(row["clip"]) is not None
    ]
    reference = next(
        (row for row in matching if row["clip"] == "Wait"),
        matching[0] if matching else None,
    )
    if reference is None:
        reference = next(
            (row for row in rows if str(row.get("name", "")).casefold() == "wait"),
            rows[0] if rows else None,
        )
        action_name = ""
    else:
        action_name = reference["clip"]
    if reference is None or not reference.get("name"):
        raise RuntimeError(STRINGS["fighter_no_reference_row"])

    _CALIBRATING = True
    try:
        with _suspend_frame_hooks(session):
            _session_success(session.load_row(reference["name"]), session)
            _session_success(session.set_frame(1), session)
            info = session.info
            if not isinstance(info, dict):
                raise RuntimeError(STRINGS["fighter_reference_failed"])
            matrices = wbspace.bone_matrices(info)
            missing = sorted(set(jm.by_index) - set(matrices))
            if missing:
                raise RuntimeError(_text(
                    "fighter_reference_missing", joints=", ".join(map(str, missing))
                ))
            mirrored = [
                joint for joint in jm.order()
                if wbspace.is_mirrored(matrices[joint])
            ]
            if mirrored:
                raise RuntimeError(_text(
                    "fighter_reference_mirrored",
                    joints=", ".join(map(str, mirrored)),
                ))
            engine_rest = {
                joint: wbspace.to_blender_matrix(matrices[joint])
                for joint in jm.by_index
            }
            for joint, matrix in engine_rest.items():
                _finite_matrix(matrix, joint)
            blender_rest = blender_rest_matrices(
                arm, jm, action_name=action_name, frame=0
            )
            missing = sorted(set(jm.by_index) - set(blender_rest))
            if missing:
                raise RuntimeError(_text(
                    "fighter_reference_missing", joints=", ".join(map(str, missing))
                ))
            mirrored = [
                joint for joint, matrix in blender_rest.items()
                if wbspace.is_mirrored(matrix)
            ]
            if mirrored:
                raise RuntimeError(_text(
                    "fighter_reference_mirrored",
                    joints=", ".join(map(str, mirrored)),
                ))
            try:
                cal = wbspace.calibrate_offsets(
                    engine_rest, blender_rest, jm.order()[0]
                )
            except ValueError as exc:
                raise RuntimeError(_text(
                    "fighter_calibration_failed", error=exc
                )) from exc

        messages = [_text(
            "fighter_calibrated",
            mapped=len(jm.by_index),
            missing=len(jm.missing_bones),
            unmapped=len(jm.unmapped_bones),
            synth=len(jm.skipped_synth),
        )]
        if abs(cal.scale - 1.0) > 0.02:
            messages.append(_text(
                "fighter_scale_warning", percent=abs(cal.scale - 1.0) * 100.0
            ))
        displaced = [
            jm.by_index[joint]
            for joint, offset in cal.k.items()
            if math.sqrt(sum(offset[axis][3] ** 2 for axis in range(3))) > 0.05
        ]
        if displaced:
            messages.append(_text(
                "fighter_head_warning", names=", ".join(displaced)
            ))
        if getattr(session, "stale", False):
            messages.append(STRINGS["fighter_stale_suffix"])
        session.status = "; ".join(messages)
        CAL = (jm, cal)
        _CAL_ARMATURE = arm
        _LAST_APPLIED = None
        return cal
    finally:
        _CALIBRATING = False


def apply_frame(arm, info, jointmap, cal):
    """Preflight, then assign parent-first matrices in armature-local space."""
    global _LAST_APPLIED
    wbspace.check_schema(info)
    rig._require_main_thread()
    rig.bone_names(arm)
    matrices = wbspace.bone_matrices(info)
    missing = set(matrices) - set(jointmap.by_index)
    missing.update(set(jointmap.by_index) - set(matrices))
    report = ApplyReport()
    targets = []

    # Complete validation before changing any Blender state.
    for joint in jointmap.order():
        matrix = matrices.get(joint)
        bone = arm.pose.bones.get(jointmap.by_index[joint])
        if matrix is None or bone is None or joint not in cal.k:
            missing.add(joint)
            continue
        _finite_matrix(matrix, joint)
        if wbspace.is_mirrored(matrix):
            report.skipped_mirrored.append(joint)
            continue
        if abs(wbspace.det3(matrix)) < 1e-12:
            raise RuntimeError(_text("fighter_singular_joint", joint=joint))
        target = wbspace.target_matrix(
            wbspace.to_blender_matrix(matrix), cal.k[joint]
        )
        _finite_matrix(target, joint)
        if wbspace.is_mirrored(target):
            report.skipped_mirrored.append(joint)
            continue
        targets.append((bone, Matrix(target)))

    report.missing = sorted(missing)
    if not targets:
        return report

    world = _matrix_tuple(arm.matrix_world)
    _finite_matrix(world, -1)
    if abs(wbspace.det3(world)) < 1e-12:
        raise RuntimeError(STRINGS["fighter_singular_armature"])
    arm_inverse = arm.matrix_world.inverted()
    previous = _RigState(arm)
    try:
        _detach_animation(arm)
        if _fast_ok(arm):
            # One depsgraph evaluation for the whole pose instead of one per bone (R2).
            _assign_bases(arm, [(bone, arm_inverse @ target) for bone, target in targets])
            report.posed += len(targets)
        else:
            for bone, target in targets:
                bone.matrix = arm_inverse @ target
                # A child's matrix setter reads its evaluated parent. Updating here
                # avoids a one-frame dependency lag in a multi-level hierarchy.
                bpy.context.view_layer.update()
                report.posed += 1
        bpy.context.view_layer.update()
    except Exception as exc:
        previous.restore()
        raise RuntimeError(_text("fighter_apply_failed", error=exc)) from exc

    if not any(_same_armature(arm, item[0]) for item in _PREVIEWS):
        _PREVIEWS.append((arm, previous))
    _LAST_APPLIED = (arm, jointmap, cal)
    return report


def _verification_calibration(arm, jointmap):
    if _LAST_APPLIED is not None:
        other_arm, other_map, cal = _LAST_APPLIED
        if (
            _same_armature(arm, other_arm)
            and other_map.by_index == jointmap.by_index
        ):
            return cal
    current = calibration_for(arm)
    if current and current[0].by_index == jointmap.by_index:
        return current[1]
    raise RuntimeError(STRINGS["fighter_verify_calibration"])


def verify_pose(arm, info, jointmap, eps=1e-3):
    """Measure world-space heads and the target's upper-left 3x3 matrix.

    ``ok`` is the requested positional test. Rotation, missing joints and
    mirrored skips are returned separately so the operator can warn on them.
    """
    wbspace.check_schema(info)
    rig._require_main_thread()
    rig.bone_names(arm)
    if not math.isfinite(eps) or eps < 0:
        raise ValueError(STRINGS["fighter_verify_epsilon"])
    cal = _verification_calibration(arm, jointmap)
    matrices = wbspace.bone_matrices(info)
    rows = {int(bone["joint"]): bone for bone in info["bones"]}
    max_err, rot_err, worst_joint, count = 0.0, 0.0, -1, 0
    missing, skipped = [], []
    bpy.context.view_layer.update()

    for joint in jointmap.order():
        bone = arm.pose.bones.get(jointmap.by_index[joint])
        matrix = matrices.get(joint)
        if bone is None or matrix is None or joint not in cal.k:
            missing.append(joint)
            continue
        _finite_matrix(matrix, joint)
        if wbspace.is_mirrored(matrix):
            skipped.append(joint)
            continue
        target = wbspace.target_matrix(
            wbspace.to_blender_matrix(matrix), cal.k[joint]
        )
        _finite_matrix(target, joint)
        if wbspace.is_mirrored(target):
            skipped.append(joint)
            continue
        try:
            position = rows[joint]["pos"]
            if isinstance(position, dict):  # frame_info writes {"x":..,"y":..,"z":..}
                position = [position["x"], position["y"], position["z"]]
            if len(position) != 3 or not all(
                math.isfinite(float(value)) for value in position
            ):
                raise ValueError
            expected = Vector(wbspace.to_blender_point(position))
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise RuntimeError(_text(
                "fighter_verify_position", joint=joint
            )) from exc

        actual_head = arm.matrix_world @ bone.head
        actual_matrix = _matrix_tuple(arm.matrix_world @ bone.matrix)
        _finite_matrix(actual_matrix, joint)
        error = (actual_head - expected).length
        if not math.isfinite(error):
            raise RuntimeError(_text("fighter_verify_position", joint=joint))
        rotation_error = math.sqrt(sum(
            (actual_matrix[r][c] - target[r][c]) ** 2
            for r in range(3) for c in range(3)
        ))
        if worst_joint == -1 or error > max_err:
            max_err, worst_joint = error, joint
        rot_err = max(rot_err, rotation_error)
        count += 1

    if not count:
        raise RuntimeError(STRINGS["fighter_verify_empty"])
    return {
        "max_err": max_err,
        "worst_joint": worst_joint,
        "n": count,
        "ok": max_err <= eps,
        "rot_err": rot_err,
        "missing": missing,
        "skipped_mirrored": skipped,
    }
