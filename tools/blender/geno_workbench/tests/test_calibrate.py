import math
import wbspace as W


def rot(axis, deg, t=(0, 0, 0)):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    if axis == "x":
        r = [1, 0, 0, t[0], 0, c, -s, t[1], 0, s, c, t[2]]
    elif axis == "y":
        r = [c, 0, s, t[0], 0, 1, 0, t[1], -s, 0, c, t[2]]
    else:
        r = [c, -s, 0, t[0], s, c, 0, t[1], 0, 0, 1, t[2]]
    return W.mat4_from_12(r)


def near(a, b, eps=1e-9):
    return all(abs(a[i][j] - b[i][j]) < eps for i in range(4) for j in range(4))


def test_calibration_recovers_bone_frame_offsets():
    # local bone frames L (model space), fixed Blender-only offsets R, world placements W0/W1
    L0 = {1: rot("z", 0), 2: rot("y", 20, (0, 0, 5)), 3: rot("x", -35, (1, 0, 8))}
    R = {1: rot("x", 90), 2: rot("z", 15), 3: rot("y", -50)}
    W0 = rot("z", 90, (10, -3, 0))
    engine_rest = {j: W.mul(W0, L0[j]) for j in L0}
    blender_rest = {j: W.mul(L0[j], R[j]) for j in L0}
    cal = W.calibrate_offsets(engine_rest, blender_rest, root_joint=1)
    assert near(cal.w0, W0)
    L1 = {1: rot("z", 0), 2: rot("y", 55, (0, 0, 5)), 3: rot("x", 10, (1, 0, 8))}
    W1 = rot("z", -90, (-4, 2, 0))
    for j in L1:
        engine = W.mul(W1, L1[j])
        assert near(W.target_matrix(engine, cal.k[j]), W.mul(W1, W.mul(L1[j], R[j])))


def test_scale_is_reported():
    L = {1: rot("z", 0)}
    big = tuple(tuple(v * 2 if i < 3 and j < 3 else v for j, v in enumerate(row)) for i, row in enumerate(rot("z", 0)))
    cal = W.calibrate_offsets({1: big}, {1: L[1]}, root_joint=1)
    assert abs(cal.scale - 2.0) < 1e-9
