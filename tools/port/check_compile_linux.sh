#!/bin/bash
# Linux COMPILE check: compile the game TUs and the native shims for the 32-bit Linux build, nothing else.
# No link, no bridge, no disc, no window, no game started. Exit 0 = everything compiled, 1 = a compile failed.
#
# Runs INSIDE the rootless Ubuntu 22.04 build environment (WSL ~/lb2, entered by ~/lb2/enter.sh); the
# Windows entry point is check_compile_linux.ps1, which sets the variables below and calls this through
# enter.sh. On a native Ubuntu 22.04 box it runs as is, with the same variables.
#
# Required environment:
#   GW_MELEE         the game checkout to compile (a normal melee checkout: needs build/GALE01/include and extern/)
#   GW_GWTOOL        the Linux gwtool executable (tools/port/build_gwtool_linux.sh builds it)
#   GW_DEPS_SOURCE_CACHE   the pinned Aurora dependency sources (sdl-src, imgui-src, dawn-src); headers only
#   GW_DAWN_GEN_INCLUDE   Dawn's generated headers (dawn-build/gen/include of an Aurora build); the gw_fx_* shims need them
#   GW_LIBUSB_BUILD a libusb install prefix's parent (<it>/install/include/libusb-1.0)
#   GW_BUILD_ROOT    where objects go (kept between runs: a second run recompiles only what changed)
# Options:
#   --quick          one batch of 24 TUs spread across the list, plus every shim (minutes, not the full set)
#   --tus-only       game TUs only         --shims-only   shims only
#   --tu <path>      (repeatable) just these TUs, e.g. src/melee/ft/ftdata.c
#   --all            ignore the staleness scan and recompile everything
set -uo pipefail
GW_ROOT="${GW_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
for v in GW_MELEE GW_GWTOOL GW_DEPS_SOURCE_CACHE GW_LIBUSB_BUILD GW_BUILD_ROOT; do
    [ -n "${!v:-}" ] || { echo "error: $v is not set" >&2; exit 2; }
done
export GW_ROOT GW_BUILD_ROOT GW_MELEE GW_GWTOOL
export GW_TU_LIST="${GW_TU_LIST:-$GW_ROOT/tools/port/linux_tus.txt}"
export GW_SDL_INCLUDE="$GW_DEPS_SOURCE_CACHE/sdl-src/include"
export GW_IMGUI_INCLUDE="$GW_DEPS_SOURCE_CACHE/imgui-src"
export GW_DAWN_INCLUDE="$GW_DEPS_SOURCE_CACHE/dawn-src/include"
export PKG_CONFIG_LIBDIR=/usr/lib/i386-linux-gnu/pkgconfig:/usr/share/pkgconfig

do_tus=1; do_shims=1; quick=0; sel=(); extra=()
while [ $# -gt 0 ]; do
    case "$1" in
    --quick) quick=1; shift ;;
    --tus-only) do_shims=0; shift ;;
    --shims-only) do_tus=0; shift ;;
    --tu) sel+=(--tu "$2"); shift 2 ;;
    --all) extra+=(--all); shift ;;
    -h | --help) sed -n '2,21p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
done
[ -x "$GW_GWTOOL" ] || { echo "error: no gwtool at $GW_GWTOOL" >&2; exit 2; }
[ -d "$GW_MELEE/build/GALE01/include" ] || { echo "error: $GW_MELEE has no build/GALE01/include (is it a built melee checkout?)" >&2; exit 2; }
for t in clang python3; do command -v "$t" > /dev/null || { echo "error: $t not found: run inside the Linux build environment" >&2; exit 2; }; done
mkdir -p "$GW_BUILD_ROOT"
log="$GW_BUILD_ROOT/check-compile.log"
: > "$log"
echo "melee   $GW_MELEE" | tee -a "$log"
echo "build   $GW_BUILD_ROOT" | tee -a "$log"

fail=0
run() { echo "== $*" | tee -a "$log"; bash "$GW_ROOT/tools/port/build_linux.sh" "$@" 2>&1 | tee -a "$log"; return "${PIPESTATUS[0]}"; }

if [ ${#sel[@]} -gt 0 ]; then
    run "${sel[@]}" --tus-only "${extra[@]}" || fail=1
else
    if [ "$quick" = 1 ] && [ "$do_tus" = 1 ]; then
        n="$(wc -l < "$GW_TU_LIST")"
        step=$(( n / 24 > 0 ? n / 24 : 1 ))
        picks=(); i=0
        # a temp file, not process substitution: the build environment's chroot has no /dev/fd
        tr -d '\r' < "$GW_TU_LIST" > "$GW_BUILD_ROOT/tu-list.lf"
        while IFS= read -r tu; do
            [ $((i % step)) -eq 0 ] && picks+=(--tu "$tu")
            i=$((i + 1))
        done < "$GW_BUILD_ROOT/tu-list.lf"
        [ ${#picks[@]} -gt 0 ] || { echo "error: no TUs picked from $GW_TU_LIST" >&2; exit 2; }
        run "${picks[@]}" --tus-only "${extra[@]}" || fail=1
    elif [ "$do_tus" = 1 ]; then
        run --tus-only "${extra[@]}" || fail=1
    fi
    if [ "$do_shims" = 1 ]; then
        run --shims-only "${extra[@]}" || fail=1
    fi
fi

# build_linux.sh's pipes print CC_FAIL / GW_FAIL / SHIM_FAIL for a failed unit: count them, whatever the exit codes said.
failed="$(grep -cE '^(CC_FAIL|GW_FAIL|SHIM_FAIL) ' "$log" || true)"
if [ "$fail" != 0 ] || [ "${failed:-0}" != 0 ]; then
    echo "LINUX COMPILE CHECK FAILED (${failed:-0} unit(s) reported a failure; full log: $log)"
    grep -E '^(CC_FAIL|GW_FAIL|SHIM_FAIL) ' "$log" | sort -u | head -40
    exit 1
fi
echo "LINUX COMPILE CHECK PASSED (log: $log)"
