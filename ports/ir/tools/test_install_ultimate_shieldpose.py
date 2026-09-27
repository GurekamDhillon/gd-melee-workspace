#!/usr/bin/env python3
"""Offline checks for the ftData guard and metal pose trees."""
import math
import struct
import unittest

import numpy as np
from scipy.spatial.transform import Rotation

import install_ultimate as IU


def joint(name, parent, trans=(0, 0, 0)):
    return {"name": name, "parent": parent, "rot": [0.0] * 3,
            "scale": [1.0] * 3, "trans": list(trans)}


class ShieldPoseTest(unittest.TestCase):
    def test_guard_frame_zero_uses_clip_srt_and_respects_translation_override(self):
        joints = [joint("TopN", None), joint("Trans", 0, (1, 2, 3)),
                  joint("Arm", 1, (4, 5, 6)), joint("Unkeyed", 1)]
        plan = {"joints": [{"name": j["name"], "parent": j["parent"],
                            "synthesized": j["name"] == "TopN"} for j in joints]}
        rest = {name: (np.array(j["trans"]), Rotation.identity(), np.ones(3), np.zeros(3))
                for name, j in ((j["name"], j) for j in joints[1:])}
        def node(name, translation, scale, rotation, override=False):
            return {"name": name, "tracks": [{"transform_flags": {"override_translation": override},
                    "values": {"Transform": [{"translation": dict(zip("xyz", translation)),
                                               "scale": dict(zip("xyz", scale)),
                                               "rotation": dict(zip("xyzw", rotation))}]}}]}
        anim = {"final_frame_index": 0.0, "groups": [{"group_type": "Transform", "nodes": [
            node("Trans", (10, 20, 30), (1, 1, 1), (0, 0, 0, 1), True),
            node("Arm", (7, 8, 9), (2, 3, 4), Rotation.from_euler("z", 90, degrees=True).as_quat())]}]}
        pose = IU.guard_pose_joints(anim, plan, rest, joints, {})
        self.assertEqual(pose[1]["trans"], [1, 2, 3])
        self.assertEqual(pose[2]["trans"], [7, 8, 9])
        self.assertEqual(pose[2]["scale"], [2, 3, 4])
        self.assertAlmostEqual(pose[2]["rot"][2], math.pi / 2)
        self.assertEqual(pose[3]["trans"], joints[3]["trans"])

    def test_ftdata_guard_and_metal_trees_match_plan(self):
        w = object.__new__(IU.Writer)
        w.data, w.relocs = bytearray(0x80), set()
        fd = 0x20
        joints = [joint("TopN", None), joint("Trans", 0), joint("Arm", 1), joint("Leg", 1)]
        guard = [dict(j, trans=[i * 2.0, 0.0, 0.0]) for i, j in enumerate(joints)]
        IU.install_ftdata_pose_trees(w, fd, joints, guard)
        root = w.u32(w.u32(fd + 0x20))
        self.assertEqual(w.u32(root), 0)  # x0[0] is HSD_Joint.name
        self.assertEqual(w.u32(root + 4), 8)  # x0[1] is HSD_Joint.flags
        self.assertEqual(IU.count_joint_tree(w, root), 4)
        self.assertEqual(IU.count_joint_tree(w, w.u32(root + 8)), 3)
        self.assertEqual(IU.count_joint_tree(w, w.u32(fd + 0x5C)), 4)
        self.assertEqual(struct.unpack_from(">f", w.data, w.u32(root + 8) + 0x2C)[0], 2.0)
        metal = w.u32(fd + 0x5C)
        self.assertEqual(struct.unpack_from(">f", w.data, w.u32(metal + 8) + 0x2C)[0], 0.0)

        # A retained host tree or a broken link must fail before save.
        w.ptr(fd + 0x5C, IU.joint_tree(w, joints[:2]))
        with self.assertRaisesRegex(ValueError, "x5C.*2 joints.*expected 4"):
            IU.validate_ftdata_pose_trees(w, fd, 4)
        w.ptr(fd + 0x5C, metal)
        w.ptr(root + 8, IU.joint_tree(w, joints[:2]))
        with self.assertRaisesRegex(ValueError, "x20->x0.*3 joints.*expected 4"):
            IU.validate_ftdata_pose_trees(w, fd, 4)


if __name__ == "__main__":
    unittest.main()
