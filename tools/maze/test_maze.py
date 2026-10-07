"""Offline maze contracts; invokes Lua, never the game."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from tools.test_support import GAME, require_game, require_path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]


class MazeTests(unittest.TestCase):
    def test_fix3_contracts(self):
        result = subprocess.run([shutil.which('lua') or 'lua', 'tools/maze/fix3.lua'],
                                cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_fix2_contracts(self):
        for path in ['tools/maze/fix2.lua', 'tools/maze/world_test.lua']:
            result = subprocess.run([shutil.which('lua') or 'lua', path], cwd=ROOT,
                                    capture_output=True, text=True, timeout=130)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_world_cli_and_region_override(self):
        from tools.maze.generate import world
        base = world(7, 3, 8)
        changed = world(7, 3, 8, reroll_region=2, region_seed=99)
        self.assertNotEqual(base, changed)
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run(['python', '-B', 'tools/maze/world.py', '7',
                '--regions', '3', '--size', '8', '--output', str(Path(temp) / 'mod'),
                '--kit', str(ROOT / 'menu/out_roguelite/room-kit'), '--prepare-mod'],
                cwd=ROOT, capture_output=True, text=True, timeout=130)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertTrue((Path(temp) / 'mod/missions/world/level.lua').is_file())
            self.assertIn('connectors:', result.stdout)

    def test_fix1_contracts(self):
        result = subprocess.run([shutil.which('lua') or 'lua', 'tools/maze/fix1.lua'],
                                cwd=ROOT, capture_output=True, text=True, timeout=130)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_custom_library_assets_and_staging_failure(self):
        require_path(ROOT / 'menu/out_roguelite/room-kit/bf_floor_4m.gxmesh', 'requires generated BF room kit (menu/out_roguelite/room-kit)')
        from tools.maze.generate import generate, materialize, starters
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            library = root / 'library.lua'
            library.write_bytes(starters()['missions/maze-chunks/library.lua'].replace(
                b'bf_floor_4m', b'bf_wall_solid_4m'))
            files = generate(7, library=library)
            target = materialize(files, root / 'mod', ROOT / 'menu/out_roguelite/room-kit',
                                 'generated', prepare_mod=True)
            self.assertTrue((target / 'models/bf_wall_solid_4m.gxmesh').is_file())
            self.assertTrue((root / 'mod/missions/models/bf_kit.glow.gxtex').is_file())
            self.assertEqual((root / 'mod/missions/maze-chunks/library.lua').read_bytes(),
                             files['missions/maze-chunks/library.lua'])
            output = root / 'failed'
            output.mkdir()
            original = Path.write_bytes
            calls = 0
            def fail_midway(path, data):
                nonlocal calls
                calls += 1
                if calls == 3:
                    raise OSError('fixture write failure')
                return original(path, data)
            with patch.object(Path, 'write_bytes', fail_midway):
                with self.assertRaises(OSError):
                    materialize(files, output, ROOT / 'menu/out_roguelite/room-kit',
                                'generated', prepare_mod=True)
            self.assertEqual(list(output.iterdir()), [], 'partial mod was published')

    def test_starter_files_current(self):
        from tools.maze.generate import starters
        for path, data in starters().items():
            self.assertEqual((GAME / 'pc/scripts/examples/missions' / path).read_bytes(), data)

    def test_headless_blender_exit_export(self):
        blender = ROOT / 'experiment/tooling/ultimate/apps/Blender/blender-5.1.2-windows-x64/blender.exe'
        if not blender.is_file():
            self.skipTest('Local Blender unavailable')
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run([str(blender), '-b', '--factory-startup',
                '--python-exit-code', '1', '--python', str(ROOT / 'tools/maze/blender_exits_test.py'),
                '--', str(ROOT), temp], capture_output=True, text=True, timeout=130)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('Blender exit markers PASS', result.stdout)

    def test_python_materialization(self):
        require_path(ROOT / 'menu/out_roguelite/room-kit/bf_floor_4m.gxmesh', 'requires generated BF room kit (menu/out_roguelite/room-kit)')
        from tools.maze.generate import generate, materialize
        files = generate(7, 12)
        self.assertEqual(files, generate(7, 12))
        with tempfile.TemporaryDirectory() as temp:
            target = materialize(files, temp, ROOT / 'menu/out_roguelite/room-kit',
                                 'generated', prepare_mod=True)
            self.assertTrue((target / 'level.lua').is_file())
            self.assertTrue((target / 'models/bf_floor_4m.gxmesh').is_file())
            self.assertTrue((Path(temp) / 'scripts/main.lua').is_file())
            with self.assertRaises(FileExistsError):
                materialize(files, temp, ROOT / 'menu/out_roguelite/room-kit', 'generated')

    def test_blender_exit_contract(self):
        from tools.blender.gd_mission.exits import attach_exits
        doc = {'chunks': [{'id': 'room', 'left': 0, 'right': 130,
                           'bottom': 0, 'top': 104}], 'errors': []}
        marker = dict(name='Door', chunk='room', side='right', slot=1,
                      traversal='walk', x=130, y=16)
        attach_exits(doc, [marker])
        self.assertEqual(doc['chunks'][0]['exits'][0]['side'], 'right')
        self.assertEqual(doc['errors'], [])
        for field, value in [('slot', 2), ('side', 'front'), ('traversal', 'teleport'),
                             ('x', 104), ('chunk', 'absent')]:
            changed = dict(marker, **{field: value})
            bad = {'chunks': [dict(doc['chunks'][0], exits=[])], 'errors': []}
            attach_exits(bad, [changed])
            self.assertTrue(bad['errors'], (field, value))
        attach_exits(doc, [marker])
        self.assertTrue(doc['errors'], 'duplicate exits must refuse')

    def test_exporter_revalidates_exit_data(self):
        from tools.blender.test_gd_mission import fixture
        from tools.blender.gd_mission.validation import validate
        doc = fixture()
        doc['chunks'] = [dict(id='room', left=0, right=130, bottom=0, top=104,
                              size=dict(w=130, h=104), exits=[dict(side='right', slot=99, traversal='walk')])]
        self.assertTrue(any('exit' in error for error in validate(doc)))

    def test_lua_contracts(self):
        result = subprocess.run([shutil.which('lua') or 'lua', 'tools/maze/test_maze.lua'],
                                cwd=ROOT, capture_output=True, text=True, timeout=130)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('1000 seeds', result.stdout)


if __name__ == '__main__':
    unittest.main()
