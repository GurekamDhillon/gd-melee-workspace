import travel


def frame(y, x=-60.0):
    return {
        "root": {"pos": {"x": x, "y": y, "z": 0.0}},
        "bones": [{"joint": 0, "parent": -1, "pos": {"x": x, "y": y, "z": 0.0},
                   "mtx": [1, 0, 0, x, 0, 1, 0, y, 0, 0, 1, 0]}],
        "hitboxes": [{"slot": 0, "world": {"x": x + 3, "y": y + 5, "z": 0.0}, "radius": 2}],
        "hurtboxes": [{"a": {"x": x, "y": y + 1, "z": 0}, "b": {"x": x, "y": y + 9, "z": 0}, "radius": 2}],
        "ecb": {"bottom": {"x": x, "y": y}, "top": {"x": x, "y": y + 14}},
        "floorY": 0.0,
    }


def test_in_place_keeps_the_root_and_moves_everything_with_it():
    anchor = travel.anchor_of(frame(130.0))
    later = frame(50.7, x=-58.0)          # fell 79.3 and slid 2
    shown = travel.in_place(later, anchor)
    assert shown["root"]["pos"] == {"x": -60.0, "y": 130.0, "z": 0.0}
    assert shown["bones"][0]["mtx"][3] == -60.0 and shown["bones"][0]["mtx"][7] == 130.0
    assert shown["hitboxes"][0]["world"] == {"x": -57.0, "y": 135.0, "z": 0.0}   # same offset from the root
    assert shown["hurtboxes"][0]["b"]["y"] == 139.0
    assert shown["ecb"]["bottom"]["y"] == 130.0
    assert abs(shown["floorY"] - 79.3) < 1e-9
    assert later["root"]["pos"]["y"] == 50.7        # the engine's data is not modified


def test_in_place_without_motion_or_anchor_is_the_same_object():
    info = frame(10.0)
    assert travel.in_place(info, travel.anchor_of(info)) is info
    assert travel.in_place(info, None) is info
