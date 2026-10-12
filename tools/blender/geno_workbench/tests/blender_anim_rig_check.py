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
from mathutils import Matrix

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


def build_synthetic(stub, bare=False):
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
    if bare:       # a fighter whose role map has legs, arms and hips only: no spine, neck, head or clavicles
        roles = {b: r for b, r in roles.items() if r.split(".")[0] not in ("spine", "chest", "neck", "head", "shoulder")}
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



def W(ctrl, name):
    return R.pose_matrix(ctrl, name)


def mdiff(a, b):
    return max(abs(x - y) for r1, r2 in zip(a, b) for x, y in zip(r1, r2))


def reset_pose(ctrl):
    for pb in ctrl.pose.bones:
        pb.location, pb.rotation_euler = (0, 0, 0), (0, 0, 0)
    for pb in ctrl.pose.bones:
        for key, dflt in (("ik", 0.0), (R.LOOK_PROP, 0.0), (R.SHOULDER_PROP, R.SHOULDER_DEFAULT), (R.SPINE_PROP, 1.0)):
            if key in pb.keys():
                pb[key] = dflt
    for lid, e in R.limbs_info(ctrl)["limbs"].items():
        ctrl.pose.bones[e["switch"]][R.SPACE_PROP] = e["space_default"]
    R.tag_switch(ctrl)


def angle_from_rest(arm, bone):
    rest = arm.data.bones[bone].matrix_local.to_3x3()
    return (R.pose_matrix(arm, bone).to_3x3() @ rest.inverted()).to_quaternion().angle


def space_name(ctrl, entry):
    R.tag_switch(ctrl)
    return entry["spaces"][R.get_space(ctrl, entry)]


