#!/bin/bash
# Build melee-pc.exe correctly, including the step that is easy to forget.
#
#   tools/port/build.sh                          relink only
#   tools/port/build.sh --tu src/melee/ft/ftdata.c --tu src/melee/it/item.c
#   tools/port/build.sh --shim shim_dvd.c
#   tools/port/build.sh --tu ... --shim ... --no-bridge
#
# THE BRIDGE FIXPOINT, which is the reason this script exists: gw_mex_bridge.c maps guest PPC
# addresses to the native functions in THIS exe, and it is generated from melee-pc.map. Any link
# that moves a function invalidates it. A stale bridge does not fail to build and does not crash
# at load - it silently calls the wrong native function (once, it routed a guest address into
# GObj_SetupGXLinkMaxSorted), which is a miserable thing to debug. So the correct sequence is
# always: link -> regenerate the bridge -> compile it -> link again. This script does that every
# time, and then verifies the result really is a fixpoint by regenerating once more and checking
# the file did not change.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
. ./portlib.sh

tus=()
shims=()
bridge=1
while [ $# -gt 0 ]; do
    case "$1" in
    --tu) tus+=("$2"); shift 2 ;;
    --shim) shims+=("$2"); shift 2 ;;
    --no-bridge) bridge=0; shift ;;          # only for a link whose addresses cannot have moved
    -h | --help) sed -n '2,16p' "$0"; exit 0 ;;
    *) gw_die "unknown argument: $1 (see --help)" ;;
    esac
done

gw_env_summary
echo

if [ ${#tus[@]} -gt 0 ]; then
    for f in "${tus[@]}"; do
        echo "TU    $f"
        gw_build_tu "$f"
    done
fi
if [ ${#shims[@]} -gt 0 ]; then
    for s in "${shims[@]}"; do
        echo "shim  $s"
        gw_build_shim "$s"
    done
fi

# A running game holds melee-pc.exe open and the link fails with LNK1104. Say so plainly rather
# than letting the linker's message stand on its own - and only ever complain about THIS build's
# exe, never kill someone else's run.
if [ -f "$GW_EXE" ] && ! ( : >>"$GW_EXE" ) 2>/dev/null; then
    gw_die "$GW_EXE is locked - a run of this build is still going. Close it, or use
       tools/port/run.sh, which runs a copy so a run can never block a link."
fi

echo "link  1/2"
gw_link

if [ "$bridge" = "0" ]; then
    echo "bridge skipped (--no-bridge)"
    exit 0
fi

bridge_c="$GW_MELEE/pc/platform/gw_mex_bridge.c"
echo "bridge"
python "$GW_ROOT/tools/mex_port/gen_bridge.py" --map "$GW_MAP" \
    --out-c "$bridge_c" --out-h "$GW_MELEE/pc/platform/gw_mex_bridge.h" | tail -1
gw_build_shim gw_mex_bridge.c
echo "link  2/2"
gw_link

# The second link moved things again if and only if it changed a gw_ symbol's address, so prove
# the bridge still matches the exe that will actually run.
before="$(md5sum <"$bridge_c")"
python "$GW_ROOT/tools/mex_port/gen_bridge.py" --map "$GW_MAP" \
    --out-c "$bridge_c" --out-h "$GW_MELEE/pc/platform/gw_mex_bridge.h" >/dev/null
after="$(md5sum <"$bridge_c")"
if [ "$before" != "$after" ]; then
    echo "bridge did not reach a fixpoint - rebuilding it once more" >&2
    gw_build_shim gw_mex_bridge.c
    gw_link
fi
echo "OK    $GW_EXE"
