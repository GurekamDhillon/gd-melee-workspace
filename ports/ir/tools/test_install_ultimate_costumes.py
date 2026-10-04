#!/usr/bin/env python3
"""Offline checks for Ultimate costume selection and m-ex row wiring."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import install_ultimate as IU


class FakeArchive:
    def public(self, symbol):
        assert symbol == "mexData"
        return 0x20


def writer():
    w = object.__new__(IU.Writer)
    w.ar = FakeArchive()
    w.data = bytearray(0x100)
    w.relocs = set()
    return w


def cstr(w, offset):
    return w.str_at(w.u32(offset))


class CostumeSelectionTest(unittest.TestCase):
    def test_costume_template_work_directory_exists_before_build(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = IU.costume_workdir(Path(tmp) / "slot")
            self.assertTrue(work.is_dir())
            (work / "template_Nr.dat").write_bytes(b"template")
            self.assertEqual((work / "template_Nr.dat").read_bytes(), b"template")

    def test_generated_ir_root_is_inherited_by_conversion_workers(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, GW_ULTIMATE_IR_ROOT=tmp)
            result = subprocess.run(
                [sys.executable, "-c", "import convert_ultimate_anim as ca; print(ca.INSTANCES)"],
                cwd=Path(__file__).parent, env=env, capture_output=True, text=True, check=True)
            self.assertEqual(result.stdout.strip(), tmp)

    def test_complete_costumes_are_selected_in_ultimate_order_and_capped_at_eight(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = Path(tmp)
            for i in range(9):
                folder = body / f"c{i:02}"
                folder.mkdir()
                for name in ("model.numshb", "model.numdlb", "model.numatb", "colour.nutexb"):
                    (folder / name).touch()
            self.assertEqual(IU.discover_costumes(body),
                             [("c00", "Nr"), ("c01", "Ye"), ("c02", "Bu"), ("c03", "Re"),
                              ("c04", "Gr"), ("c05", "Wh"), ("c06", "Bk"), ("c07", "Or")])
            self.assertEqual(IU.discover_costumes(body, c00_only=True), [("c00", "Nr")])

    def test_missing_middle_costume_fails_instead_of_mismatching_ui_art(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = Path(tmp)
            for i in (0, 2):
                folder = body / f"c{i:02}"
                folder.mkdir()
                for name in ("model.numshb", "model.numdlb", "model.numatb", "colour.nutexb"):
                    (folder / name).touch()
            with self.assertRaisesRegex(ValueError, "c01"):
                IU.discover_costumes(body)

    def test_incomplete_costume_is_not_installed(self):
        with tempfile.TemporaryDirectory() as tmp:
            body = Path(tmp)
            for i in (0, 1):
                folder = body / f"c{i:02}"
                folder.mkdir()
                for name in ("model.numshb", "model.numdlb", "model.numatb"):
                    (folder / name).touch()
            (body / "c00" / "colour.nutexb").touch()
            self.assertEqual(IU.discover_costumes(body), [("c00", "Nr")])


class MexCostumeRowTest(unittest.TestCase):
    def test_eight_files_replace_host_count_and_all_costume_rows(self):
        w = writer()
        w.put(0x28, 0x40)       # mexData.fighter
        w.put(0x50, 0x80)       # fighter.costume_info
        w.put(0x54, 0xA0)       # fighter.costume_file
        w.data[0x80 + 4 * 3:0x80 + 4 * 3 + 4] = bytes((7, 1, 0, 2))
        files = [f"PlUs{suffix}.dat" for suffix in ("Nr", "Ye", "Bu", "Re", "Gr", "Wh", "Bk", "Or")]

        IU.write_costume_rows(w, internal=5, external=3, files=files,
                              joint_sym="PlySora5K_Share_joint", mat_sym="PlySora5K_Share_matanim_joint")

        self.assertEqual(bytes(w.data[0x8C:0x90]), bytes((8, 1, 0, 2)))
        table = w.u32(0xA0 + 5 * 4)
        self.assertIn(0xA0 + 5 * 4, w.relocs)
        self.assertEqual([cstr(w, table + i * 16) for i in range(8)], files)
        self.assertEqual([cstr(w, table + i * 16 + 4) for i in range(8)],
                         ["PlySora5K_Share_joint"] * 8)
        self.assertEqual([cstr(w, table + i * 16 + 8) for i in range(8)],
                         ["PlySora5K_Share_matanim_joint"] * 8)
        self.assertEqual([w.u32(table + i * 16 + 12) for i in range(8)], list(range(8)))

    def test_one_file_sets_one_selectable_costume(self):
        w = writer()
        w.put(0x28, 0x40)
        w.put(0x50, 0x80)
        w.put(0x54, 0xA0)
        w.data[0x8C:0x90] = bytes((7, 1, 0, 2))
        IU.write_costume_rows(w, 5, 3, ["PlUsNr.dat"], "joint", "matanim")
        self.assertEqual(bytes(w.data[0x8C:0x90]), bytes((1, 0, 0, 0)))
        self.assertEqual(cstr(w, w.u32(0xB4)), "PlUsNr.dat")


class CostumeVisibilityTest(unittest.TestCase):
    def test_each_costume_uses_its_own_dobj_indices(self):
        w = writer()
        channels = [["blink", "face"]]          # one ModelVis model: state 0 none, 1 blink, 2 face
        groups = [["body", "face", "blink"], ["blink", "body", "face", "extra"]]

        table = IU.write_costume_modelvis(w, channels, groups)

        first = w.u32(table)
        second = w.u32(table + 16)
        self.assertNotEqual(first, second)
        for model, expected in ((first, ([], [2], [1])), (second, ([], [0], [2]))):
            self.assertEqual(w.u32(model), len(expected))
            state_table = w.u32(model + 4)
            for index, dobjs in enumerate(expected):
                entry = state_table + index * 8
                self.assertEqual(w.u32(entry), len(dobjs))
                self.assertEqual(list(w.data[w.u32(entry + 4):w.u32(entry + 4) + len(dobjs)]), dobjs)
        self.assertEqual(w.u32(table + 2 * 16), first)

    def test_every_channel_is_its_own_model_entry(self):
        w = writer()
        table = IU.write_costume_modelvis(w, [["a", "b"], ["c"]], [["a", "b", "c"]])
        model = w.u32(table)
        self.assertEqual([w.u32(model + 8 * i) for i in range(2)], [3, 2])


if __name__ == "__main__":
    unittest.main()
