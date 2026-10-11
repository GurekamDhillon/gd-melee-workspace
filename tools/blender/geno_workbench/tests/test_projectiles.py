import copy
import json
import math
from pathlib import Path

import pytest

import projectiles as P

ROOT = Path(__file__).resolve().parents[4]
GOKU = ROOT / "ports" / "goku-xv2" / "gameplay.json"


def goku_articles():
    return P.articles_of(json.loads(GOKU.read_text(encoding="utf-8")))


def test_goku_has_articles():
    arts = goku_articles()
    assert len(arts) >= 5 and arts[0]["name"] == "KameTap"


@pytest.mark.parametrize("i", range(5))
def test_flatten_unflatten_is_identity(i):
    art = goku_articles()[i]
    out = P.unflatten(art, P.flatten(art))
    assert out == art and P.canonical(out) == P.canonical(art)
    assert P.diff_ops(art, out) == []


def test_edit_only_changed_leaf():
    art = goku_articles()[0]
    flat = P.flatten(art)
    flat["velocity/#0"] = 5.5
    flat["hitboxes"][1]["damage"] = 9
    new = P.unflatten(art, flat)
    ops = P.diff_ops(art, new)
    assert ops == [
        {"op": "set", "path": "velocity/#0", "value": 5.5},
        {"op": "set", "path": "hitboxes/#1/damage", "value": 9.0},
    ] or [o["path"] for o in ops] == ["velocity/#0", "hitboxes/#1/damage"]
    assert P.apply_ops(art, ops) == new


def test_default_value_not_written():
    art = {"name": "A", "lifetime": 30}
    flat = P.flatten(art)
    flat["gravity"] = 0.0  # the default of an absent key
    assert P.unflatten(art, flat) == art
    flat["gravity"] = 0.2
    assert P.unflatten(art, flat)["gravity"] == 0.2


def test_hitbox_add_remove_ops():
    art = {"name": "A", "hitboxes": [{"damage": 3}]}
    flat = P.flatten(art)
    flat["hitboxes"].append(dict(flat["hitboxes"][0]))
    flat["hitboxes"][1]["offset/#2"] = -3.0
    new = P.unflatten(art, flat)
    ops = P.diff_ops(art, new)
    assert ops and ops[0]["op"] == "insert" and ops[0]["path"] == "hitboxes"
    assert P.apply_ops(art, ops) == new
    back = P.diff_ops(new, art)
    assert back == [{"op": "remove", "path": "hitboxes", "at": 1}]
    assert P.apply_ops(new, back) == art


def test_unknown_keys_survive():
    art = {"name": "A", "future_key": {"x": [1, 2]}, "children": [{"article": 1}], "hitboxes": [{"damage": 3, "mystery": 7}]}
    flat = P.flatten(art)
    flat["lifetime"] = 10
    new = P.unflatten(art, flat)
    assert new["future_key"] == art["future_key"] and new["children"] == art["children"]
    assert new["hitboxes"][0]["mystery"] == 7 and new["lifetime"] == 10


def test_spawn_arg_roundtrip():
    for a, v, ang in [(3, 0, 0), (5, 2, -15), (255, 255, 90), (0, 1, -32768)]:
        assert P.decode_spawn_arg(P.encode_spawn_arg(a, v, ang)) == (a, v, ang)
    assert P.decode_spawn_arg(3) == (3, 0, 0)


def test_straight_flight():
    art = {"lifetime": 10, "velocity": [2.0, 0], "spawn": [3, 4]}
    pts = P.trajectory(art, base=(10, 20), facing=1)
    assert pts[0] == (13, 24) and pts[10] == (33, 24) and len(pts) == 11
    left = P.trajectory(art, base=(10, 20), facing=-1)
    assert left[0] == (7, 24) and left[10] == (-13, 24)


def test_angle_and_gravity():
    art = {"lifetime": 4, "velocity": [1.0, 0], "angle": 90, "gravity": 0.5}
    pts = P.trajectory(art)
    # v0=(0,1); step: vy = 1-0.5=.5 -> y .5, then 0, -.5, -1
    ys = [round(p[1], 6) for p in pts]
    assert ys == [0, 0.5, 0.5, 0.0, -1.0] or ys == [0, 0.5, 0.5, 0.0, -1.0]
    assert abs(pts[1][0]) < 1e-9


def test_max_fall_and_speed_cap():
    art = {"lifetime": 6, "velocity": [0, 0], "gravity": 1, "max_fall": 2.5}
    ys = [p[1] for p in P.trajectory(art)]
    assert ys == [0, -1, -3, -5.5, -8, -10.5, -13]
    cap = {"lifetime": 3, "velocity": [10, 0], "max_speed": 4}
    assert P.trajectory(cap)[3][0] == pytest.approx(12.0)


def test_brake_to_min_speed():
    art = {"lifetime": 6, "velocity": [3.0, 0], "accel": -1.0, "min_speed": 1.0}
    xs = [p[0] for p in P.trajectory(art)]
    assert xs == pytest.approx([0, 2, 3, 4, 5, 6, 7])


def test_homing_turns_toward_target():
    art = {"lifetime": 3, "velocity": [1.0, 0], "homing": {"turn": 30, "range": 0, "delay": 0}}
    pts = P.trajectory(art, target=(0, 100))
    # 30 degrees a frame toward straight up
    assert pts[1][1] == pytest.approx(math.sin(math.radians(30)))
    assert pts[3][1] > pts[1][1] > 0


def test_hitbox_window_and_ghost():
    art = {"lifetime": 8, "velocity": [1, 0], "hitboxes": [
        {"damage": 5, "size": 2, "offset": [1, 0.5, 0], "start": 3, "end": 5},
        {"damage": 5, "size": 1, "start": 1, "end": 0}]}
    assert [P.hitbox_live(art, 0, n) for n in range(0, 9)] == [False, False, False, True, True, True, False, False, False]
    assert P.hitbox_live(art, 1, 8) and not P.hitbox_live(art, 1, 9)
    g = P.ghost_at(art, spawn_frame=10, frame=14, base=(0, 0))
    assert g["life"] == 4 and g["root"] == (4.0, 0.0)
    assert g["hitboxes"][0][:3] == (5.0, 0.5, 2.0) and len(g["hitboxes"]) == 2
    assert P.ghost_at(art, 10, 9)["life"] is None and P.ghost_at(art, 10, 19)["life"] is None
    assert P.ghost_at(art, 10, 18)["life"] == 8


def test_spawn_variants_and_extra_angle():
    art = {"lifetime": 2, "velocity": [1.0, 0], "spawn": [1, 1], "spawns": [[5, 5], [6, 6], [7, 7]]}
    assert P.spawn_offset(art, 0) == (5, 5) and P.spawn_offset(art, 2) == (7, 7) and P.spawn_offset(art, 9) == (5, 5)
    vx, vy = P.initial_velocity({"velocity": [2, 0]}, 1, 90)
    assert (round(vx, 6), round(vy, 6)) == (0, 2)
