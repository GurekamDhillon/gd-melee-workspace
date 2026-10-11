#!/usr/bin/env python3
"""Classify a codes.gct by Gecko type and by the section its target address falls in (read-only).

  python tools/research/gecko_classify.py --iso "$GW_ISO_ACE" --splits melee/config/GALE01/splits.txt \
      --symbols melee/config/GALE01/symbols.txt [--list-data]

Sections come from the decomp's splits.txt (min start / max end per section over all TUs); a data write is
then checked against the symbol table (does it land inside a sized object? which?). Prints counts only plus,
with --list-data, one line per data write (address, symbol+off, size). No disc bytes are printed.
"""
import argparse, bisect, collections, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "mex_port"))
from mex_hsd import Gcm
from dump_gct import parse

def parse_any(gct):
    """Walk every Gecko line group (all type bytes, not just the five dump_gct knows). Returns (type, addr, off, payload)."""
    import struct
    off, out = 8, []
    while off + 8 <= len(gct):
        w0, w1 = struct.unpack_from(">II", gct, off)
        if w0 == 0xF0000000: break
        t = (w0 >> 24) & 0xFE
        addr = 0x80000000 | (w0 & 0x01FFFFFF)
        if t in (0xC0, 0xC2, 0xC4, 0xF2, 0xF4): n = w1 * 8
        elif t == 0x06: n = (w1 + 7) & ~7
        elif t == 0x08: n = 8
        else: n = 0
        out.append(("%02X" % t, addr, off, gct[off + 8: off + 8 + n]))
        off += 8 + n
    return out

def sections(path):
    rng = collections.defaultdict(lambda: [1 << 40, 0])
    for l in open(path, encoding="utf8", errors="replace"):
        m = re.match(r"\s+(\S+)\s+start:0x([0-9A-Fa-f]+) end:0x([0-9A-Fa-f]+)", l)
        if m:
            r = rng[m.group(1)]; r[0] = min(r[0], int(m.group(2), 16)); r[1] = max(r[1], int(m.group(3), 16))
    return sorted((v[0], v[1], k) for k, v in rng.items())

def objsyms(path):
    out = []
    for l in open(path, encoding="utf8", errors="replace"):
        m = re.match(r"(\S+) = \.(\w+):0x([0-9A-Fa-f]+); // type:(\w+) size:0x([0-9A-Fa-f]+)", l)
        if m: out.append((int(m.group(3), 16), int(m.group(5), 16), m.group(1), m.group(4)))
    out.sort(); return out


def hook_sites(codes, funcs, fstarts, sec):
    c = collections.Counter(); ex = collections.defaultdict(list)
    for typ, addr, off, payload in codes:
        if sec(addr) not in (".text", ".init"): continue
        i = bisect.bisect_right(fstarts, addr) - 1
        if i < 0 or addr >= funcs[i][0] + funcs[i][1]: k = "no-function"
        else:
            d = addr - funcs[i][0]; sz = funcs[i][1]
            k = "entry(+0)" if d == 0 else "last-insn(exit)" if d == sz - 4 else "mid-function"
        c[(typ, k)] += 1
        if len(ex[(typ, k)]) < 3: ex[(typ, k)].append(f"0x{addr:08X}")
    return c, ex

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iso"); ap.add_argument("--gct"); ap.add_argument("--ini", help="Dolphin GALE01.ini: its [Gecko] and [Gecko_Enabled-less] hex lines")
    ap.add_argument("--splits", required=True); ap.add_argument("--symbols", required=True)
    ap.add_argument("--list-data", action="store_true")
    a = ap.parse_args()
    if a.ini:
        # Per-code blocks ("$Name" then hex lines): classify each block by its FIRST line group, so a mis-sized
        # body can never desynchronise the next code. Bodies of C0/C2/F2... are skipped by their declared length.
        import re as _re, struct as _st
        blocks, cur, sec_name = [], None, None
        for l in open(a.ini, encoding="utf8", errors="replace"):
            l = l.strip()
            if l.startswith("["): sec_name = l; cur = None; continue
            if sec_name != "[Gecko]": continue
            if l.startswith("$"): cur = []; blocks.append((l, cur)); continue
            if cur is not None and _re.match(r"^[0-9A-Fa-f]{8} [0-9A-Fa-f]{8}\s*(#.*)?$", l):
                cur += [int(x, 16) for x in l.split()[:2]]
        codes = []
        for name, words in blocks:
            if not words: continue
            gct = bytes.fromhex("00D0C0DE00D0C0DE") + b"".join(_st.pack(">I", w) for w in words) + bytes.fromhex("F000000000000000")
            codes += parse_any(gct)
        gct = None
    else:
        gct = Gcm(a.iso).read("codes.gct") if a.iso else open(a.gct, "rb").read()
    if gct is not None: codes = parse_any(gct)
    secs = sections(a.splits); syms = objsyms(a.symbols); starts = [s[0] for s in syms]
    def sec(addr):
        for lo, hi, k in secs:
            if lo <= addr < hi: return k
        return "outside-dol" if addr >= 0x80000000 and addr < 0x81800000 else "other"
    cnt = collections.Counter(); bytes_c = collections.Counter(); lands = collections.Counter()
    for typ, addr, off, payload in codes:
        s = sec(addr)
        cnt[(typ, s)] += 1
        bytes_c[typ] += len(payload)
        if typ != "C2" and s not in (".text", ".init"):
            i = bisect.bisect_right(starts, addr) - 1
            hit = i >= 0 and addr < syms[i][0] + syms[i][1]
            lands[(s, "in-sized-object" if hit else "no-object")] += 1
            if a.list_data:
                print(f"{typ} 0x{addr:08X} {s} " + (f"{syms[i][2]}+0x{addr-syms[i][0]:X} (size 0x{syms[i][1]:X})" if hit else "-"))
    print(f"total codes {len(codes)}")
    t = collections.Counter(c[0] for c in codes); print("by type", dict(t))
    print("by (type, section):")
    for k, v in sorted(cnt.items()): print("  ", k, v)
    print("data writes vs symbol table:", dict(lands))
    print("payload bytes by type", dict(bytes_c))
    funcs = [x for x in syms if x[3] == "function"]; fst = [x[0] for x in funcs]
    hs, ex = hook_sites(codes, funcs, fst, sec)
    print("text-hook placement (function entry / last insn / mid):")
    for k, v in sorted(hs.items()): print("  ", k, v, ex[k])
    print("DOL sections:", [(k, hex(lo), hex(hi)) for lo, hi, k in secs])
main()
