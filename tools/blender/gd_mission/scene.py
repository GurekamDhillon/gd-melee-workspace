"""Read ordinary Blender objects into the pure exporter document."""
import json
import math
from pathlib import Path
import struct
from .constants import UNITS
from .data import coordinates
from .mesh import export_mesh, HEADER
from .collision import solid_floor_variant
from .authoring import instance_name, camera_properties
from .exits import attach_exits


def default_kit():
    # Source checkout convenience; installed add-ons use the panel's explicit path.
    return Path(__file__).resolve().parents[3] / 'menu/out_roguelite/room-kit'


def collect_scene(scene, kit_folder=None):
    import bpy
    from mathutils import Vector
    kit = Path(kit_folder or scene.get('gd_kit_folder', '') or default_kit())
    doc = dict(level=dict(version=2, units=UNITS, parts=[]), mission={},
               models={}, objects=[], markers=[], chunks=[], errors=[])
    mission = doc['mission']
    objective = scene.get('gd_objective', scene.get('objective'))
    if objective:
        mission['objective'] = {'type': objective}
        for key in ('time', 'lives'):
            if 'gd_' + key in scene: mission['objective'][key] = scene['gd_' + key]
    def problem(ob, text): doc['errors'].append(ob.name + ': ' + text)
    def position(ob):
        x, y, z = coordinates(ob.matrix_world.translation)
        return dict(x=x, y=y, z=z)
    def zone(ob):
        p = position(ob)
        matrix = ob.matrix_world
        if ob.type == 'MESH':
            points = [matrix @ Vector(v) for v in ob.bound_box]
            xs, ys = [v.x*UNITS for v in points], [v.z*UNITS for v in points]
            if max(v.y for v in points)-min(v.y for v in points) > 1e-5 or any(
                min(abs(x-min(xs)), abs(x-max(xs))) > 1e-5 or
                min(abs(y-min(ys)), abs(y-max(ys))) > 1e-5 for x, y in zip(xs, ys)):
                problem(ob, 'rectangle mesh must be an axis-aligned plane in XZ')
            return dict(x=(min(xs)+max(xs))/2, y=(min(ys)+max(ys))/2,
                        w=max(xs)-min(xs), h=max(ys)-min(ys), _name=ob.name)
        if ob.type != 'EMPTY': problem(ob, 'rectangles must be empties or mesh planes')
        # Empties are mathematical cubes with half-extent one, independent of display size.
        basis = matrix.to_3x3()
        a, b = basis @ Vector((1, 0, 0)), basis @ Vector((0, 0, 1))
        if abs(a.z) > 1e-5 or abs(b.x) > 1e-5: problem(ob, 'zone rectangle must be axis aligned in XZ')
        return dict(x=p['x'], y=p['y'], w=2*abs(a.x)*UNITS, h=2*abs(b.z)*UNITS, _name=ob.name)
    def rectangle(ob):
        z = zone(ob)
        return dict(left=z['x']-z['w']/2, right=z['x']+z['w']/2,
                    bottom=z['y']-z['h']/2, top=z['y']+z['h']/2, _name=ob.name)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    names = set()
    exits = []
    for ob in sorted(scene.objects, key=lambda ob: ob.name):
        if ob.get('gd_ignore', False) or ob.name.startswith('KIT_'): continue
        if 'gd_exit' in ob:
            if ob.type != 'EMPTY': problem(ob, 'exit markers must be empties'); continue
            p = position(ob)
            side = ob['gd_exit']
            exits.append(dict(name=ob.name, chunk=ob.get('gd_exit_chunk', ''), side=side,
                slot=ob.get('gd_exit_slot', 1), traversal=ob.get('gd_exit_traversal',
                    'walk' if side in ('left', 'right') else 'climb' if side == 'up' else 'drop'),
                x=p['x'], y=p['y']))
            continue
        if 'gd_bounds' in ob:
            kind = ob['gd_bounds']
            if kind not in ('camera', 'blast'): problem(ob, 'gd_bounds must be camera or blast')
            elif kind in doc['level']: problem(ob, 'duplicate ' + kind + ' bounds')
            else: doc['level'][kind] = rectangle(ob)
            continue
        if 'gd_chunk' in ob:
            r = rectangle(ob); r['id'] = str(ob['gd_chunk']); doc['chunks'].append(r)
            camera = camera_properties(ob)
            if camera is not None: r['camera'] = camera
            continue
        if 'gd_marker' in ob:
            if ob.type != 'EMPTY': problem(ob, 'mission markers must be empties'); continue
            kind = ob['gd_marker']
            p = position(ob); p.pop('z'); p['_name'] = ob.name
            if kind in ('goal', 'checkpoint', 'trigger'): p = zone(ob)
            doc['markers'].append(dict(name=ob.name, **{k: v for k, v in p.items() if not k.startswith('_')}))
            if kind in ('start', 'goal'):
                if kind in mission: problem(ob, 'duplicate ' + kind)
                else: mission[kind] = p
            elif kind == 'enemy':
                p.update(kind=ob.get('kind', ''), wave=ob.get('wave', 1)); mission.setdefault('enemies', []).append(p)
            elif kind == 'checkpoint': mission.setdefault('checkpoints', []).append(p)
            elif kind == 'wave':
                rule = dict(wave=ob.get('wave', 1), _name=ob.name)
                if 'time' in ob: rule['time'] = ob['time']
                else: rule.update(x=p['x'], dir=ob.get('dir', 1))
                mission.setdefault('waves', []).append(rule)
            elif kind == 'trigger':
                action = ob.get('action', '')
                p['action'] = action
                if 'once' in ob: p['once'] = bool(ob['once'])
                if action == 'wave': p['wave'] = ob.get('wave', 1)
                elif action == 'message': p['text'] = ob.get('text', '')
                elif action == 'collision':
                    target = bpy.data.objects.get(ob.get('target', ''))
                    if target is None: problem(ob, 'collision trigger target object is missing')
                    else:
                        at = position(target); p['at'] = dict(x=at['x'], y=at['y'])
                    p.update(r=float(ob.get('radius', 1))*UNITS, open=bool(ob.get('open', True)))
                mission.setdefault('triggers', []).append(p)
            else: problem(ob, 'unknown gd_marker ' + str(kind))
            continue
        if ob.type != 'MESH': continue
        part = ob.get('gd_part', ob.get('kit_part', ''))
        if not part and (kit / (ob.name.split('.')[0] + '.gxmesh')).is_file(): part = ob.name.split('.')[0]
        try:
            solid = ob.get('gd_solid', False)
            if not isinstance(solid, bool): raise ValueError('gd_solid must be true or false')
            if solid and not bool(ob.get('collision', True)): raise ValueError('gd_solid requires collision=true')
            if part:
                if Path(part).name != part or '/' in part or '\\' in part: raise ValueError('unsafe kit part name')
                binary = (kit / (part + '.gxmesh')).read_bytes()
                magic, version, nv, ni, *rest = HEADER.unpack_from(binary)
                if magic != b'GXMS' or version != 2: raise ValueError('invalid GXMS v2 kit mesh')
                sidecar = (kit / (part + '.coll.json')).read_bytes()
                meta = json.loads(sidecar); lines = len(meta.get('lines', []))
                assets = {part + '.gxmesh': binary, part + '.coll.json': sidecar}
                atlas = meta.get('atlas')
                if atlas:
                    for suffix in ('.gxtex', '.glow.gxtex'):
                        path = kit / (atlas + suffix)
                        if path.is_file(): assets[path.name] = path.read_bytes()
                        elif suffix == '.gxtex': raise ValueError('missing atlas ' + path.name)
                if solid:
                    part, variant, lines = solid_floor_variant(part, binary, sidecar)
                    # Retain atlas dependencies; omit the unmodified source mesh.
                    assets = {name: content for name, content in assets.items() if name.endswith('.gxtex')}
                    assets.update(variant)
            else:
                if solid: raise ValueError('gd_solid requires a supported kit floor; custom meshes use explicit collision')
                part, assets, nv, ni, lines = export_mesh(ob, depsgraph)
            doc['models'].update(assets)
            matrix = ob.matrix_world.to_3x3()
            a, b, depth = [matrix @ Vector(v) for v in ((1, 0, 0), (0, 0, 1), (0, 1, 0))]
            sx, sy, sz = a.length, b.length, depth.length
            if min(sx, sy, sz) < .001: raise ValueError('zero or near-zero scale')
            if abs(a.y) > 1e-5 or abs(b.y) > 1e-5 or abs(depth.x) > 1e-5 or abs(depth.z) > 1e-5 or abs(a.dot(b)) > 1e-5:
                raise ValueError('transform must preserve the XZ game plane without shear')
            angle = math.atan2(a.z, a.x)
            # Signed local Z and depth preserve two-axis mirrors as well as odd ones.
            sy *= 1 if -math.sin(angle)*b.x + math.cos(angle)*b.z > 0 else -1
            sz *= 1 if depth.y > 0 else -1
            collision = bool(ob.get('collision', True))
            p = position(ob)
            p.update(part=part, rot=math.degrees(angle), scale_x=sx, scale_y=sy, scale_z=sz,
                     collision=collision, floor_flags=int(ob.get('floor_flags', 1 if 'ramp' in part or 'stairs' in part else 3)), _name=ob.name)
            p['name'] = instance_name(ob.name, names)
            if solid: p['floor_flags'] &= ~1
            # Collision-kind reversal includes X/Z double mirrors (180 degrees).
            mirrored = any(v < 0 for v in ob.scale) or sy < 0 or sz < 0
            if collision and lines and abs(math.degrees(angle)) >= 90: problem(ob, 'rotation reverses collision direction')
            if not 0 <= p['floor_flags'] <= 3: problem(ob, 'floor_flags must be 0..3')
            doc['level']['parts'].append(p)
            doc['objects'].append(dict(name=ob.name, part=part, lines=lines, vertices=nv,
                                       indices=ni, collision=collision, mirrored=mirrored))
        except (OSError, ValueError, struct.error, KeyError, TypeError) as exc:
            problem(ob, str(exc))
    attach_exits(doc, exits)
    doc['bounds'] = doc['level'].get('camera') or doc['level'].get('blast')
    if not doc['bounds'] and doc['chunks']:
        doc['bounds'] = dict(left=min(c['left'] for c in doc['chunks']), right=max(c['right'] for c in doc['chunks']),
                             bottom=min(c['bottom'] for c in doc['chunks']), top=max(c['top'] for c in doc['chunks']))
    if not doc['bounds']:
        doc['errors'].append('Scene: add camera/blast bounds or chunk rectangles to define level bounds')
    camera = camera_properties(scene)
    if camera is not None:
        doc['level'].setdefault('camera', dict(doc['bounds'] or {})).update(camera)
    return doc
