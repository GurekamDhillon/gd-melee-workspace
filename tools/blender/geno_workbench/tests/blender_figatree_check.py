"""Executed by background Blender; synthetic fixtures only."""
import importlib.util
import json
from pathlib import Path
import sys

import bpy
from mathutils import Matrix, Quaternion

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path[:0] = [str(ROOT), str(HERE), str(HERE.parent)]
work = Path(sys.argv[sys.argv.index("--") + 1])

from figatree_fixtures import F, archive, bank, model, stream
import figatree_decode as D
import figatree_import as I
import wbspace as W

assert importlib.util.find_spec("operators_figatree") is not None, "Blender figatree action writer is missing"
from figatree_actions import create_actions


def bind(arm, action):
    ad = arm.animation_data_create()
    ad.action = action
    if getattr(action, "slots", None):
        ad.action_slot = action.slots[0]


def at(frame):
    whole = int(frame)
    bpy.context.scene.frame_set(whole, subframe=frame-whole)
    bpy.context.view_layer.update()


def curves(action):
    if getattr(action, "slots", None):
        return list(action.layers[0].strips[0].channelbag(action.slots[0]).fcurves)
    return list(action.fcurves)


def close(a, b, tolerance=2e-4):
    error = max(abs(a[r][c]-b[r][c]) for r in range(4) for c in range(4))
    assert error < tolerance, (error, a, b)
    return error


rest = D.read_model(model([(None, (.15, .2, -.1), (1, 2, 3), (1, 1, 1), 8),
                          (0, (.2, -.1, .3), (0, 2, 0), (1, 1, 1), 8)]))
plan = {"joints": [{"index": 0, "name": "engine_root", "parent": None},
                   {"index": 1, "name": "engine_foot", "parent": None}]}
aliases = {"engine_root": "Root", "engine_foot": "Foot"}
data = bpy.data.armatures.new("SyntheticRig")
arm = bpy.data.objects.new("SyntheticRig", data)
bpy.context.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
world_rest = I.world_matrices(rest)
for i, name in enumerate(("Root", "Foot")):
    bone = data.edit_bones.new(name)
    bone.tail = (0, .5, 0)
    bone.matrix = Matrix(W.mul(W.C4, world_rest[i]))
    bone.length = .5
    if i:
        bone.parent = data.edit_bones["Root"]
bpy.ops.object.mode_set(mode="OBJECT")
arm.pose.bones["Root"].rotation_mode = "XYZ"
arm.pose.bones["Foot"].rotation_mode = "QUATERNION"

linear = []
for ji, joint in enumerate(rest):
    tracks = []
    for prop, kinds in (("rotation", (1, 2, 3)), ("translation", (5, 6, 7)), ("scale", (8, 9, 10))):
        for axis, kind in enumerate(kinds):
            v = getattr(joint, prop)[axis]
            delta = (.08 if prop == "rotation" else .2) if axis == 0 else 0
            body, fv, fs, _ = F.encode_mixed_spline([(0, v, 0), (4, v+delta, 0)], [2, 2], 0, 0)
            tracks.append((kind, body, fv, fs))
    linear.append(tracks)
roundtrip_raw = archive(linear, name="PlySynthetic_ACTION_Roundtrip_figatree")
stretch_raw = archive([[], [(8, stream([(4, 1, 0, 2), (4, 2, .25, 2), (4, 1.5, 0, None)]), 0, 0)]],
                      name="PlySynthetic_ACTION_Stretch_figatree")
reset_raw = archive([[], []], name="PlySynthetic_ACTION_Reset_figatree")
step_raw = archive([[(5, stream([(1, 1, None, 2), (1, 4, None, None)]), 0, 0)], []],
                   name="PlySynthetic_ACTION_Step_figatree")
clips = D.read_bank(bank(roundtrip_raw, stretch_raw, reset_raw, step_raw))
prior = bpy.data.actions.new("Prior")
bind(arm, prior)
arm.pose.bones["Foot"].scale = (1.25, 1, 1)
arm.pose.bones["Foot"].keyframe_insert("scale", frame=7)
at(7.25)
before = arm.pose.bones["Foot"].matrix_basis.copy()
actions = create_actions(arm, clips, rest, plan, aliases=aliases)
assert arm.animation_data.action == prior
assert bpy.context.scene.frame_current == 7 and abs(bpy.context.scene.frame_subframe-.25) < 1e-6
close(arm.pose.bones["Foot"].matrix_basis, before)
assert [action.name for action in actions] == ["Roundtrip", "Stretch", "Reset", "Step"]
assert all(action.use_fake_user for action in actions)
assert all(abs(action.frame_range[0]-1) < 1e-6 and abs(action.frame_range[1]-5) < 1e-6 for action in actions)
assert any(c.data_path.endswith("rotation_quaternion") for c in curves(actions[0]))

