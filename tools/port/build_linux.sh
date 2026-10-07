#!/bin/bash
# Build the Melee PC port for a 32-bit x86 (i686) Linux host.
#
# The counterpart of tools/port/build.sh, for the Linux lane. Same shape: compile what is stale,
# link, regenerate the guest->native bridge from the link map, relink, prove the bridge is a
# fixpoint, then audit the bridge ABI against the executable that will actually run.
#
# Why every step exists is documented in build.sh; the Linux-specific parts are:
#   - game TUs go clang(ppc32) -> gwtool -> i686 ELF   (pc/build/masstest/pipe_linux.sh)
#   - the link is clang++/lld                          (tools/port/link_linux.sh), and its map must
#     be converted into the MSVC-shaped one the bridge tools read (tools/port/map_to_msvc.py)
#   - staleness comes from the depfiles clang writes, not content hashes (tools/port/stale_linux.py)
#
# Usage:
#   tools/port/build_linux.sh                     compile what is stale, then link
#   tools/port/build_linux.sh --tu src/melee/ft/ftdata.c --tu src/melee/it/item.c
#   tools/port/build_linux.sh --shim shim_dvd.c
#   tools/port/build_linux.sh --tus-only          compile every stale game TU, no link
#   tools/port/build_linux.sh --shims-only        compile every stale shim, no link
#   tools/port/build_linux.sh --all               ignore the staleness scan
#   tools/port/build_linux.sh --link-only
set -euo pipefail
GW_ROOT="${GW_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
GW_MELEE="${GW_MELEE:-$GW_ROOT/melee/worktrees/linux}"
GW_BUILD_ROOT="${GW_BUILD_ROOT:-$GW_ROOT/_build/agents/linux}"
GW_OUT="${GW_OUT:-$GW_BUILD_ROOT/out}"
GW_SHIMOBJ="${GW_SHIMOBJ:-$GW_BUILD_ROOT/shimobj}"
GW_EXE="${GW_EXE:-$GW_BUILD_ROOT/melee}"
GW_MAP="${GW_MAP:-$GW_BUILD_ROOT/melee-pc.map}"
GW_CLANG="${GW_CLANG:-clang}"
GW_GWTOOL="${GW_GWTOOL:-$GW_ROOT/_build/gwtool_linux/gwtool}"
GW_JOBS="${GW_JOBS:-$(python3 -c 'import os; m=int(next(x.split()[1] for x in open("/proc/meminfo") if x.startswith("MemAvailable:"))); print(max(1,min(12,os.cpu_count() or 1,m//1500000)))')}"
TU_LIST="${GW_TU_LIST:-$GW_ROOT/tools/port/linux_tus.txt}"

tus=(); shims=(); stage=build; force=""
while [ $# -gt 0 ]; do
    case "$1" in
    --tu) tus+=("$2"); shift 2 ;;
    --shim) shims+=("$2"); shift 2 ;;
    --tus-only) stage=tus; shift ;;
    --shims-only) stage=shims; shift ;;
    --link-only) stage=link; shift ;;
    --all) force="--all"; shift ;;
    -h | --help) sed -n '2,22p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 1 ;;
    esac
done

export GW_BUILD_ROOT GW_EXE GW_MAP
export GW_ROOT GW_MELEE GW_OUT GW_SHIMOBJ GW_CLANG GW_GWTOOL GW_JOBS
export GW_AURORA_LINUX_BUILD="${GW_AURORA_LINUX_BUILD:-$GW_ROOT/_build/linux/ax86m}"

export GW_LINUX_FINGERPRINT_TU="$(python3 "$GW_ROOT/tools/port/stale_linux.py" --fingerprint tu)"
export GW_LINUX_FINGERPRINT_SHIM="$(python3 "$GW_ROOT/tools/port/stale_linux.py" --fingerprint shim)"

echo "melee     $GW_MELEE"
echo "build     $GW_BUILD_ROOT"
echo "exe       $GW_EXE"
echo "jobs      $GW_JOBS"
mkdir -p "$GW_OUT" "$GW_SHIMOBJ" "$GW_BUILD_ROOT"
# The source identity netplay compares (pc/platform/gw_build_id.h): see tools/port/build_id.py.
python3 "$GW_ROOT/tools/port/build_id.py" --melee "$GW_MELEE"

[ -f "$TU_LIST" ] || { echo "error: no TU list at $TU_LIST" >&2; exit 1; }
[ -x "$GW_GWTOOL" ] || { echo "error: no gwtool at $GW_GWTOOL (see tools/port/build_gwtool_linux.sh)" >&2; exit 1; }

compile_tus() {
    local list="$1" n
    n="$(wc -l < "$list")"
    [ "$n" -gt 0 ] || { echo "TUs      up to date"; return 0; }
    echo "TUs      $n stale"
    xargs -P "$GW_JOBS" -I{} bash "$GW_ROOT/tools/port/pipe_linux.sh" {} < "$list"
}

compile_shims() {
    local list="$1" n
    n="$(wc -l < "$list")"
    [ "$n" -gt 0 ] || { echo "shims    up to date"; return 0; }
    echo "shims    $n stale"
    xargs -P "$GW_JOBS" -I{} bash "$GW_ROOT/tools/port/shim_linux.sh" {} < "$list"
}

