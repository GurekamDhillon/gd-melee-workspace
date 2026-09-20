#!/bin/bash
# WSL-side per-TU pipeline: the current, correct game-world compile for the port.
#  -fgnu89-inline: `extern inline` in MSL headers must not emit a definition per TU
#  -include src/MSL/math_ppc.h: makes sqrtf/sqrtf_accurate the Gekko refinements and declares
#   __frsqrte, which clang does not provide as a builtin (MWERKS_GEKKO would gate it out).
# Exe arguments use Windows paths; shell redirections/rm use the WSL view of the same files.
f="$1"; n=$(echo "$f" | tr '/' '_')
# GW_ROOT_WIN is the Windows-style root (the toolchain is native and cannot read /mnt/c),
# GW_ROOT the WSL-style one. Both default off this script's location. See SETUP.md.
GW_ROOT="${GW_ROOT:-$( cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd )}"
GW_ROOT_WIN="${GW_ROOT_WIN:-$( echo "$GW_ROOT" | sed -E 's#^/mnt/([a-z])/#\U\1:/#' )}"
d_win="${GW_OUT_WIN:-$GW_ROOT_WIN/_build/masstest/out}"
d_wsl="$GW_ROOT/_build/masstest/out"
$GW_ROOT/_toolchains/llvm/bin/clang.exe --target=ppc32-none-eabi -std=c99 -nostdinc -fno-builtin -DLINT -DTARGET_PC \
  -fno-short-enums -fsigned-char -mlong-double-64 -fno-strict-aliasing -fwrapv -fcommon -fgnu89-inline \
  -ftrivial-auto-var-init=zero -O2 -Xclang -disable-llvm-passes -emit-llvm -c -w \
  -Isrc -isystem src/MSL -isystem libs/dolphin/include -isystem libs/dolphin/src -isystem build/GALE01/include \
  -include src/MSL/math_ppc.h \
  "$f" -o "$d_win/$n.bc" 2> "$d_wsl/$n.cc.err" || { echo "CC_FAIL $f"; cat "$d_wsl/$n.cc.err"; rm -f "$d_wsl/$n.cc.err"; exit 1; }
rm -f "$d_wsl/$n.cc.err"
$GW_ROOT/_build/gwtool/gwtool.exe "$d_win/$n.bc" -o "$d_win/$n.obj.tmp" --imports="$d_win/$n.imports.tmp" 2> "$d_wsl/$n.gw.err" || { echo "GW_FAIL $f"; cat "$d_wsl/$n.gw.err"; rm -f "$d_wsl/$n.gw.err"; exit 1; }
rm -f "$d_wsl/$n.gw.err"
# Write-then-rename, NOT write-in-place - see the matching note in pipe_win.sh. gwtool truncates
# its -o path instead of unlinking it, and agent_new.sh hardlinks this baseline into every
# agent's build root, so a direct write lands this TU in every other agent's build at once.
mv -f "$d_wsl/$n.obj.tmp" "$d_wsl/$n.obj"
mv -f "$d_wsl/$n.imports.tmp" "$d_wsl/$n.imports"
