#!/usr/bin/env python3
"""Find m-ex guest calls that pass an argument register nothing set - a "leftover-register" call.

    python tools/mex_port/scan_leftover_args.py --iso C:/iso/Akaneia.iso --iso "C:/iso/SSBM ACE Build v2.0.0.iso"
    python tools/mex_port/scan_leftover_args.py --iso C:/iso/Akaneia.iso --file PlSc.dat --all

The class: m-ex content written against a header that declares a game function with FEWER
arguments than it really takes (ACE's PlSc.dat calls `it_80276174(gobj, pos)` as one-argument).
On hardware the missing argument is whatever the register held - usually the previous call's
leftover - and the game happens to survive it. The port's bridge cannot reproduce a native
callee's leftover volatile registers, so the same call reads something else (for 80276174, NULL).

Method, per relocated blob (every ftFunction, itFunction article and grFunction on the disc):
forward dataflow over the blob's reachable code, tracking which GPRs are DEFINITELY written.
Function entries start with every register defined (they may be genuine parameters). A call
to NATIVE code (`bl` out of the blob, `bctrl`, `blrl`) undefines r0 and r4..r12 and defines r3
(its result); a `bl` to the blob's own code does not, because the interpreter runs it and so
reproduces its leftovers exactly. At each call - or
tail branch - to a game function with a known signature (gw_mex_sigs_gen.inc), every integer
argument register the signature needs but the dataflow says is undefined is reported: on every
path from the last call to here, nothing wrote it.

A report is a lead, not a verdict: the callee may ignore the argument on the path the caller
takes (check the decomp source), and a jump-table target reached only through `bctr` is not
analysed at all. Each confirmed case needs a shim like gw_mex_shim_it_snap_ground.
"""
import argparse
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mex_hsd  # noqa: E402
from dump_ftfunction import FtFunction  # noqa: E402
from dump_itfunction import parse as parse_itfunction  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SIGS = os.path.join(ROOT, "melee", "pc", "platform", "gw_mex_sigs_gen.inc")
BRIDGE = os.path.join(ROOT, "melee", "pc", "platform", "gw_mex_bridge.c")
CODE_BASE = 0x81000000  # above all game code, within bl's +-32 MB reach of it

ALL = 0xFFFFFFFF
CLOBBER = (1 << 0) | sum(1 << r for r in range(4, 13))  # r3 is the result: defined
PROLOGUE = (0x7C0802A6,)  # mflr r0


def load_sigs():
    sigs = {}
    pat = re.compile(r"\{ 0x([0-9A-F]+)u, 0x([0-9A-F]+)u, (\d+), (\d) \}, /\* (\S+)")
    for line in open(SIGS, encoding="utf-8"):
        m = pat.search(line)
        if m:
            fmask = int(m.group(2), 16) & 0x7FFFFFFF
            n = int(m.group(3))
            nint = sum(1 for i in range(n) if not (fmask >> i) & 1)
            sigs[int(m.group(1), 16)] = (nint, m.group(5))
    return sigs


def load_bridged():
    pat = re.compile(r"\{ 0x([0-9A-F]{8})u, 0x[0-9A-F]+u, \d+ \}")
    return {int(m.group(1), 16) for m in pat.finditer(open(BRIDGE, encoding="utf-8").read())}


def sext(v, bits):
    return v - (1 << bits) if v & (1 << (bits - 1)) else v


OP31_RD = {23, 55, 87, 119, 279, 311, 343, 375, 534, 790, 339, 19, 83, 371, 595, 659}
OP31_RD_UPD = {55, 119, 311, 375}  # lwzux lbzux lhzux lhaux: also rA
OP31_RA_UPD = {183, 247, 439, 695, 759, 567, 631}  # st?ux / lf?ux: rA only
OP31_RA = {28, 60, 444, 412, 316, 476, 124, 284, 24, 536, 792, 824, 26, 954, 922}
OP31_ARITH9 = {266, 10, 138, 234, 202, 40, 8, 136, 232, 200, 104, 235, 75, 11, 491, 459}


