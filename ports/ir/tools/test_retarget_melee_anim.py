"""retarget_melee_anim: synthetic rigs and clips only (no disc, no game files). The decode test needs the game checkout's headers and skips without them."""
import json
import os
import struct
import sys
import tempfile
import unittest

import numpy as np
from scipy.spatial.transform import Rotation as R

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import retarget_melee_anim as T  # noqa: E402


def humanoid(scale=1.0, a_pose=False, spine_bones=1, names=None):
    """A synthetic T-pose (or A-pose) humanoid. Returns Rig with every role the solver reads."""
    names = names or {}
    joints = []                                      # (key, parent key, translation)
    k = lambda x: names.get(x, x)
    joints.append(("root", None, (0, 0, 0)))
    joints.append(("hips", "root", (0, 5, 0)))
    prev = "hips"
    spine_keys = ["spine"] + (["chest"] if spine_bones == 2 else [])
    for key in spine_keys:
        joints.append((key, prev, (0, 1, 0)))
        prev = key
    joints.append(("neck", prev, (0, 2, 0)))
    joints.append(("head", "neck", (0, 1, 0)))
    for side, sx in (("L", 1), ("R", -1)):
        joints.append(("shoulder." + side, prev, (sx * 1, 1.5, 0)))
        joints.append(("upper_arm." + side, "shoulder." + side, (sx * 1, 0, 0)))
        down = -1.0 if a_pose else 0.0
        joints.append(("lower_arm." + side, "upper_arm." + side, (sx * 1.5, down * 1.5, 0)))
        joints.append(("hand." + side, "lower_arm." + side, (sx * 1.5, down * 1.5, 0)))
        joints.append(("upper_leg." + side, "hips", (sx * 1, 0, 0)))
        joints.append(("lower_leg." + side, "upper_leg." + side, (0, -2, 0)))
        joints.append(("foot." + side, "lower_leg." + side, (0, -2, 0)))
    order = [j[0] for j in joints]
    t = np.array([j[2] for j in joints], float) * scale
    rig = T.Rig([k(j[0]) for j in joints], [-1 if j[1] is None else order.index(j[1]) for j in joints], t, np.tile([0, 0, 0, 1.0], (len(joints), 1)))
    rig.roles = {j[0]: i for i, j in enumerate(joints) if j[0] != "root"}
    rig.roles["translation"] = 0
    return rig


def pose_of(rig, rot_by_role, hip_shift=(0, 0, 0)):
    """Local TRS arrays shaped (F=1, N, *) with given local rotations (role -> Rotation)."""
    q = np.tile(rig.q, (1, 1, 1)).copy()
    t = np.tile(rig.t, (1, 1, 1)).copy()
    for role, rot in rot_by_role.items():
        q[0, rig.roles[role]] = rot.as_quat()
    t[0, rig.roles["hips"]] += hip_shift
    return t, q, np.tile(rig.s, (1, 1, 1))


