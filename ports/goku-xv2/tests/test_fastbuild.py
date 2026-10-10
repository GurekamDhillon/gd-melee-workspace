"""build.py --gameplay-only / --auto: the Stage A staleness contract (offline; no Blender, no engine)."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import types
import unittest

PORT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PORT / 'tools'))


def load_build():
    spec = importlib.util.spec_from_file_location('goku_build_fast', PORT / 'tools/build.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FastBuild(unittest.TestCase):
    def setUp(self):
        self.b = load_build()
        self.base = self.b.ROOT / '_build/_test_fastbuild'
        shutil.rmtree(self.base, ignore_errors=True)
        self.art = self.base / 'art'
        self.out = self.base / 'out'
        self.art.mkdir(parents=True)
        (self.art / 'fighter.json').write_text(json.dumps({'key': 'kk'}))
        (self.art / 'goku.glb').write_bytes(b'glb')
        (self.out / 'mods/kk/files').mkdir(parents=True)
        (self.out / 'mods/kk/geno.json').write_text('{}')
        (self.out / 'mods/kk/files/plan.json').write_text('{}')
        (self.out / 'build').mkdir()
        self.fighter = self.art / 'fighter.json'

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    def test_no_stamp_is_stale(self):
        self.assertIn('no full-build stamp', self.b.stage_a_stale(self.fighter, self.out))

    def test_current_after_stamp(self):
        self.b.write_stamp(self.fighter, self.out)
        self.assertIsNone(self.b.stage_a_stale(self.fighter, self.out))

    def test_art_change_is_stale(self):
        self.b.write_stamp(self.fighter, self.out)
        (self.art / 'goku.glb').write_bytes(b'glb2')
        self.assertIn('goku.glb', self.b.stage_a_stale(self.fighter, self.out))

    def test_new_art_file_is_stale(self):
        self.b.write_stamp(self.fighter, self.out)
        (self.art / 'extra.blend').write_bytes(b'x')
        self.assertIn('extra.blend', self.b.stage_a_stale(self.fighter, self.out))

    def test_missing_output_is_stale(self):
        self.b.write_stamp(self.fighter, self.out)
        (self.out / 'mods/kk/files/plan.json').unlink()
        self.assertIn('output missing', self.b.stage_a_stale(self.fighter, self.out))

    def test_gameplay_inputs_are_not_stage_a_inputs(self):
        names = {p.name for p in self.b.stage_a_inputs(self.fighter)}
        self.assertNotIn('gameplay.json', names)
        self.assertFalse([p for p in self.b.stage_a_inputs(self.fighter) if p.suffix == '.genoasm'])
        self.assertIn('ground_modes.json', names)
        self.assertIn('splices.json', names)

    def run_main(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            try:
                code = self.b.main(argv)
            except SystemExit as e:
                code = e.code
        return code, buf.getvalue()

    def test_gameplay_only_refuses_when_stale(self):
        code, text = self.run_main(['--gameplay-only', '--fighter', str(self.fighter), '--out', str(self.out)])
        self.assertEqual(code, 2)
        self.assertIn('--gameplay-only refused', text)
        self.assertIn('full build', text)

    def test_gameplay_only_needs_fighter(self):
        code, _ = self.run_main(['--gameplay-only'])
        self.assertEqual(code, 2)  # argparse error

    def test_auto_falls_back_to_full_when_stale(self):
        called = []
        pipeline = types.ModuleType('tools.geno.artist.pipeline')
        pipeline.build = lambda *a, **k: (called.append(a) or 7, None)  # nonzero: stop right after Stage A
        sys.modules['tools.geno.artist.pipeline'] = pipeline
        try:
            import tools.geno.artist as artist_pkg
            old = getattr(artist_pkg, 'pipeline', None)
            artist_pkg.pipeline = pipeline
            code, text = self.run_main(['--auto', '--fighter', str(self.fighter), '--out', str(self.out)])
        finally:
            sys.modules.pop('tools.geno.artist.pipeline', None)
            if old is not None:
                artist_pkg.pipeline = old
        self.assertEqual(code, 7)
        self.assertEqual(len(called), 1)
        self.assertIn('full build needed', text)

    def test_auto_picks_gameplay_only_when_current(self):
        self.b.write_stamp(self.fighter, self.out)
        calls = []
        self.b.apply = lambda package, art_build, *a: calls.append((package, art_build)) or package
        self.b.finish_checks = lambda *a, **k: 0
        code, text = self.run_main(['--auto', '--no-audit', '--fighter', str(self.fighter), '--out', str(self.out)])
        self.assertEqual(code, 0)
        self.assertEqual(len(calls), 1)
        self.assertIn('BUILD_MODE: gameplay-only', text)


if __name__ == '__main__':
    unittest.main()
