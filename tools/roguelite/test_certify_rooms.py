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

    def test_unexpected_fall_on_ascent_is_a_failure(self):
        result = certify.classify_trace({'truncated': False},
                                        trace((20, 0, 0, False), (0, -40, -3, True), (0, -80, -3, True)),
                                        floor_y=0, target={'x': 39, 'y': 26})
        self.assertEqual(result['status'], 'unexpected-fall')
        self.assertTrue(result['checks']['unexpected_fall'])
        self.assertNotIn(result['status'], certify.PASS_STATUSES)

    def test_drop_needs_actual_downward_motion(self):
        # below the floor, but never airborne and never descending: a teleport sample
        result = certify.classify_trace({'truncated': False},
                                        trace((20, 0, 0, False), (0, -40, 0, False)),
                                        floor_y=0, requires_fall=True)
        self.assertEqual(result['status'], 'failed-no-descent')
        self.assertTrue(result['checks']['fell'])
        self.assertFalse(result['checks']['descended'])

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

    def test_no_samples_error_and_fixture_only_never_vanish(self):
        outcomes = [{'id': 'empty', 'status': 'no-samples'},
                    {'id': 'boom', 'status': 'error'},
                    {'id': 'inspect', 'status': 'fixture-only'},
                    {'id': 'nope', 'status': 'totally-unknown'}]
        verdict = certify.recipe_verdict('x', 2, outcomes, native_run=True)
        self.assertEqual(verdict['segments_with_observation'], 0)
        self.assertEqual(verdict['failed_segments'], ['boom'])
        self.assertEqual(sorted(verdict['inconclusive_segments']),
                         ['empty', 'inspect', 'nope'])
        self.assertEqual(verdict['unclassified_segments'], ['nope'])

    def test_unexpected_fall_is_not_a_pass(self):
        outcomes = [{'id': 'ascent', 'status': 'unexpected-fall'},
                    {'id': 'drop', 'status': 'fell'}]
        verdict = certify.recipe_verdict('x', 2, outcomes, native_run=True)
        self.assertEqual(verdict['passed_segments'], ['drop'])
        self.assertIn('ascent', verdict['failed_segments'])

    def test_every_known_status_is_bucketed(self):
        for status in certify.PASS_STATUSES + certify.FAILED_STATUSES + certify.INCONCLUSIVE_STATUSES:
            verdict = certify.recipe_verdict('x', 2, [{'id': status, 'status': status}], native_run=True)
            listed = (verdict['passed_segments'] + verdict['failed_segments']
                      + verdict['inconclusive_segments'])
            self.assertIn(status, listed, status + ' vanished from the verdict')


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
            '= gd.match().active': 'true',
            '= gd.player(1) ~= nil': 'true', '= gd.player(2) ~= nil': 'true',
            '= gd.player(1).cpu': 'true',
        })
        with self.assertRaises(certify.UnsupportedRun):
            certify.CertificationDriver(console).launch_scene('fox')


