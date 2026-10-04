#!/bin/bash
# Git-Bash-side per-TU pipeline. Identical flags to pipe_wsl.sh -- see that file for why
# -fgnu89-inline and -include src/MSL/math_ppc.h are required. The only difference is that both
# the exe arguments and the shell redirections use the same Windows-style view, since Git Bash
# and the toolchain share one filesystem namespace. Run from $GW_MELEE.
set -euo pipefail
f="$1"; n=$(echo "$f" | tr '/' '_')

# NOT TIED TO A PARTICULAR CHECKOUT PATH. GW_ROOT defaults to this script's grandparent
# (_build/masstest -> the repo root); portlib.sh exports it and that wins. The toolchain is native
# Windows and cannot read /c/... paths, so the root is converted to a Windows-style path.
if [ -z "${GW_ROOT:-}" ]; then
    GW_ROOT="$( cd "$(dirname "${BASH_SOURCE[0]}")/../.." && { pwd -W 2>/dev/null || pwd; } |
        sed -E 's#^/([a-zA-Z])/#\1:/#' )"
fi
GW_CLANG="${GW_CLANG:-$GW_ROOT/_toolchains/llvm/bin/clang.exe}"
GW_GWTOOL="${GW_GWTOOL:-$GW_ROOT/_build/gwtool/gwtool.exe}"

d="${GW_OUT:-$GW_ROOT/_build/masstest/out}"  # per-agent build root; see tools/port/portlib.sh
mkdir -p "$d"
tmp_suffix=".$$.${RANDOM}"
bc_tmp="$d/$n.bc$tmp_suffix.tmp"
obj_tmp="$d/$n.obj$tmp_suffix.tmp"
imports_tmp="$d/$n.imports$tmp_suffix.tmp"
dep_tmp="$d/$n.obj.d$tmp_suffix.tmp"
cc_err="$d/$n.cc$tmp_suffix.err"
gw_err="$d/$n.gw$tmp_suffix.err"
trap 'rm -f "$bc_tmp" "$obj_tmp" "$imports_tmp" "$dep_tmp" "$cc_err" "$gw_err"' EXIT
"$GW_CLANG" --target=ppc32-none-eabi -std=c99 -nostdinc -fno-builtin -DLINT -DTARGET_PC \
  -fno-short-enums -fsigned-char -mlong-double-64 -fno-strict-aliasing -fwrapv -fcommon -fgnu89-inline \
  -ftrivial-auto-var-init=zero -O2 -Xclang -disable-llvm-passes -emit-llvm -c -w \
  -Isrc -Ipc -isystem src/MSL -isystem libs/dolphin/include -isystem libs/dolphin/src -isystem build/GALE01/include \
  -include src/MSL/math_ppc.h -MD -MF "$dep_tmp" -MT object \
  "$f" -o "$bc_tmp" 2> "$cc_err" || { echo "CC_FAIL $f"; cat "$cc_err"; exit 1; }
mv -f "$bc_tmp" "$d/$n.bc"
"$GW_GWTOOL" ${GW_GWTOOL_FLAGS:-} "$d/$n.bc" -o "$obj_tmp" --imports="$imports_tmp" 2> "$gw_err" || { echo "GW_FAIL $f"; cat "$gw_err"; exit 1; }
# Write-then-rename, NOT write-in-place. tools/port/agent_new.sh HARDLINKS this baseline into
# every agent's build root, and gwtool truncates its -o path rather than unlinking it - so
# writing directly would mutate the shared inode and land this TU in every other agent's build
# at once. (That cost most of an evening: see docs/HANDOFF.md section 6.) A rename replaces only
# THIS directory entry and leaves the other links pointing at the old inode.
mv -f "$obj_tmp" "$d/$n.obj"
mv -f "$imports_tmp" "$d/$n.imports"
mv -f "$dep_tmp" "$d/$n.obj.d"
