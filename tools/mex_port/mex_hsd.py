#!/usr/bin/env python3
"""Shared readers for m-ex offline analysis: GCM discs and HSD archives.

Used by `dump_ftfunction.py` and `dump_mxdt.py`. Everything here is strictly read-only;
no function in this module ever opens a file for writing.

HSD archive layout (big-endian), as implemented by the port in
`melee/pc/platform/gw_mex_ftfunction.c`:

    0x00 u32 file_size
    0x04 u32 data_size
    0x08 u32 nb_reloc
    0x0C u32 nb_public
    0x10 u32 nb_extern
    0x14..0x1F pad
    0x20                        data section (data_size bytes)
    0x20 + data_size            reloc table: nb_reloc * u32 data offsets
    ... + nb_reloc*4            public table: nb_public * { u32 data_off, u32 sym_off }
    ... + nb_public*8           extern table: nb_extern * { u32 data_off, u32 sym_off }
    ... + nb_extern*8           symbol string blob (sym_off is relative to here)

The reloc table is a list of *data offsets*; the word stored at each of those offsets is
itself a data offset, and relocation means adding the data base to it. Offline we keep the
data base at 0 (so relocated pointers stay file-relative data offsets) unless a caller asks
for a non-zero base.
"""

import struct

HSD_HEADER_SIZE = 0x20


def u32(buf, off):
    return struct.unpack_from(">I", buf, off)[0]


def u16(buf, off):
    return struct.unpack_from(">H", buf, off)[0]


def s32(buf, off):
    return struct.unpack_from(">i", buf, off)[0]


def u8(buf, off):
    return buf[off]


# --------------------------------------------------------------------------- GCM disc


class Gcm:
    """Read-only GCM/ISO image with an FST index keyed by full path."""

    def __init__(self, path):
        self.path = path
        with open(path, "rb") as fp:
            self.fp = None
            fp.seek(0x420)
            self.dol_offset = struct.unpack(">I", fp.read(4))[0]
            self.fst_offset, self.fst_size = struct.unpack(">II", fp.read(8))
            fp.seek(self.fst_offset)
            fst = fp.read(self.fst_size)
        self.files = {}
        self._parse_fst(fst)

    def _parse_fst(self, fst):
        n_entries = u32(fst, 0x08)
        strings = n_entries * 12
        stack = [(n_entries, "")]  # (end index, prefix)

        def name_at(off):
            end = fst.index(b"\0", strings + off)
            return fst[strings + off:end].decode("shift_jis", "replace")

        i = 1
        while i < n_entries:
            e = i * 12
            w0 = u32(fst, e)
            is_dir = (w0 >> 24) & 1
            name = name_at(w0 & 0x00FFFFFF)
            arg1, arg2 = u32(fst, e + 4), u32(fst, e + 8)
            while len(stack) > 1 and i >= stack[-1][0]:
                stack.pop()
            prefix = stack[-1][1]
            if is_dir:
                stack.append((arg2, prefix + name + "/"))
            else:
                self.files[prefix + name] = (arg1, arg2)
            i += 1

    def read(self, path):
        """Return the bytes of `path` (e.g. "PlSn.dat"). Matches on basename too."""
        ent = self.files.get(path)
        if ent is None:
            base = path.rsplit("/", 1)[-1]
            hits = [k for k in self.files if k.rsplit("/", 1)[-1] == base]
            if len(hits) != 1:
                raise KeyError(f"{path!r} not found on {self.path} ({len(hits)} basename matches)")
            ent = self.files[hits[0]]
        off, size = ent
        with open(self.path, "rb") as fp:
            fp.seek(off)
            return fp.read(size)


def load_dat(arg, iso=None):
    """Resolve a tool argument to bytes: a loose file path, or a name inside `iso`."""
    if iso:
        return Gcm(iso).read(arg)
    with open(arg, "rb") as fp:
        return fp.read()


# ----------------------------------------------------------------------- HSD archive


class Archive:
    """A parsed HSD archive. `data` is a mutable copy of the data section."""

    def __init__(self, raw):
        if len(raw) < HSD_HEADER_SIZE:
            raise ValueError("file is shorter than an HSD header")
        self.raw = raw
        self.file_size = u32(raw, 0x00)
        self.data_size = u32(raw, 0x04)
        self.nb_reloc = u32(raw, 0x08)
        self.nb_public = u32(raw, 0x0C)
        self.nb_extern = u32(raw, 0x10)

        self.o_data = HSD_HEADER_SIZE
        self.o_reloc = self.o_data + self.data_size
        self.o_public = self.o_reloc + self.nb_reloc * 4
        self.o_extern = self.o_public + self.nb_public * 8
        self.o_symbols = self.o_extern + self.nb_extern * 8
        if self.o_symbols > len(raw):
            raise ValueError(
                f"archive tables run past EOF (need 0x{self.o_symbols:X}, have 0x{len(raw):X})")

        self.data = bytearray(raw[self.o_data:self.o_data + self.data_size])
        self.reloc_offsets = [u32(raw, self.o_reloc + i * 4) for i in range(self.nb_reloc)]
        self.reloc_set = set(self.reloc_offsets)
        self.publics = [self._sym(self.o_public + i * 8) for i in range(self.nb_public)]
        self.externs = [self._sym(self.o_extern + i * 8) for i in range(self.nb_extern)]

    def _sym(self, off):
        data_off = u32(self.raw, off)
        sym_off = u32(self.raw, off + 4)
        p = self.o_symbols + sym_off
        end = self.raw.index(b"\0", p)
        return (self.raw[p:end].decode("ascii", "replace"), data_off)

    def public(self, name):
        for sym, off in self.publics:
            if sym == name:
                return off
        raise KeyError(f"no public symbol {name!r} (have: "
                       f"{', '.join(s for s, _ in self.publics)})")

    def relocate(self, base=0):
        """Apply the archive's own relocation table in place, adding `base` to each word."""
        for off in self.reloc_offsets:
            if off + 4 > len(self.data):
                continue
            struct.pack_into(">I", self.data, off, (u32(self.data, off) + base) & 0xFFFFFFFF)
        return self

    # data-section accessors ------------------------------------------------
    def u32(self, off):
        return u32(self.data, off)

    def s32(self, off):
        return s32(self.data, off)

    def u16(self, off):
        return u16(self.data, off)

    def u8(self, off):
        return self.data[off]

    def cstr(self, off):
        if off <= 0 or off >= len(self.data):
            return None
        end = self.data.find(b"\0", off)
        if end < 0:
            return None
        return self.data[off:end].decode("ascii", "replace")

    def in_data(self, off):
        return 0 < off < self.data_size