class DriverStateTests(unittest.TestCase):
    def test_scene_waits_for_stable_active_match_with_stale_fighters(self):
        active = iter(['false', 'true', 'false', 'true', 'true'])
        console = make_console({
            'certify_scene': 'certify_scene p1=falco/c0 ok=true result=nil',
            'certify_status': 'certify_status phase=idle template=nil',
            '= gd.match().active': lambda text: next(active),
        }, scalars={
            '= gd.player(1) ~= nil': 'true', '= gd.player(2) ~= nil': 'true',
            '= gd.player(1).cpu': 'false',
            '= gd.match().frame': '200',
        })
        self.assertTrue(certify.CertificationDriver(console).launch_scene('falco'))
        commands = [c['command'] for c in console.calls]
        self.assertEqual(commands.count('= gd.match().active'), 5)
        self.assertEqual(commands[-1], "gd.cpu_mode(2, 'stand')")

    SAMPLE = 'certify_sample port=1 x=0 y=0 vx=0 vy=0 airborne=false action=14 facing=1'

    def test_replay_renders_real_pad_inputs_on_one_port(self):
        console = make_console({'certify_sample': self.SAMPLE})
        driver = certify.CertificationDriver(console, sleep_frames=lambda n: None)
        driver.replay_until([('walk', 1, 60), ('neutral', 10), ('button', 'A', 4), ('down', 30)],
                            target=None, floor_y=-1000.0, chunk=1000)
        rendered = [c['command'] for c in console.calls]
        self.assertIn('input 1 none 60 127 0', rendered)
        self.assertIn('input 1 none 10', rendered)
        self.assertIn('input 1 A 4', rendered)
        self.assertIn('input 1 DOWN 30', rendered)
        self.assertTrue(all('input 1' in c for c in rendered if c.startswith('input')))

    def test_replay_stops_at_the_arrival_region(self):
        # first poll far away, second poll on target; walk should stop after 2 chunks
        samples = iter(['certify_sample port=1 x=-40 y=0 vx=0 vy=0 airborne=false action=14 facing=1',
                        'certify_sample port=1 x=39 y=26 vx=0 vy=0 airborne=false action=14 facing=1'])
        console = make_console({'certify_sample': lambda t: next(samples)})
        driver = certify.CertificationDriver(console, sleep_frames=lambda n: None)
        stopped = driver.replay_until([('walk', 1, 200)], target={'x': 39, 'y': 26},
                                      floor_y=0.0, chunk=20)
        self.assertEqual(stopped, 'arrived')
        walks = [c['command'] for c in console.calls if c['command'].startswith('input 1 none 20')]
        self.assertEqual(len(walks), 2)

    def test_replay_stops_when_it_would_leave_the_room(self):
        samples = iter(['certify_sample port=1 x=0 y=-50 vx=0 vy=-3 airborne=true action=14 facing=1'])
        console = make_console({'certify_sample': lambda t: next(samples)})
        driver = certify.CertificationDriver(console, sleep_frames=lambda n: None)
        stopped = driver.replay_until([('walk', 1, 400)], target={'x': 39, 'y': 26},
                                      floor_y=0.0, chunk=20)
        self.assertEqual(stopped, 'out-of-bounds')
        walks = [c['command'] for c in console.calls if c['command'].startswith('input 1 none 20')]
        self.assertEqual(len(walks), 1)

    def test_cleanup_releases_pad_and_calls_native_cleanup(self):
        console = make_console({'certify_cleanup': 'certify_cleanup errors=0',
                                'certify_sample': self.SAMPLE})
        driver = certify.CertificationDriver(console, sleep_frames=lambda n: None)
        driver.replay_until([('walk', 1, 10)], target=None, floor_y=-1000.0, chunk=1000)
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
            'certify_place': 'certify_place ok=true x=20 y=0 fixture=true',
            'certify_arm': 'certify_arm label=drop socket=branch_b target_x=39 target_y=26 floor_y=0 start_x=20 start_y=0 limit=900',
            'certify_sample': self.SAMPLE,
            'certify_result': ('certify_result header=1 label=drop socket=branch_b target_x=39 target_y=26 floor_y=0 samples=2 truncated=false min_y=-40 max_y=0 air_frames=1 start_x=20 start_y=0\n'
                               'certify_trace i=1 frame=1 x=20 y=0 vx=-2 vy=0 airborne=false action=14\n'
                               'certify_trace i=2 frame=2 x=0 y=-40 vx=0 vy=-3 airborne=true action=14'),
        })
        driver = certify.CertificationDriver(console, sleep_frames=lambda n: None)
        segment = {'id': 'drop_through', 'natural': True, 'fixture': {'x': 20, 'y': 0},
                   'requires_fall': True, 'target': None, 'source': None, 'probes': [[('walk', -1, 10)]]}
        outcome = driver.certify_segment(segment, None, 40.0)
        self.assertEqual(outcome['status'], 'fell')
        rendered = [c['command'] for c in console.calls]
        self.assertIn('certify_place_at 20.000 0.000', rendered)
        self.assertIn('certify_arm_coords drop_through none none', rendered)

    def test_arm_window_uses_socket_target_when_present(self):
        console = make_console({'certify_arm': 'certify_arm label=ascent socket=window target_x=39 target_y=26 floor_y=0 start_x=0 start_y=0 limit=900'})
        driver = certify.CertificationDriver(console, sleep_frames=lambda n: None)
        driver.arm_window('ascent', {'x': 39.0, 'y': 26.0})
        self.assertIn('certify_arm_coords ascent 39.0 26.0', [c['command'] for c in console.calls])
        driver.arm_window('drop')
        self.assertIn('certify_arm_coords drop none none', [c['command'] for c in console.calls])

    def test_arm_refusal_is_explicit(self):
        console = make_console({'certify_error': 'certify_error where=arm_coords message=bad'})
        driver = certify.CertificationDriver(console, sleep_frames=lambda n: None)
        with self.assertRaises(certify.UnsupportedRun):
            driver.arm_window('drop', None)

    def test_result_without_header_is_an_error_not_a_pass(self):
        console = make_console({'certify_result': 'certify_trace i=1 frame=1 x=39 y=26 vx=0 vy=0 airborne=false action=14'})
        driver = certify.CertificationDriver(console, sleep_frames=lambda n: None)
        summary, rows = driver.result()
        self.assertIsNone(summary)
        self.assertEqual(rows, [])

    def test_fixture_place_retries_then_succeeds(self):
        outputs = iter(['certify_place ok=false reason=refused x=1 y=2 fixture=true',
                        'certify_place ok=true x=1 y=2 fixture=true'])
        console = make_console({'certify_place': lambda t: next(outputs)})
        driver = certify.CertificationDriver(console, sleep_frames=lambda n: None)
        result = driver.fixture_place(socket='in', timeout=10.0, interval=0.5)
        self.assertTrue(result['ok'])
        self.assertEqual(result['attempts'], 2)

    def test_fixture_place_unknown_socket_fails_fast(self):
        console = make_console({'certify_place': 'certify_place ok=false reason=unknown_socket socket=x'})
        driver = certify.CertificationDriver(console, sleep_frames=lambda n: None)
        result = driver.fixture_place(socket='x', timeout=10.0)
        self.assertFalse(result['ok'])
        self.assertEqual(result['attempts'], 1)
        self.assertEqual(result['reason'], 'unknown_socket')

    def test_fixture_place_timeout_is_reported(self):
        console = make_console({'certify_place': 'certify_place ok=false reason=refused'})
        driver = certify.CertificationDriver(console, sleep_frames=lambda n: None)
        result = driver.fixture_place(socket='in', timeout=1.0, interval=0.5)
        self.assertFalse(result['ok'])
        self.assertGreater(result['attempts'], 1)
        self.assertEqual(result['reason'], 'timeout')

    def test_capture_confirms_a_fresh_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / 'shot.png'

            def command(text, category='observation'):
                if text.startswith('shot '):
                    target.write_bytes(b'png-bytes')
                return ''

            console = certify.Console(command, sleep=lambda s: None, clock=time.monotonic,
                                      note=lambda r: None)
            driver = certify.CertificationDriver(console, capture_dir=tmp, sleep_frames=lambda n: None)
            self.assertEqual(driver.capture('shot.png', timeout=1.0), str(target.resolve()))

    def test_capture_failure_is_not_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            console = make_console({})
            driver = certify.CertificationDriver(console, capture_dir=tmp, sleep_frames=lambda n: None)
            self.assertIsNone(driver.capture('missing.png', timeout=0.2))


