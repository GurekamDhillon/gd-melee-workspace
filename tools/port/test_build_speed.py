"""Focused regression checks for the build's stale scan and generated bridge writes."""

import importlib.util
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from contextlib import redirect_stderr

import scan_stale_tus
import build_objects


PORT = Path(__file__).resolve().parent
ROOT = PORT.parent.parent
BRIDGE = PORT.parent / "mex_port" / "gen_bridge.py"


def load_bridge():
    spec = importlib.util.spec_from_file_location("gen_bridge", BRIDGE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WindowsShimSelectionTests(unittest.TestCase):
    def test_linux_only_sources_are_not_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            melee = Path(tmp)
            platform = melee / "pc/platform"
            platform.mkdir(parents=True)
            for name in ("main.c", "gw_fx_render.cpp", "gw_compat_linux.c"):
                (platform / name).write_text("/* source */")
            self.assertEqual(
                [p.name for p in build_objects.shim_sources(melee)],
                ["gw_fx_render.cpp", "main.c"],
            )


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
             "--out", str(self.out), "--compare", "--bash", scan_stale_tus.default_bash()],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("match", result.stdout)

    def test_compare_reports_a_tree_changed_during_the_shell_scan(self):
        before = self.scan()
        def shell_scan(*args, **kwargs):
            self.set_time(self.source, 40)
            return subprocess.CompletedProcess(args, 0, b"src/example.c\n", b"")
        stderr = io.StringIO()
        with mock.patch.object(scan_stale_tus.subprocess, "run", side_effect=shell_scan), redirect_stderr(stderr):
            self.assertFalse(scan_stale_tus.compare(self.files, self.melee, self.out, before, "bash"))
        self.assertIn("tree changed", stderr.getvalue())

    def test_dependency_hash_ignores_timestamps_and_tracks_only_includes(self):
        included = self.melee / "include" / "used header.h"
        unrelated = self.melee / "include" / "other.h"
        included.write_text("#define VALUE 1\n")
        unrelated.write_text("old\n")
        depfile = self.obj.with_suffix(self.obj.suffix + ".d")
        depfile.write_text("object: src/example.c include/used\\ header.h \\\n include/used\\ header.h\n")
        config = b"flags and tools"
        key = self.obj.with_suffix(self.obj.suffix + ".sha256")
        key.write_text(scan_stale_tus.object_key(depfile, self.melee, config) + "\n")
        self.set_time(self.source, 100)
        self.set_time(included, 100)
        self.assertEqual(scan_stale_tus.scan_content(self.files, self.melee, self.out, config), [])
        unrelated.write_text("changed\n")
        self.assertEqual(scan_stale_tus.scan_content(self.files, self.melee, self.out, config), [])
        included.write_text("#define VALUE 2\n")
        self.assertEqual(scan_stale_tus.scan_content(self.files, self.melee, self.out, config), ["src/example.c"])
        included.write_text("#define VALUE 1\n")
        self.assertEqual(scan_stale_tus.scan_content(self.files, self.melee, self.out, config), [])
        self.assertEqual(scan_stale_tus.scan_content(self.files, self.melee, self.out, b"new flag"), ["src/example.c"])

    def test_missing_dependency_record_rebuilds_even_when_source_is_older(self):
        self.assertEqual(scan_stale_tus.scan_content(self.files, self.melee, self.out, b"config"), ["src/example.c"])

    def test_shim_without_dependency_record_rebuilds_when_source_is_older(self):
        platform = self.melee / "pc/platform"
        platform.mkdir()
        source = platform / "example.c"
        source.write_text("int example;\n")
        self.set_time(source, 20)
        obj = self.out / "example.obj"
        obj.write_bytes(b"legacy object")
        self.set_time(obj, 30)
        self.assertEqual(build_objects.scan_shims(self.melee, self.out, ROOT), ["example.c"])

    def test_missing_included_file_is_stale(self):
        depfile = self.obj.with_suffix(self.obj.suffix + ".d")
        depfile.write_text("object: src/example.c include/gone.h\n")
        self.obj.with_suffix(self.obj.suffix + ".sha256").write_text("old\n")
        self.assertEqual(scan_stale_tus.scan_content(self.files, self.melee, self.out, b"config"), ["src/example.c"])

    def test_partial_dependency_record_is_rebuilt(self):
        depfile = self.obj.with_suffix(self.obj.suffix + ".d")
        depfile.write_text("object: src/example.c\n")
        self.assertEqual(scan_stale_tus.scan_content(self.files, self.melee, self.out, b"config"), ["src/example.c"])

    def test_same_dependency_contents_have_same_key_in_another_lane(self):
        depfile = self.obj.with_suffix(self.obj.suffix + ".d")
        depfile.write_text("object: src/example.c include/api.h\n")
        header = self.melee / "include/api.h"
        header.write_text("same bytes\n")
        first = scan_stale_tus.object_key(depfile, self.melee, b"config", self.source)
        other = Path(self.tmp.name) / "other lane" / "melee"
        (other / "src").mkdir(parents=True)
        (other / "include").mkdir()
        shutil.copyfile(self.source, other / "src/example.c")
        shutil.copyfile(header, other / "include/api.h")
        self.assertEqual(scan_stale_tus.object_key(depfile, other, b"config", other / "src/example.c"), first)
        other_out = Path(self.tmp.name) / "other objects"
        other_out.mkdir()
        other_obj = other_out / self.obj.name
        shutil.copyfile(self.obj, other_obj)
        shutil.copyfile(depfile, Path(str(other_obj) + ".d"))
        Path(str(other_obj) + ".sha256").write_text(first + "\n")
        self.assertEqual(scan_stale_tus.scan_content(self.files, other, other_out, b"config"), [])
        (other / "src/example.c").write_text("different bytes\n")
        self.set_time(other / "src/example.c", 10)  # Backdated checkout must still rebuild.
        self.assertEqual(scan_stale_tus.scan_content(self.files, other, other_out, b"config"), ["src/example.c"])


