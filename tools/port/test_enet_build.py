"""Exercise the real ENet selector, including copied objects and failed compiles."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

PORT = Path(__file__).resolve().parent
PARTS = ('callbacks', 'compress', 'host', 'list', 'packet', 'peer', 'protocol', 'win32')
BASH = 'C:/Program Files/Git/bin/bash.exe' if os.name == 'nt' else shutil.which('bash')


@unittest.skipUnless(BASH and Path(BASH).exists(), 'bash unavailable')
class EnetBuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='enet build ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.game, self.build = self.root/'game', self.root/'build'
        self.objects = self.build/'shims'
        self.external = self.game/'extern/enet'
        for directory in (self.game/'pc/platform', self.external/'include/enet', self.objects):
            directory.mkdir(parents=True)
        (self.game/'pc/platform/gw_slippi_peer.c').write_text('/* shim */')
        (self.objects/'gw_slippi_peer.obj').write_text('shim')
        self.header = self.external/'include/enet/enet.h'
        self.header.write_text('header version 1')
        for part in PARTS:
            src = self.external/(part+'.c')
            src.write_text('source version 1')
            obj = self.objects/('enet_'+part+'.obj')
            obj.write_text('old object')
            os.utime(src, (100, 100))
            os.utime(obj, (200, 200))
            Path(str(obj)+'.sha256').write_text('')
        os.utime(self.header, (100, 100))
        self.link = self.build/'objects.rsp'
        self.link.write_text('"ordinary.obj"\n')
        self.compiler = self.root/'compiler.sh'
        self.compiler.write_text('#!/bin/bash\nset -eu\n'
            'if [ "${1:-}" = --version ]; then echo fixture-compiler; exit; fi\n'
            '[ ! -f "$ENET_FAIL" ] || exit 7\n'
            'printf "compile\\n" >> "$ENET_CALLS"\n'
            'while [ "$#" -gt 0 ]; do\n'
            ' if [ "$1" = -o ]; then printf "new object" > "$2"; exit; fi\n'
            ' shift\ndone\n', encoding='utf-8', newline='\n')
        self.compiler.chmod(0o755)
        self.calls, self.fail_marker = self.root/'calls', self.root/'fail'

    def run_build(self, success=True):
        env = os.environ.copy()
        env.update(GW_MELEE=self.game.as_posix(), GW_BUILD_ROOT=self.build.as_posix(),
                   GW_SHIMOBJ=self.objects.as_posix(), GW_LINK_OBJECTS=self.link.as_posix(),
                   GW_CLANG=self.compiler.as_posix(), ENET_CALLS=self.calls.as_posix(),
                   ENET_FAIL=self.fail_marker.as_posix())
        result = subprocess.run([BASH, '-lc',
            'set -euo pipefail; gw_die() { echo "$*" >&2; exit 2; }; . "$1"',
            'test', (PORT/'slippi_build.sh').as_posix()], env=env, capture_output=True, text=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
        return result

    def count(self):
        return len(self.calls.read_text().splitlines()) if self.calls.exists() else 0

    def test_backdated_lane_rebuilds_and_warm_build_skips(self):
        self.run_build()
        self.assertEqual(self.count(), 8)
        self.run_build()
        self.assertEqual(self.count(), 8)

    def test_source_and_header_changes_ignore_timestamp(self):
        self.run_build()
        source = self.external/'peer.c'
        source.write_text('source version 2')
        os.utime(source, (100, 100))
        self.run_build()
        self.assertEqual(self.count(), 9)
        self.header.write_text('header version 2')
        os.utime(self.header, (100, 100))
        self.run_build()
        self.assertEqual(self.count(), 17)

    def test_rebuild_replaces_hardlink_without_changing_baseline(self):
        obj = self.objects/'enet_peer.obj'
        baseline = self.root/'baseline.obj'
        os.link(obj, baseline)
        self.run_build()
        self.assertEqual(obj.read_text(), 'new object')
        self.assertEqual(baseline.read_text(), 'old object')

    def test_failed_compile_preserves_previous_object_and_stamp(self):
        self.fail_marker.touch()
        result = self.run_build(success=False)
        self.assertEqual(result.returncode, 7)
        self.assertEqual((self.objects/'enet_callbacks.obj').read_text(), 'old object')
        self.assertEqual((self.objects/'enet_callbacks.obj.sha256').read_text(), '')


if __name__ == '__main__':
    unittest.main()
