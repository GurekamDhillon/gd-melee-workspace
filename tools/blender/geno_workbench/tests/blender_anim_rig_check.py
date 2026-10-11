"""Blender-side check of the animation control rig and the hand-animation bake (run by test_anim_rig_blender.py).

    blender -b --factory-startup --python blender_anim_rig_check.py -- [--synthetic tall|stub | --blend FILE.blend] [--hand OUT.json]

Prints `ANIMRIG OK <variant> <n checks>` or fails with a traceback. --synthetic builds a small humanoid (tall: long bones along
the limbs like Goku; stub: 0.07 stubs pointing up with in-between joints and Euler rotation like Falcon's retail skeleton).
"""
import json
import math
import sys
import tempfile
from pathlib import Path

import bpy

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools.geno.artist.blender import anim_rig as R, hand_bake as HB, hand_layer as HL  # noqa: E402

CHECKS = 0


def check(cond, label):
    global CHECKS
    if not cond:
        raise AssertionError("FAIL: " + label)
    CHECKS += 1
    print("ok  ", label)


def build_synthetic(stub):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    data = bpy.data.armatures.new("Syn")
    arm = bpy.data.objects.new("SynExport", data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = data.edit_bones
    roles = {}

    def bone(name, head, tail, parent=None, role=None):
        b = eb.new(name)
        b.head = head
        b.tail = tail if not stub else (head[0], head[1], head[2] + .07)
        if parent:
            b.parent = eb[parent]
        if role:
            roles[name] = role
        return b

    bone("Base", (0, 0, 0), (0, 0, 9), role="translation")
    bone("Hips", (0, 0, 9), (0, 0, 10), "Base", "hips")
    bone("Spine", (0, 0, 10), (0, 0, 12), "Hips", "spine")
    bone("Chest", (0, 0, 12), (0, 0, 15), "Spine", "chest")
    bone("Neck", (0, 0, 15), (0, 0, 16), "Chest", "neck")
    bone("Head", (0, 0, 16), (0, 0, 18), "Neck", "head")
    for sx, s in ((1, "L"), (-1, "R")):
        bone(f"Clav{s}", (sx * .5, 0, 15), (sx * 2.5, 0, 15), "Chest", f"shoulder.{s}")
        bone(f"Arm1{s}", (sx * 2.5, 0, 15), (sx * 6, 0, 15), f"Clav{s}", f"upper_arm.{s}")
        if stub:
            bone(f"ArmJA{s}", (sx * 6, .1, 15), (sx * 6, .1, 15.07), f"Arm1{s}")
        bone(f"Arm2{s}", (sx * 6, .1, 15), (sx * 9.5, 0, 15), f"ArmJA{s}" if stub else f"Arm1{s}", f"lower_arm.{s}")
        bone(f"Hand{s}", (sx * 9.5, 0, 15), (sx * 11, 0, 15), f"Arm2{s}", f"hand.{s}")
        bone(f"Finger{s}", (sx * 11, 0, 15), (sx * 12, 0, 15), f"Hand{s}")
        bone(f"Leg1{s}", (sx * 1, 0, 9), (sx * 1, -.3, 5), "Hips", f"upper_leg.{s}")
        bone(f"Leg2{s}", (sx * 1, -.3, 5), (sx * 1, 0, 1.2), f"Leg1{s}", f"lower_leg.{s}")
        bone(f"Foot{s}", (sx * 1, 0, 1.2), (sx * 1, -1.5, .5), f"Leg2{s}", f"foot.{s}")
        bone(f"Toe{s}", (sx * 1, -1.5, .5), (sx * 1, -2.2, .3), f"Foot{s}", f"toe.{s}")
    bpy.ops.object.mode_set(mode="OBJECT")
    arm["geno"] = json.dumps({"fighter": "Syn", "roles": roles})
    for pb in arm.pose.bones:
        pb.rotation_mode = "XYZ" if stub else "QUATERNION"
    # a "converted clip" to layer over: hips bob + spine twist, 12 frames
    act = bpy.data.actions.new("Jab")
    act.use_fake_user = True
    arm.animation_data_create().action = act
    for f in range(12):
        pb = arm.pose.bones["Hips"]
        pb.location = (0, 0, .2 * math.sin(f / 11 * math.pi))
        pb.keyframe_insert("location", frame=f)
        sp = arm.pose.bones["Spine"]
        if stub:
            sp.rotation_euler = (0, 0, .3 * f / 11)
            sp.keyframe_insert("rotation_euler", frame=f)
        else:
            sp.rotation_quaternion = (math.cos(.15 * f / 11), 0, 0, math.sin(.15 * f / 11))
            sp.keyframe_insert("rotation_quaternion", frame=f)
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.location, pb.rotation_euler = (0, 0, 0), (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
    return arm


def snapshot(arm):
    return {b.name: (b.parent.name if b.parent else None, tuple(round(v, 5) for row in b.matrix_local for v in row), round(b.length, 5))
            for b in arm.data.bones}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    variant = argv[argv.index("--synthetic") + 1] if "--synthetic" in argv else None
    if variant:
        arm = build_synthetic(variant == "stub")
        label, row = variant, "Jab"
    else:
        bpy.ops.wm.open_mainfile(filepath=argv[argv.index("--blend") + 1])
        arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and "geno" in o)
        label = Path(argv[argv.index("--blend") + 1]).stem
        if arm.animation_data:
            arm.animation_data.action = None
        row = "Attack11" if bpy.data.actions.get("Attack11") else sorted(a.name for a in bpy.data.actions)[0]
    out = Path(argv[argv.index("--hand") + 1]) if "--hand" in argv else Path(tempfile.mkdtemp()) / "hand.json"
    before = snapshot(arm)

    ctrl = R.generate(arm)
    check(snapshot(arm) == before, "deform bone names, hierarchy, rest matrices and lengths unchanged by generate()")
    info = R.limbs_info(ctrl)
    check(sorted(info["limbs"]) == ["arm.L", "arm.R", "leg.L", "leg.R"], "IK for both arms and both legs")
    check(all(e["pole_error"] < 1e-2 for e in info["limbs"].values()), "pole angle calibrated: IK at rest leaves the chain at rest")
    check(all(e["roll_lifts"] for e in info["limbs"].values() if e["kind"] == "leg"), "positive foot roll lifts the heel")
    nfk = sum(1 for pb in ctrl.pose.bones if pb.name.startswith(R.FK))
    check(nfk == len(arm.data.bones), "one FK control per deform bone")
    check(R.FK + info["root"] in ctrl.pose.bones and R.FK + info["cog"] in ctrl.pose.bones, "root and COG controls exist")
    ev = R.evaluated(arm)
    worst = max(abs(x) for b in arm.data.bones for r in (ev.pose.bones[b.name].matrix - b.matrix_local) for x in r)
    check(worst < 1e-4, f"rig at rest reproduces the rest pose (worst {worst:.2e})")

    # FK drives the deform bones
    d = info["limbs"]["arm.L"]["deform"]
    fk = ctrl.pose.bones[R.FK + d[0]]
    fk.rotation_euler = (0, 0, .5)
    bpy.context.view_layer.update()
    tip = R.pose_matrix(arm, d[2]).translation
    check((tip - arm.data.bones[d[2]].matrix_local.translation).length > 1, "FK rotation of the upper arm moves the hand")
    fk.rotation_euler = (0, 0, 0)

    # IK drives the deform bones
    for lid in ("arm.L", "leg.R"):
        e = info["limbs"][lid]
        R.set_ik(ctrl, lid, 1.0)
        owner = ctrl.pose.bones[e["foot"] if e["kind"] == "leg" else e["target"]]
        owner.location = (0, 0, 1.2) if e["kind"] == "leg" else (0, -2.0, 1.0)
        bpy.context.view_layer.update()
        end = e["deform"][2]
        moved = R.pose_matrix(arm, end).translation - arm.data.bones[end].matrix_local.translation
        check(moved.length > .5, f"IK target moves the {lid} end bone (moved {moved.length:.2f})")
        owner.location = (0, 0, 0)
        R.set_ik(ctrl, lid, 0.0)

    # snap both ways with a non-trivial pose
    for lid, e in info["limbs"].items():
        ctrl.pose.bones[e["fk"][0]].rotation_euler = (.4, .1, .2)
        ctrl.pose.bones[e["fk"][1]].rotation_euler = (-.7 if e["kind"] == "leg" else 0, 0, -.5 if e["kind"] == "arm" else 0)
        bpy.context.view_layer.update()
        a = [R.pose_matrix(arm, x) for x in e["deform"]]
        R.auto_snap_on_switch(ctrl, lid, True)
        b = [R.pose_matrix(arm, x) for x in e["deform"]]
        err = max((x.translation - y.translation).length for x, y in zip(a, b))
        check(err < 2e-3, f"snap FK->IK keeps {lid} in place (err {err:.5f})")
        keep = ctrl.pose.bones[e["fk"][0]].rotation_euler.copy()
        ctrl.pose.bones[e["fk"][0]].rotation_euler = (1.2, 0, 0)
        bpy.context.view_layer.update()
        c = [R.pose_matrix(arm, x) for x in e["deform"]]
        ctrl.pose.bones[e["fk"][0]].rotation_euler = keep
        check(max((x.translation - y.translation).length for x, y in zip(b, c)) < 2e-3, f"in IK mode the FK controls of {lid} no longer drive it (the switch is live)")
        ctrl.pose.bones[e["foot"] if e["kind"] == "leg" else e["target"]].location.z += .6
        bpy.context.view_layer.update()
        a = [R.pose_matrix(arm, x) for x in e["deform"]]
        R.auto_snap_on_switch(ctrl, lid, False)
        b = [R.pose_matrix(arm, x) for x in e["deform"]]
        err = max((x.translation - y.translation).length for x, y in zip(a, b))
        check(err < 2e-3, f"snap IK->FK keeps {lid} in place (err {err:.5f})")
        for pb in ctrl.pose.bones:
            pb.location, pb.rotation_euler = (0, 0, 0), (0, 0, 0)

    # re-generation: one control rig, no duplicate constraints
    n_con = sum(len(pb.constraints) for pb in arm.pose.bones)
    ctrl = R.generate(arm)
    check(len([o for o in bpy.data.objects if o.get("geno_deform") == arm.name]) == 1, "re-generate leaves exactly one control rig")
    check(sum(len(pb.constraints) for pb in arm.pose.bones) == n_con, "re-generate does not stack constraints")
    check(snapshot(arm) == before, "deform armature still unchanged after re-generate")
    info = R.limbs_info(ctrl)

    # hand clip: layer over the converted row (when there is one), edit with FK, bake, check, save, reload
    mode = "layer" if HB.converted_action(row) else "replace"
    act = HB.new_clip(ctrl, row, mode)
    n = HB.frame_count(act)
    check(n >= 2, f"hand action seeded ({mode}, {n} frames)")
    e = info["limbs"]["arm.R"]
    up = ctrl.pose.bones[e["fk"][0]]
    for f, v in ((0, 0.0), (n // 2, .6), (n - 1, 0.0)):
        bpy.context.scene.frame_set(f)
        up.rotation_euler = (0, 0, v)
        up.keyframe_insert("rotation_euler", frame=f)
    clip, rep = HB.bake_clip(ctrl, act, row, mode)
    check(rep["max_pos_err"] < HB.POS_TOL and rep["max_rot_err_rad"] < HB.ROT_TOL,
          f"baked FK keys reproduce the rig (pos {rep['max_pos_err']:.2e}, rot {rep['max_rot_err_rad']:.2e})")
    check(rep["max_replay_err_rad"] < HB.REPLAY_TOL, f"stored delta applied to the base reproduces the hand pose ({rep['max_replay_err_rad']:.2e} rad)")
    check(e["deform"][0] in clip["bones"], "the edited bone is in the hand clip")
    if mode == "layer":
        check(len(clip["bones"]) <= 4, f"only the edited chain is stored, not the seed ({sorted(clip['bones'])})")
    HB.save_clip(out, "Syn", row, clip)
    doc = HL.load(out)
    check(row in doc["clips"], "hand file written and valid")
    again = HB.load_clip(ctrl, doc, row)
    clip2, rep2 = HB.bake_clip(ctrl, again, row, mode)
    q1 = clip["bones"][e["deform"][0]]["rot"]
    q2 = clip2["bones"][e["deform"][0]]["rot"]
    check(max(abs(a - b) for x, y in zip(q1, q2) for a, b in zip(x, y)) < 1e-4, "reload from the hand file bakes back to the same delta")
    check(arm.name + "_bake" not in bpy.data.objects, "no bake copy left behind")
    print(f"ANIMRIG OK {label} {CHECKS}")


try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)