def decode(w, pc):
    """(defs_mask, kind, target) - kind: seq | call | icall | br | cbr | ret | stop."""
    op = w >> 26
    rd = (w >> 21) & 31
    ra = (w >> 16) & 31
    if op == 18:
        t = sext(w & 0x03FFFFFC, 26)
        t = (t if w & 2 else pc + t) & 0xFFFFFFFF
        return 0, ("call" if w & 1 else "br"), t
    if op == 16:
        t = sext(w & 0xFFFC, 16)
        t = (t if w & 2 else pc + t) & 0xFFFFFFFF
        if w & 1:
            return 0, "seq", None  # bcl 20,31,$+4 - reads the PC, calls nothing
        return 0, ("br" if (rd & 0x14) == 0x14 else "cbr"), t
    if op == 19:
        xo = (w >> 1) & 0x3FF
        if xo in (16, 528):
            if w & 1:
                return 0, "icall", None
            if xo == 16:
                return 0, ("ret" if (rd & 0x14) == 0x14 else "seq"), None
            return 0, "stop", None  # bctr: a jump table or tail call through CTR
        return 0, "seq", None
    if op in (32, 34, 40, 42) or op in (7, 8, 12, 13, 14, 15):
        return 1 << rd, "seq", None
    if op in (33, 35, 41, 43):
        return (1 << rd) | (1 << ra), "seq", None
    if op == 46:
        return sum(1 << r for r in range(rd, 32)), "seq", None
    if op in (37, 39, 45, 53, 55, 49, 51, 57, 61):
        return 1 << ra, "seq", None
    if op in (20, 21, 23, 24, 25, 26, 27, 28, 29):
        return 1 << ra, "seq", None
    if op == 31:
        xo = (w >> 1) & 0x3FF
        if xo in OP31_RD_UPD:
            return (1 << rd) | (1 << ra), "seq", None
        if xo in OP31_RD:
            return 1 << rd, "seq", None
        if xo in OP31_RA_UPD or xo in OP31_RA:
            return 1 << ra, "seq", None
        if (xo & 0x1FF) in OP31_ARITH9:
            return 1 << rd, "seq", None
        return 0, "seq", None  # compares, stores, cache ops, mtspr...
    return 0, "seq", None


