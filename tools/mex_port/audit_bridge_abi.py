#!/usr/bin/env python3
"""Audit the guest->native bridge for calling-convention mismatches.

gw_ppc_bridge_call invokes EVERY target through `gw_ppc_native_fn`, which is cdecl: arguments on
the stack. That is correct for the gwtool-retargeted game functions, which are external and get
the platform C ABI. It is NOT correct for a function that was `static` in its TU: the backend is
free to give an internal function a private convention, and on i686 LLVM passes the first
arguments in ECX/EDX. The callee then reads registers the bridge never set.

This prints, for every bridge function entry, whether its map symbol is `_gw_`-prefixed (external,
cdecl) or bare (internal), and for the bare ones whether the prologue actually reads ECX or EDX.

It should now always find none, because gwtool pins internal functions to the C ABI before it
runs the optimization pipeline (`pinInternalAbi`) and verifies per TU that nothing changed a
function's convention or signature. This is the backstop for what that per-TU check cannot see:
an exe linked from objects an older gwtool built. `tools/port/build.sh` runs it after the final
link, so a regression fails the build rather than turning up months later as a bridged call whose
arguments are all zero.

Exits non-zero, and lists them, when it finds any.
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


def reads_argreg(b):
    """The argument register this prologue reads before writing, or None.

    On i686 LLVM's `fastcc` the first two integer arguments arrive in ECX and EDX, and such a
    callee opens by moving them somewhere it can keep them: `mov r32, ecx` / `mov r32, edx`,
    encoded 89 /r with the reg field naming the source. Immediately after the push block, before
    anything has written either register, that is unambiguous - nothing else can have put a value
    there. So this test has no false positives, which is what lets the build gate on it.

    It is deliberately NOT a general convention detector. A fastcc callee whose only register
    arguments are floats takes them in XMM0-2 and this will not see it; so will one that reads
    ECX a few instructions in. Guessing at those from a disassembly is how an audit starts being
    confidently wrong. The exhaustive check lives in the compiler instead: gwtool pins every
    internal function to the C ABI and verifies per TU that the pipeline did not change any
    function's convention or signature. This is the backstop for the one thing gwtool cannot
    see - an exe linked from objects an older gwtool built.
    """
    i = 0
    while i < len(b) and b[i] in PUSHES:
        i += 1
    # 89 /r, mod == 11: reg field 001 = ECX, 010 = EDX.
    if i + 1 < len(b) and b[i] == 0x89 and (b[i + 1] & 0xC0) == 0xC0:
        return {1: "ecx", 2: "edx"}.get((b[i + 1] >> 3) & 7)
    return None


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
    risky = [(g, n, s) for g, n, s in bare if reads_argreg(sl(n, 12)) is not None]

    print(f"bridge function entries          : {len(funcs)}")
    print(f"  resolved against the live map  : {len(resolved)}")
    print(f"  symbol is NOT _gw_-prefixed    : {len(bare)}  (static in its TU)")
    print(f"  ... reads ECX/EDX in prologue  : {len(risky)}  <-- called wrong by the bridge")
    if not risky and not a.all:
        return 0
    print()
    for g, n, s in sorted(a.all and bare or risky)[:40]:
        print(f"   guest 0x{g:08X} -> {s:<40} {' '.join('%02X' % x for x in sl(n, 8))}")
    shown = bare if a.all else risky
    if len(shown) > 40:
        print(f"   ... and {len(shown) - 40} more")
    if not risky:
        return 0
    print()
    print("A target listed above is called with arguments on the stack but reads them from")
    print("registers, so every one of its calls through the bridge gets the wrong arguments.")
    print("gwtool is supposed to make this impossible: pinInternalAbi gives every internal")
    print("function an external, address-taking reference before the optimization pipeline, so")
    print("no pass will retarget it to fastcc or rewrite its signature, and gwtool then verifies")
    print("that per TU. Seeing one here means this exe was linked from objects an OLDER gwtool")
    print("built: rebuild gwtool (melee/pc/tools/gwtool/build.bat), rebuild those TUs and relink.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
