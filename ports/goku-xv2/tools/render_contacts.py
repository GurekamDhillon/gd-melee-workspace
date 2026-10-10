"""Render the actual Blender poses with installed native-bank collision overlays.

Run using Blender --background author-source/goku.blend --python THIS -- --root
_build/goku-xv2. Generated contact sheets are evidence of offline pose/encoding,
not runtime contact or XV2 fidelity. Native model (x,y,z) -> Blender (x,-z,y).
"""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def emission(name, rgb):
    material=bpy.data.materials.new(name)
    material.use_nodes=True
    nodes=material.node_tree.nodes
    nodes.clear()
    shader=nodes.new('ShaderNodeEmission')
    shader.inputs['Color'].default_value=(*rgb,1)
    output=nodes.new('ShaderNodeOutputMaterial')
    material.node_tree.links.new(shader.outputs[0],output.inputs[0])
    return material


def lines(name, paths, mat, width=.022):
    curve=bpy.data.curves.new(name,'CURVE')
    curve.dimensions='3D';curve.bevel_depth=width;curve.bevel_resolution=0
    for path in paths:
        spline=curve.splines.new('POLY');spline.points.add(len(path)-1)
        for point,xyz in zip(spline.points,path):point.co=(*xyz,1)
    obj=bpy.data.objects.new(name,curve);bpy.context.collection.objects.link(obj)
    obj.data.materials.append(mat)
    return obj


def rings(centre,radius):
    paths=[]
    for axis in range(3):
        path=[]
        for i in range(41):
            p=Vector(centre);angle=2*math.pi*i/40
            p[(axis+1)%3]+=radius*math.cos(angle)
            p[(axis+2)%3]+=radius*math.sin(angle)
            path.append(p)
        paths.append(path)
    return paths


def label(text,at,rotation,material,size=.55):
    data=bpy.data.curves.new('Label','FONT');data.body=text
    data.align_x='CENTER';data.size=size
    obj=bpy.data.objects.new('Label',data);bpy.context.collection.objects.link(obj)
    obj.location=at;obj.rotation_euler=rotation;data.materials.append(material)
    return obj


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--limit',type=int,default=0)
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    args=ap.parse_args(argv);root=args.root.resolve()
    if root.name!='goku-xv2' or root.parent.name!='_build':raise ValueError('Use dedicated _build/goku-xv2')
    build=root/'author-source/package/build';dest=root/'contact-sheets';dest.mkdir(exist_ok=True)
    frames=read(build/'framedata-parity-check.json')['moves']
    hits=read(build/'hitbox-positions.json')['positions']
    hurts=read(build/'hurtbox-coverage.json')['poses']
    arm=next(o for o in bpy.data.objects if o.type=='ARMATURE')
    meshes=[o for o in bpy.data.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers)]
    for track in arm.animation_data.nla_tracks:track.mute=True
    scene=bpy.context.scene;scene.render.fps=60
    scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=1536;scene.render.resolution_y=640
    scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG'
    scene.view_settings.view_transform='Standard';scene.world.color=(.028,.033,.045)
    cam=scene.camera;cam.location=(32,-60,23)
    centre=Vector((0,0,10))
    cam.rotation_euler=(centre-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.type='ORTHO';cam.data.ortho_scale=76
    right=cam.rotation_euler.to_quaternion()@Vector((1,0,0))
    up=cam.rotation_euler.to_quaternion()@Vector((0,1,0))
    red=emission('Hit spheres',(1,.12,.07));green=emission('Hurt capsules',(.14,.8,.42))
    white=emission('Labels',(.87,.9,.95))
    def native(p,shift):return Vector((p[0],-p[2],p[1]))+shift
    manifest=[];seen=set()
    for move in frames:
        if args.limit and len(manifest)>=args.limit:break
        name=move['move']
        if name in seen:continue
        seen.add(name);row=move['row']
        samples=[p for p in hurts if p['move']==name]
        if not samples:raise ValueError('No native pose samples for '+name)
        clip=samples[0]['clip'];action=bpy.data.actions.get(clip)
        if action is None:raise ValueError('Blender action missing: '+clip)
        arm.animation_data.action=action
        if hasattr(action,'slots') and action.slots:arm.animation_data.action_slot=action.slots[0]
        chosen=[samples[0],samples[min(1,len(samples)-1)],samples[-1]]
        created=[]
        for panel,sample in enumerate(chosen):
            frame=sample['frame'];shift=right*((panel-1)*23)
            scene.frame_set(frame);bpy.context.view_layer.update()
            deps=bpy.context.evaluated_depsgraph_get()
            for original in meshes:
                geometry=bpy.data.meshes.new_from_object(original.evaluated_get(deps),depsgraph=deps)
                obj=bpy.data.objects.new('Contact pose',geometry);bpy.context.collection.objects.link(obj)
                obj.matrix_world=original.matrix_world.copy();obj.location+=shift;created.append(obj)
            hpaths=[]
            for capsule in sample.get('capsules',[]):
                a=native(capsule['a'],shift);b=native(capsule['b'],shift);r=capsule['radius']
                hpaths+=rings(a,r)+rings(b,r)+[[a,b]]
            if not hpaths:raise ValueError('Posed hurtbox endpoints missing for '+name)
            created.append(lines('Hurtboxes',hpaths,green,.014))
            paths=[]
            for hit in hits:
                if hit['move']==name and hit['row']==row and hit['frame']==frame:
                    paths+=rings(native(hit['native_bank_world_centre'],shift),hit['radius'])
            if paths:created.append(lines('Hitboxes',paths,red,.035))
            created.append(label(f'{clip} | frame {frame}',centre+shift+up*11.7,cam.rotation_euler,white,.75))
        created.append(label(name+'  |  red: hit spheres   green: hurt capsules',centre+up*13.7,cam.rotation_euler,white,.95))
        created.append(label('Offline installed-bank poses. Source fidelity and runtime contact are unverified.',centre-up*13.7,cam.rotation_euler,white,.65))
        for original in meshes:original.hide_render=True
        scene.render.filepath=str(dest/(name+'.png'));bpy.ops.render.render(write_still=True)
        for original in meshes:original.hide_render=False
        manifest.append(dict(move=name,row=row,clip=clip,frames=[s['frame'] for s in chosen],image=name+'.png'))
        for obj in created:
            data=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
            if data.users==0:
                if isinstance(data,bpy.types.Mesh):bpy.data.meshes.remove(data)
                elif isinstance(data,bpy.types.Curve):bpy.data.curves.remove(data)
    (dest/'index.json').write_text(json.dumps(dict(note='Blender source pose with installed FigaTree collision overlays; not runtime proof',sheets=manifest),indent=2),encoding='utf-8')
    print('CONTACT_SHEETS',len(manifest),dest)


if __name__=='__main__':main()
