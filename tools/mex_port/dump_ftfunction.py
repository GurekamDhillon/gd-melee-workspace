#!/usr/bin/env python3
"""Dump an m-ex `ftFunction` blob out of a fighter .dat.

An m-ex fighter archive (e.g. Akaneia's `PlSn.dat`) carries its moveset as relocatable
PowerPC under the public symbol `ftFunction`. The port loads that blob in
`melee/pc/platform/gw_mex_ftfunction.c`; this is an independent Python implementation of
the same parse, for cross-checking and for turning interpreter crash addresses into names.

`MEXFunction` header, data-relative (mirrors gw_mex_ftfunction.c and m-ex's mxdt.h):

    +0x00 code                      -> data offset of the flat PPC blob
    +0x04 instruction_reloc_table   -> data offset, stride 8
    +0x08 instruction_reloc_table_num
    +0x0C func_table                -> data offset, stride 8 (the override table)
    +0x10 func_table_num
    +0x14 code_size
    +0x18 debug_symbol_num
    +0x1C debug_symbol              -> data offset, stride 12

`MEXDebugSymbol` is { u32 code_offset; u32 code_end; char *symbol; }. m-ex's header names
the second word `code_length`, but in the shipped blob it is an **end offset**, not a
length: see --check-symbols, which proves it.

Examples:

    python dump_ftfunction.py --iso C:/iso/Akaneia.iso PlSn.dat --header --overrides
    python dump_ftfunction.py --iso C:/iso/Akaneia.iso PlSn.dat --symbols
    python dump_ftfunction.py --iso C:/iso/Akaneia.iso PlSn.dat --check-symbols
    python dump_ftfunction.py --iso C:/iso/Akaneia.iso PlSn.dat --resolve 0x800033E0
    python dump_ftfunction.py --iso C:/iso/Akaneia.iso PlSn.dat --emit-blob sn.bin
    python dump_ftfunction.py PlSn.dat --relocs --limit 20
"""

import argparse
import struct
import sys

import mex_hsd

FTFUNC_OFF_CODE = 0x00
FTFUNC_OFF_INSTR_RELOC = 0x04
FTFUNC_OFF_INSTR_RELOC_NUM = 0x08
FTFUNC_OFF_FUNC_RELOC = 0x0C
FTFUNC_OFF_FUNC_RELOC_NUM = 0x10
FTFUNC_OFF_CODE_SIZE = 0x14
FTFUNC_OFF_DEBUG_NUM = 0x18
FTFUNC_OFF_DEBUG = 0x1C

DEBUG_SYMBOL_STRIDE = 12

# Arch_FighterFunc slot names as the port currently spells them
# (gw_mex_ftfunction.c, gw_ftfunction_slot_names). Kept here so a disagreement between the
# port's guessed names and the blob's own debug symbols is visible in one place.
PORT_SLOT_NAMES = [
    "onLoad", "onDeath", "onDestroy", "MoveLogic",
    "SpecialN", "SpecialNAir", "SpecialS", "SpecialSAir",
    "SpecialHi", "SpecialHiAir", "SpecialLw", "SpecialLwAir",
    "onAbsorb", "OnItemPickup", "onMakeItemInvisible", "onMakeItemVisible",
    "OnItemRelease", "OnItemPickup2", "onUnknownItemRelated", "onApplyHeadItem",
    "onRemoveHeadItem", "onKnockbackEnter", "onKnockbackExit", "onFrame",
    "onActionStateChange", "onReapplyAttr", "onModelRender", "onShadowRender",
    "onUnknownMultijump", "onActionStateChangeWhileEyeTextureIsChanged", "onTwoEntryTable",
    "onFloat", "onDoubleJump", "onZair", "onLanding", "onFSmash",
    "onUSmash", "onDSmash", "onGetExtResultAnim", "onIndexExtResultAnim",
    "MoveLogicDemo", "onIntroL", "onIntroR", "onTaunt",
    "onCatch", "GetTrailData",
]

