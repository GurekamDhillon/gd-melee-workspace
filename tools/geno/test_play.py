"""Resolution tests: no shell, game, Blender, disc data or build tools required."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from tools.geno import play


class PlayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.put('.git', 'gitdir: unused')
        # Tests may keep TEMP inside a worktree; stop parent .env discovery at this fixture.
        self.put('.env', '')
        self.put('tools/port/run.sh', '# synthetic wrapper, never run')
        self.project = self.root / 'ports/second fighter'
        self.config = {'schema': 'workbench/1', 'id': 'second', 'mod_id': 'second',
                       'gameplay': 'gameplay.json', 'moves_dir': 'moves',
                       'plan_abs': '_build/second/mods/second/files/plan.json',
                       'mods_dir': '_build/second/mods',
                       'rebuild': ['python', 'ports/second/tools/build.py', '--fighter',
                                   '_build/second/fighter.json', '--auto']}
        self.put('ports/second fighter/workbench.json', self.config)
        self.put('ports/second fighter/gameplay.json', {'moves': [
            {'name': 'jab1', 'motions': [44]},
            {'name': 'custom', 'motions': [70], 'pick': {'clip': 'CustomPose'}}]})
        self.put('ports/second fighter/moves/jab1.genoasm', 'end')
        self.package = self.root / '_build/second/mods/second'
        self.put('_build/second/mods/second/mod.json', {'id': 'second'})
        self.put('_build/second/mods/second/geno.json', {'geno': 10, 'fighters': [
            {'define': {'key': 'second', 'base': 'none'},
             'fighter': {'plan': 'plan.json'}}]})
        self.put('_build/second/mods/second/files/plan.json', {
            'motion_rows': [{'motion': 44, 'row': 46, 'clip': 'Attack11'}],
            'bank': {'clips': [{'name': 'Attack11'}, {'name': 'CustomPose'}]}})
        self.put('_build/second/mods/geno-lab/mod.json', {'id': 'geno-lab'})
        self.put('_build/second/mods/enabled.txt', 'geno-lab\nsecond\n')
        self.put('_build/melee-pc.exe', 'synthetic executable; never run')
        self.put('own.iso', 'synthetic path fixture; never read')
        self.env = {'GW_ISO_VANILLA': str(self.root / 'own.iso'), 'GW_BASH': 'git bash.exe'}
        for p in self.root.rglob('*'):
            if p.is_file(): os.utime(p, ns=(1_000_000_000, 1_000_000_000))
        for p in (self.package / 'geno.json', self.package / 'mod.json'):
            os.utime(p, ns=(2_000_000_000, 2_000_000_000))

    def put(self, name, value):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value) if isinstance(value, dict) else value, encoding='utf-8')
        return p

    def resolve(self, **kwargs):
        return play.resolve_project(self.project, root=self.root, env=self.env,
                                    run_name=kwargs.pop('run_name', 'second-lab-test'), **kwargs)

    def test_lab_resolves_package_scene_and_wrapper_run_directory(self):
        p = self.resolve()
        self.assertEqual(p.key, 'second')
        self.assertEqual(p.package, self.package)
        self.assertEqual(p.scene, 'mode=lab;p1=geno:second/hu;p2=mario/cpu0;stage=fd;items=off;time=0')
        self.assertEqual(p.run_dir, self.root / '_build/runs/second-lab-test')
        self.assertEqual(p.log_path, p.run_dir / 'melee-pc.log')
        self.assertEqual(p.argv, ('git bash.exe', str(self.root / 'tools/port/run.sh'),
                                '--realtime', 'second-lab-test', '--iso', str(self.root / 'own.iso')))
        self.assertFalse(p.stale)

    def test_current_move_uses_animation_row_not_motion_or_display_name(self):
        p = self.resolve(clip='jab1')
        self.assertEqual(p.env['MELEE_LAB_CLIP'], '46')
        self.assertEqual(p.env['MELEE_LAB_MODE'], 'clips')
        self.assertEqual(p.env['MELEE_CPU_IDLE'], '1')
        self.assertEqual(self.resolve(clip='custom').env['MELEE_LAB_CLIP'], 'CustomPose')
        self.assertEqual(self.resolve(clip='303').env['MELEE_LAB_CLIP'], '303')

    def test_unknown_workbench_row_is_actionable(self):
        with self.assertRaisesRegex(play.PlayError, 'clip|row'):
            self.resolve(clip='misspelled_move')

    def test_vs_cpu_uses_cpu9_and_clears_inherited_lab_and_batch_flags(self):
        self.env.update({'MELEE_TURBO': '1', 'MELEE_UNATTENDED': '1', 'MELEE_FPS': 'u',
                         'MELEE_WINDOW_HIDE': '1', 'MELEE_FULLSCREEN': '1',
                         'MELEE_LAB_MODE': 'clips', 'MELEE_LAB_CLIP': '999',
                         'MELEE_LAB_BATCH': '1', 'MELEE_LAB_BATCH_QUIT': '1',
                         'MELEE_CPU_IDLE': '1', 'MELEE_PAD_SCRIPT': 'batch.lua',
                         'MELEE_CONSOLE_PORT': '51726', 'MELEE_WORKBENCH': '1',
                         'MELEE_WB_HEADLESS': '1', 'MELEE_WINDOW_X': '30000', 'MELEE_WINDOW_Y': '30000',
                         'MELEE_PAD_IGNORE_ADAPTER': '1'})
        p = self.resolve(mode='vs', clip='jab1')
        self.assertEqual(p.scene, 'mode=vs;p1=geno:second/hu;p2=mario/cpu9;stage=fd;items=off;time=0')
        for key in ('MELEE_TURBO', 'MELEE_UNATTENDED', 'MELEE_WINDOW_HIDE', 'MELEE_FULLSCREEN', 'MELEE_MAX_SECONDS'):
            self.assertEqual(p.env[key], '0')
        self.assertEqual(p.env['MELEE_FPS'], '60')
        for key in ('MELEE_LAB_MODE', 'MELEE_LAB_CLIP', 'MELEE_CPU_IDLE', 'MELEE_PAD_SCRIPT',
                    'MELEE_WORKBENCH', 'MELEE_CONSOLE_PORT', 'MELEE_WB_HEADLESS',
                    'MELEE_LAB_BATCH', 'MELEE_LAB_BATCH_QUIT',
                    'MELEE_WINDOW_X', 'MELEE_WINDOW_Y', 'MELEE_PAD_IGNORE_ADAPTER'):
            self.assertNotIn(key, p.env)
        self.assertEqual(self.env['MELEE_TURBO'], '1')

    def test_sources_newer_than_package_offer_only_gameplay_rebuild(self):
        source = self.project / 'moves/jab1.genoasm'
        os.utime(source, ns=(3_000_000_000, 3_000_000_000))
        p = self.resolve()
        self.assertTrue(any('jab1.genoasm' in reason for reason in p.stale))
        self.assertEqual(p.rebuild_argv, ('python', 'ports/second/tools/build.py', '--fighter',
                                        '_build/second/fighter.json', '--gameplay-only'))
        self.assertNotIn('--auto', p.rebuild_argv)

    def test_view_only_project_can_play_but_cannot_rebuild(self):
        self.config['rebuild'] = []
        self.put('ports/second fighter/workbench.json', self.config)
        p = self.resolve()
        self.assertEqual(p.rebuild_argv, ())
        self.assertTrue(p.stale)

    def test_rebuild_preserves_configured_output_and_non_python_executable(self):
        self.config['rebuild'] = ['author build.exe', '--fighter', '_build/second/fighter.json',
                                  '--out', '_build/custom package', '--auto']
        self.put('ports/second fighter/workbench.json', self.config)
        self.assertEqual(self.resolve().rebuild_argv, ('author build.exe', '--fighter',
            '_build/second/fighter.json', '--out', '_build/custom package', '--gameplay-only'))

    def test_missing_package_returns_stale_plan_for_rebuild_offer(self):
        (self.package / 'geno.json').unlink()
        p = self.resolve()
        self.assertTrue(any('geno.json' in reason for reason in p.stale))
        self.assertEqual(p.key, 'second')

    def test_disabled_fighter_or_lab_cannot_silently_boot_retail(self):
        self.put('_build/second/mods/enabled.txt', 'other\n')
        with self.assertRaisesRegex(play.PlayError, 'enabled.txt'):
            self.resolve()
        self.put('_build/second/mods/enabled.txt', 'second\n')
        with self.assertRaisesRegex(play.PlayError, 'geno-lab'):
            self.resolve()
        self.assertEqual(self.resolve(mode='vs').key, 'second')

    def test_define_key_comes_from_installed_package_not_project_display_id(self):
        self.put('_build/second/mods/second/geno.json', {'fighters': [
            {'define': {'key': 'own-key', 'base': 'none'}, 'fighter': {'plan': 'plan.json'}}]})
        self.assertIn('p1=geno:own-key/hu', self.resolve().scene)

    def test_artist_directory_and_fighter_json_use_output_relative_to_config(self):
        cfg = {'schema': 'geno-artist/1', 'key': 'second', 'output': '../../_build/second'}
        source = self.put('artists/second/fighter.json', cfg)
        for arg in (source, source.parent):
            p = play.resolve_project(arg, root=self.root, env=self.env, run_name='artist-test')
            self.assertEqual(p.package, self.package)
            self.assertEqual(p.rebuild_argv, (play.python_executable(self.env), '-m', 'tools.geno.artist',
                'build', str(source), '--out', str(self.root / '_build/second'), '--gameplay-only'))

    def test_artist_default_output_and_adjacent_custom_package(self):
        source = self.put('artist/fighter.json', {'schema': 'geno-artist/1', 'key': 'pip'})
        p = play.resolve_project(source, root=self.root, env=self.env, run_name='pip-test')
        self.assertEqual(p.mods_dir, self.root / '_build/artist/pip/mods')
        self.put('artist/package/mods/pip/mod.json', {'id': 'pip'})
        p = play.resolve_project(source, root=self.root, env=self.env, run_name='pip-test')
        self.assertEqual(p.mods_dir, source.parent / 'package/mods')

    def test_env_file_literals_and_explicit_overrides_do_not_execute_shell(self):
        self.put('.env', 'export GW_ISO_VANILLA="own.iso"\nGW_BUILD_ROOT="_build/lane with spaces"\nUNRELATED=$(touch impossible)\n')
        p = play.resolve_project(self.project, root=self.root, env={'GW_BASH': 'bash'}, run_name='env-test')
        self.assertEqual(p.run_dir, self.root / '_build/lane with spaces/runs/env-test')
        self.assertEqual(p.iso, self.root / 'own.iso')
        self.assertEqual(self.resolve().iso, self.root / 'own.iso')
        self.assertNotIn('UNRELATED', p.env)

    def test_unique_run_names_do_not_share_sandbox(self):
        a = play.resolve_project(self.project, root=self.root, env=self.env)
        b = play.resolve_project(self.project, root=self.root, env=self.env)
        self.assertNotEqual(a.run_dir, b.run_dir)

    def test_invalid_key_config_and_sandbox_names_are_rejected(self):
        for name in ('..', 'nested/run', r'back\slash'):
            with self.assertRaises(play.PlayError): self.resolve(run_name=name)
        self.put('bad.json', {'schema': 'unknown'})
        with self.assertRaisesRegex(play.PlayError, 'schema'):
            play.resolve_project(self.root / 'bad.json', root=self.root, env=self.env)

    def test_plan_does_not_create_run_directory_or_modify_package(self):
        before = (self.package / 'geno.json').read_bytes()
        p = self.resolve(clip='jab1')
        self.assertFalse(p.run_dir.exists())
        self.assertEqual((self.package / 'geno.json').read_bytes(), before)

    def test_named_rows_and_dictionary_bank_match_real_artist_plan_schema(self):
        self.put('_build/second/mods/second/files/plan.json', {
            'motion_rows': [{'motion': 44, 'row': 'Attack11', 'clip': 'AuthoredJab'}],
            'bank': {'clips': {'AuthoredJab': {'symbol': 'PlySecond_Jab', 'frames': 30}}}})
        self.assertEqual(self.resolve(clip='jab1').env['MELEE_LAB_CLIP'], 'AuthoredJab')
        self.assertEqual(self.resolve(clip='Attack11').env['MELEE_LAB_CLIP'], 'AuthoredJab')
        self.assertEqual(self.resolve(clip='AuthoredJab').env['MELEE_LAB_CLIP'], 'AuthoredJab')
        self.assertEqual(self.resolve(clip='PlySecond_Jab').env['MELEE_LAB_CLIP'], 'PlySecond_Jab')

    def test_engine_environment_override_still_uses_run_wrapper(self):
        self.env['GW_ENGINE_EXE'] = str(self.root / '_build/lane/melee-pc.exe')
        p = self.resolve()
        self.assertEqual(p.run_dir, self.root / '_build/lane/runs/second-lab-test')
        self.assertEqual(p.env['GW_BUILD_ROOT'], str(self.root / '_build/lane'))
        self.assertEqual(p.env['GW_ENV_RESOLVED'], '1')
        self.assertIn('--realtime', p.argv)

    def test_lab_clip_play_clears_batch_export_switches(self):
        self.env.update(MELEE_LAB_BATCH='1', MELEE_LAB_BATCH_QUIT='1')
        p = self.resolve(clip='jab1')
        self.assertNotIn('MELEE_LAB_BATCH', p.env)
        self.assertNotIn('MELEE_LAB_BATCH_QUIT', p.env)
        self.assertEqual(p.env['MELEE_LAB_MODE'], 'clips')


    def test_artist_config_preserves_supported_whole_line_comments(self):
        source = self.put('artists/commented/fighter.json',
                          '// Authored project note\n' + json.dumps({
                              'schema': 'geno-artist/1', 'key': 'second',
                              'output': '../../_build/second'}))
        p = play.resolve_project(source, root=self.root, env=self.env, run_name='commented-test')
        self.assertEqual(p.package, self.package)
        self.assertEqual(p.key, 'second')


    def test_windows_discovery_prefers_git_bash_over_the_wsl_shim(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        git = self.put('Git/cmd/git.exe', 'synthetic path fixture; never run')
        bash = self.put('Git/bin/bash.exe', 'synthetic path fixture; never run')
        wsl = self.put('Windows/System32/bash.exe', 'synthetic WSL path; never run')
        def discover(name, **kwargs):
            return str(git if name == 'git' else wsl) if name in ('git', 'bash') else None
        with patch.object(play, 'os', SimpleNamespace(name='nt', defpath=os.defpath)), \
             patch.object(play.shutil, 'which', side_effect=discover):
            self.assertEqual(play._bash({'PATH': 'synthetic'}), str(bash))
            self.assertEqual(play._bash({'GW_BASH': 'explicit bash.exe'}), 'explicit bash.exe')


    def test_gameplay_rebuild_inherits_the_runtime_game_checkout_default(self):
        self.assertEqual(self.resolve().env['GW_MELEE'], str(self.root / 'melee'))
        self.env['GW_MELEE'] = str(self.root / 'alternate game')
        self.assertEqual(self.resolve().env['GW_MELEE'], str(self.root / 'alternate game'))


if __name__ == '__main__':
    unittest.main()
