import wbspace as W
import fake_engine as F


def test_plan_shape():
    p = F.synthetic_plan()
    assert [j["index"] for j in p["joints"]] == list(range(9)) and p["joints"][0]["synth"] is True


def test_schema2_frame_has_matrices_and_root():
    info = F.synthetic_provider("jab", 6)
    assert info["schema"] == 2 and len(info["bones"]) == 9
    m = W.bone_matrices(info)
    assert set(m) == set(range(9)) and "mtx" in info["root"]


def test_hitbox_active_window():
    assert F.synthetic_provider("jab", 4)["hitboxes"] == []
    assert len(F.synthetic_provider("jab", 6)["hitboxes"]) == 1
    assert F.synthetic_provider("jab", 9)["hitboxes"] == []


def test_hitbox_world_matches_bone_chain():
    info = F.synthetic_provider("jab", 6)
    hand = W.bone_matrices(info)[8]
    expect = W.apply_point(hand, (0, 0, 1))
    w = info["hitboxes"][0]["world"]
    assert max(abs(expect[0] - w["x"]), abs(expect[1] - w["y"]), abs(expect[2] - w["z"])) < 1e-6


def test_facing_changes_root_not_local_geometry():
    a, b = F.synthetic_provider("wait", 1, facing=1), F.synthetic_provider("wait", 1, facing=-1)
    ra, rb = W.root_matrix(a), W.root_matrix(b)
    pa = W.world_to_model(ra, tuple(W.bone_matrices(a)[8][i][3] for i in range(3)))
    pb = W.world_to_model(rb, tuple(W.bone_matrices(b)[8][i][3] for i in range(3)))
    assert max(abs(x - y) for x, y in zip(pa, pb)) < 1e-9


def test_pose_changes_with_frame():
    p1 = F.synthetic_provider("jab", 1); p9 = F.synthetic_provider("jab", 9)
    assert W.bone_matrices(p1)[8] != W.bone_matrices(p9)[8]
