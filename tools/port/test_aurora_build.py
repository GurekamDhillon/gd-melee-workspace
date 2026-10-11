"""Aurora freshness and native response-file regression tests (no game needed)."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

import aurora_build
import generated_shims
import link_response


class AuroraBuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "game with spaces" / "extern/aurora"
        self.source.mkdir(parents=True)
        self.input = self.source / "gx.cpp"
        self.input.write_text("old renderer")
        self.output = self.root / "build" / "aurora_core.lib"
        self.stamp = self.root / "build" / ".aurora.json"

    def run_build(self, builder=None):
        def compile_fixture():
            self.output.parent.mkdir(parents=True, exist_ok=True)
            self.output.write_text(self.input.read_text())
        return aurora_build.ensure(self.source, self.stamp, [self.output],
                                   "x86 release", builder or compile_fixture)

    def test_unchanged_build_does_not_run_builder(self):
        self.assertTrue(self.run_build())
        before = self.output.stat().st_mtime_ns
        self.assertFalse(self.run_build(lambda: self.fail("warm build compiled")))
        self.assertEqual(self.output.stat().st_mtime_ns, before)

    def test_backdated_changed_source_is_rebuilt(self):
        self.run_build()
        self.input.write_text("new renderer")
        os.utime(self.input, (1, 1))
        self.assertTrue(self.run_build())
        self.assertEqual(self.output.read_text(), "new renderer")

    def test_removed_source_and_missing_output_are_rebuilt(self):
        extra = self.source / "removed.cpp"
        extra.write_text("obsolete")
        self.run_build()
        extra.unlink()
        self.assertTrue(self.run_build())
        self.output.unlink()
        self.assertTrue(self.run_build())

    def test_failed_build_does_not_bless_inputs(self):
        self.run_build()
        self.input.write_text("changed")
        def fail():
            raise RuntimeError("compiler failed")
        with self.assertRaisesRegex(RuntimeError, "compiler failed"):
            self.run_build(fail)
        self.assertTrue(self.run_build())
        self.assertEqual(self.output.read_text(), "changed")

    def test_source_change_during_build_is_refused(self):
        def race():
            self.output.parent.mkdir(parents=True)
            self.output.write_text("old renderer")
            self.input.write_text("new renderer")
        with self.assertRaisesRegex(RuntimeError, "changed during"):
            self.run_build(race)
        self.assertFalse(self.stamp.exists())

    def test_success_without_required_library_is_refused(self):
        with self.assertRaisesRegex(RuntimeError, "did not produce"):
            self.run_build(lambda: None)
        self.assertFalse(self.stamp.exists())

    def test_missing_dependency_library_triggers_rebuild(self):
        dependency = self.output.parent / "_deps/png-build/libpng16_static.lib"
        dependency.parent.mkdir(parents=True)
        template = self.root / "libs.rsp"
        template.write_text('aurora_core.lib\n_deps/png-build/libpng16_static.lib\nkernel32.lib\n')
        outputs = [p for p in aurora_build.windows_link_inputs(template, self.output.parent)
                   if isinstance(p, Path)]
        def compile_fixture():
            self.output.write_text("Aurora")
            dependency.write_text("PNG")
        aurora_build.ensure(self.source, self.stamp, outputs, "config", compile_fixture)
        dependency.unlink()
        self.assertTrue(aurora_build.ensure(self.source, self.stamp, outputs, "config", compile_fixture))
        self.assertEqual(dependency.read_text(), "PNG")

    def test_config_change_rebuilds(self):
        self.run_build()
        self.assertTrue(aurora_build.ensure(self.source, self.stamp, [self.output],
                                          "different flags", lambda: self.output.write_text("new flags")))
        self.assertEqual(self.output.read_text(), "new flags")

    @unittest.skipUnless(shutil.which("ninja"), "Ninja is required")
    def test_backdated_change_reaches_a_timestamp_based_builder(self):
        build = self.output.parent
        build.mkdir()
        copier = self.root / "copy.py"
        copier.write_text('import pathlib, sys\n'
                          'p = pathlib.Path(sys.argv[2]); p.parent.mkdir(parents=True, exist_ok=True)\n'
                          'p.write_bytes(pathlib.Path(sys.argv[1]).read_bytes())\n')
        def ninja_path(path):
            return str(path).replace("\\", "/").replace(":", "$:").replace(" ", "$ ")
        (build / "build.ninja").write_text(
            f'rule copy\n  command = "{sys.executable}" "{copier}" $in $out\n'
            f'build CMakeFiles/aurora_core.dir/gx.obj: copy {ninja_path(self.input)}\n'
            'build aurora_core.lib: copy CMakeFiles/aurora_core.dir/gx.obj\n')
        def compile_ninja():
            subprocess.run([shutil.which("ninja"), "-C", str(build)], check=True, capture_output=True)
        self.run_build(compile_ninja)
        self.input.write_text("new renderer")
        os.utime(self.input, (1, 1))
        self.run_build(compile_ninja)
        self.assertEqual(self.output.read_text(), "new renderer")

    def test_link_libraries_use_private_outputs_and_keep_system_libraries(self):
        self.output.parent.mkdir()
        (self.output.parent / "_deps/sdl3_prebuilt-src/lib").mkdir(parents=True)
        self.output.write_bytes(b"local Aurora")
        sdl = self.output.parent / "_deps/sdl3_prebuilt-src/lib/SDL3.lib"
        sdl.write_bytes(b"local SDL")
        template = self.root / "libs.rsp"
        template.write_text('aurora_core.lib\n../ax86/_deps/sdl3_prebuilt-src/lib/SDL3.lib\nkernel32.lib\n-ignore:4221\n')
        response = aurora_build.windows_link_libraries(template, self.output.parent)
        self.assertEqual(response, f'"{self.output.as_posix()}"\n"{sdl.as_posix()}"\nkernel32.lib\n-ignore:4221\n')
        self.output.unlink()
        with self.assertRaisesRegex(RuntimeError, "missing private"):
            aurora_build.windows_link_libraries(template, self.output.parent)

    def test_runtime_dlls_match_private_build_even_with_older_timestamp(self):
        build = self.root / "aurora"
        lane = self.root / "lane"
        lane.mkdir()
        sdl = build / "_deps/sdl3_prebuilt-src/bin/SDL3.dll"
        dawn = build / "_deps/dawn-build/webgpu_dawn.dll"
        for path in (sdl, dawn):
            path.parent.mkdir(parents=True)
            path.write_bytes(b"new runtime")
            os.utime(path, (1, 1))
            (lane / path.name).write_bytes(b"old runtime")
        aurora_build.stage_runtime(build, lane)
        self.assertEqual((lane / "webgpu_dawn.dll").read_bytes(), b"new runtime")
        self.assertEqual((lane / "SDL3.dll").read_bytes(), b"new runtime")


class GeneratedInputsTests(unittest.TestCase):
    def test_generated_bridge_is_preserved_and_source_consumers_are_refreshed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            platform = root / "game/pc/platform"
            platform.mkdir(parents=True)
            originals = {"gw_mex_bridge.c": b"seed", "gw_mex_bridge.h": b"header",
                         "gw_ppc.c": b'#include "gw_mex_bridge.h"\nint old;',
                         "gw_netplay.c": b'#include "gw_build_id.h"', "other.c": b"int other;"}
            for name, body in originals.items():
                (platform / name).write_bytes(body)
            output = root / "build/generated"
            generated_shims.prepare(root / "game", output)
            (output / "gw_mex_bridge.c").write_text("final link table")
            (platform / "gw_ppc.c").write_text('#include "gw_mex_bridge.h"\nint changed;')
            generated_shims.prepare(root / "game", output)
            self.assertEqual((output / "gw_mex_bridge.c").read_text(), "final link table")
            self.assertEqual((platform / "gw_mex_bridge.c").read_bytes(), b"seed")
            self.assertEqual((output / "gw_ppc.c").read_bytes(), (platform / "gw_ppc.c").read_bytes())
            self.assertFalse((output / "other.c").exists())
            before = (output / "gw_netplay.c").stat().st_mtime_ns
            generated_shims.prepare(root / "game", output)
            self.assertEqual((output / "gw_netplay.c").stat().st_mtime_ns, before)

    def test_lane_object_list_has_no_working_directory_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "_build").mkdir()
            (root / "_build/melee_link_objects.rsp").write_text('../masstest/out/game.obj\n')
            build = root / "private build"
            self.assertEqual(link_response.response_text(root, build),
                             f'"{(build / "masstest/out/game.obj").as_posix()}"\n')


@unittest.skipUnless(os.name == "nt" and shutil.which("bash"), "Git Bash regression")
class SlippiPathTests(unittest.TestCase):
    def test_msys_paths_become_native_paths_inside_response_file(self):
        with tempfile.TemporaryDirectory(prefix="slippi paths ") as tmp:
            root = Path(tmp)
            platform = root / "game/pc/platform"
            shims = root / "build/masstest/shimobj"
            platform.mkdir(parents=True)
            shims.mkdir(parents=True)
            (platform / "gw_slippi_pad.c").write_text("int pad;")
            (shims / "gw_slippi_pad.obj").write_bytes(b"fixture")
            rsp = root / "build/melee_link_objects.rsp"
            rsp.write_text('"unrelated.obj"\n')
            script = Path(__file__).with_name("slippi_build.sh").as_posix()
            env = dict(os.environ, FIXTURE_ROOT=root.as_posix(), SLIPPI_SCRIPT=script)
            subprocess.run([shutil.which("bash"), "-c", '''set -eu
GW_MELEE="$(cygpath -u "$FIXTURE_ROOT/game")"
GW_BUILD_ROOT="$(cygpath -u "$FIXTURE_ROOT/build")"
GW_SHIMOBJ="$GW_BUILD_ROOT/masstest/shimobj"
GW_LINK_OBJECTS="$GW_BUILD_ROOT/melee_link_objects.rsp"
gw_die() { echo "$*" >&2; exit 1; }
. "$SLIPPI_SCRIPT"
'''], env=env, check=True, capture_output=True)
            result = (root / "build/.slippi_link_objects.rsp").read_text()
            self.assertIn('"' + (shims / "gw_slippi_pad.obj").as_posix() + '"', result)
            self.assertIn('"unrelated.obj"', result)


if __name__ == "__main__":
    unittest.main()