class EvidenceTests(unittest.TestCase):
    def test_run_certification_writes_summary_on_console_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = Path(tmp) / 'app'
            (app / 'mods/roguelite_certification/scripts').mkdir(parents=True)
            (app / 'mods/roguelite_certification/scripts/main.lua').write_text('-- installed')

            class Reader:
                def readline(self):
                    return 'banner\n'

            class Sock:
                def makefile(self, mode='r'):
                    return Reader()

            def console_run(reader, sock, text):
                raise OSError('console timeout')

            summary = certify.run_certification(
                app, connect=lambda: (Sock(), console_run),
                log_path=Path(tmp) / 'evidence.jsonl', capture_dir=Path(tmp) / 'caps')
            self.assertTrue(summary['failed'])
            self.assertTrue(any('aborted' in e for e in summary['errors']))
            self.assertFalse(summary['any_certified'])
            self.assertTrue((Path(tmp) / 'evidence.jsonl').is_file())


class ProbeModuleTests(unittest.TestCase):
    def test_real_lua_commands_and_cleanup_contract(self):
        lua = shutil.which('lua5.4') or shutil.which('lua')
        self.assertIsNotNone(lua, 'Lua required')
        prelude = r'''
local commands,logs,moves={},{},{}
local removals,refuse,next_handle=0,false,0
local scene,isolated,refuse_teleport=false,false
local function handle() next_handle=next_handle+1; return next_handle end
gd={api_version=1,command=function(n,f)commands[n]=f end,log=function(s)logs[#logs+1]=s end,
 player=function()return {x=0,y=0,vx=0,vy=0,airborne=false,action=14,facing=1}end,
 match=function()return {active=true,frame=200}end,
 teleport=function(p,x,y)if refuse_teleport then error('dead') end moves[#moves+1]={p,x,y}end,
 model_load=function()return handle()end, model_spawn=function()return handle()end,
 model_get=function(h)return {handle=h}end, model_despawn=function()return true end,
 model_release=function()return true end,
 hud_visible=function()return true end,
 camera_detach=function()return true end,camera_set=function()return nil end,
 camera_attach=function()return nil end,
 stage_remove=function()removals=removals+1;return not refuse end,
 stage_add_platform=function()return handle()end,
 stage_add_line=function()return handle()end,
 scene_launch=function(s)scene=s end,
 stage_isolate=function(v)if v~=nil then isolated=v end return isolated end}
function has(pat)for _,s in ipairs(logs)do if s:find(pat,1,true)then return true end end return false end
'''
        checks = r'''
commands.certify_scene('falco 2');assert(scene.p1=='falco/c2')

-- 1. explicit phase: placement before a build is refused and does not poison state
logs={};commands.certify_place_at('10 0')
assert(probe.state.phase=='idle')
assert(has('certify_place ok=false reason=phase_idle'))

-- 2. real successful callbacks: preload -> visuals -> collision -> isolate
commands.certify_build('branch_y')
local guard=0
while probe.state.phase~='ready' and probe.state.phase~='error' and guard<400 do guard=guard+1;on_tick()end
assert(probe.state.phase=='ready','build failed: '..tostring(probe.state.error))
assert(gd.stage_isolate()==true,'isolation not held after build')
assert(#probe.state.handles==5,'unexpected collider count '..#probe.state.handles)

-- 3. operational refusal preserves constructed phase and isolation (no fake arm)
refuse_teleport=true
logs={};commands.certify_place('in')
assert(probe.state.phase=='ready','refused placement changed the phase')
assert(gd.stage_isolate()==true,'refused placement lost isolation')
assert(has('certify_place ok=false reason=refused'))
refuse_teleport=false
logs={};commands.certify_place('in')
assert(has('certify_place ok=true'))
assert(moves[#moves][1]==1)

-- 4. clean preview changes only the diagnostic draw
commands.certify_build('branch_y clean')
assert(probe.state.clean==true,'clean flag not set')
guard=0
while probe.state.phase~='ready' and probe.state.phase~='error' and guard<400 do guard=guard+1;on_tick()end
assert(probe.state.phase=='ready','clean rebuild failed')

-- 5. camera preview is scoped to this mod and restored
logs={};commands.certify_camera('wide')
assert(probe.state.camera_mode=='wide');assert(has('certify_camera ok=true mode=wide'))
commands.certify_camera('auto');assert(probe.state.camera_mode==nil)

-- 6. arm + bounded result page + paging
commands.certify_arm_coords('window 39 26')
assert(probe.state.arm.target.x==39 and probe.state.arm.target.y==26)
probe.state.phase='ready';for i=1,25 do on_frame()end
logs={};commands.certify_result()
assert(has('header=1'),'result header missing')
local n=0;for _,s in ipairs(logs)do if s:match('^certify_trace i=')then n=n+1 end end
assert(n==20,'result exceeded bounded trace page')
logs={};commands.certify_trace('21 3');assert(#logs==3)
assert(logs[1]:find('i=21 ',1,true) and logs[3]:find('i=23 ',1,true))

-- 7. partial build keeps ownership; cleanup retries; teardown forgets stale handles
local original=gd.stage_add_platform
local calls=0
gd.stage_add_platform=function()calls=calls+1;if calls==1 then return 42 end return nil,'pool full' end
probe.state.phase='collision';probe.state.plan={floor_segments={{left=0,right=1,y=0},{left=1,right=2,y=0}},platforms={},lines={}}
on_tick();assert(probe.state.phase=='error' and probe.state.handles[1]==42,'partial build lost ownership')
refuse=true;probe.cleanup();assert(probe.state.handles[1]==42,'refused removal lost ownership')
refuse=false;probe.cleanup();assert(#probe.state.handles==0)
gd.stage_add_platform=original
local before=removals;probe.state.handles={9};on_match_end()
assert(removals==before and #probe.state.handles==0,'native teardown retried stale handles')
print('PASS')
'''
        code = prelude + '\nlocal probe=(function()\n' + certify.bundle_text() + '\nend)();\n' + checks
        result = subprocess.run([lua, '-'], input=code, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('PASS', result.stdout)


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