class SolverTests(unittest.TestCase):
    def test_same_skeleton_twice_the_size_reproduces_rotations_and_scales_the_hips(self):
        src, dst = humanoid(1.0), humanoid(2.0, names={"hips": "pelvis", "head": "Head"})
        rng = np.random.default_rng(3)
        rots = {role: R.from_rotvec(rng.normal(size=3) * 0.4) for role in src.roles if role not in ("translation",)}
        t, q, s = pose_of(src, rots, hip_shift=(0.5, 0.25, -1))
        res = T.retarget(src, t, q, s, dst)
        self.assertAlmostEqual(res.report["ratio"], 2.0, places=6)
        for role in rots:
            got = R.from_quat(res.q[0, dst.roles[role]])
            self.assertLess((got * rots[role].inv()).magnitude(), 1e-6, role)
        np.testing.assert_allclose(res.hips_t[0], dst.t[dst.roles["hips"]] + 2.0 * np.array([0.5, 0.25, -1]), atol=1e-9)
        # end effectors land where the scaled source's do
        err = T.pose_error(src, t, q, s, res, 2.0)
        self.assertLess(max(v[0] for v in err.values()), 1e-6)

    def test_a_pose_destination_follows_the_source_bone_directions(self):
        src, dst = humanoid(1.0), humanoid(1.0, a_pose=True)
        rots = {"upper_arm.L": R.from_euler("z", 50, degrees=True), "lower_arm.L": R.from_euler("y", 40, degrees=True),
                "upper_leg.R": R.from_euler("x", -60, degrees=True)}
        for rest_only in (False, True):
            t, q, s = pose_of(src, {} if rest_only else rots)
            res = T.retarget(src, t, q, s, dst, ratio=1.0)
            ws, wd = src.world(t, q, s), T.solved_world(res)
            for a, b in (("upper_arm.L", "lower_arm.L"), ("lower_arm.L", "hand.L"), ("upper_leg.R", "lower_leg.R"),
                         ("upper_arm.R", "lower_arm.R"), ("lower_leg.L", "foot.L")):
                vs = ws[0, src.roles[b], :3, 3] - ws[0, src.roles[a], :3, 3]
                vd = wd[0, dst.roles[b], :3, 3] - wd[0, dst.roles[a], :3, 3]
                cos = vs @ vd / np.linalg.norm(vs) / np.linalg.norm(vd)
                self.assertGreater(cos, 0.9999, "%s -> %s (rest_only=%s)" % (a, b, rest_only))

    def test_twist_about_the_bone_axis_is_kept(self):
        src, dst = humanoid(1.0), humanoid(1.0)
        t, q, s = pose_of(src, {"upper_arm.L": R.from_euler("x", 70, degrees=True)})       # the arm lies on X: this is pure twist
        res = T.retarget(src, t, q, s, dst, ratio=1.0)
        got = R.from_quat(res.q[0, dst.roles["upper_arm.L"]])
        self.assertLess((got * R.from_euler("x", 70, degrees=True).inv()).magnitude(), 1e-6)

    def test_one_torso_bone_drives_spine_with_half_and_chest_with_all(self):
        src, dst = humanoid(1.0, spine_bones=1), humanoid(1.0, spine_bones=2)
        t, q, s = pose_of(src, {"spine": R.from_euler("x", 40, degrees=True)})
        res = T.retarget(src, t, q, s, dst, ratio=1.0)
        wd = R.from_matrix(T.world_rotations(T.solved_world(res))[0])
        self.assertAlmostEqual(wd[dst.roles["spine"]].magnitude() * 180 / np.pi, 20, places=4)
        self.assertAlmostEqual(wd[dst.roles["chest"]].magnitude() * 180 / np.pi, 40, places=4)
        self.assertEqual(res.report["roles"]["chest"]["driven_by"], "spine")

    def test_unmatched_destination_bones_keep_their_rest_rotation(self):
        src, dst = humanoid(1.0), humanoid(1.0)
        extra = T.Rig(dst.names + ["helper"], dst.parents + [dst.roles["upper_arm.L"]], np.vstack([dst.t, [0, 0.1, 0]]),
                      np.vstack([dst.q, [0, 0, 0, 1]]), roles=dst.roles)
        t, q, s = pose_of(src, {"upper_arm.L": R.from_euler("z", 30, degrees=True)})
        res = T.retarget(src, t, q, s, extra, ratio=1.0)
        np.testing.assert_allclose(res.q[0, -1], [0, 0, 0, 1], atol=1e-12)

    def test_missing_destination_roles_are_reported_not_invented(self):
        src, dst = humanoid(1.0), humanoid(1.0)
        del dst.roles["hand.L"]
        t, q, s = pose_of(src, {})
        res = T.retarget(src, t, q, s, dst, ratio=1.0)
        self.assertNotIn("hand.L", res.report["roles"])

    def test_size_ratio_uses_limb_chains(self):
        mean, per, leg = T.size_ratio(humanoid(1.0), humanoid(1.7))
        self.assertAlmostEqual(mean, 1.7, places=6)
        self.assertAlmostEqual(leg, 1.7, places=6)
        self.assertEqual(set(per), {"leg.L", "leg.R", "arm.L", "arm.R"})

    def test_save_and_load_round_trip(self):
        src, dst = humanoid(1.0), humanoid(1.0)
        t, q, s = pose_of(src, {"head": R.from_euler("y", 20, degrees=True)})
        res = T.retarget(src, t, q, s, dst, ratio=1.0)
        with tempfile.TemporaryDirectory() as d:
            res.save(os.path.join(d, "c.npz"))
            back = T.Retargeted.load(os.path.join(d, "c.npz"))
        np.testing.assert_allclose(back["q"], res.q)
        self.assertEqual(back["names"], dst.names)


