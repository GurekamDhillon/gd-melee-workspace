#!/bin/bash
# Run through ubuntu_shell.sh after ubuntu_setup.sh.
set -euo pipefail
export GW_ROOT=/work
export GW_MELEE="${GW_MELEE:-/work/melee/worktrees/linux}"
export GW_BUILD_ROOT=/work/_build/linux/ubuntu22
export GW_AURORA_LINUX_BUILD=/work/_build/linux/ubuntu22-aurora
export GW_GWTOOL=/work/_build/linux/ubuntu22-gwtool/gwtool
export GWTOOL_OUT=/work/_build/linux/ubuntu22-gwtool
export GW_LIBUSB_BUILD=/work/_build/linux/ubuntu22-libusb
export GW_ENET_BUILD=/work/_build/linux/ubuntu22-enet
export GW_JOBS="${GW_JOBS:-8}"
export PKG_CONFIG_LIBDIR=/usr/lib/i386-linux-gnu/pkgconfig:/usr/share/pkgconfig
if [ -d /work/_build/linux/ax86m/_deps ]; then
    export GW_DEPS_SOURCE_CACHE=/work/_build/linux/ax86m/_deps
    export GW_SDL_INCLUDE="$GW_DEPS_SOURCE_CACHE/sdl-src/include"
    export GW_IMGUI_INCLUDE="$GW_DEPS_SOURCE_CACHE/imgui-src"
    export GW_DAWN_INCLUDE="$GW_DEPS_SOURCE_CACHE/dawn-src/include"
fi
bash /work/tools/port/build_gwtool_linux.sh
bash /work/tools/port/build_aurora_linux.sh
cmake -S "$GW_MELEE/extern/enet" -B "$GW_ENET_BUILD" -G Ninja \
    -DCMAKE_C_COMPILER=clang -DCMAKE_C_FLAGS=-m32 -DCMAKE_BUILD_TYPE=RelWithDebInfo
cmake --build "$GW_ENET_BUILD" -j "$GW_JOBS"
bash /work/tools/port/build_libusb_linux.sh
bash /work/tools/port/build_linux.sh
