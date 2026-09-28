#!/bin/bash
# Verify that every changed game translation unit still compiles.
#
# Uses the shared Windows pipeline and its exit status; successful compiler output is not
# a failure. Native shims use the shared writer so lane hardlinks are never truncated.
#
# Usage: tools/mex_port/verify_changed.sh [path-prefix]
#   defaults to src/ (game translation units). Pass "pc/" to check platform files instead,
#   which use a different compile command and are NOT covered here.

set -u

. "$(dirname "${BASH_SOURCE[0]}")/../port/portlib.sh"
MELEE_DIR="$GW_MELEE"
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
  failed=0
  case "$f" in
    pc/platform/*)
      # Only pc/platform/ uses clang directly. pc/gameworld/ and pc/tests/ go through the game
      # pipeline like src/, so they fall through to the default branch below.
      out="$(gw_build_shim "${f#pc/platform/}" 2>&1)" || failed=1
      ;;
    *)
      out="$(GW_OUT="$GW_OUT" bash "$GW_ROOT/_build/masstest/pipe_win.sh" "$f" 2>&1)" || failed=1
      ;;
  esac
  if [ "$failed" = 1 ]; then
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
CLANG="$GW_CLANG"
nonpc=0
for f in "${files[@]}"; do
  [ -f "$f" ] || continue
  case "$f" in pc/platform/*) continue ;; esac
  out="$("$CLANG" --target=ppc32-none-eabi -std=c99 -nostdinc -fno-builtin -DLINT \
      -fno-short-enums -fsigned-char -mlong-double-64 -fno-strict-aliasing -fwrapv -fcommon \
      -fgnu89-inline -ftrivial-auto-var-init=zero -O2 -Xclang -disable-llvm-passes -fsyntax-only -w \
      -Isrc -isystem src/MSL -isystem libs/dolphin/include -isystem libs/dolphin/src \
      -isystem build/GALE01/include -include src/MSL/math_ppc.h \
      "$f" 2>&1)"
  if [ -n "$out" ]; then
    echo "NONPC_FAIL $f"
    echo "$out" | head -5 | sed 's/^/    /'
    nonpc=$((nonpc + 1))
  fi
done
echo "verified ${#files[@]} files, ${nonpc} failure(s) [non-TARGET_PC]"
echo "----------------------------------------"

exit $((fails + nonpc > 0))
