#!/usr/bin/env python3
"""Convert an lld/ld link map into the MSVC-style map the mex_port tools already read.

`tools/mex_port/gen_bridge.py` (the guest->native bridge generator) and
`tools/mex_port/audit_bridge_abi.py` (the ABI backstop) were written against the map MSVC's
`/MAP` writes, because that is what the Windows port links with. On Linux the same link is lld and
the map is a different format - so this translates it instead of teaching two load-bearing tools a
second dialect:

    0001:00309e40       _gw_OSReport_PrintSpaces   1030ae40 f   src_melee_os_ossreport.c.obj

The lld map does not print either of the two columns that matter:

  * the object a symbol came from. It is implied - a symbol is listed under the input section it
    was emitted into - so this walks the map tracking the current object file.
  * whether a symbol is code or data and public or static. That comes from `nm -P` on the linked
    ELF: uppercase type = external (goes in "Publics by Value"), lowercase = internal (goes in the
    "Static symbols" section gen_bridge.py reads for `scope:local` decomp symbols).

Names get an MSVC-style leading underscore (`gw_Foo` -> `_gw_Foo`) because MAP_RE in gen_bridge.py
requires one; it strips exactly one back off. Addresses are 32-bit (this port is i686 on every
platform), so the eight-hex-digit columns match too.

Usage:
    map_to_msvc.py --map melee-pc.map --elf melee-pc --out melee-pc.msvc.map
    map_to_msvc.py --self-test
"""
import argparse
import bisect
import os
import re
import subprocess
import sys
import tempfile

# An output-section header, at column 0: ".text           0x00001040      0x156"
OUT_SECTION_RE = re.compile(r"^(\S+)\s+0x([0-9a-fA-F]+)\s+0x([0-9a-fA-F]+)\s*$")
# An input section: " .text          0x00001040       0x2c /path/to/thing.o"
IN_SECTION_RE = re.compile(r"^\s+(\S+)\s+0x([0-9a-fA-F]+)\s+0x([0-9a-fA-F]+)\s+(\S.*\S|\S)\s*$")
# A symbol under an input section: "                0x00001170                helper"
SYMBOL_RE = re.compile(r"^\s+0x([0-9a-fA-F]+)\s+(\S+)\s*$")
# A definition rather than a placed symbol: "PROVIDE(__rel_iplt_start = .)" / "= ABSOLUTE(.)"
DEFINITION_MARK = re.compile(r"=|PROVIDE")


LLD_ROW = re.compile(r"^\s*([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9]+) (.*)$")


def read_lld(path):
    ranges, symbols = [], {}
    current = ""
    with open(path, encoding="utf-8", errors="replace") as f:
        header = next(f, "")
        if "VMA" not in header or "Symbol" not in header:
            raise ValueError("expected an LLD ELF map (link with -fuse-ld=lld)")
        for line in f:
            m = LLD_ROW.match(line)
            if not m:
                continue
            addr, size = int(m[1], 16), int(m[3], 16)
            value = m[5]
            indent = len(value) - len(value.lstrip())
            value = value.strip()
            if indent == 0:
                current = ""
            elif ":(" in value:
                current = os.path.basename(value.rsplit(":(", 1)[0])
                if size and current != "<internal>":
                    ranges.append((addr, addr + size, current))
            elif indent >= 16 and current and current != "<internal>":
                symbols[(addr, value)] = current
    return sorted(ranges), symbols


def parse_map_sections(path):
    return read_lld(path)[0]


def nm_symbols(elf):
    """-> [(name, type, addr)] from `nm -P`: <name> <type> <value> [<size>]."""
    result = subprocess.run(["nm", "-P", elf], capture_output=True, text=True, check=True)
    out = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        name, typ, value = parts[0], parts[1], parts[2]
        try:
            addr = int(value, 16)
        except ValueError:
            continue  # undefined ('U') and debug symbols have no address
        if typ in ("U", "u", "N", "n", "a", "A"):
            continue
        out.append((name, typ, addr))
    return out


def object_for(ranges, starts, addr):
    """The object file whose input section contains `addr`, or '' - same search as mapsym's."""
    i = bisect.bisect_right(starts, addr)
    if i == 0:
        return ""
    start, end, obj = ranges[i - 1]
    return obj if start <= addr < end else ""


