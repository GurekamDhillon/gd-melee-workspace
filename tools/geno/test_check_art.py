import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.geno import check_art

ART = Path(__file__).resolve().parents[2] / "ports" / "vanilla-original"


@unittest.skipUnless((ART / "out" / "courier.glb").exists(), "run ports/vanilla-original/build_all.sh first")
class CheckArt(unittest.TestCase):
    def copy(self):
        d = Path(tempfile.mkdtemp())
        for f in ("manifest.json", "skeleton.json", "hurtboxes.json"):
            shutil.copy(ART / f, d / f)
        (d / "out").mkdir()
        shutil.copy(ART / "out" / "courier.glb", d / "out" / "courier.glb")
        shutil.copytree(ART / "out" / "tex", d / "out" / "tex")
        self.addCleanup(shutil.rmtree, d, True)
        return d

    def test_courier_passes(self):
        errs, warns, info = check_art.check(ART)
        self.assertEqual(errs, [])
        self.assertEqual(info["bones"], 39)
        self.assertEqual(info["hurtboxes"], 15)
        self.assertTrue(any("placeholder" in w for w in warns))

    def test_bad_clip_reference_names_the_row(self):
        d = self.copy()
        m = json.load(open(d / "manifest.json"))
        m["motion_rows"][5]["clip"] = "NoSuchClip"
        m["motion_rows"][5]["status"] = "own"
        json.dump(m, open(d / "manifest.json", "w"))
        errs, _, _ = check_art.check(d)
        self.assertTrue(any("NoSuchClip" in e and "motion_rows" in e for e in errs), errs)

    def test_hurtbox_and_ecb_errors(self):
        d = self.copy()
        h = json.load(open(d / "hurtboxes.json"))
        h["hurtboxes"][0]["bone"] = "nonexistent"
        h["ecb"]["standing"]["top"] = -1
        json.dump(h, open(d / "hurtboxes.json", "w"))
        errs, _, _ = check_art.check(d)
        self.assertTrue(any("nonexistent" in e for e in errs))
        self.assertTrue(any("ecb.standing is inverted" in e for e in errs))

    def test_missing_texture(self):
        d = self.copy()
        (d / "out" / "tex" / "costume_red.png").unlink()
        errs, _, _ = check_art.check(d)
        self.assertTrue(any("costume 'red'" in e for e in errs))


if __name__ == "__main__":
    unittest.main()
