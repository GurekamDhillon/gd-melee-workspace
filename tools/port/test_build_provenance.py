"""Bind release inputs to exact source and artifact bytes, not mtimes."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

WRITER = Path(__file__).with_name('build_provenance.py')


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='build provenance ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.game, self.build = self.root/'game', self.root/'build'
        (self.game/'pc/platform').mkdir(parents=True)
        (self.game/'src').mkdir()
        self.build.mkdir()
        self.source = self.game/'src/game.c'
        self.source.write_text('int game = 1;\n')
        (self.game/'pc/platform/gw_net.h').write_text('#define GW_NET_PROTOCOL_VERSION 3u\n')
        for args in (['init','-q'], ['add','.'], ['-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','fixture']):
            subprocess.run(['git',*args],cwd=self.game,check=True,capture_output=True)
        for name in ('melee-pc.exe','melee-pc.map'):
            (self.build/name).write_bytes(name.encode())

    def invoke(self, *args, ok=True):
        r = subprocess.run([sys.executable,str(WRITER),'--melee',str(self.game),
                            '--build',str(self.build),*args],capture_output=True,text=True)
        if ok:
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)
        else:
            self.assertNotEqual(r.returncode,0,r.stdout+r.stderr)
        return r

    def test_round_trip_and_protocol(self):
        self.invoke()
        stamp=json.loads((self.build/'build-provenance.json').read_text())
        self.assertEqual(stamp['format'],1)
        self.assertEqual(stamp['netplay_protocol'],3)
        self.assertFalse(stamp['source_dirty'])
        self.invoke('--verify','--require-clean')

    def test_backdated_source_change_is_refused(self):
        self.invoke()
        before=self.source.stat()
        self.source.write_text('int game = 2;\n')
        os.utime(self.source,ns=(before.st_atime_ns,before.st_mtime_ns))
        self.invoke('--verify',ok=False)

    def test_untracked_source_is_part_of_snapshot(self):
        self.invoke()
        (self.game/'src/extra.inc').write_text('int extra;\n')
        self.invoke('--verify',ok=False)

    def test_tampered_binary_or_missing_map_is_refused(self):
        self.invoke()
        (self.build/'melee-pc.exe').write_bytes(b'different executable')
        self.invoke('--verify',ok=False)
        (self.build/'melee-pc.map').unlink()
        self.invoke(ok=False)

    def test_dirty_build_can_be_verified_but_not_released_as_clean(self):
        self.source.write_text('int game = 2;\n')
        self.invoke()
        self.invoke('--verify')
        self.invoke('--verify','--require-clean',ok=False)

    def test_source_mutation_during_build_prevents_stamp(self):
        token=self.invoke('--snapshot').stdout.strip()
        self.source.write_text('int game = 2;\n')
        self.invoke('--expect-source',token,ok=False)
        self.assertFalse((self.build/'build-provenance.json').exists())


if __name__ == '__main__':
    unittest.main()
