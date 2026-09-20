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

# REBUILD ANY GAME TU WHOSE SOURCE IS NEWER THAN ITS OBJECT.
#
# The shim loop below has existed for a while; game TUs never got the same treatment, and that
# gap silently invalidated a day's work. Four TUs sat with sources from 07:43 against objects
# from the previous night - mncharsel.c, tobj.c, ftkirby.c and ground.c - so the CSS fix, the
# tlut_no widening, the Kirby fix and the ACE stage work were NEVER IN A BINARY. Each was then
# "verified" against an exe that did not contain it, and one of those verifications became the
# premise for a whole follow-up investigation that was chasing a ghost. The tell was findable all
# along: the exe did not contain the format string the fix added.
#
# Header changes have no dependency scanner here either, so a TU whose object predates the newest
# header under src/ or include/ is rebuilt too. That is blunt - a header touch can mean all 988 -
# but the full set takes about a minute in parallel, and it is the difference between a slow
# build and a WRONG one.
tu_list="$GW_ROOT/_build/masstest/files.txt"
if [ -f "$tu_list" ]; then
    newest_inc=""
    for h in $(find "$GW_MELEE/src" "$GW_MELEE/include" -name '*.h' -newer "$tu_list" 2>/dev/null); do
        if [ -z "$newest_inc" ] || [ "$h" -nt "$newest_inc" ]; then newest_inc="$h"; fi
    done
    stale_tus="$GW_BUILD_ROOT/.stale_tus"
    : >"$stale_tus"
    while IFS= read -r f; do
        [ -n "$f" ] || continue
        obj="$GW_OUT/$(echo "$f" | tr '/' '_').obj"
        src="$GW_MELEE/$f"
        [ -e "$src" ] || continue
        if [ ! -f "$obj" ] || [ "$src" -nt "$obj" ] ||
           { [ -n "$newest_inc" ] && [ "$newest_inc" -nt "$obj" ]; }; then
            printf '%s
' "$f" >>"$stale_tus"
        fi
    done <"$tu_list"
    n_stale=$(wc -l <"$stale_tus" | tr -d ' ')
    if [ "$n_stale" -gt 0 ]; then
        echo "TUs stale: $n_stale"
        ( cd "$GW_MELEE" && GW_OUT="$GW_OUT" xargs -P 8 -I{} bash "$GW_ROOT/_build/masstest/pipe_win.sh" {} <"$stale_tus" ) ||
            gw_die "a stale TU failed to rebuild"
    fi
    rm -f "$stale_tus"
fi

# REBUILD ANY SHIM WHOSE SOURCE IS NEWER THAN ITS OBJECT.
#
# This used to rebuild a shim only when --shim named it, so editing pc/platform/*.c and running
# build.sh produced a green build of the OLD code. That is not a slow build, it is a WRONG one:
# a night was spent concluding that a committed interpreter fix "did not fix Wolf", from an exe
# that had never contained it - and then re-testing the same stale binary on three discs and
# calling it 63/63. A stale object here does not announce itself anywhere.
#
# Header changes are handled by touching every shim whose object predates the newest header,
# since these sources have no dependency scanner.
newest_hdr=""
for h in "$GW_MELEE"/pc/platform/*.h; do
    [ -e "$h" ] || continue
    if [ -z "$newest_hdr" ] || [ "$h" -nt "$newest_hdr" ]; then newest_hdr="$h"; fi
done
stale=()
for src in "$GW_MELEE"/pc/platform/*.c "$GW_MELEE"/pc/platform/*.cpp; do
    [ -e "$src" ] || continue
    name="$(basename "$src")"
    obj="$GW_SHIMOBJ/${name%.*}.obj"
    if [ ! -f "$obj" ] || [ "$src" -nt "$obj" ] ||
       { [ -n "$newest_hdr" ] && [ "$newest_hdr" -nt "$obj" ]; }; then
        stale+=("$name")
    fi
done
if [ ${#stale[@]} -gt 0 ]; then
    echo "shims stale: ${#stale[@]}"
    for s in "${stale[@]}"; do
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
# symbols.txt and splits.txt come from THIS build's melee worktree, not from $GW_ROOT/melee.
# An agent builds its own checkout's objects, so taking the decomp metadata from the default
# checkout would describe a different tree - and splits.txt is now load-bearing, since it is what
# tells two same-named statics apart.
python "$GW_ROOT/tools/mex_port/gen_bridge.py" --map "$GW_MAP" \
    --symbols "$GW_MELEE/config/GALE01/symbols.txt" \
    --splits "$GW_MELEE/config/GALE01/splits.txt" \
    --out-c "$bridge_c" --out-h "$GW_MELEE/pc/platform/gw_mex_bridge.h" | tail -1
gw_build_shim gw_mex_bridge.c
echo "link  2/2"
gw_link

# The second link moved things again if and only if it changed a gw_ symbol's address, so prove
# the bridge still matches the exe that will actually run.
before="$(md5sum <"$bridge_c")"
python "$GW_ROOT/tools/mex_port/gen_bridge.py" --map "$GW_MAP" \
    --symbols "$GW_MELEE/config/GALE01/symbols.txt" \
    --splits "$GW_MELEE/config/GALE01/splits.txt" \
    --out-c "$bridge_c" --out-h "$GW_MELEE/pc/platform/gw_mex_bridge.h" >/dev/null
after="$(md5sum <"$bridge_c")"
if [ "$before" != "$after" ]; then
    echo "bridge did not reach a fixpoint - rebuilding it once more" >&2
    gw_build_shim gw_mex_bridge.c
    gw_link
fi

# THE BRIDGE ABI, which is the other thing that is silently wrong rather than loudly broken.
# gw_ppc_bridge_call invokes every target as cdecl, arguments on the stack. A game function that
# is `static` in its TU has no caller LLVM can see, so the optimizer used to be free to give it a
# private convention - on i686, `fastcc`: the first two integer arguments in ECX and EDX, floats
# in XMM0-2. grTSeak_80223908 got exactly that, and every m-ex custom stage built map model 0
# three times instead of 0, 1 and 2, so Meta Crystal rendered black.
#
# gwtool now pins internal functions to the C ABI (pinInternalAbi) and verifies it per TU, so
# this should always pass. It is checked here anyway, against the EXE that will actually run,
# because that is the artefact the bridge indexes - and because the commonest way to lose the pin
# is to link objects built by an older gwtool.exe, which no per-TU check can see.
#
# Not through a pipe: `$?` after a pipe is the pipe's status, which has already fooled someone.
echo "abi"
if ! python "$GW_ROOT/tools/mex_port/audit_bridge_abi.py" \
    --map "$GW_MAP" --exe "$GW_EXE" --bridge "$GW_MELEE/pc/platform/gw_mex_bridge.c"; then
    gw_die "the bridge calls a target that reads its arguments from registers (listed above).
       Rebuild gwtool (melee/pc/tools/gwtool/build.bat) and rebuild the TUs those functions
       live in; if it persists, the pin no longer holds and gwtool needs a look."
fi
echo "OK    $GW_EXE"
