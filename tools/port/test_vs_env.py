"""Behavioral discovery checks; fixture files stay under this worktree's .omo."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).absolute().parents[2]


@unittest.skipUnless(os.name == 'nt', 'cmd/Visual Studio discovery is Windows-only')
class VsEnvTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp = ROOT / '.omo' / 'tmp'
        tmp.mkdir(parents=True, exist_ok=True)
        cls.fixture = tempfile.TemporaryDirectory(dir=tmp)
        cls.addClassCleanup(cls.fixture.cleanup)
        source = Path(cls.fixture.name) / 'vswhere.cs'
        cls.exe = source.with_suffix('.exe')
        source.write_text('''using System;
class Program {
    static int Main(string[] args) {
        if (String.Join(" ", args) != "-latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath") return 2;
        if (Environment.GetEnvironmentVariable("VS_FIXTURE_FAIL") == "1") {
            Console.Error.WriteLine("fixture vswhere failure"); return 3;
        }
        Console.WriteLine(Environment.GetEnvironmentVariable("VS_FIXTURE_INSTALL")); return 0;
    }
}
''')
        compiler = Path(os.environ['SystemRoot']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
        subprocess.run([str(compiler), '/nologo', '/out:' + str(cls.exe), str(source)],
                       check=True, capture_output=True, text=True)

    def setUp(self):
        tmp = ROOT / '.omo' / 'tmp'
        tmp.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=tmp)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pf = self.root / 'Program Files'
        self.pfx = self.root / 'Program Files (x86)'
        self.install = self.root / 'custom VS (chosen)'
        self.vcvars(self.install, 'discovered')
        self.vcvars(self.pf / 'Microsoft Visual Studio/2022/Community', 'fallback')
        self.env = dict({k.upper(): v for k, v in os.environ.items()}, GW_VCVARSALL='', GW_VSDIR='',
                        NoDefaultCurrentDirectoryInExePath='1',
                        VS_FIXTURE_INSTALL=str(self.install), VS_FIXTURE_FAIL='')
        self.env.update({'PROGRAMFILES': str(self.pf), 'PROGRAMFILES(X86)': str(self.pfx)})
        self.env['PATH'] = str(Path(os.environ['SystemRoot']) / 'System32')

    def vcvars(self, install, marker):
        file = install / 'VC/Auxiliary/Build/vcvarsall.bat'
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text('@echo off\nset "VS_FIXTURE=' + marker + '"\nexit /b 0\n')
        return file

    def vswhere(self, pf, fails=False):
        installer = pf / 'Microsoft Visual Studio/Installer'
        installer.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.exe, installer / 'vswhere.exe')
        self.env['VS_FIXTURE_FAIL'] = '1' if fails else ''

    def run_batch(self):
        driver = self.root / 'driver.cmd'
        driver.write_text('@echo off\nset "ProgramFiles=' + str(self.pf) +
                          '"\nset "ProgramFiles(x86)=' + str(self.pfx) +
                          '"\ncall "' + str(ROOT / 'tools/port/vs_env.bat') +
                          '" x64\nif errorlevel 1 exit /b 1\necho selected=%VS_FIXTURE%\n')
        return subprocess.run([os.environ['ComSpec'], '/d', '/c', str(driver)],
                              env=self.env, capture_output=True, text=True)

    def test_missing_vswhere_uses_fallback_without_noise(self):
        result = self.run_batch()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('selected=fallback', result.stdout)
        self.assertEqual(result.stderr, '')

    def test_standard_vswhere_is_found_without_current_directory_search(self):
        self.vswhere(self.pfx)
        result = self.run_batch()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('selected=discovered', result.stdout)
        self.assertEqual(result.stderr, '')

    def test_program_files_lookup_remains_supported(self):
        self.vswhere(self.pf)
        result = self.run_batch()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('selected=discovered', result.stdout)
        self.assertEqual(result.stderr, '')

    def test_failed_vswhere_falls_back_without_noise(self):
        self.vswhere(self.pfx, fails=True)
        result = self.run_batch()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('selected=fallback', result.stdout)
        self.assertEqual(result.stderr, '')

    def test_explicit_vcvars_override_does_not_probe(self):
        self.env['GW_VCVARSALL'] = str(self.install / 'VC/Auxiliary/Build/vcvarsall.bat')
        result = self.run_batch()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('selected=discovered', result.stdout)
        self.assertEqual(result.stderr, '')


if __name__ == '__main__':
    unittest.main()
