"""Blender script: HSDRaw exports -> falcon.blend.

    blender -b --python build_blend.py -- GLB SKELETON.smd ANIM_DIR OUT.blend [PARTS.json]

* meshes + materials + textures come from the glTF (every mesh is skinned to vertex groups JOBJ_<n>);
* the rig is the .smd skeleton imported with Blender Source Tools (external add-on, loaded from the
  BLENDER_USER_SCRIPTS dir make_falcon_art.py prepares): its bone axes are the engine's joint frames, which is
  what the Workbench calibration wants. Bones are JOBJ_<n>, n = the engine joint index, parent-first;
* PARTS.json (HsdExport --parts) bakes the default model-part visibility: the low-poly LOD set is hidden;
* every ANIM_DIR/<Clip>.smd becomes an Action named <Clip>, frame 0 = engine frame 1 (the Workbench rule).
Output stays under _build/ (git-ignored); nothing here ships.
"""
import glob
import os
import sys
import time

import bpy

_args = sys.argv[sys.argv.index("--") + 1:]
glb, smd, anim_dir, out = _args[:4]
parts_json = _args[4] if len(_args) > 4 else None

bpy.ops.wm.read_factory_settings(use_empty=True)
import addon_utils  # noqa: E402
addon_utils.enable("io_scene_valvesource", default_set=False, persistent=False)

# 1. rig from the .smd skeleton (Y-up in the file; BST rotates it to Z-up like the glTF import). First, because BST
#    would otherwise reuse an armature that already exists in the scene.
bpy.ops.import_scene.smd(filepath=smd, doAnim=False, upAxis="Y")
rig = next(o for o in bpy.data.objects if o.type == "ARMATURE")
for o in [o for o in bpy.data.objects if o.type == "MESH"]:
    bpy.data.objects.remove(o, do_unlink=True)   # the .smd's own rigid-bound mesh and bone-display shapes
for me in [m for m in bpy.data.meshes if m.users == 0]:
    bpy.data.meshes.remove(me)   # and its mesh data, which holds the .smd's materials
for mat in [m for m in bpy.data.materials if m.users == 0]:
    bpy.data.materials.remove(mat)

# 2. meshes from glTF
bpy.ops.import_scene.gltf(filepath=glb)
gltf_arm = next(o for o in bpy.data.objects if o.type == "ARMATURE" and o is not rig)
for o in [o for o in bpy.data.objects if o.type == "MESH" and o.name.startswith("Icosphere") and not o.modifiers]:
    bpy.data.objects.remove(o, do_unlink=True)   # the importer's bone-display helper, loose and unskinned
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")
for eb in [b for b in rig.data.edit_bones if not b.name.startswith("JOBJ_")]:
    rig.data.edit_bones.remove(eb)   # per-mesh helper bones BST makes for rigid parts
bpy.ops.object.mode_set(mode="OBJECT")
rig.name = "falcon_skeleton"
rig["geno"] = "geno-falcon"

# the two skeletons must agree, else the weights would sit on the wrong joints
worst = 0.0
for b in rig.data.bones:
    g = gltf_arm.data.bones.get(b.name)
    assert g is not None, "glTF has no bone " + b.name
    worst = max(worst, (rig.matrix_world @ b.head_local - gltf_arm.matrix_world @ g.head_local).length)
assert len(rig.data.bones) == len(gltf_arm.data.bones) == 63, (len(rig.data.bones), len(gltf_arm.data.bones))
assert worst < 1e-3, "skeleton mismatch %.5f" % worst

# 4. skin the glTF meshes to the .smd rig
for m in meshes:
    mw = m.matrix_world.copy()
    m.parent = rig
    m.matrix_parent_inverse = rig.matrix_world.inverted()
    m.matrix_world = mw
    mods = [md for md in m.modifiers if md.type == "ARMATURE"]
    assert mods, "unskinned mesh " + m.name
    mods[0].object = rig
bpy.data.objects.remove(gltf_arm, do_unlink=True)

# 5. clips
t0 = time.time()
files = sorted(glob.glob(os.path.join(anim_dir, "*.smd")))
for f in files:
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    if rig.animation_data:
        rig.animation_data.action = None   # BST would otherwise write the next clip into the last one
    bpy.ops.import_scene.smd(filepath=f, doAnim=True, upAxis="Y")
    act = rig.animation_data.action if rig.animation_data else None
    if act is not None:
        act.name = os.path.splitext(os.path.basename(f))[0]
        act.use_fake_user = True
if rig.animation_data:
    rig.animation_data.action = None
for b in rig.pose.bones:
    b.location = (0, 0, 0)
    b.rotation_euler = (0, 0, 0)
    b.rotation_quaternion = (1, 0, 0, 0)
for mat in [m for m in bpy.data.materials if m.users == 0]:
    bpy.data.materials.remove(mat)   # the .smd skeleton import brought its own, unused ones
print("FALCON_CLIPS imported=%d actions=%d in %.1fs" % (len(files), len(bpy.data.actions), time.time() - t0))
if parts_json:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import part_visibility
    _hidden, _missing = part_visibility.apply_to_objects(meshes, part_visibility.hidden_names(part_visibility.load(parts_json)))
    assert not _missing, "parts.json names meshes the glTF lacks: %s" % _missing
    print("FALCON_PARTS hidden=%d" % len(_hidden))
    print("FALCON_ALPHA", part_visibility.apply_alpha(meshes, part_visibility.alpha_by_name(part_visibility.load(parts_json))))
    print("FALCON_CULL", len(part_visibility.apply_cull(meshes, part_visibility.cull_names(part_visibility.load(parts_json)))))
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=out)
print("FALCON_BLEND bones=%d meshes=%d materials=%d images=%d skeleton_diff=%.2g -> %s" % (
    len(rig.data.bones), len(meshes), len(bpy.data.materials), len(bpy.data.images), worst, out))
