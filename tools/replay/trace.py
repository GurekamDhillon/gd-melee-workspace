"""Reader for the port's per-frame state trace.

The port emits one CSV row per player per frame (see `MELEE_STATE_TRACE` in the
harness README), mirroring the Slippi post-frame fields:

    frame,player,follower,char,action_state,x,y,facing,percent,stocks
"""

from __future__ import annotations

import csv
from pathlib import Path

from slp import PlayerKey, State

COLUMNS = ("frame", "player", "follower", "char", "action_state", "x", "y", "facing", "percent", "stocks")
_INT = {"frame", "player", "char", "action_state", "stocks"}
_BOOL = {"follower"}


def read(path: str | Path) -> dict[int, dict[PlayerKey, State]]:
    trace: dict[int, dict[PlayerKey, State]] = {}
    with open(path, newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or tuple(reader.fieldnames) != COLUMNS:
            raise ValueError(f"{path}: unexpected header {reader.fieldnames}")
        for row in reader:
            frame = _int(row["frame"])
            key: PlayerKey = (_int(row["player"]), _bool(row["follower"]))
            trace.setdefault(frame, {})[key] = State(
                char=_int(row["char"]),
                action_state=_int(row["action_state"]),
                x=_float(row["x"]),
                y=_float(row["y"]),
                facing=_float(row["facing"]),
                percent=_float(row["percent"]),
                shield=0.0,
                stocks=_int(row["stocks"]),
            )
    return trace


def _int(value: str) -> int:
    return int(value, 0)


def _float(value: str) -> float:
    return float(value)


def _bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes"}
