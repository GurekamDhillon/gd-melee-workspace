"""Decoder-level checks for the Ultimate Kirby side-B HSD patch."""

import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
BUILDER = ROOT / "ports/kirby-ultimate/tools/build_side_b.py"
IR = ROOT / "experiment/character-ir/instances/kirby.ultimate.ir.json"
BASE = ROOT / "experiment/brawl-kirby/disc/PlKb.dat"
DECODER = ROOT / "experiment/brawl-kirby/tools/melee_dump.py"
sys.path.insert(0, str(ROOT / "tools/mex_port"))
import mex_hsd  # noqa: E402


class SideBTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name)
        self.mod = self.work / "ultimate-kirby-movement"
        (self.mod / "files").mkdir(parents=True)
        self.output = self.mod / "files/PlKb.dat"
        raw = bytearray(BASE.read_bytes())
        ar = mex_hsd.Archive(raw)
        fd = ar.public("ftDataKirby")
        attrs = ar.u32(fd)
        # A sentinel movement attribute proves the patcher uses the existing
        # mod file as its destination instead of replacing it with vanilla.
        struct.pack_into(">f", raw, 0x20 + attrs + 8, 0.9375)
        self.output.write_bytes(raw)
        self.before = bytes(raw)
        (self.mod / "mod.json").write_text(json.dumps({
            "id": "ultimate-kirby-movement",
            "name": "Ultimate Kirby movement",
            "description": "Movement proof of life",
        }), encoding="utf-8")
        (self.mod / "source-manifest.json").write_text(json.dumps({
            "source_document_id": "kirby.ultimate",
            "target": "Geno v3 overlay attached to vanilla Melee Kirby",
        }), encoding="utf-8")

    def build(self):
        self.assertTrue(BUILDER.is_file(), "side-B builder has not been implemented")
        result = subprocess.run(
            [sys.executable, str(BUILDER), "--ir", str(IR),
             "--base", str(BASE), "--mod", str(self.mod)],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def decode(self, path, name):
        report = self.work / f"{name}.json"
        env = dict(os.environ, MD_IN=str(path), MD_OUT=str(report))
        subprocess.run([sys.executable, str(DECODER)], check=True,
                       capture_output=True, text=True, env=env)
        data = json.loads(report.read_text(encoding="utf-8"))
        scripts = {s["offset"]: s for s in data["scripts"]}
        return {i: scripts[data["motion_table"][i]["script"]] for i in (322, 323)}

    def test_ir_hitboxes_and_unchanged_host_events(self):
        original = self.decode(self.output, "original")
        self.build()
        patched = self.decode(self.output, "patched")
        ir = json.loads(IR.read_text(encoding="utf-8"))
        ir_scripts = {s["id"]: s for s in ir["behavior"]["scripts"]}
        expected = {
            322: (19, 48, [(11, 0, 5.4), (11, 1, 3.5)], [(12, 13)]),
            323: (16, 50, [(11, 0, 5.4), (11, 1, 3.2),
                           (25, 0, 5.4), (25, 1, 3.2)], [(12, 13), (26, 27)]),
        }
        flow = {"SyncWait", "AsyncWait", "SetLoop", "ExecLoop"}
        hitops = {"Hitbox", "ClearHitboxes", "RemoveHitbox",
                  "HitboxDamage", "HitboxSize", "HitboxFlags"}
        for row, (damage, angle, hits, windows) in expected.items():
            with self.subTest(row=row):
                source_id = ("script:kirby/specials/game_specials" if row == 322 else
                             "script:kirby/specialairs/game_specialairs")
                source_hits = [e["hitbox"] for e in ir_scripts[source_id]["events"]
                               if e["op"] == "hitbox.create"]
                events = patched[row]["events"]
                got = [(e["frame"], e["hitbox"]["slot"], e["hitbox"]["size"])
                       for e in events if e["name"] == "Hitbox"]
                self.assertEqual(len(got), len(hits))
                for (frame, slot, size), (want_frame, want_slot, want_size) in zip(got, hits):
                    self.assertEqual((frame, slot), (want_frame, want_slot))
                    self.assertAlmostEqual(size, want_size, delta=1 / 256)
                for e, source in zip((e for e in events if e["name"] == "Hitbox"), source_hits):
                    h = e["hitbox"]
                    self.assertEqual((h["damage"], h["angle"],
                                      h["knockback_growth"], h["base_knockback"],
                                      h["element"]),
                                     (damage, angle, 78, 60, source["element"]))
                self.assertEqual(
                    [(w["start"], w["end"]) for w in patched[row]["timeline"]["hit_windows"]],
                    windows,
                )
                def kept(script):
                    return [(e.get("frame"), e["name"], e["raw"]["words"])
                            for e in script["events"] if e["name"] not in flow | hitops]
                self.assertEqual(kept(patched[row]), kept(original[row]))

    def test_only_side_b_script_pointers_change_and_rebuild_is_stable(self):
        self.build()
        first = self.output.read_bytes()
        old, new = mex_hsd.Archive(self.before), mex_hsd.Archive(first)
        mt = old.u32(old.public("ftDataKirby") + 0xC)
        original_data = bytearray(old.data)
        patched_data = bytearray(new.data[:len(original_data)])
        for row in (322, 323):
            pointer = mt + row * 0x18 + 0xC
            patched_data[pointer:pointer + 4] = original_data[pointer:pointer + 4]
        self.assertEqual(patched_data, original_data)
        self.assertEqual(struct.unpack_from(">f", new.data, old.u32(old.public("ftDataKirby")) + 8)[0], 0.9375)
        self.build()
        self.assertEqual(self.output.read_bytes(), first)
        mod = json.loads((self.mod / "mod.json").read_text(encoding="utf-8"))
        self.assertEqual(mod["id"], "ultimate-kirby-movement")
        self.assertIn("side B", mod["name"])
        self.assertIn("side B", mod["description"])
        manifest = json.loads((self.mod / "source-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["side_b"]["ir_scripts"], [
            "script:kirby/specials/game_specials",
            "script:kirby/specialairs/game_specialairs",
        ])
        self.assertIn("not version-matched", manifest["side_b"]["source_revision_status"])

    def test_creates_payload_when_movement_overlay_has_no_pl_file(self):
        self.output.unlink()
        self.build()
        self.assertTrue(self.output.is_file())
        patched = self.decode(self.output, "new_payload")
        self.assertEqual([e["hitbox"]["damage"] for e in patched[322]["events"]
                          if e["name"] == "Hitbox"], [19, 19])


if __name__ == "__main__":
    unittest.main()
