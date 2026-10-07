"""The retail text gate (Atlas step 8, Task 1): can the disc's own words be decoded at run time with the font's reverse table?

    python tools/port/sis_probe.py [--iso-env GW_ISO_VANILLA] [--melee PATH] [--archive SdMenu.usd] [--symbol SIS_MenuData]

Reads one SIS text archive straight out of a disc image IN MEMORY (the disc path comes from the named environment variable and is never
printed), walks every string of its SIS table with the same rules as pc/platform/gw_ui_retailtext.c (the opcode operand sizes of
HSD_SisLib_803A84BC, the font atlas's own SJIS pairs read from src/sysdolphin/baselib/hsd_3A76.c run in reverse) and prints COUNTS ONLY: strings,
characters, unknown glyphs, stops. With --unknown it also lists, per group, the SJIS code (or the glyph number when the font table has no
code) of each glyph that did not decode and how often: character codes and counts, never decoded text. Nothing decoded is printed, logged, written or kept: the strings live in a Python variable for one loop.
That is the rule of the step (no disc-derived data in either repo or on disk) and tools/port/check_no_disc_text.py guards the C side.

Verdict per group, by the share of glyphs that did not decode (u / c):
  GO       0 unknown glyphs and no bad opcode: the screen shows the disc's words.
  PARTIAL  under 2 percent unknown: the strings that decode are shown, a row with an unknown glyph keeps its authored label.
  NO-GO    anything else: the screen ships without the disc's words.
"""
import argparse
import os
import re
import struct
import sys

OPERANDS = [0, 0, 0, 0, 0, 2, 4, 4, 4, 4, 4, 0, 3, 0, 4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1, -1, -1, -1, -1]
LATIN = {}


def _latin():
    """The SJIS pairs gw_ui_retailtext.c's at_sjis_to_utf8 maps (kept in step with it by test_sis_probe.py)."""
    if LATIN:
        return LATIN
    for i in range(10):
        LATIN[(0x82, 0x4F + i)] = chr(48 + i)
    for i in range(26):
        LATIN[(0x82, 0x60 + i)] = chr(65 + i)
        LATIN[(0x82, 0x81 + i)] = chr(97 + i)
    for lo, c in ((0x40, " "), (0x43, ","), (0x44, "."), (0x46, ":"), (0x47, ";"), (0x48, "?"), (0x49, "!"), (0x51, "_"), (0x5E, "/"), (0x66, "'"),
                  (0x68, '"'), (0x69, "("), (0x6A, ")"), (0x6D, "["), (0x6E, "]"), (0x6F, "{"), (0x70, "}"), (0x7B, "+"), (0x7C, "-"), (0x81, "="),
                  (0x83, "<"), (0x84, ">"), (0x90, "$"), (0x93, "%"), (0x94, "#"), (0x95, "&"), (0x96, "*"), (0x97, "@")):
        LATIN[(0x81, lo)] = c
    return LATIN


def font_tables(melee):
    """(glyph pairs, SJIS pairs) from the decompiled font tables in hsd_3A76.c: both are 0x240 bytes, 0x120 pairs."""
    with open(os.path.join(melee, "src/sysdolphin/baselib/hsd_3A76.c"), encoding="utf-8", errors="replace") as fh:
        src = fh.read()

    def arr(name):
        m = re.search(r"\b%s\[0x240\]\s*=\s*\{(.*?)\};" % name, src, re.S)
        if not m:
            raise SystemExit("font table %s not found" % name)
        return bytes(int(x, 16) for x in re.findall(r"0x([0-9A-Fa-f]{1,2})", m.group(1)))

    g, s = arr("HSD_SisLib_8040C680"), arr("lbl_8040C8C0")
    if len(g) != 0x240 or len(s) != 0x240:
        raise SystemExit("font table size")
    return g, s


def decode(stream, lut, unknown_codes=None):
    """chars, unknown, controls, jumps, bad for one SIS stream (bytes from the first item), the text itself dropped.
    unknown_codes: an optional dict that counts the SJIS pair (or the glyph when the table has none) of each unknown glyph: codes, never text."""
    glyph_to_sjis = lut
    i = chars = unknown = controls = jumps = bad = 0
    latin = _latin()
    for _ in range(1024):
        if i >= len(stream):
            bad += 1
            break
        op = stream[i]
        if op >= 0x20:
            if i + 1 >= len(stream):
                bad += 1
                break
            g = (op << 8) | stream[i + 1]
            i += 2
            chars += 1
            pair = glyph_to_sjis.get(g)
            if pair is None or pair not in latin:
                unknown += 1
                if unknown_codes is not None:
                    key = pair if pair is not None else ("glyph", g)
                    unknown_codes[key] = unknown_codes.get(key, 0) + 1
            continue
        if op == 0:
            break
        if op in (8, 9):
            jumps += 1
            break
        if OPERANDS[op] < 0:
            bad += 1
            break
        if i + 1 + OPERANDS[op] > len(stream):      # its operand bytes are cut: bad, as gw_ui_retailtext.c says
            bad += 1
            break
        if op == 3:
            chars += 1
        i += 1 + OPERANDS[op]
        controls += 1
    return chars, unknown, controls, jumps, bad


