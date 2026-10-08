"""Tests for the Geno artist pipeline. Pure-Python tests always run; the Blender ones need Blender (BLENDER or the usual install),
the build ones also need the .NET SDK + HSDLib (GW_FIGHTERBUILD) and the game checkout (GW_MELEE).

    python -m pytest tools/geno/artist -q
"""
import filecmp
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)
from tools.geno.artist import assemble, model, pipeline, spec, validate  # noqa: E402
from tools.geno.artist.model import AF  # noqa: E402


def blender():
    try:
        return pipeline.blender_exe()
    except Exception:  # noqa: BLE001
        return None


def game():
    g = spec.game_dir()
    return g if os.path.isdir(os.path.join(g, "pc", "geno", "mods", "vanilla-striker")) else None


def fighterbuild():
    try:
        from tools.geno.artist import convert
        return convert.fighterbuild_dll()
    except Exception:  # noqa: BLE001
        return None


class SpecTests(unittest.TestCase):
    def test_role_guess(self):
        g = spec.guess_role
        self.assertEqual(g("mixamorig:LeftArm"), "upper_arm.L")
        self.assertEqual(g("Pelvis"), "hips")
        self.assertEqual(g("Shin_R"), "lower_leg.R")
        self.assertEqual(g("thigh.L"), "upper_leg.L")
        self.assertIsNone(g("Arm"))               # sided role without a side: no guess
        self.assertIsNone(g("Wing3"))

    def test_roles_cover_parts(self):
        for r in spec.REQUIRED:
            self.assertIn(r, spec.ALL_ROLES)
        self.assertEqual(spec.canonical_role("upper_arm", "upperarm_L"), "upper_arm.L")
        self.assertEqual(spec.canonical_role("hips", "hips"), "hips")

    def test_clip_table(self):
        t = spec.clip_table()
        self.assertEqual(len(t["rows"]), 351)
        names = {r["name"] for r in t["rows"]}
        for p in t["prototype"]:
            self.assertIn(p, names)
        for r in t["rows"]:
            self.assertNotIn(r["name"], r.get("fallback", []))
        self.assertEqual(len(t["rows_sm"]), 296)
        self.assertEqual(sum(1 for r in t["rows"] if r.get("timing")), 32)

    def test_mario_joint_roles(self):
        m = spec.mario_joint_roles()
        self.assertEqual(m[0], "TopN")
        self.assertIn(m[9], ("hand.L",))


class AssembleTests(unittest.TestCase):
    def test_retarget_script(self):
        text = "# jab\nPUT ANIM_RATE 1.45\nwait 3\nhitbox slot=0 joint=9 damage=2 size=3.4 x=0 y=0 z=0 angle=361 kbg=100 fkb=0 bkb=0\nwait 1\nwait 2\n"
        out = assemble.retarget_script(text, {9: 20}, "jab1", {}, {}, 0.5, {"TopN": 0})
        self.assertIn("joint=20", out)
        self.assertIn("size=1.7", out)
        self.assertIn("PUT ANIM_RATE 1.0", out)
        out2 = assemble.retarget_script(text, {9: 20}, "jab1", {"jab1": {"0": {"joint": "TopN", "x": 2}}}, {"jab1": 1}, 1.0, {"TopN": 0})
        self.assertIn("joint=0", out2)
        self.assertIn("x=2", out2)
        self.assertIn("wait 4", out2)             # delay moves a frame in front of the hitbox
        self.assertIn("wait 1", out2.split("hitbox")[1])

    def test_delay_defaults(self):
        self.assertEqual(assemble.DEFAULT_DELAY["fsmash"], 1)


def mutate_glb(src, dst, fn):
    b = open(src, "rb").read()
    jl = struct.unpack_from("<I", b, 12)[0]
    g = json.loads(b[20:20 + jl])
    off = 20 + jl
    bl = struct.unpack_from("<I", b, off)[0]
    binary = bytearray(b[off + 8: off + 8 + bl])
    fn(g, binary)
    js = json.dumps(g).encode()
    js += b" " * (-len(js) % 4)
    total = 12 + 8 + len(js) + 8 + len(binary)
    open(dst, "wb").write(b"glTF" + struct.pack("<II", 2, total) + struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(binary), 0x004E4942) + bytes(binary))


