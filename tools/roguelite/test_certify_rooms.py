#!/usr/bin/env python3
"""Pure tests for the native room certification harness.

These validate plans, the console parser, refusal/state handling and install
safety. They do NOT run the game and cannot show that a recipe traverses. The
native verdict is always pending or manual.
"""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location('certify_rooms', HERE / 'certify_rooms.py')
certify = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(certify)


def make_console(mapping, scalars=None, clock=None):
    """Build a Console whose command handler is a scripted mapping."""
    scalars = scalars or {}
    calls = []
    now = {'t': 0.0}

    def command(text, category='observation'):
        calls.append({'command': text, 'category': category})
        if text in scalars:
            return str(scalars[text])
        for key, value in mapping.items():
            if text == key or text.startswith(key):
                return value(text) if callable(value) else value
        return ''

    def sleep(seconds):
        now['t'] += seconds

    console = certify.Console(command, sleep=sleep, clock=lambda: now['t'], note=lambda r: None)
    console.calls = calls
    console.now = now
    return console


def trace(*samples):
    return [{'x': x, 'y': y, 'vy': vy, 'airborne': air, 'frame': i}
            for i, (x, y, vy, air) in enumerate(samples)]


class ParserTests(unittest.TestCase):
    def test_rows_parse_typed_values(self):
        output = 'certify_status phase=ready certified=false samples=12 trunc=true name=abc'
        rows = certify.parse_rows(output, 'certify_status')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['phase'], 'ready')
        self.assertIs(rows[0]['certified'], False)
        self.assertEqual(rows[0]['samples'], 12.0)
        self.assertIs(rows[0]['trunc'], True)
        self.assertEqual(rows[0]['name'], 'abc')

    def test_rows_ignore_ansi_and_other_text(self):
        output = '\x1b[32mcertify_trace i=1 x=-4.5 y=0\x1b[0m\nnoise\ncertify_trace i=2 x=-3 y=1'
        rows = certify.parse_rows(output, 'certify_trace')
        self.assertEqual([r['i'] for r in rows], [1.0, 2.0])
        self.assertEqual(rows[0]['x'], -4.5)

    def test_scalar_reads_last_number(self):
        self.assertEqual(certify.parse_scalar('junk\n60\n'), 60.0)
        self.assertIs(certify.parse_scalar('false'), False)
        with self.assertRaises(ValueError):
            certify.parse_scalar('no scalar here')

    def test_no_prefix_match_inside_identifier(self):
        self.assertEqual(certify.parse_rows('xcertify_status a=1', 'certify_status'), [])


class PlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inspection = certify.inspect_recipes(certify.GAME)

    def test_inspection_available_and_uncertified(self):
        if not self.inspection['available']:
            self.skipTest('lua/recipe modules unavailable: ' + str(self.inspection['reason']))
        by = {r['template']: r for r in self.inspection['recipes']}
        for template in certify.REQUIRED_TEMPLATES:
            self.assertIn(template, by)
            self.assertIs(by[template]['certified'], False)
            self.assertTrue(by[template]['sockets'])

    def test_plans_cover_required_segments(self):
        if not self.inspection['available']:
            self.skipTest('lua/recipe modules unavailable')
        plans, errors = certify.build_plans(self.inspection)
        self.assertEqual(errors, [])
        by = {p['template']: p for p in plans}
        self.assertEqual(set(by), set(certify.REQUIRED_TEMPLATES))
        ids = {s['id'] for s in by['branch_y']['segments']}
        self.assertIn('ascent', ids)
        self.assertIn('return', ids)
        self.assertTrue(any(s['kind'] == 'fork' for s in by['branch_y']['segments']))
        entries = {s['id'] for s in by['rejoin_merge']['segments']}
        self.assertEqual(entries, {'entry_left', 'entry_top'})
        drop = next(s for s in by['junction_cross']['segments'] if s['id'] == 'drop_through')
        self.assertTrue(drop['requires_fall'])
        self.assertIsNone(drop['target'])
        self.assertIsNotNone(drop['fixture'])
        kinds = {s['kind'] for s in by['junction_cross']['segments']}
        self.assertIn('safe-arrival', kinds)
        self.assertIn('alternate-return', kinds)
        one_way = next(s for s in by['junction_cross']['segments'] if s['id'] == 'drop_one_way')
        self.assertTrue(one_way['forbid_climb_back'])

    def test_plans_reference_declared_sockets(self):
        if not self.inspection['available']:
            self.skipTest('lua/recipe modules unavailable')
        plans, _ = certify.build_plans(self.inspection)
        for plan in plans:
            valid = {s['socket'] for s in plan['sockets']}
            for segment in plan['segments']:
                for name in (segment['source'], segment['target']):
                    if name is not None:
                        self.assertIn(name, valid, '%s: unknown socket %s' % (plan['template'], name))

    def test_plan_is_json_and_never_certified(self):
        if not self.inspection['available']:
            self.skipTest('lua/recipe modules unavailable')
        plans, _ = certify.build_plans(self.inspection)
        text = json.dumps(plans)
        self.assertNotIn('"certified": true', text)
        for plan in plans:
            self.assertFalse(plan['certified'])
            for segment in plan['segments']:
                self.assertEqual(segment['status'], 'proposed-needs-native-validation')

    def test_unknown_template_is_an_error(self):
        self.assertEqual(certify.build_plans({'available': True, 'recipes': []}, ['nope'])[0], [])
        self.assertEqual(certify.build_plans({'available': True, 'recipes': []}, ['nope'])[1], ['nope: not in the room catalogue'])

    def test_inspection_unavailable_is_reported(self):
        plans, errors = certify.build_plans({'available': False, 'reason': 'no lua'})
        self.assertEqual(plans, [])
        self.assertEqual(errors, ['no lua'])


class ParseRosterTests(unittest.TestCase):
    def test_mobility_profiles_exist_in_roster(self):
        roster = (certify.RT / 'roster.lua').read_text()
        ids = set(certify.re.findall(r"\{id='([a-z]+)',name=", roster))
        self.assertTrue(ids)
        for profile in certify.MOBILITY_PROFILES:
            self.assertIn(profile['fighter'], ids, profile['id'])


class ClassifyTests(unittest.TestCase):
    def test_arrival(self):
        result = certify.classify_trace({'truncated': False},
                                        trace((-42, 0, 0, False), (-30, 0, 0, False), (39, 26, 0, False)),
                                        floor_y=0, target={'x': 39, 'y': 26})
        self.assertEqual(result['status'], 'arrived')
        self.assertTrue(result['checks']['arrived'])

    def test_fall(self):
        result = certify.classify_trace({'truncated': False},
                                        trace((20, 0, 0, False), (0, -5, -3, True), (0, -40, -3, True)),
                                        floor_y=0, requires_fall=True)
        self.assertEqual(result['status'], 'fell')
        self.assertTrue(result['checks']['fell'])

    def test_drop_without_fall_fails_even_if_target_reached(self):
        result = certify.classify_trace({'truncated': False},
                                        trace((20, 0, 0, False), (20, 0, 0, False)),
                                        floor_y=0, target={'x': 39, 'y': 26}, requires_fall=True)
        self.assertEqual(result['status'], 'failed-no-fall')

    def test_stuck(self):
        samples = trace(*[(10, 0, 0, False)] * 120)
        result = certify.classify_trace({'truncated': False}, samples, floor_y=0)
        self.assertEqual(result['status'], 'stuck')

    def test_no_samples(self):
        self.assertEqual(certify.classify_trace({}, [], floor_y=0)['status'], 'no-samples')

    def test_one_way_violated_when_climb_back(self):
        result = certify.classify_trace({},
                                        trace((20, 0, 0, False), (0, -40, 0, True), (12, 0, 0, False)),
                                        floor_y=0, requires_fall=True, forbid_climb_back=True)
        self.assertEqual(result['status'], 'one-way-violated')
        self.assertTrue(result['checks']['climb_back'])

    def test_seam_pop_candidate_flagged_for_manual_review(self):
        result = certify.classify_trace({'truncated': False},
                                        trace((-10, 0, 0, False), (-9, 0, 0, True), (-8, 0, 0, False)),
                                        floor_y=0)
        self.assertTrue(result['checks']['seam_pop_candidate'])
        self.assertTrue(result['manual_review'])

    def test_truncated_trace_needs_review(self):
        result = certify.classify_trace({'truncated': True},
                                        trace((0, 0, 0, False), (1, 0, 0, False)), floor_y=0)
        self.assertTrue(any('truncated' in note for note in result['manual_review']))


