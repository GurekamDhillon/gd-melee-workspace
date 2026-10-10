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
