#!/bin/bash
# Build Aurora (+ Dawn, + SDL3) for a 32-bit x86 (i686) Linux host - the counterpart of
# _build/build_aurora_melee.bat, same features and same set of targets.
#
# Why 32-bit: the retargeted game keeps GameCube 32-bit pointers in game memory, and an i686 host
# makes a game pointer and a host pointer the same width - so MEM1 at 0x80000000 and the game's
# own "< 0x80000000 means ARAM" rule hold unchanged (shim_ar.c, gw_runtime.c). gwtool emits
# i686-unknown-linux-gnu objects to match; there is no x86-64 variant of this port.
#
# Three differences from the Windows recipe, all forced by what exists on Linux:
#   - Dawn: no i686 Linux prebuilt is published, so AURORA_DAWN_PROVIDER=vendor builds it from
#     source at the pinned ref (AuroraDependencyVersions.cmake). Dawn's host codegen tools build
#     32-bit too and run fine, because multilib is installed.
#   - SDL3: lib32-sdl3 is not packaged, so AURORA_SDL3_PROVIDER=vendor builds 3.4.10 from source.
#   - Vulkan is the only backend (D3D12/Metal are not Linux); Aurora's own Linux defaults pick
#     DAWN_ENABLE_VULKAN=ON and DAWN_USE_WAYLAND=ON.
#
# The libraries land in $BUILD and are linked by tools/port/link_linux.sh.
set -euo pipefail
GW_ROOT="${GW_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
GW_MELEE="${GW_MELEE:-$GW_ROOT/melee/worktrees/linux}"
BUILD="${GW_AURORA_LINUX_BUILD:-$GW_ROOT/_build/linux/ax86m}"
JOBS="${GW_JOBS:-8}"
AURORA_SRC="$GW_MELEE/extern/aurora"

[ -f "$AURORA_SRC/CMakeLists.txt" ] || {
    echo "error: no Aurora at $AURORA_SRC - set GW_MELEE to the melee checkout" >&2
    exit 1
}
echo "aurora    $AURORA_SRC"
echo "build     $BUILD"
echo "jobs      $JOBS"

source_options=()
if [ -n "${GW_DEPS_SOURCE_CACHE:-}" ]; then
    # Reuse only source trees; every library is rebuilt for this toolchain/sysroot.
    for source in "$GW_DEPS_SOURCE_CACHE"/*-src; do
        [ -d "$source" ] || continue
        dependency="$(basename "$source" -src)"
        source_options+=("-DFETCHCONTENT_SOURCE_DIR_${dependency^^}=$source")
    done
fi
cmake -S "$AURORA_SRC" -B "$BUILD" -G Ninja "${source_options[@]}" \
    -DCMAKE_BUILD_TYPE=RelWithDebInfo \
    -DCMAKE_MAKE_PROGRAM="$(command -v ninja)" \
    -DCMAKE_C_COMPILER="${GW_CLANG:-clang}" \
    -DCMAKE_CXX_COMPILER="${GW_CLANGXX:-clang++}" \
    -DAURORA_ENABLE_TESTS=OFF \
    -DCMAKE_C_FLAGS=-m32 \
    -DCMAKE_CXX_FLAGS=-m32 \
    -DCMAKE_ASM_FLAGS=-m32 \
    -DCMAKE_EXE_LINKER_FLAGS=-m32 \
    -DCMAKE_SHARED_LINKER_FLAGS=-m32 \
    -DAURORA_DAWN_PROVIDER=vendor \
    -DAURORA_SDL3_PROVIDER=vendor \
    -DAURORA_ENABLE_DVD=OFF \
    -DAURORA_ENABLE_CARD=ON \
    -DAURORA_ENABLE_THP=OFF \
    -DAURORA_ENABLE_RMLUI=OFF

# Dawn is fetched from a tag, so the one 32-bit source fix it needs ships as a patch here rather
# than as an edit to a file that a clean configure would re-fetch. The configure above is what
# populates _deps/dawn-src, so this has to run after it and before the build; the grep makes it
# idempotent (a second run finds the source already fixed and does nothing).
DAWN_PATCH="$GW_ROOT/tools/port/patches/dawn-32bit-vk-null-handle.patch"
DAWN_SOURCE="${GW_DEPS_SOURCE_CACHE:-$BUILD/_deps}/dawn-src"
DAWN_VK_ALLOC="$DAWN_SOURCE/src/dawn/native/vulkan/ResourceMemoryAllocatorVk.cpp"
if [ -f "$DAWN_VK_ALLOC" ] && grep -q 'dedicatedInfo.buffer = VK_NULL_HANDLE;' "$DAWN_VK_ALLOC"; then
    echo "dawn patch: applying $(basename "$DAWN_PATCH")"
    patch -d "$DAWN_SOURCE" -p1 < "$DAWN_PATCH"
fi

# The port links aurora_core/gx/main/vi plus os/pad/si/card, which the "simple" example alone
# does not build - and a stale lib here does not announce itself. Same target set as
# build_aurora_melee.bat.
cmake --build "$BUILD" -j "$JOBS" --target simple aurora_os aurora_pad aurora_si aurora_card

echo AURORA_LINUX_BUILD_OK "$BUILD"
