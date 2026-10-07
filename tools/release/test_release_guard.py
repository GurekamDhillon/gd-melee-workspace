"""Exercise the release guard against complete and deliberately damaged bundles."""
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
import warnings
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'_build/audit-20261003/further-release'
RULES = json.loads((ROOT/'tools/release/mod_rules.json').read_text(encoding='utf-8'))['mods']


class ReleaseGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        BASE.mkdir(parents=True, exist_ok=True)
        cls.work = Path(tempfile.mkdtemp(prefix='guard-repairs-', dir=BASE))
        cls.stage = cls.work/'GDMelee-fixture-win64'
        cls.stage.mkdir()
        names = ['README.txt', 'HOW TO PLAY ONLINE.txt', 'LICENSES/GPL-2.0.txt',
                 'LICENSES/THIRD-PARTY-NOTICES.txt', 'melee-pc.exe', 'melee-pc.map',
                 'GD Melee.exe', 'SDL3.dll', 'webgpu_dawn.dll', 'msvcp140.dll',
                 'msvcp140_atomic_wait.dll', 'vcruntime140.dll',
                 'initial_pipeline_cache.db', 'initial_pipeline_cache.core',
                 'launcher/bin/gd-melee-launcher.exe', 'launcher/bin/Qt6Core.dll',
                 'launcher/bin/Qt6Gui.dll', 'launcher/bin/Qt6Widgets.dll',
                 'launcher/bin/msvcp140.dll', 'launcher/bin/vcruntime140.dll',
                 'launcher/bin/vcruntime140_1.dll', 'launcher/bin/qt.conf',
                 'launcher/bin/platforms/qwindows.dll', 'launcher/qt-build.txt',
                 'launcher/licenses/LGPL-3.0-only.txt',
                 'launcher/licenses/Qt-GPL-exception-1.0.txt',
                 'launcher/licenses/SourceSans3-OFL-1.1.txt',
                 'launcher/licenses/BarlowCondensed-OFL-1.1.txt']
        for name in names:
            file = cls.stage/name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b'synthetic release fixture\n')
        for name in subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only', 'HEAD', '--', '_build/ui'], text=True).splitlines():
            file = cls.stage/name.removeprefix('_build/')
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(subprocess.check_output(['git', '-C', str(ROOT), 'show', 'HEAD:'+name]))
        for name, text in {'mods/README.txt': 'mods', 'mods/enabled.txt': '# on\ngeno-lab\nenvoy\nenvoy_drives\n',
                           'mods/geno-lab/mod.json': '{}', 'mods/geno-lab/scripts/main.lua': 'x',
                           'mods/envoy/mod.json': '{}', 'mods/envoy/scripts/main.lua': 'x',
                           'mods/envoy/shaders/crit.wgsl': 'x', 'mods/envoy/items/drive_press/item.json': '{}',
                           'mods/envoy_drives/mod.json': '{}', 'mods/envoy_drives/models/a.gxmesh': 'x',
                           'mods/envoy_drives/models/a.gxtex': 'x', 'mods/envoy_drives/models/a.material.json': '{}',
                           'mods/vanilla-striker/mod.json': '{}', 'mods/vanilla-striker/geno.json': '{}',
                           'mods/vanilla-striker/moves/jab.genoasm': 'x', 'mods/vanilla-striker/moves/jab.words': 'x'}.items():
            file = cls.stage/name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(text)
        for mid in ('envoy', 'envoy_drives'):          # every file a mod's 'required' list names
            for need in RULES[mid]['required']:
                file = cls.stage/'mods'/mid/need
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text('{}' if need.endswith('.json') else 'x')
        (cls.stage/'version.txt').write_text('fixture\nmelee      '+40*'a'+'  source\nnetplay_protocol 5\n')
        cls.stamp = dict(format=1, melee_commit=40*'a', netplay_protocol=5,
                         source_sha256=64*'b', source_dirty=False,
                         files={name:hashlib.sha256((cls.stage/name).read_bytes()).hexdigest()
                                for name in ('melee-pc.exe', 'melee-pc.map')})
        (cls.stage/'build-provenance.json').write_text(json.dumps(cls.stamp))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.work)

    def manifest(self, extra=''):
        (self.stage/'MANIFEST.sha256').write_text(''.join(
            hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(self.stage).as_posix()+'\n'
            for p in sorted(self.stage.rglob('*')) if p.is_file() and p.name != 'MANIFEST.sha256')+extra)

    def check(self, path=None):
        result = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                                 str(ROOT/'tools/release/check_release.ps1'), str(path or self.stage),
                                 '-RepoRoot', str(ROOT)], text=True, capture_output=True)
        return result.returncode, result.stdout+result.stderr

    def test_complete_folder_and_zip_pass(self):
        self.manifest()
        self.assertEqual(self.check()[0], 0, self.check()[1])
        archive = self.work/'release.zip'
        with zipfile.ZipFile(archive, 'w') as out:
            for p in self.stage.rglob('*'):
                if p.is_file():
                    out.write(p, self.stage.name+'/'+p.relative_to(self.stage).as_posix())
        code, log = self.check(archive)
        self.assertEqual(code, 0, log)

    def test_missing_essential_files_are_rejected_even_with_matching_manifest(self):
        for name in ('melee-pc.map', 'SDL3.dll', 'ui/manifest.json',
                     'launcher/bin/Qt6Gui.dll', 'launcher/bin/platforms/qwindows.dll',
                     'launcher/bin/vcruntime140_1.dll', 'build-provenance.json',
                     'launcher/licenses/BarlowCondensed-OFL-1.1.txt'):
            with self.subTest(name=name):
                file = self.stage/name
                data = file.read_bytes()
                try:
                    file.unlink()
                    self.manifest()
                    code, log = self.check()
                    self.assertNotEqual(code, 0, log)
                    self.assertIn('missing required file: '+name, log)
                finally:
                    file.write_bytes(data)

    def test_provenance_must_match_artifacts_and_version(self):
        file = self.stage/'build-provenance.json'
        for field, value in [('format', 2), ('melee_commit', 40*'c'),
                             ('netplay_protocol', 2), ('source_sha256', 'bad'),
                             ('files', {'melee-pc.exe':64*'d', 'melee-pc.map':64*'e'})]:
            with self.subTest(field=field):
                try:
                    file.write_text(json.dumps({**self.stamp, field:value}))
                    self.manifest()
                    code, log = self.check()
                    self.assertNotEqual(code, 0, log)
                    self.assertIn('provenance', log.lower())
                finally:
                    file.write_text(json.dumps(self.stamp))

    def test_malformed_provenance_is_refused(self):
        file = self.stage/'build-provenance.json'
        try:
            file.write_text('{broken')
            self.manifest()
            code, log = self.check()
            self.assertNotEqual(code, 0, log)
            self.assertIn('provenance refused', log)
        finally:
            file.write_text(json.dumps(self.stamp))

    def test_rehashed_replacement_artifacts_cannot_keep_the_old_stamp(self):
        for name in ('melee-pc.exe', 'melee-pc.map'):
            with self.subTest(name=name):
                file = self.stage/name
                before = file.read_bytes()
                try:
                    file.write_bytes(before+b'replacement')
                    self.manifest()
                    code, log = self.check()
                    self.assertNotEqual(code, 0, log)
                    self.assertIn('build provenance hash mismatch: '+name, log)
                finally:
                    file.write_bytes(before)

    def test_manifest_duplicate_is_rejected(self):
        self.manifest(hashlib.sha256((self.stage/'README.txt').read_bytes()).hexdigest()+'  README.txt\n')
        code, log = self.check()
        self.assertNotEqual(code, 0, log)
        self.assertIn('duplicate', log)

    def test_duplicate_zip_entry_is_rejected(self):
        self.manifest()
        archive = self.work/'duplicate.zip'
        with zipfile.ZipFile(archive, 'w') as out:
            for p in self.stage.rglob('*'):
                if p.is_file():
                    out.write(p, self.stage.name+'/'+p.relative_to(self.stage).as_posix())
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', UserWarning)
                out.write(self.stage/'README.txt', self.stage.name+'/README.txt')
        code, log = self.check(archive)
        self.assertNotEqual(code, 0, log)
        self.assertIn('duplicate release entry', log)

    def test_unrecognized_qt_module_remains_blocked(self):
        file = self.stage/'launcher/bin/Qt6WebEngineCore.dll'
        try:
            file.write_bytes(b'unrecognized runtime')
            self.manifest()
            code, log = self.check()
            self.assertNotEqual(code, 0, log)
            self.assertIn('not on the release allowlist', log)
        finally:
            file.unlink()

    def test_wide_personal_path_is_rejected(self):
        file = self.stage/'launcher/bin/Qt6Core.dll'
        before = file.read_bytes()
        try:
            file.write_bytes(before+'C:\\Users\\Builder\\src\\qt.cpp'.encode('utf-16le'))
            self.manifest()
            code, log = self.check()
            self.assertNotEqual(code, 0, log)
            self.assertIn('personal path', log)
        finally:
            file.write_bytes(before)

    # ---- mods: the allowlist from mod_rules.json -------------------------------------------------

    def put(self, name, data=b'x'):
        file = self.stage/name
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(data)
        return file

    def cleanup(self, *names):
        for name in names:
            path = self.stage/name
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()

    def expect_fail(self, text):
        self.manifest()
        code, log = self.check()
        self.assertNotEqual(code, 0, log)
        self.assertIn(text, log)

    def courier(self, data=None, listed=True, symbols=b'PlyCourier_Share_joint courier_joint', name='GnCourier_default.dat'):
        data = data if data is not None else (b'\0'*4+symbols+b'\0'*64)
        rel = 'mods/vanilla-courier/files/'+name
        self.put('mods/vanilla-courier/mod.json', b'{}')
        self.put(rel, data)
        if listed:
            self.put('mods/original-assets.json', json.dumps({'format': 1, 'files': [
                {'path': rel, 'sha256': hashlib.sha256(data).hexdigest()}]}).encode())
        return rel

    def test_envoy_assets_pass(self):
        self.manifest()
        code, log = self.check()
        self.assertEqual(code, 0, log)

    def test_unknown_or_private_mod_is_rejected(self):
        for mod, text in (('envoy_drives_sa2', 'never-package'), ('metaknight-slot', 'never-package'),
                          ('ultimate-kirby', 'never-package'), ('local-assets', 'never-package'),
                          ('ace-wolf', 'never-package'), ('my-fighter', 'not a mod this release carries')):
            with self.subTest(mod=mod):
                try:
                    self.put('mods/'+mod+'/mod.json', b'{}')
                    self.expect_fail(text)
                finally:
                    self.cleanup('mods/'+mod)

    def test_a_file_a_mod_does_not_allow_is_rejected(self):
        for name in ('mods/envoy/art/hero.png', 'mods/envoy/tools/make.py', 'mods/envoy/NATIVE-TEST-PLAN.md',
                     'mods/envoy_drives/tools/make_drives.py', 'mods/vanilla-striker/files/PlMr.dat',
                     'mods/envoy/scripts/extra.wgsl'):
            with self.subTest(name=name):
                try:
                    self.put(name, b'x'*64)
                    self.manifest()
                    code, log = self.check()
                    self.assertNotEqual(code, 0, log)
                finally:
                    self.cleanup(name)

    def test_disc_content_under_an_allowed_mod_name_is_rejected(self):
        # Names the allow list accepts (the new Envoy/Geno asset types), bytes that are disc data:
        # the content sniffs in check_release.ps1 must still fire whatever the file is called.
        gc = bytearray(0x440); gc[0:6] = b'GALE01'; gc[0x1C:0x20] = bytes.fromhex('C2339F3D')   # GameCube disc header
        wii = bytearray(0x440); wii[0x18:0x1C] = bytes.fromhex('5D1C9EA3')                       # Wii disc header
        hsd = struct.pack('>I', 64) + b'\0'*60                                                    # HSD archive: first word = its own size
        gci = b'GALE01' + b'\0'*60                                                                # memory-card save / game ID
        rvz = b'RVZ\x01' + b'\0'*60                                                               # compressed disc image
        cases = (('mods/envoy_drives/models/drive_red.gxmesh', bytes(gc), 'contains a GameCube disc header', True),
                 ('mods/envoy_drives/models/drive_atlas.gxtex', hsd, 'looks like an HSD archive', True),
                 ('mods/envoy/shaders/crit.wgsl', gci, 'starts with a game ID', True),
                 ('mods/geno-lab/ui/lab_tex.gxtex', bytes(wii), 'contains a Wii disc header', False),
                 ('mods/vanilla-striker/moves/jab.words', rvz, 'is a compressed disc image', True))
        for name, data, text, existed in cases:
            with self.subTest(name=name):
                original = (self.stage/name).read_bytes() if existed else None
                try:
                    self.put(name, data)
                    self.expect_fail(text)
                finally:
                    if existed:
                        self.put(name, original)
                    else:
                        self.cleanup(name)
        self.manifest()
        code, log = self.check()
        self.assertEqual(code, 0, log)

    def test_a_missing_envoy_shader_or_drive_model_fails_the_guard(self):
        # the allow list lets these ship; the 'required' list is what fails a package that lacks one
        for mid, need in [(m, n) for m in ('envoy', 'envoy_drives') for n in RULES[m]['required']]:
            with self.subTest(file=mid+'/'+need):
                name = 'mods/'+mid+'/'+need
                data = (self.stage/name).read_bytes()
                try:
                    (self.stage/name).unlink()
                    self.expect_fail('missing required file: '+name)
                finally:
                    self.put(name, data)
        self.manifest()
        self.assertEqual(self.check()[0], 0, self.check()[1])

    def test_the_required_lists_cover_the_shaders_and_every_drive_model(self):
        self.assertEqual({n for n in RULES['envoy']['required'] if n.endswith('.wgsl')},
                         {'shaders/'+x+'.wgsl' for x in ('crit', 'drive-pulse', 'gene-sheen', 'modifiers_chain', 'modifiers_surface')})
        drives = RULES['envoy_drives']['required']
        for colour in ('red', 'green', 'yellow', 'blue', 'white', 'purple', 'glass', 'ring_magic', 'ring_rare', 'ring_unique'):
            self.assertIn('models/drive_'+colour+'.gxmesh', drives)
        self.assertIn('models/drive_atlas.gxtex', drives)

    def test_envoy_is_not_an_example_script(self):
        try:
            self.put('scripts/examples/envoy/scripts/main.lua')
            self.expect_fail('is a mod now')
        finally:
            self.cleanup('scripts/examples/envoy')

    def test_original_dat_passes_only_when_listed_and_original(self):
        try:
            rel = self.courier()
            # a first word equal to the file's own size is how every HSD archive looks: allowed for the listed original only
            data = (self.stage/rel).read_bytes()
            data = len(data).to_bytes(4, 'big')+data[4:]
            self.put(rel, data)
            self.put('mods/original-assets.json', json.dumps({'format': 1, 'files': [
                {'path': rel, 'sha256': hashlib.sha256(data).hexdigest()}]}).encode())
            self.manifest()
            code, log = self.check()
            self.assertEqual(code, 0, log)
        finally:
            self.cleanup('mods/vanilla-courier', 'mods/original-assets.json')

    def test_dat_not_in_the_original_list_is_disc_data(self):
        try:
            self.courier(listed=False)
            self.expect_fail('does not list is disc data')
        finally:
            self.cleanup('mods/vanilla-courier', 'mods/original-assets.json')

    def test_dat_with_wrong_hash_is_rejected(self):
        try:
            rel = self.courier()
            self.put(rel, b'\0'*4+b'PlyCourier_x'+b'tampered')
            self.expect_fail('does not match mods/original-assets.json')
        finally:
            self.cleanup('mods/vanilla-courier', 'mods/original-assets.json')

    def test_listed_dat_carrying_another_fighters_symbols_is_rejected(self):
        try:
            self.courier(symbols=b'courier_joint PlyMario5K_Share_joint')
            self.expect_fail("another fighter's symbol")
        finally:
            self.cleanup('mods/vanilla-courier', 'mods/original-assets.json')

    def test_dat_with_a_disc_name_is_rejected_even_if_listed(self):
        try:
            self.courier(name='PlMr.dat')
            self.expect_fail('disc data')
        finally:
            self.cleanup('mods/vanilla-courier', 'mods/original-assets.json')

    def test_enabled_txt_cannot_turn_on_an_off_or_unknown_mod(self):
        file = self.stage/'mods/enabled.txt'
        before = file.read_text()
        try:
            for line, text in (('vanilla-striker', 'must ship off by default'), ('metaknight', 'not a mod this release carries')):
                with self.subTest(line=line):
                    file.write_text(before+line+'\n')
                    self.expect_fail(text)
        finally:
            file.write_text(before)

    def test_default_on_mod_is_required(self):
        file = self.stage/'mods/envoy/mod.json'
        data = file.read_bytes()
        try:
            file.unlink()
            self.expect_fail('missing required file: mods/envoy/mod.json')
        finally:
            file.write_bytes(data)

    def test_personal_path_in_a_mod_script_is_rejected(self):
        file = self.stage/'mods/envoy/scripts/main.lua'
        try:
            file.write_text('-- C:\\Users\\Builder\\src\\x.lua\n')
            self.expect_fail('personal path')
        finally:
            file.write_text('x')


if __name__ == '__main__':
    unittest.main()
