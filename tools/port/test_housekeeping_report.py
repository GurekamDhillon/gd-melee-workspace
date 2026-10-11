"""Run the report against owned trees, including real Windows junctions."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).absolute().parents[2]
SCRIPT = ROOT / 'tools/port/housekeeping_report.py'
DAY = 86400


class HousekeepingTests(unittest.TestCase):
    def setUp(self):
        tmp = ROOT / '.omo/tmp'
        tmp.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=tmp)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.build = self.root / '_build'
        (self.build / 'runs').mkdir(parents=True)
        (self.build / 'agents').mkdir()
        (self.root / '.git').mkdir()
        (self.root / '.git/HEAD').write_text('ref: refs/heads/ws/main\n')
        (self.root / 'melee/.git').mkdir(parents=True)
        (self.root / 'melee/.git/HEAD').write_text('ref: refs/heads/pc-port\n')

    def worktree(self, name, branch):
        path = self.root / 'worktrees' / name
        path.mkdir(parents=True)
        reg = self.root / '.git/worktrees' / name
        reg.mkdir(parents=True)
        (reg / 'gitdir').write_text(str(path / '.git') + '\n')
        (reg / 'HEAD').write_text('ref: refs/heads/' + branch + '\n')
        (path / '.git').write_text('gitdir: ' + str(reg) + '\n')
        return path

    def old(self, path):
        timestamp = time.time() - 10 * DAY
        for p in sorted(path.rglob('*'), key=lambda p: len(p.parts), reverse=True):
            os.utime(p, (timestamp, timestamp))
        os.utime(path, (timestamp, timestamp))

    def run_report(self, build=None, days='7', as_json=True):
        args = [sys.executable, str(SCRIPT), '--build', str(build or self.build),
                '--workspace', str(self.root), '--days', days]
        if as_json:
            args.append('--json')
        result = subprocess.run(args, capture_output=True, text=True,
                                env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout) if as_json else result.stdout

    def junction(self, link, target):
        # Both resolved absolute paths must stay within this test's owned tree.
        for p in (link, target):
            self.assertTrue(p.absolute().is_relative_to(self.root.absolute()))
        if os.name == 'nt':
            driver = self.root / 'junction.cmd'
            driver.write_text(f'@echo off\nmklink /J "{link}" "{target}"\n')
            result = subprocess.run([os.environ['ComSpec'], '/d', '/c', str(driver)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.addCleanup(os.rmdir, link)
        else:
            link.symlink_to(target, target_is_directory=True)
            self.addCleanup(link.unlink)

    def test_old_rows_have_sizes_owners_and_leave_every_file_unchanged(self):
        self.worktree('alpha', 'ws/alpha')
        agent = self.build / 'agents/alpha'
        (agent / 'runs/one').mkdir(parents=True)
        (agent / 'obj').write_bytes(b'abcd')
        (agent / 'runs/one/log').write_bytes(b'xyz')
        run = self.build / 'runs/old'
        run.mkdir(); (run / 'log').write_bytes(b'hello')
        self.old(agent); self.old(run)
        before = {str(p): (p.read_bytes(), p.stat().st_mtime_ns)
                  for p in self.root.rglob('*') if p.is_file()}
        report = self.run_report()
        rows = {Path(r['path']).relative_to(self.build).as_posix(): r for r in report['entries']}
        self.assertEqual(set(rows), {'agents/alpha', 'agents/alpha/runs/one', 'runs/old'})
        self.assertEqual(rows['agents/alpha']['bytes'], 7)
        self.assertEqual(rows['agents/alpha/runs/one']['bytes'], 3)
        self.assertEqual(rows['runs/old']['bytes'], 5)
        self.assertEqual(rows['agents/alpha']['owners'][0]['branch'], 'ws/alpha')
        self.assertEqual(rows['runs/old']['owners'][0]['branch'], 'pc-port')
        self.assertEqual(rows['agents/alpha']['ownership_basis'], 'name convention (inferred)')
        self.assertEqual(before, {str(p): (p.read_bytes(), p.stat().st_mtime_ns)
                                  for p in self.root.rglob('*') if p.is_file()})

    def test_recent_nested_file_keeps_a_root_out_of_old_candidates(self):
        agent = self.build / 'agents/unknown'
        (agent / 'nested').mkdir(parents=True)
        (agent / 'nested/active').write_bytes(b'active')
        self.old(agent)
        os.utime(agent / 'nested/active', None)
        self.assertEqual(self.run_report()['entries'], [])

    def test_cmake_source_evidence_wins_over_a_misleading_root_name(self):
        self.worktree('alpha', 'ws/alpha')
        actual = self.worktree('beta', 'ws/beta')
        agent = self.build / 'agents/alpha'
        (agent / 'ax86m').mkdir(parents=True)
        (agent / 'ax86m/CMakeCache.txt').write_text(
            'CMAKE_HOME_DIRECTORY:INTERNAL=' + str(actual / 'extern/aurora') + '\n')
        self.old(agent)
        row = self.run_report()['entries'][0]
        self.assertEqual(row['owners'][0]['branch'], 'ws/beta')
        self.assertEqual(row['ownership_basis'], 'CMake source path')

    def test_run_owner_label_overrides_main_location_convention(self):
        self.worktree('alpha', 'ws/alpha')
        run = self.build / 'runs/custom'; run.mkdir()
        (run / 'run.json').write_text(json.dumps({'owner': 'alpha / custom'}))
        self.old(run)
        row = self.run_report()['entries'][0]
        self.assertEqual(row['owners'][0]['branch'], 'ws/alpha')
        self.assertEqual(row['owner_label'], 'alpha / custom')
        self.assertEqual(row['ownership_basis'], 'run owner label (inferred)')

    def test_copied_dependency_cache_does_not_claim_main_source_ownership(self):
        self.worktree('alpha', 'ws/alpha')
        agent = self.build / 'agents/alpha'
        (agent / 'copied-dependency').mkdir(parents=True)
        (agent / 'copied-dependency/CMakeCache.txt').write_text(
            'CMAKE_HOME_DIRECTORY:INTERNAL=' + str(agent / 'dependency-source') + '\n')
        self.old(agent)
        row = self.run_report()['entries'][0]
        self.assertEqual(row['owners'][0]['branch'], 'ws/alpha')
        self.assertEqual(row['ownership_basis'], 'name convention (inferred)')

    def test_hardlinks_are_reported_as_logical_bytes(self):
        run = self.build / 'runs/hardlinks'; run.mkdir()
        (run / 'a').write_bytes(b'abcde')
        os.link(run / 'a', run / 'b'); self.old(run)
        self.assertEqual(self.run_report()['entries'][0]['bytes'], 10)

    def test_unknown_run_label_does_not_guess_main_checkout(self):
        run = self.build / 'runs/custom'; run.mkdir()
        (run / 'run.json').write_text(json.dumps({'owner': 'removed / custom'}))
        self.old(run)
        row = self.run_report()['entries'][0]
        self.assertEqual(row['owners'], [])
        self.assertEqual(row['owner_label'], 'removed / custom')

    def test_unknown_owner_is_explicit(self):
        agent = self.build / 'agents/orphan'
        agent.mkdir(); self.old(agent)
        row = self.run_report()['entries'][0]
        self.assertEqual(row['owners'], [])
        self.assertEqual(row['ownership_basis'], 'unknown')
        self.assertIn('owner=unknown', self.run_report(as_json=False))

    def test_ambiguous_name_reports_both_current_branches(self):
        self.worktree('alpha', 'ws/alpha')
        reg = self.root / 'melee/.git/worktrees/alpha'
        reg.mkdir(parents=True)
        (reg / 'gitdir').write_text(str(self.root / 'game-worktrees/alpha/.git') + '\n')
        (reg / 'HEAD').write_text('ref: refs/heads/agent/alpha\n')
        agent = self.build / 'agents/alpha'; agent.mkdir(); self.old(agent)
        row = self.run_report()['entries'][0]
        self.assertEqual({o['branch'] for o in row['owners']}, {'ws/alpha', 'agent/alpha'})
        self.assertTrue(row['ownership_ambiguous'])

    def test_independent_nested_source_owners_are_both_reported(self):
        agent = self.build / 'agents/mixed'
        (agent / 'launcher').mkdir(parents=True)
        (agent / 'aurora').mkdir()
        (agent / 'launcher/CMakeCache.txt').write_text(
            'CMAKE_HOME_DIRECTORY:INTERNAL=' + str(self.root / 'tools/release/launcher/qt') + '\n')
        (agent / 'aurora/CMakeCache.txt').write_text(
            'CMAKE_HOME_DIRECTORY:INTERNAL=' + str(self.root / 'melee/extern/aurora') + '\n')
        self.old(agent)
        row = self.run_report()['entries'][0]
        self.assertEqual({o['branch'] for o in row['owners']}, {'ws/main', 'pc-port'})
        self.assertTrue(row['ownership_ambiguous'])

    def test_root_and_nested_junctions_are_flagged_and_targets_never_counted(self):
        target = self.root / 'target'; target.mkdir()
        (target / 'important').write_bytes(b'keep' * 100)
        agent = self.build / 'agents/old'; agent.mkdir()
        (agent / 'log').write_bytes(b'ok'); self.old(agent)
        self.junction(agent / 'aurora', target)
        self.junction(self.build / 'agents/linked', target)
        self.junction(self.build / 'runs/linked', target)
        report = self.run_report(days='0')
        self.assertEqual({Path(p['path']).name for p in report['reparse_points']}, {'aurora', 'linked'})
        self.assertEqual(len(report['reparse_points']), 3)
        self.assertEqual(report['entries'][0]['bytes'], 2)
        self.assertEqual((target / 'important').read_bytes(), b'keep' * 100)
        self.assertIn('REPARSE', self.run_report(days='0', as_json=False))

    def test_linked_build_ancestor_is_flagged_without_traversing(self):
        alias = self.root / 'alias'; self.junction(alias, self.build)
        report = self.run_report(build=alias / 'nested')
        self.assertEqual(report['entries'], [])
        self.assertEqual(report['reparse_points'][0]['path'], str(alias))

    def test_linked_runs_container_is_flagged_without_traversing(self):
        target = self.root / 'target'; (target / 'child').mkdir(parents=True)
        os.rmdir(self.build / 'runs')
        self.junction(self.build / 'runs', target)
        report = self.run_report()
        self.assertEqual(report['entries'], [])
        self.assertEqual(report['reparse_points'][0]['path'], str(self.build / 'runs'))

    def test_invalid_age_is_rejected(self):
        for value in ('-1', 'nan', 'inf'):
            result = subprocess.run([sys.executable, str(SCRIPT), '--days', value],
                                    capture_output=True, text=True,
                                    env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
            self.assertEqual(result.returncode, 2)
            self.assertIn('finite non-negative', result.stderr)


if __name__ == '__main__':
    unittest.main()
