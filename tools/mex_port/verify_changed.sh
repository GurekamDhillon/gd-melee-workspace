#!/bin/bash
# Verify that every changed game translation unit still compiles.
#
# This exists because pipe_wsl.sh reports success in a way that is easy to misread: its failure
# handlers `exit 0`, so a non-zero return code never occurs. The ONLY reliable signal is the
# presence of "CC_FAIL"/"GW_FAIL" in the output, and the diagnostic file it writes is deleted by
# the script itself. Checking $? -- as several sessions have done -- silently passes on failure.
#
# Usage: tools/mex_port/verify_changed.sh [path-prefix]
#   defaults to src/ (game translation units). Pass "pc/" to check platform files instead,
#   which use a different compile command and are NOT covered here.

set -u

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
MELEE_DIR="$REPO_ROOT/melee"
PREFIX="${1:-src/}"

cd "$MELEE_DIR" || { echo "cannot cd to $MELEE_DIR"; exit 1; }

mapfile -t files < <(
  # -uall expands untracked directories. Plain --porcelain collapses them to a single `?? dir/`
  # entry, which the .c filter then drops -- silently hiding every newly added file.
  GIT_MASTER=1 git status --porcelain -uall 2>/dev/null |
    awk '{print $NF}' |
    grep -E "^${PREFIX}.*\.c$" |
    sort -u
)

if [ "${#files[@]}" -eq 0 ]; then
  echo "no changed files under ${PREFIX}"
  exit 0
fi

fails=0
for f in "${files[@]}"; do
  if [ ! -f "$f" ]; then
    echo "SKIP $f (deleted)"
    continue
  fi
  case "$f" in
    pc/platform/*)
      # Only pc/platform/ uses clang directly. pc/gameworld/ and pc/tests/ go through the game
      # pipeline like src/, so they fall through to the default branch below.
      obj="C:/gdm/_build/masstest/shimobj/$(basename "${f%.c}").obj"
      out="$(/mnt/c/gdm/_toolchains/llvm/bin/clang.exe --target=i686-pc-windows-msvc -c -O2 -DTARGET_PC \
          -I C:/gdm/melee/extern/aurora/include -I C:/gdm/melee/pc/platform \
          -I C:/gdm/_build/ax86/_deps/sdl3_prebuilt-src/include \
          "C:/gdm/melee/$f" -o "$obj" 2>&1 | grep -iE 'error:' )"
      ;;
    *)
      out="$(bash /mnt/c/gdm/_build/masstest/pipe_wsl.sh "$f" 2>&1)"
      ;;
  esac
  if [ -n "$out" ]; then
    echo "FAIL $f"
    echo "$out" | sed 's/^/    /'
    fails=$((fails + 1))
  fi
done

echo "----------------------------------------"
echo "verified ${#files[@]} files, ${fails} failure(s) [TARGET_PC]"

# Second pass: compile WITHOUT -DTARGET_PC, which is the only way the `#else` branches that carry
# the original code ever get exercised. The fork's core promise is that those branches keep the
# matching build byte-identical, and every other check in this project passes -DTARGET_PC, so that
# promise was previously unverified.
CLANG=/mnt/c/gdm/_toolchains/llvm/bin/clang.exe
nonpc=0
for f in "${files[@]}"; do
  [ -f "$f" ] || continue
  case "$f" in pc/platform/*) continue ;; esac
  out="$("$CLANG" --target=ppc32-none-eabi -std=c99 -nostdinc -fno-builtin -DLINT \
      -fno-short-enums -fsigned-char -mlong-double-64 -fno-strict-aliasing -fwrapv -fcommon \
      -fgnu89-inline -ftrivial-auto-var-init=zero -O2 -Xclang -disable-llvm-passes -emit-llvm -c -w \
      -Isrc -isystem src/MSL -isystem extern/dolphin/include -isystem extern/dolphin/src \
      -isystem build/GALE01/include -include src/MSL/math_ppc.h \
      "$f" -o "C:/gdm/_build/masstest/out/nonpc_check.bc" 2>&1)"
  if [ -n "$out" ]; then
    echo "NONPC_FAIL $f"
    echo "$out" | head -5 | sed 's/^/    /'
    nonpc=$((nonpc + 1))
  fi
done
rm -f /mnt/c/gdm/_build/masstest/out/nonpc_check.bc
echo "verified ${#files[@]} files, ${nonpc} failure(s) [non-TARGET_PC]"
echo "----------------------------------------"

exit $((fails + nonpc > 0))
