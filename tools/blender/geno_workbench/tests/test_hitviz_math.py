import math

import hitviz_math as M


def test_knockback_matches_the_published_formula():
    # 10% damage hit, kbg 100, bkb 0, victim at 0%, weight 100: ((1 + 5) * 1 * 1.4 + 18) = 26.4
    assert abs(M.knockback(10, 100, 0, 0, 0, 100) - 26.4) < 1e-9
    # bkb adds, kbg scales the rest
    assert abs(M.knockback(10, 50, 30, 0, 0, 100) - (26.4 * 0.5 + 30)) < 1e-9
    # heavier victim -> less knockback; higher percent -> more
    assert M.knockback(10, 100, 0, 0, 0, 150) < M.knockback(10, 100, 0, 0, 0, 100)
    assert M.knockback(10, 100, 0, 0, 100, 100) > M.knockback(10, 100, 0, 0, 0, 100)


def test_set_knockback_ignores_percent_and_caps():
    a = M.knockback(8, 100, 0, 40, 0, 100)
    b = M.knockback(8, 100, 0, 40, 150, 100)
    assert a == b
    assert M.knockback(500, 500, 500, 0, 999, 50) == M.KB_CAP


def test_meteor_rule_is_the_decomp_range_and_excludes_sakurai():
    assert M.is_meteor(270) and M.is_meteor(230) and M.is_meteor(310)
    assert not M.is_meteor(229) and not M.is_meteor(311) and not M.is_meteor(361) and not M.is_meteor(45)
    assert M.classify_angle(361) == "sakurai"
    assert M.classify_angle(270) == "meteor"
    assert M.classify_angle(45) == "normal"
    assert M.classify_angle(365) == "special"


def test_direction_is_facing_aware():
    dx, dy = M.direction(45, 1)
    assert abs(dx - math.sqrt(0.5)) < 1e-9 and abs(dy - math.sqrt(0.5)) < 1e-9
    dx, dy = M.direction(45, -1)
    assert dx < 0 and dy > 0
    dx, dy = M.direction(270, 1)
    assert abs(dx) < 1e-9 and abs(dy + 1) < 1e-9          # a spike points straight down either way
    assert M.direction(135, 1)[0] < 0                      # >90 is backwards relative to facing


def test_sakurai_fan_and_ground_angle():
    low, high, resolved = M.angle_span(361, 20)
    assert (low, high) == (0.0, M.SAKURAI_GROUND_MAX_DEG) and resolved == 0.0   # below kb 32: flat
    assert M.sakurai_ground_degrees(88) == 44.0 and M.sakurai_ground_degrees(500) == 44.0
    assert 0 < M.sakurai_ground_degrees(60) < 44
    pts = M.fan_points(0, 44, 1, 10)
    assert pts[0] == (0.0, 0.0) and pts[-1] == (0.0, 0.0) and len(pts) == 9
    assert all(abs(math.hypot(*p) - 10) < 1e-9 for p in pts[1:-1])
    assert M.angle_span(365, 50)[2] is None


def test_arrow_length_scales_and_clamps():
    assert M.arrow_length(0) == M.ARROW_MIN
    assert M.arrow_length(100) < M.arrow_length(200)
    assert M.arrow_length(1e6) == M.ARROW_MAX


def test_slot_colours_are_ordered_by_lightness_with_room_between():
    lum = [M.luminance(M.slot_rgb(i)) for i in range(4)]
    assert lum == sorted(lum)
    assert all(b - a >= 0.15 for a, b in zip(lum, lum[1:]))
    assert M.slot_rgb(4) == M.slot_rgb(0)
    assert M.METEOR_RGB not in M.SLOT_RGB


def test_badges_and_label():
    assert M.badges({"element": 1, "damage": 5}) == ["fire"]
    assert M.badges({"element": 13, "damage": 5}) == ["darkness"]
    assert M.badges({"damage": 0}) == ["windbox"]
    assert "set kb 30" in M.badges({"fkb": 30, "damage": 4})
    assert "ground only" in M.badges({"hit_air": False, "hit_ground": True, "damage": 4})
    assert "air only" in M.badges({"hit_air": True, "hit_ground": False, "damage": 4})
    assert M.badges({"damage": 4, "shield_damage": 3}) == ["shield +3"]
    assert M.badges({"damage": 4}) == []
    assert M.label(1, 12.0) == "1 \u00b7 12%"


def test_match_source_and_frame_bar():
    src = [{"slot": 0, "start_frame": 5, "end_frame": 8, "damage": 9},
           {"slot": 0, "start_frame": 9, "end_frame": 12, "damage": 4}]
    assert M.match_source(src, 0, 6)["damage"] == 9
    assert M.match_source(src, 0, 10)["damage"] == 4
    assert M.match_source(src, 1, 6) is None
    bar = M.frame_bar(5, 8, 20, 6, cells=20)
    assert len(bar) == 20 and bar[4] == "#" and bar[5] == "|" and bar[0] == "."


def test_build_items_joins_source_and_sweeps():
    info = {"frame": 6, "facing": -1, "hitboxes": [
        {"slot": 0, "active": True, "world": {"x": 2.0, "y": 5.0, "z": 0.0}, "radius": 3.0}]}
    prev = {"hitboxes": [{"slot": 0, "active": True, "world": {"x": 0.0, "y": 5.0, "z": 0.0}, "radius": 3.0}]}
    src = [{"slot": 0, "start_frame": 5, "end_frame": 8, "damage": 14, "angle": 361, "kbg": 100, "bkb": 30,
            "element": 2}]
    (item,) = M.build_items(info, prev, src, 6, 50, 100)
    assert item["label"] == "0 \u00b7 14%" and item["kind"] == "sakurai" and item["badges"] == ["electric"]
    assert item["sweep"] is not None and item["fan"] and item["lines"]
    # facing -1: the arrow goes toward -x in engine space (Blender x as well)
    (p0, p1) = item["lines"][0]
    assert p1[0] < p0[0]
    # no source -> still a sphere with a slot label, no arrow
    (bare,) = M.build_items(info, None, [], 6)
    assert bare["label"] == "slot 0" and not bare["lines"] and bare["sweep"] is None
