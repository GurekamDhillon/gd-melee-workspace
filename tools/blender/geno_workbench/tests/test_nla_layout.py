"""Synthetic timing only: no source-game clip names or animation fixtures."""
from copy import deepcopy
from dataclasses import replace

import pytest

from nla_layout import layout, recipe_from_layout, validate


LENGTHS = {"wind": 40, "strike": 40, "idle": 40, "melee:synthetic/Kick": 40}


@pytest.mark.parametrize("recipe, starts, ends, holds, total, marks", [
    ({"move": "upper", "blend": 3, "segments": [
        {"clip": "wind", "from": 1, "to": 5},
        {"clip": "strike", "from": 10, "to": 20, "marks": {"hit": 12}},
        {"clip": "idle", "from": 0, "to": 6},
    ]}, [0, 8, 22], [4, 18, 28], [0, 0, 0], 29, [10]),
    ({"move": "down", "segments": [
        {"clip": "strike", "from": 2, "to": 14, "hold": 26, "marks": {"hit": 8}},
    ]}, [0], [12], [26], 39, [6]),
    ({"row": "Kick", "segments": [
        {"clip": "melee:synthetic/Kick", "from": 0, "to": 29, "marks": {"hit": 6}},
    ]}, [0], [29], [0], 30, [6]),
])
def test_three_recipe_shapes(recipe, starts, ends, holds, total, marks):
    # Catches overlap-style blends and exclusive-end crop off-by-ones.
    result = layout(recipe, LENGTHS)
    assert [s.frame_start for s in result.segments] == starts
    assert [s.frame_end for s in result.segments] == ends
    assert [s.hold for s in result.segments] == holds
    assert result.total_length == total
    assert [m.frame for m in result.marks] == marks
    assert result.segments[0].action_name == recipe["segments"][0]["clip"]


def test_speed_reverse_hold_and_incoming_blend_override():
    result = layout({"row": "Kick", "blend": 4, "segments": [
        {"clip": "wind", "from": 0, "to": 7, "speed": 2, "hold": 2},
        {"clip": "strike", "from": 9, "to": 3, "speed": 2,
         "blend": 1, "mirror": True, "root_yaw": 90, "yaw_ramp": True,
         "marks": {"hit": 5}},
    ]}, LENGTHS)
    a, b = result.segments
    assert (a.samples, a.frame_end, a.hold_end, a.scale) == (4, 3, 5, 0.5)
    assert (b.frame_start, b.frame_end, b.reversed, b.scale) == (7, 10, True, 0.5)
    assert b.mirror and b.root_yaw == 90 and b.yaw_ramp
    gap, = result.blend_gaps
    assert (gap.frame_start, gap.frame_end, gap.length) == (6, 6, 1)
    assert result.marks[0].frame == 9
    assert result.total_length == 11


def test_retime_keeps_endpoint_span_and_splice_double_rounding():
    recipe = {"row": "Kick", "frames": 10, "segments": [
        {"clip": "wind", "from": 0, "to": 8, "speed": 2,
         "marks": {"half_even": 1, "half_up": 3, "end": 8}},
    ]}
    result = layout(recipe, LENGTHS)
    assert (result.raw_length, result.total_length, result.retime_scale) == (5, 10, 2.25)
    assert (result.segments[0].frame_start, result.segments[0].frame_end) == (0, 9)
    assert result.segments[0].scale == 0.5  # source speed, separate from whole-clip retime
    assert [m.frame for m in result.marks] == [0, 4, 9]


def test_marks_and_source_mapping_include_direction_and_inserted_frames():
    recipe = {"row": "Kick", "blend": 2, "segments": [
        {"clip": "wind", "from": 0, "to": 2, "hold": 1},
        {"clip": "strike", "from": 10, "to": 4, "speed": 2,
         "marks": {"first": 10, "middle": 8, "last": 4}},
    ]}
    result = layout(recipe, LENGTHS)
    assert [m.frame for m in result.marks] == [6, 7, 9]
    assert [result.segments[1].output_frame(f, result.retime_scale)
            for f in (10, 9, 8, 6, 4)] == [6, 6.5, 7, 8, 9]