RELOC_FLAGS = {
    0x01: "abs32",
    0x04: "lo16",
    0x06: "hi16",
    0x0A: "branch",
    0x1A: "rel32",
}


class FtFunction:
    def __init__(self, archive, symbol="ftFunction"):
        self.ar = archive
        self.symbol = symbol
        self.base = archive.public(symbol)
        r = archive.u32
        b = self.base
        self.code_off = r(b + FTFUNC_OFF_CODE)
        self.instr_reloc_off = r(b + FTFUNC_OFF_INSTR_RELOC)
        self.instr_reloc_num = r(b + FTFUNC_OFF_INSTR_RELOC_NUM)
        self.func_reloc_off = r(b + FTFUNC_OFF_FUNC_RELOC)
        self.func_reloc_num = r(b + FTFUNC_OFF_FUNC_RELOC_NUM)
        self.code_size = r(b + FTFUNC_OFF_CODE_SIZE)
        self.debug_num = r(b + FTFUNC_OFF_DEBUG_NUM)
        self.debug_off = r(b + FTFUNC_OFF_DEBUG)
        self.warnings = self._sanity(archive.data_size)

    def _sanity(self, data_size):
        """Does this actually look like a MEXFunction? `itFunction` does not - see the doc."""
        w = []
        if not (0 < self.code_off < data_size) or self.code_off + self.code_size > data_size:
            w.append(f"code 0x{self.code_off:X}+0x{self.code_size:X} does not fit in the "
                     f"0x{data_size:X}-byte data section")
        if self.instr_reloc_off + self.instr_reloc_num * 8 > data_size:
            w.append("instructionRelocTable runs past the data section")
        if self.debug_off + self.debug_num * DEBUG_SYMBOL_STRIDE > data_size:
            w.append("debugSymbol table runs past the data section")
        if self.func_reloc_num and self.func_reloc_off == 0:
            w.append("functionRelocTable pointer is 0 with a non-zero count")
        return w

    # ------------------------------------------------------------------ tables
    def instr_relocs(self):
        out = []
        for i in range(self.instr_reloc_num):
            e = self.instr_reloc_off + i * 8
            w0 = self.ar.u32(e)
            w1 = self.ar.u32(e + 4)
            out.append((w0 >> 24, w0 & 0x00FFFFFF, w1))
        return out

    def func_relocs(self):
        out = []
        for i in range(self.func_reloc_num):
            e = self.func_reloc_off + i * 8
            out.append((self.ar.u32(e), self.ar.u32(e + 4)))
        return out

    def debug_symbols(self):
        """[(code_offset, second_word, name)] in file order."""
        out = []
        for i in range(self.debug_num):
            e = self.debug_off + i * DEBUG_SYMBOL_STRIDE
            out.append((self.ar.u32(e), self.ar.u32(e + 4), self.ar.cstr(self.ar.u32(e + 8))))
        return out

    # ------------------------------------------------------------------ code
    def relocated_code(self, code_base):
        """The flat blob with the instruction reloc table applied - what the interpreter runs."""
        blob = bytearray(self.ar.data[self.code_off:self.code_off + self.code_size])
        applied = {}
        for flag, code_off, target in self.instr_relocs():
            applied[flag] = applied.get(flag, 0) + 1
            if code_off + 4 > len(blob):
                continue
            ptr = code_base + code_off
            fn = target if (target & 0xF0000000) == 0x80000000 else code_base + target
            if flag == 0x01:
                struct.pack_into(">I", blob, code_off, fn & 0xFFFFFFFF)
            elif flag in (0x04, 0x06):
                v = fn & 0xFFFFFFFF
                if v & 0x8000:
                    high = (v >> 16) + 1
                    v = ((high << 16) | ((v - (high << 16)) & 0xFFFF)) & 0xFFFFFFFF
                half = (v & 0xFFFF) if flag == 0x04 else ((v >> 16) & 0xFFFF)
                struct.pack_into(">H", blob, code_off, half)
            elif flag == 0x0A:
                old = struct.unpack_from(">I", blob, code_off)[0]
                struct.pack_into(">I", blob, code_off,
                                 (old | ((fn - ptr) & 0x03FFFFFC)) & 0xFFFFFFFF)
            elif flag == 0x1A:
                struct.pack_into(">I", blob, code_off, (fn - ptr) & 0xFFFFFFFF)
        return bytes(blob), applied


