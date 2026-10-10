"""Blender 3.5.1 worker. Appends a local template Scene; never saves a .blend.

All CSProject internals are discovered at runtime. See README.md before the
lead's first render: default donor/camera-property assumptions need inspection.
"""
import argparse
import json
from pathlib import Path
import re
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.csp import framing
from tools.csp.blender_common import fighter_meshes, jsonable, skeleton_frame_inputs, world_points
from tools.csp.project import confined_path, generated_path, workspace_root

import bpy
from mathutils import Vector


ADDONS = ('loom', 'render_button')


def enable_addons():
    if bpy.app.version != (3, 5, 1):
        raise RuntimeError('CSProject requires exact Blender 3.5.1; got ' + bpy.app.version_string)
    import addon_utils
    for module in ADDONS:
        addon_utils.enable(module, default_set=True, persistent=True)
        if not addon_utils.check(module)[1]:
            raise RuntimeError('Could not enable external add-on ' + module)


def append_template(path, settings):
    with bpy.data.libraries.load(str(path), link=False) as (source, target):
        name = settings.get('scene')
        if name is None:
            if len(source.scenes) == 1:
                name = source.scenes[0]
            elif 'Scene' in source.scenes:
                name = 'Scene'
            else:
                raise RuntimeError('Choose scene_config.scene from: ' + ', '.join(source.scenes))
        if name not in source.scenes:
            raise RuntimeError('Unknown template scene: ' + name)
        target.scenes = [name]
    scene = target.scenes[0]
    # Scene append brings Objects, Camera/Light data, World, render settings,
    # collections and compositor nodes with their original relationships.
    bpy.context.window.scene = scene
    return scene


def camera_list(scene, settings):
    cameras = {o.name: o for o in scene.objects if o.type == 'CAMERA'}
    names = settings.get('camera_names', sorted(cameras))
    if len(names) != 9 or len(set(names)) != 9 or any(n not in cameras for n in names):
        raise RuntimeError('CSProject must select exactly nine cameras; found ' + repr(sorted(cameras)))
    return [cameras[n] for n in names]


def json_value(value):
    if isinstance(value, (str, bool, int, float)) or value is None:
        return value
    if hasattr(value, 'to_dict'):
        return {k: json_value(v) for k, v in value.to_dict().items()}
    if hasattr(value, 'to_list'):
        return value.to_list()
    try:
        return list(value)
    except TypeError:
        return str(value)


def property_inventory(value):
    result = {'custom': {k: json_value(v) for k, v in value.items()}}
    group = getattr(value, 'loom', None)
    if group is not None and hasattr(group, 'bl_rna'):
        result['loom'] = {}
        for prop in group.bl_rna.properties:
            if prop.identifier != 'rna_type' and prop.type not in ('POINTER', 'COLLECTION'):
                result['loom'][prop.identifier] = json_value(getattr(group, prop.identifier))
    return result


def inventory(scene):
    return {
        'blender': bpy.app.version_string, 'scene': scene.name,
        'world': scene.world.name if scene.world else None,
        'render': {'engine': scene.render.engine, 'width': scene.render.resolution_x,
                   'height': scene.render.resolution_y, 'percentage': scene.render.resolution_percentage,
                   'fps': scene.render.fps, 'film_transparent': scene.render.film_transparent},
        'cameras': [{'name': c.name, 'data': c.data.name, 'parent': c.parent.name if c.parent else None,
                     'type': c.data.type, 'lens': c.data.lens, 'ortho_scale': c.data.ortho_scale,
                     'object_settings': property_inventory(c), 'data_settings': property_inventory(c.data)}
                    for c in scene.objects if c.type == 'CAMERA'],
        'objects': [{'name': o.name, 'type': o.type, 'parent': o.parent.name if o.parent else None,
                     'hide_render': o.hide_render,
                     'constraints': [{'type': c.type, 'target': c.target.name if getattr(c, 'target', None) else None,
                                      'subtarget': getattr(c, 'subtarget', '')} for c in o.constraints]}
                    for o in scene.objects],
        'compositor': [n.bl_idname for n in scene.node_tree.nodes] if scene.use_nodes else [],
        'actions': [a.name for a in bpy.data.actions],
        'enabled_addons': list(ADDONS),
    }