def rig_v2_checks(arm, ctrl, info):
    """Spaces, spine handle, look-at and clavicle follow (rig v2)."""
    roles = R.roles_of(arm)
    V = R.Vector
    check(bool(ctrl.get("geno_report")) and "spaces" in ctrl["geno_report"], "generate() stored a report of what the fighter got")
    reset_pose(ctrl)
    bpy.context.view_layer.update()
    ev = R.evaluated(arm)
    worst = max(abs(x) for b in arm.data.bones for r in (ev.pose.bones[b.name].matrix - b.matrix_local) for x in r)
    check(worst < 1e-4, f"rig v2 at rest (all sliders at default) still reproduces the rest pose (worst {worst:.2e})")

    # ---- spaces: no world jump on any switch, and the control then follows its space
    cog, chest, head = (ctrl.pose.bones.get(R.FK + roles[r]) if r in roles else None for r in ("hips", "chest", "head"))
    for lid, e in info["limbs"].items():
        reset_pose(ctrl)
        R.set_ik(ctrl, lid, 1.0)
        owner = ctrl.pose.bones[e["space_ctl"][0]]
        owner.location = (0.4, -1.0, 0.7) if e["kind"] == "arm" else (0.5, -0.8, 0.9)
        bpy.context.view_layer.update()
        if cog is not None:
            cog.location, cog.rotation_euler = (0.3, 0.2, -0.5), (0.05, 0.1, 0.15)
        if chest is not None:
            chest.rotation_euler = (0.05, -0.1, 0.3)
        if head is not None:
            head.rotation_euler = (0.0, 0.1, 0.25)
        bpy.context.view_layer.update()
        names = e["spaces"]
        check(len(names) >= 2 and "world" in names and "root" in names, f"{lid} offers spaces {'/'.join(names)}")
        worst_jump, worst_deform = 0.0, 0.0
        order = [n for n in names if n != names[R.get_space(ctrl, e)]] + [names[e["space_default"]]]
        for sname in order:
            before = {n: W(ctrl, n) for n in e["space_ctl"]}
            deform0 = [W(arm, d) for d in e["deform"]]
            R.set_space(ctrl, lid, sname)
            assert space_name(ctrl, e) == sname, (lid, sname)
            worst_jump = max(worst_jump, max(mdiff(before[n], W(ctrl, n)) for n in e["space_ctl"]))
            worst_deform = max(worst_deform, max((a.translation - W(arm, d).translation).length for a, d in zip(deform0, e["deform"])))
        check(worst_jump < 0.001, f"{lid}: switching through every space ({' > '.join(order)}) leaves the IK target and pole in place (world jump {worst_jump:.2e})")
        check(worst_deform < 0.001, f"{lid}: the deform limb does not move either ({worst_deform:.2e})")
        # the control now really follows the space it is in (and not the others)
        moved = {}
        for sname, bone in zip(names, e["space_bones"]):
            if bone is None:
                continue
            R.set_space(ctrl, lid, sname)
            t0 = W(ctrl, e["space_ctl"][0]).translation.copy()
            pb = ctrl.pose.bones[bone]
            keep = pb.location.copy()
            pb.location = keep + V((1.5, 1.0, 0.7))
            bpy.context.view_layer.update()
            moved[sname] = (W(ctrl, e["space_ctl"][0]).translation - t0).length
            pb.location = keep
        R.set_space(ctrl, lid, "world")
        t0 = W(ctrl, e["space_ctl"][0]).translation.copy()
        for bone in e["space_bones"]:
            if bone:
                ctrl.pose.bones[bone].location = (2, 2, 2)
        bpy.context.view_layer.update()
        stay = (W(ctrl, e["space_ctl"][0]).translation - t0).length
        check(stay < 1e-4, f"{lid}: in world space the control ignores root/cog/chest/head motion ({stay:.2e})")
        check(all(v > 0.5 for v in moved.values()), f"{lid}: every other space carries the control when its bone moves ({', '.join(f'{k} {v:.2f}' for k, v in moved.items())})")
        reset_pose(ctrl)
    # keyable: the space value and stepped keys
    lid0 = next(iter(info["limbs"]))
    e0 = info["limbs"][lid0]
    ctrl.animation_data_create()
    act = bpy.data.actions.new("spacekeys")
    ctrl.animation_data.action = act
    bpy.context.scene.frame_set(1)
    R.key_space(ctrl, e0)
    bpy.context.scene.frame_set(10)
    R.set_space(ctrl, lid0, e0["spaces"][-1], key=True)
    path = f'pose.bones["{e0["switch"]}"]["{R.SPACE_PROP}"]'
    fcs = [fc for fc in R._fcurves(act) if fc.data_path == path]
    check(bool(fcs) and len(fcs[0].keyframe_points) == 2 and all(kp.interpolation == "CONSTANT" for kp in fcs[0].keyframe_points),
          "the space value is keyable (two stepped keys)")
    bpy.context.scene.frame_set(1)
    check(space_name(ctrl, e0) == e0["spaces"][e0["space_default"]], "frame 1 plays back the first key's space")
    bpy.context.scene.frame_set(10)
    check(space_name(ctrl, e0) == e0["spaces"][-1], "frame 10 plays back the second key's space")
    ctrl.animation_data.action = None
    bpy.data.actions.remove(act)
    bpy.context.scene.frame_set(1)
    reset_pose(ctrl)

    # ---- spine handle
    if "spine" in info:
        sp = info["spine"]
        h = ctrl.pose.bones[sp["handle"]]
        h.rotation_euler = (0, 0, 0.6)
        bpy.context.view_layer.update()
        top = sp["bones"][-1]
        ang = angle_from_rest(arm, top)
        moves = [angle_from_rest(arm, b) for b in sp["bones"]]
        check(abs(ang - 0.6) < 0.15 and all(m > 0.05 for m in moves),
              f"chest handle turns the chest ~0.6 rad ({ang:.3f}) and every spine bone takes a share ({', '.join(f'{m:.2f}' for m in moves)})")
        h[R.SPINE_PROP] = 0.0
        R.tag_switch(ctrl)
        check(angle_from_rest(arm, top) < 1e-4, "spine slider 0 switches the chest handle off")
        h[R.SPINE_PROP] = 1.0
        h.rotation_euler = (0, 0, 0)
        ctrl.pose.bones[R.FK + sp["bones"][0]].rotation_euler = (0.3, 0, 0)
        R.tag_switch(ctrl)
        check(angle_from_rest(arm, top) > 0.1, "FK spine controls still drive the spine")
        reset_pose(ctrl)
    else:
        print("note: no spine handle on this fighter")

    # ---- look-at
    if "look" in info:
        lk = info["look"]
        t = ctrl.pose.bones[lk["target"]]
        head_bone = lk["bones"][-1]
        fwd = V(info["facing"])
        lat = V((0, 0, 1)).cross(fwd).normalized()
        axis, sign, _ = R._nearest_axis(arm.data.bones[head_bone].matrix_local, fwd)
        t.location = lat * 7.0 + V((0, 0, 2.0))
        t[R.LOOK_PROP] = 0.0
        R.tag_switch(ctrl)
        check(angle_from_rest(arm, head_bone) < 1e-4, "look slider 0: the head ignores the target")
        t[R.LOOK_PROP] = 1.0
        R.tag_switch(ctrl)
        hm = W(arm, head_bone)
        gaze = hm.to_3x3().col[axis].normalized() * sign
        want = (W(ctrl, lk["target"]).translation - hm.translation).normalized()
        check(gaze.angle(want) < math.radians(4), f"look-at 1.0: the head faces the target (off by {math.degrees(gaze.angle(want)):.2f} deg)")
        full = angle_from_rest(arm, head_bone)
        if len(lk["bones"]) > 1:
            na = angle_from_rest(arm, lk["bones"][0])
            check(0.02 < na < full, f"the neck takes part ({na:.2f} rad) but less than the head ({full:.2f})")
        t[R.LOOK_PROP] = 0.5
        R.tag_switch(ctrl)
        half = angle_from_rest(arm, head_bone)
        check(0.1 < half < full, f"look-at 0.5 turns the head part of the way ({half:.2f} of {full:.2f} rad)")
        reset_pose(ctrl)
    else:
        print("note: no look-at on this fighter")

    # ---- clavicle follow: an overhead IK hand lifts the clavicle and the hand reaches higher
    for lid, e in info["limbs"].items():
        if "shoulder" not in e:
            continue
        sh = e["shoulder"]
        reset_pose(ctrl)
        R.set_ik(ctrl, lid, 1.0)
        top_pos = arm.data.bones[e["deform"][0]].head_local
        rest_hand = arm.data.bones[e["deform"][2]].head_local
        reach = (rest_hand - top_pos).length
        goal = top_pos + V((0, 0, reach * 1.1))
        tgt = ctrl.pose.bones[e["target"]]
        res = {}
        for val in (0.0, R.SHOULDER_DEFAULT):
            ctrl.pose.bones[e["switch"]][R.SHOULDER_PROP] = val
            tgt.location = goal - rest_hand
            R.tag_switch(ctrl)
            res[val] = (angle_from_rest(arm, sh["deform"]), (R.evaluated(ctrl).pose.bones[e["ikm"][1]].tail - W(ctrl, e["target"]).translation).length)
        check(res[0.0][0] < 1e-4, f"{lid}: shoulder slider 0 leaves the clavicle alone")
        check(res[R.SHOULDER_DEFAULT][0] > 0.03, f"{lid}: an overhead hand raises the clavicle ({res[R.SHOULDER_DEFAULT][0]:.3f} rad)")
        check(res[R.SHOULDER_DEFAULT][1] < res[0.0][1] - 0.02, f"{lid}: with the clavicle follow the arm reaches closer to the overhead target ({res[R.SHOULDER_DEFAULT][1]:.3f} vs {res[0.0][1]:.3f} short)")
        R.set_ik(ctrl, lid, 0.0)
        check(angle_from_rest(arm, sh["deform"]) < 1e-4, f"{lid}: in FK mode the clavicle does not follow the hidden IK hand")
        # switching modes keeps the clavicle and arm where they are
        R.set_ik(ctrl, lid, 1.0)
        tol = 0.012 * e["total"]
        names = [sh["deform"]] + e["deform"]
        before = [W(arm, d) for d in names]
        R.auto_snap_on_switch(ctrl, lid, False)
        after = [W(arm, d) for d in names]
        err = max((a.translation - b.translation).length for a, b in zip(before, after))
        check(err < tol, f"{lid}: IK->FK switch keeps clavicle and arm in place (err {err:.4f})")
        R.auto_snap_on_switch(ctrl, lid, True)
        after2 = [W(arm, d) for d in names]
        err = max((a.translation - b.translation).length for a, b in zip(after, after2))
        check(err < tol, f"{lid}: FK->IK switch keeps clavicle and arm in place (err {err:.4f})")
        reset_pose(ctrl)
    if not any("shoulder" in e for e in info["limbs"].values()):
        print("note: no clavicle follow on this fighter")
    reset_pose(ctrl)



