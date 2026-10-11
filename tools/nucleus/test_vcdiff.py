#!/usr/bin/env python3
"""Tests for vcdiff.py (against the third-party xdelta.exe) and iso_diff.py."""
import os
import random
import struct
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import iso_diff  # noqa: E402
import vcdiff  # noqa: E402

XD = os.environ.get("XDELTA_EXE", r"E:/Projects/Melee Workspace/_research/tm/Build TM Start.dol/xdelta.exe")
SETTINGS = [[], ["-S", "none"], ["-S", "djw"], ["-S", "fgk"], ["-S", "lzma"]] + [["-%d" % i] for i in range(10)] \
    + [["-0", "-S", "none"], ["-9", "-S", "lzma"], ["-B", "4096", "-W", "16384"]]


def make_pair(seed=1):
    rnd = random.Random(seed)
    blocks = [bytes(rnd.getrandbits(8) for _ in range(512)) for _ in range(40)]
    src = b"".join(rnd.choice(blocks) for _ in range(300)) + bytes(2000)
    tgt = bytearray(src)
    for _ in range(30):
        p = rnd.randrange(len(tgt) - 100)
        tgt[p:p + rnd.randrange(1, 90)] = bytes(rnd.getrandbits(8) for _ in range(rnd.randrange(1, 90)))
    tgt[5000:5000] = b"ABCABCABC" * 500 + bytes(777)  # insert run/overlap material
    tgt += b"".join(rnd.choice(blocks) for _ in range(20))
    return src, bytes(tgt)


def describe(patch):
    hi = patch[4]
    return vcdiff.SECONDARY.get(patch[5], "id%d" % patch[5]) if hi & 1 else "none"


@unittest.skipUnless(os.path.exists(XD), "xdelta.exe not available")
class XdeltaRoundTrip(unittest.TestCase):
    results = {}

    def test_settings(self):
        src, tgt = make_pair()
        with tempfile.TemporaryDirectory() as d:
            sp, tp, pp = (os.path.join(d, n) for n in ("s", "t", "p"))
            open(sp, "wb").write(src)
            open(tp, "wb").write(tgt)
            for st in SETTINGS:
                if os.path.exists(pp):
                    os.remove(pp)
                r = subprocess.run([XD, "-e", "-f"] + st + ["-s", sp, tp, pp], capture_output=True)
                if r.returncode != 0:
                    print("  xdelta %-14s encode failed: %s" % (" ".join(st), r.stderr.decode(errors="replace").strip()[:80]))
                    continue
                patch = open(pp, "rb").read()  # noqa
                sec = describe(patch)
                try:
                    ok = vcdiff.apply(src, patch) == tgt
                    res = "OK" if ok else "MISMATCH"
                    self.assertTrue(ok, st)
                except vcdiff.VcdiffError as e:
                    res = "ERR " + str(e)
                    self.assertIn(sec, ("djw", "fgk"), (st, str(e)))
                print("  xdelta %-16s secondary=%-5s size=%6d -> %s" % (" ".join(st) or "(default)", sec, len(patch), res))

    def test_cli_streaming(self):
        src, tgt = make_pair(2)
        with tempfile.TemporaryDirectory() as d:
            sp, tp, pp, op = (os.path.join(d, n) for n in ("s", "t", "p", "o"))
            open(sp, "wb").write(src)
            open(tp, "wb").write(tgt)
            subprocess.run([XD, "-e", "-f", "-S", "none", "-s", sp, tp, pp], check=True, capture_output=True)
            vcdiff.apply_files(sp, pp, op)
            self.assertEqual(open(op, "rb").read(), tgt)


class Handmade(unittest.TestCase):
    def test_lzma_secondary_selfmade(self):
        # hand-built patch: ADD "hello world" with the data section xz-compressed (id 32),
        # adler32 present. Not produced by xdelta3 (the local exe has no lzma): layout only.
        import lzma
        import zlib
        raw = b"hello world"
        comp = bytes([len(raw)]) + lzma.compress(raw, format=lzma.FORMAT_XZ)
        inst = bytes([1, 11])  # opcode 1 = ADD, size from the instruction stream
        # window: tlen=11, delta_ind=1 (data compressed), data/inst/addr lengths, adler32
        delta = bytes([11, 1, len(comp), len(inst), 0]) + struct.pack(">I", zlib.adler32(raw)) + comp + inst
        patch = bytes([0xD6, 0xC3, 0xC4, 0, 1, 32]) + bytes([4, len(delta)]) + delta
        self.assertEqual(vcdiff.apply(b"", patch), raw)

    def test_bad_magic(self):
        with self.assertRaises(vcdiff.VcdiffError):
            vcdiff.apply(b"", b"nope")

    def test_secondary_named(self):
        # header with DECOMPRESS, djw, then a window whose data section is flagged compressed
        p = b"\xd6\xc3\xc4\x00\x01\x01" + b"\x00" + bytes([5, 1, 1, 1, 1, 1, 0]) + b"x" * 3
        with self.assertRaises(vcdiff.VcdiffError) as c:
            vcdiff.apply(b"", p)
        self.assertIn("djw", str(c.exception))


