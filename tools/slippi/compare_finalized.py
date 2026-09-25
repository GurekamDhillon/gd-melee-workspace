"""Fail-closed evidence checks for the experimental two-client Slippi runner.

Uses the existing gameplay comparer, adding complete recording, network
provenance, finalized checksum and distinct-process artifact requirements.

Direct evidence schema 1 adds `run_salt` (16 random bytes, lowercase hex),
`account_tag`, and `peer_account_tag` (64 lowercase hex digits each). A tag is
SHA256(the ASCII bytes of "GD Slippi account v1", then one NUL byte, then
bytes.fromhex(run_salt), then the assigned account's FNV64 UID fingerprint as
eight big-endian bytes). Both processes
receive the same fresh salt from the runner. Only tags and salt may appear in
evidence; the peer tag must equal the other client's account tag. This is
diagnostic identity evidence, not authentication.
Finalized hashes cover every fixture frame and may additionally include the
start-of-next-frame boundary at last_frame + 1 on both clients.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'replay'))
import diff as replay_diff  # noqa: E402
import slp  # noqa: E402


TRACE_COLUMNS = ('frame', 'player', 'follower', 'char', 'action_state', 'x', 'y',
                 'facing', 'percent', 'stocks')
MAX_FIXTURE_FRAMES = 300_000
INPUT_FIELDS = ('stick_x', 'stick_y', 'cstick_x', 'cstick_y', 'trigger', 'buttons')


def _ubjson_int(data: bytes, cursor: int) -> tuple[int, int]:
    if cursor >= len(data):
        raise ValueError('truncated UBJSON integer')
    marker = data[cursor]
    widths = {ord('i'): (1, True), ord('U'): (1, False),
              ord('I'): (2, True), ord('l'): (4, True), ord('L'): (8, True)}
    if marker not in widths:
        raise ValueError('invalid UBJSON length')
    width, signed = widths[marker]
    cursor += 1
    if cursor + width > len(data):
        raise ValueError('truncated UBJSON integer')
    return int.from_bytes(data[cursor:cursor + width], 'big', signed=signed), cursor + width


def _ubjson_value_end(data: bytes, cursor: int, depth: int = 0) -> int:
    if cursor >= len(data) or depth > 64:
        raise ValueError('truncated or deeply nested UBJSON value')
    marker = data[cursor]
    cursor += 1
    if marker == ord('{'):
        while cursor < len(data) and data[cursor] != ord('}'):
            if data[cursor] == ord('N'):
                cursor += 1
                continue
            length, cursor = _ubjson_int(data, cursor)
            if length < 0 or cursor + length > len(data):
                raise ValueError('truncated UBJSON object key')
            cursor = _ubjson_value_end(data, cursor + length, depth + 1)
        if cursor >= len(data):
            raise ValueError('unterminated UBJSON object')
        return cursor + 1
    if marker == ord('['):
        while cursor < len(data) and data[cursor] != ord(']'):
            cursor = _ubjson_value_end(data, cursor, depth + 1)
        if cursor >= len(data):
            raise ValueError('unterminated UBJSON array')
        return cursor + 1
    if marker in (ord('S'), ord('H')):
        length, cursor = _ubjson_int(data, cursor)
        if length < 0 or cursor + length > len(data):
            raise ValueError('truncated UBJSON string')
        return cursor + length
    if marker in (ord('T'), ord('F'), ord('Z'), ord('N')):
        return cursor
    widths = {ord('C'): 1, ord('i'): 1, ord('U'): 1, ord('I'): 2,
              ord('l'): 4, ord('L'): 8, ord('d'): 4, ord('D'): 8}
    width = widths.get(marker)
    if width is None or cursor + width > len(data):
        raise ValueError('invalid or truncated UBJSON value')
    return cursor + width


def _complete_container_tail(data: bytes, cursor: int) -> None:
    # The raw optimized byte array was consumed separately. Parse remaining
    # top-level key/value pairs so a metadata object's `}` cannot masquerade
    # as the missing outer container close.
    while cursor < len(data) and data[cursor] != ord('}'):
        if data[cursor] == ord('N'):
            cursor += 1
            continue
        length, cursor = _ubjson_int(data, cursor)
        if length < 0 or cursor + length > len(data):
            raise ValueError('truncated replay metadata key')
        cursor = _ubjson_value_end(data, cursor + length)
    if cursor != len(data) - 1 or data[cursor] != ord('}'):
        raise ValueError('incomplete replay container')


def _complete_replay(path: Path) -> slp.Replay:
    data = path.read_bytes()
    if not data.startswith(b'{U\x03raw[$U#l') or not data.endswith(b'}'):
        raise ValueError('incomplete replay container')
    marker = data.find(b'raw[$U#l')
    if marker < 0 or marker + 12 > len(data):
        raise ValueError('missing raw event block')
    length = struct.unpack_from('>I', data, marker + 8)[0]
    begin = marker + 12
    end = begin + length
    if not length or end > len(data):
        raise ValueError('unfinalized or truncated raw event block')
    _complete_container_tail(data, end)
    raw = data[begin:end]
    if len(raw) < 2 or raw[0] != 0x35:
        raise ValueError('missing event-size table')
    table_size = raw[1]
    if table_size < 1 or (table_size - 1) % 3 or 1 + table_size > len(raw):
        raise ValueError('invalid event-size table')
    sizes = {}
    for offset in range(2, 1 + table_size, 3):
        command = raw[offset]
        if command in sizes:
            raise ValueError('duplicate event-size entry')
        sizes[command] = struct.unpack_from('>H', raw, offset + 1)[0]
    cursor = 1 + table_size
    starts = ends = 0
    minimums = {0x36: 0x140, 0x37: 0x30, 0x38: 0x21, 0x39: 1}
    while cursor < len(raw):
        command = raw[cursor]
        size = sizes.get(command)
        if size is None or size < minimums.get(command, 0):
            raise ValueError('unknown or undersized event')
        if cursor + 1 + size > len(raw):
            raise ValueError('truncated event')
        if ends:
            raise ValueError('events after Game End')
        if command == 0x36:
            starts += 1
        elif command == 0x39:
            ends += 1
        elif command in (0x37, 0x38) and starts != 1:
            raise ValueError('frame outside a single Game Start')
        cursor += 1 + size
    if starts != 1 or ends != 1:
        raise ValueError('recording needs one Game Start and one Game End')
    replay = slp.parse(path)
    if not replay.pre or not replay.post:
        raise ValueError('recording contains no gameplay frames')
    for inputs in replay.pre.values():
        for controls in inputs.values():
            if not all(math.isfinite(getattr(controls, name)) for name in INPUT_FIELDS[:-1]):
                raise ValueError('non-finite processed input')
    for states in replay.post.values():
        for state in states.values():
            if not all(math.isfinite(getattr(state, name)) for name in
                       ('x', 'y', 'facing', 'percent')):
                raise ValueError('non-finite gameplay state')
    return replay


def _trace(path: Path):
    frames = {}
    with path.open(newline='') as handle:
        rows = csv.DictReader(handle)
        if tuple(rows.fieldnames or ()) != TRACE_COLUMNS:
            raise ValueError('unexpected trace header')
        for row in rows:
            if None in row:
                raise ValueError('extra trace columns')
            frame = int(row['frame'], 0)
            follower = int(row['follower'], 0)
            port = int(row['player'], 0)
            if follower not in (0, 1) or port not in range(4):
                raise ValueError('invalid trace player')
            key = (port, bool(follower))
            players = frames.setdefault(frame, {})
            if key in players:
                raise ValueError('duplicate finalized trace row')
            values = {name: float(row[name]) for name in ('x', 'y', 'facing', 'percent')}
            if not all(math.isfinite(value) for value in values.values()):
                raise ValueError('non-finite trace state')
            players[key] = slp.State(char=int(row['char'], 0),
                                    action_state=int(row['action_state'], 0),
                                    stocks=int(row['stocks'], 0), shield=0.0, **values)
    return frames


def _hashes(path: Path) -> dict[int, int]:
    result = {}
    with path.open(newline='') as handle:
        for row in csv.reader(handle):
            if len(row) != 2:
                raise ValueError('invalid checksum row')
            frame, value = int(row[0]), int(row[1], 16)
            if frame in result or not 0 < value <= 0xFFFFFFFF:
                raise ValueError('duplicate or invalid finalized checksum')
            result[frame] = value
    return result


def verify_pair(fixture: Path, client_a: dict, client_b: dict, *,
                require_mode: str = 'loopback', require_rollback: bool = False) -> dict:
    """Validate a pair; each client supplies trace/recording/hashes paths and evidence.

    Evidence is written by the native mode. `input_delay` is an integer 1..7;
    `local_fixture_reads` counts applied pads after the initial D neutral frames,
    so at least N-D reads are expected for N fixture frames. A successful transport
    handshake alone is insufficient. This function never reads credentials.
    """
    result = dict(ok=False, errors=[], first_divergence=None, first_input_divergence=None,
                  compared_player_frames=0, inputs_equal=False,
                  postframes_equal=False, checksums_equal=False, mode=require_mode)
    errors = result['errors']
    if require_mode not in ('loopback', 'direct'):
        errors.append('unsupported requested mode')
        return result
    try:
        original = _complete_replay(Path(fixture))
    except (OSError, ValueError, IndexError, struct.error) as exc:
        errors.append(f'fixture: {exc}')
        return result
    first, last = original.first_frame, original.last_frame
    if last < first or last - first + 1 > MAX_FIXTURE_FRAMES:
        errors.append('fixture frame span is invalid or implausibly large')
        return result
    frames = set(range(first, last + 1))
    count = len(frames)
    result.update(first_frame=first, last_frame=last)
    if first != -123 or set(original.post) != frames or set(original.pre) != frames:
        errors.append('fixture does not contain a complete frame sequence from -123')
    if any(not {(0, False), (1, False)} <= set(players) for players in original.post.values()):
        errors.append('fixture does not contain both P1 and P2 on every frame')
    allowed_players = {(port, follower) for port in (0, 1) for follower in (False, True)}
    if any(not set(players) <= allowed_players for players in original.post.values()):
        errors.append('fixture has post-frame players outside P1 and P2')
    for port in (0, 1):
        inputs = [original.pre.get(frame, {}).get((port, False)) for frame in range(first, last + 1)]
        if any(value is None for value in inputs):
            errors.append(f'fixture missing P{port + 1} Pre-Frame inputs')
        elif len(set(inputs)) < 2:
            errors.append(f'fixture P{port + 1} controls never change')
    clients = (client_a, client_b)
    evidences = []
    for kind in ('trace', 'recording', 'hashes'):
        try:
            if Path(client_a[kind]).resolve() == Path(client_b[kind]).resolve():
                errors.append(f'clients share the same {kind} artifact')
        except (KeyError, TypeError):
            errors.append(f'missing {kind} artifact')
    traces = []
    hash_sets = []
    post_ok = True
    inputs_ok = True
    for role, client in enumerate(clients, 1):
        prefix = f'P{role}'
        evidence = client.get('evidence', {})
        if not isinstance(evidence, dict):
            errors.append(f'{prefix}: invalid evidence object')
            evidence = {}
        evidences.append(evidence)
        exact = dict(schema=1, mode=require_mode, role=role, connection_selected=True,
                     match_started=True, match_completed=True, first_frame=first,
                     last_frame=last, remote_fixture_reads=0, desyncs=0)
        for key, expected in exact.items():
            value = evidence.get(key)
            if type(value) is not type(expected) or value != expected:
                detail = 'remote fixture reads must be zero' if key == 'remote_fixture_reads' else f'invalid {key}'
                errors.append(f'{prefix}: {detail}')
        delay = evidence.get('input_delay')
        if type(delay) is not int or not 1 <= delay <= 7:
            errors.append(f'{prefix}: invalid input_delay')
            delay = 0
        minimums = dict(confirmed_frame=last, sent_local_frames=count,
                        received_remote_frames=count,
                        local_fixture_reads=max(0, count - delay),
                        pad_packets_received=1, ack_packets_received=1,
                        remote_input_changes=1, rollbacks=int(require_rollback))
        for key, minimum in minimums.items():
            value = evidence.get(key)
            if type(value) is not int or value < minimum:
                detail = ('no received PAD packets' if key == 'pad_packets_received' else
                          'no changing remote input' if key == 'remote_input_changes' else
                          f'insufficient {key}')
                errors.append(f'{prefix}: {detail}')
        if not isinstance(evidence.get('match_id'), str) or not evidence['match_id']:
            errors.append(f'{prefix}: missing match identity')
        try:
            state = _trace(Path(client['trace']))
            recording = _complete_replay(Path(client['recording']))
            traces.append(state)
            hash_sets.append(_hashes(Path(client['hashes'])))
            if set(recording.pre) != frames or any(
                set(recording.pre.get(frame, {})) != set(original.pre.get(frame, {}))
                for frame in frames
            ):
                inputs_ok = False
                errors.append(f'{prefix}: incomplete processed input sequence')
            input_mismatch = None
            for frame in sorted(frames):
                for player, expected in original.pre.get(frame, {}).items():
                    actual = recording.pre.get(frame, {}).get(player)
                    if actual is None:
                        continue
                    for field in INPUT_FIELDS:
                        want, got = getattr(expected, field), getattr(actual, field)
                        equal = want == got if field == 'buttons' else (
                            struct.pack('>f', want) == struct.pack('>f', got))
                        if not equal and input_mismatch is None:
                            input_mismatch = dict(client=role, frame=frame, player=player[0],
                                                  follower=player[1], field=field,
                                                  expected=want, actual=got)
            if input_mismatch:
                inputs_ok = False
                errors.append(f'{prefix}: processed inputs differ from fixture')
                previous = result['first_input_divergence']
                if previous is None or input_mismatch['frame'] < previous['frame']:
                    result['first_input_divergence'] = input_mismatch
            for label, actual in (('trace', state), ('recording', recording.post)):
                comparison = replay_diff.compare(original.post, actual)
                exact_shape = set(actual) == frames and all(
                    set(actual[frame]) == set(original.post[frame]) for frame in frames
                    if frame in actual and frame in original.post)
                if not comparison.ok or not exact_shape:
                    post_ok = False
                    errors.append(f'{prefix}: {label} mismatch or missing gameplay frames')
                if comparison.first is not None:
                    mismatch = comparison.first
                    candidate = dict(client=role, artifact=label, frame=mismatch.frame,
                                     player=mismatch.player[0], follower=mismatch.player[1],
                                     field=mismatch.field, expected=mismatch.original,
                                     actual=mismatch.port)
                    previous = result['first_divergence']
                    if previous is None or candidate['frame'] < previous['frame']:
                        result['first_divergence'] = candidate
            if role == 1:
                result['compared_player_frames'] = sum(len(p) for p in original.post.values())
        except (OSError, KeyError, TypeError, ValueError, IndexError, struct.error) as exc:
            post_ok = False
            inputs_ok = False
            errors.append(f'{prefix}: invalid artifact: {exc}')
    if evidences[0].get('match_id') != evidences[1].get('match_id'):
        errors.append('client match identities differ')
    if evidences[0].get('input_delay') != evidences[1].get('input_delay'):
        errors.append('client input delays differ')
    if require_mode == 'direct':
        # The runner supplies one random 16-byte salt to both processes. Native
        # evidence hashes salted FNV64 UID fingerprints; no IDs appear here.
        def hex_tag(value: object, length: int) -> bool:
            return isinstance(value, str) and bool(re.fullmatch(rf'[0-9a-f]{{{length}}}', value))

        salts = [evidence.get('run_salt') for evidence in evidences]
        locals_ = [evidence.get('account_tag') for evidence in evidences]
        peers = [evidence.get('peer_account_tag') for evidence in evidences]
        if not all(hex_tag(salt, 32) for salt in salts) or salts[0] != salts[1]:
            errors.append('Direct clients lack a shared run salt')
        if not all(hex_tag(tag, 64) for tag in locals_ + peers):
            errors.append('Direct clients lack redacted account identity tags')
        elif locals_[0] == locals_[1] or peers != locals_[::-1]:
            errors.append('Direct account identities are not distinct and reciprocal')
    checksums_ok = len(hash_sets) == 2
    if checksums_ok:
        keys = [set(hashes) for hashes in hash_sets]
        # The checksum after the final simulated frame may be written as the
        # start-of-next-frame boundary. If present, both clients must include it.
        if keys[0] != keys[1] or keys[0] not in (frames, frames | {last + 1}):
            errors.append('missing or extra finalized checksum frames')
            checksums_ok = False
        if any(hash_sets[0].get(frame) != hash_sets[1].get(frame) for frame in keys[0] | keys[1]):
            errors.append('finalized checksums differ')
            checksums_ok = False
    result.update(inputs_equal=inputs_ok and len(traces) == 2,
                  postframes_equal=post_ok and len(traces) == 2,
                  checksums_equal=checksums_ok, ok=not errors)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixture', type=Path)
    parser.add_argument('client_a', type=Path, help='run directory containing evidence.json, state.csv, hashes.csv, match.slp')
    parser.add_argument('client_b', type=Path)
    parser.add_argument('--mode', choices=('loopback', 'direct'), default='loopback')
    parser.add_argument('--require-rollback', action='store_true')
    args = parser.parse_args()
    clients = []
    try:
        for directory in (args.client_a, args.client_b):
            clients.append(dict(evidence=json.loads((directory / 'evidence.json').read_text()),
                                trace=directory / 'state.csv', hashes=directory / 'hashes.csv',
                                recording=directory / 'match.slp'))
        result = verify_pair(args.fixture, *clients, require_mode=args.mode,
                             require_rollback=args.require_rollback)
    except (OSError, ValueError) as exc:
        result = dict(ok=False, errors=[f'cannot read evidence: {exc}'])
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