def emit(map_path, elf_path):
    outlines = []
    section_ranges, placed = read_lld(map_path)
    starts = [r[0] for r in section_ranges]

    def row(name, typ, addr):
        obj = placed.get((addr, name), object_for(section_ranges, starts, addr))
        # a function-local static ("gw_nd_classic_plan.pass_of") has no input section of its own; only real gw_ symbols must map
        if name.startswith("gw_") and "." not in name and not obj:
            raise ValueError(f"no originating object for {name} at {addr:#x}")
        # "f" marks a function for audit_bridge_abi.py; data has no letter (MAP_RE allows both).
        letter = {"T": "f", "t": "f", "W": "f", "w": "f"}.get(typ, "d" if typ.isupper() else "")
        return (f" 0001:{addr:08X}       _{name}   {addr:08X}"
                f"{(' ' + letter) if letter else '   '}   {obj}")

    publics, statics = [], []
    for name, typ, addr in nm_symbols(elf_path):
        # The map is authoritative for placement: a symbol the linker did not place is not in it.
        (publics if typ.isupper() else statics).append((addr, name, typ))

    # ELF writable symbols have explicit extents; snapshot code must not infer across gaps.
    for line in subprocess.check_output(["nm", "-S", "-P", elf_path], text=True).splitlines():
        fields = line.split()
        if len(fields) < 4 or fields[1] not in "BbDdGgSs":
            continue
        name, typ, addr, size = fields[:4]
        addr, size = int(addr, 16), int(size, 16)
        obj = placed.get((addr, name), object_for(section_ranges, starts, addr))
        if size and obj:
            outlines.append(f"GW_STATE {addr:08X} {size:08X} _{name} {obj}")
    outlines.append(" Address         Publics by Value              Rva+Base     Lib:Object")
    outlines.append("")
    outlines.extend(row(n, t, a) for a, n, t in sorted(publics))
    outlines.append("")
    outlines.append("Static symbols")
    outlines.append("")
    outlines.extend(row(n, t, a) for a, n, t in sorted(statics))
    return "\n".join(outlines) + "\n"


def _map_re_check(text):
    """The exact MAP_RE from tools/mex_port/gen_bridge.py, applied to the converted file."""
    pattern = re.compile(
        r"^\s*[0-9A-Fa-f]{4}:[0-9A-Fa-f]{8}\s+"
        r"(?P<name>_[A-Za-z0-9_$@?.]+)\s+"
        r"(?P<addr>[0-9A-Fa-f]{8})\b"
        r"(?:(?:\s+[a-z])*\s+(?P<obj>\S+))?\s*$"
    )
    got = {}
    for line in text.splitlines():
        m = pattern.match(line)
        if m:
            got[m.group("name").lstrip("_")] = (m.group("addr"), m.group("obj") or "")
    return got.get("gw_OSReport", ("", ""))[1] == "src_melee_os_ossreport.c.obj"


def self_test():
    """Link a two-object i686 program, convert its map, and check the columns survived.

    This runs a real link rather than reading a canned map, because the whole point of the script
    is that lld's map layout is what it claims: if lld's format moves, this fails here instead of
    silently emptying the static-symbol side of the bridge.
    """
    with tempfile.TemporaryDirectory(prefix="lld map spaces ") as tmp:
        a = os.path.join(tmp, "src_melee_ft_ftdata.c")
        b = os.path.join(tmp, "src_melee_os_ossreport.c")
        open(a, "w").write("static __attribute__((noinline)) int priv(int x){return x+1;}\n"
                           "int gw_FtData_Call(int);\n"
                           "int gw_FtData_Call(int x){return ((int (*)(int))priv)(x);}\n")
        open(b, "w").write("static __attribute__((noinline)) int priv(int x){return x+2;}\n"
                           "int gw_FtData_Call(int x);\n"
                           "int gw_OSReport(void){return gw_FtData_Call(priv(39));}\n"
                           "int main(void){return gw_OSReport();}\n")
        objs = []
        for src in (a, b):
            obj = src + ".obj"
            subprocess.run(["clang", "-m32", "-O0", "-c", src, "-o", obj], check=True)
            objs.append(obj)
        exe = os.path.join(tmp, "toy")
        mapf = os.path.join(tmp, "toy.map")
        subprocess.run(["clang", "-m32", "-fuse-ld=lld", "-no-pie", *objs, "-o", exe,
                        f"-Wl,-Map={mapf}"], check=True)
        text = emit(mapf, exe)
        checks = {
            "public function carries name, address and object": re.search(
                r"^\s*0001:[0-9A-F]{8}\s+_gw_OSReport\s+[0-9A-F]{8} f\s+"
                r"src_melee_os_ossreport\.c\.obj$", text, re.M) is not None,
            "static lands under the Static symbols marker": "_priv" in text.split("Static symbols")[1],
            "object attribution follows the input section": re.search(
                r"_gw_FtData_Call\s+[0-9A-F]{8} f\s+src_melee_ft_ftdata\.c\.obj", text) is not None,
            "gen_bridge.py's MAP_RE accepts the rows": _map_re_check(text),
            "duplicate local names retain both objects": all(re.search(
                r"_priv\s+[0-9A-F]{8} f\s+" + re.escape(os.path.basename(obj)), text)
                for obj in objs),
        }
        for name, ok in checks.items():
            print(f"{'ok  ' if ok else 'FAIL'} {name}")
        if not all(checks.values()):
            print("--- converted map ---")
            print(text)
        return 0 if all(checks.values()) else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--map", help="lld/ld -Map output")
    ap.add_argument("--elf", help="the linked executable")
    ap.add_argument("--out", help="where to write the MSVC-style map (default: stdout)")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    if not (a.map and a.elf):
        ap.error("--map and --elf are required")
    text = emit(a.map, a.elf)
    if a.out:
        open(a.out, "w").write(text)
        print(f"{a.out}: {text.count(chr(10))} lines")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
