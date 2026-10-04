#!/bin/bash
# Linux per-TU pipeline: clang (PPC frontend) -> gwtool -> i686-unknown-linux-gnu ELF object.
# The Linux counterpart of pipe_win.sh / pipe_wsl.sh; same flags, same output names, no Windows
# path dancing (one filesystem namespace, and both tools are native ELF binaries here).
#
# Object NAMES stay "<path with / -> _>.obj" on purpose: tools/mex_port/gen_bridge.py derives the
# object a guest address belongs to from splits.txt as `src_<path>.obj`, and matches that against
# the object column of the link map. Renaming to .o here would silently empty the static-symbol
# side of the bridge.
#
# The flags are the load-bearing part, not ceremony (see docs/DEVLOG.md §2):
#  -fgnu89-inline   `extern inline` in the MSL headers must not emit a definition per TU
#  -include src/MSL/math_ppc.h
#                   makes sqrtf/sqrtf_accurate the Gekko refinements and declares __frsqrte,
#                   which clang has no builtin for (MWERKS_GEKKO would gate it out otherwise)
#  -O2 -Xclang -disable-llvm-passes
#                   keep the IR unoptimized: gwtool does the lowering itself
set -euo pipefail
f="$1"
n="$(echo "$f" | tr '/' '_')"

# GW_ROOT is the workspace root (_build/masstest -> up two). GW_MELEE is the checkout to build
# from; it defaults to the shared checkout but tools/port/build_linux.sh points it at a lane.
GW_ROOT="${GW_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
GW_MELEE="${GW_MELEE:-$GW_ROOT/melee/worktrees/linux}"
GW_CLANG="${GW_CLANG:-clang}"
GW_GWTOOL="${GW_GWTOOL:-$GW_ROOT/_build/gwtool_linux/gwtool}"
# The Linux port's object format. See gwtool.cpp's --target comment for why ELF has to keep the
# Windows environment's layout: the game's aggregates have 8-byte-aligned i64s on PowerPC, and plain
# i686-linux aligns them to 4, which the layout check refuses (correctly).
GW_GWTOOL_TARGET="${GW_GWTOOL_TARGET:-i686-unknown-linux-gnu}"

d="${GW_OUT:-$GW_ROOT/_build/masstest/out}"
# The workspace's own checkout may be empty in a fresh clone; build from GW_MELEE, which is where
# the sources and libs/ are, but keep objects in GW_OUT.
cd "$GW_MELEE"
mkdir -p "$d"
tmp_suffix=".$$.${RANDOM}"
bc_tmp="$d/$n.bc$tmp_suffix.tmp"
obj_tmp="$d/$n.obj$tmp_suffix.tmp"
imports_tmp="$d/$n.imports$tmp_suffix.tmp"
dep_tmp="$d/$n.obj.d$tmp_suffix.tmp"
cc_err="$d/$n.cc$tmp_suffix.err"
gw_err="$d/$n.gw$tmp_suffix.err"
rm -f "$d/$n.obj" "$d/$n.obj.inputs.json"
trap 'rm -f "$bc_tmp" "$obj_tmp" "$imports_tmp" "$dep_tmp" "$cc_err" "$gw_err"' EXIT

"$GW_CLANG" --target=ppc32-none-eabi -std=c99 -nostdinc -fno-builtin -DLINT -DTARGET_PC \
  -fno-short-enums -fsigned-char -mlong-double-64 -fno-strict-aliasing -fwrapv -fcommon -fgnu89-inline \
  -ftrivial-auto-var-init=zero -O2 -Xclang -disable-llvm-passes -emit-llvm -c -w \
  -Isrc -Ipc -isystem src/MSL -isystem libs/dolphin/include -isystem libs/dolphin/src -isystem build/GALE01/include \
  -include src/MSL/math_ppc.h -MD -MF "$dep_tmp" -MT object \
  "$f" -o "$bc_tmp" 2> "$cc_err" || { echo "CC_FAIL $f"; cat "$cc_err"; exit 1; }
mv -f "$bc_tmp" "$d/$n.bc"

"$GW_GWTOOL" --target="$GW_GWTOOL_TARGET" ${GW_GWTOOL_FLAGS:-} "$d/$n.bc" -o "$obj_tmp" --imports="$imports_tmp" 2> "$gw_err" ||
    { echo "GW_FAIL $f"; cat "$gw_err"; exit 1; }

# Write-then-rename, NOT write-in-place: gwtool truncates its -o path rather than unlinking it, and
# a lane's build root may hold hardlinks to a shared baseline (tools/port/agent_new.sh), so a
# direct write would land this TU in every other lane's build at once.
mv -f "$obj_tmp" "$d/$n.obj"
mv -f "$imports_tmp" "$d/$n.imports"
mv -f "$dep_tmp" "$d/$n.obj.d"

python3 "$GW_ROOT/tools/port/stale_linux.py" --record "$d/$n.obj" --mode tu --root "$GW_MELEE" --source "$f"