class Disc:
    """A GameCube disc image opened read-only; files are read into memory by name."""

    def __init__(self, path):
        self.f = open(path, "rb")
        h = self.f.read(0x440)
        if len(h) < 0x440 or struct.unpack(">I", h[0x1C:0x20])[0] != 0xC2339F3D:
            raise SystemExit("not a GameCube disc image")
        off, size = struct.unpack(">II", h[0x424:0x42C])
        self.f.seek(off)
        self.fst = self.f.read(size)
        self.n = struct.unpack(">I", self.fst[8:12])[0]

    def find(self, basename):
        for idx in range(1, self.n):
            w0, off, ln = struct.unpack(">III", self.fst[idx * 12:idx * 12 + 12])
            if (w0 >> 24) & 0xFF:
                continue
            start = self.n * 12 + (w0 & 0xFFFFFF)
            name = self.fst[start:self.fst.find(b"\0", start)].decode("shift_jis", "replace")
            if name.lower() == basename.lower():
                return off, ln
        return None

    def read(self, basename):
        e = self.find(basename)
        if e is None:
            return None
        self.f.seek(e[0])
        return self.f.read(e[1])


def archive_table(data, symbol):
    """The pointer table of one public symbol of an HSD archive: [stream bytes from each non-null slot], None for a null slot."""
    file_size, data_size, reloc_n, pub_n, ext_n = struct.unpack(">5I", data[:20])
    base = 0x20
    reloc_at = base + data_size
    pub_at = reloc_at + reloc_n * 4
    str_at = pub_at + pub_n * 8 + ext_n * 8
    sym_off = None
    for k in range(pub_n):
        off, name_off = struct.unpack(">II", data[pub_at + k * 8:pub_at + k * 8 + 8])
        s = str_at + name_off
        if data[s:data.index(b"\0", s)].decode("ascii", "replace") == symbol:
            sym_off = off
    if sym_off is None:
        raise SystemExit("symbol %s not found" % symbol)
    first = struct.unpack(">I", data[base + sym_off:base + sym_off + 4])[0]
    count = (first - sym_off) // 4 if first > sym_off else 0
    out = []
    for k in range(count):
        p = struct.unpack(">I", data[base + sym_off + k * 4:base + sym_off + k * 4 + 4])[0]
        out.append(data[base + p:base + data_size] if 0 < p < data_size else None)
    return out


# the groups the screens read (indices from the retail sources; see the plan's Task 1 step 8). Anything else is "other".
GROUPS = [
    ("event names", [0x154 + 2 * k for k in range(51)]),
    ("event descriptions", [0x155 + 2 * k for k in range(51)]),
    ("misc record labels", list(range(0xC9, 0xE7))),
    ("sound test names", list(range(0xE7, 0x13E))),
    ("bonus record lines", list(range(0x1BA, 0x1BA + 3 * 30))),
    # un_802FE3F8(id, 0x4BD, ...): id k is 0x4BD + k, except ids 62 to 65 (ifprize.c un_803F9B30: 63, 67, 68, 62); id 0x3E is never shown
    ("special messages", [0x4BD + k for k in range(62) if k != 0x3E] + [0x4BD + 67, 0x4BD + 68, 0x4BD + 62]),
]


def verdict(chars, unknown, bad):
    if chars == 0:
        return "EMPTY"
    if unknown == 0 and bad == 0:
        return "GO"
    return "PARTIAL" if unknown * 100 < chars * 2 else "NO-GO"


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--iso-env", default="GW_ISO_VANILLA")
    ap.add_argument("--melee", default=os.environ.get("GW_MELEE", ""))
    ap.add_argument("--archive", default="SdMenu.usd")
    ap.add_argument("--symbol", default="SIS_MenuData")
    ap.add_argument("--all", action="store_true", help="also report the whole table")
    ap.add_argument("--unknown", action="store_true", help="list the SJIS codes of the unknown glyphs per group (codes and counts, never text)")
    a = ap.parse_args(argv)
    iso = os.environ.get(a.iso_env, "")
    if not iso or not os.path.isfile(iso):
        print("sis_probe: the %s environment variable names no disc image" % a.iso_env)
        return 2
    g, s = font_tables(a.melee)
    lut = {}
    for k in range(0x120):
        lut.setdefault((g[2 * k] << 8) | g[2 * k + 1], (s[2 * k], s[2 * k + 1]))
    disc = Disc(iso)
    data = disc.read(a.archive)
    if data is None:
        print("sis_probe: %s is not on the disc" % a.archive)
        return 2
    table = archive_table(data, a.symbol)
    print("sis_probe: %s %s: %d table slots" % (a.archive, a.symbol, len(table)))
    rc = 0
    groups = GROUPS if a.archive.lower().startswith("sdmenu") else [("all", list(range(len(table))))]
    for name, idxs in groups:
        n = c = u = ctl = jmp = bad = missing = 0
        codes = {} if a.unknown else None
        for i in idxs:
            if i >= len(table) or table[i] is None:
                missing += 1
                continue
            ch, un, co, ju, ba = decode(table[i], lut, codes)
            n += 1; c += ch; u += un; ctl += co; jmp += ju; bad += ba
        v = verdict(c, u, bad)
        print("sis probe %-20s: %3d strings, %5d chars, %4d unknown glyphs, %d jumps, %d bad, %d missing -> %s" % (name, n, c, u, jmp, bad, missing, v))
        if codes:
            print("    unknown codes: " + ", ".join("%s x%d" % (("%02X%02X" % k) if len(k) == 2 and k[0] != "glyph" else "glyph %04X" % k[1], codes[k]) for k in sorted(codes, key=lambda k: -codes[k])))
        if v == "NO-GO":
            rc = 1
    if a.all:
        n = c = u = bad = 0
        for t in table:
            if t is None:
                continue
            ch, un, co, ju, ba = decode(t, lut)
            n += 1; c += ch; u += un; bad += ba
        print("sis probe %-20s: %3d strings, %5d chars, %4d unknown glyphs, %d bad -> %s" % ("whole table", n, c, u, bad, verdict(c, u, bad)))
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