def test_zero_blend_and_single_pose_are_real_samples():
    result = layout({"row": "Kick", "blend": 0, "segments": [
        {"clip": "wind", "from": 3, "to": 3, "hold": 2},
        {"clip": "idle", "from": 0, "to": 1},
    ]}, LENGTHS)
    assert result.blend_gaps == []
    assert result.segments[1].frame_start == 3
    assert result.total_length == 5


def signature(result):
    return (result.segments, result.blend_gaps, result.marks,
            result.total_length, result.raw_length, result.retime_scale)


def test_round_trip_preserves_retime_flags_notes_and_unsampled_crop_tail():
    recipe = {"row": "Kick", "wired": False, "example": True, "note": "synthetic",
              "loop": True, "loop_blend": 2, "blend": 3, "frames": 25,
              "segments": [
        {"clip": "wind", "from": 0, "to": 7, "speed": 2, "note": "crop", "hold": 2},
        {"clip": "strike", "from": 10, "to": 4, "mirror": True,
         "root_yaw": -90, "yaw_ramp": True, "blend": 1, "marks": {"hit": 7}},
    ]}
    original = deepcopy(recipe)
    first = layout(recipe, LENGTHS)
    recovered = recipe_from_layout(first)
    assert recovered["segments"][0]["to"] == 7
    assert recovered["wired"] is False and recovered["note"] == "synthetic"
    assert recovered["loop"] is True and recovered["frames"] == 25
    assert signature(layout(recovered, LENGTHS)) == signature(first)
    assert recipe == original


def test_inverse_uses_edited_strip_positions():
    result = layout({"row": "Kick", "blend": 1, "segments": [
        {"clip": "wind", "from": 0, "to": 2},
        {"clip": "strike", "from": 1, "to": 3},
    ]}, LENGTHS)
    result.segments[1] = replace(result.segments[1], frame_start=6, frame_end=8, hold_end=8)
    recovered = recipe_from_layout(result)
    assert recovered["segments"][1]["blend"] == 3
    assert layout(recovered, LENGTHS).total_length == 9


def test_inverse_rejects_overlap_instead_of_silently_changing_timing():
    result = layout({"row": "Kick", "blend": 0, "segments": [
        {"clip": "wind", "from": 0, "to": 2},
        {"clip": "strike", "from": 1, "to": 3},
    ]}, LENGTHS)
    result.segments[1] = replace(result.segments[1], frame_start=2, frame_end=4, hold_end=4)
    with pytest.raises(ValueError, match="overlap"):
        recipe_from_layout(result)


@pytest.mark.parametrize("patch", [
    {"speed": 0}, {"speed": -1}, {"speed": float("nan")}, {"speed": True},
    {"hold": -1}, {"hold": 0.5}, {"blend": -1}, {"from": -1}, {"to": 40},
    {"mirror": "yes"}, {"root_yaw": float("inf")}, {"marks": {"hit": 9}},
    {"clip": "missing"}, {"oops": 1},
])
def test_invalid_segments_are_diagnostics_not_crashes(patch):
    recipe = {"row": "Kick", "segments": [{"clip": "wind", "from": 0, "to": 4, **patch}]}
    assert validate(recipe, LENGTHS)
    with pytest.raises(ValueError):
        layout(recipe, LENGTHS)


@pytest.mark.parametrize("recipe", [None, [], {}, {"row": "Kick", "segments": []},
    {"row": "Kick", "segments": [None]},
    {"row": "Kick", "segments": [{"clip": "wind", "from": 0, "to": 2}], "frames": 1},
])
def test_invalid_recipe_is_reported(recipe):
    assert validate(recipe, LENGTHS)
