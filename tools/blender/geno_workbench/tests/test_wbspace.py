import math
import pytest
import wbspace as W

I12 = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0]


def roty(deg, t=(0, 0, 0)):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return W.mat4_from_12([c, 0, s, t[0], 0, 1, 0, t[1], -s, 0, c, t[2]])


def close(a, b, eps=1e-9):
    return all(abs(x - y) <= eps for x, y in zip(a, b))


def test_point_axes():
    assert W.to_blender_point((1, 2, 3)) == (1, -3, 2)
    assert W.from_blender_point(W.to_blender_point((1, 2, 3))) == (1, 2, 3)


def test_rotation_converts_to_blender_axes():
    # engine R_y(+90) maps forward +Z to +X; in Blender forward is -Y.
    b = W.to_blender_matrix(roty(90))
    assert close(W.apply_point(b, (0, -1, 0)), (1, 0, 0))


def test_affine_inverse_roundtrip():
    m = roty(33, (4, -2, 7))
    prod = W.mul(m, W.affine_inverse(m))
    for i in range(4):
        for j in range(4):
            assert abs(prod[i][j] - (1.0 if i == j else 0.0)) < 1e-9


def test_singular_inverse_raises():
    with pytest.raises(ValueError):
        W.affine_inverse(W.mat4_from_12([0] * 12))


def test_world_to_model_undoes_root():
    root = roty(90, (-12.5, 0, 0))
    world = W.apply_point(root, (0, 5, 3))
    assert close(W.world_to_model(root, world), (0, 5, 3))


def test_facing_flip_roundtrip():
    for facing in (1, -1):
        root = roty(90 * facing, (7, 0, 0))
        local = (1.5, 8.0, -2.0)
        world = W.apply_point(root, local)
        assert close(W.world_to_model(root, world), local)


def test_schema1_rejected():
    info = {"bones": [{"joint": 1, "parent": 0, "pos": {"x": 0, "y": 0, "z": 0}}]}
    with pytest.raises(W.SchemaError, match="schema 2 needed"):
        W.check_schema(info)
    with pytest.raises(W.SchemaError):
        W.bone_matrices({"schema": 2, "bones": [{"joint": 1, "parent": 0}]})


def test_bone_matrices_and_root():
    info = {"schema": 2, "bones": [{"joint": 3, "parent": 0, "mtx": I12}],
            "root": {"joint": 0, "mtx": I12}}
    assert W.bone_matrices(info)[3][0][0] == 1
    assert W.root_matrix(info)[3] == (0, 0, 0, 1)


def test_mirrored_joint_is_detected():
    assert W.is_mirrored(W.mat4_from_12([-1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0]))
    assert not W.is_mirrored(W.mat4_from_12(I12))


def test_affine_inverse_with_scale_and_shear():
    m = W.mat4_from_12([2, 1, 0, 4, 0, 3, 1, -2, 0, 0, 4, 7])
    point = (-1.0, 2.0, 0.5)
    assert close(W.apply_point(W.affine_inverse(m), W.apply_point(m, point)), point)
