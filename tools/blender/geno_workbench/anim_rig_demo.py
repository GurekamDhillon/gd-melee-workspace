"""Author a short example hand clip on the control rig, headless: a jab that reaches further and twists the torso.

    blender -b COPY_OF_FIGHTER.blend --python tools/blender/geno_workbench/anim_rig_demo.py -- \
        --row Attack11 [--side auto|L|R] --hand OUT/hand.json [--reach 3.0] [--save-blend OUT/rig.blend] [--mode layer|replace]

It does what an animator does with the panel: Generate rig, Start clip (Layer over the converted row), switch the arm to IK on every
frame (the converted motion is kept as IK keys), pull the IK hand forward with a smooth pulse, twist the spine and turn the head
with FK keys, then Bake + save into the hand file. Use a COPY of the fighter's .blend, never the one open in the artist's Blender.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.geno.artist.blender import anim_rig as R, hand_bake as HB  # noqa: E402


def arg(name, default=None):
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return argv[argv.index(name) + 1] if name in argv else default


def pulse(f, n, a=.2, b=.7):
    t = (f / max(n - 1, 1) - a) / (b - a)
    return 0.0 if t <= 0 or t >= 1 else math.sin(math.pi * t) ** 2


def main():
    row, side, mode = arg("--row", "Attack11"), arg("--side", "auto"), arg("--mode", "layer")
    reach = float(arg("--reach", "3.0"))
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and "geno" in o)
    if arm.animation_data:
        arm.animation_data.action = None
    ctrl = R.generate(arm)
    info = R.limbs_info(ctrl)
    act = HB.new_clip(ctrl, row, mode)
    n = HB.frame_count(act)
    facing = Vector(info["facing"])
    if side == "auto":                                                # the punching hand is the one that gets furthest in front of the hips
        far = {}
        for s_ in ("L", "R"):
            end = info["limbs"][f"arm.{s_}"]["deform"][2]
            far[s_] = max((R.pose_matrix(arm, end).translation).dot(facing) for f in range(n) if bpy.context.scene.frame_set(f) is None)
        side = max(far, key=far.get)
        print("DEMO side", side, far)
    limb = f"arm.{side}"
    e = info["limbs"][limb]
    HB.limb_switch(ctrl, limb, True)                                  # converted motion -> IK keys on every frame
    target = ctrl.pose.bones[e["target"]]
    for f in range(n):                                                # push the hand forward with a smooth pulse
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()
        w = pulse(f, n)
        if w:
            target.location = target.location + facing * reach * w + Vector((0, 0, .3 * w))
            target.keyframe_insert("location", frame=f, group=e["target"])
    spine = next(b for b in R.roles_of(arm).items() if b[0] == "spine")[1]
    head = R.roles_of(arm).get("head")
    for bone, axis, amount in ((spine, 2, .5), (head, 2, -.3)):      # FK twist of the torso, head turns the other way
        if not bone:
            continue
        pb = ctrl.pose.bones[R.FK + bone]
        for f in range(n):
            if not pulse(f, n):
                continue
            bpy.context.scene.frame_set(f)
            bpy.context.view_layer.update()
            pb.rotation_euler[axis] += amount * pulse(f, n)
            pb.keyframe_insert("rotation_euler", index=axis, frame=f, group=pb.name)
    bpy.context.scene.frame_set(0)
    clip, rep = HB.bake_clip(ctrl, act, row, mode, note=f"example: {row} reaches {reach} further with the {side} hand (IK), torso twist (FK)")
    out = Path(arg("--hand"))
    HB.save_clip(out, arm.name.replace("Export", ""), row, clip)
    print("DEMO", json.dumps({k: v for k, v in rep.items() if k != "moved_bones"}), "bones", rep["moved_bones"][:12])
    if arg("--save-blend"):
        bpy.ops.wm.save_as_mainfile(filepath=str(Path(arg("--save-blend"))), copy=True)


main()
