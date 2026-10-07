"""Exercise mod_package.py (the Linux packager's mod copy) on a throwaway melee repository, offline.

    python3 tools/release/test_mod_package.py

The fixture is a tiny git repo laid out like the melee checkout. The last test also stages the real mods of the
workspace's melee checkout (when one is present) and runs the Linux guard over a package that holds them.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
import mod_package  # noqa: E402
import check_release_linux  # noqa: E402

RULES = mod_package.load_rules()


def git(repo, *args):
    subprocess.run(['git', '-C', str(repo), '-c', 'user.name=t', '-c', 'user.email=t@t', *args], check=True, capture_output=True)


def put(base, rel, data=b'x'):
    f = Path(base) / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_bytes(data if isinstance(data, bytes) else data.encode())


class StageModsTests(unittest.TestCase):
    def setUp(self):
        self.work = Path(tempfile.mkdtemp(prefix='modpkg-'))
        self.melee = self.work / 'melee'
        self.melee.mkdir()
        git(self.melee, 'init', '-q')
        self.dest = self.work / 'pkg'
        for mid, mod in RULES['mods'].items():
            if mod.get('optional'):
                continue
            put(self.melee, mod['source'] + '/mod.json', '{}')
        for mid, mod in RULES['mods'].items():                           # the files a mod needs to work
            for need in mod.get('required', []):
                put(self.melee, mod['source'] + '/' + need, '{}' if need.endswith('.json') else 'x')
        put(self.melee, 'pc/geno/mods/geno-lab/scripts/lab.lua')
        put(self.melee, 'pc/geno/mods/geno-lab/art/hero.png')            # allowed by no pattern: stays out
        put(self.melee, 'pc/scripts/examples/envoy/scripts/main.lua')    # envoy is a mod, not an example
        put(self.melee, 'pc/scripts/examples/state_overlay.lua')
        put(self.melee, 'pc/scripts/examples/notes.md')

    def tearDown(self):
        shutil.rmtree(self.work, ignore_errors=True)

    def stage(self):
        git(self.melee, 'add', '-A')
        return mod_package.stage_mods(self.melee, self.dest, workspace=ROOT, log=lambda *_: None)

    def files(self):
        return {p.relative_to(self.dest).as_posix() for p in self.dest.rglob('*') if p.is_file()}

    def test_copies_the_rule_table_and_nothing_else(self):
        enabled, off, warnings = self.stage()
        self.assertEqual(warnings, [])
        self.assertEqual(enabled, [m for m, r in RULES['mods'].items() if r.get('default_on')])
        self.assertEqual(off, [m for m, r in RULES['mods'].items() if not r.get('default_on') and not r.get('optional')])
        files = self.files()
        self.assertIn('mods/geno-lab/scripts/lab.lua', files)
        self.assertNotIn('mods/geno-lab/art/hero.png', files)
        self.assertNotIn('mods/vanilla-courier/mod.json', files)         # optional: never in a Linux package
        self.assertIn('scripts/examples/state_overlay.lua', files)
        self.assertFalse([f for f in files if 'examples/envoy' in f or f.endswith('notes.md')])
        listed = [l for l in (self.dest / 'mods/enabled.txt').read_text().splitlines() if not l.startswith('#')]
        self.assertEqual(listed, enabled)

    def test_untracked_allowed_file_is_refused(self):
        put(self.melee, 'pc/geno/mods/geno-lab/scripts/local.lua')
        git(self.melee, 'add', '-A')
        git(self.melee, 'rm', '-q', '--cached', 'pc/geno/mods/geno-lab/scripts/local.lua')
        with self.assertRaises(SystemExit) as c:
            mod_package.stage_mods(self.melee, self.dest, workspace=ROOT, log=lambda *_: None)
        self.assertIn('not tracked', str(c.exception))

    def test_envoy_shaders_and_drive_models_are_staged(self):
        self.stage()
        files = self.files()
        for mid in ('envoy', 'envoy_drives'):
            for need in RULES['mods'][mid]['required']:
                self.assertIn(f'mods/{mid}/{need}', files)
        self.assertFalse([f for f in files if 'sa2' in f.lower()])

    def test_a_missing_required_shader_or_model_stops_the_packaging(self):
        for mid, need in [(m, n) for m in ('envoy', 'envoy_drives') for n in RULES['mods'][m]['required']]:
            with self.subTest(file=f'{mid}/{need}'):
                f = self.melee / RULES['mods'][mid]['source'] / need
                data = f.read_bytes()
                f.unlink()
                try:
                    git(self.melee, 'add', '-A')
                    with self.assertRaises(SystemExit) as c:
                        mod_package.stage_mods(self.melee, self.dest, workspace=ROOT, log=lambda *_: None)
                    self.assertIn(need, str(c.exception))
                    self.assertIn('required', str(c.exception))
                finally:
                    f.write_bytes(data)
                    shutil.rmtree(self.dest, ignore_errors=True)

    def test_a_required_file_that_no_allow_pattern_names_is_refused(self):
        rules = json.loads(json.dumps(RULES))
        rules['mods']['envoy']['required'].append('shaders/not-allowed/deep.wgsl')
        put(self.melee, rules['mods']['envoy']['source'] + '/shaders/not-allowed/deep.wgsl')
        git(self.melee, 'add', '-A')
        with self.assertRaises(SystemExit) as c:
            mod_package.stage_mods(self.melee, self.dest, rules=rules, workspace=ROOT, log=lambda *_: None)
        self.assertIn('deep.wgsl', str(c.exception))

    def test_never_package_names_are_refused(self):
        # vanilla-hero allows fx/.+\.json, so these paths are allowed by the pattern and refused by name
        for rel in ('local-assets/x.json', '_local/x.json', 'envoy_drives_sa2/x.json', 'sora/x.json'):
            with self.subTest(rel=rel):
                put(self.melee, 'pc/geno/mods/vanilla-hero/fx/' + rel)
                with self.assertRaises(SystemExit) as c:
                    self.stage()
                shutil.rmtree(self.dest, ignore_errors=True)
                self.assertIn('never-package', str(c.exception))
                (self.melee / 'pc/geno/mods/vanilla-hero/fx' / rel).unlink()

    def test_a_rule_table_naming_a_private_mod_is_refused(self):
        rules = json.loads(json.dumps(RULES))
        rules['mods']['envoy_drives_sa2'] = {'source': 'x', 'default_on': True, 'allow': ['mod\\.json']}
        git(self.melee, 'add', '-A')
        with self.assertRaises(SystemExit) as c:
            mod_package.stage_mods(self.melee, self.dest, rules=rules, workspace=ROOT, log=lambda *_: None)
        self.assertIn('never-package', str(c.exception))

    def test_disc_data_extension_and_folders_are_refused(self):
        with self.assertRaises(SystemExit):
            mod_package.copy_in(self.melee / 'a.dat', self.dest / 'a.dat', ROOT)
        put(self.work, 'a.iso')
        with self.assertRaises(SystemExit) as c:
            mod_package.copy_in(self.work / 'a.iso', self.dest / 'a.iso', ROOT)
        self.assertIn('disc data', str(c.exception))
        with self.assertRaises(SystemExit) as c:
            mod_package.copy_in(ROOT / '_build/local-assets/ssbm-geno/x.lua', self.dest / 'x.lua', ROOT)
        self.assertIn('local-only', str(c.exception))

    def test_missing_mod_source_is_a_warning(self):
        shutil.rmtree(self.melee / 'pc/geno/mods/vanilla-hero')
        _, _, warnings = self.stage()
        self.assertEqual(len(warnings), 1)
        self.assertIn('vanilla-hero', warnings[0])


class RealMeleeTests(unittest.TestCase):
    def test_real_mods_pass_the_linux_guard(self):
        melee = Path(os.environ['GW_MELEE']) if os.environ.get('GW_MELEE') else ROOT / 'melee'
        if not (melee / 'pc/geno/mods/geno-lab/mod.json').is_file():
            main = Path(subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', '--git-common-dir'], text=True).strip()).resolve().parent / 'melee'
            melee = main
        if not (melee / 'pc/geno/mods/geno-lab/mod.json').is_file():
            self.skipTest('no melee checkout with mods here')
        work = Path(tempfile.mkdtemp(prefix='modpkg-real-'))
        try:
            stage = work / 'GDMelee-fixture-linux-x86_64'
            enabled, off, warnings = mod_package.stage_mods(melee, stage, workspace=ROOT, log=lambda *_: None)
            self.assertEqual(warnings, [])
            self.assertEqual(set(enabled), {'geno-lab', 'envoy', 'envoy_drives'})
            for mid in enabled + off:
                self.assertTrue((stage / 'mods' / mid / 'mod.json').is_file(), mid)
            self.assertFalse((stage / 'mods/envoy_drives_sa2').exists())
            # complete the package with synthetic non-mod files, then run the guard
            number = re.search(r'return (\d+)', (HERE / 'netplay_protocol.ps1').read_text())[1]
            version = f'fixture\nmelee      {40 * "a"}  src\nnetplay_protocol {number}\n'
            for name, data in {'README.txt': 'r', 'IMPLEMENTATION_STATUS.md': 's', 'bin/melee': b'\x7fELF\x01x',
                               'bin/melee-pc.msvc.map': 'm', 'launcher/bin/gd-melee-launcher': b'\x7fELF\x02x',
                               'launcher/licenses/BarlowCondensed-OFL-1.1.txt': 'ofl',
                               'licenses/GPL-2.0.txt': 'g', 'licenses/THIRD-PARTY-NOTICES.txt': 'n',
                               'version.txt': version, 'bin/version.txt': version}.items():
                put(stage, name, data)
            for name in subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only', 'HEAD', '--', '_build/ui'], text=True).splitlines():
                put(stage, 'assets/' + name.removeprefix('_build/'), subprocess.check_output(['git', '-C', str(ROOT), 'show', 'HEAD:' + name]))
            sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
            rel = lambda p: p.relative_to(stage).as_posix()
            rt = [p for p in sorted(stage.rglob('*')) if p.is_file()]
            (stage / 'runtime.sha256').write_text(''.join(f'{sha(p)}  {rel(p)}\n' for p in rt))
            allf = [p for p in sorted(stage.rglob('*')) if p.is_file()]
            (stage / 'manifest.json').write_text(json.dumps({'files': {rel(p): sha(p) for p in allf}}))
            problems, count, _ = check_release_linux.check(stage, ROOT)
            self.assertEqual(problems, [])
            self.assertGreater(count, 50)
        finally:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
