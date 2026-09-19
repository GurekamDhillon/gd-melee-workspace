#!/bin/bash
# Git-Bash-side per-TU pipeline. Identical flags to pipe_wsl.sh -- see that file for why
# -fgnu89-inline and -include src/MSL/math_ppc.h are required. The only difference is that both
# the exe arguments and the shell redirections use the C:/gdm view, since Git Bash and the
# toolchain share one filesystem namespace. Run from C:/gdm/melee.
f="$1"; n=$(echo "$f" | tr '/' '_')
d="${GW_OUT:-C:/gdm/_build/masstest/out}"  # per-agent build root; see tools/port/portlib.sh
mkdir -p "$d"
C:/gdm/_toolchains/llvm/bin/clang.exe --target=ppc32-none-eabi -std=c99 -nostdinc -fno-builtin -DLINT -DTARGET_PC \
  -fno-short-enums -fsigned-char -mlong-double-64 -fno-strict-aliasing -fwrapv -fcommon -fgnu89-inline \
  -ftrivial-auto-var-init=zero -O2 -Xclang -disable-llvm-passes -emit-llvm -c -w \
  -Isrc -isystem src/MSL -isystem libs/dolphin/include -isystem libs/dolphin/src -isystem build/GALE01/include \
  -include src/MSL/math_ppc.h \
  "$f" -o "$d/$n.bc.tmp" 2> "$d/$n.cc.err" || { echo "CC_FAIL $f"; cat "$d/$n.cc.err"; exit 1; }
rm -f "$d/$n.cc.err"
mv -f "$d/$n.bc.tmp" "$d/$n.bc"
C:/gdm/_build/gwtool/gwtool.exe "$d/$n.bc" -o "$d/$n.obj.tmp" --imports="$d/$n.imports.tmp" 2> "$d/$n.gw.err" || { echo "GW_FAIL $f"; cat "$d/$n.gw.err"; exit 1; }
rm -f "$d/$n.gw.err"
# Write-then-rename, NOT write-in-place. tools/port/agent_new.sh HARDLINKS this baseline into
# every agent's build root, and gwtool truncates its -o path rather than unlinking it - so
# writing directly would mutate the shared inode and land this TU in every other agent's build
# at once. (That cost most of an evening: see docs/HANDOFF.md section 6.) A rename replaces only
# THIS directory entry and leaves the other links pointing at the old inode.
mv -f "$d/$n.obj.tmp" "$d/$n.obj"
mv -f "$d/$n.imports.tmp" "$d/$n.imports"
