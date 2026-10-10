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


class PlanTests(unittest.TestCase):
    DAY=86400

    def entries(self,n,stamped=True,base=1000):
        return [(f'r{i}',base+i,stamped) for i in range(n)]  # r{n-1} is newest

    def test_keeps_newest_n_and_deletes_the_rest(self):
        from prune_runs import plan
        delete,strip=plan(self.entries(6),3,3,'none',set(),now=2000)
        self.assertEqual(sorted(delete),['r0','r1','r2'])
        self.assertEqual(strip,[])

    def test_strip_applies_between_strip_after_and_keep(self):
        from prune_runs import plan
        delete,strip=plan(self.entries(10),6,2,'none',set(),now=2000)
        self.assertEqual(sorted(delete),['r0','r1','r2','r3'])
        self.assertEqual(sorted(strip),['r4','r5','r6','r7'])

    def test_current_and_active_are_never_selected(self):
        from prune_runs import plan
        delete,strip=plan(self.entries(6),1,1,'r0',{'r1'},now=2000)
        self.assertNotIn('r0',delete+strip)
        self.assertNotIn('r1',delete+strip)
        self.assertEqual(sorted(delete),['r2','r3','r4'])

    def test_young_unstamped_is_protected_old_unstamped_is_not(self):
        from prune_runs import plan
        now=10*self.DAY
        entries=[('new',now,True),('young',now-60,False),('old',now-5*self.DAY,False)]
        delete,_=plan(entries,1,1,'none',set(),now=now)
        self.assertEqual(delete,['old'])

    def test_everything_active_deletes_nothing(self):
        from prune_runs import plan
        delete,strip=plan(self.entries(3),0,0,'none',{'r0','r1','r2'},now=2000)
        self.assertEqual((delete,strip),([],[]))


class StripTests(unittest.TestCase):
    def test_strip_keeps_logs_and_removes_exe_dll_caches(self):
        from prune_runs import prune
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'runs'; root.mkdir()
            for i,name in enumerate(('a','b','c')):
                d=root/name; d.mkdir(); (d/'.last_run').touch(); os.utime(d/'.last_run',(100+i,100+i))
                for f in ('melee-pc.exe','SDL3.dll','dawn_cache.db','melee-pc.log','melee-pc.map'):
                    (d/f).write_text('x')
                (d/'crashlogs').mkdir(); (d/'crashlogs'/'c.txt').write_text('crash')
            msgs=[]
            prune(root,2,'none',[],strip_after=1,log=msgs.append,now=200)
            self.assertFalse((root/'a').exists())                      # beyond keep: deleted
            self.assertFalse((root/'b'/'melee-pc.exe').exists())        # beyond strip_after: stripped
            self.assertFalse((root/'b'/'dawn_cache.db').exists())
            self.assertTrue((root/'b'/'melee-pc.log').exists())
            self.assertTrue((root/'b'/'crashlogs'/'c.txt').exists())
            self.assertTrue((root/'c'/'melee-pc.exe').exists())         # newest: intact
            self.assertFalse((root/'c'/'.active-run').exists())         # lock released
            self.assertTrue(any('pruned run a' in m for m in msgs))
            self.assertTrue(any('stripped run b' in m for m in msgs))

    def test_never_touches_outside_root(self):
        from prune_runs import prune
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'runs'; root.mkdir()
            outside=Path(tmp)/'outside'; outside.mkdir(); (outside/'melee-pc.exe').write_text('keep')
            d=root/'old'; d.mkdir(); (d/'.last_run').touch()
            prune(root,0,'none',[],log=lambda m:None)
            self.assertTrue((outside/'melee-pc.exe').exists())
            self.assertFalse(d.exists())

if __name__=='__main__': unittest.main()
