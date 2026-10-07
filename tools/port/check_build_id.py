#!/usr/bin/env python3
"""Check that an executable carries the build id stamped in the checkout (tools/port/build_id.py).

    python tools/port/check_build_id.py --melee <checkout> --exe <exe or ELF>

A shim object compiled before pc/platform/gw_build_id.h existed does not list it as a dependency and is
not rebuilt when the header appears; that exe would fall back to the whole-file hash and refuse every build
on another platform. build.sh and build_linux.sh run this after the link and stop on a mismatch.
"""
import argparse, re, sys
from pathlib import Path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--melee', type=Path, required=True)
    ap.add_argument('--exe', type=Path, required=True)
    a = ap.parse_args()
    header = a.melee / 'pc/platform/gw_build_id.h'
    if not header.is_file():
        sys.exit('check_build_id: no %s (run tools/port/build_id.py)' % header)
    m = re.search(r'GW_BUILD_SOURCE_HEX "([0-9a-f]{16})"', header.read_text())
    if not m:
        sys.exit('check_build_id: %s has no GW_BUILD_SOURCE_HEX' % header)
    if ('GWBUILDID:' + m.group(1)).encode() not in a.exe.read_bytes():
        sys.exit('check_build_id: %s does not carry build id %s - gw_netplay.c was compiled without the current gw_build_id.h. '
                 'Rebuild it: build.sh --shim gw_netplay.c' % (a.exe, m.group(1)))
    print('build id  %s is in %s' % (m.group(1), a.exe.name))

if __name__ == '__main__':
    main()