sampler = I.PoseSampler(rest, plan, {b.name: tuple(tuple(row) for row in b.matrix_local) for b in arm.data.bones},
                        {b.name: b.parent.name if b.parent else None for b in arm.data.bones}, aliases=aliases)
worst = 0
for clip, action in zip(clips, actions):
    bind(arm, action)
    for f in (0, .125, .25, .5, 1, 1.75, 1.999, 2, 2.5, 3.25, 4):
        at(f+1)
        for name, basis in sampler.bases(clip, f).items():
            worst = max(worst, close(arm.pose.bones[name].matrix_basis, Matrix(basis)))
bind(arm, actions[1])
at(3)
assert arm.pose.bones["Foot"].scale.x > 1.5
bind(arm, actions[2])
at(3)
assert tuple(arm.pose.bones["Foot"].scale) == (1, 1, 1)

# Decode/map every clip before creating any action; failure leaves the rig intact.
bad = D.read_bank(archive([[(4, *F.encode_const(1)[:3])], []]))[0]
count = len(bpy.data.actions)
try:
    create_actions(arm, [clips[0], bad], rest, plan, aliases=aliases)
except ValueError:
    pass
else:
    raise AssertionError("unsupported path track was accepted")
assert len(bpy.data.actions) == count
assert arm.animation_data.action == actions[2]

# Existing Blender glTF exporter -> existing figatree encoder, no changes to either.
bind(arm, actions[0])
for obj in bpy.context.selected_objects:
    obj.select_set(obj == arm)
bpy.context.scene.frame_start, bpy.context.scene.frame_end = 1, 5
glb = work / "synthetic-roundtrip.glb"
bpy.ops.export_scene.gltf(filepath=str(glb), export_format="GLB", use_selection=True, export_extras=False,
                         export_yup=True, export_apply=False, export_animations=True, export_animation_mode="ACTIVE_ACTIONS",
                         export_force_sampling=True, export_optimize_animation_size=False, export_frame_range=True,
                         export_skins=False, export_leaf_bone=False, export_def_bones=False, export_reset_pose_bones=False,
                         export_anim_slide_to_zero=False)
from tools.geno.artist.blender.hand_bake import read_glb
arrays = read_glb(glb)
rebuilt = []
for ji, name in enumerate(("Root", "Foot")):
    rows = arrays[name]
    quats = rows["rotation"]
    eulers = []
    previous = None
    for q in quats:
        quat = Quaternion((q[3], q[0], q[1], q[2]))
        euler = quat.to_euler("XYZ", previous) if previous is not None else quat.to_euler("XYZ")
        eulers.append(tuple(euler))
        previous = euler
    tracks = []
    for values, kinds in ((eulers, (1, 2, 3)), (rows["translation"], (5, 6, 7)), (rows["scale"], (8, 9, 10))):
        assert len(values) == 5, (name, len(values))
        for axis, kind in enumerate(kinds):
            body, fv, fs, _ = F.encode_mixed_spline([(f, float(row[axis]), 0) for f, row in enumerate(values)], [2]*5, 0, 0)
            tracks.append((kind, body, fv, fs))
    rebuilt.append(tracks)
exported = D.read_bank(archive(rebuilt))[0]
curve_error = 0
for source_joint, result_joint in zip(clips[0].joints, exported.joints):
    for source, result in zip(source_joint, result_joint):
        for f in (0, .25, .5, 1, 1.5, 2, 2.75, 3, 4):
            curve_error = max(curve_error, abs(source.evaluate(f)-result.evaluate(f)))
assert curve_error < 3e-4, curve_error


def simple_rig(name, joints, *, connected=False, extra_parent=False):
    """Bind a synthetic source exactly, with an optional Blender-only parent."""
    for obj in bpy.context.selected_objects:
        obj.select_set(False)
    rig_data = bpy.data.armatures.new(name)
    rig = bpy.data.objects.new(name, rig_data)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    if extra_parent:
        extra = rig_data.edit_bones.new("Extra")
        extra.tail = (0, 1, 0)
    worlds = I.world_matrices(joints)
    for i, joint in enumerate(joints):
        bone = rig_data.edit_bones.new(f"j{i}")
        bone.tail = (0, 1, 0)
        bone.matrix = Matrix(W.mul(W.C4, worlds[i]))
        bone.length = 1
        if joint.parent is not None:
            bone.parent = rig_data.edit_bones[f"j{joint.parent}"]
            bone.use_connect = connected
        elif extra_parent:
            bone.parent = rig_data.edit_bones["Extra"]
    bpy.ops.object.mode_set(mode="OBJECT")
    return rig, {"joints": [{"index": i, "name": f"j{i}"} for i in range(len(joints))]}


