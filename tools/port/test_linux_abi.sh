#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "$0")/../.." && pwd)"
build="${GW_BUILD_ROOT:-$root/_build/agents/linux}/abi-probe"
mkdir -p "$build"
clang --target=ppc32-none-eabi -O2 -Xclang -disable-llvm-passes -fno-builtin -emit-llvm -c "$root/tools/port/tests/abi_guest.c" -o "$build/guest.bc"
"${GW_GWTOOL:-$root/_build/gwtool_linux/gwtool}" --target=i686-unknown-linux-gnu "$build/guest.bc" -o "$build/guest.o"
clang -m32 -O2 -fuse-ld=lld -no-pie "$root/tools/port/tests/abi_host.c" "$build/guest.o" -o "$build/abi-probe"
"$build/abi-probe"
melee="${GW_MELEE:-$root/melee/worktrees/linux}"
clang -m32 -O2 -ffunction-sections -fdata-sections -I "$melee/pc/platform" -I "${GW_SDL_INCLUDE:-${GW_AURORA_LINUX_BUILD:-$root/_build/linux/ax86m}/_deps/sdl-src/include}" \
    "$root/tools/port/tests/linux_compat.c" "$melee/pc/platform/gw_compat_linux.c" \
    -no-pie -fuse-ld=lld -Wl,--gc-sections -lpthread -o "$build/compat-probe"
"$build/compat-probe"
clang -m32 -O2 -I "$melee/pc/platform" -I "$melee/extern/aurora/include" "$root/tools/port/tests/gc_report.c" -o "$build/gc-report-probe"
"$build/gc-report-probe"