# ------------------------------------------------------------------ symbol resolution

def build_index(syms, code_size, as_length=False):
    """Sorted [(start, end, name)] from the debug symbol table.

    `as_length` interprets the second word as a length (m-ex's header name) instead of as
    an end offset (what the shipped data actually is).
    """
    out = []
    for start, second, name in syms:
        end = (start + second) if as_length else second
        out.append((start, end, name))
    out.sort()
    return out


def resolve(index, off):
    for start, end, name in index:
        if start <= off < end:
            return start, end, name
    # fall back to the nearest preceding symbol
    prev = None
    for start, end, name in index:
        if start <= off:
            prev = (start, end, name)
    return prev if prev else None


def check_symbols(syms, code_size):
    """Decide end-offset vs length empirically. Returns (verdict, notes[])."""
    notes = []
    end_idx = build_index(syms, code_size, as_length=False)
    len_idx = build_index(syms, code_size, as_length=True)

    def score(idx, label):
        bad_order = sum(1 for s, e, _ in idx if e <= s)
        past_end = sum(1 for s, e, _ in idx if e > code_size)
        # exact chaining: does entry i's end equal entry i+1's start?
        chain = sum(1 for i in range(len(idx) - 1) if idx[i][1] == idx[i + 1][0])
        overlap = sum(1 for i in range(len(idx) - 1) if idx[i][1] > idx[i + 1][0])
        notes.append(f"  as {label:<10} end<=start:{bad_order}  end>codeSize:{past_end}  "
                     f"end==next.start:{chain}/{len(idx) - 1}  overlaps:{overlap}")
        return (bad_order == 0 and past_end == 0, chain)

    end_ok, end_chain = score(end_idx, "END OFFSET")
    len_ok, len_chain = score(len_idx, "LENGTH")
    if end_chain > len_chain:
        return "END OFFSET", notes
    if len_chain > end_chain:
        return "LENGTH", notes
    return ("END OFFSET" if end_ok and not len_ok else "AMBIGUOUS"), notes