def build_iso(path, files, dol=b"DOL0" + bytes(0x200)):
    """Minimal GCM: header 0x440, FST right after, dol, then files. files: {path: bytes}."""
    dirs, entries = {}, []

    def walk(prefix):
        names = sorted({p[len(prefix):].split("/")[0] for p in files if p.startswith(prefix)})
        for n in names:
            if prefix + n in files:
                entries.append((0, n, prefix + n))
            else:
                idx = len(entries)
                entries.append((1, n, None))
                walk(prefix + n + "/")
                entries[idx] = (1, n, len(entries))
    walk("")
    nt = b"".join(n.encode() + b"\0" for _, n, _ in entries)
    fst_off = 0x440
    fst_size = 12 * (len(entries) + 1) + len(nt)
    dol_off = (fst_off + fst_size + 0x1F) & ~0x1F
    pos = (dol_off + len(dol) + 0x1F) & ~0x1F
    # dol header: one text section at 0x100 of its own size
    dolb = bytearray(0x300)
    dolb[0x100:0x100 + len(dol)] = dol
    struct.pack_into(">I", dolb, 0, 0x100)
    struct.pack_into(">I", dolb, 0x90, len(dolb) - 0x100)
    dol = bytes(dolb)
    pos = (dol_off + len(dol) + 0x1F) & ~0x1F
    fst, nameo, body = struct.pack(">BBHII", 1, 0, 0, 0, len(entries) + 1), 0, b""
    out = bytearray()
    for flag, n, v in entries:
        if flag:
            fst += struct.pack(">I", nameo)[1:].rjust(3, b"\0") and bytes([1]) + struct.pack(">I", nameo)[1:] + struct.pack(">II", 0, v + 1)
        else:
            data = files[v]
            fst += bytes([0]) + struct.pack(">I", nameo)[1:] + struct.pack(">II", pos + len(body), len(data))
            body += data.ljust((len(data) + 0x1F) & ~0x1F, b"\0")
        nameo += len(n.encode()) + 1
    img = bytearray(pos + len(body))
    struct.pack_into(">III", img, 0x420, dol_off, fst_off, fst_size)
    img[fst_off:fst_off + len(fst)] = fst
    img[fst_off + len(fst):fst_off + len(fst) + len(nt)] = nt
    img[dol_off:dol_off + len(dol)] = dol
    img[pos:] = body
    open(path, "wb").write(img)


class IsoDiff(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()

    def run_diff(self, a, b, out=None):
        import io
        import contextlib
        pa, pb = os.path.join(self.d, "a.iso"), os.path.join(self.d, "b.iso")
        build_iso(pa, a[0], a[1] if len(a) > 1 else b"DOL0")
        build_iso(pb, b[0], b[1] if len(b) > 1 else b"DOL0")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            iso_diff.main([pa, pb] + (["--out", out] if out else []))
        return buf.getvalue()

    BASE = {"PlCo.dat": b"A" * 100, "audio/x.hps": b"B" * 70, "audio/sub/y.hps": b"C" * 10, "Z.dat": b"zz"}

    def test_loose(self):
        new = dict(self.BASE, **{"PlCo.dat": b"A" * 99 + b"X", "New.dat": b"n", "audio/x.hps": b"B" * 71})
        out = os.path.join(self.d, "o")
        t = self.run_diff((self.BASE,), (new,), out)
        self.assertIn("unchanged=2 changed=2 added=1 removed=0", t)
        self.assertIn("VERDICT: LOOSE-OVERRIDE", t)
        self.assertEqual(open(os.path.join(out, "files", "audio", "x.hps"), "rb").read(), b"B" * 71)
        self.assertEqual(open(os.path.join(out, "files", "New.dat"), "rb").read(), b"n")

    def test_mex_and_dol(self):
        t = self.run_diff((self.BASE,), (dict(self.BASE, **{"MxDt.dat": b"m"}),))
        self.assertIn("NEEDS-DISC-BOOT", t)
        t = self.run_diff((self.BASE, b"DOL0"), (self.BASE, b"DOL1"))
        self.assertIn("main.dol differs: True", t)
        self.assertIn("NEEDS-DISC-BOOT", t)
        t = self.run_diff((self.BASE,), (self.BASE,))
        self.assertIn("main.dol differs: False", t)
        self.assertIn("LOOSE-OVERRIDE", t)


if __name__ == "__main__":
    unittest.main(verbosity=1)