def bounds(objects):
    points = []
    graph = bpy.context.evaluated_depsgraph_get()
    for obj in objects:
        if obj.type == 'MESH':
            evaluated = obj.evaluated_get(graph)
            points.extend(evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box)
    if not points:
        raise RuntimeError('No fighter mesh bounds; set scene_config.fighter_objects')
    low = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    if high.z - low.z < 0.0001:
        raise RuntimeError('Fighter bounds have no height')
    return low, high


def donor_objects(scene, settings):
    keep = set(settings.get('keep_objects', []))
    names = settings.get('fighter_objects')
    if names:
        missing = set(names) - set(scene.objects.keys())
        if missing:
            raise RuntimeError('Unknown template fighter_objects: ' + repr(missing))
        return [scene.objects[n] for n in names if n not in keep]
    return [o for o in scene.objects if o.type in ('MESH', 'ARMATURE') and o.name not in keep]


def import_art(path, scene, settings):
    before_objects = set(bpy.data.objects)
    before_actions = set(bpy.data.actions)
    action_names = {}
    if Path(path).suffix.lower() == '.blend':
        with bpy.data.libraries.load(path, link=False) as (source, target):
            name = settings.get('art_scene')
            if name is None:
                if len(source.scenes) == 1:
                    name = source.scenes[0]
                elif 'Scene' in source.scenes:
                    name = 'Scene'
                else:
                    raise RuntimeError('Choose scene_config.art_scene from: ' + ', '.join(source.scenes))
            if name not in source.scenes:
                raise RuntimeError('Unknown original art scene: ' + str(name))
            original_names = list(source.actions)
            target.scenes = [name]
            target.actions = original_names
        action_names = {n: a for n, a in zip(original_names, target.actions) if a is not None}
        source_scene = target.scenes[0]
        objects = [o for o in source_scene.objects if o.type in ('MESH', 'ARMATURE', 'EMPTY')]
        # Link the author's collection hierarchy rather than flattening objects.
        # Nested costume membership, materials and rig dependencies remain intact;
        # the template still owns World, render settings and compositor.
        for collection in list(source_scene.collection.children):
            scene.collection.children.link(collection)
        for obj in list(source_scene.collection.objects):
            scene.collection.objects.link(obj)
        for obj in source_scene.objects:
            if obj.type not in ('MESH', 'ARMATURE', 'EMPTY'):
                obj.hide_render = True
        bpy.data.scenes.remove(source_scene, do_unlink=True)
        bpy.context.view_layer.update()
    else:
        # glTF seconds map to the project's 60 Hz animation samples.
        scene.render.fps, scene.render.fps_base = 60, 1.0
        bpy.ops.import_scene.gltf(filepath=path)
        objects = list(set(bpy.data.objects) - before_objects)
    if settings.get('art_objects'):
        wanted = set(settings['art_objects'])
        objects = [o for o in objects if o.name in wanted or re.sub(r'\.\d{3}$', '', o.name) in wanted]
        for obj in set(bpy.data.objects) - before_objects - set(objects):
            obj.hide_render = True
    rigs = [o for o in objects if o.type == 'ARMATURE']
    if len(rigs) != 1:
        raise RuntimeError('Original art must select one armature; found ' + repr([o.name for o in rigs]))
    rig = rigs[0]
    for action in set(bpy.data.actions) - before_actions:
        action_names.setdefault(action.name, action)
    if rig.animation_data:
        for track in rig.animation_data.nla_tracks:
            if len(track.strips) == 1:
                action_names.setdefault(track.name, track.strips[0].action)
    return objects, rig, action_names


