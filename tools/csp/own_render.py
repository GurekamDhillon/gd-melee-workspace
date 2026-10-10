"""Own UI renderer (--backend own). Runs inside current Blender (tested 5.2); no CSProject.

Imports the fighter art, poses it, finds its joints through the role map, frames every
UI asset from the posed skeleton (tools/csp/framing.py), lights it with a rig written
here, and renders the same ten camera names the CSProject path produces, so the
same conversion and publish code consumes them. Never saves a .blend.
"""
import argparse
import json
import math
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.csp import framing
from tools.csp.blender_common import fighter_meshes, jsonable, matrix_for, skeleton_frame_inputs
from tools.csp.project import confined_path

import bpy
from mathutils import Vector

# camera name -> (asset, width, height). SD twins render at 4x their retail size and are fitted
# down by the host (aliasing at 24x24 otherwise); HD twins use CSProject's HD sizes.
SUPERSAMPLE = 4
CAMERAS = (
    ('All-Star_HD', 'allstar', 256, 230), ('All-Star_SD', 'allstar', 128 * SUPERSAMPLE, 115 * SUPERSAMPLE),
    ('CSP_HD', 'portrait', 408, 564), ('CSP_SD', 'portrait', 136 * SUPERSAMPLE, 188 * SUPERSAMPLE),
    ('CSS Icon_HD', 'icon', 320, 280), ('CSS Icon_SD', 'icon', 64 * SUPERSAMPLE, 56 * SUPERSAMPLE),
    ('Render', 'render', 1000, 1500),
    ('STC_HD', 'stock', 144, 144), ('STC_SD', 'stock', 24 * SUPERSAMPLE * 2, 24 * SUPERSAMPLE * 2),
    ('Results_SD', 'results', 52 * SUPERSAMPLE, 74 * SUPERSAMPLE),
)

# Light rig defaults, in the 3/4 camera's own terms (degrees); the job's own_render.look can override.
DEFAULT_LOOK = {
    'yaw': 28.0, 'pitch': 3.0,
    'key': {'color': (1.0, 0.96, 0.9), 'energy': 3.8, 'azimuth': -40.0, 'elevation': 38.0},
    'fill': {'color': (0.85, 0.9, 1.0), 'energy': 1.1, 'azimuth': 55.0, 'elevation': 12.0},
    'rim': {'color': (1.0, 1.0, 1.0), 'energy': 2.0, 'azimuth': 150.0, 'elevation': 25.0},
    'ambient': (0.55, 0.57, 0.62), 'ambient_strength': 0.55, 'specular': 0.4, 'roughness': 0.4, 'view_transform': 'Standard',
}


def merged_look(job):
    look = json.loads(json.dumps(DEFAULT_LOOK))
    for key, value in (job.get('own_render') or {}).items():
        if isinstance(value, dict) and isinstance(look.get(key), dict):
            look[key].update(value)
        else:
            look[key] = value
    return look


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.data.scenes[0] if bpy.data.scenes else bpy.data.scenes.new('Scene')
    bpy.context.window.scene = scene
    return scene


def set_engine(scene):
    names = [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items]
    scene.render.engine = 'BLENDER_EEVEE' if 'BLENDER_EEVEE' in names else 'BLENDER_EEVEE_NEXT'


def build_world(scene, look):
    world = bpy.data.worlds.new('GenoUIWorld')
    world.use_nodes = True
    background = world.node_tree.nodes.get('Background')
    background.inputs['Color'].default_value = (*look['ambient'], 1.0)
    background.inputs['Strength'].default_value = look['ambient_strength']
    scene.world = world
    scene.render.film_transparent = True
    scene.view_settings.view_transform = look['view_transform']
    scene.view_settings.look = 'None'


def sun(scene, name, spec, basis):
    """Sun lamp placed by azimuth/elevation relative to the camera basis (azimuth 0 = from the camera)."""
    az, el = math.radians(spec['azimuth']), math.radians(spec['elevation'])
    towards = (basis['right'][i] * math.sin(az) * math.cos(el) - basis['look'][i] * math.cos(az) * math.cos(el)
               + basis['up'][i] * math.sin(el) for i in range(3))
    towards = Vector(tuple(towards)).normalized()  # direction from the fighter toward the light
    data = bpy.data.lights.new(name, 'SUN')
    data.color = spec['color']
    data.energy = spec['energy']
    data.angle = math.radians(12)
    obj = bpy.data.objects.new(name, data)
    obj.rotation_euler = (-towards).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(obj)
    return obj


