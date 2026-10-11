"""Behavior tests for the publish-side generator; fixtures contain no game data."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

HERE = Path(__file__).resolve().parent


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.version = "0.3.0"  # Stable fixture, independent of the current release/RC.
        self.protocol = 6
        self.zip = self.root / f"GDMelee-{self.version}-win64.zip"
        self.output = self.root / "update.json"
        self.notes = self.root / "notes.md"
        self.notes.write_text("<!-- update-summary\nen: A small update.\nes: Una actualización pequeña.\n-->\n\n## Notes\n", encoding="utf-8")
        self.files_manifest = b"a" * 64 + b"  README.txt\n"
        self.write_zip()

    def write_zip(self, version=None, protocol=None, duplicate=False):
        name = f"GDMelee-{self.version}-win64"
        metadata = f"{version or self.version} (melee abcdef0)\nmelee {'a' * 40}\nworkspace {'b' * 40}\nbuilt 2026-10-11\nnetplay_protocol {protocol or self.protocol}\n"
        with zipfile.ZipFile(self.zip, "w") as z:
            z.writestr(f"{name}/version.txt", metadata)
            z.writestr(f"{name}/MANIFEST.sha256", self.files_manifest)
            z.writestr(f"{name}/README.txt", "synthetic package")
            if duplicate:
                z.writestr("other/version.txt", metadata)

    def run_generator(self, *extra, unsigned=True):
        args = [sys.executable, str(HERE / "generate_update_manifest.py"), "--zip", str(self.zip),
                "--version", self.version, "--protocol", str(self.protocol), "--notes", str(self.notes),
                "--released", "2026-10-11", "--output", str(self.output)]
        if unsigned:
            args.append("--allow-unsigned")
        return subprocess.run(args + list(extra), capture_output=True, text=True, encoding="utf-8")

    def test_generates_exact_archive_facts_and_bilingual_notes(self):
        result = self.run_generator()
        self.assertEqual(result.returncode, 0, result.stderr)
        raw = self.output.read_bytes()
        m = json.loads(raw)
        self.assertEqual(m["schema"], 1)
        self.assertEqual(m["channel"], "stable")
        self.assertEqual(m["version"], self.version)
        self.assertEqual(m["netplay_protocol"], 6)
        self.assertEqual(m["notes_short"], {"en": "A small update.", "es": "Una actualización pequeña."})
        self.assertEqual(m["package"]["size"], self.zip.stat().st_size)
        self.assertEqual(m["package"]["sha256"], hashlib.sha256(self.zip.read_bytes()).hexdigest())
        self.assertEqual(m["files_manifest_sha256"], hashlib.sha256(self.files_manifest).hexdigest())
        self.assertEqual(m["notes_url"], f"https://github.com/GurekamDhillon/gd-melee-workspace/releases/tag/v{self.version}")
        self.assertEqual(m["package"]["url"], f"https://github.com/GurekamDhillon/gd-melee-workspace/releases/download/v{self.version}/{self.zip.name}")
        self.assertFalse(self.output.with_suffix(".json.sig").exists())
        self.assertIn("UNSIGNED", result.stdout)
        self.assertEqual(self.run_generator().returncode, 0)
        self.assertEqual(self.output.read_bytes(), raw)

    def test_without_unsigned_flag_refuses_before_writing(self):
        result = self.run_generator(unsigned=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("signing", result.stderr.lower())
        self.assertFalse(self.output.exists())

    def test_archive_version_and_protocol_cannot_be_relabelled(self):
        for version, protocol in [("9.9.9", 6), (self.version, 5)]:
            with self.subTest(version=version, protocol=protocol):
                self.write_zip(version=version, protocol=protocol)
                self.assertNotEqual(self.run_generator().returncode, 0)
                self.assertFalse(self.output.exists())

    def test_missing_spanish_summary_is_rejected(self):
        self.notes.write_text("<!-- update-summary\nen: English only.\n-->\n", encoding="utf-8")
        self.assertNotEqual(self.run_generator().returncode, 0)

    def test_ambiguous_metadata_and_prereleases_are_rejected(self):
        self.write_zip(duplicate=True)
        self.assertNotEqual(self.run_generator().returncode, 0)
        self.write_zip()
        self.assertNotEqual(self.run_generator("--version", "0.3.0-beta").returncode, 0)
        self.assertNotEqual(self.run_generator("--released", "2026-02-30").returncode, 0)
        self.assertNotEqual(self.run_generator("--repo", "../escape").returncode, 0)

    def test_oversized_summary_and_empty_package_are_rejected(self):
        self.notes.write_text("<!-- update-summary\nen: " + "a" * 2049 + "\nes: Hola\n-->\n")
        self.assertNotEqual(self.run_generator().returncode, 0)
        self.zip.write_bytes(b"")
        self.assertNotEqual(self.run_generator().returncode, 0)


if __name__ == "__main__":
    unittest.main()