class FigaTests(unittest.TestCase):
    def test_tracks_are_sampled_per_axis_and_untracked_axes_keep_the_rest_euler(self):
        rig = humanoid(1.0)
        rig.rest_euler = np.zeros((len(rig), 3))
        rig.rest_euler[rig.roles["head"]] = [0.0, 0.3, 0.0]
        rig.q[rig.roles["head"]] = T.hsd_euler([0.0, 0.3, 0.0]).as_quat()[0]
        j = rig.roles["head"]
        tree = {"frames": 4.0, "joints": [[] for _ in range(len(rig))]}
        # ROTX 0 -> 1 rad linearly over 4 frames (LIN with wait 4, then the end key); TRAY constant 2
        tree["joints"][j] = [dict(type=1, start=0, keys=[(T.F.LIN, 0.0, None, 4), (T.F.LIN, 1.0, None, None)]),
                             dict(type=6, start=0, keys=[(T.F.CON, 2.0, None, None)])]
        clip = T.FigaClip(tree)
        t, q, s = clip.sample(rig, np.array([0.0, 2.0, 4.0]))
        e = R.from_quat(q[:, j]).as_matrix()
        want = T.hsd_euler(np.array([[0, 0.3, 0], [0.5, 0.3, 0], [1.0, 0.3, 0]])).as_matrix()   # Y stays at its rest 0.3
        np.testing.assert_allclose(e, want, atol=1e-6)
        np.testing.assert_allclose(t[:, j, 1], 2.0)
        self.assertEqual(clip.frames, 4.0)
        self.assertEqual(len(T.sample_frames(clip)), 5)


class HitboxTests(unittest.TestCase):
    @staticmethod
    def words(slot=0, joint=55, damage=11, size=3.5, x=3.0, y=0.5, z=-0.25, angle=361, kbg=100, fkb=0, bkb=12, elem=0, shield=0):
        q = lambda v: int(round(v * 256)) & 0xFFFF
        w0 = (11 << 26) | (slot << 23) | (joint << 11) | damage
        w1 = (int(size * 256) << 16) | q(x)
        w2 = (q(y) << 16) | q(z)
        w3 = (angle << 23) | (kbg << 14) | (fkb << 5) | 0x13                       # 0x13: bits the Geno command does not name
        w4 = (bkb << 23) | (elem << 18) | ((shield & 255) << 10) | 0x8B
        return [w0, w1, w2, w3, w4]

    def test_decode_and_reencode_keep_every_bit(self):
        w = self.words()
        hb = T.decode_hitbox(w)
        self.assertEqual((hb["slot"], hb["joint"], hb["damage"], hb["angle"], hb["kbg"], hb["bkb"]), (0, 55, 11, 361, 100, 12))
        self.assertEqual((hb["size"], hb["x"], hb["y"], hb["z"]), (3.5, 3.0, 0.5, -0.25))
        self.assertEqual(T.hitbox_words(hb), w)

    def test_new_joint_and_scale(self):
        hb = T.decode_hitbox(self.words())
        w = T.hitbox_words(hb, joint=9, scale=0.5)
        out = T.decode_hitbox(w)
        self.assertEqual((out["joint"], out["size"], out["x"], out["y"], out["z"]), (9, 1.75, 1.5, 0.25, -0.125))
        self.assertEqual(w[3], hb["raw"][3])                                         # angle/knockback/unnamed bits untouched
        self.assertEqual(w[4], hb["raw"][4])
        with self.assertRaises(ValueError):
            T.hitbox_words(hb, scale=100)

    def test_sphere_keeps_its_fraction_along_the_bone_and_scales_across_it(self):
        src, dst = humanoid(1.0), humanoid(2.0)
        # source shin: child (foot) is 2 below -> bone axis -Y in the (identity-rotation) local frame; a sphere half way along and 0.5 off in X
        hb = T.decode_hitbox(self.words(x=0.5, y=-1.0, z=0.0, size=2.0))
        out = T.retarget_hitbox(hb, src, dst, src.roles["lower_leg.R"], dst.roles["lower_leg.R"], 2.0)
        np.testing.assert_allclose([out["x"], out["y"], out["z"]], [1.0, -2.0, 0.0], atol=1e-9)    # 2x: half way along a 4-long bone, 1.0 across
        self.assertEqual(out["size"], 4.0)
        self.assertEqual(out["joint"], dst.roles["lower_leg.R"])

    def test_across_part_follows_a_rotated_bone_axis(self):
        src = humanoid(1.0)
        dst = humanoid(1.0)
        dst.t[dst.roles["foot.R"]] = [2.0, 0.0, 0.0]                                # the destination shin points along +X instead
        hb = T.decode_hitbox(self.words(x=0.0, y=-1.0, z=0.5))
        out = T.retarget_hitbox(hb, src, dst, src.roles["lower_leg.R"], dst.roles["lower_leg.R"], 1.0)
        c = np.array([out["x"], out["y"], out["z"]])
        self.assertAlmostEqual(c @ [1, 0, 0], 1.0, places=6)                         # half of the 2-long bone
        self.assertAlmostEqual(np.linalg.norm(c - (c @ [1, 0, 0]) * np.array([1, 0, 0])), 0.5, places=6)

    def test_decode_script_timeline(self):
        try:
            from tools.geno import script  # needs the game checkout's headers
        except Exception as e:  # noqa: BLE001
            self.skipTest("geno script tables unavailable: %s" % e)
        lines = ["wait_until 6", "hitbox slot=0 joint=3 damage=5 size=2 x=1 y=0 z=0 angle=45 kbg=90 fkb=0 bkb=20",
                 "wait 12", "clear_hitboxes", "wait_until 29", "iasa"]
        text = chr(10).join(lines) + chr(10)
        words = script.assemble(text, {})
        ev = T.decode_script(words)
        kinds = [(e["frame"], e["kind"]) for e in ev]
        self.assertIn((6, "hitbox"), kinds)
        self.assertIn((29, "iasa"), kinds)
        hb = next(e for e in ev if e["kind"] == "hitbox")
        self.assertEqual((hb["damage"], hb["joint"], hb["size"]), (5, 3, 2.0))


