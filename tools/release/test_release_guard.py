"""Exercise the release guard against complete and deliberately damaged bundles."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import warnings
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'_build/audit-20261003/further-release'


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
                 'launcher/licenses/SourceSans3-OFL-1.1.txt']
        for name in names:
            file = cls.stage/name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b'synthetic release fixture\n')
        for name in subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only', 'HEAD', '--', '_build/ui'], text=True).splitlines():
            file = cls.stage/name.removeprefix('_build/')
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(subprocess.check_output(['git', '-C', str(ROOT), 'show', 'HEAD:'+name]))
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
                     'launcher/bin/vcruntime140_1.dll', 'build-provenance.json'):
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


if __name__ == '__main__':
    unittest.main()
