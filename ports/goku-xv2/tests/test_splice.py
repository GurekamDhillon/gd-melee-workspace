"""Splice recipes (tools/splice.py): synthetic clips only, no XV2 or disc data."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.spatial.transform import Rotation

PORT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PORT / "tools"))
sys.path.insert(0, str(PORT.parents[1]))
import splice as S  # noqa: E402

NAMES = ["b_C_Base", "b_C_Pelvis", "b_C_Spine1", "b_L_Arm1", "b_R_Arm1", "b_L_Leg1", "b_R_Leg1"]
PARENTS = [-1, 0, 1, 2, 2, 1, 1]
M = np.diag([-1., 1., 1.])


def quat(axis, deg):
    return Rotation.from_euler(axis, np.radians(deg)).as_quat()


def mkrig(asym_rest=False):
    rest = np.tile([0., 0., 0., 1.], (len(NAMES), 1))
    if asym_rest:                                   # mirrored limb frames: R = M L M
        rest[3] = quat("z", 30)
        rest[4] = Rotation.from_matrix(M @ Rotation.from_quat(rest[3]).as_matrix() @ M).as_quat()
    return S.Rig(list(NAMES), list(PARENTS), rest)


def ramp_clip(rig, n=10, bone="b_C_Spine1", axis="x", per=10.0, hips=None):
    rot = {nm: np.tile(rig.rest_q[i], (n, 1)) for i, nm in enumerate(rig.names)}
    rot[bone] = np.stack([quat(axis, per * f) for f in range(n)])
    h = np.zeros((n, 3)) if hips is None else hips
    return S.Clip(rot, h, np.zeros((n, 3)))


def resolver(**clips):
    return lambda ref: S.ArraySource(clips[ref], ref)


def angle(a, b):
    return float(S.angle_between(np.asarray(a), np.asarray(b)))


def test_segment_crop_forward_back_speed():
    rig = mkrig()
    src = S.ArraySource(ramp_clip(rig), "c")
    res = resolver(c=src.clip)
    out, rep = S.bake("t", {"row": "X", "segments": [{"clip": "c", "from": 2, "to": 5}]}, res, rig)
    assert out.n == 4 and rep["frames"] == 4
    for i, f in enumerate(range(2, 6)):
        assert angle(out.rot["b_C_Spine1"][i], quat("x", 10 * f)) < 1e-6
    back, _ = S.bake("t", {"row": "X", "segments": [{"clip": "c", "from": 5, "to": 2}]}, res, rig)
    assert angle(back.rot["b_C_Spine1"][0], quat("x", 50)) < 1e-6 and angle(back.rot["b_C_Spine1"][3], quat("x", 20)) < 1e-6
    fast, _ = S.bake("t", {"row": "X", "segments": [{"clip": "c", "from": 0, "to": 8, "speed": 2}]}, res, rig)
    assert fast.n == 5 and angle(fast.rot["b_C_Spine1"][4], quat("x", 80)) < 1e-6
    slow, _ = S.bake("t", {"row": "X", "segments": [{"clip": "c", "from": 0, "to": 2, "speed": 0.5}]}, res, rig)
    assert slow.n == 5 and angle(slow.rot["b_C_Spine1"][1], quat("x", 5)) < 1e-6      # fractional frames interpolate


def test_out_of_range_is_clamped_and_reported():
    rig = mkrig()
    out, rep = S.bake("t", {"row": "X", "segments": [{"clip": "c", "from": 8, "to": 12}]}, resolver(c=ramp_clip(rig)), rig)
    assert out.n == 5 and rep["notes"] and "outside the source" in rep["notes"][0]
    assert angle(out.rot["b_C_Spine1"][4], quat("x", 90)) < 1e-6


def test_blend_inserts_frames_and_is_continuous():
    rig = mkrig()
    a = ramp_clip(rig, 4, "b_C_Spine1", "x", 0.0)                                       # held rest
    b = ramp_clip(rig, 4, "b_C_Spine1", "x", 0.0)
    b.rot["b_C_Spine1"][:] = quat("x", 80)
    b.hips[:] = [5., 2., -3.]
    rec = {"row": "X", "blend": 3, "segments": [{"clip": "a", "from": 0, "to": 3}, {"clip": "b", "from": 0, "to": 3}]}
    out, rep = S.bake("t", rec, resolver(a=a, b=b), rig)
    assert out.n == 4 + 3 + 4 == S.recipe_length(rec)
    seam = rep["seams"][0]
    assert abs(seam["raw_jump_deg"] - 80) < 1e-4 and seam["blend"] == 3 and seam["pop"] is True        # an 80 degree jump eased over 3 frames still steps 40 degrees per frame: reported as a pop
    # monotone ease: the spine angle never decreases through the transition, and each step is under the raw jump
    ang = [angle(out.rot["b_C_Spine1"][i], quat("x", 0)) for i in range(3, 8)]
    assert all(x <= y + 1e-9 for x, y in zip(ang, ang[1:])) and abs(ang[-1] - 80) < 1e-4
    assert max(np.diff(ang)) < 80 * 0.5
    assert seam["max_step_deg"] <= 80 * 0.5 + 1e-6
    # translation: x/z are shifted onto the previous pose (no pop), y blends
    assert np.allclose(out.hips[7][[0, 2]], out.hips[3][[0, 2]]) and np.allclose(out.hips[-1][[0, 2]], 0.)
    assert out.hips[7][1] == pytest.approx(2.0) and 0. < out.hips[4][1] < out.hips[6][1] < 2.0
    assert seam["translation_before_fix"]["hips_xz"] == pytest.approx(np.hypot(5., 3.))


def test_blend_zero_and_per_segment_override():
    rig = mkrig()
    a, b = ramp_clip(rig, 3), ramp_clip(rig, 3)
    rec = {"row": "X", "blend": 3, "segments": [{"clip": "a", "from": 0, "to": 2}, {"clip": "b", "from": 0, "to": 2, "blend": 0}]}
    out, _ = S.bake("t", rec, resolver(a=a, b=b), rig)
    assert out.n == 6 == S.recipe_length(rec)


def test_pop_is_flagged_without_blend():
    rig = mkrig()
    a = ramp_clip(rig, 3, per=0.0)
    b = ramp_clip(rig, 3, per=0.0)
    b.rot["b_C_Spine1"][:] = quat("x", 120)
    out, rep = S.bake("t", {"row": "X", "segments": [{"clip": "a", "from": 0, "to": 2}, {"clip": "b", "from": 0, "to": 2, "blend": 0}]}, resolver(a=a, b=b), rig)
    assert rep["seams"][0]["pop"] and not rep["ok"]


@pytest.mark.parametrize("asym", [False, True])
def test_mirror_swaps_limbs_and_negates_x(asym):
    rig = mkrig(asym)
    clip = ramp_clip(rig, 6, "b_L_Arm1", "z", 12.0)
    clip.rot["b_L_Arm1"] = np.stack([(Rotation.from_quat(quat("z", 12 * f)) * Rotation.from_quat(rig.rest_q[3])).as_quat() for f in range(6)])
    clip.rot["b_R_Leg1"] = np.stack([quat("x", 7 * f) for f in range(6)])
    clip.hips = np.array([[1., 2., 3.]] * 6) * np.arange(1, 7)[:, None]
    clip.root = np.array([[0.5, 0., 1.]] * 6)
    out = S.mirror(clip, rig)
    # the L arm's motion now drives the R arm, as the mirror image
    for f in range(6):
        dl = Rotation.from_quat(clip.rot["b_L_Arm1"][f]) * Rotation.from_quat(rig.rest_q[3]).inv()          # world delta (arm parent is identity-rest)
        want = M @ dl.as_matrix() @ M @ Rotation.from_quat(rig.rest_q[4]).as_matrix()
        assert angle(out.rot["b_R_Arm1"][f], Rotation.from_matrix(want).as_quat()) < 1e-6
    # the old R arm (rest only) and the new L arm are both at their own rest
    assert angle(out.rot["b_L_Arm1"][3], rig.rest_q[3]) < 1e-6
    # the R leg's x-rotation lands on the L leg as a x-rotation of the same angle (axis x lies in the plane's normal: pseudo-vector, so the sign is kept)
    want_leg = Rotation.from_matrix(M @ Rotation.from_quat(clip.rot["b_R_Leg1"][5]).as_matrix() @ M).as_quat()
    assert angle(out.rot["b_L_Leg1"][5], want_leg) < 1e-6
    assert angle(out.rot["b_R_Leg1"][5], rig.rest_q[6]) < 1e-6
    # translations: x negated, y and z kept
    assert np.allclose(out.hips, clip.hips * [-1, 1, 1]) and np.allclose(out.root, clip.root * [-1, 1, 1])
    # involution
    back = S.mirror(out, rig)
    for nm in rig.names:
        assert S.angle_between(back.rot[nm], clip.rot[nm]).max() < 1e-6
    assert np.allclose(back.hips, clip.hips)


def test_mirror_centre_bone_flips_yaw_and_roll_not_pitch():
    rig = mkrig()
    clip = ramp_clip(rig, 2, "b_C_Spine1", "y", 30.0)
    out = S.mirror(clip, rig)
    assert angle(out.rot["b_C_Spine1"][1], quat("y", -30)) < 1e-6              # a turn to the left becomes a turn to the right
    pitch = S.mirror(ramp_clip(rig, 2, "b_C_Spine1", "x", 30.0), rig)
    assert angle(pitch.rot["b_C_Spine1"][1], quat("x", 30)) < 1e-6              # a forward lean stays a forward lean


def test_mirror_in_a_segment_and_sanity_report():
    rig = mkrig(True)
    src = ramp_clip(rig, 5, "b_L_Arm1", "z", 5.0)
    out, _ = S.bake("t", {"row": "X", "segments": [{"clip": "c", "from": 0, "to": 4, "mirror": True}]}, resolver(c=src), rig)
    assert np.allclose(out.hips, 0) and angle(out.rot["b_L_Arm1"][4], rig.rest_q[3]) < 1e-6
    sane = S.mirror_sanity(src, rig)
    assert sane["pairs"] == 2 and sane["unpaired"] == [] and sane["involution_error_deg"] < 1e-4


def test_mirror_scale_tracks_follow_the_partner():
    rig = mkrig()
    c = ramp_clip(rig, 3)
    c.scl["b_L_Leg1"] = np.tile([1.5, 1., 1.], (3, 1))
    out = S.mirror(c, rig)
    assert "b_R_Leg1" in out.scl and "b_L_Leg1" not in out.scl


def test_root_yaw_constant_and_ramp():
    rig = mkrig()
    base = ramp_clip(rig, 5, "b_C_Base", "x", 0.0)
    out, _ = S.bake("t", {"row": "X", "segments": [{"clip": "c", "from": 0, "to": 4, "root_yaw": 180}]}, resolver(c=base), rig)
    for f in range(5):
        assert angle(out.rot["b_C_Base"][f], quat("y", 180)) < 1e-6
    ramp, _ = S.bake("t", {"row": "X", "segments": [{"clip": "c", "from": 0, "to": 4, "root_yaw": 180, "yaw_ramp": True}]}, resolver(c=base), rig)
    assert angle(ramp.rot["b_C_Base"][0], quat("y", 0)) < 1e-6 and angle(ramp.rot["b_C_Base"][4], quat("y", 180)) < 1e-6
    mid = angle(ramp.rot["b_C_Base"][2], quat("y", 0))
    assert mid == pytest.approx(90.0, abs=1e-4)                                  # smoothstep is symmetric
    assert angle(out.rot["b_C_Spine1"][2], rig.rest_q[2]) < 1e-6                  # only the root bone turns


def test_hold_and_marks():
    rig = mkrig()
    rec = {"row": "X", "blend": 2, "segments": [{"clip": "c", "from": 0, "to": 3, "marks": {"hit": 2}, "hold": 2},
                                                 {"clip": "c", "from": 4, "to": 8, "speed": 2, "marks": {"hit": 6}}]}
    out, rep = S.bake("t", rec, resolver(c=ramp_clip(rig)), rig)
    assert out.n == S.recipe_length(rec) == (4 + 2) + 2 + 3
    assert rep["segments"][0]["marks"] == {"hit": 2} and rep["segments"][1]["out_start"] == 6 + 2 and rep["segments"][1]["marks"] == {"hit": 8 + 1}
    assert angle(out.rot["b_C_Spine1"][4], out.rot["b_C_Spine1"][3]) < 1e-9       # hold repeats the last pose
    assert S.hit_check(rep, [[0, 3], [8, 3]]) == []                          # both marks (f2, f9) sit inside a window
    assert len(S.hit_check(rep, [[0, 3]])) == 1                                 # only the f9 mark misses
    assert S.hit_check({"segments": [{"marks": {"hit": 30}}]}, [[5, 3]])


def test_retime_exact_length_and_endpoints():
    rig = mkrig()
    src = ramp_clip(rig, 10)
    out, rep = S.bake("t", {"row": "X", "frames": 17, "segments": [{"clip": "c", "from": 0, "to": 9}]}, resolver(c=src), rig)
    assert out.n == 17 and rep["frames"] == 17 and rep["frames_before_retime"] == 10
    assert angle(out.rot["b_C_Spine1"][0], quat("x", 0)) < 1e-6 and angle(out.rot["b_C_Spine1"][16], quat("x", 90)) < 1e-6
    assert S.recipe_length({"frames": 17, "segments": [{"clip": "c", "from": 0, "to": 9}]}) == 17
    shorter, _ = S.bake("t", {"row": "X", "frames": 4, "segments": [{"clip": "c", "from": 0, "to": 9}]}, resolver(c=src), rig)
    assert shorter.n == 4


def test_loop_eases_back_to_the_first_pose():
    rig = mkrig()
    src = ramp_clip(rig, 12, per=10.0)
    open_, rep0 = S.bake("t", {"row": "X", "segments": [{"clip": "c", "from": 0, "to": 11}]}, resolver(c=src), rig)
    assert open_.n == 12
    looped, rep = S.bake("t", {"row": "X", "loop": True, "loop_blend": 5, "segments": [{"clip": "c", "from": 0, "to": 11}]}, resolver(c=src), rig)
    assert looped.n == 12 and rep["loop"]["last_to_first_deg"] < 110 * 0.2
    assert rep["loop"]["last_to_first_deg"] < S.pose_jump(open_, 11, open_, 0)[0]
    assert rep["loop"]["bone"] == "b_C_Spine1"


def test_pad_to_holds_last_pose():
    rig = mkrig()
    c = ramp_clip(rig, 4)
    p = S.pad_to(c, 7)
    assert p.n == 7 and angle(p.rot["b_C_Spine1"][6], c.rot["b_C_Spine1"][3]) < 1e-9
    assert S.pad_to(c, 2).n == 4


def test_determinism():
    rig = mkrig(True)
    rec = {"row": "X", "blend": 3, "frames": 20, "loop": True, "segments": [
        {"clip": "a", "from": 0, "to": 7, "mirror": True, "marks": {"hit": 3}}, {"clip": "b", "from": 9, "to": 2, "speed": 1.5, "root_yaw": 90, "yaw_ramp": True, "hold": 2}]}
    a, b = ramp_clip(rig, 10, "b_L_Arm1", "z", 9.0), ramp_clip(rig, 10, "b_R_Leg1", "x", 4.0, hips=np.linspace(0, 1, 30).reshape(10, 3))
    o1, r1 = S.bake("t", rec, resolver(a=a, b=b), rig)
    o2, r2 = S.bake("t", rec, resolver(a=a.copy(), b=b.copy()), rig)
    assert json.dumps(r1, sort_keys=True, default=str) == json.dumps(r2, sort_keys=True, default=str)
    assert all(np.array_equal(o1.rot[k], o2.rot[k]) for k in o1.rot) and np.array_equal(o1.hips, o2.hips)


def test_scales_blend_with_the_segments():
    rig = mkrig()
    a, b = ramp_clip(rig, 3), ramp_clip(rig, 3)
    b.scl["b_L_Leg1"] = np.tile([1.8, 1., 1.], (3, 1))
    out, _ = S.bake("t", {"row": "X", "blend": 3, "segments": [{"clip": "a", "from": 0, "to": 2}, {"clip": "b", "from": 0, "to": 2}]}, resolver(a=a, b=b), rig)
    sx = out.scl["b_L_Leg1"][:, 0]
    assert sx[0] == 1.0 and sx[-1] == pytest.approx(1.8) and np.all(np.diff(sx) >= -1e-9) and sx[4] > 1.0


def test_recipe_validation():
    with pytest.raises(S.SpliceError):
        S.validate_recipe("x", {"row": "A", "segments": []})
    with pytest.raises(S.SpliceError):
        S.validate_recipe("x", {"segments": [{"clip": "a", "from": 0, "to": 1}]})
    with pytest.raises(S.SpliceError):
        S.validate_recipe("x", {"row": "A", "segments": [{"clip": "a", "from": 0, "to": 1, "bogus": 1}]})
    with pytest.raises(S.SpliceError):
        S.validate_recipe("x", {"row": "A", "segments": [{"clip": "a", "from": 0}]})


def test_lr_partner_matches_the_artist_roles():
    import xv2_to_artist as X
    for bone, role in X.ROLES.items():
        if role.endswith(".L"):
            assert X.ROLES[S.lr_partner(bone)] == role[:-2] + ".R", bone
        if role.endswith(".R") and bone.startswith("b_"):
            assert X.ROLES[S.lr_partner(bone)] == role[:-2] + ".L", bone
    assert S.lr_partner("b_C_Head") == "b_C_Head" and S.lr_partner("item_socket.R") == "item_socket.L"


def test_shipped_recipes_are_valid_and_examples_are_not_wired():
    doc = S.load()
    assert doc["recipes"]
    for name, r in doc["recipes"].items():
        S.validate_recipe(name, r)
        if r.get("example"):
            assert not r.get("wired"), name + ": an EXAMPLE must not be wired until the owner picks it"
        assert len(S.library_name(name)) <= 31
        assert S.recipe_length(r) > 0


# ---- the XV2 adapter (needs the local source IR, git-ignored; skipped on a fresh clone)

IR = PORT / "ir/goku.xv2.ir.json"
needs_ir = pytest.mark.skipif(not IR.exists() or not (PORT.parents[1] / "_build/goku-xv2/cross-port/AttackAirB/clip.npz").exists(),
                              reason="needs the local XV2 IR and the cross-port npz")


@pytest.fixture(scope="module")
def adapter():
    import xv2_to_artist as X
    source = X.Source(IR)
    return X, source, X.build_mesh(source, 20.)


def run_rows(X, source, mesh, tmp_path, wired):
    doc = json.loads((PORT / "splices.json").read_text())
    for r in doc["recipes"].values():
        r["wired"] = wired
    f = tmp_path / "splices.json"
    f.write_text(json.dumps(doc))
    old = S.SPLICES
    S.SPLICES = f
    try:
        rows = X.row_specs(source)
        out, rep = X.animations(source, mesh, rows)
    finally:
        S.SPLICES = old
    return rows, out, rep


@needs_ir
def test_splice_context_resolves_xv2_and_cross_port(adapter):
    X, source, mesh = adapter
    ctx = X.splice_context(source, mesh)
    assert ctx["rig"].names == list(mesh["names"]) and ctx["rig"].parents[0] == -1
    xv2 = ctx["resolve"]("GOK_ATC_004")
    c = xv2.sample(np.arange(5.))
    assert c.n == 5 and c.hips.shape == (5, 3) and "b_R_Arm1" in c.rot
    cp = ctx["resolve"]("melee:luigi/AttackAirB")
    assert cp.length == 29 and cp.clip.scl                      # the retargeted clip with its thigh-stretch tracks
    mm, mr = ctx["move_rows"]
    assert S.target_rows({"move": "utilt"}, mm, mr) == ["AttackHi3"] and S.target_rows({"row": "AttackAirB"}) == ["AttackAirB"]
    with pytest.raises(S.SpliceError):
        ctx["resolve"]("GOK_NO_SUCH_CLIP")


@needs_ir
def test_unwired_recipes_only_add_library_rows(adapter, tmp_path):
    X, source, mesh = adapter
    rows, out, rep = run_rows(X, source, mesh, tmp_path, False)
    base = X.row_specs(source)
    for target in ("AttackHi3", "AttackAirLw", "AttackAirB"):
        assert "splice" not in rows[target] and rows[target]["status"] == base[target]["status"]
    for name in S.load()["recipes"]:
        lib = S.library_name(name)
        assert lib in out and rep[lib]["splice"]["wired"] is False and out[lib]["frames"] == S.recipe_length(S.load()["recipes"][name])


@needs_ir
def test_wired_recipes_replace_rows_and_bair_keep_is_the_shipped_row(adapter, tmp_path):
    X, source, mesh = adapter
    import copy
    import fidelity
    _, base, _ = (None,) + X.animations(source, mesh, copy.deepcopy(X.row_specs(source)))
    rows, out, rep = run_rows(X, source, mesh, tmp_path, True)
    # the one-segment cross-port recipe must equal the shipped cross-port row bit for bit (rotations, hips, bone scales)
    a, b = base["AttackAirB"], out["AttackAirB"]
    assert a["frames"] == b["frames"] == 30
    assert all(S.angle_between(a["rotation"][k], b["rotation"][k]).max() < 1e-6 for k in a["rotation"])
    assert np.allclose(a["hips"], b["hips"]) and all(np.allclose(a["scale"][k], b["scale"][k]) for k in a["scale"])
    # a real splice replaces utilt, padded to the gameplay minimum, and the ledger calls it SPLICED
    assert out["AttackHi3"]["frames"] == rows["AttackHi3"]["frames"] >= S.recipe_length(S.load()["recipes"]["utilt_windup_strike"])
    assert max(float(S.angle_between(base["AttackHi3"]["rotation"][k], out["AttackHi3"]["rotation"][k]).max()) for k in b["rotation"]) > 10
    status, how = fidelity.classify({"source": rep["AttackHi3"], "status": "own", "clip": "x"})
    assert status == "SPLICED" and "utilt_windup_strike" in how
    assert fidelity.classify({"source": rep["AttackAirB"], "status": "own", "clip": "x"})[0] == "SPLICED"
    assert fidelity.classify({"source": base and {"status": "x", "frames": 3}, "status": "own", "clip": "x"})[0] != "SPLICED"
