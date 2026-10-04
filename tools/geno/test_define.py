"""Disc-free tests for complete native definitions, not executable acceptance."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from tools.geno import check, script


class DefineAuthorTests(unittest.TestCase):
    def test_new_is_definition_not_overlay_and_checks(self):
        from tools.geno.new import create
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "hero"
            create(root, "vanilla-hero", "Vanilla Hero", "mario")
            data = check.load_json(root / "geno.json")
            self.assertEqual(data["geno"], 6)
            f = data["fighters"][0]
            self.assertNotIn("attach", f)
            self.assertEqual(f["define"]["base"], "mario")
            self.assertEqual(check.validate(data, root), [])
            self.assertTrue(f["attributes"])
            self.assertTrue(f["subactions"])
            self.assertFalse(any(p.suffix.lower() in (".dat", ".usd", ".ssm") for p in root.rglob("*")))
            words = script.assemble((root / "moves/hero-jab.genoasm").read_text())
            self.assertTrue(words)
            from tools.geno.define import export_package
            out = Path(tmp) / "export"
            export_package(root, out)
            self.assertEqual(check.validate(check.load_json(out / "geno.json"), out), [])
            self.assertEqual(json.loads((out / "manifest.runtime.json").read_text())["backend"], "geno.define.v1")

    def test_definition_rejects_unsupported_contracts(self):
        from tools.geno.new import create
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "hero"
            create(root, "hero", "Hero", "mario")
            data = check.load_json(root / "geno.json")
            for field, value in (("base", "kirby"), ("common", "melee.common.v2"), ("resources", "private/archive.dat")):
                bad = copy.deepcopy(data)
                bad["fighters"][0]["define"][field] = value
                self.assertTrue(check.validate(bad, root), field)
            bad = copy.deepcopy(data); bad["fighters"][0]["attach"] = "mario"
            self.assertTrue(check.validate(bad, root))
            bad = copy.deepcopy(data); bad["geno"] = 5
            self.assertTrue(check.validate(bad, root))
            with self.assertRaises(ValueError):
                create(Path(tmp) / "unsupported", "hero", "Hero", "kirby")
            with self.assertRaises(ValueError):
                create(root, "hero", "Hero", "mario")

    def test_export_refuses_unlisted_disc_payload(self):
        from tools.geno.new import create
        from tools.geno.define import export_package
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "hero"
            create(root, "hero", "Hero", "mario")
            (root / "MxDt.dat").write_bytes(b"synthetic")
            with self.assertRaises(ValueError):
                export_package(root, Path(tmp) / "export")

    def test_native_script_and_state_row_bounds(self):
        from tools.geno.new import create
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "hero"
            create(root, "hero", "Hero", "mario")
            data = check.load_json(root / "geno.json")
            for index in (302, 303, 304, 1023):
                bad = copy.deepcopy(data)
                bad["fighters"][0]["subactions"][0]["index"] = index
                self.assertEqual(bool(check.validate(bad, root)), index >= 303)
                bad = copy.deepcopy(data)
                bad["fighters"][0]["common_states"] = [{"motion": 44, "subaction": index}]
                self.assertEqual(bool(check.validate(bad, root)), index >= 303)


if __name__ == "__main__":
    unittest.main()
