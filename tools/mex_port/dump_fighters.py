#!/usr/bin/env python3
"""List every fighter an m-ex build defines, from its MxDt.dat (read-only).

    python tools/mex_port/dump_fighters.py --iso <m-ex ISO> [--funcs]

Per internal kind: name, Pl file + ftData symbol, anim file, costume count and files, results /
demo symbols, sound bank (by external id), and which external id maps to it. --funcs adds the
fighter_function slot table (guest addresses of each kind's default callbacks).

Layouts are m-ex's MexTK/include/mxdt.h (MexData.fighter / fighter_function)."""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mex_hsd import Archive, Gcm  # noqa: E402
import dump_mxdt as d  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iso", required=True)
    ap.add_argument("--funcs", action="store_true")
    args = ap.parse_args()
    ar = Archive(Gcm(args.iso).read("MxDt.dat"))
    md = d.MexData(ar)
    meta = md.metadata()
    n_int, n_ext = meta["internal_id_count"], meta["external_id_count"]

    def cstr(p):
        if p == 0 or p >= len(ar.data):
            return None
        b = bytes(ar.data[p:p + 64]).split(b"\0")[0]
        return b.decode("latin-1")

    def ptr(p):
        return ar.u32(p) if 0 < p + 4 <= len(ar.data) else 0

    f = {name: md.fighter_field(name) for name in d.FIGHTER_FIELDS}
    # ft_kind_desc: per EXTERNAL id, 3 bytes {internal, extra_internal (-1 none), has_transform}
    ext_of = {}
    for e in range(n_ext):
        k = ar.u8(f["ft_kind_desc"] + e * 3)
        ext_of.setdefault(k, e)

    print(f"{n_int} internal kinds, {n_ext} external ids")
    for k in range(n_int):
        pl = f["pl_file"] + k * 8
        pl_name, pl_sym = cstr(ptr(pl)), cstr(ptr(pl + 4))
        anim = cstr(ptr(f["anim_filenames"] + k * 4))
        e = ext_of.get(k)
        name = cstr(ptr(f["names"] + e * 4)) if e is not None else None
        ci = f["costume_info"] + (e if e is not None else 0) * 4
        ncost = ar.u8(ci) if e is not None else 0
        cf = ptr(f["costume_file"] + k * 4)
        costumes = [cstr(ptr(cf + c * 16)) for c in range(ar.u8(ci) if e is not None else 0)] if cf else []
        demo = ptr(f["ftdemo"] + k * 4)
        result_sym = cstr(ptr(demo)) if demo else None
        ssm = ar.u8(f["ssm_files"] + e * 0x10) if e is not None else None
        rst = cstr(ptr(f["result_file"] + e * 4)) if e is not None else None
        print(f"[{k:2}] ext={e!s:>4} {name!s:16} {pl_name!s:12} {pl_sym!s:22} anim={anim!s:14} "
              f"costumes={ncost} ssm={ssm} rst={rst} demo={result_sym}")
        if costumes:
            print(f"       costumes: {', '.join(c or '-' for c in costumes)}")
    if args.funcs:
        ff = md.root["fighter_function"]
        slots = []
        for s in range(46):
            t = ptr(ff + s * 4)
            if t == 0 or t >= len(ar.data):
                break
            slots.append(t)
        print(f"fighter_function: {len(slots)} slot tables")
        for k in range(n_int):
            row = [ar.u32(t + k * 4) for t in slots]
            print(f"[{k:2}] " + " ".join(f"{v:08X}" for v in row[:12]))


if __name__ == "__main__":
    main()
