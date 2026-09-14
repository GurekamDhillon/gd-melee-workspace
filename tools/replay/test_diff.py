"""Tests for the frame differ (synthetic traces; a real .slp is still needed)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from diff import compare  # noqa: E402
from slp import State  # noqa: E402


def state(**overrides) -> State:
    base = dict(
        char=2,
        action_state=14,
        x=0.0,
        y=0.0,
        facing=1.0,
        percent=0.0,
        shield=60.0,
        stocks=4,
    )
    base.update(overrides)
    return State(**base)


class CompareTest(unittest.TestCase):
    def test_identical_traces_match(self) -> None:
        trace = {10: {(0, False): state(), (1, False): state(x=5.0)}}
        result = compare(trace, dict(trace))
        self.assertTrue(result.ok)
        self.assertEqual(result.frames, 1)
        self.assertEqual(result.player_frames, 2)

    def test_reports_first_field_and_frame(self) -> None:
        original = {10: {(0, False): state(y=1.0)}, 11: {(0, False): state(y=2.0)}}
        port = {10: {(0, False): state(y=1.0)}, 11: {(0, False): state(y=2.5)}}
        result = compare(original, port)
        self.assertFalse(result.ok)
        self.assertEqual(result.frames, 2)
        self.assertEqual(len(result.mismatches), 1)
        self.assertEqual((result.first.frame, result.first.field), (11, "y"))
        self.assertEqual((result.first.original, result.first.port), (2.0, 2.5))

    def test_one_mismatch_per_player_frame(self) -> None:
        original = {10: {(0, False): state(x=1.0, y=1.0)}}
        port = {10: {(0, False): state(x=2.0, y=2.0)}}
        result = compare(original, port)
        self.assertEqual(len(result.mismatches), 1)

    def test_missing_frame_and_player(self) -> None:
        original = {10: {(0, False): state()}, 11: {(0, False): state()}}
        port = {10: {}}
        result = compare(original, port)
        self.assertEqual(result.missing_frames, [11])
        self.assertEqual(result.missing_players, 1)
        self.assertFalse(result.ok)

    def test_ignores_frames_only_the_port_has(self) -> None:
        original = {10: {(0, False): state()}}
        port = {10: {(0, False): state()}, 11: {(0, False): state(x=9.0)}}
        result = compare(original, port)
        self.assertTrue(result.ok)
        self.assertEqual(result.frames, 1)


if __name__ == "__main__":
    unittest.main()