def pose(rig, actions, name, frame):
    action = actions.get(name)
    if action is None:
        raise RuntimeError('Art has no action ' + name + '; found ' + ', '.join(sorted(actions)))
    if not min(0, action.frame_range[0]) <= frame <= action.frame_range[1]:
        raise RuntimeError('Requested frame is outside action range: ' + name + ' ' + str(tuple(action.frame_range)))
    rig.animation_data_create()
    for track in rig.animation_data.nla_tracks:
        track.mute = True
    rig.animation_data.action = action
    if hasattr(rig.animation_data, 'action_slot') and getattr(action, 'slots', None) and rig.animation_data.action_slot is None:
        # Blender 4.4+/5.x slotted actions: choose the slot that animates objects.
        slots = [sl for sl in action.slots if sl.target_id_type in ('OBJECT', 'UNSPECIFIED')] or list(action.slots)
        rig.animation_data.action_slot = slots[0]
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()


def align_art(objects, target, settings):
    # Bounds of the body only: a helper mesh (Goku's 2-unit icosphere at the origin) otherwise
    # sets the floor 3 units below his feet and he renders airborne.
    low, high = bounds(fighter_meshes(objects))
    target_low, target_high = target
    height = settings.get('fit_height', target_high.z - target_low.z)
    if height <= 0:
        raise RuntimeError('fit_height must be positive')
    scale = height / (high.z - low.z)
    anchor = bpy.data.objects.new('GenoUIArtRoot', None)
    bpy.context.scene.collection.objects.link(anchor)
    for obj in objects:
        if obj.parent not in objects:
            world = obj.matrix_world.copy()
            obj.parent = anchor
            obj.matrix_world = world
    centre = Vector(((low.x + high.x) / 2, (low.y + high.y) / 2, low.z))
    destination = Vector(((target_low.x + target_high.x) / 2, (target_low.y + target_high.y) / 2, target_low.z))
    anchor.scale = (scale,) * 3
    anchor.location = destination - centre * scale
    anchor.rotation_euler.z = float(settings.get('yaw_degrees', 0)) * 3.141592653589793 / 180
    if settings.get('offset'):
        anchor.location += Vector(settings['offset'])
    bpy.context.view_layer.update()


def apply_costume(objects, costume, keep=()):
    meshes = [o for o in objects if o.type == 'MESH' and o.name not in keep]
    selected = costume.get('objects')
    collections = costume.get('collections')
    if selected or collections:
        found = []
        for obj in meshes:
            object_names = {obj.name, re.sub(r'\.\d{3}$', '', obj.name)}
            collection_names = {name for c in obj.users_collection for name in (c.name, re.sub(r'\.\d{3}$', '', c.name))}
            visible = bool(object_names.intersection(selected or [])) or bool(collection_names.intersection(collections or []))
            obj.hide_render = not visible
            if visible:
                found.append(obj)
        if not found:
            raise RuntimeError('Costume selects no mesh objects: ' + str(costume['index']))
        meshes = found
    texture = costume.get('texture')
    colors = dict(costume.get('material_colors', {}))
    if not texture and not colors:
        return
    image = bpy.data.images.load(texture, check_existing=True) if texture else None
    replaced, matched = 0, set()
    for material in {m for o in meshes for m in o.data.materials if m is not None}:
        if not material.use_nodes:
            continue
        key = re.sub(r'\.\d{3}$', '', material.name)
        for node in material.node_tree.nodes:
            if node.type != 'BSDF_PRINCIPLED':
                continue
            base = node.inputs['Base Color']
            if key in colors or material.name in colors:
                color_key = material.name if material.name in colors else key
                color = colors[color_key]
                if not isinstance(color, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}(?:[0-9a-fA-F]{2})?', color):
                    raise RuntimeError('Material color must be #RRGGBB or #RRGGBBAA')
                channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
                linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in channels]
                for link in list(base.links):
                    material.node_tree.links.remove(link)
                base.default_value = (*linear, int(color[7:9], 16) / 255 if len(color) == 9 else 1)
                matched.add(color_key)
            elif image:
                for link in base.links:
                    if link.from_node.type == 'TEX_IMAGE':
                        link.from_node.image = image
                        replaced += 1
    if image and not replaced:
        raise RuntimeError('No directly linked Principled base-color image to recolor; use per-costume art')
    if set(colors) - matched:
        raise RuntimeError('Material recolor names not found: ' + repr(set(colors) - matched))


