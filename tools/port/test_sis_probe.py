"""python -m unittest tools/port/test_sis_probe.py: the text gate's Python decoder agrees with the C one, and reads an archive built from invented bytes.

Nothing here touches a disc: the archive is made in memory from invented strings. GW_MELEE (or ../melee) supplies the font tables and the C decoder's source.
"""
import os
import re
import struct
import unittest

import sis_probe as p

GAME = os.environ.get("GW_MELEE") or os.path.join(os.path.dirname(__file__), "..", "..", "melee")


def c_latin_pairs():
    """The (hi, lo) -> char pairs at_sjis_to_utf8 in gw_ui_retailtext.c maps, read from its source."""
    with open(os.path.join(GAME, "pc/platform/gw_ui_retailtext.c"), encoding="utf-8") as fh:
        src = fh.read()
    body = src[src.index("int at_sjis_to_utf8"):src.index("int at_sis_decode")]
    pairs = {}
    for lo in range(10):
        pairs[(0x82, 0x4F + lo)] = chr(48 + lo)
    for i in range(26):
        pairs[(0x82, 0x60 + i)] = chr(65 + i)
        pairs[(0x82, 0x81 + i)] = chr(97 + i)
    assert "hi == 0x82 && lo >= 0x4F && lo <= 0x58" in body and "lo >= 0x60 && lo <= 0x79" in body and "lo >= 0x81 && lo <= 0x9A" in body
    for m in re.finditer(r"case 0x([0-9A-Fa-f]{2}): c = '(\\?.)';", body):
        ch = m.group(2)
        pairs[(0x81, int(m.group(1), 16))] = ch[1] if ch.startswith("\\") else ch
    return pairs


class Probe(unittest.TestCase):
    def test_latin_set_is_the_c_one(self):
        self.assertEqual(p._latin(), c_latin_pairs())

    def test_opcode_operands_are_the_c_ones(self):
        with open(os.path.join(GAME, "pc/platform/gw_ui_retailtext.c"), encoding="utf-8") as fh:
            src = fh.read()
        m = re.search(r"OPERANDS\[32\] = \{(.*?)\};", src, re.S)
        self.assertEqual([int(x) for x in re.findall(r"-?\d+", m.group(1))], p.OPERANDS)

    def test_font_tables_are_the_decomp_tables(self):
        g, s = p.font_tables(GAME)
        self.assertEqual((len(g), len(s)), (0x240, 0x240))
        self.assertEqual(g[:4], bytes([0x20, 0xE3, 0x20, 0xEC]))     # the first glyph codes of the atlas
        self.assertEqual(s[:4], bytes([0x81, 0x40, 0x81, 0x49]))     # a full-width space, then '!'

    def test_decode_counts(self):
        lut = {0x2041: (0x82, 0x60), 0x2062: (0x82, 0x82), 0x2077: (0x83, 0x41)}
        self.assertEqual(p.decode(bytes([10, 0, 0, 0, 0, 0x20, 0x41, 0x20, 0x62, 0]), lut), (2, 0, 1, 0, 0))
        self.assertEqual(p.decode(bytes([0x20, 0x41, 0x20, 0x77, 0x40, 0x00, 0]), lut), (3, 2, 0, 0, 0))   # kana and an unknown glyph (>= 0x4000 symbols too)
        self.assertEqual(p.decode(bytes([0x20, 0x41, 8, 0, 0, 0, 0]), lut), (1, 0, 0, 1, 0))
        self.assertEqual(p.decode(bytes([0x20, 0x41, 29, 0]), lut), (1, 0, 0, 0, 1))
        self.assertEqual(p.decode(bytes([0x20]), lut)[4], 1)                                              # a cut glyph is bad, never read past
        codes = {}
        p.decode(bytes([0x20, 0x77, 0x40, 0x00, 0]), lut, codes)
        self.assertEqual(codes, {(0x83, 0x41): 1, ("glyph", 0x4000): 1})

    def test_verdicts(self):
        self.assertEqual(p.verdict(100, 0, 0), "GO")
        self.assertEqual(p.verdict(100, 1, 0), "PARTIAL")
        self.assertEqual(p.verdict(100, 2, 0), "NO-GO")
        self.assertEqual(p.verdict(100, 0, 1), "PARTIAL" if 0 * 100 < 100 * 2 else "NO-GO")
        self.assertEqual(p.verdict(0, 0, 0), "EMPTY")

    def test_archive_table_from_invented_bytes(self):
        # header: file size, data size, reloc count, public count, extern count, 3 pad words; then data, relocs, one public symbol "SIS_X"
        s1 = bytes([0x20, 0x41, 0])                      # one invented stream
        s2 = bytes([0x20, 0x62, 0x20, 0x41, 0])
        table_at = 0
        data = bytearray(16)                             # two pointer slots and two more (null) words
        s1_at, s2_at = len(data), len(data) + len(s1)
        data += s1 + s2
        struct.pack_into(">I", data, 0, 16)              # slot 0 -> the first stream (the table is 16 bytes long, so 4 slots)
        struct.pack_into(">I", data, 4, 0)               # slot 1 null
        struct.pack_into(">I", data, 8, s2_at)
        struct.pack_into(">I", data, 0, s1_at)           # slot 0 points at s1 (s1_at == 16 here: the table ends where the streams begin)
        while len(data) % 4:
            data += b"\0"
        relocs = struct.pack(">II", 0, 8)
        name = b"SIS_X\0"
        pub = struct.pack(">II", table_at, 0)
        blob = struct.pack(">5I", 0, len(data), 2, 1, 0) + b"\0" * 12 + bytes(data) + relocs + pub + name
        t = p.archive_table(blob, "SIS_X")
        self.assertEqual(len(t), 4)
        self.assertTrue(t[0].startswith(s1) and t[1] is None and t[2].startswith(s2) and t[3] is None)


if __name__ == "__main__":
    unittest.main()