# --- game TUs: an explicit selection, or everything whose object is missing/stale -------------
if [ "$stage" = build ] || [ "$stage" = tus ]; then
    if [ ${#tus[@]} -gt 0 ]; then
        printf '%s\n' "${tus[@]}" > "$GW_BUILD_ROOT/tu-selection.txt"
        compile_tus "$GW_BUILD_ROOT/tu-selection.txt"
    else
        python3 "$GW_ROOT/tools/port/stale_linux.py" --mode tu --sources "$TU_LIST" \
            --objects "$GW_OUT" --root "$GW_MELEE" $force > "$GW_BUILD_ROOT/tu-stale.txt"
        compile_tus "$GW_BUILD_ROOT/tu-stale.txt"
    fi
fi

# --- shims: every pc/platform source that is stale (the Windows build's conservative rule) ----
if [ "$stage" = build ] || [ "$stage" = shims ]; then
    if [ ${#shims[@]} -gt 0 ]; then
        printf '%s\n' "${shims[@]}" > "$GW_BUILD_ROOT/shim-selection.txt"
        compile_shims "$GW_BUILD_ROOT/shim-selection.txt"
    else
        cp "$GW_ROOT/tools/port/linux_shims.txt" "$GW_BUILD_ROOT/shim-sources.txt"
        python3 "$GW_ROOT/tools/port/stale_linux.py" --mode shim \
            --sources "$GW_BUILD_ROOT/shim-sources.txt" --objects "$GW_SHIMOBJ" \
            --root "$GW_MELEE/pc/platform" $force > "$GW_BUILD_ROOT/shim-stale.txt"
        compile_shims "$GW_BUILD_ROOT/shim-stale.txt"
    fi
fi

[ "$stage" = build ] || [ "$stage" = link ] || exit 0

# --- link, bridge regeneration, relink, fixpoint, ABI audit -----------------------------------
# The bridge maps guest PPC addresses to native functions in THIS executable, so any link that
# moves a function invalidates it - and a stale bridge does not fail, it calls the wrong function.
# Hence: link, regenerate from the map, recompile what includes the new header, link again, and
# check that a further regeneration changes nothing (build.sh's fixpoint proof).
bridge_c="$GW_MELEE/pc/platform/gw_mex_bridge.c"
bridge_h="$GW_MELEE/pc/platform/gw_mex_bridge.h"
echo "link  1"
bash "$GW_ROOT/tools/port/link_linux.sh"
python3 "$GW_ROOT/tools/port/map_to_msvc.py" --map "$GW_MAP" --elf "$GW_EXE" \
    --out "$GW_BUILD_ROOT/melee-pc.msvc.map" > /dev/null

linked_bridge_header="$(cat "$bridge_c" "$bridge_h" | sha256sum)"
for pass in 1 2 3 4; do
    echo "bridge check $pass/4"
    python3 "$GW_ROOT/tools/mex_port/gen_bridge.py" --map "$GW_BUILD_ROOT/melee-pc.msvc.map" \
        --symbols "$GW_MELEE/config/GALE01/symbols.txt" \
        --splits "$GW_MELEE/config/GALE01/splits.txt" \
        --out-c "$bridge_c" --out-h "$bridge_h" | tail -1
    generated="$(cat "$bridge_c" "$bridge_h" | sha256sum)"
    if [ "$generated" = "$linked_bridge_header" ]; then
        echo "bridge stable"
        break
    fi
    [ "$pass" -lt 4 ] || {
        echo "error: bridge did not reach a fixpoint after 4 passes; do not run this exe" >&2
        exit 1
    }
    echo "bridge changed; recompiling shims that include it, then relinking"
    bash "$GW_ROOT/tools/port/shim_linux.sh" gw_mex_bridge.c
    for src in "$GW_MELEE"/pc/platform/*.c "$GW_MELEE"/pc/platform/*.cpp; do
        name="$(basename "$src")"
        [ "$name" = "gw_mex_bridge.c" ] && continue
        if grep -lq 'gw_mex_bridge\.h' "$src" 2>/dev/null; then
            bash "$GW_ROOT/tools/port/shim_linux.sh" "$name"
        fi
    done
    echo "link  $((pass + 1)) (bridge)"
    bash "$GW_ROOT/tools/port/link_linux.sh"
    python3 "$GW_ROOT/tools/port/map_to_msvc.py" --map "$GW_MAP" --elf "$GW_EXE" \
        --out "$GW_BUILD_ROOT/melee-pc.msvc.map" > /dev/null
    linked_bridge_header="$generated"
done

# The ABI backstop: a bridged target that reads its arguments from registers means an object built
# by an older gwtool, which no per-TU check can see (see audit_bridge_abi.py).
echo "abi"
python3 "$GW_ROOT/tools/mex_port/audit_bridge_abi.py" --map "$GW_BUILD_ROOT/melee-pc.msvc.map" \
    --exe "$GW_EXE" --bridge "$bridge_c" || {
    echo "error: the bridge calls a target that reads its arguments from registers (listed above)" >&2
    exit 1
}
mkdir -p "$GW_BUILD_ROOT/bridge"
cp "$bridge_c" "$bridge_h" "$GW_BUILD_ROOT/bridge/"
sha256sum "$GW_EXE" "$GW_BUILD_ROOT/melee-pc.msvc.map" > "$GW_BUILD_ROOT/validated.sha256"
echo "OK    $GW_EXE"