class VerdictTests(unittest.TestCase):
    def test_never_certifies_even_with_all_arrivals(self):
        outcomes = [{'id': 'a', 'status': 'arrived'}, {'id': 'b', 'status': 'fell'}]
        verdict = certify.recipe_verdict('branch_y', 2, outcomes, native_run=True)
        self.assertFalse(verdict['certified'])
        self.assertEqual(verdict['auto_certification'], 'forbidden')
        self.assertEqual(verdict['verdict'], 'manual-review-required')
        self.assertTrue(verdict['requires_human_review'])

    def test_pending_without_native_run(self):
        verdict = certify.recipe_verdict('branch_y', 2, [], native_run=False)
        self.assertEqual(verdict['verdict'], 'pending-native-run')
        self.assertFalse(verdict['certified'])

    def test_failed_and_inconclusive_are_listed(self):
        outcomes = [{'id': 'stuck_seg', 'status': 'stuck'}, {'id': 'maybe', 'status': 'inconclusive'}]
        verdict = certify.recipe_verdict('x', 2, outcomes, native_run=True)
        self.assertEqual(verdict['failed_segments'], ['stuck_seg'])
        self.assertEqual(verdict['inconclusive_segments'], ['maybe'])


class DriverRefusalTests(unittest.TestCase):
    def driver(self, mapping, scalars=None):
        return certify.CertificationDriver(make_console(mapping, scalars))

    def test_missing_api_is_precise(self):
        console = make_console({
            'certify_apis': 'certify_api name=model_load present=true\ncertify_api name=stage_add_line present=false',
        })
        with self.assertRaises(certify.MissingAPI) as caught:
            certify.CertificationDriver(console).ensure_apis()
        self.assertIn('stage_add_line', str(caught.exception))

    def test_normal_speed_refuses_turbo_target(self):
        console = make_console({}, scalars={'= gd.perf().target': 120})
        with self.assertRaises(certify.UnsupportedRun):
            certify.CertificationDriver(console).ensure_normal_speed(sample=False)

    def test_normal_speed_refuses_paused(self):
        console = make_console({}, scalars={'= gd.perf().target': 60, '= gd.paused()': 'true'})
        with self.assertRaises(certify.UnsupportedRun):
            certify.CertificationDriver(console).ensure_normal_speed(sample=False)

    def test_normal_speed_refuses_fly(self):
        console = make_console({}, scalars={'= gd.perf().target': 60, '= gd.paused()': 'false',
                                            '= gd.fly(1)': 'true'})
        with self.assertRaises(certify.UnsupportedRun):
            certify.CertificationDriver(console).ensure_normal_speed(sample=False)

    def test_normal_speed_refuses_accelerated_rate(self):
        def frame(text):
            return '100'
        # clock advances only via sleep(0.5); frame jumps by 5000 -> rate 10000
        frames = iter(['0', '5000'])
        console = make_console({'= gd.match().frame': lambda t: next(frames)},
                               scalars={'= gd.perf().target': 60, '= gd.paused()': 'false',
                                        '= gd.fly(1)': 'false', '= gd.fly(2)': 'false'})
        with self.assertRaises(certify.UnsupportedRun):
            certify.CertificationDriver(console).ensure_normal_speed(sample=True)

    def test_wrong_port_refused(self):
        with self.assertRaises(certify.UnsupportedRun):
            certify.CertificationDriver(make_console({}), port=2)

    def test_cpu_port_refused(self):
        console = make_console({
            'certify_scene': 'certify_scene p1=fox/c0 ok=true result=nil',
            'certify_status': 'certify_status phase=idle template=nil',
        }, scalars={
            '= gd.player(1) ~= nil': 'true', '= gd.player(2) ~= nil': 'true',
            '= gd.player(1).cpu': 'true',
        })
        with self.assertRaises(certify.UnsupportedRun):
            certify.CertificationDriver(console).launch_scene('fox')


