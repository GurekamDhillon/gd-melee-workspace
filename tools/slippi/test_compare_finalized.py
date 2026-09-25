"""Synthetic acceptance evidence; no game assets or real account data."""

import copy
import csv
import struct
import tempfile
import unittest
from pathlib import Path

from compare_finalized import verify_pair


FRAMES = range(-123, -120)
HEADER = ('frame', 'player', 'follower', 'char', 'action_state', 'x', 'y',
          'facing', 'percent', 'stocks')


def replay_bytes(*, ended=True, extra_post=False, metadata=False,
                 alter_input=False, omit_input=False):
    sizes = {0x36: 0x1A4, 0x37: 0x42, 0x38: 0x54, 0x39: 6}
    raw = bytearray((0x35, 1 + len(sizes) * 3))
    for command, size in sizes.items():
        raw += bytes((command,)) + struct.pack('>H', size)
    start = bytearray(1 + sizes[0x36])
    start[0:5] = bytes((0x36, 3, 19, 1, 0))
    start[0x1A4] = 8
    raw += start
    for frame in FRAMES:
        for port in (0, 1):
            pre = bytearray(1 + sizes[0x37])
            pre[0] = 0x37
            struct.pack_into('>i', pre, 1, frame)
            pre[5] = port
            struct.pack_into('>I', pre, 0x2D, 0x100 if frame % 2 else 0)
            if alter_input and frame == -122 and port == 0:
                struct.pack_into('>I', pre, 0x2D, 0x200)
            if not (omit_input and frame == -122 and port == 0):
                raw += pre
            post = bytearray(1 + sizes[0x38])
            post[0] = 0x38
            struct.pack_into('>i', post, 1, frame)
            post[5] = port
            post[7] = 2
            struct.pack_into('>H', post, 8, 14)
            for offset, value in ((0x0A, frame + 123 + port), (0x0E, 0),
                                  (0x12, 1), (0x16, 0), (0x1A, 60)):
                struct.pack_into('>f', post, offset, value)
            post[0x21] = 4
            raw += post
    if extra_post:
        post = bytearray(1 + sizes[0x38])
        post[0] = 0x38
        struct.pack_into('>i', post, 1, -121)
        post[5] = 2
        raw += post
    if ended:
        raw += bytes((0x39, 7, 0, 0, 0, 0, 0))
    trailer = b'U\x08metadata{U\x04noteSU\x02{}}}' if metadata else b'}'
    return b'{U\x03raw[$U#l' + struct.pack('>I', len(raw)) + raw + trailer


class AcceptanceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.fixture = self.root / 'fixture.slp'
        self.fixture.write_bytes(replay_bytes())
        self.clients = []
        for role in (1, 2):
            directory = self.root / str(role)
            directory.mkdir()
            trace = directory / 'state.csv'
            with trace.open('w', newline='') as handle:
                writer = csv.writer(handle)
                writer.writerow(HEADER)
                for frame in FRAMES:
                    for port in (0, 1):
                        writer.writerow((frame, port, 0, 2, 14, frame + 123 + port,
                                         0, 1, 0, 4))
            recording = directory / 'match.slp'
            recording.write_bytes(replay_bytes())
            hashes = directory / 'hashes.csv'
            hashes.write_text(''.join(f'{frame},{frame + 124:08X}\n' for frame in FRAMES))
            evidence = dict(schema=1, mode='loopback', role=role, match_id='synthetic',
                            connection_selected=True, match_started=True, match_completed=True,
                            first_frame=-123, last_frame=-121, confirmed_frame=-121,
                            sent_local_frames=3, received_remote_frames=3,
                            remote_input_changes=2, remote_fixture_reads=0,
                            input_delay=2, local_fixture_reads=1, pad_packets_received=3,
                            ack_packets_received=3, rollbacks=1, desyncs=0)
            self.clients.append(dict(trace=trace, recording=recording, hashes=hashes,
                                     evidence=evidence))

    def verify(self, **kwargs):
        return verify_pair(self.fixture, self.clients[0], self.clients[1], **kwargs)

    def test_complete_pair_passes(self):
        result = self.verify(require_rollback=True)
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['compared_player_frames'], 6)

    def test_changed_controls_fail_even_when_all_poststates_match(self):
        for client in self.clients:
            client['recording'].write_bytes(replay_bytes(alter_input=True))
        result = self.verify()
        self.assertFalse(result['ok'])
        self.assertTrue(result['postframes_equal'])
        self.assertFalse(result['inputs_equal'])
        self.assertEqual(result['first_input_divergence']['frame'], -122)
        self.assertEqual(result['first_input_divergence']['field'], 'buttons')

    def test_missing_processed_input_fails_with_complete_poststates(self):
        self.clients[1]['recording'].write_bytes(replay_bytes(omit_input=True))
        result = self.verify()
        self.assertFalse(result['ok'])
        self.assertIn('incomplete processed input sequence', ' '.join(result['errors']))

    def test_fixture_reads_follow_input_delay(self):
        self.assertTrue(self.verify()['ok'])  # N=3, D=2, one applied fixture read.
        self.clients[0]['evidence']['local_fixture_reads'] = 0
        self.assertIn('insufficient local_fixture_reads', ' '.join(self.verify()['errors']))

    def test_input_delay_must_be_integer_in_supported_range(self):
        for bad in (None, True, '2', 0, 8):
            with self.subTest(bad=bad):
                self.clients[0]['evidence']['input_delay'] = bad
                self.assertIn('invalid input_delay', ' '.join(self.verify()['errors']))

    def test_client_input_delays_must_match(self):
        self.clients[1]['evidence']['input_delay'] = 3
        self.assertIn('client input delays differ', ' '.join(self.verify()['errors']))

    def test_identical_title_screens_fail(self):
        for client in self.clients:
            client['evidence']['match_started'] = False
        self.assertFalse(self.verify()['ok'])

    def test_remote_fixture_read_fails(self):
        self.clients[0]['evidence']['remote_fixture_reads'] = 1
        self.assertIn('remote fixture', ' '.join(self.verify()['errors']))

    def test_no_packets_and_all_neutral_fail(self):
        self.clients[0]['evidence']['pad_packets_received'] = 0
        self.clients[1]['evidence']['remote_input_changes'] = 0
        result = self.verify()
        self.assertFalse(result['ok'])
        self.assertTrue(any('PAD' in error for error in result['errors']))
        self.assertTrue(any('changing' in error for error in result['errors']))

    def test_missing_last_trace_frame_fails(self):
        path = self.clients[0]['trace']
        path.write_text('\n'.join(path.read_text().splitlines()[:-2]) + '\n')
        self.assertFalse(self.verify()['ok'])

    def test_input_negative_control_reports_first_divergence(self):
        path = self.clients[0]['trace']
        path.write_text(path.read_text().replace('-122,0,0,2,14,1,', '-122,0,0,2,14,9,'))
        result = self.verify()
        self.assertFalse(result['ok'])
        self.assertEqual(result['first_divergence']['frame'], -122)
        self.assertEqual(result['first_divergence']['field'], 'x')

    def test_truncated_recording_fails(self):
        path = self.clients[0]['recording']
        path.write_bytes(path.read_bytes()[:-5])
        self.assertFalse(self.verify()['ok'])

    def test_missing_outer_container_end_fails(self):
        self.clients[0]['recording'].write_bytes(replay_bytes()[:-1])
        self.assertFalse(self.verify()['ok'])

    def test_missing_outer_end_after_metadata_fails(self):
        self.clients[0]['recording'].write_bytes(replay_bytes(metadata=True))
        self.assertTrue(self.verify()['ok'])
        self.clients[0]['recording'].write_bytes(replay_bytes(metadata=True)[:-1])
        self.assertFalse(self.verify()['ok'])

    def test_extra_finalized_trace_and_checksum_frame_fails(self):
        with self.clients[0]['trace'].open('a') as handle:
            handle.write('999,0,0,2,14,9,0,1,0,4\n')
        with self.clients[0]['hashes'].open('a') as handle:
            handle.write('999,DEADBEEF\n')
        self.assertFalse(self.verify()['ok'])

    def test_shared_matching_checksum_boundary_passes(self):
        for client in self.clients:
            with client['hashes'].open('a') as handle:
                handle.write('-120,DEADBEEF\n')
        self.assertTrue(self.verify()['ok'])
        self.clients[1]['hashes'].write_text(
            self.clients[1]['hashes'].read_text().replace('DEADBEEF', 'FEEDBEEF'))
        self.assertFalse(self.verify()['ok'])

    def test_extra_recording_player_fails(self):
        self.clients[0]['recording'].write_bytes(replay_bytes(extra_post=True))
        self.assertFalse(self.verify()['ok'])

    def test_all_neutral_fixture_fails_even_with_change_counter(self):
        data = replay_bytes().replace(b'\x00\x00\x01\x00', b'\x00\x00\x00\x00')
        self.fixture.write_bytes(data)
        self.assertFalse(self.verify()['ok'])

    def test_invalid_evidence_is_structured_failure(self):
        self.clients[0]['evidence'] = []
        result = self.verify()
        self.assertFalse(result['ok'])
        self.assertTrue(result['errors'])

    def test_direct_requires_distinct_reciprocal_salted_tags(self):
        for client in self.clients:
            client['evidence']['mode'] = 'direct'
            client['evidence']['run_salt'] = 'ab' * 16
        self.clients[0]['evidence'].update(account_tag='01' * 32,
                                           peer_account_tag='02' * 32)
        self.clients[1]['evidence'].update(account_tag='02' * 32,
                                           peer_account_tag='01' * 32)
        self.assertTrue(self.verify(require_mode='direct')['ok'])
        self.clients[1]['evidence']['peer_account_tag'] = '03' * 32
        self.assertFalse(self.verify(require_mode='direct')['ok'])
        self.clients[1]['evidence']['peer_account_tag'] = '01' * 32
        self.clients[1]['evidence']['account_tag'] = '01' * 32
        self.assertFalse(self.verify(require_mode='direct')['ok'])

    def test_implausible_fixture_frame_span_fails_safely(self):
        data = replay_bytes()
        # The last Post-Frame event's frame index becomes INT32_MAX.
        end = data.rfind(bytes((0x38,)))
        assert end >= 0
        data = data[:end + 1] + struct.pack('>i', 0x7fffffff) + data[end + 5:]
        self.fixture.write_bytes(data)
        result = self.verify()
        self.assertFalse(result['ok'])
        self.assertTrue(any('frame span' in error for error in result['errors']))

    def test_missing_game_end_fails(self):
        self.clients[0]['recording'].write_bytes(replay_bytes(ended=False))
        self.assertFalse(self.verify()['ok'])

    def test_checksum_mismatch_and_missing_checksum_fail(self):
        self.clients[0]['hashes'].write_text('-123,00000001\n-122,000000FF\n')
        self.assertFalse(self.verify()['ok'])

    def test_duplicate_confirmed_trace_row_fails(self):
        path = self.clients[0]['trace']
        with path.open('a') as handle:
            handle.write(path.read_text().splitlines()[-1] + '\n')
        self.assertFalse(self.verify()['ok'])

    def test_direct_requirement_rejects_loopback(self):
        self.assertFalse(self.verify(require_mode='direct')['ok'])

    def test_same_artifacts_cannot_stand_for_two_clients(self):
        self.clients[1] = copy.deepcopy(self.clients[0])
        self.clients[1]['evidence']['role'] = 2
        self.assertFalse(self.verify()['ok'])


if __name__ == '__main__':
    unittest.main()
