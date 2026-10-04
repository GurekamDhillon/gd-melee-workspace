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


if __name__ == '__main__':
    unittest.main()
