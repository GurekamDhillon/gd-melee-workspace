"""Converter tests for the authored-fighter path (needs ports/vanilla-original/out/courier.glb; skips without it)."""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ART = os.path.normpath(os.path.join(HERE, "..", "..", "vanilla-original"))


@unittest.skipUnless(os.path.exists(os.path.join(ART, "out", "courier.glb")), "regenerate the art first")
class Authored(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import authored_fighter as af
        cls.af = af
        cls.g, cls.bin, cls.pl, cls.joints, cls.skin_pos, cls.jn, cls.src, cls.err = af.build_plan(ART, 1.0)

    def test_plan_is_depth_first_and_matches_gltf_world(self):
        for i, j in enumerate(self.joints):
            if j["parent"] is not None:
                self.assertLess(j["parent"], i)
        self.assertLess(self.err, 1e-4)
        self.assertEqual(len(self.joints), 42)                       # 39 bones + TopN, XRotN, YRotN
        self.assertEqual([j["name"] for j in self.joints[:2]], ["TopN", "root"])

    def test_parts_table_covers_the_roles(self):
        p2j = self.pl["parts"]["part_to_joint"]
        self.assertEqual(len(p2j), 54)
        names = [j["name"] for j in self.joints]
        for part, bone in (("TransN", "trans"), ("HeadN", "head"), ("RHaveN", "socket_item_R"), ("LFootJ", "foot_L")):
            idx = plan_index(part)
            self.assertEqual(names[p2j[idx]], bone, part)
        self.assertEqual([u.get("common_part") for u in self.pl["unresolved"] if u.get("common_part")], ["LHaveN"])

    def test_euler_roundtrip(self):
        import numpy as np
        for q in ([0, 0, 0, 1], [0.3, -0.2, 0.5, 0.78], [0.7071, 0, 0, 0.7071]):
            q = np.array(q, float) / np.linalg.norm(q)
            rx, ry, rz = self.af.quat_to_euler(q)
            c = lambda a: (np.cos(a), np.sin(a))
            cx, sx = c(rx); cy, sy = c(ry); cz, sz = c(rz)
            Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
            Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
            Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
            self.assertLess(np.abs(Rz @ Ry @ Rx - self.af.quat_to_mat(q)).max(), 1e-9)

    def test_anim_bank(self):
        with tempfile.TemporaryDirectory() as d:
            self.af.anim_main(ART, d, 1.0)
            b = json.load(open(os.path.join(d, "bank.json")))
            self.assertEqual(len(b["clips"]), 179)
            self.assertLess(b["max_euler_error_rad"], 1e-3)
            self.assertLess(max(c["bytes"] for c in b["clips"].values()), 0x20000)


def plan_index(part):
    import plan_parts
    return plan_parts.COMMON.index(part)



class ConstantTracks(unittest.TestCase):
    """A constant channel must never be a one-key track: fobj.c FObjLoadData takes a key's interpolation op from the key BEFORE it,
    so a single key ends in state 6 with op_intrp 0 and the engine writes an uninitialised 0 to the joint (measured on the Courier:
    thigh rest rotation pi and hips height lost). Two LIN keys of the same value hold it."""

    def test_constant_channel_is_two_lin_keys(self):
        import authored_fighter as af
        import figatree as F
        body, fv, fs = af._encode_channel([0.5] * 40, af.FRAC_ROT)
        keys = F.decode_keys(body, 0, len(body), fv, fs)
        self.assertEqual([k[0] for k in keys], [F.LIN, F.LIN])
        self.assertEqual(keys[0][3], 39)                                # the first key waits the clip length
        self.assertAlmostEqual(keys[0][1], 0.5, places=3)
        self.assertAlmostEqual(keys[1][1], 0.5, places=3)
        self.assertAlmostEqual(F.evaluate(keys, 17), 0.5, places=3)


if __name__ == "__main__":
    unittest.main()
