"""Task 7 operators and optional frame-preview integration.

Register after Task 6's props/API. Frame callbacks accept an info dictionary,
a session, or no arguments. Off-thread callbacks enqueue data; the registered
main-thread timer performs all Blender operations.

Task 8's optional overlay entry point is ``overlays.update(info)``.
"""

from copy import deepcopy
import importlib
from pathlib import Path
import threading

import bpy
from bpy.props import FloatProperty, IntProperty, PointerProperty, StringProperty

try:
    from . import api, pose, rig, travel, wbspace
    from .props import STRINGS
except ImportError:
    import api
    import pose
    import rig
    import travel
    import wbspace
    from props import STRINGS


for _key, _value in {
    "fighter_armature_label": "Armature",
    "fighter_art_path_label": "Loaded art",
    "fighter_mapped_label": "Mapped joints",
    "fighter_missing_label": "Missing joints",
    "fighter_unmapped_label": "Unmapped bones",
    "fighter_synth_label": "Synthesized joints",
    "fighter_scale_label": "Calibration scale",
    "fighter_pose_error_label": "Maximum head error",
    "fighter_load_label": "Load Fighter",
    "fighter_calibrate_label": "Calibrate",
    "fighter_verify_label": "Verify Pose",
    "fighter_load_description": "Load local fighter art and calibrate its engine joint mapping",
    "fighter_calibrate_description": "Calibrate against engine frame 1 and reference action frame 0",
    "fighter_verify_description": "Compare evaluated bone heads and matrices with the engine frame",
    "fighter_art_extension": "Fighter art must be a .blend or .glb file: {path}",
    "fighter_named_armature_missing": "Armature was not found: {name}",
    "fighter_not_connected": "Connect to the workbench before calibrating a fighter",
    "fighter_project_setup_failed": "Could not configure the workbench project",
    "fighter_no_frame": "No engine frame is available",
    "fighter_frame_report": (
        "posed {posed} joints; mirrored joints skipped: {mirrored}; "
        "unmapped or unavailable joints: {missing}"
    ),
    "fighter_none": "none",
    "fighter_verify_result": (
        "{result}: max head error={head:.6g}, rotation error={rotation:.6g}, "
        "worst joint={joint}, compared={count}, missing={missing}, mirrored={mirrored}"
    ),
    "fighter_ok": "OK",
    "fighter_warning": "WARNING",
    "fighter_status_error": "Fighter preview: {error}",
}.items():
    STRINGS.setdefault(_key, _value)


def _text(key, **values):
    return STRINGS[key].format(**values)


class GenoWBFighterProps(bpy.types.PropertyGroup):
    armature: StringProperty(
        name=STRINGS["fighter_armature_label"], default=""
    )
    art_path: StringProperty(
        name=STRINGS["fighter_art_path_label"], subtype="FILE_PATH", default=""
    )
    mapped_joints: IntProperty(
        name=STRINGS["fighter_mapped_label"], default=0, min=0
    )
    missing_joints: IntProperty(
        name=STRINGS["fighter_missing_label"], default=0, min=0
    )
    unmapped_bones: IntProperty(
        name=STRINGS["fighter_unmapped_label"], default=0, min=0
    )
    skipped_synth: IntProperty(
        name=STRINGS["fighter_synth_label"], default=0, min=0
    )
    calibration_scale: FloatProperty(
        name=STRINGS["fighter_scale_label"], default=1.0
    )
    pose_error: FloatProperty(
        name=STRINGS["fighter_pose_error_label"], default=-1.0, min=-1.0
    )


_REGISTERED = False
_REGISTERED_CLASSES = []
_OWN_PROPS = False
_HOOK_SESSIONS = []
_PENDING = None
_PENDING_LOCK = threading.Lock()
_IN_FRAME_UPDATE = False


def add_props(cls_or_scene=None):
    """Attach an independent group to Scene; never modify Task 6's properties.

    cls_or_scene is accepted for integration with either registration style.
    The properties deliberately always belong to bpy.types.Scene.
    """
    global _OWN_PROPS
    rig._require_main_thread()
    if not _OWN_PROPS:
        bpy.utils.register_class(GenoWBFighterProps)
        try:
            bpy.types.Scene.geno_wb_fighter = PointerProperty(
                type=GenoWBFighterProps
            )
        except Exception:
            bpy.utils.unregister_class(GenoWBFighterProps)
            raise
        _OWN_PROPS = True


