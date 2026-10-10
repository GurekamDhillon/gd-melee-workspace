import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import agent_slim
import prune_runs


class SlimTests(unittest.TestCase):
    def make(self, tmp):
        agents = Path(tmp) / 'agents'
        root = agents / 'lane'
        (root / 'runs' / 'r1' / 'crashlogs').mkdir(parents=True)
        (root / 'masstest' / 'out').mkdir(parents=True)
        for rel in ('melee-pc.exe', 'melee-pc.map', 'build.log', 'runs/r1/melee-pc.exe', 'runs/r1/melee-pc.log',
                    'runs/r1/crashlogs/c.bin', 'masstest/out/a.obj'):
            (root / rel).write_bytes(b'x' * 10)
        return agents, root

    def test_plan_keeps_evidence_and_selects_bulk(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, root = self.make(tmp)
            files, links, total = agent_slim.plan(root)
            names = sorted(Path(f).relative_to(root).as_posix() for f in files)
            self.assertEqual(names, ['masstest/out/a.obj', 'melee-pc.exe', 'runs/r1/melee-pc.exe'])
            self.assertEqual(total, 30)

    def test_dry_run_deletes_nothing_and_yes_deletes_only_bulk(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(prune_runs, 'live_games', return_value=[]):
            agents, root = self.make(tmp)
            self.assertEqual(agent_slim.main(['lane', '--agents', str(agents)]), 0)
            self.assertTrue((root / 'melee-pc.exe').exists())
            self.assertEqual(agent_slim.main(['lane', '--agents', str(agents), '--yes']), 0)
            self.assertFalse((root / 'melee-pc.exe').exists())
            self.assertFalse((root / 'masstest').exists())
            self.assertTrue((root / 'build.log').exists())
            self.assertTrue((root / 'runs' / 'r1' / 'crashlogs' / 'c.bin').exists())

    def test_refuses_with_running_game_or_unknown_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            agents, root = self.make(tmp)
            with patch.object(prune_runs, 'live_games', return_value=[str(root / 'runs' / 'r1' / 'melee-pc.exe')]):
                self.assertEqual(agent_slim.main(['lane', '--agents', str(agents), '--yes']), 1)
            with patch.object(prune_runs, 'live_games', return_value=None):
                self.assertEqual(agent_slim.main(['lane', '--agents', str(agents), '--yes']), 1)
            self.assertTrue((root / 'melee-pc.exe').exists())


if __name__ == '__main__':
    unittest.main()
