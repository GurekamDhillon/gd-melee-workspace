"""Offline contract tests; Blender helpers are dispatched from this same file."""
import copy
import importlib
import json
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
BLENDER = ROOT / 'experiment/tooling/ultimate/apps/Blender/blender-5.1.2-windows-x64/blender.exe'
KIT = ROOT / 'menu/out_roguelite/room-kit'


def api():
    return importlib.import_module('tools.blender.gd_mission.core')


def fixture():
    return dict(level={'version': 2, 'units': 6.5, 'parts': [
        dict(part='floor', name='Floor', x=0, y=0, z=0, rot=0, collision=True, floor_flags=3)]},
        mission={'start': {'x': 0, 'y': 1}, 'goal': {'x': 4, 'y': 1, 'w': 2, 'h': 2},
                 'objective': {'type': 'reach_goal'}},
        objects=[{'name': 'Floor', 'part': 'floor', 'lines': 1, 'indices': 6,
                  'mirrored': False}],
        markers=[{'name': 'Start', 'x': 0, 'y': 1}], chunks=[],
        bounds={'left': -10, 'right': 10, 'bottom': -10, 'top': 10}, models={})


class DataTests(unittest.TestCase):
    def test_instance_names_and_validation(self):
        from tools.blender.gd_mission.authoring import instance_name
        used = set()
        values = [instance_name(s, used) for s in ('Wall 1', 'Wall.1', 'Wall_1', '', 'x'*90, 'x'*90)]
        self.assertEqual(values[:4], ['Wall_1', 'Wall_1_1', 'Wall_1_2', 'Part'])
        self.assertEqual(len(set(values)), len(values))
        self.assertTrue(all(len(v) <= 48 for v in values))
        self.check_error(lambda d: d['level']['parts'][0].update(name='x'*49), 'instance name')
        self.check_error(lambda d: d['level']['parts'].append(copy.deepcopy(d['level']['parts'][0])), 'duplicate instance name')

    def test_camera_validation_and_chunk_export(self):
        from tools.blender.gd_mission.authoring import camera_properties
        self.assertIsNone(camera_properties({}))
        config = dict(mode='follow', window=dict(w=250, h=180), min_dist=300, fov=30)
        d = fixture(); d['level']['camera'] = config
        d['chunks'] = [dict(id='a', left=-10, right=10, bottom=-10, top=10,
                            camera=dict(mode='shaft', window=dict(w=150, h=180)))]
        self.assertEqual(api().validate(d), [])
        with tempfile.TemporaryDirectory() as tmp:
            out = api().export_document(d, tmp, 'camera')
            root = (out/'level.lua').read_text()
            chunk = (out/'chunks/a/level.lua').read_text()
            self.assertIn('["mode"]="follow"', root)
            self.assertIn('["mode"]="shaft"', chunk)
            self.assertIn('["name"]="Floor"', chunk)
        for key, bad in [('mode', 'orbit'), ('min_dist', 0), ('min_dist', True),
                         ('fov', 90), ('fov', float('nan')), ('window', {'w': 1}),
                         ('window', {'w': 0, 'h': 180})]:
            broken = copy.deepcopy(d); broken['chunks'][0]['camera'][key] = bad
            self.assertTrue(any('camera' in e for e in api().validate(broken)))

    def test_coordinate_mapping(self):
        self.assertEqual(api().coordinates((2, 3, 4)), (13, 26, -19.5))

    def test_lua_round_trip(self):
        c = api()
        value = {'quote': '"\\\n\t\x00é', 'n': 1.234567, 'yes': True,
                 'items': [1, False, {'a-b': 'end'}]}
        result = c.lua(value)
        self.assertEqual(result, c.lua(dict(reversed(list(value.items())))))
        lua = shutil.which('lua')
        if not lua:
            self.skipTest('lua is not on PATH')
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'data.lua'
            path.write_text('return ' + result, encoding='utf-8')
            script = "local x=dofile(arg[1]); assert(x.n==1.2346 and x.yes and x.items[2]==false and x.items[3]['a-b']=='end'); assert(x.quote==string.char(34,92,10,9,0)..'é')"
            check = Path(d) / 'check.lua'
            check.write_text(script, encoding='utf-8')
            subprocess.run([lua, str(check), str(path)], check=True, capture_output=True)

    def test_nonfinite_lua_rejected(self):
        with self.assertRaises(ValueError):
            api().lua(float('nan'))

    def test_content_hash_naming(self):
        c = api()
        self.assertEqual(c.model_name(b'abc'), 'mesh_ba7816bf8f01cfea414140de5dae2223b00361a3961')
        self.assertLessEqual(len(c.model_name(b'abc')), 48)  # engine basename limit
        self.assertNotEqual(c.model_name(b'abc'), c.model_name(b'abd'))

    def test_chunk_assignment_edges(self):
        chunks = [{'id': 'a', 'left': 0, 'right': 10, 'bottom': 0, 'top': 10},
                  {'id': 'b', 'left': 10, 'right': 20, 'bottom': 0, 'top': 10}]
        self.assertEqual(api().assign_chunk(10, 2, chunks), 'b')
        self.assertEqual(api().assign_chunk(0, 0, chunks), 'a')
        self.assertIsNone(api().assign_chunk(20, 2, chunks))

    def test_valid_document(self):
        self.assertEqual(api().validate(fixture()), [])

    def check_error(self, change, message):
        doc = fixture()
        change(doc)
        self.assertTrue(any(message in e for e in api().validate(doc)), api().validate(doc))

    def test_part_budget(self):
        self.check_error(lambda d: d['level'].update(parts=d['level']['parts'] * 129), '128')

    def test_line_budget_names_object(self):
        self.check_error(lambda d: d['objects'][0].update(lines=65), 'Floor: 65 collision lines exceeds 64')
        d = fixture(); d['objects'][0]['lines'] = 64
        self.assertEqual(api().validate(d), [])

    def test_index_budget(self):
        self.check_error(lambda d: d['objects'][0].update(indices=65536), '65535')

    def test_mirrored_collision(self):
        self.check_error(lambda d: d['objects'][0].update(mirrored=True), 'mirrored')
        d = fixture(); d['objects'][0].update(mirrored=True, lines=0)
        self.assertEqual(api().validate(d), [])

    def test_marker_bounds_names_object(self):
        self.check_error(lambda d: d['markers'][0].update(x=11), 'Start:')

    def test_start_required(self):
        self.check_error(lambda d: d['mission'].pop('start'), 'start')

    def test_objective_required(self):
        self.check_error(lambda d: d['mission'].pop('objective'), 'objective')

    def test_objective_requirements(self):
        for kind, enemies, goal, valid in [('reach_goal', False, False, False),
            ('defeat_all', False, True, False), ('defeat_all', True, False, True),
            ('defeat_then_goal', True, False, False), ('defeat_then_goal', True, True, True)]:
            with self.subTest(kind=kind, enemies=enemies, goal=goal):
                d = fixture(); d['mission']['objective']['type'] = kind
                if not goal: d['mission'].pop('goal')
                if enemies: d['mission']['enemies'] = [dict(kind='topi', x=0, y=1, wave=1)]
                self.assertEqual(not api().validate(d), valid)

    def test_unknown_enemy_names_marker(self):
        self.check_error(lambda d: d['mission'].update(enemies=[dict(kind='bad', x=0, y=1, wave=1, _name='Bad enemy')]), 'Bad enemy:')

    def test_overlap_names_chunks(self):
        self.check_error(lambda d: d.update(chunks=[dict(id='a', left=0, right=10, bottom=0, top=10),
            dict(id='b', left=9, right=20, bottom=0, top=10)]), 'a / b')

    def test_chunk_grid_matches_runtime(self):
        for right, bottom, top, reason in [(21, 0, 10, 'equal'), (20, 1, 11, 'align')]:
            with self.subTest(reason=reason):
                self.check_error(lambda d: d.update(chunks=[
                    dict(id='a', left=0, right=10, bottom=0, top=10),
                    dict(id='b', left=10, right=right, bottom=bottom, top=top, _name='ChunkB')]), 'ChunkB:')

    def test_wave_reference_and_limits(self):
        self.check_error(lambda d: d['mission'].update(waves=[dict(wave=2, time=1)]), 'wave 2')
        self.check_error(lambda d: d['mission']['objective'].update(lives=0), 'lives')

    def test_atomic_write_order_and_folder(self):
        c = api(); d = fixture(); d['models'] = {'floor.gxmesh': b'geometry', 'floor.coll.json': b'{}'}
        with tempfile.TemporaryDirectory() as tmp:
            calls = []
            replace = os.replace
            def observed(src, dst):
                calls.append(Path(dst).name)
                replace(src, dst)
            with patch('os.replace', side_effect=observed):
                out = c.export_document(d, tmp, 'demo')
            self.assertEqual(calls[-3:], ['level.lua', 'mission.lua', 'demo'])
            self.assertEqual((out / 'models/floor.gxmesh').read_bytes(), b'geometry')
            self.assertTrue((out / 'mission.lua').read_text().startswith('return {'))
            c.export_document(d, tmp, 'demo')
            self.assertEqual(sorted(p.name for p in out.iterdir()), ['level.lua', 'mission.lua', 'models'])

    def test_invalid_export_leaves_previous(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = fixture(); out = api().export_document(d, tmp, 'demo')
            before = (out / 'level.lua').read_bytes()
            d['mission'].pop('start')
            with self.assertRaises(ValueError): api().export_document(d, tmp, 'demo')
            self.assertEqual((out / 'level.lua').read_bytes(), before)

    def test_send_console_protocol(self):
        net = importlib.import_module('tools.blender.gd_mission.console')
        with socket.socket() as server:
            server.bind(('127.0.0.1', 0)); server.listen(1)
            received = []
            def serve():
                with server.accept()[0] as sock:
                    sock.sendall(b'console\n')
                    received.append(sock.makefile('rb').readline())
                    sock.sendall(b'reloaded\n>>> ok\n')
            worker = threading.Thread(target=serve); worker.start()
            ok, message = net.reload_mission(server.getsockname()[1]); worker.join(3)
            self.assertTrue(ok, message); self.assertEqual(received, [b'mission reload\n'])

    def test_send_no_listener_quiet(self):
        net = importlib.import_module('tools.blender.gd_mission.console')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
        self.assertFalse(net.reload_mission(port)[0])

    def test_custom_texture_header(self):
        # A malformed GXTX header makes custom geometry invisible in the game.
        from tools.blender.gd_mission.mesh import neutral_texture
        payload = neutral_texture()
        self.assertEqual(struct.unpack_from('>4sIIIIIIIIII', payload),
            (b'GXTX', 1, 6, 4, 4, 0xffffffff, 0, 64, 0, 64, 128))
        self.assertEqual(len(payload), 128)

    def test_publication_failure_restores_previous(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = fixture(); out = api().export_document(d, tmp, 'demo')
            old = (out / 'mission.lua').read_bytes()
            d['mission']['objective']['time'] = 10
            replace = os.replace
            def fail_publish(src, dst):
                if Path(src).is_dir() and Path(dst) == out and '-old-' not in str(src):
                    raise OSError('simulated publication failure')
                replace(src, dst)
            with patch('os.replace', side_effect=fail_publish):
                with self.assertRaises(OSError): api().export_document(d, tmp, 'demo')
            self.assertEqual((out / 'mission.lua').read_bytes(), old)
            self.assertEqual([p.name for p in out.parent.iterdir()], ['demo'])

    def test_lua_canonical_negative_zero_and_unicode(self):
        self.assertEqual(api().lua(-0.00001), '0')
        self.assertEqual(api().lua({'a': 'é'}), '{["a"]="é"}')

    def test_scene_all_markers_and_mapping(self):
        # Executed in the Blender scene helper; use one process per test suite scene.
        self.assertEqual(api().coordinates((-2, -1, .5)), (-13, 3.25, 6.5))

    def test_message_runtime_constraints(self):
        for text in ('', 'a\n', 'é'*41):
            with self.subTest(text=text):
                self.check_error(lambda d: d['mission'].update(triggers=[dict(
                    x=0, y=1, w=1, h=1, action='message', text=text, _name='Message')]), 'Message:')

    def test_collision_trigger_radius_limit(self):
        self.check_error(lambda d: d['mission'].update(triggers=[dict(
            x=0, y=1, w=1, h=1, action='collision', at={'x': 0, 'y': 0},
            open=True, r=201, _name='Door trigger')]), 'Door trigger:')

    def test_part_scale_limit_and_name(self):
        self.check_error(lambda d: d['level']['parts'][0].update(scale_x=101, _name='Huge floor'), 'Huge floor:')
        self.check_error(lambda d: d['level']['parts'][0].update(part='a'*49, _name='Long name'), 'Long name:')
        d = fixture(); d['level']['parts'][0]['part'] = 'a'*48
        self.assertEqual(api().validate(d), [])

    def test_atomic_write_unchanged_keeps_file_and_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'file'
            api().atomic_write(path, b'abc')
            os.utime(path, ns=(1234567890000000000, 1234567890000000000))
            before = path.stat()
            api().atomic_write(path, b'abc')
            self.assertEqual((path.stat().st_ino, path.stat().st_mtime_ns), (before.st_ino, before.st_mtime_ns))
            api().atomic_write(path, b'abd')
            self.assertEqual(path.read_bytes(), b'abd')
            self.assertNotEqual(path.stat().st_mtime_ns, before.st_mtime_ns)

    def test_shared_atlas_and_unchanged_generation_files(self):
        d = fixture()
        d['level']['parts'][0].update(part='floor', x=-2)
        d['level']['parts'].append(dict(d['level']['parts'][0], name='Floor_2', x=2))
        d['chunks'] = [dict(id='a', left=-10, right=0, bottom=-10, top=10),
                       dict(id='b', left=0, right=10, bottom=-10, top=10)]
        d['models'] = {'floor.gxmesh': b'mesh', 'floor.coll.json': b'{"version":1,"atlas":"kit","lines":[]}',
                       'kit.gxtex': b'colour', 'kit.glow.gxtex': b'glow'}
        with tempfile.TemporaryDirectory() as tmp:
            out = api().export_document(d, tmp, 'demo')
            atlas = out / 'models/kit.gxtex'
            stamp = 1234567890000000000
            for path in (atlas, out/'models/kit.glow.gxtex', out/'models/floor.gxmesh'):
                os.utime(path, ns=(stamp, stamp))
            before = atlas.stat()
            for chunk in ('a', 'b'):
                ref = out / f'chunks/{chunk}/models/kit.gxtex'
                self.assertEqual(ref.resolve(), atlas.resolve())
                self.assertTrue(os.path.samefile(ref, atlas))
            d['mission']['objective']['time'] = 10
            api().export_document(d, tmp, 'demo')
            self.assertEqual((atlas.stat().st_ino, atlas.stat().st_mtime_ns), (before.st_ino, before.st_mtime_ns))
            self.assertEqual((out/'models/floor.gxmesh').stat().st_mtime_ns, stamp)
            self.assertEqual((out/'models/kit.glow.gxtex').stat().st_mtime_ns, stamp)
            d['models']['floor.gxmesh'] = b'edited geometry'
            api().export_document(d, tmp, 'demo')
            self.assertEqual(atlas.stat().st_mtime_ns, stamp)
            self.assertEqual((out/'models/floor.gxmesh').read_bytes(), b'edited geometry')
            for chunk in ('a', 'b'):
                self.assertEqual((out/f'chunks/{chunk}/models/floor.gxmesh').resolve(), (out/'models/floor.gxmesh').resolve())

    def test_asset_memory_estimate_and_warning(self):
        from tools.blender.gd_mission.assets import estimate_asset_memory, asset_warnings
        d = fixture()
        d['level']['parts'] *= 10
        d['models'] = {'floor.gxmesh': b'x'*100, 'floor.coll.json': b'{"atlas":"kit","lines":[]}',
                       'kit.gxtex': struct.pack('>4sIIIIIIIIII', b'GXTX', 1, 6, 4, 4, 0xffffffff, 0, 64, 0, 64, 128) + bytes(84),
                       'kit.glow.gxtex': struct.pack('>4sIIIIIIIIII', b'GXTX', 1, 6, 4, 4, 0xffffffff, 0, 64, 0, 64, 128) + bytes(84)}
        self.assertEqual(estimate_asset_memory(d), 228)  # 100 mesh + 64 colour + 64 glow; sidecar not pinned
        with patch('tools.blender.gd_mission.constants.ASSET_MEMORY_BUDGET', 250):
            self.assertTrue(any('228' in w and '250' in w for w in asset_warnings(d)))
        with patch('tools.blender.gd_mission.constants.ASSET_MEMORY_BUDGET', 200):
            self.assertTrue(any('228' in e and '200' in e for e in api().validate(d)))

    @unittest.skipUnless(os.name == 'nt', 'NTFS junction fallback is Windows only')
    def test_shared_model_reference_junction_fallback(self):
        from tools.blender.gd_mission.references import model_reference
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pool = root / 'models'; pool.mkdir(); (pool / 'mesh.gxmesh').write_bytes(b'geometry')
            link = root / 'chunks/a/models'
            with patch('os.symlink', side_effect=OSError('symlink privilege unavailable')):
                model_reference(link, pool)
            self.assertEqual((link / 'mesh.gxmesh').resolve(), (pool / 'mesh.gxmesh').resolve())
            self.assertEqual((link / 'mesh.gxmesh').read_bytes(), b'geometry')
            # Removing the directory reference must leave the shared pool alone.
            link.rmdir()
            self.assertEqual((pool / 'mesh.gxmesh').read_bytes(), b'geometry')

    def test_shared_model_reference_relative_relocation(self):
        from tools.blender.gd_mission.references import model_reference
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'original'; pool = root / 'models'
            pool.mkdir(parents=True); (pool / 'mesh.gxmesh').write_bytes(b'geometry')
            link = root / 'chunks/a/models'; model_reference(link, pool)
            if not link.is_symlink(): self.skipTest('NTFS junctions require re-export after relocation')
            moved = Path(tmp) / 'renamed'; root.rename(moved)
            self.assertEqual((moved / 'chunks/a/models/mesh.gxmesh').resolve(), (moved / 'models/mesh.gxmesh').resolve())
            self.assertEqual((moved / 'chunks/a/models/mesh.gxmesh').read_bytes(), b'geometry')

    def test_solid_floor_variant_preserves_default(self):
        from tools.blender.gd_mission.collision import solid_floor_variant
        original = b'{"version":1,"atlas":"kit","lines":[["floor",-13,0,13,0,3]]}'
        name, assets, count = solid_floor_variant('bf_floor_4m', b'mesh', original)
        self.assertTrue(name.startswith('mesh_'))
        self.assertLessEqual(len(name), 48)
        self.assertEqual(count, 2)
        self.assertEqual(json.loads(assets[name+'.coll.json'])['lines'],
                         [['floor', -13, 0, 13, 0, 2], ['ceiling', 13, -2.6, -13, -2.6, 0]])
        self.assertEqual(json.loads(original)['lines'], [['floor', -13, 0, 13, 0, 3]])
        with self.assertRaisesRegex(ValueError, 'gd_solid'):
            solid_floor_variant('bf_wall_solid_4m', b'mesh', original)


class BlenderTests(unittest.TestCase):
    def run_blender(self, mode):
        if not BLENDER.exists(): self.skipTest('Blender executable missing')
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
                       BLENDER_USER_RESOURCES=str(Path(tmp) / 'blender-user'))
            run = subprocess.run([str(BLENDER), '--factory-startup', '--background',
                '--python-exit-code', '1', '--python', str(Path(__file__).resolve()), '--', mode, tmp],
                capture_output=True, text=True, timeout=240, env=env)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertTrue((Path(tmp) / 'PASS').exists(), run.stdout + run.stderr)

    def test_headless_scene_export(self): self.run_blender('scene')
    def test_headless_kit_collision_export(self): self.run_blender('kit')


def blender_helper(mode, tmp):
    import bpy
    sys.path.insert(0, str(ROOT))
    if mode == 'scene':
        from tools.blender.gd_mission.scene import collect_scene
        from tools.blender.gd_mission.core import export_document
        bpy.ops.wm.read_factory_settings(use_empty=True)
        scene = bpy.context.scene
        scene['gd_objective'] = 'reach_goal'
        scene['gd_camera_mode'] = 'follow'
        scene['gd_camera_window_w'] = 250.0
        scene['gd_camera_window_h'] = 180.0
        scene['gd_camera_min_dist'] = 300.0
        scene['gd_camera_fov'] = 30.0
        def empty(name, loc, **props):
            ob = bpy.data.objects.new(name, None); scene.collection.objects.link(ob)
            ob.location = loc
            for k, v in props.items(): ob[k] = v
            return ob
        empty('Start', (0, 0, 1), gd_marker='start')
        empty('Goal', (3, 0, 1), gd_marker='goal').scale = (.5, 1, 1)
        empty('Enemy', (-1, 0, 1), gd_marker='enemy', kind='topi', wave=2)
        empty('Checkpoint', (1, 0, 1), gd_marker='checkpoint').scale = (.25, 1, .5)
        empty('Wave', (1, 0, 1), gd_marker='wave', wave=2, time=5)
        empty('Trigger', (-1, 0, 1), gd_marker='trigger', action='message', text='Go!').scale = (.5, 1, .5)
        empty('Camera', (0, 0, 0), gd_bounds='camera').scale = (10, 1, 10)
        empty('ChunkA', (-2, 0, 0), gd_chunk='a').scale = (2, 1, 10)
        empty('ChunkB', (2, 0, 0), gd_chunk='b').scale = (2, 1, 10)
        bpy.data.objects['ChunkB']['gd_camera_mode'] = 'shaft'
        for name, x in [('bf_floor_4m', -3), ('bf_floor_4m', -1),
                        ('bf_ramp_4m_rise2m', 1), ('bf_wall_solid_4m', 3)]:
            bpy.ops.mesh.primitive_cube_add(location=(x, 0, 0))
            bpy.context.object['gd_part'] = name
        bpy.ops.mesh.primitive_cube_add(location=(1, 0, 3))
        bpy.context.object.name = 'Custom cube'
        bpy.context.view_layer.update()
        doc = collect_scene(scene, KIT)
        assert doc['level']['camera']['window'] == {'w': 250.0, 'h': 180.0}
        assert doc['chunks'][1]['camera'] == {'mode': 'shaft'}
        assert len({p['name'] for p in doc['level']['parts']}) == len(doc['level']['parts'])
        assert next(p for p in doc['level']['parts'] if p['_name'] == 'Custom cube')['name'] == 'Custom_cube'
        assert doc['mission']['start']['y'] == 6.5
        assert doc['mission']['goal']['w'] == 6.5
        assert doc['mission']['enemies'][0]['kind'] == 'topi'
        assert doc['mission']['waves'][0]['time'] == 5
        assert doc['mission']['triggers'][0]['text'] == 'Go!'
        out = export_document(doc, tmp, 'test')
        assert (out / 'chunks/a/level.lua').exists()
        assert (out / 'chunks/b/models/bf_ramp_4m_rise2m.gxmesh').exists()
        assert (out / 'mission.lua').exists()
        assert len(list((out / 'chunks/b/models').glob('mesh_*.gxmesh'))) == 1
        assert not list(out.rglob('*.tmp'))
        lua = shutil.which('lua')
        if lua and (ROOT / 'melee/pc/scripts/examples/missions/scripts/loader.lua').is_file():
            check = Path(tmp) / 'runtime-check.lua'
            manifest = {}
            for path in out.rglob('*'):
                if path.is_dir():
                    manifest['missions/test/' + path.relative_to(out).as_posix() + '/'] = [
                        dict(name=p.name, dir=p.is_dir()) for p in path.iterdir()]
            from tools.blender.gd_mission.data import lua as emit
            runtime = (ROOT / 'melee/pc/scripts/examples/missions/scripts').as_posix()
            check.write_text('local D={}\nlocal base=' + emit(runtime) + '\n' +
                'D.mission=dofile(base.."/mission.lua")\n' +
                'D.validator=dofile(base.."/validator.lua")(D)\nD.loader=dofile(base.."/loader.lua")(D)\n' +
                'local entries=' + emit(manifest) + '\nlocal root=' + emit(str(Path(tmp)).replace('\\', '/')) + '\n' +
                'local g={mod_list=function(p) return entries[p] end, mod_stamp=function() return 1 end,\n' +
                'mod_read=function(p) local f=io.open(root.."/"..p,"rb");if not f then return nil end;local s=f:read("a");f:close();return s end}\n' +
                'local d=D.loader.folder(g,"test");assert(#d.chunks==2); assert(#d.chunks[1].level.parts==2);\n', encoding='utf-8')
            checked = subprocess.run([lua, str(check)], capture_output=True, text=True)
            assert checked.returncode == 0, checked.stdout + checked.stderr
        from tools.blender.gd_mission import register, unregister
        register()
        assert bpy.ops.gd_mission.camera(clear=True) == {'FINISHED'}
        assert not any(k.startswith('gd_camera_') for k in scene.keys())
        defaults = collect_scene(scene, KIT)
        assert 'mode' not in defaults['level']['camera']
        assert bpy.ops.gd_mission.camera() == {'FINISHED'}
        assert collect_scene(scene, KIT)['level']['camera']['mode'] == 'follow'
        bpy.context.view_layer.objects.active = bpy.data.objects['ChunkB']
        assert bpy.ops.gd_mission.camera(chunk=True, clear=True) == {'FINISHED'}
        assert 'camera' not in next(c for c in collect_scene(scene, KIT)['chunks'] if c['id']=='b')
        assert bpy.ops.gd_mission.camera(chunk=True) == {'FINISHED'}
        assert bpy.data.objects['ChunkB']['gd_camera_mode'] == 'chunk'
        unregister()
        floor = next(ob for ob in scene.objects if ob.get('gd_part') == 'bf_floor_4m')
        floor['gd_solid'] = True
        solid = collect_scene(scene, KIT)
        solid_part = next(p for p in solid['level']['parts'] if p['_name'] == floor.name)
        side = json.loads(solid['models'][solid_part['part']+'.coll.json'])
        assert any(l[0] == 'ceiling' for l in side['lines'])
        assert solid_part['floor_flags'] == 2
        floor['collision'] = False
        refused = collect_scene(scene, KIT)
        assert any(floor.name+':' in e and 'gd_solid' in e for e in refused['errors'])
        del floor['gd_solid']; del floor['collision']
        # Custom geometry identities change with edited geometry but not placement.
        mesh_name = next(p['part'] for p in doc['level']['parts'] if p['part'].startswith('mesh_'))
        cube = bpy.data.objects['Custom cube']
        cube.location.x += .1; bpy.context.view_layer.update()
        again = collect_scene(scene, KIT)
        assert mesh_name in [p['part'] for p in again['level']['parts']]
        cube.data.vertices[0].co.x += .1; bpy.context.view_layer.update()
        changed = collect_scene(scene, KIT)
        assert mesh_name not in [p['part'] for p in changed['level']['parts']]
        import math
        bpy.ops.mesh.primitive_plane_add()
        rectangle = bpy.context.object
        rectangle.name = 'Rotated bounds'
        rectangle['gd_bounds'] = 'blast'
        rectangle.rotation_euler = (math.pi/2, math.pi/6, 0)
        bpy.context.view_layer.update()
        rotated = collect_scene(scene, KIT)
        assert any('Rotated bounds:' in e for e in rotated['errors'])
    elif mode == 'kit':
        import runpy
        module = runpy.run_path(str(ROOT / 'melee/pc/assets_src/bf_interior/export_kit.py'))
        # Exercise actual kit geometry writer without rebaking unchanged atlases.
        parts = module['build_parts']()
        ob = module['combined'](parts, False); module['unwrap'](ob, 256)
        ob.data.calc_loop_triangles()
        unchanged = ['Floor_4m', 'Floor_2m', 'Balcony_4m', 'Floor_Opening_4m',
                     'Ramp_4m_Rise2m', 'Stairs_4m_Rise2m']
        for i, (name, collection) in enumerate(parts):
            stem = module['model_name'](name)
            if any(pid.value == i for pid in ob.data.attributes['part_id'].data):
                module['write_part'](Path(tmp) / (stem + '.gxmesh'), ob.data, i,
                    i * module['SPACING'], tuple(collection['module_size']))
            data = module['sidecar'](module['COLLISION'].get(name, []))
            (Path(tmp) / (stem + '.coll.json')).write_text(json.dumps(data, separators=(',', ':')) + '\n')
            assert len(data['lines']) <= 64
            baseline = KIT / (stem + '.coll.json')
            if baseline.exists():
                floors_before = [l for l in json.loads(baseline.read_bytes())['lines'] if l[0] == 'floor']
                floors_after = [l for l in data['lines'] if l[0] == 'floor']
                if not name.startswith(('Wall_', 'Corner_')):
                    assert json.dumps(floors_before).encode() == json.dumps(floors_after).encode(), stem
            if name in unchanged:
                before = (KIT / (stem + '.coll.json')).read_bytes()
                assert (Path(tmp) / (stem + '.coll.json')).read_bytes().rstrip(b'\r\n') == before.rstrip(b'\r\n'), stem
            if name.startswith(('Wall_', 'Corner_')) and name not in ('Wall_Doorway_4m', 'Wall_Window_4m'):
                assert any(l[0] in ('left_wall', 'right_wall') for l in data['lines']), name
                assert any(l[0] == 'ceiling' for l in data['lines']), name
            for kind, x0, y0, x1, y1, flags in data['lines']:
                if kind == 'right_wall': assert y0 > y1, (name, kind)
                if kind == 'left_wall': assert y0 < y1, (name, kind)
                if kind == 'ceiling': assert x0 > x1, (name, kind)
        assert module['COLLISION']['Wall_Doorway_4m'] == []
        assert module['COLLISION']['Wall_Window_4m'] == []
        for name in ('Floor_4m', 'Floor_2m', 'Balcony_4m', 'Floor_Opening_4m'):
            assert all(l['kind'] == 'floor' for l in module['COLLISION'][name])
        for name in ('Wall_Solid_4m', 'Wall_Side_Return', 'Corner_Inside_4m', 'Corner_Outside_4m'):
            lines = module['COLLISION'][name]
            left = next(l for l in lines if l['kind'] == 'left_wall')
            right = next(l for l in lines if l['kind'] == 'right_wall')
            assert left['x0'] < right['x0'] and left['z0'] < left['z1'] and right['z0'] > right['z1'], name
    (Path(tmp) / 'PASS').write_text('ok')


if __name__ == '__main__':
    if '--' in sys.argv:
        blender_helper(*sys.argv[sys.argv.index('--') + 1:])
    else:
        unittest.main()
