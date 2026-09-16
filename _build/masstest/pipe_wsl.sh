#!/bin/bash
# WSL-side per-TU pipeline: the current, correct game-world compile for the port.
#  -fgnu89-inline: `extern inline` in MSL headers must not emit a definition per TU
#  -include src/MSL/math_ppc.h: makes sqrtf/sqrtf_accurate the Gekko refinements and declares
#   __frsqrte, which clang does not provide as a builtin (MWERKS_GEKKO would gate it out).
# Exe arguments use Windows paths; shell redirections/rm use the WSL view of the same files.
f="$1"; n=$(echo "$f" | tr '/' '_')
d_win="C:/gdm/_build/masstest/out"
d_wsl="/mnt/c/gdm/_build/masstest/out"
/mnt/c/gdm/_toolchains/llvm/bin/clang.exe --target=ppc32-none-eabi -std=c99 -nostdinc -fno-builtin -DLINT -DTARGET_PC \
  -fno-short-enums -fsigned-char -mlong-double-64 -fno-strict-aliasing -fwrapv -fcommon -fgnu89-inline \
  -ftrivial-auto-var-init=zero -O2 -Xclang -disable-llvm-passes -emit-llvm -c -w \
  -Isrc -isystem src/MSL -isystem extern/dolphin/include -isystem extern/dolphin/src -isystem build/GALE01/include \
  -include src/MSL/math_ppc.h \
  "$f" -o "$d_win/$n.bc" 2> "$d_wsl/$n.cc.err" || { echo "CC_FAIL $f"; cat "$d_wsl/$n.cc.err"; rm -f "$d_wsl/$n.cc.err"; exit 1; }
rm -f "$d_wsl/$n.cc.err"
/mnt/c/gdm/_build/gwtool/gwtool.exe "$d_win/$n.bc" -o "$d_win/$n.obj" --imports="$d_win/$n.imports" 2> "$d_wsl/$n.gw.err" || { echo "GW_FAIL $f"; cat "$d_wsl/$n.gw.err"; rm -f "$d_wsl/$n.gw.err"; exit 1; }
rm -f "$d_wsl/$n.gw.err"
