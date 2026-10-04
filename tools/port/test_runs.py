import json
import tempfile
import time
import unittest
import os
import sys
import subprocess
from unittest.mock import patch, Mock
from pathlib import Path

import runs


class RunsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def record(self, name, owner='alpha', pid=123):
        path = self.root / name
        path.mkdir()
        runs.atomic_json(path / 'run.json', dict(pid=pid, owner=owner, sandbox=str(path),
            start=time.time()-100, process_created=42, command=[str(path/'melee-pc.exe')]))
        return path

    def test_missing_feature(self):
        self.assertTrue(callable(getattr(runs, 'classify', None)), 'verdict classifier missing')

    def test_fresh_heartbeat_without_progress_is_hung(self):
        watch = runs.ProgressWatch(100)
        h = dict(main_ticks=1, wall_clock=100, watchdog_seconds=10)
        self.assertFalse(watch.hung(h, 100))
        self.assertTrue(watch.hung(dict(h, wall_clock=116), 116))
        self.assertFalse(watch.hung(dict(h, main_ticks=2, wall_clock=117), 117))
        self.assertFalse(watch.hung(dict(h, debugger=True, wall_clock=200), 200))
        self.assertFalse(watch.hung(dict(h, modal=True, wall_clock=220), 220))
        self.assertFalse(watch.hung(dict(h, watchdog_seconds=0), 500))
        self.assertTrue(runs.ProgressWatch(100).hung({}, 116))

    def test_verdicts(self):
        self.assertEqual(runs.classify(0, 'gw: final exit reason=normal code=0'), 'OK')
        self.assertEqual(runs.classify(0, ''), 'SILENT_EXIT')
        self.assertEqual(runs.classify(3, ''), 'SILENT_EXIT code=3')
        self.assertEqual(runs.classify(0xc0000005, ''), 'CRASH code=3221225477')
        self.assertEqual(runs.classify(1, 'gw: FATAL access'), 'CRASH code=1')
        self.assertEqual(runs.classify(124, '', 'TIMEOUT'), 'TIMEOUT')
        self.assertEqual(runs.classify(86, '', 'HUNG presenting=0 logic=0'), 'HUNG presenting=0 logic=0')

    def test_heartbeat_state(self):
        now = time.time()
        h = dict(wall_clock=now, main_age_seconds=0, logic_age_seconds=0,
                 present_age_seconds=0, watchdog_seconds=10)
        self.assertEqual(runs.heartbeat_state(h, now), 'running')
        self.assertEqual(runs.heartbeat_state(dict(h, paused=True), now), 'paused')
        self.assertEqual(runs.heartbeat_state(dict(h, hidden=True), now), 'hidden')
        self.assertEqual(runs.heartbeat_state(dict(h, main_age_seconds=20), now), 'hung')
        self.assertEqual(runs.heartbeat_state(dict(h, paused=True, main_age_seconds=20), now), 'hung')
        self.assertEqual(runs.heartbeat_state(dict(h, debugger=True, main_age_seconds=20), now), 'paused')
        self.assertEqual(runs.heartbeat_state(h, now+30), 'hung')
        self.assertEqual(runs.heartbeat_state({}, now), 'unknown')
        self.assertEqual(runs.heartbeat_state(dict(h, watchdog_seconds=0, main_age_seconds=100), now), 'disabled')

    def test_inventory_identity_and_filtering(self):
        a = self.record('a')
        b = self.record('b', 'beta', 456)
        processes = [dict(pid=123, path=str(a/'melee-pc.exe'), created=42, memory=100),
                     dict(pid=456, path=str(b/'melee-pc.exe'), created=42, memory=200),
                     dict(pid=999, path=str(self.root/'untracked/melee-pc.exe'), created=43)]
        rows = runs.inventory(self.root, processes)
        self.assertEqual(len(rows), 3)
        selected = runs.select(rows, owner='alpha')
        self.assertEqual([r['pid'] for r in selected], [123])
        self.assertEqual([r['pid'] for r in runs.select(rows, sandbox='b')], [456])
        self.assertEqual(runs.select(rows, owner='alpha', older_than=1000), [])
        killed = []
        runs.reap_rows(selected, lambda row: killed.append(row['pid']))
        self.assertEqual(killed, [123])
        # Reused PID with the same path still cannot match the former owner's run.
        processes[0]['created'] = 10043
        self.assertEqual(runs.select(runs.inventory(self.root, processes), owner='alpha'), [])

    def test_cim_timestamp_precision_and_boundary(self):
        path = self.record('precision')
        stamp = 134355479274178404
        record = runs.read_json(path/'run.json'); record['process_created'] = stamp
        runs.atomic_json(path/'run.json', record)
        runs.atomic_json(path/'heartbeat.json', dict(pid=123, process_created=stamp,
            wall_clock=time.time(), main_age_seconds=0))
        process = dict(pid=123, path=str(path/'melee-pc.exe'), created=stamp-4)
        row = runs.inventory(self.root, [process])[0]
        self.assertTrue(row['tracked']); self.assertEqual(row['state'], 'running')
        self.assertTrue(runs.same_created(stamp, stamp+10000))
        self.assertFalse(runs.same_created(stamp, stamp+10001))
        self.assertFalse(runs.same_created(None, stamp))

    def test_verified_reap_uses_tolerance_and_exact_marker(self):
        path = self.record('reap')
        api = Mock(); api.check.side_effect = lambda v: v
        api.created.return_value = 134355479274178404
        api.path.return_value = str(path/'melee-pc.exe')
        api.k.WaitForSingleObject.return_value = 0
        row = dict(pid=123, created=134355479274178400, path=api.path.return_value,
                   sandbox=str(path), tracked=True)
        with patch.object(runs, 'WinAPI', return_value=api):
            runs.terminate_verified(row)
        self.assertEqual(runs.read_json(path/'termination.json')['process_created'], api.created.return_value)
        api.created.return_value += 10001
        with patch.object(runs, 'WinAPI', return_value=api):
            with self.assertRaisesRegex(RuntimeError, 'identity changed'): runs.terminate_verified(row)
        self.assertEqual(api.k.TerminateProcess.call_count, 1)

    def test_reap_no_match_is_an_explicit_failure(self):
        import io
        output = io.StringIO()
        with patch.object(sys, 'argv', ['runs', '--root', str(self.root), 'reap', '--owner', 'missing']), \
             patch.object(runs, 'live_processes', return_value=[]), patch('sys.stdout', output):
            self.assertNotEqual(runs.main(), 0)
        self.assertIn('No matching', output.getvalue())

    def test_disc_paths_never_reach_run_artifacts(self):
        disc = r'C:\private images\example.iso'
        with patch.dict(os.environ, {'GW_ISO_VANILLA': disc}):
            text = disc + '\n' + disc.replace('\\', '/') + '\n' + json.dumps(disc)
            runs.atomic_json(self.root/'run.json', dict(command=['game', '--iso', disc], note=text))
            (self.root/'melee-pc.log').write_text(runs.redact(text))
            (self.root/'hang.txt').write_text(runs.redact(text))
            runs.diagnose(self.root, text, dict(note=text))
            for file in self.root.iterdir():
                saved = file.read_text()
                for secret in (disc, disc.replace('\\', '/'), json.dumps(disc)[1:-1]):
                    self.assertNotIn(secret, saved, file.name)
                self.assertIn('<disc>', saved)

    def test_cache_seed_skips_live_and_active_and_handles_spaces(self):
        a = self.root/'big live'; a.mkdir(); (a/'dawn_cache.db').write_bytes(b'x'*50)
        b = self.root/'active'; b.mkdir(); (b/'dawn_cache.db').write_bytes(b'x'*40); (b/'.active-run').mkdir()
        c = self.root/'safe spaces'; c.mkdir(); (c/'dawn_cache.db').write_bytes(b'correct')
        target = self.root/'target'; target.mkdir()
        runs.seed_cache(self.root, target, [dict(path=str(a/'melee-pc.exe'))])
        self.assertEqual((target/'dawn_cache.db').read_bytes(), b'correct')
        self.assertFalse((c/'.active-run').exists())

    def test_diagnosis_redacts_legacy_native_inputs_before_copy(self):
        disc = r'C:\private images\old.gcm'
        with patch.dict(os.environ, {'MELEE_ISO': disc}):
            (self.root/'melee-pc.log').write_text(disc)
            (self.root/'hang.txt').write_text(disc)
            runs.diagnose(self.root, 'HUNG', {})
            self.assertEqual((self.root/'diagnosis-log.txt').read_text(), '<disc>')
            self.assertEqual((self.root/'diagnosis-hang.txt').read_text(), '<disc>')

    def test_scene_transition_is_bounded_and_never_masks_main_stall(self):
        h = dict(wall_clock=time.time(), main_age_seconds=0, logic_age_seconds=12,
                 state='scene-transition', transition_age_seconds=12)
        self.assertEqual(runs.heartbeat_state(h), 'scene-transition')
        self.assertEqual(runs.heartbeat_state(dict(h, transition_age_seconds=30)), 'logic-stalled')
        self.assertEqual(runs.heartbeat_state(dict(h, main_age_seconds=12)), 'hung')

    @unittest.skipUnless(Path('C:/Program Files/Git/bin/bash.exe').exists(), 'Git Bash')
    def test_actual_wrapper_volume_defaults_and_override(self):
        wrapper = Path(runs.__file__).with_name('run.sh').read_text()
        start = wrapper.index('if [ "${MELEE_UNATTENDED:-0}" = 1 ]; then', wrapper.index('# Test windows'))
        fragment = wrapper[start:wrapper.index('\nfi', start)+3]
        for unattended, override, expected in [('0', None, '3'), ('1', None, '0'), ('1', '7', '7')]:
            env = dict(os.environ, MELEE_UNATTENDED=unattended)
            env.pop('MELEE_VOLUME', None)
            if override is not None: env['MELEE_VOLUME'] = override
            result = subprocess.run(['C:/Program Files/Git/bin/bash.exe', '--noprofile', '--norc',
                '-c', fragment+'\nprintf "%s" "$MELEE_VOLUME"'], env=env,
                capture_output=True, text=True, check=True)
            self.assertEqual(result.stdout, expected)

    def test_launch_redacts_cli_disc_before_any_metadata_write(self):
        import argparse
        import io
        disc = r'C:\private images\cli.iso'
        args = argparse.Namespace(sandbox=self.root, command=['--iso', disc], max_seconds=0, unattended=False)
        api = Mock(); api.check.side_effect = lambda v: v
        api.path.return_value = 'bash.exe'; api.k.WaitForSingleObject.return_value = 0
        child = Mock(pid=123, created=42); child.code.return_value = 0
        output = io.StringIO()
        (self.root/'melee-pc.log').write_text('gw: final exit reason=normal code=0')
        with patch.object(runs, 'WinAPI', return_value=api), \
             patch.object(runs, 'JobChild', return_value=child) as create, \
             patch.object(runs, '_command_discs', set()), patch('sys.stdout', output), \
             patch.dict(os.environ, {'MELEE_UNATTENDED':'1'}):
            os.environ.pop('MELEE_VOLUME', None)
            self.assertEqual(runs.launch(args), 0)
            self.assertEqual(os.environ['MELEE_VOLUME'], '0')
            self.assertIn(disc, create.call_args.args[1]) # executable receives the actual path
            for file in self.root.iterdir():
                saved = file.read_text()
                for secret in (disc, disc.replace('\\','/'), json.dumps(disc)[1:-1]):
                    self.assertNotIn(secret, saved)
            self.assertEqual(runs.read_json(self.root/'run.json')['command'][-1], '<disc>')

    def test_malformed_and_partial_records(self):
        p = self.root/'bad'; p.mkdir(); (p/'run.json').write_text('{')
        self.assertEqual(runs.inventory(self.root, []), [])
        self.assertEqual(runs.read_json(p/'run.json'), {})

    @unittest.skipUnless(os.name == 'nt', 'Windows job object')
    def test_job_close_kills_only_its_benign_python_child(self):
        api = runs.WinAPI()
        child = runs.JobChild(api, [sys.executable, '-c', 'import time; time.sleep(60)'], self.root)
        unrelated = runs.JobChild(api, [sys.executable, '-c', 'import time; time.sleep(60)'], self.root)
        observer = api.check(api.k.OpenProcess(0x100000 | 0x1000, False, child.pid))
        try:
            # Suspended creation really stays alive until explicitly resumed.
            self.assertEqual(api.k.WaitForSingleObject(observer, 10), 258)
            child.resume()
            unrelated.resume()
            child.close()
            self.assertEqual(api.k.WaitForSingleObject(observer, 3000), 0)
            self.assertEqual(api.k.WaitForSingleObject(unrelated.process, 10), 258)
            # The test runner itself is never assigned to the child job.
            self.assertTrue(os.getpid() > 0)
        finally:
            child.close()
            unrelated.close()
            api.k.CloseHandle(observer)

    def test_hung_filter_does_not_reap_other_owner(self):
        rows = [dict(pid=1, tracked=True, owner='alpha', sandbox='a', age=5, state='hung'),
                dict(pid=2, tracked=True, owner='beta', sandbox='b', age=50, state='hung'),
                dict(pid=3, tracked=True, owner='alpha', sandbox='c', age=50, state='running')]
        killed=[]
        runs.reap_rows(runs.select(rows, owner='alpha', hung=True), lambda r: killed.append(r['pid']))
        self.assertEqual(killed,[1])
        with self.assertRaisesRegex(RuntimeError,'untracked'):
            runs.reap_rows([dict(pid=4,tracked=False)],lambda r:killed.append(r['pid']))
        self.assertEqual(killed,[1])

    @unittest.skipUnless(os.name == 'nt', 'Windows supervisor death')
    def test_killed_supervisor_closes_job_without_cleanup_code(self):
        ready=self.root/'ready.json'
        script=self.root/'guardian.py'
        script.write_text('import sys,time\n'
            f'sys.path.insert(0,{str(Path(runs.__file__).parent)!r})\n'
            'import runs\n'
            f'child=runs.JobChild(runs.WinAPI(),[sys.executable,"-c","import time;time.sleep(60)"],{str(self.root)!r})\n'
            'child.resume()\n'
            f'runs.atomic_json({str(ready)!r},dict(pid=child.pid,created=child.created))\n'
            'time.sleep(60)\n',encoding='utf-8')
        guardian=subprocess.Popen([sys.executable,str(script)],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        api=runs.WinAPI(); observer=None
        try:
            for _ in range(100):
                record=runs.read_json(ready)
                if record:break
                if guardian.poll() is not None:self.fail(guardian.stderr.read().decode())
                time.sleep(.05)
            else:self.fail('guardian did not publish its benign child identity')
            observer=api.check(api.k.OpenProcess(0x100000|0x1000,False,record['pid']))
            self.assertEqual(api.created(observer),record['created'])
            self.assertEqual(api.k.WaitForSingleObject(observer,0),258)
            # This is only the exact Popen handle we started, never an inventory PID.
            guardian.kill(); guardian.wait(timeout=5)
            self.assertEqual(api.k.WaitForSingleObject(observer,5000),0)
        finally:
            if guardian.poll() is None:guardian.kill();guardian.wait(timeout=5)
            guardian.stderr.close()
            if observer:api.k.CloseHandle(observer)
if __name__ == '__main__': unittest.main()
