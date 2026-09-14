"""Diff a Slippi recording against the port's per-frame state trace.

    python tools/replay/replay_compare.py original.slp port-trace.csv [--fields ...]

Exit code is 0 only when every compared player-frame matches and no frame or
player is missing from the port trace. Prints the first divergence, which is the
bisect point for a replay regression.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import diff  # noqa: E402
import slp  # noqa: E402
import trace  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("replay", type=Path, help="original Slippi .slp")
    parser.add_argument("trace", type=Path, help="port state trace CSV")
    parser.add_argument("--fields", default=",".join(diff.DEFAULT_FIELDS))
    args = parser.parse_args()

    recording = slp.parse(args.replay)
    port = trace.read(args.trace)
    fields = tuple(f.strip() for f in args.fields.split(",") if f.strip())

    result = diff.compare(recording.post, port, fields)
    print(
        f"recording frames {recording.first_frame}..{recording.last_frame} "
        f"({len(recording.post)}), port frames {len(port)}"
    )
    print(
        f"{result.player_frames} player-frames compared over {result.frames} frames; "
        f"{len(result.mismatches)} mismatches, {len(result.missing_frames)} missing frames, "
        f"{result.missing_players} missing players"
    )
    if result.missing_frames:
        print(f"first missing frame: {result.missing_frames[0]}")
    if result.first is not None:
        mismatch = result.first
        print(
            f"first divergence: frame {mismatch.frame} player/follower {mismatch.player} "
            f"{mismatch.field}: original {mismatch.original} vs port {mismatch.port}"
        )
    return 0 if result.ok else 1


if __name__ == "__main__":
    sys.exit(main())
