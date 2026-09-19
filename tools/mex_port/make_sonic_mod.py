#!/usr/bin/env python3
"""Build mods/sonic/ - the files that let the PC port run Sonic on a vanilla Melee disc.

Copies them out of an m-ex build that has Sonic (Akaneia). Read-only on the ISO.

    python tools/mex_port/make_sonic_mod.py --iso C:/iso/Akaneia.iso [--out C:/gdm/_build/mods/sonic]

What goes in, and why (derived with MELEE_DVD_TRACE=1 runs on Akaneia, diffed against vanilla):
  new files       his fighter data, animations, 7 costumes and victory poses (PlSn*), results
                  screen (GmRstMSn), m-ex's data table (MxDt), victory theme (ff_sonic.hps),
                  his sound bank (sonic.ssm) and m-ex's "no bank" slot (null.ssm)
  modified files  PlCo.dat    - its parts table carries Sonic's entry
                  IfAll.usd   - m-ex stock icons (Stc_icns) and emblems (Eblm_matanim_joint)
                  MnSlChr.usd - m-ex character select (mexSelectChr)
                  smash2.sem  - sound scripts for 78 banks. Its retail-bank scripts match vanilla's
                                (same sample ids; m-ex only re-encodes waits), so vanilla .ssm
                                files work with it.
Left out on purpose: Akaneia's re-encoded retail .ssm files, nr_name.ssm (Sonic's announcer line
reuses a retail sample), and everything for Akaneia's other fighters and stages.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mex_hsd import Gcm  # noqa: E402

FILES = [
    "PlSn.dat", "PlSnAJ.dat", "PlSnNr.dat", "PlSnRe.dat", "PlSnGr.dat", "PlSnYe.dat",
    "PlSnBk.dat", "PlSnOr.dat", "PlSnWh.dat", "PlSnDViWaitAJ.dat", "GmRstMSn.dat", "MxDt.dat",
    "audio/ff_sonic.hps", "audio/us/sonic.ssm", "audio/us/null.ssm",
    "PlCo.dat", "IfAll.usd", "MnSlChr.usd", "audio/us/smash2.sem",
]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--iso", required=True, help="an m-ex disc image with Sonic (Akaneia)")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "..", "_build",
                                                  "mods", "sonic"))
    args = ap.parse_args()
    disc = Gcm(args.iso)
    total = 0
    for f in FILES:
        data = disc.read(f)
        dst = os.path.join(args.out, *f.split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as fp:
            fp.write(data)
        total += len(data)
        print(f"  {f:24} {len(data):>9,}")
    print(f"{len(FILES)} files, {total / 1048576:.2f} MiB -> {os.path.normpath(args.out)}")


if __name__ == "__main__":
    main()
