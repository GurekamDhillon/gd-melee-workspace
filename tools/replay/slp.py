"""Minimal Slippi (.slp) reader.

Decodes the `raw` event block of a Slippi replay into per-frame controller and
post-frame records. This is the ground truth a frame-exact port replay is
compared against. The container is read directly; no UBJSON dependency.

The raw-block layout and per-event offsets mirror the reader in
Hero88go/melee-unlocked `tools/replay_compare.py` (GPL-2.0-or-later), whose
behaviour was validated against real replays.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

EVENT_PAYLOADS = 0x35
GAME_START = 0x36
PRE_FRAME = 0x37
POST_FRAME = 0x38

PlayerKey = tuple[int, bool]


@dataclass(frozen=True)
class Input:
    stick_x: float
    stick_y: float
    cstick_x: float
    cstick_y: float
    trigger: float
    buttons: int


@dataclass(frozen=True)
class State:
    char: int
    action_state: int
    x: float
    y: float
    facing: float
    percent: float
    shield: float
    stocks: int


@dataclass
class Replay:
    settings: bytes | None
    pre: dict[int, dict[PlayerKey, Input]]
    post: dict[int, dict[PlayerKey, State]]

    @property
    def first_frame(self) -> int:
        return min(self.post)

    @property
    def last_frame(self) -> int:
        return max(self.post)


def parse(path: str | Path) -> Replay:
    data = Path(path).read_bytes()
    marker = data.find(b"raw")
    if marker < 0:
        raise ValueError(f"{path}: no raw event block")
    pos = marker + 3
    if data[pos : pos + 2] != b"[$":
        raise ValueError(f"{path}: raw block is not a UBJSON array")
    length = struct.unpack(">I", data[pos + 5 : pos + 9])[0]
    # 0 = a replay still being written (Slippi's convention; the port's recorder leaves it so when
    # a run is killed): the events run to the end of the file
    raw = data[pos + 9 : pos + 9 + length] if length else data[pos + 9 :]
    if not raw or raw[0] != EVENT_PAYLOADS:
        raise ValueError(f"{path}: raw block does not start with the event-size table")

    sizes = _event_size_table(raw)
    cursor = 1 + raw[1]
    settings: bytes | None = None
    pre: dict[int, dict[PlayerKey, Input]] = {}
    post: dict[int, dict[PlayerKey, State]] = {}
    while cursor < len(raw):
        command = raw[cursor]
        size = sizes.get(command)
        if size is None:
            break
        body = raw[cursor : cursor + 1 + size]
        if len(body) < 1 + size:
            break  # the last event of a replay cut off mid-write
        if command == GAME_START:
            settings = bytes(body)
        elif command == PRE_FRAME:
            frame = struct.unpack(">i", body[1:5])[0]
            key: PlayerKey = (body[5], bool(body[6]))
            pre.setdefault(frame, {})[key] = Input(
                stick_x=_f32(body, 0x19),
                stick_y=_f32(body, 0x1D),
                cstick_x=_f32(body, 0x21),
                cstick_y=_f32(body, 0x25),
                trigger=_f32(body, 0x29),
                buttons=struct.unpack(">I", body[0x2D:0x31])[0],
            )
        elif command == POST_FRAME:
            frame = struct.unpack(">i", body[1:5])[0]
            key = (body[5], bool(body[6]))
            post.setdefault(frame, {})[key] = State(
                char=body[7],
                action_state=struct.unpack(">H", body[8:10])[0],
                x=_f32(body, 0x0A),
                y=_f32(body, 0x0E),
                facing=_f32(body, 0x12),
                percent=_f32(body, 0x16),
                shield=_f32(body, 0x1A),
                stocks=body[0x21],
            )
        cursor += 1 + size
    return Replay(settings, pre, post)


def _event_size_table(raw: bytes) -> dict[int, int]:
    count = (raw[1] - 1) // 3
    return {
        raw[2 + 3 * k]: struct.unpack(">H", raw[3 + 3 * k : 5 + 3 * k])[0]
        for k in range(count)
    }


def _f32(body: bytes, offset: int) -> float:
    return struct.unpack(">f", body[offset : offset + 4])[0]