class CachedScanTests(unittest.TestCase):
    setUp = StaleScanTests.setUp
    set_time = staticmethod(StaleScanTests.set_time)
    def prepare_record(self):
        depfile = Path(str(self.obj) + ".d")
        depfile.write_text("object: src/example.c include/shared.h\n")
        self.header = self.melee / "include/shared.h"
        self.header.write_bytes(b"header A")
        build_objects.record(self.obj, self.source, self.melee, b"config")

    def test_warm_scan_reads_each_input_once(self):
        self.prepare_record()
        self.assertEqual(scan_stale_tus.scan_content(self.files, self.melee, self.out, b"config"), [])
        original_open = Path.open
        reads = []
        def tracked_open(path, *args, **kwargs):
            if path in (self.source, self.header, Path(str(self.obj) + ".d"), Path(str(self.obj) + ".sha256")):
                reads.append(path)
            return original_open(path, *args, **kwargs)
        with mock.patch.object(Path, "open", tracked_open):
            self.assertEqual(scan_stale_tus.scan_content(self.files, self.melee, self.out, b"config"), [])
        self.assertCountEqual(reads, [self.source, self.header, Path(str(self.obj) + ".d"), Path(str(self.obj) + ".sha256")])

    def test_same_size_edit_with_restored_mtime_invalidates_object(self):
        self.prepare_record()
        self.set_time(self.header, 80)
        self.assertEqual(scan_stale_tus.scan_content(self.files, self.melee, self.out, b"config"), [])
        self.header.write_bytes(b"header B")
        self.set_time(self.header, 80)
        self.assertEqual(scan_stale_tus.scan_content(self.files, self.melee, self.out, b"config"), ["src/example.c"])

    def test_shared_header_is_read_once_and_stat_changes_invalidate_hash(self):
        self.prepare_record()
        second = self.melee / "src/second.c"
        second.write_bytes(b"second")
        obj = self.out / "src_second.c.obj"
        obj.write_bytes(b"second object")
        Path(str(obj) + ".d").write_text("object: src/second.c include/shared.h\n")
        build_objects.record(obj, second, self.melee, b"config")
        self.files.write_text("src/example.c\nsrc/second.c\n")
        scan_stale_tus.scan_content(self.files, self.melee, self.out, b"config")
        original_open = Path.open
        for content, stamp in ((b"header B", 80), (b"longer header", 80), (b"header A", 5)):
            self.header.write_bytes(content)
            self.set_time(self.header, stamp)
            reads = []
            def tracked_open(path, *args, **kwargs):
                if path == self.header:
                    reads.append(path)
                return original_open(path, *args, **kwargs)
            with mock.patch.object(Path, "open", tracked_open):
                actual = scan_stale_tus.scan_content(self.files, self.melee, self.out, b"config")
            self.assertEqual(actual, [] if content == b"header A" else ["src/example.c", "src/second.c"])
            self.assertEqual(len(reads), 1)

    def test_revert_after_successful_compile_restores_recorded_object(self):
        self.prepare_record()
        original = self.source.read_bytes()
        build_objects.preserve_object(self.obj)
        self.source.write_bytes(b"version B")
        self.obj.write_bytes(b"object B")
        Path(str(self.obj) + ".d").write_text("object: src/example.c\n")
        build_objects.record(self.obj, self.source, self.melee, b"config")
        self.assertEqual(scan_stale_tus.scan_content(self.files, self.melee, self.out, b"config"), [])
        self.source.write_bytes(original)
        self.set_time(self.source, 90)
        self.header.write_bytes(b"header B")
        self.assertEqual(scan_stale_tus.scan_content(self.files, self.melee, self.out, b"config"), ["src/example.c"])
        self.header.write_bytes(b"header A")
        self.assertEqual(scan_stale_tus.scan_content(self.files, self.melee, self.out, b"other flags"), ["src/example.c"])
        self.assertEqual(scan_stale_tus.scan_content(self.files, self.melee, self.out, b"config"), [])
        self.assertEqual(self.obj.read_bytes(), b"object")
        self.assertEqual(scan_stale_tus.scan_content(self.files, self.melee, self.out, b"config"), [])

    def test_replaced_depfile_and_missing_header_are_not_hidden_by_cache(self):
        self.prepare_record()
        scan_stale_tus.scan_content(self.files, self.melee, self.out, b"config")
        depfile = Path(str(self.obj) + ".d")
        depfile.write_text("object: src/example.c include/another.h\n")
        self.assertEqual(scan_stale_tus.scan_content(self.files, self.melee, self.out, b"config"), ["src/example.c"])
        self.prepare_record()
        scan_stale_tus.scan_content(self.files, self.melee, self.out, b"config")
        self.header.unlink()
        self.assertEqual(scan_stale_tus.scan_content(self.files, self.melee, self.out, b"config"), ["src/example.c"])

    def test_invalid_cache_is_recreated_without_invalidating_objects(self):
        self.prepare_record()
        (self.out / ".content-cache.json").write_text("interrupted JSON")
        self.assertEqual(scan_stale_tus.scan_content(self.files, self.melee, self.out, b"config"), [])

    def test_tool_bytes_are_rechecked_between_scans_even_with_same_stat(self):
        tool = self.out / "clang.exe"
        tool.write_bytes(b"compiler A")
        self.set_time(tool, 3)
        cache_path = self.out / "tools.json"
        cache = scan_stale_tus.FileCache(cache_path)
        with mock.patch.dict(os.environ, {"GW_CLANG": str(tool)}):
            old = build_objects.config("shim", ROOT, self.source, cache)
            cache.save()
            original_open = Path.open
            reads = []
            def tracked_open(path, *args, **kwargs):
                if path == tool:
                    reads.append(path)
                return original_open(path, *args, **kwargs)
            with mock.patch.object(Path, "open", tracked_open):
                self.assertEqual(build_objects.config("shim", ROOT, self.source, scan_stale_tus.FileCache(cache_path)), old)
            self.assertEqual(reads, [tool])
            tool.write_bytes(b"compiler B")
            self.set_time(tool, 3)
            self.assertNotEqual(build_objects.config("shim", ROOT, self.source, scan_stale_tus.FileCache(cache_path)), old)