def camera_settings(camera, scene, override):
    result = {'width': scene.render.resolution_x, 'height': scene.render.resolution_y, 'source': 'template scene'}
    # These are intentionally narrow, unverified storage aliases. An inventory
    # plus explicit per-camera config avoids depending on unknown add-on APIs.
    for value in (camera, camera.data, getattr(camera, 'loom', None), getattr(camera.data, 'loom', None)):
        if value is None:
            continue
        x = getattr(value, 'resolution_x', None) or (value.get('resolution_x') if hasattr(value, 'get') else None)
        y = getattr(value, 'resolution_y', None) or (value.get('resolution_y') if hasattr(value, 'get') else None)
        if x and y:
            result.update(width=int(x), height=int(y), source='camera resolution_x/y')
    # Verified: the template stores per-camera size on the object as
    # RBTab_obj_Settings.Custom_CamHRes_prop / Custom_CamVRes_prop (pixel multipliers
    # Custom_CamH/VPixRes_prop, 1.0 in every shipped camera).
    try:
        rb = camera.get('RBTab_obj_Settings')
        if rb is not None and rb.get('Custom_CamHRes_prop') and rb.get('Custom_CamVRes_prop'):
            result.update(width=int(rb['Custom_CamHRes_prop'] * rb.get('Custom_CamHPixRes_prop', 1.0)),
                          height=int(rb['Custom_CamVRes_prop'] * rb.get('Custom_CamVPixRes_prop', 1.0)),
                          source='RBTab_obj_Settings')
    except (AttributeError, TypeError, KeyError):
        pass
    result.update(override)
    if any(not isinstance(result[k], int) or not 1 <= result[k] <= 8192 for k in ('width', 'height')):
        raise RuntimeError('Camera dimensions must be integers from 1 to 8192')
    scene.render.resolution_x, scene.render.resolution_y = result['width'], result['height']
    scene.render.resolution_percentage = 100
    crop = result.get('crop')
    scene.render.use_border = crop is not None
    scene.render.use_crop_to_border = crop is not None
    if crop is not None:
        if len(crop) != 4 or not 0 <= crop[0] < crop[2] <= 1 or not 0 <= crop[1] < crop[3] <= 1:
            raise RuntimeError('crop must be normalized [xmin,ymin,xmax,ymax]')
        scene.render.border_min_x, scene.render.border_min_y, scene.render.border_max_x, scene.render.border_max_y = crop
    return result