def active_armature(context, required=False):
    fighter = getattr(context.scene, "geno_wb_fighter", None)
    name = fighter.armature if fighter else ""
    arm = rig.find_armature(name)
    # find_armature has a fallback rule, but an explicit UI choice must not
    # silently switch to another rig after the chosen object was deleted.
    if name and (arm is None or arm.name != name):
        if required:
            raise RuntimeError(_text(
                "fighter_named_armature_missing", name=name
            ))
        return None
    if arm is None and required:
        raise RuntimeError(STRINGS["fighter_not_armature"])
    return arm


def _status(session, message, error=False):
    message = str(message)
    if getattr(session, "stale", False):
        suffix = STRINGS["fighter_stale_suffix"]
        if suffix not in message:
            message = f"{message}; {suffix}"
    session.status = message
    session.last_error = message if error else ""
    props = getattr(bpy.context.scene, "geno_wb", None)
    if props is not None:
        props.status = message
    return message


def _failure(operator, session, exc):
    message = _status(session, str(exc), error=True)
    operator.report({"ERROR"}, message)
    return {"CANCELLED"}


def _attach_hook(session):
    hooks = getattr(session, "on_frame", None)
    if isinstance(hooks, list):
        if _frame_hook not in hooks:
            hooks.append(_frame_hook)
        if not any(session is known for known in _HOOK_SESSIONS):
            _HOOK_SESSIONS.append(session)


def _prepare_project(context):
    props = getattr(context.scene, "geno_wb", None)
    project = getattr(props, "project", "") if props else ""
    if project:
        result = api.set_project(bpy.path.abspath(project))
        if result is False:
            session = api.session()
            raise RuntimeError(
                getattr(session, "last_error", "")
                or STRINGS["fighter_project_setup_failed"]
            )
    session = api.session()
    _attach_hook(session)
    if not session.connected:
        raise RuntimeError(STRINGS["fighter_not_connected"])
    return session


def _resolve_art(context, session):
    props = getattr(context.scene, "geno_wb", None)
    override = getattr(props, "blender_art", "") if props else ""
    value = (
        override
        or getattr(session, "art_blend", "")
        or getattr(session, "art_glb", "")
    )
    if not value:
        raise RuntimeError(STRINGS["fighter_no_art"])
    value = str(value)
    if value.startswith("//"):
        path = Path(bpy.path.abspath(value))
    else:
        path = Path(value).expanduser()
        project = getattr(props, "project", "") if props else ""
        if not path.is_absolute() and project:
            path = Path(bpy.path.abspath(project)).expanduser() / path
    if path.suffix.lower() not in (".blend", ".glb"):
        raise RuntimeError(_text("fighter_art_extension", path=path))
    return path.resolve()


def _sync_mapping(context, arm, jointmap, cal):
    props = context.scene.geno_wb_fighter
    props.armature = arm.name
    props.mapped_joints = len(jointmap.by_index)
    props.missing_joints = len(jointmap.missing_bones)
    props.unmapped_bones = len(jointmap.unmapped_bones)
    props.skipped_synth = len(jointmap.skipped_synth)
    props.calibration_scale = cal.scale
    props.pose_error = -1.0


def _overlay_module():
    module_name = f"{__package__}.overlays" if __package__ else "overlays"
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name == module_name:
            return None
        raise


def _pose_warning(report, jointmap):
    missing = [
        joint for joint in report.missing
        if joint not in jointmap.skipped_synth
    ]
    if not report.skipped_mirrored and not missing:
        return ""
    return _text(
        "fighter_frame_report",
        posed=report.posed,
        mirrored=", ".join(map(str, report.skipped_mirrored))
        or STRINGS["fighter_none"],
        missing=", ".join(map(str, missing)) or STRINGS["fighter_none"],
    )


