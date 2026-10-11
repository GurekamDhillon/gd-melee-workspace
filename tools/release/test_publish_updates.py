"""Exercise the real publisher/generator with synthetic archives and no GitHub calls."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

HERE = Path(__file__).resolve().parent
SHELL = shutil.which("powershell")


@unittest.skipUnless(SHELL, "Windows PowerShell unavailable")
class PublishUpdateTests(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory(prefix="publish-updates-")
        self.addCleanup(work.cleanup)
        self.root = Path(work.name)
        self.release = self.root / "tools/release"
        self.release.mkdir(parents=True)
        for name in ("publish.ps1", "generate_update_manifest.py", "netplay_protocol.ps1"):
            shutil.copyfile(HERE / name, self.release / name)
        header = self.root / "melee/pc/platform/gw_net.h"
        header.parent.mkdir(parents=True)
        header.write_text("#define GW_NET_PROTOCOL_VERSION 73u\n", encoding="utf-8")
        self.output = self.root / "output"
        self.output.mkdir()
        self.capture = self.root / "release-args.json"
        # Only the prebuilt archive/guard boundary is substituted here. The guard
        # itself has folder/zip tests, including header selection and TLS files.
        (self.release / "build_release.ps1").write_text(
            "[IO.File]::WriteAllText($env:PUBLISH_TEST_BUILT, 'built')\nexit 0\n")
        (self.release / "check_release.ps1").write_text("exit 0\n")
        self.runner = self.root / "run.ps1"
        self.runner.write_text(r"""param([switch]$Unsigned, [switch]$Dry)
$ErrorActionPreference = 'Stop'
function gh {
  if ($args[0] -eq 'auth') { $global:LASTEXITCODE = 0; return }
  if ($args[0] -eq 'release' -and $args[1] -eq 'view') { $global:LASTEXITCODE = 1; return }
  if ($args[0] -eq 'release' -and $args[1] -eq 'create') {
    [IO.File]::WriteAllText($env:PUBLISH_TEST_CAPTURE, (ConvertTo-Json -InputObject @($args)))
    $global:LASTEXITCODE = 0; return
  }
  throw "Unexpected gh arguments: $args"
}
function git {
  if ($args[2] -eq 'rev-parse') { $global:LASTEXITCODE = 0; return ('b' * 40) }
  if ($args[2] -eq 'branch') { $global:LASTEXITCODE = 0; return ' origin-ws/master' }
  throw "Unexpected git arguments: $args"
}
function python { & $env:PUBLISH_TEST_PYTHON @args; $global:LASTEXITCODE = $LASTEXITCODE }
& "$PSScriptRoot/tools/release/publish.ps1" -OutDir "$PSScriptRoot/output" -MeleeDir "$PSScriptRoot/melee" -AllowUnsignedUpdate:$Unsigned -DryRun:$Dry
""", encoding="utf-8")

    def archive(self, version, summary=True):
        # Both VERSION and archive metadata are fixtures, never the live release.
        (self.release / "VERSION").write_text(version, encoding="utf-8")
        notes = self.release / f"notes/{version}.md"
        notes.parent.mkdir(exist_ok=True)
        notes.write_text("<!-- update-summary\nen: Update.\nes: Actualización.\n-->\n" if summary
                         else "Release candidate for testing.\n", encoding="utf-8")
        name = f"GDMelee-{version}-win64"
        stage = self.output / name
        stage.mkdir()
        (stage / "version.txt").write_text(f"{version} (melee abc)\nmelee {'a' * 40}\nnetplay_protocol 73\n")
        (stage / "MANIFEST.sha256").write_text("a" * 64 + "  README.txt\n")
        archive = self.output / (name + ".zip")
        with zipfile.ZipFile(archive, "w") as z:
            for path in stage.iterdir():
                z.write(path, f"{name}/{path.name}")
        Path(str(archive) + ".sha256").write_text(hashlib.sha256(archive.read_bytes()).hexdigest())
        return archive

    def publish(self, *switches):
        self.capture.unlink(missing_ok=True)
        env = dict(os.environ, PUBLISH_TEST_CAPTURE=str(self.capture),
                   PUBLISH_TEST_BUILT=str(self.root / "built"), PUBLISH_TEST_PYTHON=sys.executable)
        return subprocess.run([SHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                               str(self.runner), *switches], cwd=self.root, env=env,
                              capture_output=True, text=True, timeout=20,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

    def test_stable_publish_attaches_generated_manifest(self):
        for version in ("0.3.0", "0.3.0.1"):
            with self.subTest(version=version):
                archive = self.archive(version)
                result = self.publish("-Unsigned")
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                args = json.loads(self.capture.read_text(encoding="utf-8"))
                manifest = self.output / "update.json"
                self.assertIn(str(manifest), args)
                self.assertIn(str(archive), args)
                self.assertNotIn("--prerelease", args)
                payload = json.loads(manifest.read_text(encoding="utf-8"))
                self.assertEqual(payload["version"], version)
                self.assertEqual(payload["netplay_protocol"], 73)
                self.assertEqual(payload["package"]["sha256"], hashlib.sha256(archive.read_bytes()).hexdigest())

    def test_rc_publish_skips_metadata_without_unsigned_opt_in(self):
        archive = self.archive("0.3.0-rc3", summary=False)
        # Reusing an output directory must never attach a previous stable asset.
        for leaf in ("update.json", "update.json.sig"):
            (self.output / leaf).write_bytes(b"previous stable asset")
        for switches in ((), ("-Unsigned",)):
            with self.subTest(switches=switches):
                result = self.publish(*switches)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                args = json.loads(self.capture.read_text(encoding="utf-8"))
                self.assertIn(str(archive), args)
                self.assertIn("--prerelease", args)
                self.assertIn("--latest=false", args)
                for leaf in ("update.json", "update.json.sig"):
                    self.assertNotIn(str(self.output / leaf), args)
                    self.assertEqual((self.output / leaf).read_bytes(), b"previous stable asset")
                self.assertIn("skip", result.stdout.lower())
                self.assertIn("stable", result.stdout.lower())

    def test_rc_dry_run_skips_manifest_with_clear_note(self):
        self.archive("0.3.0-rc3", summary=False)
        result = self.publish("-Dry")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.output / "update.json").exists())
        self.assertFalse(self.capture.exists())
        self.assertIn("--prerelease", result.stdout)
        self.assertIn("--latest=false", result.stdout)
        self.assertIn("skip", result.stdout.lower())
        self.assertIn("stable", result.stdout.lower())

    def test_stable_publish_still_requires_unsigned_opt_in(self):
        self.archive("0.3.0")
        result = self.publish()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("-AllowUnsignedUpdate", result.stderr)
        self.assertFalse((self.root / "built").exists())
        self.assertFalse(self.capture.exists())


if __name__ == "__main__":
    unittest.main()
