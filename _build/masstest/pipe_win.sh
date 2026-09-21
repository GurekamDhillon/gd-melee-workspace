#!/bin/bash
# Git-Bash-side per-TU pipeline. Identical flags to pipe_wsl.sh -- see that file for why
# -fgnu89-inline and -include src/MSL/math_ppc.h are required. The only difference is that both
# the exe arguments and the shell redirections use the same Windows-style view, since Git Bash
# and the toolchain share one filesystem namespace. Run from $GW_MELEE.
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
"$GW_CLANG" --target=ppc32-none-eabi -std=c99 -nostdinc -fno-builtin -DLINT -DTARGET_PC \
  -fno-short-enums -fsigned-char -mlong-double-64 -fno-strict-aliasing -fwrapv -fcommon -fgnu89-inline \
  -ftrivial-auto-var-init=zero -O2 -Xclang -disable-llvm-passes -emit-llvm -c -w \
  -Isrc -isystem src/MSL -isystem libs/dolphin/include -isystem libs/dolphin/src -isystem build/GALE01/include \
  -include src/MSL/math_ppc.h \
  "$f" -o "$d/$n.bc.tmp" 2> "$d/$n.cc.err" || { echo "CC_FAIL $f"; cat "$d/$n.cc.err"; exit 1; }
rm -f "$d/$n.cc.err"
mv -f "$d/$n.bc.tmp" "$d/$n.bc"
"$GW_GWTOOL" ${GW_GWTOOL_FLAGS:-} "$d/$n.bc" -o "$d/$n.obj.tmp" --imports="$d/$n.imports.tmp" 2> "$d/$n.gw.err" || { echo "GW_FAIL $f"; cat "$d/$n.gw.err"; exit 1; }
rm -f "$d/$n.gw.err"
# Write-then-rename, NOT write-in-place. tools/port/agent_new.sh HARDLINKS this baseline into
# every agent's build root, and gwtool truncates its -o path rather than unlinking it - so
# writing directly would mutate the shared inode and land this TU in every other agent's build
# at once. (That cost most of an evening: see docs/HANDOFF.md section 6.) A rename replaces only
# THIS directory entry and leaves the other links pointing at the old inode.
mv -f "$d/$n.obj.tmp" "$d/$n.obj"
mv -f "$d/$n.imports.tmp" "$d/$n.imports"
