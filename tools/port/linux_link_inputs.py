#!/usr/bin/env python3
"""Generate exact object and library lists from source manifests and Aurora's Ninja link edge."""
import os
from pathlib import Path
import re
import sys
root, melee, build, out, shim, aurora = map(Path, sys.argv[1:])

def sources(path):
    return [s.strip() for s in path.read_text().splitlines() if s.strip() and not s.startswith('#')]
objects = [out / (s.replace('/', '_') + '.obj') for s in sources(Path(os.environ.get('GW_TU_LIST', root / 'tools/port/linux_tus.txt')))]
objects += [shim / (Path(s).stem + '.obj') for s in sources(root / 'tools/port/linux_shims.txt')]
for obj in objects:
    if not obj.is_file(): raise SystemExit(f'Missing required object: {obj}')
# Use the resolved dependencies of Aurora's actual CMake target, including shared Unix libraries.
lines = (aurora / 'build.ninja').read_text().splitlines()
edge = next((i for i, s in enumerate(lines) if s.startswith('build examples/simple: ')), None)
if edge is None: raise SystemExit('Aurora simple link edge missing; configure the dependency build')
linkline = next((s.split(' = ', 1)[1] for s in lines[edge+1:edge+15] if s.startswith('  LINK_LIBRARIES = ')), None)
if linkline is None: raise SystemExit('Aurora dependency link libraries missing')
# Ninja escapes literal spaces with $ ; preserve them before splitting.
words = linkline.replace('$ ', '\0').split()
libs = []
for word in words:
    word = word.replace('\0', ' ').replace('$$', '$')
    if word.startswith('-'):
        libs.append(word)
    else:
        p = Path(word)
        p = p if p.is_absolute() else aurora / p
        if not p.is_file(): raise SystemExit(f'Missing Aurora dependency: {p}')
        libs.append(str(p))
for name in ('os', 'pad', 'si', 'card', 'mtx', 'gd', 'ms'):
    p = aurora / f'libaurora_{name}.a'
    if not p.is_file(): raise SystemExit(f'Missing Aurora archive: {p}')
    libs.append(str(p))
libs.append(str(Path(os.environ.get('GW_ENET_BUILD', root / '_build/linux/enet')) / 'libenet.a'))
libs.append(str(Path(os.environ.get('GW_LIBUSB_BUILD', root / '_build/linux/libusb')) / 'install/lib/libusb-1.0.a'))

def quote(s):
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"') + '"'
(build / 'link_objects_linux.rsp').write_text('\n'.join(map(quote, objects)) + '\n')
(build / 'link_libraries_linux.rsp').write_text('\n'.join(map(quote, libs)) + '\n')
print(f'link {len(objects)} objects, {len(libs)} libraries')
