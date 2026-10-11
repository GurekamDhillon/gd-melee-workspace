#!/usr/bin/env python3
"""Pure-Python RFC 3284 VCDIFF decoder (xdelta3 flavour).

apply(source, patch) -> bytes      source: bytes-like or mmap (never copied)
CLI: python vcdiff.py SRC PATCH OUT  (streams output to OUT)

Supports: default code table, near/same address cache, multiple windows,
VCD_SOURCE / VCD_TARGET, xdelta3 magic + app-header + adler32 (verified).
Secondary compression: id 32 (xdelta3 -S lzma, an .xz stream) is decoded with
the stdlib lzma module; djw / fgk raise VcdiffError naming the algorithm.
Custom code tables (VCD_CODETABLE) are rejected.
"""
import mmap
import struct
import sys
import zlib

SECONDARY = {1: "djw", 16: "fgk", 32: "lzma"}  # ids as assigned by xdelta3


class VcdiffError(Exception):
    pass


def _build_table():
    # entry = (type1, size1, mode1, type2, size2, mode2); types 0 noop 1 add 2 run 3 copy
    t = [(2, 0, 0, 0, 0, 0)]
    for s in range(0, 18):
        t.append((1, s, 0, 0, 0, 0))
    for mode in range(9):
        t.append((3, 0, mode, 0, 0, 0))
        for s in range(4, 19):
            t.append((3, s, mode, 0, 0, 0))
    for mode in range(6):
        for a in range(1, 5):
            for c in range(4, 7):
                t.append((1, a, 0, 3, c, mode))
    for mode in range(6, 9):
        for a in range(1, 5):
            t.append((1, a, 0, 3, 4, mode))
    for mode in range(9):
        t.append((3, 4, mode, 1, 1, 0))
    assert len(t) == 256
    return t


TABLE = _build_table()


class _Reader:
    __slots__ = ("b", "p")

    def __init__(self, b):
        self.b = b
        self.p = 0

    def byte(self):
        v = self.b[self.p]
        self.p += 1
        return v

    def varint(self):
        v = 0
        while True:
            c = self.byte()
            v = (v << 7) | (c & 0x7F)
            if not c & 0x80:
                return v

    def take(self, n):
        if self.p + n > len(self.b):
            raise VcdiffError("truncated patch")
        v = self.b[self.p:self.p + n]
        self.p += n
        return v

    def eof(self):
        return self.p >= len(self.b)


class _MemSink:
    def __init__(self):
        self.buf = bytearray()

    def write(self, b):
        self.buf += b

    def read(self, pos, size):
        return memoryview(self.buf)[pos:pos + size]

    def size(self):
        return len(self.buf)


class _FileSink:
    def __init__(self, f):
        self.f = f
        self.n = 0

    def write(self, b):
        self.f.seek(self.n)
        self.f.write(b)
        self.n += len(b)

    def read(self, pos, size):
        self.f.seek(pos)
        return self.f.read(size)

    def size(self):
        return self.n


def _section(r, n, compressed, algo):
    raw = r.take(n)
    if not compressed:
        return raw
    if algo != "lzma":
        raise VcdiffError("patch uses secondary compression '%s' (xdelta3 -S %s), not supported" % (algo, algo))
    import lzma
    sr = _Reader(raw)
    want = sr.varint()
    try:
        out = lzma.LZMADecompressor(format=lzma.FORMAT_AUTO).decompress(bytes(raw[sr.p:]))
    except lzma.LZMAError as e:
        raise VcdiffError("lzma secondary section failed: %s" % e)
    if len(out) != want:
        raise VcdiffError("lzma section size mismatch")
    return out


