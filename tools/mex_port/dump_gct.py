#!/usr/bin/env python3
"""List / extract Gecko codes from a GCT (e.g. Akaneia's codes.gct on the ISO).

Read-only. Understands the code types Akaneia uses: 04 (32-bit write), C2 (insert asm),
plus 00/02 (8/16-bit write) and 06 (string write) for completeness.

  python dump_gct.py --iso C:/iso/Akaneia.iso                     # list every code
  python dump_gct.py --iso C:/iso/Akaneia.iso --addr 0x803D7060   # codes that target this address
  python dump_gct.py --iso C:/iso/Akaneia.iso --addr 0x803D7060 --disasm
  python dump_gct.py --iso ... --range 0x802F9000 0x802FA000      # codes whose target is in range

--disasm dumps a C2 payload to a temp file and runs ppc_disasm.py --raw on it (base 0x81000000,
payloads are position independent). --emit PATH writes the raw payload.
"""
import argparse
import os
import struct
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mex_hsd import Gcm  # noqa: E402


def parse(gct):
    assert gct[:8] == bytes.fromhex("00D0C0DE00D0C0DE"), "not a GCT"
    off = 8
    codes = []
    while off < len(gct):
        w0, w1 = struct.unpack_from(">II", gct, off)
        if w0 == 0xF0000000:
            break
        typ = (w0 >> 24) & 0xFE
        addr = 0x80000000 | (w0 & 0x01FFFFFF)
        if typ == 0xC2:
            n = w1
            payload = gct[off + 8: off + 8 + n * 8]
            codes.append(("C2", addr, off, payload))
            off += 8 + n * 8
        elif typ in (0x00, 0x02, 0x04):
            codes.append(({0: "00", 2: "02", 4: "04"}[typ], addr, off, struct.pack(">I", w1)))
            off += 8
        elif typ == 0x06:
            n = w1
            ln = (n + 7) & ~7
            codes.append(("06", addr, off, gct[off + 8: off + 8 + n]))
            off += 8 + ln
        else:
            raise ValueError(f"unhandled code type {typ:02X} at gct+0x{off:X}")
    return codes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iso")
    ap.add_argument("--gct", help="loose codes.gct instead of --iso")
    ap.add_argument("--addr", type=lambda s: int(s, 0))
    ap.add_argument("--range", nargs=2, type=lambda s: int(s, 0))
    ap.add_argument("--disasm", action="store_true")
    ap.add_argument("--emit")
    a = ap.parse_args()
    gct = Gcm(a.iso).read("codes.gct") if a.iso else open(a.gct, "rb").read()
    codes = parse(gct)
    sel = codes
    if a.addr is not None:
        sel = [c for c in codes if c[1] == a.addr]
    if a.range:
        sel = [c for c in sel if a.range[0] <= c[1] < a.range[1]]
    print(f"# {len(codes)} codes total, {len(sel)} selected")
    for typ, addr, off, payload in sel:
        extra = payload.hex().upper() if typ != "C2" else f"{len(payload)} bytes"
        print(f"{typ} 0x{addr:08X} gct+0x{off:X} {extra}")
        if typ == "C2" and (a.disasm or a.emit):
            path = a.emit or os.path.join(tempfile.gettempdir(), f"gct_{addr:08X}.bin")
            open(path, "wb").write(payload)
            if a.disasm:
                here = os.path.dirname(os.path.abspath(__file__))
                subprocess.run([sys.executable, os.path.join(here, "ppc_disasm.py"), "--raw", path,
                                "--base", "0x81000000", "--start", "0x81000000",
                                "--count", str(len(payload) // 4)])


if __name__ == "__main__":
    main()
