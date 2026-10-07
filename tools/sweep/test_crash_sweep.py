import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock

import crash_sweep as sweep


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.run = sweep.Run('fixture', 'stage', 'test', 'mode=vs', 120, 'fixture')
        self.run.sandbox = self.tmp.name
        self.run.proc = Mock(returncode=None)
        self.run.proc.poll.return_value = None
        self.log = Path(self.tmp.name)/'melee-pc.log'
        self.log.write_text('scene: enter mode=GM_VS(2) screen=GS_VS(2)\n')

    def beat(self, frame, presented, now):
        with self.log.open('a') as f:
            f.write(f'heartbeat retrace={frame} presented={presented} gx: copydisp={presented} prim={presented} dlist=1\n')
        if hasattr(sweep, 'sample_progress'):
            sweep.sample_progress(self.run, now=now)

    def test_early_progress_followed_by_freeze_cannot_pass(self):
        self.beat(0, 0, 0)
        self.beat(600, 600, 10)
        if hasattr(sweep, 'sample_progress'):
            sweep.sample_progress(self.run, now=120)
        self.assertEqual(sweep.judge(self.run)[0], 'HANG')

    def test_logic_progress_without_presentation_cannot_pass(self):
        for t in range(0, 121, 2):
            self.beat(t*60, 0, t)
        self.assertEqual(sweep.judge(self.run)[0], 'HANG')

    def test_regular_logic_and_render_progress_pass(self):
        for t in range(0, 121, 2):
            self.beat(t*60, t*60, t)
        self.assertEqual(sweep.judge(self.run), ('PASS', ''))

    def test_long_mid_run_stall_is_not_erased_by_final_progress(self):
        self.beat(0, 0, 0)
        self.beat(600, 600, 10)
        self.beat(720, 720, 118)
        self.beat(840, 840, 120)
        self.assertEqual(sweep.judge(self.run)[0], 'HANG')


class TurboAndGateTests(unittest.TestCase):
    def setUp(self):
        self.run = sweep.Run('fixture', 'stage', 'test', 'mode=vs', 24, 'fixture')
        self.run.t0 = 100.0

    def test_turbo_secs_are_game_seconds(self):
        self.assertFalse(sweep.run_finished(self.run, True, now=101.0, frames=24 * 60 - 1))
        self.assertTrue(sweep.run_finished(self.run, True, now=101.0, frames=24 * 60))

    def test_turbo_wall_cap_ends_a_stalled_run(self):
        self.assertFalse(sweep.run_finished(self.run, True, now=195.0, frames=0))
        self.assertTrue(sweep.run_finished(self.run, True, now=197.0, frames=0))

    def test_realtime_secs_are_wall_seconds(self):
        self.assertFalse(sweep.run_finished(self.run, False, now=123.0, frames=99999))
        self.assertTrue(sweep.run_finished(self.run, False, now=124.0, frames=0))

    def test_gate_waits_until_fewer_than_max_games(self):
        counts = iter([4, 3, 2])
        orig_count, orig_sleep = sweep.running_games, sweep.time.sleep
        sweep.running_games = lambda: next(counts)
        sweep.time.sleep = lambda s: None
        try:
            sweep.wait_for_slot(3)
            self.assertEqual(next(counts, None), None)  # consumed 4, 3, 2: returned on the third
        finally:
            sweep.running_games, sweep.time.sleep = orig_count, orig_sleep

    def test_gate_off_never_polls(self):
        orig = sweep.running_games
        sweep.running_games = lambda: 99
        try:
            sweep.wait_for_slot(0)
        finally:
            sweep.running_games = orig

    def test_second_monitor_tiling_stays_left_of_the_primary(self):
        for slot in range(4):
            x, y, w, h = sweep.window_geometry(slot, True)
            self.assertLess(x + w, 0)
        self.assertEqual(sweep.window_geometry(0, False)[:2], (0, 30))

    def test_empty_pad_script_exists(self):
        self.assertTrue(Path(sweep.EMPTY_PAD).is_file())


if __name__ == '__main__':
    unittest.main()
