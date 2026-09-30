#!/bin/bash
# Compile ONE native shim (pc/platform/<name>.c|.cpp) for the 32-bit Linux build.
#
# The Linux counterpart of gw_build_shim() in tools/port/portlib.sh, with the same output layout
# (GW_SHIMOBJ/<stem>.obj) so tools/port/link_linux.sh and the bridge tooling see the same shape as
# the Windows build. Objects stay *.obj on purpose - see the note at the top of
# pc/build/masstest/pipe_linux.sh.
#
# Flags: clang -m32 (i686-linux-gnu, the host ABI the Aurora/Dawn/SDL3 libraries here are built
# with) plus -DTARGET_PC, which is what selects the port's own code paths in the shims.
set -euo pipefail
src="${1:?usage: shim_linux.sh <name.c|name.cpp>}"

GW_ROOT="${GW_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
GW_MELEE="${GW_MELEE:-$GW_ROOT/melee/worktrees/linux}"
GW_CLANG="${GW_CLANG:-clang}"
GW_SHIMOBJ="${GW_SHIMOBJ:-$GW_ROOT/_build/agents/linux/shimobj}"
AURORA_BUILD="${GW_AURORA_LINUX_BUILD:-$GW_ROOT/_build/linux/ax86m}"
GW_SDL_INCLUDE="${GW_SDL_INCLUDE:-$AURORA_BUILD/_deps/sdl-src/include}"
GW_IMGUI_INCLUDE="${GW_IMGUI_INCLUDE:-$AURORA_BUILD/_deps/imgui-src}"
GW_DAWN_INCLUDE="${GW_DAWN_INCLUDE:-$AURORA_BUILD/_deps/dawn-src/include}"
GW_DAWN_GEN_INCLUDE="${GW_DAWN_GEN_INCLUDE:-$AURORA_BUILD/_deps/dawn-build/gen/include}"

[ -f "$GW_MELEE/pc/platform/$src" ] || { echo "error: no such shim: pc/platform/$src" >&2; exit 1; }

name="$(basename "$src")"
name="${name%.*}"
mkdir -p "$GW_SHIMOBJ"
rm -f "$GW_SHIMOBJ/$name.obj" "$GW_SHIMOBJ/$name.obj.sha256"
suffix=".$$.${RANDOM}"
obj_tmp="$GW_SHIMOBJ/$name.obj$suffix.tmp"
dep_tmp="$GW_SHIMOBJ/$name.obj.d$suffix.tmp"
cc_err="$GW_SHIMOBJ/$name.cc$suffix.err"
trap 'rm -f "$obj_tmp" "$dep_tmp" "$cc_err"' EXIT

cc=("$GW_CLANG" -m32 -c -O2 -g -DTARGET_PC
    -I "$GW_MELEE/extern/aurora/include" -I "$GW_MELEE/pc/platform" -I "$GW_SDL_INCLUDE"
    -I "$GW_MELEE/extern/enet/include" -I "${GW_LIBUSB_BUILD:-$GW_ROOT/_build/linux/libusb}/install/include/libusb-1.0" -I /usr/include/freetype2)
case "$src" in
*.cpp)
    # gw_overlay.cpp is the only C++ shim that drives Dear ImGui, which Aurora builds for its own
    # overlay and the port links (libimgui.a). The gw_fx_* shims use Aurora's Dawn-based draw API,
    # and Dawn's C++ headers need C++20 (std::span).
    cpp_standard=c++17
    case "$src" in gw_fx_*.cpp) cpp_standard=c++20 ;; esac
    cc=("${cc[@]}" -std="$cpp_standard" -DWEBGPU_DAWN
        -I "$GW_IMGUI_INCLUDE" -I "$GW_DAWN_INCLUDE" -I "$GW_DAWN_GEN_INCLUDE")
    [ -d "$GW_IMGUI_INCLUDE" ] ||
        { echo "error: no ImGui headers at $GW_IMGUI_INCLUDE - is the Aurora build done?" >&2; exit 1; }
    ;;
esac

if ! "${cc[@]}" -MD -MF "$dep_tmp" -MT object "$GW_MELEE/pc/platform/$src" -o "$obj_tmp" \
        >"$cc_err" 2>&1; then
    cat "$cc_err" >&2
    echo "SHIM_FAIL $src"
    exit 1
fi
grep -E "error|warning: .*(uninitialized|implicit)" "$cc_err" || true
[ -f "$obj_tmp" ] && [ -f "$dep_tmp" ] || { echo "error: shim $src produced no object" >&2; exit 1; }
mv -f "$obj_tmp" "$GW_SHIMOBJ/$name.obj"
mv -f "$dep_tmp" "$GW_SHIMOBJ/$name.obj.d"

python3 "$GW_ROOT/tools/port/stale_linux.py" --record "$GW_SHIMOBJ/$name.obj" --mode shim --root "$GW_MELEE/pc/platform" --source "$src"
