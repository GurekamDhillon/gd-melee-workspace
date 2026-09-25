"""Runner ownership checks use fake processes; no native game is launched."""

import io
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import two_client_replay as runner


class RunnerOwnershipTest(unittest.TestCase):
    def test_negative_control_requires_divergence_after_mutation_and_consensus(self):
        normal = dict(ok=False, first_divergence={'frame': 45}, checksums_equal=True)
        consensus = dict(ok=True, first_divergence=None, checksums_equal=True)
        good = runner.evaluate_negative_control({'frame': 45}, normal, consensus)
        self.assertTrue(good['ok'])
        self.assertEqual(good['kind'], 'negative_control')
        self.assertIs(good['normal_verification'], normal)
        self.assertIs(good['consensus_verification'], consensus)
        for altered_normal, altered_consensus in (
            (dict(normal, ok=True), consensus),
            (dict(normal, first_divergence=None), consensus),
            (dict(normal, first_divergence={'frame': 44}), consensus),
            (normal, dict(consensus, ok=False)),
            (dict(normal, checksums_equal=False), consensus),
        ):
            with self.subTest(normal=altered_normal, consensus=altered_consensus):
                self.assertFalse(runner.evaluate_negative_control(
                    {'frame': 45}, altered_normal, altered_consensus)['ok'])

    def test_launch_uses_private_fixture_only_for_selected_role(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = SimpleNamespace(build_root=root, game_root=root, iso=root/'game.iso',
                                   fixture=root/'source.slp', mode='loopback', delay=2,
                                   empty_mods=root/'empty-mods')
            seen = []
            def fake_popen(command, **kwargs):
                seen.append(kwargs['env']['MELEE_SLP'])
                return SimpleNamespace(pid=123, stdin=io.BytesIO())
            with mock.patch.object(runner.psutil, 'virtual_memory',
                                   return_value=SimpleNamespace(available=16 * 1024**3)), \
                 mock.patch.object(runner.subprocess, 'Popen', side_effect=fake_popen), \
                 mock.patch.object(runner, 'OwnedRun',
                                   side_effect=lambda process, exe, directory, log, launched_after:
                                   SimpleNamespace(close=log.close)):
                first = runner.launch(args, 1, (45001, 45002), 'first', 'ab'*16, [],
                                      fixture_override=root/'altered.slp')
                second = runner.launch(args, 2, (45001, 45002), 'second', 'ab'*16, [])
                first.close()
                second.close()
            self.assertEqual(seen, [(root/'altered.slp').as_posix(),
                                    (root/'source.slp').as_posix()])

    def test_evidence_pid_must_belong_to_that_launch(self):
        owned = SimpleNamespace(games={321: (100.0, 'C:/run/melee-pc.exe')})
        runner.verify_owned_game({'process_id': 321}, owned)
        for foreign in (322, True, '321', None):
            with self.assertRaises(runner.RunError):
                runner.verify_owned_game({'process_id': foreign}, owned)

    def test_failed_launch_cleans_started_process(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = SimpleNamespace(build_root=root, game_root=root, iso=root/'game.iso',
                                   fixture=root/'source.slp', mode='loopback', delay=2,
                                   empty_mods=root/'empty-mods')
            fake = SimpleNamespace(pid=123, stdin=io.BytesIO())
            with mock.patch.object(runner.psutil, 'virtual_memory', return_value=SimpleNamespace(available=16 * 1024**3)), \
                 mock.patch.object(runner.subprocess, 'Popen', return_value=fake), \
                 mock.patch.object(runner, 'OwnedRun', side_effect=RuntimeError('identity unavailable')), \
                 mock.patch.object(runner, 'cleanup_failed_launch') as cleanup:
                with self.assertRaises(RuntimeError):
                    runner.launch(args, 1, (45001, 45002), 'test', 'ab'*16, [])
                cleanup.assert_called_once()
                self.assertIs(cleanup.call_args.args[0], fake)
                self.assertTrue(fake.stdin.closed)

    def test_scoped_game_cleanup_ignores_other_executables(self):
        exe = Path('C:/unique-run/melee-pc.exe')
        own = SimpleNamespace(info={'pid': 501, 'create_time': 200.0,
                                    'exe': str(exe)})
        other = SimpleNamespace(info={'pid': 502, 'create_time': 200.0,
                                      'exe': 'C:/other/melee-pc.exe'})
        older = SimpleNamespace(info={'pid': 503, 'create_time': 100.0,
                                      'exe': str(exe)})
        with mock.patch.object(runner.psutil, 'process_iter', return_value=[own, other, older]), \
             mock.patch.object(runner.OwnedRun, 'stop_identity') as stop:
            runner.stop_copied_games(exe, 150.0)
        stop.assert_called_once_with(501, 200.0, str(exe))

    def test_profile_write_failure_closes_owned_run(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = SimpleNamespace(build_root=root, game_root=root, iso=root/'game.iso',
                                   fixture=root/'source.slp', mode='direct', delay=2,
                                   empty_mods=root/'empty-mods')
            stdin = mock.Mock()
            stdin.closed = False
            stdin.write.side_effect = BrokenPipeError('provider secret must not be reported')
            process = SimpleNamespace(pid=123, stdin=stdin)
            owned = mock.Mock()
            with mock.patch.object(runner.psutil, 'virtual_memory', return_value=SimpleNamespace(available=16 * 1024**3)), \
                 mock.patch.object(runner.subprocess, 'Popen', return_value=process), \
                 mock.patch.object(runner, 'OwnedRun', return_value=owned):
                with self.assertRaises(BrokenPipeError):
                    runner.launch(args, 1, (45001, 45002), 'test', 'ab'*16,
                                  [{'uid': 'one'}, {'connectCode': 'TWO#123'}])
            owned.close.assert_called_once()

    def test_safe_local_error_text(self):
        with mock.patch.object(runner.psutil, 'virtual_memory',
                               return_value=SimpleNamespace(available=0)):
            with self.assertRaisesRegex(runner.RunError, 'fewer than 8 GiB'):
                runner.launch(None, 1, (45001, 45002), 'test', 'ab'*16, [])


if __name__ == '__main__':
    unittest.main()
