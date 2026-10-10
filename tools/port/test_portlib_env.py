"""Wrapper env precedence tests source portlib only; no engine or build runs."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from tools.geno.play import PlayError, _bash


class PortlibEnvironmentTests(unittest.TestCase):
    def setUp(self):
        try:
            bash = _bash(dict(os.environ))
        except PlayError as exc:
            self.skipTest(str(exc))
        if not Path(bash).is_file() and not shutil.which(bash):
            self.skipTest("Bash is required to check the existing shell wrapper")
        self.bash = bash
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.portlib = Path(__file__).resolve().parent / "portlib.sh"
        (self.root / ".env").write_text(
            'GW_BUILD_ROOT="lane-from-env"\nMELEE_WINDOW_HIDE=1\nMELEE_LAB_BATCH=1\n',
            encoding="utf-8")

    def read_environment(self, resolved):
        env = dict(os.environ, GW_ROOT=self.root.as_posix(),
                   GW_BUILD_ROOT="lane-selected-by-play", GW_MELEE=self.root.as_posix(),
                   GW_DAWN_INCLUDE="unused", MELEE_WINDOW_HIDE="0", MELEE_LAB_BATCH="0",
                   GW_PORTLIB_TEST_PATH=self.portlib.as_posix())
        env.pop("GW_ENV_RESOLVED", None)
        if resolved:
            env["GW_ENV_RESOLVED"] = "1"
        result = subprocess.run(
            [self.bash, "--noprofile", "--norc", "-c",
             '. "$GW_PORTLIB_TEST_PATH"; printf "%s\\n" "$GW_BUILD_ROOT" "$MELEE_WINDOW_HIDE" "$MELEE_LAB_BATCH"'],
            env=env, capture_output=True, text=True, check=True, timeout=10)
        return result.stdout.strip().splitlines()

    def test_resolved_play_settings_survive_the_wrapper(self):
        self.assertEqual(self.read_environment(True), ["lane-selected-by-play", "0", "0"])

    def test_existing_callers_still_load_machine_env(self):
        self.assertEqual(self.read_environment(False), ["lane-from-env", "1", "1"])

    def test_configured_python_with_spaces_is_used_by_wrapper_helpers(self):
        configured = self.root / "configured Python.sh"
        configured.write_text('#!/bin/bash\necho "configured interpreter"; printf "%s\\n" "$@"\n',
                              encoding="utf-8")
        configured.chmod(0o755)
        env = dict(os.environ, GW_ROOT=self.root.as_posix(), GW_MELEE=self.root.as_posix(),
                   GW_DAWN_INCLUDE="unused", GW_ENV_RESOLVED="1",
                   GW_PYTHON=configured.as_posix(), GW_PORTLIB_TEST_PATH=self.portlib.as_posix())
        result = subprocess.run(
            [self.bash, "--noprofile", "--norc", "-c",
             '. "$GW_PORTLIB_TEST_PATH"; gw_python --fixture "argument with spaces"'],
            env=env, capture_output=True, text=True, check=True, timeout=10)
        self.assertEqual(result.stdout.strip().splitlines(),
                         ["configured interpreter", "--fixture", "argument with spaces"])


if __name__ == "__main__":
    unittest.main()
