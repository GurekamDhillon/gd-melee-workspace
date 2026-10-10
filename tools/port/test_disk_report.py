import contextlib
import io
import os
import tempfile
import time
import unittest
from pathlib import Path

import disk_report

DAY = 86400


class ReportTests(unittest.TestCase):
    def test_scanner_counts_hardlinks_once(self):
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)
            (t / 'a').mkdir()
            (t / 'b').mkdir()
            (t / 'a' / 'f').write_bytes(b'x' * 1000)
            os.link(t / 'a' / 'f', t / 'b' / 'g')
            (t / 'b' / 'h').write_bytes(b'y' * 500)
            s = disk_report.Scanner()
            self.assertEqual(s.size(t / 'a')[0], 1000)
            self.assertEqual(s.size(t / 'b')[0], 500)   # the hardlink was already counted under a/

    def test_suggestions_pick_idle_roots_sweeps_and_release_staging(self):
        now = 100 * DAY
        agents = [
            dict(name='old', path='/x/agents/old', bytes=5, newest=now - 10 * DAY, runs_count=0, runs_bytes=0),
            dict(name='busy', path='/x/agents/busy', bytes=9, newest=now - 10 * DAY, runs_count=0, runs_bytes=0),
            dict(name='fresh', path='/x/agents/fresh', bytes=7, newest=now - 1 * DAY, runs_count=80, runs_bytes=6),
            dict(name='tidy', path='/x/agents/tidy', bytes=7, newest=now - 1 * DAY, runs_count=3, runs_bytes=1),
        ]
        top = [
            dict(name='sweep-0.2.2', path='/x/sweep-0.2.2', bytes=11, newest=now - 20 * DAY),
            dict(name='release-021', path='/x/release-021', bytes=13, newest=now - 20 * DAY),
            dict(name='release-new', path='/x/release-new', bytes=17, newest=now - 1 * DAY),
            dict(name='ax86m', path='/x/ax86m', bytes=99, newest=now - 50 * DAY),
        ]
        live = [str(Path('/x/agents/busy').resolve()).replace('\\', '/').casefold()]
        sug = disk_report.suggestions(top, agents, now, 3.0, live_dirs=live)
        text = '\n'.join(t for _, t in sug)
        self.assertIn('agent_rm.sh old', text)
        self.assertNotIn('busy', text)
        self.assertIn('prune_runs.py', text)           # fresh has 80 runs
        self.assertNotIn('tidy', text)
        self.assertIn('sweep-0.2.2', text)
        self.assertIn('release-021', text)
        self.assertNotIn('release-new', text)
        self.assertNotIn('ax86m', text)                # never suggested: not an agent/sweep/release
        self.assertEqual([b for b, _ in sug], sorted((b for b, _ in sug), reverse=True))

    def test_report_runs_on_a_temp_build_and_deletes_nothing(self):
        with tempfile.TemporaryDirectory() as t:
            b = Path(t) / '_build'
            (b / 'agents' / 'x' / 'runs' / 'r1').mkdir(parents=True)
            (b / 'agents' / 'x' / 'runs' / 'r1' / 'melee-pc.exe').write_bytes(b'z' * 100)
            (b / 'sweep-old').mkdir()
            (b / 'sweep-old' / 'a').write_bytes(b'q')
            old = time.time() - 30 * DAY
            os.utime(b / 'sweep-old' / 'a', (old, old))
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = disk_report.main(['--build', str(b)])
            self.assertEqual(rc, 0)
            self.assertIn('sweep-old', buf.getvalue())
            self.assertTrue((b / 'sweep-old' / 'a').exists())
            self.assertTrue((b / 'agents' / 'x' / 'runs' / 'r1' / 'melee-pc.exe').exists())


if __name__ == '__main__':
    unittest.main()
