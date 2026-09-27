"""Focused regression checks for the build's stale scan and generated bridge writes."""

import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import scan_stale_tus


PORT = Path(__file__).resolve().parent
BRIDGE = PORT.parent / "mex_port" / "gen_bridge.py"


def load_bridge():
    spec = importlib.util.spec_from_file_location("gen_bridge", BRIDGE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StaleScanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.melee = root / "GD's Melee" / "melee"
        self.out = root / "objects"
        self.files = root / "files.txt"
        for directory in (self.melee / "src", self.melee / "include", self.melee / "pc" / "geno", self.out):
            directory.mkdir(parents=True)
        self.source = self.melee / "src" / "example.c"
        self.source.write_text("int example;\n")
        self.obj = self.out / "src_example.c.obj"
        self.obj.write_bytes(b"object")
        self.files.write_bytes(b"src/example.c\r\nsrc/missing.c\r\n\r\n")
        self.set_time(self.files, 10)
        self.set_time(self.source, 20)
        self.set_time(self.obj, 30)

    @staticmethod
    def set_time(path, seconds):
        os.utime(path, ns=(seconds * 1_000_000_000, seconds * 1_000_000_000))

    def scan(self):
        return scan_stale_tus.scan(self.files, self.melee, self.out)

    def test_source_and_missing_object_preserve_manifest_order_and_crlf(self):
        self.assertEqual(self.scan(), [])  # Missing source is skipped.
        self.set_time(self.source, 40)
        self.assertEqual(self.scan(), ["src/example.c"])
        self.set_time(self.source, 20)
        self.obj.unlink()
        self.assertEqual(self.scan(), ["src/example.c"])

    def test_generated_inc_and_pc_geno_header_use_strict_newer(self):
        part = self.melee / "src" / "example_extra.inc"
        part.write_text("part\n")
        self.set_time(part, 30)
        self.assertEqual(self.scan(), [])
        self.set_time(part, 31)
        self.assertEqual(self.scan(), ["src/example.c"])
        self.set_time(part, 9)
        header = self.melee / "pc" / "geno" / "api.h"
        header.write_text("header\n")
        self.set_time(header, 9)  # Older than files.txt: old scan excludes it.
        self.assertEqual(self.scan(), [])
        self.set_time(header, 31)
        self.assertEqual(self.scan(), ["src/example.c"])

    @unittest.skipUnless(shutil.which("bash"), "Git Bash unavailable")
    def test_compare_mode_runs_the_legacy_scanner(self):
        result = subprocess.run(
            [sys.executable, str(PORT / "scan_stale_tus.py"),
             "--files", str(self.files), "--melee", str(self.melee),
             "--out", str(self.out), "--compare", "--bash", shutil.which("bash")],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("match", result.stdout)


class BridgeWriteTests(unittest.TestCase):
    def test_identical_bytes_leave_mtime_unchanged_and_changes_replace(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gw_mex_bridge.h"
            path.write_text("old\n")
            os.utime(path, ns=(10_000_000_000, 10_000_000_000))
            bridge = load_bridge()
            self.assertFalse(bridge.write_if_changed(path, "old\n"))
            self.assertEqual(path.stat().st_mtime_ns, 10_000_000_000)
            self.assertTrue(bridge.write_if_changed(path, "new\n"))
            self.assertEqual(path.read_text(), "new\n")
            self.assertEqual(list(path.parent.glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
