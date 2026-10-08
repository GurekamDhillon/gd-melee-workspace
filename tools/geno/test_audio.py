"""Tests for tools/geno/audio.py (run: python -m unittest tools.geno.test_audio -v)."""

import contextlib
import io
import os
import struct
import tempfile
import unittest
import wave

from tools.geno import audio


def write_wav(path, raw, channels, width, rate):
    with wave.open(path, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(width)
        wf.setframerate(rate)
        wf.writeframes(raw)


def pack16(values):
    return struct.pack("<%dh" % len(values), *values)


class _TempDirTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = tmp.name

    def path(self, name):
        return os.path.join(self.dir, name)

    def read(self, name):
        with open(self.path(name), "rb") as fh:
            return fh.read()


class ConvertTests(_TempDirTest):

    def test_16bit_mono_roundtrip(self):
        vals = [i * 300 - 15000 for i in range(100)]
        src, dst = self.path("ramp.wav"), self.path("ramp.gnsnd")
        write_wav(src, pack16(vals), 1, 2, 32000)
        info = audio.convert_wav(src, dst)
        self.assertEqual(info["frames"], 100)
        self.assertEqual(info["channels"], 1)
        self.assertEqual(info["source_rate"], 32000)
        parsed = audio.parse(self.read("ramp.gnsnd"))
        self.assertEqual(parsed["rate"], 32000)
        self.assertEqual(parsed["channels"], 1)
        self.assertEqual(parsed["frames"], 100)
        self.assertEqual(parsed["samples"], vals)

    def test_stereo_16000_to_32000_resamples(self):
        left = [i * 1000 for i in range(10)]
        right = [-i * 1000 for i in range(10)]
        interleaved = [v for pair in zip(left, right) for v in pair]
        src, dst = self.path("st.wav"), self.path("st.gnsnd")
        write_wav(src, pack16(interleaved), 2, 2, 16000)
        info = audio.convert_wav(src, dst)
        self.assertEqual(info["frames"], 20)
        self.assertEqual(info["channels"], 2)
        self.assertEqual(info["source_rate"], 16000)
        parsed = audio.parse(self.read("st.gnsnd"))
        self.assertEqual(parsed["frames"], 20)
        self.assertEqual(parsed["channels"], 2)
        self.assertEqual(parsed["rate"], 32000)
        s = parsed["samples"]
        self.assertEqual(s[0:2], [0, 0])  # first frame preserved
        self.assertEqual(s[-2:], [9000, -9000])  # last frame preserved
        L, R = s[0::2], s[1::2]
        self.assertTrue(all(a < b for a, b in zip(L, L[1:])))
        self.assertTrue(all(a > b for a, b in zip(R, R[1:])))

    def test_8bit_mono_maps_to_signed_16(self):
        src, dst = self.path("u8.wav"), self.path("u8.gnsnd")
        write_wav(src, bytes([128, 255, 0]), 1, 1, 32000)
        audio.convert_wav(src, dst)
        s = audio.parse(self.read("u8.gnsnd"))["samples"]
        self.assertEqual(s[0], 0)
        self.assertEqual(s[1], 127 << 8)  # 32512
        self.assertEqual(s[2], -32768)

    def test_24bit_mono_keeps_top_16_bits(self):
        values = [0x123456, -65536, 0x7FFFFF, -0x800000]
        raw = b"".join((v & 0xFFFFFF).to_bytes(3, "little") for v in values)
        src, dst = self.path("s24.wav"), self.path("s24.gnsnd")
        write_wav(src, raw, 1, 3, 32000)
        audio.convert_wav(src, dst)
        s = audio.parse(self.read("s24.gnsnd"))["samples"]
        self.assertEqual(s, [0x1234, -256, 0x7FFF, -0x8000])

    def test_three_channels_refused(self):
        src, dst = self.path("tri.wav"), self.path("tri.gnsnd")
        write_wav(src, pack16([0] * 12), 3, 2, 32000)
        with self.assertRaises(ValueError) as cm:
            audio.convert_wav(src, dst)
        self.assertIn("channel", str(cm.exception))
        self.assertFalse(os.path.exists(dst))

    def test_eleven_seconds_refused(self):
        src, dst = self.path("long.wav"), self.path("long.gnsnd")
        write_wav(src, b"\0\0" * 352000, 1, 2, 32000)
        with self.assertRaises(ValueError) as cm:
            audio.convert_wav(src, dst)
        self.assertIn("10 seconds", str(cm.exception))
        self.assertFalse(os.path.exists(dst))

    def test_dst_must_end_in_gnsnd(self):
        src, dst = self.path("ok.wav"), self.path("out.wav")
        write_wav(src, pack16([1, 2, 3, 4]), 1, 2, 32000)
        with self.assertRaises(ValueError):
            audio.convert_wav(src, dst)
        self.assertFalse(os.path.exists(dst))

    def test_header_bytes(self):
        src, dst = self.path("four.wav"), self.path("four.gnsnd")
        write_wav(src, pack16([1, 2, 3, 4]), 1, 2, 32000)
        audio.convert_wav(src, dst)
        data = self.read("four.gnsnd")
        self.assertEqual(data[:32], b"GNSD" + struct.pack(">7I", 1, 32000, 1, 4, 32, 8, 0))
        self.assertEqual(len(data), 40)


class ParseTests(_TempDirTest):

    def setUp(self):
        super().setUp()
        src, dst = self.path("four.wav"), self.path("four.gnsnd")
        write_wav(src, pack16([1, 2, 3, 4]), 1, 2, 32000)
        audio.convert_wav(src, dst)
        self.blob = self.read("four.gnsnd")

    def with_field(self, index, value):
        fields = list(struct.unpack(">7I", self.blob[4:32]))
        fields[index] = value
        return self.blob[:4] + struct.pack(">7I", *fields) + self.blob[32:]

    def test_valid_blob(self):
        parsed = audio.parse(self.blob)
        self.assertEqual(parsed["samples"], [1, 2, 3, 4])

    def test_bad_magic(self):
        with self.assertRaises(ValueError) as cm:
            audio.parse(b"XXXX" + self.blob[4:])
        self.assertIn("magic", str(cm.exception))

    def test_wrong_version(self):
        with self.assertRaises(ValueError) as cm:
            audio.parse(self.with_field(0, 2))
        self.assertIn("version", str(cm.exception))

    def test_truncated_body(self):
        with self.assertRaises(ValueError) as cm:
            audio.parse(self.blob[:-2])
        self.assertIn("truncated", str(cm.exception))

    def test_trailing_bytes(self):
        with self.assertRaises(ValueError) as cm:
            audio.parse(self.blob + b"\0\0")
        self.assertIn("trailing", str(cm.exception))

    def test_check_file_reports_problems(self):
        self.assertEqual(audio.check_file(self.path("four.gnsnd")), [])
        with open(self.path("bad.gnsnd"), "wb") as fh:
            fh.write(b"nope")
        self.assertTrue(audio.check_file(self.path("bad.gnsnd")))
        self.assertTrue(audio.check_file(self.path("missing.gnsnd")))


class MainTests(_TempDirTest):

    def test_main_writes_file_and_returns_zero(self):
        src, dst = self.path("four.wav"), self.path("four.gnsnd")
        write_wav(src, pack16([1, 2, 3, 4]), 1, 2, 32000)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = audio.main([src, dst])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.exists(dst))
        line = out.getvalue()
        self.assertIn("4 frames, 1 channel(s)", line)
        self.assertIn("from 32000 Hz", line)

    def test_main_missing_input_returns_one(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = audio.main([self.path("missing.wav"), self.path("x.gnsnd")])
        self.assertEqual(rc, 1)
        self.assertIn("error:", err.getvalue())


if __name__ == "__main__":
    unittest.main()