class JobTests(unittest.TestCase):
    def test_invalid_job_count_is_rejected(self):
        for value in ("0", "-1", "many"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                build_objects.job_count(value)

    def test_failed_job_stops_queued_work(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "queued"
            jobs = [
                ("fails", [sys.executable, "-c", "import sys; sys.exit(7)"]),
                ("queued", [sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).touch()"]),
            ]
            with self.assertRaises(RuntimeError):
                build_objects.run_jobs(jobs, workers=1)
            self.assertFalse(marker.exists())

    def test_two_jobs_can_make_progress_together(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / name for name in ("first", "second")]
            jobs = []
            for own, other in ((paths[0], paths[1]), (paths[1], paths[0])):
                script = ("from pathlib import Path\nimport time, sys\n"
                          f"Path({str(own)!r}).touch()\n"
                          "deadline = time.monotonic() + 3\n"
                          f"while not Path({str(other)!r}).exists() and time.monotonic() < deadline:\n"
                          "    time.sleep(0.01)\n"
                          f"sys.exit(0 if Path({str(other)!r}).exists() else 1)\n")
                jobs.append((own.name, [sys.executable, "-c", script]))
            build_objects.run_jobs(jobs, workers=2)


class ShimHashTests(unittest.TestCase):
    def test_header_change_selects_only_shims_that_include_it_and_flags_select_all(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            melee = base / "melee"
            platform = melee / "pc/platform"
            out = base / "shimobj"
            platform.mkdir(parents=True)
            out.mkdir()
            clang = base / "clang.exe"
            clang.write_bytes(b"compiler")
            old_clang = os.environ.get("GW_CLANG")
            old_sdl = os.environ.get("GW_SDL_INCLUDE")
            os.environ["GW_CLANG"] = str(clang)
            os.environ["GW_SDL_INCLUDE"] = "old flags"
            try:
                header = platform / "narrow.h"
                header.write_text("old\n")
                for name in ("a.c", "b.c"):
                    source = platform / name
                    source.write_text(f"int {name[0]};\n")
                    obj = out / (source.stem + ".obj")
                    obj.write_bytes(b"object")
                    depfile = Path(str(obj) + ".d")
                    includes = " pc/platform/narrow.h" if name == "a.c" else ""
                    depfile.write_text(f"object: pc/platform/{name}{includes}\n")
                    build_objects.record(obj, source, melee, build_objects.config("shim", ROOT, source))
                self.assertEqual(build_objects.scan_shims(melee, out, ROOT), [])
                header.write_text("new\n")
                self.assertEqual(build_objects.scan_shims(melee, out, ROOT), ["a.c"])
                header.write_text("old\n")
                os.environ["GW_SDL_INCLUDE"] = "new flags"
                self.assertEqual(build_objects.scan_shims(melee, out, ROOT), ["a.c", "b.c"])
                os.environ["GW_SDL_INCLUDE"] = "old flags"
                clang.write_bytes(b"changed compiler")
                self.assertEqual(build_objects.scan_shims(melee, out, ROOT), ["a.c", "b.c"])
            finally:
                if old_clang is None:
                    os.environ.pop("GW_CLANG", None)
                else:
                    os.environ["GW_CLANG"] = old_clang
                if old_sdl is None:
                    os.environ.pop("GW_SDL_INCLUDE", None)
                else:
                    os.environ["GW_SDL_INCLUDE"] = old_sdl


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

    def test_generated_bridge_is_always_written_with_lf(self):
        # melee/.gitattributes is eol=lf: a CRLF write made a checkout without autocrlf look dirty to build_provenance.py
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gw_mex_bridge.c"
            bridge = load_bridge()
            self.assertTrue(bridge.write_if_changed(path, "a\nb\n"))
            self.assertEqual(path.read_bytes(), b"a\nb\n")
            path.write_bytes(b"a\r\nb\r\n")  # an autocrlf checkout of the same text is "unchanged"
            self.assertFalse(bridge.write_if_changed(path, "a\nb\n"))
            self.assertEqual(path.read_bytes(), b"a\r\nb\r\n")


if __name__ == "__main__":
    unittest.main()
