#!/usr/bin/env python3
"""Map every Gecko code in the ACE codes.gct to a decomp symbol (read-only).

  python tools/research/ace_gecko_map.py --iso "$GW_ISO_ACE" --symbols melee/config/GALE01/symbols.txt \
      [--match REGEX] [--disasm]
Prints: type, target address, symbol+offset, size. With --match only symbols whose name matches the regex.
--disasm dumps C2 payloads with tools/mex_port/ppc_disasm.py (raw, base 0x81000000).
Output contains code addresses and instruction text of the mod's patches (not disc game data dumps beyond the patch itself).
"""
import argparse, bisect, os, re, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
MP = os.path.join(HERE, "..", "mex_port")
sys.path.insert(0, MP)
from mex_hsd import Gcm
from dump_gct import parse

def load_syms(path):
    syms = []
    for l in open(path, encoding="utf8", errors="replace"):
        m = re.match(r"(\S+) = \.\w+:0x([0-9A-Fa-f]+); // type:function size:0x([0-9A-Fa-f]+)", l)
        if m: syms.append((int(m.group(2), 16), int(m.group(3), 16), m.group(1)))
    syms.sort()
    return syms

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iso", required=True); ap.add_argument("--symbols", required=True)
    ap.add_argument("--match"); ap.add_argument("--disasm", action="store_true")
    a = ap.parse_args()
    syms = load_syms(a.symbols); starts = [s[0] for s in syms]
    codes = parse(Gcm(a.iso).read("codes.gct"))
    for typ, addr, off, payload in codes:
        i = bisect.bisect_right(starts, addr) - 1
        name = "?"
        if i >= 0 and addr < syms[i][0] + syms[i][1]:
            name = f"{syms[i][2]}+0x{addr - syms[i][0]:X}"
        if a.match and not re.search(a.match, name): continue
        extra = payload.hex().upper() if typ != "C2" else f"{len(payload)}B"
        print(f"{typ} 0x{addr:08X} gct+0x{off:X} {name} {extra}")
        if a.disasm and typ == "C2":
            p = os.path.join(tempfile.gettempdir(), f"gct_{addr:08X}.bin"); open(p, "wb").write(payload)
            subprocess.run([sys.executable, os.path.join(MP, "ppc_disasm.py"), "--raw", p, "--base", "0x81000000",
                            "--start", "0x81000000", "--count", str(len(payload) // 4)])
main()
