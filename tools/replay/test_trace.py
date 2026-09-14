"""Tests for reading the port state trace."""

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import trace  # noqa: E402

HEADER = "frame,player,follower,char,action_state,x,y,facing,percent,stocks\n"
ROWS = "10,0,0,2,14,1.5,-3.0,1.0,12.5,4\n10,1,0,9,20,0.0,0.0,-1.0,0.0,3\n11,0,0,2,15,2.0,-3.0,1.0,13.0,4\n"


class TraceTest(unittest.TestCase):
    def test_reads_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.csv"
            path.write_text(HEADER + ROWS)
            result = trace.read(path)
        self.assertEqual(sorted(result), [10, 11])
        first = result[10][(0, False)]
        self.assertEqual((first.char, first.action_state, first.stocks), (2, 14, 4))
        self.assertAlmostEqual(first.x, 1.5)
        self.assertAlmostEqual(first.percent, 12.5)

    def test_rejects_bad_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "trace.csv"
            path.write_text("nope\n")
            with self.assertRaises(ValueError):
                trace.read(path)


if __name__ == "__main__":
    unittest.main()