def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    variant = argv[argv.index("--synthetic") + 1] if "--synthetic" in argv else None
    if variant:
        arm = build_synthetic(variant == "stub", bare=variant == "bare")
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

    # snap both ways. The bent pose comes from the IK itself (a pulled-in target), so it bends the way the limb really bends.
    for lid, e in info["limbs"].items():
        tol = 0.012 * e["total"]
        owner = ctrl.pose.bones[e["foot"] if e["kind"] == "leg" else e["target"]]
        R.set_ik(ctrl, lid, 1.0)
        owner.location = (0, 0, 0)
        bpy.context.view_layer.update()
        end = R.pose_matrix(ctrl, e["target"]).translation
        top = R.pose_matrix(ctrl, e["ikm"][0]).translation
        owner.matrix = Matrix.Translation((top - end) * .3) @ owner.matrix
        bpy.context.view_layer.update()
        a = [R.pose_matrix(arm, x) for x in e["deform"]]
        R.auto_snap_on_switch(ctrl, lid, False)                                 # IK -> FK on a bent pose
        b = [R.pose_matrix(arm, x) for x in e["deform"]]
        err = max((x.translation - y.translation).length for x, y in zip(a, b))
        check(err < tol, f"snap IK->FK keeps {lid} in place (err {err:.5f})")
        for pb in ctrl.pose.bones:
            if not pb.name.startswith(R.FK):
                pb.location, pb.rotation_euler = (0, 0, 0), (0, 0, 0)
        ctrl.pose.bones[e["fk"][0]].rotation_euler = (.3, .1, .2)               # swing/twist the upper limb in FK, keep the bend
        bpy.context.view_layer.update()
        a = [R.pose_matrix(arm, x) for x in e["deform"]]
        R.auto_snap_on_switch(ctrl, lid, True)                                  # FK -> IK
        b = [R.pose_matrix(arm, x) for x in e["deform"]]
        err = max((x.translation - y.translation).length for x, y in zip(a, b))
        check(err < tol, f"snap FK->IK keeps {lid} in place (err {err:.5f})")
        ctrl.pose.bones[e["fk"][0]].rotation_euler = (1.2, 0, 0)
        bpy.context.view_layer.update()
        c = [R.pose_matrix(arm, x) for x in e["deform"]]
        check(max((x.translation - y.translation).length for x, y in zip(b, c)) < tol, f"in IK mode the FK controls of {lid} no longer drive it (the switch is live)")
        R.set_ik(ctrl, lid, 0.0)
        for pb in ctrl.pose.bones:
            pb.location, pb.rotation_euler = (0, 0, 0), (0, 0, 0)

    rig_v2_checks(arm, ctrl, info)

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
    # FK -> IK -> FK over the whole clip with the clavicle follow and the spaces in play: the arm must not move
    sw = info["limbs"]["arm.L"]
    chain = ([sw["shoulder"]["deform"]] if "shoulder" in sw else []) + sw["deform"]

    def arm_track():
        out = []
        for f in range(n):
            bpy.context.scene.frame_set(f)
            out.append([R.pose_matrix(arm, d).translation.copy() for d in chain])
        return out
    base = arm_track()
    for to_ik in (True, False):
        HB.limb_switch(ctrl, "arm.L", to_ik)
        now = arm_track()
        err = max((a - b).length for x, y in zip(base, now) for a, b in zip(x[-3:], y[-3:]))
        check(err < 0.02 * sw["total"], f"limb_switch {'FK->IK' if to_ik else 'IK->FK'} over {n} frames keeps the arm where it was "
              f"(worst {err:.4f}, {100 * err / sw['total']:.1f}% of the limb)")
        if "shoulder" in sw:
            cerr = max((x[0] - y[0]).length for x, y in zip(base, now))
            check(cerr < 1e-3, f"...and the clavicle exactly where it was ({cerr:.2e})")
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


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