def soften_specular(look):
    for material in bpy.data.materials:
        if not material.use_nodes:
            continue
        for node in material.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                for key in ('Specular IOR Level', 'Specular'):
                    if key in node.inputs:
                        node.inputs[key].default_value = look['specular']
                if 'Roughness' in node.inputs:
                    node.inputs['Roughness'].default_value = max(node.inputs['Roughness'].default_value, look['roughness'])
                if 'Metallic' in node.inputs and not node.inputs['Metallic'].links:
                    node.inputs['Metallic'].default_value = 0.0


def make_camera(scene, name, plan, basis, width, height):
    data = bpy.data.cameras.new(name)
    data.type = 'ORTHO'
    data.ortho_scale = plan['ortho_scale']
    data.sensor_fit = 'AUTO'
    data.clip_start, data.clip_end = 0.1, plan['distance'] * 4 + 1000
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.matrix_world = matrix_for(plan['location'], basis)
    return obj


def render_job(job):
    boundary = Path(job['root']).resolve() / '_build'
    work = confined_path(job['work'], boundary)
    work.mkdir(parents=True, exist_ok=True)
    from tools.csp import blender_render as shared
    settings = job.get('scene_config', {})
    look = merged_look(job)
    renders, reports = {}, []
    for costume in job['costumes']:
        scene = reset_scene()
        set_engine(scene)
        build_world(scene, look)
        scene.render.fps, scene.render.fps_base = 60, 1.0
        objects, rig, actions = shared.import_art(costume.get('art') or job['art'], scene, settings)
        rig.animation_data_create()
        shared.pose(rig, actions, job['action'], job['frame'] + job.get('frame_offset', 0))
        shared.apply_costume(objects, costume, settings.get('keep_objects', []))
        body = fighter_meshes(objects)
        for obj in objects:
            if obj.type == 'MESH' and obj not in body:
                obj.hide_render = True
        anchors, points, facing = skeleton_frame_inputs(rig, job.get('roles', {}), body)
        facing = facing or tuple(job.get('facing') or (0.0, -1.0, 0.0))
        basis = framing.camera_basis(facing, look['yaw'], look['pitch'])
        soften_specular(look)
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGBA'
        scene.render.image_settings.color_depth = '8'
        scene.render.resolution_percentage = 100
        for lamp, spec in (('Key', look['key']), ('Fill', look['fill']), ('Rim', look['rim'])):
            sun(scene, lamp, spec, basis)
        costume_out = confined_path(work / ('c%03d' % costume['index']), work)
        costume_out.mkdir(parents=True, exist_ok=True)
        outputs, plans = {}, {}
        for index, (name, asset, width, height) in enumerate(CAMERAS):
            plan = framing.plan(asset, anchors, points, basis, size=(width, height))
            camera = make_camera(scene, name, plan, basis, width, height)
            scene.camera = camera
            scene.render.resolution_x, scene.render.resolution_y = width, height
            output = confined_path(costume_out / ('camera-%02d.png' % index), costume_out)
            scene.render.filepath = str(output)
            bpy.ops.render.render(write_still=True)
            if not output.is_file():
                raise RuntimeError('Renderer produced no PNG for ' + name)
            outputs[name] = str(output)
            plans[name] = dict(jsonable(plan), asset=asset, width_px=width, height_px=height)
        renders[str(costume['index'])] = outputs
        reports.append({'backend': 'own', 'blender': bpy.app.version_string, 'facing': facing,
                        'anchors': {k: (list(v) if isinstance(v, tuple) else v) for k, v in anchors.items()},
                        'mesh_vertices': len(points), 'body_meshes': [o.name for o in body],
                        'hidden_helpers': [o.name for o in objects if o.type == 'MESH' and o not in body],
                        'look': look, 'cameras': plans})
    confined_path(work / 'renders.json', work).write_text(
        json.dumps({'renders': renders, 'scenes': reports, 'enabled_addons': []}, indent=2) + '\n', encoding='utf-8')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--job', type=Path, required=True)
    args = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    render_job(json.loads(args.job.read_text(encoding='utf-8')))


if __name__ == '__main__':
    main()
