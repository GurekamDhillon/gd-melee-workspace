#!/usr/bin/env python3
"""Dump m-ex's sound-bank (SSM / "FGM") tables out of MxDt.dat, offline.

mexData root +0x10 (`MexData.ssm`, m-ex Header.s `Arch_FGM`) points at a 4-word struct:

    +0x00 Files         char*[ssm_count]      bank file names (relative to audio/us/)
    +0x04 Flags         {u32 size; u32 flag}[ssm_count]  ("ssm buffer sizes"; size is
                        recomputed from the disc at boot by m-ex, flag = retail's 2nd word)
    +0x08 LookupTable   {s8 group; s8 load_prio; s8 unload_prio; s8 x3}[ssm_count]
                        ("audio groups": the widened form of retail s32_arr_803BB5D0)
    +0x0C RuntimeStruct {Header, ToLoadOrig, ToLoadCopy, IsLoadedOrig, IsLoadedCopy, Footer}
                        six pointers to runtime s32 arrays (zeroed/-1 at boot)

Per-fighter (`MexData.fighter +0x38`, Header.s Arch_Fighter_SSMFileIDs) is
{u8 ssm_id; pad[7]; u64 mask} x external_id_count - the same 16-byte layout as retail
lbl_803BB3C0, indexed by EXTERNAL character id (CharacterKind).

Usage:
    python dump_ssm.py --iso C:/iso/Akaneia.iso
"""

import argparse
import struct

import mex_hsd
from dump_mxdt import MexData


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iso", required=True)
    ap.add_argument("--dat", default="MxDt.dat")
    args = ap.parse_args()

    gcm = mex_hsd.Gcm(args.iso)
    ar = mex_hsd.Archive(gcm.read(args.dat)).relocate(0)
    md = MexData(ar)
    meta = md.metadata()
    n = meta["ssm_count"]
    n_ext = meta["external_id_count"]
    n_int = meta["internal_id_count"]
    fgm = md.root["ssm"]
    files, flags, lookup, runtime = (ar.u32(fgm + i * 4) for i in range(4))
    print(f"mexData.ssm @0x{fgm:X}: Files=0x{files:X} Flags=0x{flags:X} "
          f"LookupTable=0x{lookup:X} RuntimeStruct=0x{runtime:X}")
    print(f"ssm_count={n} ext={n_ext} int={n_int}")
    # runtime struct words
    rt = [ar.u32(runtime + i * 4) for i in range(6)]
    print("RuntimeStruct words:", " ".join(f"0x{x:X}" for x in rt))

    names = []
    print("\n id  file                      disc_size   tbl_size  flag  grp lprio uprio x3")
    for i in range(n):
        p = ar.u32(files + i * 4)
        name = ar.cstr(p) if p else None
        names.append(name)
        size = ar.u32(flags + i * 8)
        flag = ar.u32(flags + i * 8 + 4)
        g = struct.unpack(">4b", bytes(ar.data[lookup + i * 4: lookup + i * 4 + 4]))
        disc = None
        if name:
            ent = gcm.files.get("audio/us/" + name)
            disc = ent[1] if ent else None
        print(f"{i:3d}  {str(name):24s} {str(disc):>10s} {size:10d} {flag:5d}  "
              f"{g[0]:3d} {g[1]:5d} {g[2]:5d} {g[3]:2d}")

    fid = md.fighter_field("ssm_files")
    names_tbl = md.fighter_field("names")
    print(f"\nfighter.ssm_files @0x{fid:X}  (16-byte stride, EXTERNAL id)")
    for k in range(max(n_ext, n_int) + 2):
        e = fid + k * 16
        if e + 16 > len(ar.data):
            break
        sid = ar.u8(e)
        pad = bytes(ar.data[e + 1:e + 8]).hex()
        mask = (ar.u32(e + 8) << 32) | ar.u32(e + 12)
        nm_p = ar.u32(names_tbl + k * 4) if k < n_int else 0
        bits = [b for b in range(64) if mask >> b & 1]
        print(f"  [{k:2d}] ssm_id={sid:3d} ({names[sid] if sid < n else '-'})"
              f"  pad={pad} mask=0x{mask:016X} bits={bits}"
              f"  name@int={ar.cstr(nm_p) if nm_p else ''}")


if __name__ == "__main__":
    main()
