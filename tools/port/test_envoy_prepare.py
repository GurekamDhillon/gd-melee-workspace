"""Prepare only local authored kit assets, atomically, without overwriting user files."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from tools.test_support import require_game
HERE=Path(__file__).resolve().parent
class PrepareTests(unittest.TestCase):
    def module(self):
        require_game('pc/scripts/examples/envoy/scripts')
        spec=importlib.util.spec_from_file_location('envoy_prepare',HERE/'envoy_prepare.py')
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
    def test_prepared_mod_has_existing_kit_in_all_loader_locations(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as t:
            kit=Path(t)/'kit';kit.mkdir();(kit/'bf_floor_4m.gxmesh').write_bytes(b'original kit fixture');(kit/'bf_floor_4m.coll.json').write_text('{}')
            out=Path(t)/'envoy';m.prepare(out,kit)
            for path in ('models/bf_floor_4m.gxmesh','missions/models/bf_floor_4m.gxmesh','missions/hub/models/bf_floor_4m.gxmesh'):
                self.assertEqual((out/path).read_bytes(),b'original kit fixture')
            self.assertTrue((out/'missions/hub/level.lua').exists())
            self.assertEqual((out/'scripts/main.lua').read_text(encoding='utf-8'),m.bundle())
            self.assertFalse((out/'data').exists())
    def test_complete_maze_kit_dependencies_stay_in_mission_scope(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as t:
            kit=Path(t)/'kit';kit.mkdir()
            for name in ('bf_floor_4m','bf_wall_solid_4m','bf_wall_doorway_4m','bf_door_leaf','bf_beam_4m'):
                (kit/(name+'.gxmesh')).write_bytes(b'original kit fixture')
                (kit/(name+'.coll.json')).write_text('{}')
            out=Path(t)/'envoy';m.prepare(out,kit)
            for name in ('bf_wall_solid_4m','bf_wall_doorway_4m','bf_door_leaf','bf_beam_4m'):
                self.assertEqual((out/'missions/models'/(name+'.gxmesh')).read_bytes(),b'original kit fixture')
            self.assertFalse((out/'models/models').exists())
    def test_existing_and_missing_kit_publish_nothing(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as t:
            out=Path(t)/'envoy';out.mkdir();(out/'keep').write_bytes(b'keep')
            with self.assertRaises(FileExistsError):m.prepare(out,Path(t)/'missing')
            self.assertEqual((out/'keep').read_bytes(),b'keep')
            absent=Path(t)/'absent'
            with self.assertRaises((FileNotFoundError,ValueError)):m.prepare(absent,Path(t)/'missing')
            self.assertFalse(absent.exists())
if __name__=='__main__':unittest.main()
