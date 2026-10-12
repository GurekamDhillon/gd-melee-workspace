"""Import generated IR GLB as editable Blender source and render a front preview."""
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector

out=Path(sys.argv[sys.argv.index('--')+1]).resolve()
_o=out.as_posix().lower()
if not (_o.endswith('/_build/goku-xv2/author-source') or '/_build/goku-xv2/turn-preview/' in _o):   # turn-preview: the locomotion-set previews (GOKU_AUTHOR=turn-preview/<set>)
    raise ValueError('Expected dedicated generated art directory')
for old in list(bpy.data.objects):
    bpy.data.objects.remove(old,do_unlink=True)  # includes hidden startup objects
bpy.context.scene.render.fps=60
bpy.context.scene.render.fps_base=1.0
bpy.context.scene.frame_start=0
bpy.ops.import_scene.gltf(filepath=str(out/'goku.glb'))
arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
arm.name='GokuExport'
# glTF importer creates an unskinned Icosphere in glTF_not_exported as its bone
# display shape. Keep the editable source to one mesh and use ordinary bones.
for pb in arm.pose.bones:pb.custom_shape=None
for ob in list(bpy.data.objects):
    if ob.type=='MESH' and not any(m.type=='ARMATURE' for m in ob.modifiers):
        bpy.data.objects.remove(ob,do_unlink=True)
meta=json.loads((out/'goku.glb.geno.json').read_text())
arm['geno']=json.dumps({'fighter':'Goku','roles':meta['roles'],'costumes':[{'name':'default','texture':'atlas.png'}]})
for a in bpy.data.actions:
    # The glTF importer uses Armature|Action names on older Blender versions.
    name=a.name.split('|')[-1]
    if name in meta['clips']:a.name=name
    a.use_fake_user=True
    if name in meta['clips']:
        a['geno_loop']=bool(meta['clips'][name]['loop'])
        a['geno_root_motion']=bool(meta['clips'][name].get('root_motion'))
        a['geno_rows']=name
        expected=meta['clips'][name]['frames']-1
        if abs(a.frame_range[0])>.01 or abs(a.frame_range[1]-expected)>.01:
            raise ValueError(f'Imported action timebase mismatch: {name} {tuple(a.frame_range)}, expected 0..{expected}')
for tr in arm.animation_data.nla_tracks:tr.mute=True
wait=next(a for a in bpy.data.actions if a.name=='Wait')
arm.animation_data.action=wait
if hasattr(wait,'slots') and len(wait.slots):arm.animation_data.action_slot=wait.slots[0]
scene=bpy.context.scene
scene.render.fps=60;scene.frame_start=0;scene.frame_end=99;scene.frame_set(0)
# Make the author view use the same baked diffuse contract as the game.
for mat in bpy.data.materials:
    if not mat.use_nodes:continue
    tex=next((n for n in mat.node_tree.nodes if n.type=='TEX_IMAGE'),None)
    output=next((n for n in mat.node_tree.nodes if n.type=='OUTPUT_MATERIAL'),None)
    if tex and output:
        emit=mat.node_tree.nodes.new('ShaderNodeEmission')
        mat.node_tree.links.new(tex.outputs['Color'],emit.inputs['Color'])
        mat.node_tree.links.new(emit.outputs[0],output.inputs['Surface'])
height=json.loads((out/'art-report.json').read_text())['geometry']['height']
ratio=height/14.
bpy.ops.object.camera_add(location=(18*ratio,-32*ratio,14*ratio))
cam=bpy.context.object;cam.name='ArtReviewCamera'
cam.rotation_euler=(Vector((0,0,7*ratio))-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type='ORTHO';cam.data.ortho_scale=19*ratio;scene.camera=cam
scene.render.engine='BLENDER_EEVEE';scene.world.color=(.12,.12,.12)
scene.render.resolution_x=800;scene.render.resolution_y=800;scene.render.resolution_percentage=100
scene.view_settings.view_transform='Standard'
for ob in bpy.context.selected_objects:ob.select_set(False)
arm.select_set(True);bpy.context.view_layer.objects.active=arm
bpy.ops.wm.save_as_mainfile(filepath=str(out/'goku.blend'))
scene.render.filepath=str(out/'art-preview.png')
bpy.ops.render.render(write_still=True)
print('ART_BLENDER',json.dumps({'armature':arm.name,'actions':[a.name for a in bpy.data.actions],'bones':len(arm.data.bones)}))
