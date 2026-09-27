"""Source-to-host structural checks for the native Hammer charge prototype."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ports/kirby-ultimate/tools"))
sys.path.insert(0, str(ROOT / "tools/mex_port"))
import build_hammer  # noqa: E402
import build_side_b  # noqa: E402
from mex_hsd import Archive  # noqa: E402

BASE = ROOT / "experiment/brawl-kirby/disc/PlKb.dat"


@unittest.skipUnless(BASE.is_file(), "local Melee Kirby baseline is required")
class BuildHammerTest(unittest.TestCase):
    def test_reserved_rows_and_source_max_damage(self):
        original = BASE.read_bytes()
        ir = json.loads(build_hammer.IR.read_text(encoding="utf-8"))
        by_id = {script["id"]: script for script in ir["behavior"]["scripts"]}
        scripts = {row: by_id[sid] for row, sid in build_hammer.MAX_IDS.items()}
        updated, changed = build_hammer.patch_fighter(original, original, scripts)
        self.assertEqual(changed, [4, 5, 18])
        ar = Archive(updated)
        for row, damage in ((5, 35), (18, 28)):
            hits = [(frame, words[0] & 1023) for frame, op, words, _ in build_side_b.flatten(ar, row)
                    if op == 11]
            self.assertEqual(hits, [(11, damage), (11, damage)])
        self.assertEqual(build_side_b.linear_words(ar, 322),
                         build_side_b.linear_words(Archive(original), 322))
        self.assertEqual(build_hammer.patch_fighter(updated, original, scripts), (updated, []))

    def test_install_profile_reads_ultimate_charge_params(self):
        with tempfile.TemporaryDirectory() as folder:
            mod = Path(folder)
            (mod / "files").mkdir()
            (mod / "files/PlKb.dat").write_bytes(BASE.read_bytes())
            (mod / "geno.json").write_text(json.dumps({"geno": 3, "fighters": [{"attach": "kirby"}]}))
            self.assertEqual(build_hammer.install(mod, build_hammer.IR, BASE), [4, 5, 18])
            self.assertEqual(build_hammer.install(mod, build_hammer.IR, BASE), [])
            fighter = json.loads((mod / "geno.json").read_text())["fighters"][0]
            self.assertEqual(fighter["hammer"],
                             {"hold_max_f": 120.0, "charge_speed": 1.0, "hold_walk_speed_x": 0.4})
            self.assertEqual(fighter["specials"],
                             {"s": "geno:HammerHold", "air_s": "geno:HammerHoldAir"})


if __name__ == "__main__":
    unittest.main()
