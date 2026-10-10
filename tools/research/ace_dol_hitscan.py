#!/usr/bin/env python3
"""Scan the main.dol of a disc for code that addresses the Fighter hit-capsule arrays (read-only).

  python tools/research/ace_dol_hitscan.py --iso "$GW_ISO_ACE" --symbols melee/config/GALE01/symbols.txt
Fighter layout (melee/src/melee/ft/types.h): x914[4] @0x914, xDF4[2] @0xDF4, x1064_thrownHitbox @0x1064, element stride 0x138.
Reports, per decomp symbol, instructions that: take the address of an array base (addi rD,rA,0x914/0xDF4/0x1064),
use the stride (mulli rD,rA,312 / addi rD,rA,312), or access fields by a displacement in [0x914,0x119C).
Only instruction counts and symbol names are printed; no disc bytes.
"""
import argparse, bisect, os, re, struct, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mex_port"))
from mex_hsd import Gcm

def load_dol(iso):
    g = Gcm(iso)
    with open(iso, "rb") as f:
        f.seek(g.dol_offset); hdr = f.read(0x100)
        offs = struct.unpack(">18I", hdr[0:0x48]); addrs = struct.unpack(">18I", hdr[0x48:0x90]); sizes = struct.unpack(">18I", hdr[0x90:0xD8])
        secs = []
        for o, a, s in zip(offs, addrs, sizes):
            if s:
                f.seek(g.dol_offset + o); secs.append((a, f.read(s)))
    return secs

def load_syms(path):
    syms = []
    for l in open(path, encoding="utf8", errors="replace"):
        m = re.match(r"(\S+) = \.\w+:0x([0-9A-Fa-f]+); // type:function size:0x([0-9A-Fa-f]+)", l)
        if m: syms.append((int(m.group(2), 16), int(m.group(3), 16), m.group(1)))
    syms.sort(); return syms

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--iso", required=True); ap.add_argument("--symbols", required=True)
    a = ap.parse_args()
    syms = load_syms(a.symbols); starts = [s[0] for s in syms]
    res = {}
    for base, data in load_dol(a.iso):
        if base < 0x80003100 or base > 0x80400000: continue
        for i in range(0, len(data) - 3, 4):
            w = struct.unpack_from(">I", data, i)[0]; op = w >> 26; va = base + i
            imm = w & 0xFFFF; simm = imm - 0x10000 if imm & 0x8000 else imm
            kind = None
            if op == 14 and simm in (0x914, 0xDF4, 0x1064): kind = f"addi_base_{simm:X}"
            elif op == 14 and simm == 0x138: kind = "addi_stride"
            elif op == 7 and simm == 0x138: kind = "mulli_stride"
            elif (op in (32,33,34,35,36,37,38,39,40,41,42,43,44,45,48,49,50,51,52,53,54,55)) and 0x914 <= simm < 0x119C: kind = "disp"
            if not kind: continue
            j = bisect.bisect_right(starts, va) - 1
            name = syms[j][2] if j >= 0 and va < syms[j][0] + syms[j][1] else "?"
            res.setdefault(name, {}).setdefault(kind, []).append(va)
    for name, d in sorted(res.items()):
        if not any(k != "disp" for k in d): continue
        print(name, {k: len(v) for k, v in d.items()}, " ".join(f"{k}@{v[0]:08X}" for k, v in d.items() if k != "disp"))
main()
