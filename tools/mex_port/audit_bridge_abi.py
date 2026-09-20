#!/usr/bin/env python3
"""Audit the guest->native bridge for calling-convention mismatches.

gw_ppc_bridge_call invokes EVERY target through `gw_ppc_native_fn`, which is cdecl: arguments on
the stack. That is correct for the gwtool-retargeted game functions, which are external and get
the platform C ABI. It is NOT correct for a function that was `static` in its TU: the backend is
free to give an internal function a private convention, and on i686 LLVM passes the first
arguments in ECX/EDX. The callee then reads registers the bridge never set.

This prints, for every bridge function entry, whether its map symbol is `_gw_`-prefixed (external,
cdecl) or bare (internal), and for the bare ones whether the prologue actually reads ECX.
"""
import re
import struct
import sys

import argparse
import os

# Default off this script's own location (tools/mex_port -> the repo root) rather than a fixed
# path, so a fresh clone works anywhere; GW_BUILD_ROOT / GW_MELEE still win. See SETUP.md.
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEF_BUILD = os.environ.get("GW_BUILD_ROOT", os.path.join(_ROOT, "_build"))
DEF_MELEE = os.environ.get("GW_MELEE", os.path.join(_ROOT, "melee"))

PUSHES = (0x55, 0x53, 0x57, 0x56)  # push ebp / ebx / edi / esi


def load_map(MAP):
    va2sym = {}
    pat = re.compile(r"\s*[0-9a-f]{4}:[0-9a-f]{8}\s+(\S+)\s+([0-9a-f]{8})\s+f\s")
    for line in open(MAP, encoding="utf-8", errors="replace"):
        m = pat.match(line)
        if m:
            va2sym.setdefault(int(m.group(2), 16), m.group(1))
    return va2sym


def load_bridge(BRIDGE):
    out = []
    pat = re.compile(r"\s*\{\s*0x([0-9A-Fa-f]+)u,\s*0x([0-9A-Fa-f]+)u,\s*(\d)\s*\}")
    for line in open(BRIDGE, encoding="utf-8", errors="replace"):
        m = pat.match(line)
        if m:
            out.append((int(m.group(1), 16), int(m.group(2), 16), int(m.group(3))))
    return out


def pe_reader(path):
    data = open(path, "rb").read()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    nsec = struct.unpack_from("<H", data, pe + 6)[0]
    optsz = struct.unpack_from("<H", data, pe + 20)[0]
    base = struct.unpack_from("<I", data, pe + 24 + 28)[0]
    off = pe + 24 + optsz
    secs = []
    for i in range(nsec):
        e = off + i * 40
        vsize, va, rawsz, rawptr = struct.unpack_from("<IIII", data, e + 8)
        secs.append((va, vsize, rawptr, rawsz))

    def sl(va, n=16):
        rva = va - base
        for sva, vsize, rawptr, rawsz in secs:
            if sva <= rva < sva + max(vsize, rawsz):
                o = rawptr + (rva - sva)
                return data[o:o + n]
        return b""

    return sl


def reads_ecx(b):
    """True if the prologue moves ECX into a callee-saved register (mov r32, ecx = 89 C?)."""
    i = 0
    while i < len(b) and b[i] in PUSHES:
        i += 1
    # 89 /r with reg field = ECX (001) -> modrm 0xC8..0xCF with (modrm>>3)&7 == 1
    return i + 1 < len(b) and b[i] == 0x89 and (b[i + 1] & 0xC0) == 0xC0 \
        and ((b[i + 1] >> 3) & 7) == 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--map", default=DEF_BUILD + "/melee-pc.map")
    ap.add_argument("--exe", default=DEF_BUILD + "/melee-pc.exe")
    ap.add_argument("--bridge", default=DEF_MELEE + "/pc/platform/gw_mex_bridge.c")
    ap.add_argument("--all", action="store_true", help="list every unprefixed target, not just "
                                                      "the ones that read ECX")
    a = ap.parse_args()
    va2sym = load_map(a.map)
    sl = pe_reader(a.exe)
    funcs = [(g, n) for g, n, kind in load_bridge(a.bridge) if kind == 1]
    resolved = [(g, n, va2sym[n]) for g, n in funcs if n in va2sym]
    bare = [(g, n, s) for g, n, s in resolved if not s.startswith("_gw_")]
    risky = [(g, n, s) for g, n, s in bare if reads_ecx(sl(n, 12))]

    print(f"bridge function entries         : {len(funcs)}")
    print(f"  resolved against the live map : {len(resolved)}")
    print(f"  symbol is NOT _gw_-prefixed   : {len(bare)}  (static in its TU)")
    print(f"  ... and reads ECX in prologue : {len(risky)}  <-- called wrong by the bridge")
    print()
    for g, n, s in sorted(a.all and bare or risky)[:40]:
        print(f"   guest 0x{g:08X} -> {s:<40} {' '.join('%02X' % x for x in sl(n, 8))}")
    shown = bare if a.all else risky
    if len(shown) > 40:
        print(f"   ... and {len(shown) - 40} more")
    print()
    print("A target listed above is called with arguments on the stack but reads them from")
    print("registers. Give it external linkage (which forces the platform C ABI), or teach")
    print("gen_bridge.py to mark it so the interpreter can call it __fastcall.")
    return 1 if risky else 0


if __name__ == "__main__":
    sys.exit(main())
