#!/usr/bin/env python3
"""Calibrated movement attributes reach the installed fighter's common attribute block."""
import json
import struct
import tempfile
import unittest
from pathlib import Path

import attr_apply as AA


class Mem:
    """The two Writer members attr_apply uses: u32 and the raw data."""
    def __init__(self, size=0x400, block=0x100, fd=0x20):
        self.data = bytearray(size)
        struct.pack_into(">I", self.data, fd, block)
        self.fd, self.block = fd, block
    def u32(self, o): return struct.unpack_from(">I", self.data, o)[0]


CAL = {"port": {"fighter": "trail", "attrs": {"walk_max_vel": 0.78063, "gravity": 0.07314, "max_jumps": 2.0,
                                              "landingairn_lag": 18.0, "model_scaling": 1.00572,
                                              "ledge_jump_horizontal_velocity": 1.0},
                "why": {}}}


class Layout(unittest.TestCase):
    def test_offsets_come_from_the_decomp_struct(self):
        lay = AA.attr_layout()
        self.assertEqual(lay["walk_max_vel"], (0x08, False))
        self.assertEqual(lay["max_jumps"], (0x58, True))
        self.assertEqual(lay["gravity"], (0x5C, False))
        self.assertEqual(lay["landingairn_lag"], (0xE8, False))
        self.assertEqual(lay["ledge_jump_horizontal_velocity"], (0xA8, False))


class Load(unittest.TestCase):
    def write(self, doc):
        d = tempfile.mkdtemp(); p = Path(d, "cal.json"); p.write_text(json.dumps(doc)); return p

    def test_other_fighters_calibration_is_refused(self):
        with self.assertRaises(ValueError):
            AA.load_port_attrs(self.write(CAL), "kirby")

    def test_model_scaling_is_held_back_with_a_reason(self):
        attrs, held = AA.load_port_attrs(self.write(CAL), "trail")
        self.assertNotIn("model_scaling", attrs)
        self.assertIn("model_scaling", held)
        self.assertEqual(attrs["walk_max_vel"], 0.78063)

    def test_unknown_field_is_an_error(self):
        bad = json.loads(json.dumps(CAL)); bad["port"]["attrs"]["not_a_field"] = 1.0
        with self.assertRaises(ValueError):
            AA.load_port_attrs(self.write(bad), "trail")


class Resolve(unittest.TestCase):
    def test_off_and_foreign_auto(self):
        self.assertIsNone(AA.resolve("off", "trail"))
        self.assertIsNone(AA.resolve("auto", "no_such_fighter"))

    def test_explicit_path(self):
        d = tempfile.mkdtemp(); p = Path(d, "c.json"); p.write_text(json.dumps(CAL))
        path, attrs, held = AA.resolve(str(p), "trail")
        self.assertEqual(path, str(p)); self.assertIn("gravity", attrs); self.assertIn("model_scaling", held)
        with self.assertRaises(ValueError):
            AA.resolve(str(p), "kirby")


class Kinetics(unittest.TestCase):
    def test_params_from_calibration(self):
        doc = json.loads(json.dumps(CAL)); doc["fits"] = {"jump_v_initial_velocity": {"median_ratio": 1.036}}
        doc["port"]["attrs"]["terminal_velocity"] = 1.815
        d = tempfile.mkdtemp(); p = Path(d, "c.json"); p.write_text(json.dumps(doc))
        self.assertEqual(AA.kinetics_params(str(p), "trail"),
                         {"speed_ratio": 1.036, "gravity": 0.07314, "terminal": 1.815})
        self.assertIsNone(AA.kinetics_params("off", "trail"))


class Apply(unittest.TestCase):
    def test_floats_and_ints_are_written_in_place(self):
        m = Mem()
        struct.pack_into(">f", m.data, m.block + 0x08, 1.6)
        struct.pack_into(">i", m.data, m.block + 0x58, 6)
        rep = AA.apply_to_block(m, m.fd, {"walk_max_vel": 0.78063, "max_jumps": 2.0, "landingairn_lag": 18.0})
        self.assertAlmostEqual(struct.unpack_from(">f", m.data, m.block + 0x08)[0], 0.78063, places=5)
        self.assertEqual(struct.unpack_from(">i", m.data, m.block + 0x58)[0], 2)
        self.assertEqual(struct.unpack_from(">f", m.data, m.block + 0xE8)[0], 18.0)
        self.assertAlmostEqual(rep["walk_max_vel"]["before"], 1.6, places=5)
        self.assertEqual(rep["max_jumps"], {"before": 6, "after": 2})

    def test_null_block_is_an_error(self):
        m = Mem(); struct.pack_into(">I", m.data, m.fd, 0)
        with self.assertRaises(ValueError):
            AA.apply_to_block(m, m.fd, {"gravity": 0.07})

    def test_block_outside_the_file_is_an_error(self):
        m = Mem(size=0x200, block=0x1F0)
        with self.assertRaises(ValueError):
            AA.apply_to_block(m, m.fd, {"landingairn_lag": 18.0})


if __name__ == "__main__":
    unittest.main()
