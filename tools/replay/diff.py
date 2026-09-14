"""Frame-exact comparison of two Slippi-shaped traces.

A comparison runs over the intersection of frames present in both traces and
reports, per player-frame, the first post-frame field that differs. It also
surfaces frames and players the port trace is missing, which is what catches a
truncated or early-terminating replay.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from slp import PlayerKey, State

DEFAULT_FIELDS = ("action_state", "x", "y", "facing", "percent", "stocks", "char")


@dataclass
class Mismatch:
    frame: int
    player: PlayerKey
    field: str
    original: object
    port: object


@dataclass
class Result:
    frames: int
    player_frames: int
    mismatches: list[Mismatch] = field(default_factory=list)
    missing_frames: list[int] = field(default_factory=list)
    missing_players: int = 0

    @property
    def ok(self) -> bool:
        return not (self.mismatches or self.missing_frames or self.missing_players)

    @property
    def first(self) -> Mismatch | None:
        return self.mismatches[0] if self.mismatches else None


def compare(
    original: dict[int, dict[PlayerKey, State]],
    port: dict[int, dict[PlayerKey, State]],
    fields: tuple[str, ...] = DEFAULT_FIELDS,
) -> Result:
    original_frames = set(original)
    port_frames = set(port)
    common = sorted(original_frames & port_frames)

    result = Result(frames=len(common), player_frames=0)
    result.missing_frames = sorted(original_frames - port_frames)

    for frame in common:
        for player, expected in original[frame].items():
            actual = port[frame].get(player)
            result.player_frames += 1
            if actual is None:
                result.missing_players += 1
                continue
            for name in fields:
                left = getattr(expected, name)
                right = getattr(actual, name)
                if left != right:
                    result.mismatches.append(Mismatch(frame, player, name, left, right))
                    break

    return result
