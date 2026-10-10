"""Invented skinned cube/action for the local Blender integration test only."""
import sys
import bpy

out = sys.argv[sys.argv.index('--') + 1]
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.context.scene.render.fps = 60
bpy.ops.object.armature_add(location=(0, 0, 0))
arm = bpy.context.object
arm.name = 'SyntheticRig'
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 1))
mesh = bpy.context.object
mesh.scale = (0.5, 0.5, 1)
group = mesh.vertex_groups.new(name=arm.data.bones[0].name)
group.add(list(range(len(mesh.data.vertices))), 1, 'REPLACE')
modifier = mesh.modifiers.new('Skin', 'ARMATURE')
modifier.object = arm
mesh.parent = arm
arm.animation_data_create()
arm.animation_data.action = bpy.data.actions.new('Wait')
bone = arm.pose.bones[0]
bone.rotation_mode = 'XYZ'
bone.keyframe_insert('rotation_euler', frame=0)
bone.rotation_euler[1] = 0.2
bone.keyframe_insert('rotation_euler', frame=8)
# The artist pipeline exports each clip as an NLA track (spec section 10); Blender 3.5 names a
# glTF animation after its track, whereas a bare active action exports as "Animation".
action = arm.animation_data.action
track = arm.animation_data.nla_tracks.new()
track.name = 'Wait'
track.strips.new('Wait', 0, action)
arm.animation_data.action = None
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
mesh.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.export_scene.gltf(filepath=out, export_format='GLB', use_selection=True,
                          export_animations=True, export_frame_range=False,
                          export_force_sampling=True, export_nla_strips=True)

# A nested author collection lets the .blend integration catch lost membership.
from pathlib import Path
parent = bpy.data.collections.new('AuthorCostumes')
child = bpy.data.collections.new('CostumeDefault')
bpy.context.scene.collection.children.link(parent)
parent.children.link(child)
child.objects.link(mesh)
for collection in list(mesh.users_collection):
    if collection != child:
        collection.objects.unlink(mesh)
bpy.ops.wm.save_as_mainfile(filepath=str(Path(out).with_suffix('.blend')))