def minimal_glb(rig):
    nodes = [{"name": n, "translation": rig.t[i].tolist(), "rotation": rig.q[i].tolist(), "scale": [1, 1, 1]} for i, n in enumerate(rig.names)]
    for i, p in enumerate(rig.parents):
        if p >= 0:
            nodes[p].setdefault("children", []).append(i)
    doc = {"asset": {"version": "2.0"}, "nodes": nodes, "scenes": [{"nodes": [0]}], "skins": [{"joints": list(range(len(nodes)))}],
           "buffers": [{"byteLength": 4}], "bufferViews": [], "accessors": []}
    js = json.dumps(doc).encode()
    js += b" " * (-len(js) % 4)
    blob = b"\0\0\0\0"
    return struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(blob)) + struct.pack("<II", len(js), 0x4E4F534A) + js + \
        struct.pack("<II", len(blob), 0x004E4942) + blob


class GlbTests(unittest.TestCase):
    def test_rig_from_glb_and_inject_animation(self):
        dst = humanoid(1.0, names={"hips": "b_hips"})
        roles = {name: role for role, i in dst.roles.items() if role != "translation" for name in [dst.names[i]]}
        with tempfile.TemporaryDirectory() as d:
            a, b = os.path.join(d, "a.glb"), os.path.join(d, "b.glb")
            open(a, "wb").write(minimal_glb(dst))
            rig = T.rig_from_glb(a, roles)
            self.assertEqual(rig.names, dst.names)
            self.assertEqual(rig.roles["hips"], dst.roles["hips"])
            src = humanoid(1.0)
            t, q, s = pose_of(src, {"head": R.from_euler("y", 30, degrees=True)})
            res = T.retarget(src, np.repeat(t, 3, 0), np.repeat(q, 3, 0), np.repeat(s, 3, 0), rig, ratio=1.0)
            T.inject_glb_animation(a, b, "Clip", res)
            raw = open(b, "rb").read()
            n = struct.unpack_from("<I", raw, 12)[0]
            doc = json.loads(raw[20:20 + n])
            an = doc["animations"][0]
            self.assertEqual(an["name"], "Clip")
            self.assertEqual(len(an["channels"]), len(rig) + 1)                       # a rotation per joint + the pelvis translation
            acc = doc["accessors"][an["samplers"][0]["input"]]
            self.assertEqual(acc["count"], 3)


if __name__ == "__main__":
    unittest.main()