# ------------------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser(
        description="Parse an m-ex ftFunction blob out of a fighter .dat.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split("Examples:", 1)[1] if "Examples:" in __doc__ else None)
    ap.add_argument("dat", help="fighter .dat: a loose file, or a name inside --iso")
    ap.add_argument("--iso", help="read `dat` out of this GCM image instead (read-only)")
    ap.add_argument("--symbol", default="ftFunction", help="public symbol (default ftFunction)")
    ap.add_argument("--code-base", default="0x80000000",
                    help="guest VA the code blob is relocated to (default 0x80000000, which is "
                         "what the port's existing log lines imply)")
    ap.add_argument("--internal-id", type=int, default=31,
                    help="internal fighter kind, for labelling only (default 31 = Sonic)")

    ap.add_argument("--header", action="store_true", help="dump the archive + MEXFunction header")
    ap.add_argument("--overrides", action="store_true",
                    help="dump the functionRelocTable (override slots) with slot + symbol names")
    ap.add_argument("--relocs", action="store_true", help="dump the instructionRelocTable")
    ap.add_argument("--symbols", action="store_true", help="dump the MEXDebugSymbol table")
    ap.add_argument("--check-symbols", action="store_true",
                    help="prove whether the second debug-symbol word is an end offset or a length")
    ap.add_argument("--resolve", action="append", default=[], metavar="ADDR",
                    help="resolve a guest address (or bare code offset) to its function; repeatable")
    ap.add_argument("--second-word-is-length", action="store_true",
                    help="interpret MEXDebugSymbol[1] as a length (m-ex's header name). Wrong for "
                         "the shipped blob; kept so the failure mode can be demonstrated.")
    ap.add_argument("--emit-blob", metavar="PATH",
                    help="write the relocated flat code blob (what the interpreter executes)")
    ap.add_argument("--limit", type=int, default=0, help="cap rows printed by table dumps")
    ap.add_argument("--all", action="store_true", help="shorthand for --header --overrides --symbols")
    args = ap.parse_args()

    if args.all:
        args.header = args.overrides = args.symbols = True
    if not any([args.header, args.overrides, args.relocs, args.symbols, args.check_symbols,
                args.resolve, args.emit_blob]):
        args.header = args.overrides = True

    code_base = int(args.code_base, 0)
    try:
        raw = mex_hsd.load_dat(args.dat, args.iso)
        ar = mex_hsd.Archive(raw).relocate(0)
        ft = FtFunction(ar, args.symbol)
    except (KeyError, ValueError, OSError) as exc:
        print(f"dump_ftfunction: {exc}", file=sys.stderr)
        return 1
    for w in ft.warnings:
        print(f"WARNING: {args.symbol} does not look like a MEXFunction: {w}", file=sys.stderr)
    if ft.warnings:
        print(f"WARNING: only `ftFunction` is known to use the MEXFunction header; "
              f"`itFunction` has a different (undecoded) shape.", file=sys.stderr)
        return 1

    syms = ft.debug_symbols()
    index = build_index(syms, ft.code_size, as_length=args.second_word_is_length)

    def cap(rows):
        return rows[:args.limit] if args.limit else rows

    if args.header:
        print(f"== {args.dat}  ({len(raw)} bytes)")
        print(f"archive: fileSize 0x{ar.file_size:X}  dataSize 0x{ar.data_size:X}  "
              f"relocs {ar.nb_reloc}  publics {ar.nb_public}  externs {ar.nb_extern}")
        for sym, off in ar.publics:
            print(f"  public  {sym:<16} data+0x{off:X}")
        print(f"== {args.symbol} header @ data+0x{ft.base:X}")
        print(f"  +0x00 code                    data+0x{ft.code_off:X}")
        print(f"  +0x04 instructionRelocTable   data+0x{ft.instr_reloc_off:X}")
        print(f"  +0x08 instructionRelocTableNum {ft.instr_reloc_num}")
        print(f"  +0x0C functionRelocTable      data+0x{ft.func_reloc_off:X}")
        print(f"  +0x10 functionRelocTableNum   {ft.func_reloc_num}")
        print(f"  +0x14 codeSize                0x{ft.code_size:X}")
        print(f"  +0x18 debugSymbolNum          {ft.debug_num}")
        print(f"  +0x1C debugSymbol             data+0x{ft.debug_off:X}  "
              f"(stride {DEBUG_SYMBOL_STRIDE}, spans "
              f"0x{ft.debug_off:X}..0x{ft.debug_off + ft.debug_num * DEBUG_SYMBOL_STRIDE:X})")
        print(f"  code blob spans data+0x{ft.code_off:X}..0x{ft.code_off + ft.code_size:X}; "
              f"relocated to 0x{code_base:08X}..0x{code_base + ft.code_size:08X}")

    if args.overrides:
        print(f"== override slot table ({ft.func_reloc_num} entries, internal kind "
              f"{args.internal_id})")
        print(f"{'idx':>3}  {'slot':>10}  {'target':>10}  {'blob symbol':<32} port name")
        for i, (replace_this, replace_with) in enumerate(cap(ft.func_relocs())):
            hit = resolve(index, replace_with)
            name = hit[2] if hit and hit[0] == replace_with else (
                f"({hit[2]}+0x{replace_with - hit[0]:X})" if hit else "?")
            if replace_this & 0x80000000:
                slot = f"@{replace_this:08X}"
                port = "(absolute guest address patch)"
            else:
                slot = str(replace_this)
                port = (PORT_SLOT_NAMES[replace_this]
                        if replace_this < len(PORT_SLOT_NAMES) else "?")
            print(f"{i:>3}  {slot:>10}  0x{code_base + replace_with:08X}  {str(name):<32} {port}")

    if args.relocs:
        rows = ft.instr_relocs()
        print(f"== instructionRelocTable ({len(rows)} entries)")
        counts = {}
        for flag, off, target in rows:
            counts[flag] = counts.get(flag, 0) + 1
        for flag in sorted(counts):
            print(f"  flag 0x{flag:02X} {RELOC_FLAGS.get(flag, 'UNKNOWN (m-ex skips it)'):<10} "
                  f"{counts[flag]}")
        for flag, off, target in cap(rows):
            kind = "abs" if (target & 0xF0000000) == 0x80000000 else "code-rel"
            print(f"  0x{off:06X}  flag 0x{flag:02X} {RELOC_FLAGS.get(flag, '?'):<8} "
                  f"target 0x{target:08X} ({kind})")

    if args.symbols:
        print(f"== MEXDebugSymbol table ({ft.debug_num} entries @ data+0x{ft.debug_off:X}, "
              f"stride {DEBUG_SYMBOL_STRIDE})")
        for i, (start, second, name) in enumerate(cap(syms)):
            end = (start + second) if args.second_word_is_length else second
            print(f"{i:>4}  0x{code_base + start:08X}..0x{code_base + end:08X}  "
                  f"(+0x{start:05X} size 0x{max(end - start, 0):X})  {name}")

    if args.check_symbols:
        verdict, notes = check_symbols(syms, ft.code_size)
        print(f"== MEXDebugSymbol second-word test ({len(syms)} entries, "
              f"codeSize 0x{ft.code_size:X})")
        for n in notes:
            print(n)
        print(f"  VERDICT: the second word is an {verdict}.")
        first = syms[0]
        nxt = syms[1] if len(syms) > 1 else None
        print(f"  entry 0: start 0x{first[0]:X} second 0x{first[1]:X} {first[2]}")
        if nxt:
            print(f"  entry 1: start 0x{nxt[0]:X} second 0x{nxt[1]:X} {nxt[2]}"
                  f"   <- entry 0's second word {'==' if first[1] == nxt[0] else '!='} "
                  f"entry 1's start")
        tail = max(s + sec for s, sec, _ in syms)
        print(f"  max(start+second) = 0x{tail:X} vs codeSize 0x{ft.code_size:X} "
              f"({'past the end of the code' if tail > ft.code_size else 'in range'})")

    for spec in args.resolve:
        v = int(spec, 0)
        off = v - code_base if v >= code_base else v
        hit = resolve(index, off)
        if not hit:
            print(f"{spec}: no symbol (code offset 0x{off:X})")
            continue
        start, end, name = hit
        inside = start <= off < end
        print(f"{spec} -> code+0x{off:X} -> {name}+0x{off - start:X} "
              f"[0x{code_base + start:08X}..0x{code_base + end:08X}]"
              f"{'' if inside else '  (PAST this symbol - address is in a gap)'}")

    if args.emit_blob:
        blob, applied = ft.relocated_code(code_base)
        with open(args.emit_blob, "wb") as fp:
            fp.write(blob)
        print(f"wrote {len(blob)} bytes to {args.emit_blob} (base 0x{code_base:08X}); "
              f"relocs applied by flag: "
              f"{', '.join(f'0x{f:02X}={c}' for f, c in sorted(applied.items()))}")
        print(f"  disassemble with: python ppc_disasm.py --raw {args.emit_blob} "
              f"--base 0x{code_base:08X} --start 0x{code_base:08X} --count 16")
    return 0


if __name__ == "__main__":
    sys.exit(main())
