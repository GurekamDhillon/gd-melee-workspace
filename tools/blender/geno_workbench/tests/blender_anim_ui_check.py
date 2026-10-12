"""Blender-side check of the Geno > Animate operators (run by test_anim_rig_blender.py).

    blender -b --factory-startup --python blender_anim_ui_check.py -- [--synthetic tall|stub | --blend FILE.blend]

Regression: **Generate rig** failed on Falcon with "Unable to execute 'Toggle Pose Mode', error changing modes" when run as an operator
(generate() called as a function worked). Runs the real operators from object mode, from pose mode, from edit mode, with the deform
armature hidden, and twice in a row, and checks the result, the control rig's mode and the space/snap operators.
Prints `ANIMUI OK <label> <n checks>`.
"""
import importlib.util
import sys
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("rigcheck", HERE / "blender_anim_rig_check.py")
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)
sys.path.insert(0, str(HERE.parent))
import anim_ui  # noqa: E402

R = rc.R
CHECKS = 0


def check(cond, label):
    global CHECKS
    if not cond:
        raise AssertionError("FAIL: " + label)
    CHECKS += 1
    print("ok  ", label)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if "--synthetic" in argv:
        variant = argv[argv.index("--synthetic") + 1]
        arm = rc.build_synthetic(variant == "stub", bare=variant == "bare")
        label = "synthetic"
    else:
        bpy.ops.wm.open_mainfile(filepath=argv[argv.index("--blend") + 1])
        arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and "geno" in o)
        label = Path(argv[argv.index("--blend") + 1]).stem
    anim_ui.register()
    scene = bpy.context.scene

    def select(ob):
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob

    for case in ("object mode", "pose mode", "edit mode", "deform armature hidden", "again, control rig selected in pose mode"):
        ctrl = R.ctrl_object(arm)
        select(arm)
        if case == "pose mode":
            bpy.ops.object.mode_set(mode="POSE")
        elif case == "edit mode":
            bpy.ops.object.mode_set(mode="EDIT")
        elif case == "deform armature hidden":
            arm.hide_set(True)
            bpy.context.view_layer.objects.active = arm
        elif case.startswith("again"):
            select(R.ctrl_object(arm))
            bpy.ops.object.mode_set(mode="POSE")
        result = bpy.ops.geno_anim.generate()
        ctrl = R.ctrl_object(arm)
        check(result == {"FINISHED"} and ctrl is not None and ctrl.mode == "OBJECT",
              f"Generate rig operator from {case}: {scene.geno_anim.status[:90]}")
        if case == "deform armature hidden":
            arm.hide_set(False)
        bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.mode != "OBJECT" else None
    check("IK limbs" in scene.geno_anim.status, "the status line says what was built")

    # the other operators, on the control rig as the panel runs them
    select(ctrl)
    info = R.limbs_info(ctrl)
    lid = next(iter(info["limbs"]))
    e = info["limbs"][lid]
    other = e["spaces"][-1]
    before = R.pose_matrix(ctrl, e["space_ctl"][0])
    check(bpy.ops.geno_anim.space(limb=lid, space=other) == {"FINISHED"} and e["spaces"][R.get_space(ctrl, e)] == other,
          f"Switch space operator moves the limb to {other}")
    check(rc.mdiff(before, R.pose_matrix(ctrl, e["space_ctl"][0])) < 1e-3, "...and the control did not move in the world")
    try:                       # a script sees an operator's ERROR report as RuntimeError
        bpy.ops.geno_anim.space(limb=lid, space="nowhere")
        refused = False
    except RuntimeError as exc:
        refused = "no space" in str(exc)
    check(refused and e["spaces"][R.get_space(ctrl, e)] == other, "an unknown space is refused with a message and changes nothing")
    check(bpy.ops.geno_anim.snap(limb=lid, to_ik=True) == {"FINISHED"}, "to IK operator")
    check(bpy.ops.geno_anim.snap(limb=lid, to_ik=False) == {"FINISHED"}, "to FK operator")
    print(f"ANIMUI OK {label} {CHECKS}")


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)