def _show_frame(session, info):
    global _IN_FRAME_UPDATE
    rig._require_main_thread()
    if _IN_FRAME_UPDATE or pose.is_calibrating():
        return
    _IN_FRAME_UPDATE = True
    try:
        wbspace.check_schema(info)
        settings = getattr(bpy.context.scene, "geno_wb", None)
        if not getattr(settings, "show_travel", False):
            # in place: only the body animates; the engine data stays as it came
            if getattr(session, "travel_anchor", None) is None:
                session.travel_anchor = travel.anchor_of(info)
            info = travel.in_place(info, session.travel_anchor)
        arm = active_armature(bpy.context)
        calibration = pose.calibration_for(arm)
        warning = ""
        if calibration is not None:
            jointmap, cal = calibration
            report = pose.apply_frame(arm, info, jointmap, cal)
            warning = _pose_warning(report, jointmap)
            props = bpy.context.scene.geno_wb_fighter
            props.pose_error = -1.0
        overlays = _overlay_module()
        if overlays is not None:
            overlays.update(info)
        message = session.status
        if warning:
            message = f"{message}; {warning}" if message else warning
        _status(session, message)
    finally:
        _IN_FRAME_UPDATE = False


def _callback_data(args, kwargs):
    session = next(
        (
            arg for arg in args
            if hasattr(arg, "on_frame") and hasattr(arg, "info")
        ),
        api.session(),
    )
    info = kwargs.get("info")
    if info is None:
        info = next(
            (
                arg for arg in args
                if isinstance(arg, dict) and ("bones" in arg or "schema" in arg)
            ),
            session.info,
        )
    return session, info


def _frame_hook(*args, **kwargs):
    global _PENDING
    if pose.is_calibrating():
        return
    session, info = _callback_data(args, kwargs)
    if info is None:
        return
    if threading.current_thread() is not threading.main_thread():
        # No bpy access, including timer registration, occurs on this path.
        with _PENDING_LOCK:
            _PENDING = (session, info, deepcopy(info))
        return
    with _PENDING_LOCK:
        _PENDING = None
    try:
        _show_frame(session, info)
    except Exception as exc:
        _status(session, _text("fighter_status_error", error=exc), error=True)


def _drain_pending():
    global _PENDING
    if not _REGISTERED:
        return None
    session = api.session()
    _attach_hook(session)
    with _PENDING_LOCK:
        pending = _PENDING
        _PENDING = None
    if pending is not None:
        owner, original, snapshot = pending
        # Discard replies superseded by another frame, project or connection.
        if owner is session and session.info is original:
            try:
                _show_frame(session, snapshot)
            except Exception as exc:
                _status(
                    session, _text("fighter_status_error", error=exc), error=True
                )
    return 0.1


def _preview_calibration(arm, session):
    pair = pose.calibration_for(arm)
    if pair is None:
        raise RuntimeError(STRINGS["fighter_verify_calibration"])
    if session.info is None:
        raise RuntimeError(STRINGS["fighter_no_frame"])
    jointmap, cal = pair
    report = pose.apply_frame(arm, session.info, jointmap, cal)
    warning = _pose_warning(report, jointmap)
    if warning:
        session.status = f"{session.status}; {warning}"
    return jointmap, cal


def _refresh_overlays(session):
    """An optional overlay failure does not undo a successfully loaded rig."""
    try:
        overlays = _overlay_module()
        if overlays is not None:
            overlays.update(session.info)
    except Exception as exc:
        return _status(
            session, _text("fighter_status_error", error=exc), error=True
        )
    return ""


class GENO_WB_OT_load_fighter(bpy.types.Operator):
    bl_idname = "geno_wb.load_fighter"
    bl_label = STRINGS["fighter_load_label"]
    bl_description = STRINGS["fighter_load_description"]
    bl_options = {"REGISTER"}

    def execute(self, context):
        session = api.session()
        try:
            session = _prepare_project(context)
            path = _resolve_art(context, session)
            # The outer import transaction also handles a server failure during
            # calibration, removing the newly imported rig and its dependencies.
            with rig.import_transaction(), pose.calibration_transaction():
                arm = rig.load_fighter(
                    blend=str(path) if path.suffix.lower() == ".blend" else "",
                    glb=str(path) if path.suffix.lower() == ".glb" else "",
                )
                pose.calibrate(arm, session)
                jointmap, cal = _preview_calibration(arm, session)
            _sync_mapping(context, arm, jointmap, cal)
            context.scene.geno_wb_fighter.art_path = str(path)
            _status(session, session.status)
        except Exception as exc:
            return _failure(self, api.session(), exc)
        overlay_error = _refresh_overlays(session)
        if overlay_error:
            self.report({"WARNING"}, overlay_error)
        return {"FINISHED"}


