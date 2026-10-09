"""Synthetic FST/project integration tests: no game or disc-derived bytes."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

TOOL = Path(__file__).with_name("make_mod_from_disc.py")


def iso(path, files):
    names = bytearray(b"\0")
    entries = [struct.pack(">III", 0x1000000, 0, len(files)+1)]
    blob = bytearray(0x2000)
    pos = 0x1000
    for name, data in files.items():
        entries.append(struct.pack(">III", len(names), pos, len(data)))
        names.extend(name.encode()+b"\0")
        blob[pos:pos+len(data)] = data
        pos += len(data)
    fst = b"".join(entries)+names
    blob[0x800:0x800+len(fst)] = fst
    struct.pack_into(">III", blob, 0x420, 0x600, 0x800, len(fst))
    path.write_bytes(blob)


class Packs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.base = self.root/"base.iso"
        iso(self.base, {"PlCo.dat": b"old", "Same.dat": b"same"})
        self.project = self.root/"project"
        self.files = self.project/"files"
        self.files.mkdir(parents=True)
        (self.files/"plco.DAT").write_bytes(b"new")
        (self.files/"same.dat").write_bytes(b"same")
        (self.files/"MxDt.dat").write_bytes(b"mex")
        (self.files/"audio").mkdir()
        (self.files/"audio"/"new.ssm").write_bytes(b"sound")
        (self.project/"project.mexproj").write_text(json.dumps({"build":{"name":"Synthetic Project"}}))
        for kind in ("fighters", "stages"):
            d = self.project/"data"/kind
            d.mkdir(parents=True)
            (d/"one.json").write_text('{"name":"Synthetic"}')
        (self.project/"sys").mkdir()
        (self.project/"sys"/"main.dol").write_bytes(b"changed dol")
        self.out = self.root/"packs"

    def run_tool(self, mod=None, *flags):
        return subprocess.run([sys.executable, str(TOOL), "--vanilla", str(self.base),
            "--mod", str(mod or self.project), "--name", "test", "--out", str(self.out), *flags],
            capture_output=True, text=True)

    def test_project_delta_metadata_and_bookkeeping(self):
        r = self.run_tool()
        self.assertEqual(r.returncode, 0, r.stderr)
        m = json.loads((self.out/"test.gdm_pack.json").read_text())
        self.assertEqual((m["new"], m["modified"]), (2, 1))
        self.assertEqual(set(m["files"]), {"MxDt.dat", "plco.DAT", "audio/new.ssm"})
        for name, entry in m["files"].items():
            data = (self.out/"test"/name).read_bytes()
            self.assertEqual(entry, {"size":len(data), "sha256":hashlib.sha256(data).hexdigest()})
        meta = json.loads((self.out/"test"/"mod.json").read_text())
        self.assertEqual(meta["source"], "nucleus")
        self.assertEqual(meta["name"], "Synthetic Project")
        self.assertIn("https://ssbmnucleus.net", meta["description"])
        self.assertIn("fighters: 1", r.stdout)
        self.assertIn("stages: 1", r.stdout)
        self.assertIn("unsupported", r.stdout)
        self.assertFalse((self.out/"test"/"data").exists())

    def test_files_root_and_dry_run(self):
        r = self.run_tool(self.files, "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("MODIFIED      1", r.stdout)
        self.assertFalse(self.out.exists())
        r = self.run_tool(self.files)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads((self.out/"test"/"mod.json").read_text())["name"], "Synthetic Project")

    def test_rerun_changed_same_size_source_and_prune(self):
        self.assertEqual(self.run_tool().returncode, 0)
        (self.files/"plco.DAT").write_bytes(b"zzz")
        (self.files/"MxDt.dat").unlink()
        r = self.run_tool()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((self.out/"test"/"plco.DAT").read_bytes(), b"zzz")
        self.assertFalse((self.out/"test"/"MxDt.dat").exists())

    def test_unchanged_dol_and_missing_project_metadata(self):
        (self.project/"project.mexproj").unlink()
        (self.project/"sys"/"main.dol").write_bytes(bytes(0x100))
        r = self.run_tool()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("unchanged (not packed)", r.stdout)
        self.assertEqual(json.loads((self.out/"test"/"mod.json").read_text())["name"], "test")

    def test_recheck_repairs_corrupt_payload(self):
        self.assertEqual(self.run_tool().returncode, 0)
        (self.out/"test"/"plco.DAT").write_bytes(b"bad")
        r = self.run_tool(None, "--recheck")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((self.out/"test"/"plco.DAT").read_bytes(), b"new")

    def test_only_filter_reports_skips_and_preserves_metadata(self):
        r = self.run_tool(None, "--only", "audio/*")
        self.assertEqual(r.returncode, 0, r.stderr)
        m = json.loads((self.out/"test.gdm_pack.json").read_text())
        self.assertEqual(set(m["files"]), {"audio/new.ssm"})
        self.assertIn("excluded      2", r.stdout)
        self.assertTrue((self.out/"test"/"mod.json").is_file())

    def test_iso_input_and_filters(self):
        mod = self.root/"mod.iso"
        iso(mod, {"plco.DAT":b"new", "same.dat":b"same", "MxDt.dat":b"mex"})
        r = self.run_tool(mod, "--exclude", "MX*", "--only", "PL*")
        self.assertEqual(r.returncode, 0, r.stderr)
        m = json.loads((self.out/"test.gdm_pack.json").read_text())
        self.assertEqual((m["new"], m["modified"]), (0, 1))
        self.assertEqual(set(m["files"]), {"plco.DAT"})


if __name__ == "__main__":
    unittest.main()