def _decode(source, patch, sink):
    src = memoryview(source) if source is not None else memoryview(b"")
    r = _Reader(memoryview(patch))
    if bytes(r.take(3)) != b"\xd6\xc3\xc4":
        raise VcdiffError("not a VCDIFF/xdelta3 patch (bad magic)")
    if r.byte() != 0:
        raise VcdiffError("unsupported VCDIFF version")
    hi = r.byte()
    algo = None
    if hi & 1:
        sid = r.byte()
        algo = SECONDARY.get(sid, "unknown(%d)" % sid)
    if hi & 2:
        raise VcdiffError("custom code table (VCD_CODETABLE) not supported")
    if hi & 4:
        r.take(r.varint())  # app header, ignored
    if hi & ~7:
        raise VcdiffError("unknown header indicator bits 0x%02x" % hi)
    while not r.eof():
        wi = r.byte()
        seg = memoryview(b"")
        if wi & 3 == 3:
            raise VcdiffError("window has both VCD_SOURCE and VCD_TARGET")
        if wi & 3:
            ssize = r.varint()
            spos = r.varint()
            if wi & 1:
                if spos + ssize > len(src):
                    raise VcdiffError("source segment outside source file")
                seg = src[spos:spos + ssize]
            else:
                if spos + ssize > sink.size():
                    raise VcdiffError("target segment outside output")
                seg = memoryview(bytes(sink.read(spos, ssize)))
        r.varint()  # delta encoding length
        tlen = r.varint()
        di = r.byte()
        dlen, ilen, alen = r.varint(), r.varint(), r.varint()
        want_sum = struct.unpack(">I", bytes(r.take(4)))[0] if wi & 4 else None
        data = _Reader(_section(r, dlen, di & 1, algo))
        inst = _Reader(_section(r, ilen, di & 2, algo))
        addr = _Reader(_section(r, alen, di & 4, algo))
        tgt = bytearray()
        slen = len(seg)
        near = [0] * 4
        same = [0] * 768
        nxt = 0
        while len(tgt) < tlen:
            ent = TABLE[inst.byte()]
            for k in (0, 3):
                typ, size, mode = ent[k], ent[k + 1], ent[k + 2]
                if typ == 0:
                    continue
                if size == 0 and typ != 0:
                    size = inst.varint()
                if typ == 1:
                    tgt += data.take(size)
                elif typ == 2:
                    tgt += bytes([data.byte()]) * size
                else:
                    here = slen + len(tgt)
                    if mode == 0:
                        a = addr.varint()
                    elif mode == 1:
                        a = here - addr.varint()
                    elif mode < 6:
                        a = near[mode - 2] + addr.varint()
                    else:
                        a = same[(mode - 6) * 256 + addr.byte()]
                    if not 0 <= a < here or (a >= slen and False):
                        raise VcdiffError("bad copy address")
                    near[nxt] = a
                    nxt = (nxt + 1) & 3
                    same[a % 768] = a
                    if a < slen:
                        n1 = min(size, slen - a)
                        tgt += seg[a:a + n1]
                        a += n1
                        size -= n1
                    if size:
                        off = a - slen
                        while size:  # may overlap own output
                            n1 = min(size, len(tgt) - off)
                            tgt += bytes(tgt[off:off + n1])
                            off += n1
                            size -= n1
        if len(tgt) != tlen:
            raise VcdiffError("window overran its declared length")
        if want_sum is not None and zlib.adler32(tgt) & 0xFFFFFFFF != want_sum:
            raise VcdiffError("adler32 mismatch in window")
        sink.write(tgt)


def apply(source, patch):
    sink = _MemSink()
    _decode(source, patch, sink)
    return bytes(sink.buf)


def apply_files(src_path, patch_path, out_path):
    with open(patch_path, "rb") as pf:
        patch = pf.read()
    with open(src_path, "rb") as sf, open(out_path, "w+b") as of:
        m = mmap.mmap(sf.fileno(), 0, access=mmap.ACCESS_READ)  # freed by GC
        _decode(m, patch, _FileSink(of))


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit("usage: vcdiff.py SRC PATCH OUT")
    try:
        apply_files(*sys.argv[1:])
    except VcdiffError as e:
        sys.exit("vcdiff: %s" % e)
