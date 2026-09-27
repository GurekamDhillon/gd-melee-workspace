"""Structural checks for installing selected Kirby visuals into the LAB pack."""

import hashlib
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
INSTALLER = ROOT / "ports/kirby-ultimate/tools/install_visuals.py"
BASE = ROOT / "experiment/brawl-kirby/disc"
sys.path.insert(0, str(ROOT / "tools/mex_port"))
import mex_hsd  # noqa: E402


def motion(ar, row):
    table = ar.u32(ar.public("ftDataKirby") + 0xC)
    return table + row * 0x18


class InstallVisualsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.mod = self.work / "mod"
        (self.mod / "files").mkdir(parents=True)
        (self.mod / "mod.json").write_text(json.dumps({
            "id": "ultimate-kirby-movement", "name": "Kirby + side B",
            "description": "Existing Melee Kirby model, animations, crouch and status logic remain in use.",
        }), encoding="utf-8")
        (self.mod / "source-manifest.json").write_text(json.dumps({
            "limitations": ["No Ultimate animations, model, collision body, status logic, or asset bytes are included."],
            "side_b": {"translation": "Melee hammer visuals remain."},
        }), encoding="utf-8")
        raw = bytearray((BASE / "PlKb.dat").read_bytes())
        ar = mex_hsd.Archive(raw)
        # Mimic a preexisting side-B patch with a different, valid script ptr.
        row = motion(ar, 322)
        other = motion(ar, 323)
        struct.pack_into(">I", raw, 0x20 + row + 0xC, ar.u32(other + 0xC))
        self.mod_pl = self.mod / "files/PlKb.dat"
        self.mod_pl.write_bytes(raw)
        self.before = bytes(raw)
        self.baseline_aj = (BASE / "PlKbAJ.dat").read_bytes()
        vanilla = mex_hsd.Archive((BASE / "PlKb.dat").read_bytes())
        row7 = motion(vanilla, 7)
        offset, size = vanilla.u32(row7 + 4), vanilla.u32(row7 + 8)
        self.clip = self.work / "WalkSlow.dat"
        clip = bytearray(self.baseline_aj[offset:offset + size])
        archive = mex_hsd.Archive(clip)
        struct.pack_into(">f", clip, 0x20 + archive.publics[0][1] + 8, 46.0)
        self.clip.write_bytes(clip)

    def install(self, *extra):
        return subprocess.run([sys.executable, str(INSTALLER),
                               "--mod", str(self.mod), *extra],
                              capture_output=True, text=True)

    def test_selected_clip_changes_only_motion_offset_and_size(self):
        manifest = self.work / "animations.json"
        manifest.write_text(json.dumps({"animations": [{
            "row": 7, "file": self.clip.name,
            "sha256": hashlib.sha256(self.clip.read_bytes()).hexdigest(),
        }]}), encoding="utf-8")
        result = self.install("--costume", str(BASE / "PlKbNr.dat"),
                              "--animations", str(manifest),
                              "--baseline-aj", str(BASE / "PlKbAJ.dat"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.mod / "files/PlKbNr.dat").read_bytes(),
                         (BASE / "PlKbNr.dat").read_bytes())
        aj = (self.mod / "files/PlKbAJ.dat").read_bytes()
        self.assertEqual(aj[:len(self.baseline_aj)], self.baseline_aj)
        new = mex_hsd.Archive(self.mod_pl.read_bytes())
        old = mex_hsd.Archive(self.before)
        slot = motion(new, 7)
        offset, size = new.u32(slot + 4), new.u32(slot + 8)
        self.assertEqual(aj[offset:offset + size], self.clip.read_bytes())
        self.assertEqual(offset % 0x20, 0)
        self.assertEqual(new.u32(motion(new, 322) + 0xC),
                         old.u32(motion(old, 322) + 0xC))
        expected = bytearray(old.data)
        expected[slot + 4:slot + 12] = new.data[slot + 4:slot + 12]
        self.assertEqual(new.data, expected)
        self.assertEqual(new.reloc_offsets, old.reloc_offsets)
        self.assertEqual(new.publics, old.publics)
        metadata = json.loads((self.mod / "source-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["visuals"]["costume"]["sha256"],
                         hashlib.sha256((BASE / "PlKbNr.dat").read_bytes()).hexdigest())
        self.assertEqual([entry["row"] for entry in metadata["visuals"]["animations"]], [7])
        self.assertFalse(any("No Ultimate animations, model" in item
                             for item in metadata["limitations"]))
        mod_json = json.loads((self.mod / "mod.json").read_text(encoding="utf-8"))
        self.assertIn("costume", mod_json["description"])
        self.assertIn("1 converted Ultimate clip", mod_json["description"])
        again = self.install("--costume", str(BASE / "PlKbNr.dat"),
                             "--animations", str(manifest),
                             "--baseline-aj", str(BASE / "PlKbAJ.dat"))
        self.assertEqual(again.returncode, 0, again.stderr)
        self.assertEqual((self.mod / "files/PlKbAJ.dat").read_bytes(), aj)
        self.assertEqual(self.mod_pl.read_bytes(), new.raw)
        costume_refresh = self.install("--costume", str(BASE / "PlKbNr.dat"))
        self.assertEqual(costume_refresh.returncode, 0, costume_refresh.stderr)
        refreshed = json.loads((self.mod / "source-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual([entry["row"] for entry in refreshed["visuals"]["animations"]], [7])

    def test_bad_symbol_is_rejected_before_mutation(self):
        manifest = self.work / "animations.json"
        manifest.write_text(json.dumps({"animations": [{
            "row": 13, "file": self.clip.name,
        }]}), encoding="utf-8")
        result = self.install("--animations", str(manifest),
                              "--baseline-aj", str(BASE / "PlKbAJ.dat"))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.mod_pl.read_bytes(), self.before)
        self.assertFalse((self.mod / "files/PlKbAJ.dat").exists())

    def test_costume_only_leaves_existing_fighter_data_alone(self):
        result = self.install("--costume", str(BASE / "PlKbNr.dat"))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.mod_pl.read_bytes(), self.before)
        self.assertFalse((self.mod / "files/PlKbAJ.dat").exists())
        metadata = json.loads((self.mod / "source-manifest.json").read_text(encoding="utf-8"))
        self.assertIsNotNone(metadata["visuals"]["costume"])
        self.assertEqual(metadata["visuals"]["animations"], [])

    def test_costume_with_changed_rest_pose_is_rejected(self):
        invalid = self.work / "bad-costume.dat"
        raw = bytearray((BASE / "PlKbNr.dat").read_bytes())
        archive = mex_hsd.Archive(raw)
        root = archive.public("PlyKirby5K_Share_joint")
        struct.pack_into(">f", raw, 0x20 + root + 0x2C, 5.0)
        invalid.write_bytes(raw)
        result = self.install("--costume", str(invalid))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.mod_pl.read_bytes(), self.before)
        self.assertFalse((self.mod / "files/PlKbNr.dat").exists())


if __name__ == "__main__":
    unittest.main()
