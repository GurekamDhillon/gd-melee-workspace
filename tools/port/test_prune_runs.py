import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class PruneTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'runs'
        self.root.mkdir()
        for i, name in enumerate(('old','live','new')):
            path=self.root/name
            path.mkdir()
            (path/'.last_run').touch()
            (path/'melee-pc.log').write_text('evidence')
            os.utime(path/'.last_run',(i+1,i+1))

    def test_live_game_is_preserved_even_outside_retention(self):
        from prune_runs import prune
        prune(self.root,1,'new',[str(self.root/'live/melee-pc.exe').upper()])
        self.assertFalse((self.root/'old').exists())
        self.assertTrue((self.root/'live/melee-pc.log').exists())

    def test_starting_wrapper_and_unstamped_runs_are_preserved(self):
        from prune_runs import prune
        (self.root/'old/.active-run').mkdir()
        (self.root/'live/.last_run').unlink()
        prune(self.root,1,'new',[])
        self.assertTrue((self.root/'old/melee-pc.log').exists())
        self.assertTrue((self.root/'live/melee-pc.log').exists())

    def test_unknown_process_inventory_refuses_deletion(self):
        from prune_runs import prune
        prune(self.root,0,'new',None)
        self.assertEqual(len(list(self.root.iterdir())),3)

    def test_current_sandbox_cannot_be_reused_while_running(self):
        from prune_runs import prune
        with self.assertRaisesRegex(RuntimeError,'already running'):
            prune(self.root,1,'new',[str(self.root/'new/melee-pc.exe')])
        self.assertTrue((self.root/'old').exists())


if __name__=='__main__': unittest.main()
