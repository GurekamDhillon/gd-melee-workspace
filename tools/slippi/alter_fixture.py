"""Create one private `.slp` P1 input mutation for two-client negative control.

The copy differs in one P1 Pre-Frame event only. It keeps Game Start, the
opponent's input, post-frame records and metadata byte-for-byte, so a verifier
can compare both clients against the original fixture. The altered replay must
be placed in an ignored run directory by the caller.

Pre-Frame offsets and event sizes follow project-slippi/slippi-wiki SPEC.md at
71c6a395f841ff67f75ab4c0084fd1d6ee22c2db; the native reader in
melee/pc/platform/gw_replay.c uses the same offsets. PAD_BUTTON_A is 0x0100.
"""

from __future__ import annotations

import struct
from pathlib import Path


class FixtureMutationError(ValueError):
    """Fixed explanation for a fixture that cannot support this negative control."""


_RAW_MARKER = b'raw[$U#l'
_A = 0x0100
_MAX_BYTES = 512 * 1024 * 1024


def _events(data: bytes):
    marker = data.find(_RAW_MARKER)
    if marker < 0 or marker + 12 > len(data):
        raise FixtureMutationError('missing raw SLP event block')
    count = struct.unpack_from('>I', data, marker + 8)[0]
    begin, end = marker + 12, marker + 12 + count
    if not count or end > len(data) or begin + 2 > end or data[begin] != 0x35:
        raise FixtureMutationError('truncated or incomplete SLP raw block')
    table_len = data[begin + 1]
    if table_len < 1 or (table_len - 1) % 3 or begin + 1 + table_len > end:
        raise FixtureMutationError('invalid SLP event-size table')
    sizes = {}
    for offset in range(begin + 2, begin + 1 + table_len, 3):
        command = data[offset]
        size = struct.unpack_from('>H', data, offset + 1)[0]
        if not size or command in sizes:
            raise FixtureMutationError('invalid SLP event size')
        sizes[command] = size
    cursor = begin + 1 + table_len
    while cursor < end:
        command = data[cursor]
        size = sizes.get(command)
        if size is None or cursor + 1 + size > end:
            raise FixtureMutationError('truncated SLP event')
        yield command, cursor, size
        cursor += 1 + size
    if cursor != end:
        raise FixtureMutationError('invalid SLP event boundary')


def make_altered_p1_fixture(source: Path, destination: Path, min_frame: int = 0) -> dict:
    """Write an exclusive private copy with one new P1 A press; return metadata.

    Selects the first frame at or after `min_frame` whose prior and current P1
    post-frame action are Wait (14), with A clear in physical and processed input
    on both frames. This makes the added A a rising edge while P1 is actionable.
    The caller should verify that this input actually causes a final-state
    divergence; fixture mutation alone does not prove game behavior.
    """
    source, destination = Path(source), Path(destination)
    if source.resolve() == destination.resolve():
        raise FixtureMutationError('source and altered fixture must differ')
    if not isinstance(min_frame, int) or min_frame < 0:
        raise FixtureMutationError('invalid minimum mutation frame')
    if source.stat().st_size > _MAX_BYTES:
        raise FixtureMutationError('SLP fixture is too large')
    data = source.read_bytes()
    start_seen = end_seen = False
    pre, post = {}, {}
    for command, offset, size in _events(data):
        if command == 0x36:
            if start_seen or size < 0x1A4:
                raise FixtureMutationError('invalid SLP Game Start')
            version = tuple(data[offset + 1:offset + 4])
            if version < (3, 17, 0) or data[offset + 0x1A4] != 8:
                raise FixtureMutationError('requires modern online SLP fixture')
            start_seen = True
        elif command == 0x39:
            end_seen = True
        elif command in (0x37, 0x38):
            if size < (0x42 if command == 0x37 else 0x21):
                raise FixtureMutationError('short SLP frame event')
            frame = struct.unpack_from('>i', data, offset + 1)[0]
            port, follower = data[offset + 5], data[offset + 6]
            if port == 0 and follower == 0:
                target = pre if command == 0x37 else post
                if frame in target:
                    raise FixtureMutationError('duplicate P1 SLP frame event')
                target[frame] = offset
    if not start_seen or not end_seen:
        raise FixtureMutationError('incomplete SLP fixture')
    selected = None
    for frame in sorted(pre):
        if frame < min_frame or frame - 1 not in pre or frame not in post or frame - 1 not in post:
            continue
        if any(struct.unpack_from('>H', data, post[f] + 8)[0] != 14 for f in (frame - 1, frame)):
            continue
        if any((struct.unpack_from('>I', data, pre[f] + 0x2D)[0] & _A) or
               (struct.unpack_from('>H', data, pre[f] + 0x31)[0] & _A)
               for f in (frame - 1, frame)):
            continue
        selected = frame
        break
    if selected is None:
        raise FixtureMutationError('no grounded idle P1 frame with A released')
    offset = pre[selected]
    altered = bytearray(data)
    processed = struct.unpack_from('>I', altered, offset + 0x2D)[0] | _A
    physical = struct.unpack_from('>H', altered, offset + 0x31)[0] | _A
    struct.pack_into('>I', altered, offset + 0x2D, processed)
    struct.pack_into('>H', altered, offset + 0x31, physical)
    with destination.open('xb') as out:
        out.write(altered)
    return {'frame': selected, 'port': 0, 'button': _A}