# A connected Blender bone silently discards its keyed location. Reject a
# translation which that rig cannot represent, without disconnecting the rig.
simple_rest = (D.RestJoint(None, (0, 0, 0), (0, 0, 0), (1, 1, 1)),
               D.RestJoint(0, (0, 0, 0), (0, 1, 0), (1, 1, 1)))
connected, connected_plan = simple_rig("Connected", simple_rest, connected=True)
moving = D.read_bank(archive([[], [(6, stream([(2, 1, None, 2), (2, 2, None, None)]), 0, 0)]],
                            name="ConnectedMove", frames=2))[0]
count = len(bpy.data.actions)
try:
    create_actions(connected, [moving], simple_rest, connected_plan)
except D.FigatreeError as exc:
    assert "connected" in str(exc).lower(), exc
else:
    raise AssertionError("connected bone translation was silently accepted")
assert len(bpy.data.actions) == count
assert connected.data.bones["j1"].use_connect

# Eight rotations per frame must survive matrix aliasing at dyadic samples.
rapid_rig, rapid_plan = simple_rig("Rapid", simple_rest[:1])
rapid = D.read_bank(archive([[(1, stream([(2, 0, None, 1), (2, 16*3.141592653589793, None, None)]), 0, 0)]],
                           name="RapidTurns", frames=1))[0]
rapid_action = create_actions(rapid_rig, [rapid], simple_rest[:1], rapid_plan)[0]
bind(rapid_rig, rapid_action)
for t in (.015625, .03125, .0625, .1, .333, .777, 1):
    at(t+1)
    expected = W.mul(W.C4, I.world_matrices(simple_rest[:1], rapid, t)[0])
    close(rapid_rig.pose.bones["j0"].matrix, Matrix(expected))

# Moving the armature object must not bake its scene placement into the action
# or make the source root rotate around the world origin.
rapid_rig.location = (4, -3, 2)
bpy.context.view_layer.update()
placed_action = create_actions(rapid_rig, [rapid], simple_rest[:1], rapid_plan)[0]
bind(rapid_rig, placed_action)
at(1.1)
close(rapid_rig.pose.bones["j0"].matrix,
      Matrix(W.mul(W.C4, I.world_matrices(simple_rest[:1], rapid, .1)[0])))

# A Blender-only ancestor needs rest keys so a prior pose cannot leak into an
# imported action. Import itself must still leave that prior pose untouched.
extra_rig, extra_plan = simple_rig("ExtraParent", simple_rest[:1], extra_parent=True)
extra_prior = bpy.data.actions.new("ExtraPrior")
bind(extra_rig, extra_prior)
extra_rig.pose.bones["Extra"].location = (3, 1, 0)
extra_rig.pose.bones["Extra"].rotation_euler = (.5, .2, .1)
extra_rig.pose.bones["Extra"].keyframe_insert("location", frame=1)
extra_rig.pose.bones["Extra"].keyframe_insert("rotation_euler", frame=1)
at(1)
extra_before = extra_rig.pose.bones["Extra"].matrix_basis.copy()
extra_action = create_actions(extra_rig, [rapid], simple_rest[:1], extra_plan)[0]
close(extra_rig.pose.bones["Extra"].matrix_basis, extra_before)
assert extra_rig.animation_data.action == extra_prior
bind(extra_rig, extra_action)
at(1.1)
close(extra_rig.pose.bones["Extra"].matrix_basis, Matrix.Identity(4))
close(extra_rig.pose.bones["j0"].matrix,
      Matrix(W.mul(W.C4, I.world_matrices(simple_rest[:1], rapid, .1)[0])))

# Exercise add-on registration and the actual file operator without an engine.
for obj in bpy.context.selected_objects:
    obj.select_set(False)
bpy.context.view_layer.objects.active = arm
arm.select_set(True)
import tools.blender.geno_workbench as addon
addon.register()
(work / "bank.dat").write_bytes(bank(roundtrip_raw, reset_raw))
(work / "model.dat").write_bytes(model([(j.parent, j.rotation, j.translation, j.scale, j.flags) for j in rest]))
(work / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
(work / "workbench.json").write_text(json.dumps({"art": {"bone_aliases": aliases}}), encoding="utf-8")
bpy.context.scene.geno_wb.project = str(work)
result = bpy.ops.geno_wb.import_figatree(filepath=str(work / "bank.dat"),
                                       model_path=str(work / "model.dat"), plan_path=str(work / "plan.json"))
assert result == {"FINISHED"}, result
assert bpy.data.actions.get("Roundtrip.001") is not None
addon.unregister()
print(f"FIGATREE ACTIONS OK actions={len(actions)} matrix_error={worst:.8g} roundtrip_curve_error={curve_error:.8g}")
