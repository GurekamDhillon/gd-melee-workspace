"""Protocol agreement and reader regressions, runnable by pytest or unittest."""
import os
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / 'tools/netplay/server/gdmelee_server.py'
HELPER = ROOT / 'tools/release/netplay_protocol.ps1'


def ps_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


class NetplayProtocolTests(unittest.TestCase):
    def setUp(self):
        self.source_melee = Path(os.environ.get('GW_MELEE') or ROOT / 'melee')
        self.explicit_source = bool(os.environ.get('GW_MELEE'))
        work = tempfile.TemporaryDirectory(prefix='netplay-protocol-')
        self.addCleanup(work.cleanup)
        self.work = Path(work.name)
        self.workspace = self.work / 'workspace'
        self.server = self.workspace / 'tools/netplay/server/gdmelee_server.py'
        self.helper = self.workspace / 'tools/release/netplay_protocol.ps1'
        for source, target in ((SERVER, self.server), (HELPER, self.helper)):
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        environment = patch.dict(os.environ)
        environment.start()
        self.addCleanup(environment.stop)
        os.environ.pop('GW_MELEE', None)

    def header(self, text, melee=None):
        melee = melee or self.workspace / 'melee'
        header = melee / 'pc/platform/gw_net.h'
        header.parent.mkdir(parents=True, exist_ok=True)
        header.write_text(text, encoding='utf-8')
        return melee

    def powershell(self, command, helper=None):
        shell = shutil.which('powershell') or shutil.which('pwsh')
        if not shell:
            self.skipTest('PowerShell unavailable')
        return subprocess.run(
            [shell, '-NoProfile', '-Command',
             "$ErrorActionPreference = 'Stop'; . " + ps_quote(helper or self.helper) + '; ' + command],
            cwd=self.work, capture_output=True, text=True)

    def assert_protocol(self, result, expected):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), str(expected))

    def test_checked_in_fallback_agrees_with_game_header(self):
        header = self.source_melee / 'pc/platform/gw_net.h'
        if not header.is_file():
            if self.explicit_source:
                self.fail('GW_MELEE must contain pc/platform/gw_net.h: ' + str(header))
            self.skipTest('set GW_MELEE to check the standalone fallback against gw_net.h (required in CI)')
        # Read the authoritative value independently of the production readers.
        definitions = re.findall(
            r'^\s*#\s*define\s+GW_NET_PROTOCOL_VERSION\s+(\d+)[uU]?\b',
            header.read_text(encoding='utf-8'), re.MULTILINE)
        self.assertEqual(len(definitions), 1, str(header))
        expected = int(definitions[0])
        os.environ['GW_MELEE'] = str(self.source_melee)
        server = runpy.run_path(str(SERVER))
        self.assertIn('FALLBACK_NETPLAY_PROTOCOL', server)
        self.assertEqual(server['FALLBACK_NETPLAY_PROTOCOL'], expected,
                         'update the standalone server fallback when gw_net.h changes')
        self.assertEqual(server['NETPLAY_PROTOCOL'], expected)
        self.assert_protocol(self.powershell('Get-NetplayProtocol', HELPER), expected)

    def test_server_reads_default_header_relative_to_script(self):
        self.header('/* #define GW_NET_PROTOCOL_VERSION 99u */\n'
                    '# define GW_NET_PROTOCOL_VERSION 7u /* new handshake */\n')
        self.assertEqual(runpy.run_path(str(self.server))['NETPLAY_PROTOCOL'], 7)

    def test_powershell_reads_default_header_relative_to_script(self):
        self.header('/* #define GW_NET_PROTOCOL_VERSION 99u */\n'
                    '# define GW_NET_PROTOCOL_VERSION 7u // new handshake\n')
        self.assert_protocol(self.powershell('Get-NetplayProtocol'), 7)

    def test_environment_and_explicit_checkout_selection(self):
        self.header('#define GW_NET_PROTOCOL_VERSION 7u\n')
        alternate = self.header('#define GW_NET_PROTOCOL_VERSION 8u\n', self.work / 'alternate game')
        explicit = self.header('#define GW_NET_PROTOCOL_VERSION 9u\n', self.work / 'explicit game')
        os.environ['GW_MELEE'] = str(alternate)
        server = runpy.run_path(str(self.server))
        self.assertEqual(server['NETPLAY_PROTOCOL'], 8)
        self.assertIn('read_netplay_protocol', server)
        self.assertEqual(server['read_netplay_protocol'](explicit), 9)
        self.assert_protocol(self.powershell('Get-NetplayProtocol'), 8)
        self.assert_protocol(self.powershell('Get-NetplayProtocol -MeleeDir ' + ps_quote(explicit)), 9)

    def test_standalone_server_and_helper_use_one_fallback(self):
        server = runpy.run_path(str(self.server))
        self.assertIn('FALLBACK_NETPLAY_PROTOCOL', server)
        self.assertEqual(server['NETPLAY_PROTOCOL'], server['FALLBACK_NETPLAY_PROTOCOL'])
        self.assert_protocol(self.powershell('Get-NetplayProtocol'), server['FALLBACK_NETPLAY_PROTOCOL'])
        result = subprocess.run([sys.executable, str(self.server), '--help'],
                                cwd=self.work, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('--bind', result.stdout)

    def test_malformed_present_header_is_rejected(self):
        for text in ('/* #define GW_NET_PROTOCOL_VERSION 7u */\n',
                     '#define GW_NET_PROTOCOL_VERSION seven\n',
                     '#define GW_NET_PROTOCOL_VERSION 7u\n#define GW_NET_PROTOCOL_VERSION 7u\n'):
            with self.subTest(header=text):
                self.header(text)
                with self.assertRaisesRegex(ValueError, 'GW_NET_PROTOCOL_VERSION'):
                    runpy.run_path(str(self.server))
                result = self.powershell('Get-NetplayProtocol')
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('GW_NET_PROTOCOL_VERSION', result.stderr)

    def test_explicit_missing_header_does_not_use_fallback(self):
        os.environ['GW_MELEE'] = str(self.work / 'missing game')
        with self.assertRaises(FileNotFoundError):
            runpy.run_path(str(self.server))
        result = self.powershell('Get-NetplayProtocol')
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('gw_net.h', result.stderr)

    def test_metadata_uses_explicit_checkout_and_rejects_bad_entries(self):
        self.header('#define GW_NET_PROTOCOL_VERSION 7u\n')
        alternate = self.header('#define GW_NET_PROTOCOL_VERSION 8u\n', self.work / 'alternate game')
        selection = ' -MeleeDir ' + ps_quote(alternate)
        command = (
            'Assert-NetplaySource ' + ps_quote(alternate) + '; '
            'Assert-NetplayMetadata "fixture`nnetplay_protocol 8`n"' + selection + '; '
            'foreach ($bad in @(\'\', \'netplay_protocol 7\', \'netplay_protocol 9\', '
            '"netplay_protocol 8`nnetplay_protocol 8")) { '
            '$rejected = $false; try { Assert-NetplayMetadata $bad' + selection + ' } '
            'catch { $rejected = $true }; if (-not $rejected) { throw "accepted: $bad" } }; '
            'Get-NetplayProtocol' + selection)
        self.assert_protocol(self.powershell(command), 8)

    def test_linux_guard_reads_selected_header(self):
        alternate = self.header('#define GW_NET_PROTOCOL_VERSION 8u\n', self.work / 'alternate game')
        os.environ['GW_MELEE'] = str(alternate)
        guard = runpy.run_path(str(ROOT / 'tools/release/check_release_linux.py'))
        self.assertEqual(guard['netplay_protocol'](), 8)

    def test_linux_guard_explicit_checkout_overrides_missing_environment(self):
        alternate = self.header('#define GW_NET_PROTOCOL_VERSION 8u\n', self.work / 'alternate game')
        missing = str(self.work / 'missing game')
        os.environ['GW_MELEE'] = missing
        guard = runpy.run_path(str(ROOT / 'tools/release/check_release_linux.py'))
        self.assertEqual(guard['netplay_protocol'](alternate), 8)
        self.assertEqual(os.environ['GW_MELEE'], missing)


if __name__ == '__main__':
    unittest.main()
