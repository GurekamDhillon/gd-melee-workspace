#!/usr/bin/env python3
"""Count which m-ex API entries (the MexTK helper region 0x803D7058..0x803D70A8) disc content calls.

    python tools/mex_port/scan_api_calls.py --iso C:/iso/Akaneia.iso --iso "C:/iso/SSBM ACE Build v2.0.0.iso"

m-ex's installer turns vanilla's gmResultCharacterData into a table of branch trampolines, one per
MexTK API function, and fighter/stage code calls them like any game function. The port has no
m-ex code there, so every entry content reaches needs a native shim in
gw_mex_interp_resolve (melee/pc/platform/gw_mex_ftfunction_runtime.c).

Per relocated blob (every ftFunction, itFunction article and grFunction), three ways in:
  call / br   a `bl` / `b` whose relocated target is an entry
  reloc       an instruction reloc (abs32 / hi16 / lo16) whose target is an entry - a pointer
  imm / word  a `lis 0x803D` + `addi`/`ori` pair, or a raw data word, that spells an entry
              without any reloc
Result on Akaneia and ACE v2.0.0 (2026-09-21): only call/br, only to IndexFighterItem, calloc,
SFX_PlayStageSFX, GetPlaylist, GetFtItemID, GetGrItemID and GetData - all shimmed. The other
entries are called only by m-ex's own codes.gct hooks, which the port reimplements natively.
"""
import argparse
import collections
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mex_hsd  # noqa: E402
import scan_leftover_args as S  # noqa: E402

LO, HI = 0x803D7058, 0x803D70A8
NAMES = {  # MexTK/links/melee.link, plus the two slots named after their m-ex payloads
    0x803D7058: "MEX_IndexFighterItem", 0x803D7060: "Mex_GetStockIconFrame",
    0x803D706C: "calloc", 0x803D7070: "itFunctionInit", 0x803D7074: "MEX_RelocRelArchive",
    0x803D7078: "SFX_PlayStageSFX", 0x803D707C: "MEX_GetPlaylist",
    0x803D7080: "KirbyStateChange", 0x803D7084: "MEX_GetKirbyCpData",
    0x803D7088: "MEX_GetFtItemID", 0x803D708C: "MEX_GetGrItemID", 0x803D7090: "MenuThink",
    0x803D7094: "MEX_GetData", 0x803D709C: "MEX_LoadRelArchive",
}


def scan_blob(fn, hits, who, base):
    blob, _ = fn.relocated_code(S.CODE_BASE)
    n = len(blob) // 4
    w = struct.unpack(">%dI" % n, blob[:n * 4])
    for i, x in enumerate(w):
        _, kind, t = S.decode(x, S.CODE_BASE + i * 4)
        if kind in ("call", "br") and t is not None and LO <= t < HI:
            hits[(t, kind)] += 1
            who[(t, kind)].add(base)
        elif LO <= x < HI:
            hits[(x, "word")] += 1
            who[(x, "word")].add(base)
        if x >> 26 == 15 and (x & 0xFFFF) == 0x803D:  # lis rD,0x803D
            rd = (x >> 21) & 31
            for y in w[i + 1:i + 8]:
                if y >> 26 in (14, 24) and ((y >> 16) & 31) == rd:
                    lo = y & 0xFFFF
                    if y >> 26 == 14 and lo & 0x8000:
                        lo -= 0x10000
                    v = (0x803D0000 + lo) & 0xFFFFFFFF
                    if LO <= v < HI:
                        hits[(v, "imm")] += 1
                        who[(v, "imm")].add(base)
                    break
    for flag, _, target in fn.instr_relocs():
        if flag != 0x0A and LO <= target < HI:
            hits[(target, "reloc")] += 1
            who[(target, "reloc")].add(base)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--iso", action="append", required=True)
    args = ap.parse_args()
    for iso in args.iso:
        gcm = mex_hsd.Gcm(iso)
        hits, who = collections.Counter(), collections.defaultdict(set)
        nblobs = 0
        for path in sorted(gcm.files):
            base = path.rsplit("/", 1)[-1]
            if not base.endswith(".dat"):
                continue
            raw = gcm.read(path)
            if b"Function\0" not in raw:
                continue
            try:
                ar = mex_hsd.Archive(raw).relocate(0)
            except Exception:  # noqa: BLE001 - not an HSD archive
                continue
            for _, fn in S.blobs_in(ar):
                S.recover_size(ar, fn)
                nblobs += 1
                scan_blob(fn, hits, who, base)
        print("== %s: %d blobs" % (os.path.basename(iso), nblobs))
        called = {t for t, _ in hits}
        for (t, kind), c in sorted(hits.items()):
            files = " ".join(sorted(who[(t, kind)]))
            print("  %08X %-22s %-5s %4d  %s" % (t, NAMES.get(t, "?"), kind, c,
                                                  files if len(files) < 100 else files[:97] + "..."))
        idle = [a for a in range(LO, HI, 4) if a not in called]
        print("  not referenced: " + ", ".join("%08X %s" % (a, NAMES.get(a, "(unnamed)"))
                                               for a in idle))


if __name__ == "__main__":
    main()