@unittest.skipUnless(blender(), "Blender not found")
class StarterTests(unittest.TestCase):
    """The starter -> export -> validate chain, with a renamed skeleton (Pip's names) and deliberate mistakes."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="artist_test_")
        pip = os.path.join(ROOT, "ports", "geno-artist-samples", "pip")
        cls.dir = cls.tmp
        shutil.copy(os.path.join(pip, "fighter.json"), os.path.join(cls.tmp, "fighter.json"))
        shutil.copy(os.path.join(pip, "params.json"), os.path.join(cls.tmp, "params.json"))
        r = subprocess.run([blender(), "-b", "--python", os.path.join(ROOT, "tools", "geno", "artist", "blender", "make_starter.py"), "--",
                            "--out", os.path.join(cls.tmp, "pip.blend"), "--name", "Pip", "--params", os.path.join(cls.tmp, "params.json")],
                           capture_output=True, text=True)
        assert os.path.isfile(os.path.join(cls.tmp, "pip.blend")), r.stdout[-500:] + r.stderr[-500:]
        ok = pipeline.export_from_blend(os.path.join(cls.tmp, "fighter.json"), log=lambda *a: None, force=True)
        assert ok
        cls.glb = os.path.join(cls.tmp, "art", "pip.glb")
        cls.cfg = os.path.join(cls.tmp, "fighter.json")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def codes(self, cfg=None):
        r, f = validate.validate(cfg or self.cfg, measure=False)
        return r, {i["code"] for i in r.items if i["severity"] == validate.B}

    def variant(self, name, fn, drop_sidecar=False):
        d = os.path.join(self.tmp, name)
        os.makedirs(os.path.join(d, "art"), exist_ok=True)
        mutate_glb(self.glb, os.path.join(d, "art", "pip.glb"), fn)
        if not drop_sidecar:
            shutil.copy(self.glb + ".geno.json", os.path.join(d, "art", "pip.glb.geno.json"))
        cfg = json.load(open(self.cfg))
        cfg["art"] = {"glb": "art/pip.glb"}
        json.dump(cfg, open(os.path.join(d, "fighter.json"), "w"))
        return os.path.join(d, "fighter.json")

    def test_clean(self):
        r, blockers = self.codes()
        self.assertEqual(blockers, set(), [i for i in r.items if i["severity"] == validate.B])

    def test_roles_come_from_the_export_not_the_config(self):
        f = model.load(self.cfg)
        self.assertEqual(f.role_bone["hips"].name, "Pelvis")
        self.assertEqual(f.role_bone["upper_arm.L"].name, "Arm_L")
        self.assertEqual(f.role_bone["hips"].role_src, "sidecar")
        self.assertNotIn("roles", f.cfg)

    def test_missing_role(self):
        def fn(g, b):
            for n in g["nodes"]:
                if n["name"] == "Pelvis":
                    n["name"] = "Hipbone"
            for n in g["nodes"]:
                ex = n.get("extras")
        cfg = self.variant("norole", fn, drop_sidecar=True)
        r, blockers = self.codes(cfg)
        self.assertIn("ROLE_MISSING", blockers)
        item = [i for i in r.items if i["code"] == "ROLE_MISSING" and "'hips'" in i["where"]][0]
        self.assertIn("fighter.json roles", item["fix"])

    def test_bone_scale_and_armature_transform(self):
        def fn(g, b):
            for n in g["nodes"]:
                if n["name"] == "Skull":
                    n["scale"] = [2, 2, 2]
            arm = [n for n in g["nodes"] if "children" in n and "Origin" in [g["nodes"][c]["name"] for c in n["children"]]]
            for n in arm:
                n["translation"] = [0, 1, 0]
        r, blockers = self.codes(self.variant("scale", fn))
        self.assertIn("BONE_SCALE", blockers)
        bs = [i for i in r.items if i["code"] == "BONE_SCALE"][0]
        self.assertEqual(bs["where"], "bone 'Skull'")

    def test_influences_named_by_vertex(self):
        def fn(g, binary):
            prim = g["meshes"][0]["primitives"][0]
            for key, vals in (("JOINTS_0", None), ("WEIGHTS_0", None)):
                a = g["accessors"][prim["attributes"][key]]
                bv = g["bufferViews"][a["bufferView"]]
                o = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
                if key == "JOINTS_0":
                    dt = {5121: "u1", 5123: "<u2"}[a["componentType"]]
                    arr = np.frombuffer(binary, dtype=dt, count=a["count"] * 4, offset=o).copy()
                    arr[0:4] = [1, 2, 3, 4]
                    binary[o:o + arr.nbytes] = arr.tobytes()
                else:
                    arr = np.frombuffer(binary, dtype="<f4", count=a["count"] * 4, offset=o).copy()
                    arr[0:4] = [0.25, 0.25, 0.25, 0.25]
                    binary[o:o + arr.nbytes] = arr.tobytes()
        r, blockers = self.codes(self.variant("infl", fn))
        self.assertIn("INFLUENCES", blockers)
        it = [i for i in r.items if i["code"] == "INFLUENCES"][0]
        self.assertIn("vertices 0", it["where"])
        self.assertIn("Limit Total", it["fix"])

    def test_clip_name_and_fps(self):
        def fn(g, b):
            for an in g["animations"]:
                if an["name"] == "Attack11":
                    an["name"] = "attack_11"
            a2 = [an for an in g["animations"] if an["name"] == "Wait"][0]
            for s in a2["samplers"]:
                acc = g["accessors"][s["input"]]
                bv = g["bufferViews"][acc["bufferView"]]
                o = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
                t = np.frombuffer(b, dtype="<f4", count=acc["count"], offset=o).copy() * 2
                b[o:o + t.nbytes] = t.tobytes()
        r, blockers = self.codes(self.variant("clips", fn))
        self.assertIn("CLIP_FPS", blockers)
        um = [i for i in r.items if i["code"] == "CLIP_UNMAPPED"]
        self.assertTrue(any("'attack_11'" in i["where"] and "Attack11" in i["fix"] for i in um), um)

    def test_converter_runs_without_dotnet(self):
        from tools.geno.artist import convert
        f = model.load(self.cfg)
        out = os.path.join(self.tmp, "conv")
        plan, tris, lost = convert.write_mesh_and_plan(f, out)
        convert.write_bank(f, out)
        p = json.load(open(os.path.join(out, "plan.json")))
        self.assertEqual(p["joint_count"], 34)
        self.assertEqual(len(p["hurtboxes"]), 15)
        self.assertEqual(len(p["motion_rows"]), 351)
        self.assertEqual(p["unresolved"][0]["common_part"], "LHaveN")
        # every placeholder for a scripted move is at least as long as the script
        t = spec.clip_table()["by_name"]
        for r in p["motion_rows"]:
            tm = t[r["row"]].get("timing")
            if tm and r["clip"]:
                self.assertGreaterEqual(p["bank"]["clips"][r["clip"]]["frames"], tm["script_frames"], r["row"])

    @unittest.skipUnless(game() and fighterbuild(), "needs the game checkout and fighterbuild")
    def test_full_build_installs_an_isolated_mods_folder(self):
        out = os.path.join(self.tmp, "full")
        logs = []
        code, f = pipeline.build(self.cfg, out, log=logs.append)
        self.assertEqual(code, 0, "\n".join(logs[-12:]))
        mods = os.path.join(out, "mods")
        self.assertTrue(os.path.isfile(os.path.join(mods, "enabled.txt")))
        self.assertTrue(os.path.isfile(os.path.join(mods, "sample-pip", "files", "GnSamplePip_default.dat")))
        self.assertTrue(os.path.isfile(os.path.join(mods, "sample-pip", "geno.json")))
        self.assertTrue(any("Restart the game" in l for l in logs))

    def test_blender_selftest(self):
        base = os.path.join(self.tmp, "pip.blend")
        for part in ("checks", "bake"):
            r = subprocess.run([blender(), "-b", base, "--python", os.path.join(ROOT, "tools", "geno", "artist", "blender", "selftest.py"), "--", part],
                               capture_output=True, text=True)
            out = r.stdout
            self.assertNotIn("SELFTEST FAIL", out, out[-800:])
            self.assertIn("SELFTEST PASS", out, out[-800:])


COURIER = os.path.join(ROOT, "ports", "vanilla-original")


@unittest.skipUnless(os.path.isfile(os.path.join(COURIER, "out", "courier.glb")) and game(), "needs the Courier's built glb and the game checkout")
class CourierRegression(unittest.TestCase):
    def test_same_outputs_as_the_courier_converter(self):
        from tools.geno.artist import convert
        tmp = tempfile.mkdtemp(prefix="artist_courier_")
        try:
            old = os.path.join(tmp, "old")
            new = os.path.join(tmp, "new")
            tools = os.path.join(ROOT, "ports", "ir", "tools", "authored_fighter.py")
            for cmd in ("mesh", "anim"):
                r = subprocess.run([sys.executable, tools, cmd, COURIER, old], capture_output=True, text=True, env=dict(os.environ, GW_MELEE=spec.game_dir()))
                self.assertEqual(r.returncode, 0, r.stderr[-400:])
            f = model.load(os.path.join(COURIER, "fighter.json"))
            convert.write_mesh_and_plan(f, new)
            convert.write_bank(f, new)
            for n in sorted(os.listdir(old)):
                if n == "plan.json":
                    a, b = json.load(open(os.path.join(old, n))), json.load(open(os.path.join(new, n)))
                    a.pop("roles"), b.pop("roles")          # canonical role names differ on purpose; the engine reads neither
                    self.assertEqual(a, b)
                else:
                    self.assertTrue(filecmp.cmp(os.path.join(old, n), os.path.join(new, n), shallow=False), n)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
