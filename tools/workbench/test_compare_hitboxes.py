"""Synthetic-only tests for the public hitbox comparison function."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import compare_hitboxes as C


def test_match_within_tolerance():
    wb = [{"slot": 0, "world": {"x": 1.0, "y": 2.0, "z": 0.0}, "radius": 2.8, "active": True}]
    ref = [{"slot": 0, "pos": (1.1, 2.0, 0.0), "radius": 2.8}]
    r = C.compare(wb, ref, 0.5)
    assert r[0]["ok"] and math.isclose(r[0]["d"], 0.1, abs_tol=1e-9)


def test_diff_beyond_tolerance_and_radius_mismatch():
    wb = [{"slot": 0, "world": {"x": 0, "y": 0, "z": 0}, "radius": 2.0, "active": True}]
    assert not C.compare(wb, [{"slot": 0, "pos": (3, 0, 0), "radius": 2.0}], 0.5)[0]["ok"]
    assert not C.compare(wb, [{"slot": 0, "pos": (0, 0, 0), "radius": 3.0}], 0.5)[0]["ok"]


def test_missing_on_either_side_is_reported():
    wb = [{"slot": 0, "world": {"x": 0, "y": 0, "z": 0}, "radius": 1, "active": True}]
    r = C.compare(wb, [], 0.5)
    assert r[0]["ok"] is False and r[0]["why"] == "missing in reference"
    r = C.compare([], [{"slot": 1, "pos": (0, 0, 0), "radius": 1}], 0.5)
    assert r[0]["why"] == "missing in wb"


def test_inactive_wb_hitboxes_ignored():
    wb = [{"slot": 0, "world": {"x": 0, "y": 0, "z": 0}, "radius": 1, "active": False}]
    assert C.compare(wb, [], 0.5) == []


def test_model_space_transform_applied_before_distance():
    wb = [{"slot": 0, "world": {"x": 10.0, "y": 2.0, "z": 0.0}, "radius": 2.0, "active": True}]
    ref = [{"slot": 0, "pos": (0.0, 2.0, 0.0), "radius": 2.0}]
    shift = lambda p: (p[0] - 10.0, p[1], p[2])           # a root offset of x=10
    assert not C.compare(wb, ref, 0.5)[0]["ok"]            # world vs model-local: the 57.8-style mismatch
    assert C.compare(wb, ref, 0.5, to_model=shift)[0]["ok"]


def test_transform_preserves_inputs_reference_and_radius():
    from copy import deepcopy

    wb = [{"slot": 0, "world": {"x": 10.0, "y": 2.0, "z": 0.0}, "radius": 3.0, "active": True}]
    ref = [{"slot": 0, "pos": (0.0, 2.0, 0.0), "radius": 2.0}]
    original_wb, original_ref = deepcopy(wb), deepcopy(ref)
    calls = []

    def shift(p):
        calls.append(p)
        return (p[0] - 10.0, p[1], p[2])

    result = C.compare(wb, ref, 0.5, to_model=shift)
    assert calls == [(10.0, 2.0, 0.0)]
    assert result == [{"slot": 0, "ok": False, "d": 0.0, "why": "radius mismatch"}]
    assert wb == original_wb and ref == original_ref


def test_transform_not_called_for_inactive_or_unmatched_hits():
    wb = [
        {"slot": 0, "world": {"x": 0, "y": 0, "z": 0}, "radius": 1, "active": False},
        {"slot": 1, "world": {"x": 10, "y": 0, "z": 0}, "radius": 1, "active": True},
    ]
    ref = [{"slot": 2, "pos": (0, 0, 0), "radius": 1}]

    def unexpected_transform(p):
        raise AssertionError("unmatched hitboxes must not be transformed")

    result = C.compare(wb, ref, 0.5, to_model=unexpected_transform)
    assert result == [
        {"slot": 1, "ok": False, "d": None, "why": "missing in reference"},
        {"slot": 2, "ok": False, "d": None, "why": "missing in wb"},
    ]
