"""Pipeline checks for the Atlas font roles:  python menu/pipeline/test_atlas_fonts.py
Regenerates menu/out_kit/font (deterministic) and reads the result, the C role table and the loader limits."""
import json
import os
import re
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kit  # noqa: E402

MENU = os.path.dirname(HERE)
REPO = os.path.dirname(MENU)
GAME = os.environ.get("GW_MELEE") or os.path.join(REPO, "melee")
LEGACY = ["caption", "body", "row", "label", "title", "heading", "hero", "display", "tag", "code"]
FACE_GROUP = {"acond": 0, "asans": 1, "anum": 2}


class AtlasFonts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import font_atlas
        assert font_atlas.main() == 0, "font_atlas.py checks failed"
        path = os.path.join(MENU, "out_kit", "font", "font_manifest.json")
        cls.m = json.load(open(path, encoding="utf-8"))
        cls.roles = cls.m["roles"]

    def test_atlas_roles_present_and_legacy_intact(self):
        for name in [s["role"] for s in kit.ATLAS_TYPE_SCALE]:
            self.assertIn(name, self.roles)
        for name in LEGACY:
            self.assertIn(name, self.roles)
        self.assertEqual(len(kit.ATLAS_TYPE_SCALE), 13)

    def test_floor_and_faces(self):
        for spec in kit.ATLAS_TYPE_SCALE:
            r = self.roles[spec["role"]]
            self.assertGreaterEqual(r["size"], 12, spec["role"])
            self.assertIn(r["face"], FACE_GROUP)
            self.assertNotIn(r["face"], ("sans", "mono"), "Atlas roles must not share a face tag with the legacy roles: the loader's fit rule steps down inside one face")

    def test_printable_ascii_everywhere(self):
        for spec in kit.ATLAS_TYPE_SCALE:
            if spec["charset"] == "caps":
                continue
            glyphs = self.roles[spec["role"]]["glyphs"]
            for ch in kit.ASCII:
                self.assertIn(ch, glyphs, "%s lacks %r" % (spec["role"], ch))
            self.assertIn("…", glyphs, "%s lacks the ellipsis the fit rule truncates with" % spec["role"])

    def test_tabular_digits_where_declared(self):
        for spec in kit.ATLAS_TYPE_SCALE:
            if spec.get("tabular", True):
                g = self.roles[spec["role"]]["glyphs"]
                self.assertEqual(len({g[d]["advance"] for d in "0123456789"}), 1, spec["role"])
        for name in ("a_num12", "a_num14", "a_num16"):
            self.assertTrue(self.roles[name]["monospaced"])

    def test_sync_with_the_c_role_table(self):
        text = open(os.path.join(GAME, "pc", "platform", "gw_ui_layout.c"), encoding="utf-8").read()
        rows = re.findall(r'\{\s*"(a_\w+)",\s*(\d+),\s*(\d+),\s*(\d+),\s*(\d+),\s*(-?\w+)\s*\}', text)
        self.assertEqual(len(rows), 13)
        for (name, size, face, caps, _tracked, _smaller), spec in zip(rows, kit.ATLAS_TYPE_SCALE):
            self.assertEqual(name, spec["role"])
            self.assertEqual(int(size), spec["size"], name)
            self.assertEqual(int(face), FACE_GROUP[spec["face"]], name)
            self.assertEqual(int(caps), 1 if spec["charset"] == "caps" else 0, name)

    def test_loader_limits_hold(self):
        text = open(os.path.join(GAME, "pc", "platform", "gw_kit.c"), encoding="utf-8").read()
        roles_cap = int(re.search(r"#define KF_ROLES (\d+)", text).group(1))
        kern_cap = int(re.search(r"#define KF_MAX_KERN (\d+)", text).group(1))
        self.assertLessEqual(len(self.roles), roles_cap)
        total = sum(len(r["kerning"]) for r in self.roles.values())
        self.assertLessEqual(total, kern_cap, "the loader silently drops kerning pairs past KF_MAX_KERN (%d pairs here)" % total)

    def test_licence_and_files_ship(self):
        for f in ("BarlowCondensed-SemiBold.ttf", "BarlowCondensed-Bold.ttf", "OFL.txt"):
            self.assertTrue(os.path.exists(os.path.join(MENU, "Barlow", f)), f)
        self.assertTrue(os.path.exists(os.path.join(REPO, "tools", "release", "licenses", "BarlowCondensed-OFL-1.1.txt")))


if __name__ == "__main__":
    unittest.main()