class GENO_WB_OT_calibrate(bpy.types.Operator):
    bl_idname = "geno_wb.calibrate"
    bl_label = STRINGS["fighter_calibrate_label"]
    bl_description = STRINGS["fighter_calibrate_description"]
    bl_options = {"REGISTER"}

    def execute(self, context):
        session = api.session()
        try:
            arm = active_armature(context, required=True)
            session = _prepare_project(context)
            with pose.calibration_transaction():
                pose.calibrate(arm, session)
                jointmap, cal = _preview_calibration(arm, session)
            _sync_mapping(context, arm, jointmap, cal)
            _status(session, session.status)
        except Exception as exc:
            return _failure(self, api.session(), exc)
        overlay_error = _refresh_overlays(session)
        if overlay_error:
            self.report({"WARNING"}, overlay_error)
        return {"FINISHED"}


class GENO_WB_OT_verify_pose(bpy.types.Operator):
    bl_idname = "geno_wb.verify_pose"
    bl_label = STRINGS["fighter_verify_label"]
    bl_description = STRINGS["fighter_verify_description"]
    bl_options = {"REGISTER"}

    def execute(self, context):
        session = api.session()
        try:
            arm = active_armature(context, required=True)
            calibration = pose.calibration_for(arm)
            if calibration is None:
                raise RuntimeError(STRINGS["fighter_verify_calibration"])
            if session.info is None:
                raise RuntimeError(STRINGS["fighter_no_frame"])
            result = pose.verify_pose(arm, session.info, calibration[0])
            context.scene.geno_wb_fighter.pose_error = result["max_err"]
            props = getattr(context.scene, "geno_wb", None)
            if props is not None:
                props.pose_error = result["max_err"]
            good = (
                result["ok"]
                and result["rot_err"] <= 1e-3
                and not result["missing"]
                and not result["skipped_mirrored"]
            )
            message = _text(
                "fighter_verify_result",
                result=STRINGS["fighter_ok"] if good else STRINGS["fighter_warning"],
                head=result["max_err"],
                rotation=result["rot_err"],
                joint=result["worst_joint"],
                count=result["n"],
                missing=len(result["missing"]),
                mirrored=len(result["skipped_mirrored"]),
            )
            message = _status(session, message)
            self.report({"INFO"} if good else {"WARNING"}, message)
            return {"FINISHED"}
        except Exception as exc:
            return _failure(self, session, exc)


_CLASSES = (
    GENO_WB_OT_load_fighter,
    GENO_WB_OT_calibrate,
    GENO_WB_OT_verify_pose,
)


def register():
    global _REGISTERED
    rig._require_main_thread()
    if _REGISTERED:
        return
    try:
        add_props(bpy.types.Scene)
        for cls in _CLASSES:
            bpy.utils.register_class(cls)
            _REGISTERED_CLASSES.append(cls)
        _REGISTERED = True
        _attach_hook(api.session())
        bpy.app.timers.register(_drain_pending, first_interval=0.1)
    except Exception:
        unregister()
        raise


def unregister():
    global _REGISTERED, _OWN_PROPS, _PENDING
    rig._require_main_thread()
    _REGISTERED = False
    if bpy.app.timers.is_registered(_drain_pending):
        bpy.app.timers.unregister(_drain_pending)
    for session in _HOOK_SESSIONS:
        hooks = getattr(session, "on_frame", None)
        if isinstance(hooks, list):
            while _frame_hook in hooks:
                hooks.remove(_frame_hook)
    _HOOK_SESSIONS.clear()
    with _PENDING_LOCK:
        _PENDING = None
    try:
        pose.release_preview()
    finally:
        while _REGISTERED_CLASSES:
            bpy.utils.unregister_class(_REGISTERED_CLASSES.pop())
        if _OWN_PROPS:
            del bpy.types.Scene.geno_wb_fighter
            bpy.utils.unregister_class(GenoWBFighterProps)
            _OWN_PROPS = False