def analyse(name, fn, sigs, bridged, findings):
    blob, _ = fn.relocated_code(CODE_BASE)
    n = len(blob) // 4
    words = struct.unpack(">%dI" % n, blob[:n * 4])
    end = CODE_BASE + n * 4

    def inblob(a):
        return CODE_BASE <= a < end and not (a & 3)

    syms = sorted((off, nm or "?") for off, _, nm in fn.debug_symbols())

    def where(pc):
        best = None
        for off, nm in syms:
            if CODE_BASE + off <= pc:
                best = (nm, pc - CODE_BASE - off)
        return "%s+0x%X" % best if best else "0x%X" % (pc - CODE_BASE)

    entries = {CODE_BASE + off for off, _ in syms}
    entries |= {CODE_BASE + off for _, off in fn.func_relocs() if off < n * 4}
    for i, w in enumerate(words):
        d, kind, t = decode(w, CODE_BASE + i * 4)
        if kind == "call" and t is not None and inblob(t):
            entries.add(t)
    for flag, off, target in fn.instr_relocs():
        if flag == 0x01 and not (target & 0xF0000000) == 0x80000000:
            a = CODE_BASE + target
            if inblob(a) and words[(a - CODE_BASE) // 4] in PROLOGUE:
                entries.add(a)

    state = {}
    work = []
    for a in entries:
        if inblob(a):
            state[a] = ALL
            work.append(a)

    def flow(a, s):
        if not inblob(a):
            return
        old = state.get(a)
        new = s if old is None else (old & s)
        if new != old:
            state[a] = new
            work.append(a)

    while work:
        pc = work.pop()
        s = state[pc]
        d, kind, t = decode(words[(pc - CODE_BASE) // 4], pc)
        if kind == "seq":
            flow(pc + 4, s | d)
        elif kind == "call" and inblob(t):
            # interpreted guest code: whatever it leaves in r4..r12 is exactly what hardware
            # leaves, so a caller that reads it afterwards behaves the same on the port
            flow(pc + 4, s | CLOBBER)
        elif kind in ("call", "icall"):
            flow(pc + 4, (s & ~CLOBBER) | (1 << 3))
        elif kind == "br":
            flow(t, s)
        elif kind == "cbr":
            flow(t, s)
            flow(pc + 4, s)

    for pc in sorted(state):
        s = state[pc]
        d, kind, t = decode(words[(pc - CODE_BASE) // 4], pc)
        if kind not in ("call", "br") or t is None or inblob(t) or t not in sigs:
            continue
        nint, tname = sigs[t]
        missing = [r for r in range(3, 3 + min(nint, 8)) if not (s >> r) & 1]
        if missing:
            findings.append((name, where(pc), pc - CODE_BASE, t, tname, nint, missing,
                             t in bridged, kind == "br"))


def recover_size(ar, fn):
    """codeSize 0 (a MexTK older than the field): the code runs up to the next archive structure,
    as gw_ftfunction_code_bound() recovers it at load time."""
    if fn.code_size:
        return
    cands = [fn.base, ar.data_size]
    if fn.instr_reloc_num:
        cands.append(fn.instr_reloc_off)
    if fn.func_reloc_num:
        cands.append(fn.func_reloc_off)
    if fn.debug_num:
        cands.append(fn.debug_off)
    cands += [off for _, off in ar.publics + ar.externs]
    for off in ar.reloc_offsets:
        cands.append(off)
        if off + 4 <= ar.data_size:
            cands.append(ar.u32(off))
    fn.code_size = min(c for c in cands if c > fn.code_off) - fn.code_off


def blobs_in(ar):
    out = []
    for sym, _ in ar.publics:
        try:
            if sym in ("ftFunction", "grFunction"):
                out.append((sym, FtFunction(ar, sym)))
            elif sym == "itFunction":
                for idx, ptr, _, it in parse_itfunction(ar)[2]:
                    if it is not None:
                        out.append(("itFunction[%d]" % idx, it))
        except Exception as exc:  # noqa: BLE001 - a malformed table is reported, not fatal
            print("  %s: cannot parse (%s)" % (sym, exc), file=sys.stderr)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--iso", action="append", required=True)
    ap.add_argument("--file", action="append", help="only these files (basename)")
    ap.add_argument("--all", action="store_true", help="also list calls to non-bridged targets")
    args = ap.parse_args()
    sigs, bridged = load_sigs(), load_bridged()

    for iso in args.iso:
        gcm = mex_hsd.Gcm(iso)
        findings = []
        nblobs = 0
        for path in sorted(gcm.files):
            base = path.rsplit("/", 1)[-1]
            if args.file and base not in args.file:
                continue
            if not base.endswith(".dat"):
                continue
            raw = gcm.read(path)
            if b"Function\0" not in raw:
                continue
            try:
                ar = mex_hsd.Archive(raw).relocate(0)
            except Exception:  # noqa: BLE001
                continue
            for sym, fn in blobs_in(ar):
                recover_size(ar, fn)
                nblobs += 1
                analyse("%s:%s" % (base, sym), fn, sigs, bridged, findings)
        shown = [f for f in findings if f[7] or args.all]
        print("== %s: %d blobs, %d leftover-register calls (%d to bridged natives)"
              % (os.path.basename(iso), nblobs, len(findings), sum(1 for f in findings if f[7])))
        for blob, where, off, t, tname, nint, missing, br, tail in shown:
            print("  %-26s %-40s -> %08X %-28s needs r3..r%d, unset: %s%s%s"
                  % (blob, where, t, tname, 2 + nint, ",".join("r%d" % r for r in missing),
                     "" if br else "  (not bridged)", "  (tail call)" if tail else ""))


if __name__ == "__main__":
    main()
