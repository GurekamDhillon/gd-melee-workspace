"""Synthetic `.slp` fixture mutation tests; no private replay bytes."""

import struct
import tempfile
import unittest
from pathlib import Path

from alter_fixture import FixtureMutationError, make_altered_p1_fixture


def sample_slp(*, online=True, version=(3, 19, 1), idle=True, truncated=False):
    sizes = {0x36: 0x1A4, 0x37: 0x42, 0x38: 0x54, 0x39: 6}
    events = bytearray((0x35, 1 + len(sizes) * 3))
    for command, size in sizes.items():
        events += bytes((command,)) + struct.pack('>H', size)
    start = bytearray(1 + sizes[0x36])
    start[0] = 0x36
    start[1:4] = bytes(version)
    start[0x1A4] = 8 if online else 2
    events += start
    for frame in (-1, 0, 1, 2):
        for port in (0, 1):
            pre = bytearray(1 + sizes[0x37])
            pre[0] = 0x37
            struct.pack_into('>i', pre, 1, frame)
            pre[5] = port
            events += pre
            post = bytearray(1 + sizes[0x38])
            post[0] = 0x38
            struct.pack_into('>i', post, 1, frame)
            post[5] = port
            struct.pack_into('>H', post, 8, 14 if idle else 30)
            events += post
    events += bytes((0x39,)) + bytes(6)
    raw = b'raw[$U#l' + struct.pack('>I', len(events)) + events + b'private-metadata'
    return raw[:12 + len(events) - 3] if truncated else raw


class FixtureMutationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / 'source.slp'
        self.output = Path(self.temp.name) / 'altered.slp'

    def test_changes_one_p1_a_press_and_preserves_other_bytes(self):
        original = sample_slp()
        self.source.write_bytes(original)
        result = make_altered_p1_fixture(self.source, self.output)
        altered = self.output.read_bytes()
        self.assertEqual(result['frame'], 0)
        self.assertEqual(result['port'], 0)
        self.assertEqual(result['button'], 0x0100)
        self.assertEqual(len(altered), len(original))
        self.assertEqual(self.source.read_bytes(), original)
        changed = {i for i, (a, b) in enumerate(zip(original, altered)) if a != b}
        self.assertEqual(len(changed), 2)  # low bytes of processed and physical A
        for index in changed:
            self.assertEqual(altered[index], 1)
            self.assertEqual(original[index], 0)
        self.assertEqual(altered[-16:], original[-16:])  # metadata kept byte-for-byte

    def test_rejects_ineligible_or_truncated_before_writing(self):
        for raw in (sample_slp(online=False), sample_slp(version=(3, 16, 9)),
                    sample_slp(idle=False), sample_slp(truncated=True)):
            with self.subTest(raw_len=len(raw)):
                self.source.write_bytes(raw)
                with self.assertRaises(FixtureMutationError):
                    make_altered_p1_fixture(self.source, self.output)
                self.assertFalse(self.output.exists())

    def test_refuses_to_overwrite_source_or_existing_destination(self):
        self.source.write_bytes(sample_slp())
        with self.assertRaises(FixtureMutationError):
            make_altered_p1_fixture(self.source, self.source)
        self.output.write_bytes(b'keep')
        with self.assertRaises(FileExistsError):
            make_altered_p1_fixture(self.source, self.output)
        self.assertEqual(self.output.read_bytes(), b'keep')


if __name__ == '__main__':
    unittest.main()