def frame_cameras(scene, cameras, rig, objects, job, settings, report):
    """Re-aim every UI camera at its own asset's crop of the posed body (framing.py).

    The template camera keeps its orientation and lens; only its position (and clip range)
    changes, so the template's authored view angles are retained while the framing no
    longer depends on the donor character's size or proportions.
    """
    body = fighter_meshes(objects)
    for obj in objects:
        if obj.type == 'MESH' and obj not in body:
            obj.hide_render = True
    if rig is not None:
        anchors, points, _ = skeleton_frame_inputs(rig, job.get('roles', {}), body)
    else:
        points = world_points(body)
        anchors = framing.anchor_points({}, points)
    report['framing'] = {'anchors': {k: (list(v) if isinstance(v, tuple) else v) for k, v in anchors.items()},
                         'body_meshes': [o.name for o in body], 'cameras': {}}
    pending = []
    for camera in cameras:
        data = camera.data
        matrix = camera.matrix_world.to_3x3()
        basis = {'right': tuple(matrix.col[0]), 'up': tuple(matrix.col[1]), 'look': tuple(-matrix.col[2])}
        size = (scene.render.resolution_x, scene.render.resolution_y)
        rb = camera.get('RBTab_obj_Settings')
        if rb is not None and rb.get('Custom_CamHRes_prop'):
            size = (int(rb['Custom_CamHRes_prop']), int(rb['Custom_CamVRes_prop']))
        override = settings.get('cameras', {}).get(camera.name, {})
        size = (override.get('width', size[0]), override.get('height', size[1]))
        asset = framing.asset_for_camera(camera.name)
        ortho = data.type == 'ORTHO'
        plan = framing.plan(asset, anchors, points, basis, size=size, lens=None if ortho else data.lens,
                            sensor=data.sensor_width, fit=data.sensor_fit)
        # The template may animate or drive cameras; render re-evaluates that and would undo this.
        report['framing'].setdefault('cleared_animation', {})[camera.name] = bool(camera.animation_data or data.animation_data)
        camera.animation_data_clear()
        data.animation_data_clear()
        camera.location = plan['location']
        data.shift_x = data.shift_y = 0.0
        if ortho:
            data.ortho_scale = plan['ortho_scale']
        data.clip_end = max(data.clip_end, plan['distance'] * 4)
        entry = dict(jsonable(plan), asset=asset, size=size, lens=data.lens, sensor=data.sensor_width,
                     sensor_fit=data.sensor_fit, scale=list(camera.scale), lens_unit=data.lens_unit)
        report['framing']['cameras'][camera.name] = entry
        pending.append((camera, entry, anchors))
    bpy.context.view_layer.update()
    from bpy_extras.object_utils import world_to_camera_view
    for camera, entry, anchors in pending:
        scene.render.resolution_x, scene.render.resolution_y = entry['size']
        scene.camera = camera
        entry['projected'] = {name: [round(v, 3) for v in world_to_camera_view(scene, camera, Vector(anchors[name]))[:2]]
                              for name in ('floor', 'top', 'neck', 'hips')}


def add_results_camera(scene, cameras):
    """The 52x74 results card gets its own camera: a clone of CSP_SD (same angle and lens)."""
    source = next((c for c in cameras if c.name == 'CSP_SD'), None)
    if source is None:
        return None
    clone = source.copy()
    clone.data = source.data.copy()
    clone.name = clone.data.name = 'Results_SD'
    scene.collection.objects.link(clone)
    return clone


