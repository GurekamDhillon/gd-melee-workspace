#!/bin/bash
# Rebuild gwtool natively on Linux, against the system LLVM (no WSL, no MSVC).
#
# AFTER REBUILDING GWTOOL, REBUILD EVERY GAME TU. The ABI pin (pinInternalAbi) is applied per
# TU: objects an older gwtool produced keep the private calling conventions the guest->native
# bridge cannot call, and an exe linked from a mixture is exactly what tools/port/build.sh's
# `abi` step exists to catch.
#
# It finds the workspace beside itself (dirname/..), so it is not relocatable: run it where it
# lives, or set GW_MELEE/GWTOOL_OUT.
set -euo pipefail

GW_ROOT="${GW_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
GW_MELEE="${GW_MELEE:-$GW_ROOT/melee/worktrees/linux}"
GWTOOL_OUT="${GWTOOL_OUT:-$GW_ROOT/_build/gwtool_linux}"
SRC="$GW_MELEE/pc/tools/gwtool"

if [ ! -f "$SRC/gwtool.cpp" ]; then
    echo "error: no gwtool.cpp under $SRC - set GW_MELEE to the melee checkout" >&2
    exit 1
fi

command -v llvm-config >/dev/null || { echo "error: llvm-config not found (install llvm)" >&2; exit 1; }
CXX="${GW_HOST_CXX:-clang++}"

mkdir -p "$GWTOOL_OUT"
"$CXX" -O2 -std=c++17 $(llvm-config --cxxflags) -fno-rtti \
    "$SRC/gwtool.cpp" "$SRC/compression_stubs.cpp" \
    -o "$GWTOOL_OUT/gwtool" \
    $(llvm-config --ldflags) \
    $(llvm-config --libs core irreader bitreader bitwriter passes x86codegen x86asmparser \
        x86desc x86info target analysis transformutils support) \
    $(llvm-config --system-libs)

echo "GWTOOL_OK $GWTOOL_OUT/gwtool"
