"""The combo string plan (pure): cut frames, string frames, markers, hit windows.  Numbers mirror the Workbench's
planComboString test (workbench/tests/combo_test.cpp stringPlanCutsAtTheWindowStartAndTheFirstHit), so the two stay one rule."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import combo_play as C  # noqa: E402

ROUTES = [
    {"name": "L1>L2", "from": "jab1", "to": "geno:Light2", "input": "light", "on": "hit", "where": "ground", "window": [10, 18]},
    {"name": "L1>H", "from": "jab1", "to": "dair", "input": "heavy", "dir": "forward", "window": [12, 0]},
    {"name": "L1>Spc", "from": ["jab1", "dair"], "to": "special_s", "input": "special", "priority": 10},
    {"name": "A>J", "from": "dair", "to": "jump_short", "input": "jump", "window": [3, 0]},
]
INFO = {"jab1": {"length": 21, "first_hit": 3}, "geno:Light2": {"length": 20, "first_hit": 4}, "dair": {"length": 40, "first_hit": 6}}


def test_cut_is_the_window_start_and_the_next_move_follows_the_cancel_frame():
    plan = C.plan_string(["jab1", "geno:Light2"], ROUTES, INFO)
    assert [s["cut"] for s in plan] == [10, 20]
    assert plan[0]["linked"] and plan[0]["route"] == "L1>L2" and plan[0]["input"] == "light"
    assert plan[0]["start"] == 1 and plan[0]["cancel_frame"] == 10
    assert plan[1]["start"] == 11 and not plan[1]["linked"]          # the last step plays out
    assert C.total_frames(plan) == 30


def test_add_buffer_is_kept_inside_the_window_and_the_move():
    assert C.plan_string(["jab1", "geno:Light2"], ROUTES, INFO, 5, True)[0]["cut"] == 15
    assert C.plan_string(["jab1", "geno:Light2"], ROUTES, INFO, 30, True)[0]["cut"] == 18      # window ends at 18
    short = {"jab1": {"length": 12, "first_hit": 3}, "geno:Light2": {"length": 20, "first_hit": 4}}
    assert C.plan_string(["jab1", "geno:Light2"], ROUTES, short, 30, True)[0]["cut"] == 12     # move ends at 12
    routes = [dict(ROUTES[0], buffer=2)]
    assert C.plan_string(["jab1", "geno:Light2"], routes, INFO, 5, True)[0]["cut"] == 12       # the route's own buffer wins


def test_a_contact_route_waits_for_the_first_hit_and_a_whiff_route_does_not():
    early = [{"name": "e", "from": "jab1", "to": "dair", "input": "light", "window": [1, 0]}]
    assert C.plan_string(["jab1", "dair"], early, INFO)[0]["cut"] == 3
    whiff = [dict(early[0], on="whiff")]
    assert C.plan_string(["jab1", "dair"], whiff, INFO)[0]["cut"] == 1


def test_missing_route_plays_the_move_out_and_exact_source_beats_star_then_priority():
    plan = C.plan_string(["dair", "jab1"], ROUTES, INFO)
    assert not plan[0]["linked"] and plan[0]["cut"] == 40
    star = [{"name": "any", "from": "*", "to": "jab1", "input": "light", "window": [9, 0], "on": "any"},
            {"name": "exact", "from": "dair", "to": "jab1", "input": "light", "window": [12, 0], "on": "any"}]
    assert C.plan_string(["dair", "jab1"], star, INFO)[0]["route"] == "exact"
    assert C.plan_string(["jab1", "jab1"], star, INFO)[0]["route"] == "any"
    tie = [{"name": "first", "from": "jab1", "to": "dair", "input": "light"}, {"name": "second", "from": "jab1", "to": "dair", "input": "heavy"}]
    assert C.find_route(tie, "jab1", "dair")["name"] == "first"          # ties keep the file order
    tie[1]["priority"] = 1
    assert C.find_route(tie, "jab1", "dair")["name"] == "second"


def test_unknown_length_plays_a_default_and_locate_maps_string_frames_to_move_frames():
    plan = C.plan_string(["x"], [], {})
    assert plan[0]["cut"] == C.PLAYED_OUT
    plan = C.plan_string(["jab1", "geno:Light2"], ROUTES, INFO)
    assert C.locate(plan, 1) == (0, 1) and C.locate(plan, 10) == (0, 10) and C.locate(plan, 11) == (1, 1)
    assert C.locate(plan, 30) == (1, 20) and C.locate(plan, 31) is None


def test_markers_cancel_points_and_route_window_starts_in_input_colours():
    plan = C.plan_string(["jab1", "geno:Light2"], ROUTES, INFO)
    marks = C.markers(plan, ROUTES)
    cancel = [m for m in marks if m["kind"] == "cancel"]
    assert len(cancel) == 1 and cancel[0]["frame"] == 10 and cancel[0]["name"].startswith("CANCEL L1>L2") and cancel[0]["input"] == "light"
    routes = {m["name"]: m for m in marks if m["kind"] == "route"}
    assert routes["ROUTE light L1>L2 [10-18]"]["frame"] == 10
    assert "ROUTE heavy L1>H [12-end]" not in routes                  # opens at 12, after the cut at 10: not part of this string
    assert routes["ROUTE special L1>Spc [1-end]"]["frame"] == 1 and routes["ROUTE special L1>Spc [1-end]"]["input"] == "special"
    late = [dict(ROUTES[0], window=[10, 18]), {"name": "far", "from": "jab1", "to": "dair", "input": "grab", "window": [20, 0]}]
    marks = C.markers(C.plan_string(["jab1", "geno:Light2"], late, INFO), late)
    assert not [m for m in marks if "far" in m["name"]]
    assert all(C.INPUT_COLOURS[m["input"]] for m in marks)
    assert len({tuple(v) for v in C.INPUT_COLOURS.values()}) == len(C.INPUT_COLOURS)       # one colour per class


def test_hit_windows_are_in_string_frames_and_clipped_to_the_played_part():
    steps = [{"hits": [{"slot": 0, "bone": "hand", "size": 3, "start_frame": 3, "end_frame": 6},
                       {"slot": 1, "bone": "arm", "size": 2, "start_frame": 12, "end_frame": -1}]},
             {"hits": [{"slot": 0, "bone": "hand", "size": 3, "start_frame": 4, "end_frame": 8}]}]
    plan = C.plan_string(["jab1", "geno:Light2"], ROUTES, INFO)         # cut at 10: the frame-12 hit is never reached
    wins = C.hit_windows(plan, steps)
    assert [(w["segment"], w["first"], w["last"]) for w in wins] == [(0, 3, 5), (1, 14, 17)]
    assert C.hit_windows(C.plan_string(["jab1"], [], INFO), steps)[1]["last"] == 21      # never cleared: to the end of the move


def test_clip_range_is_crop_plus_move_frame_held_inside_the_action():
    seg = {"cut": 10}
    assert C.clip_range(seg, 0, 41.0) == (1, 10)
    assert C.clip_range(seg, 9, 41.0) == (10, 19)
    assert C.clip_range(seg, 35, 41.0) == (36, 41)