def render_job(job):
    boundary = Path(job['root']).resolve() / '_build/csp-render'
    work = confined_path(job['work'], boundary)
    work.mkdir(parents=True, exist_ok=True)
    settings = job.get('scene_config', {})
    renders, reports = {}, []
    initial_scene = bpy.context.scene
    for costume in job['costumes']:
        scene_path = (costume.get('art') or job.get('retail_scene') or job['template']) if job['retail'] else job['template']
        scene = append_template(scene_path, settings)
        report = inventory(scene)
        report['template_path'] = str(scene_path)
        cameras = camera_list(scene, settings)
        donor = donor_objects(scene, settings)
        if job['retail']:
            objects = donor
            rigs = [o for o in donor if o.type == 'ARMATURE']
            actions = {a.name: a for a in bpy.data.actions}
            if job.get('pose_requested', False):
                if len(rigs) != 1:
                    raise RuntimeError('Retail pose override needs one selected donor armature')
                pose(rigs[0], actions, job['action'], job['frame'] + job.get('frame_offset', 0))
        else:
            target = bounds(donor)
            # Donor armatures and helpers stay for camera constraints/drivers;
            # only donor meshes are hidden. keep_objects preserves stage/light cards.
            for obj in donor:
                if obj.type == 'MESH':
                    obj.hide_render = True
            objects, rig, actions = import_art(costume.get('art') or job['art'], scene, settings)
            # Fit in rest pose once; the selected animation must not change scale.
            rig.animation_data_create()
            for track in rig.animation_data.nla_tracks:
                track.mute = True
            rig.animation_data.action = None
            for bone in rig.pose.bones:
                bone.matrix_basis.identity()
            bpy.context.view_layer.update()
            align_art(objects, target, settings)
            pose(rig, actions, job['action'], job['frame'] + job.get('frame_offset', 0))
        apply_costume(objects, costume, settings.get('keep_objects', []))
        results_camera = add_results_camera(scene, cameras)
        if results_camera is not None:
            cameras.append(results_camera)
            settings = dict(settings, cameras=dict(settings.get('cameras', {}), Results_SD={'width': 208, 'height': 296}))
        if settings.get('framing', 'skeleton') == 'skeleton':
            rig_for_frame = rig if not job['retail'] else (rigs[0] if len(rigs) == 1 else None)
            frame_cameras(scene, cameras, rig_for_frame, objects, job, settings, report)
        # ROOT CAUSE of "every camera shows the same framing": the template binds cameras to
        # timeline markers, and every frame change (render does one) re-selects the camera the
        # marker at that frame names, whatever scene.camera was set to. Unbind them all.
        report['bound_markers'] = [(m.name, m.camera.name if m.camera else None) for m in scene.timeline_markers]
        for marker in list(scene.timeline_markers):
            marker.camera = None
        scene.render.film_transparent = True
        scene.render.image_settings.file_format = 'PNG'
        scene.render.image_settings.color_mode = 'RGBA'
        scene.render.image_settings.color_depth = '8'
        scene.render.use_file_extension = True
        scene.render.use_sequencer = False
        if settings.get('engine'):
            scene.render.engine = settings['engine']
        per_camera = settings.get('cameras', {})
        costume_out = confined_path(work / ('c%03d' % costume['index']), work)
        costume_out.mkdir(parents=True, exist_ok=True)
        outputs, render_settings = {}, {}
        base_resolution = (scene.render.resolution_x, scene.render.resolution_y)
        for index, camera in enumerate(cameras):
            scene.render.resolution_x, scene.render.resolution_y = base_resolution
            render_settings[camera.name] = camera_settings(camera, scene, per_camera.get(camera.name, {}))
            scene.camera = camera
            output = confined_path(costume_out / ('camera-%02d.png' % index), costume_out)
            scene.render.filepath = str(output)
            # Appended File Output compositor nodes must not use the template
            # author's saved output directories. Keep every write in this job.
            if scene.use_nodes:
                for node in scene.node_tree.nodes:
                    if node.type == 'OUTPUT_FILE':
                        node.base_path = str(confined_path(costume_out / 'compositor' / ('camera-%02d' % index), costume_out))
                        for slot_index, slot in enumerate(node.file_slots):
                            slot.path = 'slot-%02d-' % slot_index
            bpy.ops.render.render(write_still=True, scene=scene.name)
            if not output.is_file():
                raise RuntimeError('Renderer produced no PNG for ' + camera.name)
            outputs[camera.name] = str(output)
        renders[str(costume['index'])] = outputs
        report['camera_render_settings'] = render_settings
        reports.append(report)
        bpy.context.window.scene = initial_scene
        bpy.data.scenes.remove(scene, do_unlink=True)
        bpy.ops.outliner.orphans_purge(do_recursive=True)
    result = {'renders': renders, 'scenes': reports, 'enabled_addons': list(ADDONS)}
    confined_path(work / 'renders.json', work).write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--job', type=Path)
    ap.add_argument('--inspect-template', type=Path)
    ap.add_argument('--out', type=Path)
    args = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    enable_addons()
    if args.inspect_template:
        if not args.out:
            ap.error('--inspect-template needs --out')
        scene = append_template(args.inspect_template, {})
        output = generated_path(args.out, workspace_root())
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(inventory(scene), indent=2) + '\n', encoding='utf-8')
    elif args.job:
        render_job(json.loads(args.job.read_text(encoding='utf-8')))
    else:
        ap.error('Supply --job or --inspect-template')


if __name__ == '__main__':
    main()
