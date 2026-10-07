"""Exercise the Linux release guard (check_release_linux.py) on a complete and on damaged packages."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT/'tools/release/check_release_linux.py'
RULES = json.loads((ROOT/'tools/release/mod_rules.json').read_text(encoding='utf-8'))['mods']


def run(path):
    r = subprocess.run([sys.executable, str(GUARD), str(path), '--repo-root', str(ROOT)], text=True, capture_output=True)
    return r.returncode, r.stdout+r.stderr


class LinuxGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = Path(tempfile.mkdtemp(prefix='linux-guard-'))
        cls.stage = cls.work/'GDMelee-fixture-linux-x86_64'
        cls.stage.mkdir()
        proto = (ROOT/'tools/release/netplay_protocol.ps1').read_text()
        import re
        number = re.search(r'return (\d+)', proto)[1]
        files = {'README.txt': 'r', 'IMPLEMENTATION_STATUS.md': 's', 'bin/melee': b'\x7fELF\x01synthetic',
                 'bin/melee-pc.msvc.map': 'map', 'launcher/bin/gd-melee-launcher': b'\x7fELF\x02synthetic',
                 'licenses/GPL-2.0.txt': 'gpl', 'licenses/THIRD-PARTY-NOTICES.txt': 'n',
                 'launcher/licenses/BarlowCondensed-OFL-1.1.txt': 'ofl',
                 'lib/libSDL3.so.0': b'\x7fELF\x01lib', 'udev/51.rules': 'x',
                 'mods/README.txt': 'm', 'mods/enabled.txt': '# on\ngeno-lab\nenvoy\nenvoy_drives\n',
                 'mods/geno-lab/mod.json': '{}', 'mods/envoy/mod.json': '{}', 'mods/envoy/scripts/main.lua': 'x',
                 'mods/envoy/shaders/crit.wgsl': 'x', 'mods/envoy_drives/mod.json': '{}',
                 'mods/envoy_drives/models/a.gxmesh': 'x', 'mods/envoy_drives/models/a.gxtex': 'x',
                 'mods/vanilla-striker/mod.json': '{}', 'mods/vanilla-striker/moves/jab.words': 'x'}
        version = f'fixture\nmelee      {40*"a"}  src\nnetplay_protocol {number}\n'
        files['version.txt'] = version
        files['bin/version.txt'] = version
        for mid in ('envoy', 'envoy_drives'):          # every file a mod's 'required' list names
            for need in RULES[mid]['required']:
                files[f'mods/{mid}/{need}'] = '{}' if need.endswith('.json') else 'x'
        for name, data in files.items():
            cls.put(name, data)
        for name in subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only', 'HEAD', '--', '_build/ui'], text=True).splitlines():
            cls.put('assets/'+name.removeprefix('_build/'), subprocess.check_output(['git', '-C', str(ROOT), 'show', 'HEAD:'+name]))

    @classmethod
    def put(cls, name, data):
        f = cls.stage/name
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(data if isinstance(data, bytes) else data.encode())
        return f

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work)

    def manifests(self):
        sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        rt = [p for p in sorted(self.stage.rglob('*')) if p.is_file() and p.relative_to(self.stage).as_posix() not in ('runtime.sha256', 'manifest.json')]
        (self.stage/'runtime.sha256').write_bytes(''.join(f'{sha(p)}  {p.relative_to(self.stage).as_posix()}\n' for p in rt).encode())
        allf = [p for p in sorted(self.stage.rglob('*')) if p.is_file() and p.relative_to(self.stage).as_posix() != 'manifest.json']
        (self.stage/'manifest.json').write_text(json.dumps({'files': {p.relative_to(self.stage).as_posix(): sha(p) for p in allf}}))

    def expect_fail(self, text):
        self.manifests()
        code, log = run(self.stage)
        self.assertNotEqual(code, 0, log)
        self.assertIn(text, log)

    def undo(self, *names):
        for n in names:
            p = self.stage/n
            if p.is_dir():
                shutil.rmtree(p)
            elif p.exists():
                p.unlink()

    def test_complete_folder_and_tarball_pass(self):
        self.manifests()
        code, log = run(self.stage)
        self.assertEqual(code, 0, log)
        archive = self.work/'p.tar.xz'
        with tarfile.open(archive, 'w:xz') as t:
            t.add(self.stage, arcname=self.stage.name)
        code, log = run(archive)
        self.assertEqual(code, 0, log)

    def test_netplay_server_txt_beside_the_game_and_the_launcher_passes(self):
        # package_linux.py --server writes it in both places, like build_release.ps1 -Server
        added = [self.put(n, 'netplay.example:51600\n') for n in ('netplay_server.txt', 'bin/netplay_server.txt')]
        self.manifests()
        try:
            code, log = run(self.stage)
            self.assertEqual(code, 0, log)
        finally:
            for f in added: f.unlink()
            self.manifests()

    def test_disc_extension_header_and_hsd_shape_are_rejected(self):
        cases = [('assets/ui/x.iso', b'x'*64, "'.iso' files are disc data"),
                 ('lib/GALE01.txt', b'GALE01'+b'x'*64, 'game ID'),
                 ('mods/envoy/scripts/blob.lua', (200).to_bytes(4, 'big')+b'x'*196, 'HSD archive')]
        for name, data, text in cases:
            with self.subTest(name=name):
                try:
                    self.put(name, data)
                    self.expect_fail(text)
                finally:
                    self.undo(name)

    def test_private_mods_and_unlisted_files_are_rejected(self):
        for mod in ('envoy_drives_sa2', 'metaknight-slot', 'ultimate-kirby', 'local-assets', 'ace-wolf'):
            with self.subTest(mod=mod):
                try:
                    self.put(f'mods/{mod}/mod.json', '{}')
                    self.expect_fail('never-package')
                finally:
                    self.undo('mods/'+mod)
        for name in ('mods/envoy/tools/make.py', 'mods/envoy/art/a.png', 'mods/vanilla-striker/files/PlMr.dat'):
            with self.subTest(name=name):
                try:
                    self.put(name, b'x'*64)
                    self.manifests()
                    self.assertNotEqual(run(self.stage)[0], 0)
                finally:
                    self.undo(name)

    def test_original_dat_needs_the_record_and_no_other_fighter(self):
        rel = 'mods/vanilla-courier/files/GnCourier_default.dat'
        try:
            self.put('mods/vanilla-courier/mod.json', '{}')
            data = b'\0'*4+b'PlyCourier_Share_joint courier_joint'+b'\0'*40
            self.put(rel, data)
            self.expect_fail('does not list is disc data')
            record = lambda d: json.dumps({'files': [{'path': rel, 'sha256': hashlib.sha256(d).hexdigest()}]})
            self.put('mods/original-assets.json', record(data))
            self.manifests()
            self.assertEqual(run(self.stage)[0], 0, run(self.stage)[1])
            bad = data+b' PlyMario5K_Share_joint'
            self.put(rel, bad)
            self.put('mods/original-assets.json', record(bad))
            self.expect_fail("another fighter's symbol")
        finally:
            self.undo('mods/vanilla-courier', 'mods/original-assets.json')

    def test_enabled_txt_and_protocol_and_manifest(self):
        f = self.stage/'mods/enabled.txt'
        before = f.read_bytes()
        try:
            f.write_bytes(before+b'vanilla-striker\n')
            self.expect_fail('must ship off by default')
        finally:
            f.write_bytes(before)
        v = self.stage/'version.txt'
        before = v.read_bytes()
        try:
            v.write_bytes(before.replace(b'netplay_protocol', b'netplay_protocol 1 #'))
            self.expect_fail('netplay_protocol')
        finally:
            v.write_bytes(before)
        self.manifests()
        (self.stage/'README.txt').write_bytes(b'changed after the manifest')
        try:
            code, log = run(self.stage)
            self.assertNotEqual(code, 0, log)
            self.assertIn('runtime.sha256', log)
        finally:
            (self.stage/'README.txt').write_bytes(b'r')

    def test_the_package_must_carry_the_default_on_mods(self):
        # the Linux package carries the same mods as the Windows zip: a package without them fails
        for name in ('mods/envoy/mod.json', 'mods/geno-lab/mod.json'):
            data = (self.stage/name).read_bytes()
            try:
                self.undo(name)
                self.expect_fail('missing required file: '+name)
            finally:
                self.put(name, data)
        f = self.stage/'mods/enabled.txt'
        before = f.read_bytes()
        try:
            f.write_bytes(b'# on\ngeno-lab\nenvoy\n')
            self.expect_fail("does not turn on 'envoy_drives'")
            f.write_bytes(b'# on\ngeno-lab\nenvoy\nenvoy_drives\nenvoy_drives_sa2\n')
            self.expect_fail('not a mod this release carries')
        finally:
            f.write_bytes(before)
        try:
            self.undo('mods/enabled.txt')
            self.expect_fail('missing required file: mods/enabled.txt')
        finally:
            f.write_bytes(before)
        self.manifests()
        self.assertEqual(run(self.stage)[0], 0)

    def test_a_missing_envoy_shader_or_drive_model_fails_the_guard(self):
        for mid, need in [(m, n) for m in ('envoy', 'envoy_drives') for n in RULES[m]['required']]:
            with self.subTest(file=f'{mid}/{need}'):
                name = f'mods/{mid}/{need}'
                data = (self.stage/name).read_bytes()
                try:
                    self.undo(name)
                    self.expect_fail('missing required file: '+name)
                finally:
                    self.put(name, data)
        self.manifests()
        self.assertEqual(run(self.stage)[0], 0)

    def test_the_launcher_must_ship_barlows_licence(self):
        name = 'launcher/licenses/BarlowCondensed-OFL-1.1.txt'
        data = (self.stage/name).read_bytes()
        try:
            self.undo(name)
            self.expect_fail('missing required file: '+name)
        finally:
            self.put(name, data)
        self.manifests()
        self.assertEqual(run(self.stage)[0], 0)

    def test_a_package_with_no_mods_folder_fails(self):
        keep = {}
        for p in sorted((self.stage/'mods').rglob('*')):
            if p.is_file():
                keep[p.relative_to(self.stage).as_posix()] = p.read_bytes()
        try:
            self.undo('mods')
            self.expect_fail('missing required file: mods/geno-lab/mod.json')
        finally:
            for name, data in keep.items():
                self.put(name, data)

    def test_personal_path_in_our_binary_is_rejected(self):
        f = self.stage/'bin/melee'
        before = f.read_bytes()
        try:
            f.write_bytes(before+b'/home/builder1/src/melee.c\0')
            self.expect_fail('personal path')
        finally:
            f.write_bytes(before)


if __name__ == '__main__':
    unittest.main()