class DriverStateTests(unittest.TestCase):
    def test_replay_renders_real_pad_inputs_on_one_port(self):
        console = make_console({})
        driver = certify.CertificationDriver(console, sleep_frames=lambda n: None)
        driver.replay([('walk', 1, 60), ('neutral', 10), ('button', 'A', 4), ('down', 30)])
        rendered = [c['command'] for c in console.calls]
        self.assertIn('input 1 none 60 127 0', rendered)
        self.assertIn('input 1 none 10', rendered)
        self.assertIn('input 1 A 4', rendered)
        self.assertIn('input 1 DOWN 30', rendered)
        self.assertTrue(all('input 1' in c for c in rendered if c.startswith('input')))

    def test_cleanup_releases_pad_and_calls_native_cleanup(self):
        console = make_console({'certify_cleanup': 'certify_cleanup errors=0'})
        driver = certify.CertificationDriver(console, sleep_frames=lambda n: None)
        driver.replay([('walk', 1, 10)])
        errors = driver.cleanup()
        rendered = [c['command'] for c in console.calls]
        self.assertIn('gd.release_pad(1)', rendered)
        self.assertIn('certify_cleanup', rendered)
        self.assertEqual(errors, [])

    def test_cleanup_reports_native_errors(self):
        console = make_console({'certify_cleanup': 'certify_cleanup_error message=stage_remove_9\ncertify_cleanup errors=1'})
        driver = certify.CertificationDriver(console, sleep_frames=lambda n: None)
        errors = driver.cleanup()
        self.assertEqual(errors, ['stage_remove_9'])

    def test_segment_uses_fixture_about_placement_and_never_certifies(self):
        console = make_console({
            'certify_arm': 'certify_arm label=drop socket=branch_b target_x=39 target_y=26 floor_y=0 start_x=20 start_y=0 limit=900',
            'certify_result': ('certify_result label=drop socket=branch_b target_x=39 target_y=26 floor_y=0 samples=2 truncated=false min_y=-40 max_y=0 air_frames=1 start_x=20 start_y=0\n'
                               'certify_trace i=1 frame=1 x=20 y=0 vx=-2 vy=0 airborne=false action=14\n'
                               'certify_trace i=2 frame=2 x=0 y=-40 vx=0 vy=-3 airborne=true action=14'),
        })
        driver = certify.CertificationDriver(console, sleep_frames=lambda n: None)
        segment = {'id': 'drop_through', 'natural': True, 'fixture': {'x': 20, 'y': 0},
                   'requires_fall': True, 'target': None, 'source': None, 'probes': [[('walk', -1, 10)]]}
        outcome = driver.certify_segment(segment, None, 0.0)
        self.assertEqual(outcome['status'], 'fell')
        rendered = [c['command'] for c in console.calls]
        self.assertIn('certify_place_at 20.000 0.000', rendered)
        self.assertIn('certify_arm_coords drop_through none none', rendered)

    def test_arm_window_uses_socket_target_when_present(self):
        console = make_console({})
        driver = certify.CertificationDriver(console, sleep_frames=lambda n: None)
        driver.arm_window('ascent', {'x': 39.0, 'y': 26.0})
        self.assertIn('certify_arm_coords ascent 39.0 26.0', [c['command'] for c in console.calls])
        driver.arm_window('drop')
        self.assertIn('certify_arm_coords drop none none', [c['command'] for c in console.calls])


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = Path(self.temp.name) / 'app'
        (self.app / 'mods').mkdir(parents=True)
        (self.app / 'scripts-data/roguelite_main').mkdir(parents=True)
        (self.app / 'scripts-data/roguelite_main/checkpoint-a.txt').write_text('user-save')
        (self.app / 'mods/enabled.txt').write_text('production_mod\n')
        (self.app / 'melee').write_bytes(b'fake-shared-binary')

    def tearDown(self):
        self.temp.cleanup()

    def kit_available(self):
        return (certify.ROOM_KIT / 'bf_floor_4m.gxmesh').is_file()

    def test_install_requires_explicit_app_dir(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            certify.main(['install'])

    def test_install_preserves_enabled_saves_and_binary(self):
        if not self.kit_available():
            self.skipTest('BF room kit not present')
        result = certify.install(self.app)
        self.assertTrue(Path(result['mod_dir'], 'scripts/main.lua').is_file())
        self.assertEqual((self.app / 'mods/enabled.txt').read_text(), certify.MOD_ID + '\n')
        self.assertEqual((self.app / 'mods' / (certify.MOD_ID + '-enabled.backup')).read_text(), 'production_mod\n')
        self.assertEqual((self.app / 'scripts-data/roguelite_main/checkpoint-a.txt').read_text(), 'user-save')
        self.assertEqual((self.app / 'melee').read_bytes(), b'fake-shared-binary')
        self.assertTrue(Path(result['mod_dir'], 'models/bf_floor_4m.gxmesh').is_file())

    def test_restore_puts_back_original_enabled_list(self):
        if not self.kit_available():
            self.skipTest('BF room kit not present')
        certify.install(self.app)
        restored = certify.restore(self.app)
        self.assertTrue(restored['restored'])
        self.assertEqual((self.app / 'mods/enabled.txt').read_text(), 'production_mod\n')

    def test_install_missing_app_dir_is_an_error(self):
        with self.assertRaises(FileNotFoundError):
            certify.install(Path(self.temp.name) / 'absent')

    def test_install_refuses_shared_review_dir(self):
        saved = certify.SHARED_APP
        certify.SHARED_APP = self.app.resolve()
        try:
            with self.assertRaises(ValueError):
                certify.install(self.app)
        finally:
            certify.SHARED_APP = saved

    def test_bundle_prepends_reviewed_modules(self):
        if not (certify.RT / 'rooms.lua').is_file() or not (certify.CERT_SRC / 'main.lua').is_file():
            self.skipTest('game modules unavailable')
        text = certify.bundle_text()
        self.assertIn('local RoomCatalogue = (function()', text)
        self.assertIn('local RoomRecipes = (function()', text)
        self.assertIn('local Rooms = (function()', text)
        self.assertIn("certify_build", text)

    def test_bundled_lua_compiles(self):
        lua = certify.lua_interpreter()
        if not lua or not (certify.RT / 'rooms.lua').is_file():
            self.skipTest('lua/modules unavailable')
        text = certify.bundle_text()
        path = Path(self.temp.name) / 'bundle.lua'
        path.write_text(text)
        # compile only: embedding the path in -e keeps lua from running the chunk
        result = subprocess.run([lua, '-e', 'assert(loadfile([==[%s]==]))' % path],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_certification_lua_compiles_standalone(self):
        lua = certify.lua_interpreter()
        main = certify.CERT_SRC / 'main.lua'
        if not lua or not main.is_file():
            self.skipTest('lua/cert mod unavailable')
        result = subprocess.run([lua, '-e', 'assert(loadfile([==[%s]==]))' % main],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


class CliTests(unittest.TestCase):
    def test_run_refuses_turbo_environment(self):
        old = os.environ.get('MELEE_TURBO')
        os.environ['MELEE_TURBO'] = '1'
        try:
            with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(certify.main(['run', '--app-dir', tmp]), 2)
        finally:
            if old is None:
                os.environ.pop('MELEE_TURBO', None)
            else:
                os.environ['MELEE_TURBO'] = old

    def test_run_refuses_uncapped_environment(self):
        old = os.environ.get('MELEE_FPS')
        os.environ['MELEE_FPS'] = 'u'
        try:
            with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(certify.main(['run', '--app-dir', tmp]), 2)
        finally:
            if old is None:
                os.environ.pop('MELEE_FPS', None)
            else:
                os.environ['MELEE_FPS'] = old

    def test_plan_cli_reports_uncertified(self):
        output = subprocess.run([sys.executable, str(HERE / 'certify_rooms.py'), 'plan'],
                                capture_output=True, text=True)
        self.assertEqual(output.returncode, 0, output.stderr)
        self.assertIn('"certified": false', output.stdout)
        self.assertIn('"verdict": "pending-native-run"', output.stdout)


if __name__ == '__main__':
    unittest.main()
