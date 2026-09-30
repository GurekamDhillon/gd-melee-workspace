#!/bin/bash
# Link the Linux port: an i686 ELF executable from the gwtool-transformed game objects, the native
# shims, and the Aurora/Dawn/SDL3 libraries built by tools/port/build_aurora_linux.sh.
#
# The counterpart of _build/build_melee_pc.bat. Three differences, all Linux-side:
#   - lld writes the map (clang -Wl,-Map=), which tools/port/map_to_msvc.py converts into the
#     MSVC-shaped map the bridge tooling reads. gen_bridge.py needs it to resolve guest addresses
#     to native ones, so the map is an input to the build, not a debugging extra.
#   - -no-pie: the game's own globals must live at fixed addresses (the crash log and melee-pc.map
#     are read together, and shim_ar.c's "< 0x80000000 means ARAM" rule assumes the image sits above
#     ARAM, which is why the Windows link pins /BASE:0x10000000).
#   - everything is static except libc/libstdc++/libm, so the executable is the whole build.
set -euo pipefail
GW_ROOT="${GW_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
GW_MELEE="${GW_MELEE:-$GW_ROOT/melee/worktrees/linux}"
GW_BUILD_ROOT="${GW_BUILD_ROOT:-$GW_ROOT/_build/agents/linux}"
GW_OUT="${GW_OUT:-$GW_BUILD_ROOT/out}"
GW_SHIMOBJ="${GW_SHIMOBJ:-$GW_BUILD_ROOT/shimobj}"
GW_EXE="${GW_EXE:-$GW_BUILD_ROOT/melee}"
GW_MAP="${GW_MAP:-$GW_BUILD_ROOT/melee-pc.map}"
AURORA_BUILD="${GW_AURORA_LINUX_BUILD:-$GW_ROOT/_build/linux/ax86m}"
GW_CLANGXX="${GW_CLANGXX:-clang++}"
JOBS="${GW_JOBS:-$(nproc)}"

[ -d "$AURORA_BUILD" ] || {
    echo "error: no Aurora build at $AURORA_BUILD - run tools/port/build_aurora_linux.sh" >&2
    exit 1
}
mkdir -p "$GW_BUILD_ROOT"

python3 "$GW_ROOT/tools/port/linux_link_inputs.py" "$GW_ROOT" "$GW_MELEE" "$GW_BUILD_ROOT" "$GW_OUT" "$GW_SHIMOBJ" "$AURORA_BUILD"
exe_tmp="$GW_EXE.pending"
map_tmp="$GW_MAP.pending"
trap 'rm -f "$exe_tmp" "$map_tmp"' EXIT
"$GW_CLANGXX" -m32 -no-pie -O1 -fuse-ld=lld \
    "-Wl,-Map=$map_tmp" -Wl,--gc-sections -Wl,-z,noexecstack -Wl,--build-id=sha1 -Wl,--image-base=0x10000000 \
    "-Wl,-T,$GW_ROOT/tools/port/linux_fixups.ld" \
    -o "$exe_tmp" @"$GW_BUILD_ROOT/link_objects_linux.rsp" \
    -Wl,--start-group @"$GW_BUILD_ROOT/link_libraries_linux.rsp" -Wl,--end-group \
    -lm -ldl -lpthread -lrt
mv -f "$exe_tmp" "$GW_EXE"
mv -f "$map_tmp" "$GW_MAP"
echo "LINK_OK $GW_EXE"
