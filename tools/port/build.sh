#!/bin/bash
# Build melee-pc.exe correctly, including the step that is easy to forget.
#
#   tools/port/build.sh                          relink only
#   tools/port/build.sh --tu src/melee/ft/ftdata.c --tu src/melee/it/item.c
#   tools/port/build.sh --shim shim_dvd.c
#   tools/port/build.sh --tu ... --shim ... --no-bridge
#   tools/port/build.sh --native-test slippi-wire   build and run an isolated native test
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
    --native-test)
        [ $# -eq 2 ] || gw_die "--native-test requires exactly one test name and no other options"
        GW_ROOT="$GW_ROOT" GW_MELEE="$GW_MELEE" GW_BUILD_ROOT="$GW_BUILD_ROOT" \
            GW_CLANG="$GW_CLANG" bash ./native_test.sh "$2"
        exit $?
        ;;
    -h | --help) sed -n '2,16p' "$0"; exit 0 ;;
    *) gw_die "unknown argument: $1 (see --help)" ;;
    esac
done

gw_env_summary
GW_GWTOOL="${GW_GWTOOL:-$GW_ROOT/_build/gwtool/gwtool.exe}"
GW_GWTOOL_FLAGS="${GW_GWTOOL_FLAGS:-}"
GW_JOBS="${GW_JOBS:-}"
export GW_ROOT GW_BUILD_ROOT GW_MELEE GW_OUT GW_SHIMOBJ GW_CLANG GW_GWTOOL GW_GWTOOL_FLAGS GW_JOBS
export GW_SDL_INCLUDE GW_IMGUI_INCLUDE GW_DAWN_INCLUDE GW_DAWN_GEN_INCLUDE
jobs="$(python "$GW_ROOT/tools/port/build_objects.py" jobs)" || gw_die "invalid GW_JOBS"
# The source identity netplay compares (pc/platform/gw_build_id.h, git-ignored): the same on any platform that
# builds the same sources; a changed header rebuilds only gw_netplay.c. See tools/port/build_id.py.
python "$GW_ROOT/tools/port/build_id.py" --melee "$GW_MELEE" || gw_die "could not stamp the build id"
source_token="$(python "$GW_ROOT/tools/port/build_provenance.py" --melee "$GW_MELEE" \
    --build "$GW_BUILD_ROOT" --snapshot)" || gw_die "could not snapshot build inputs"
echo "jobs      $jobs"
echo

if [ ${#tus[@]} -gt 0 ]; then
    tu_args=()
    for f in "${tus[@]}"; do tu_args+=(--tu "$f"); done
    python "$GW_ROOT/tools/port/build_objects.py" game --jobs "$jobs" "${tu_args[@]}" ||
        gw_die "explicit TU compilation failed"
fi
if [ ${#shims[@]} -gt 0 ]; then
    shim_args=()
    for s in "${shims[@]}"; do shim_args+=(--shim "$s"); done
    python "$GW_ROOT/tools/port/build_objects.py" shim --jobs "$jobs" "${shim_args[@]}" ||
        gw_die "explicit shim compilation failed"
fi

# REBUILD GAME TUs SELECTED BY CONTENT HASHES.
#
# The shim loop below has existed for a while; game TUs never got the same treatment, and that
# gap silently invalidated a day's work. Four TUs sat with sources from 07:43 against objects
# from the previous night - mncharsel.c, tobj.c, ftkirby.c and ground.c - so the CSS fix, the
# tlut_no widening, the Kirby fix and the ACE stage work were NEVER IN A BINARY. Each was then
# "verified" against an exe that did not contain it, and one of those verifications became the
# premise for a whole follow-up investigation that was chasing a ghost. The tell was findable all
# along: the exe did not contain the format string the fix added.
#
# Older objects without dependency records rebuild once. Each compiled object
# records every actual clang include, including forced and system include roots.
tu_list="$GW_ROOT/_build/masstest/files.txt"
if [ -f "$tu_list" ]; then
    python "$GW_ROOT/tools/port/build_objects.py" game --jobs "$jobs" --files "$tu_list" ||
        gw_die "stale TU compilation failed"
fi

# REBUILD NATIVE SHIMS SELECTED BY CONTENT HASHES.
#
# This used to rebuild a shim only when --shim named it, so editing pc/platform/*.c and running
# build.sh produced a green build of the OLD code. That is not a slow build, it is a WRONG one:
# a night was spent concluding that a committed interpreter fix "did not fix Wolf", from an exe
# that had never contained it - and then re-testing the same stale binary on three discs and
# calling it 63/63. A stale object here does not announce itself anywhere.
#
# Older shims without dependency records rebuild once to establish provenance.
python "$GW_ROOT/tools/port/build_objects.py" shim --jobs "$jobs" ||
    gw_die "stale shim compilation failed"

# Optional Slippi native sources and their ENet dependency. The derived response
# file includes only sources present in this checkout, so switching a lane back
# to an older branch cannot silently link a stale experimental object.
. "$GW_ROOT/tools/port/slippi_build.sh"

# A running game holds melee-pc.exe open and the link fails with LNK1104. Say so plainly rather
# than letting the linker's message stand on its own - and only ever complain about THIS build's
# exe, never kill someone else's run.
if [ -f "$GW_EXE" ] && ! ( : >>"$GW_EXE" ) 2>/dev/null; then
    gw_die "$GW_EXE is locked - a run of this build is still going. Close it, or use
       tools/port/run.sh, which runs a copy so a run can never block a link."
fi

bridge_c="$GW_MELEE/pc/platform/gw_mex_bridge.c"
bridge_h="$GW_MELEE/pc/platform/gw_mex_bridge.h"
bridge_obj="$GW_SHIMOBJ/gw_mex_bridge.obj"
bridge_stamp="$GW_BUILD_ROOT/.gw_mex_bridge_linked.sha256"
bridge_trusted=0
linked_bridge_source=""
linked_bridge_header=""
if [ -f "$bridge_h" ]; then linked_bridge_header="$(sha256sum <"$bridge_h")"; fi
# The stamp records the source, header and object of a previously audited final link.
# A pre-existing lane without a stamp takes one conservative bridge rebuild/link.
if [ "$bridge" = "1" ] && [ -f "$bridge_c" ] && [ -f "$bridge_h" ] &&
   [ -f "$bridge_obj" ] && [ -f "$bridge_stamp" ]; then
    bridge_proof="$(sha256sum "$bridge_c" "$bridge_h" "$bridge_obj")"
    if [ "$bridge_proof" = "$(cat "$bridge_stamp")" ]; then
        bridge_trusted=1
        linked_bridge_source="$(sha256sum "$bridge_c" "$bridge_h")"
    fi
fi

echo "link  1"
gw_link

if [ "$bridge" = "0" ]; then
    echo "bridge skipped (--no-bridge)"
    exit 0
fi

# symbols.txt and splits.txt come from THIS build's melee worktree, not from $GW_ROOT/melee.
# An agent builds its own checkout's objects, so taking the decomp metadata from the default
# checkout would describe a different tree - and splits.txt is now load-bearing, since it is what
# tells two same-named statics apart.
bridge_stable=0
max_bridge_passes=4
for ((pass=1; pass<=max_bridge_passes; pass++)); do
    echo "bridge check $pass/$max_bridge_passes"
    python "$GW_ROOT/tools/mex_port/gen_bridge.py" --map "$GW_MAP" \
        --symbols "$GW_MELEE/config/GALE01/symbols.txt" \
        --splits "$GW_MELEE/config/GALE01/splits.txt" \
        --out-c "$bridge_c" --out-h "$bridge_h" | tail -1
    generated_bridge_header="$(sha256sum <"$bridge_h")"
    if [ "$generated_bridge_header" != "$linked_bridge_header" ]; then
        # The first link used shims compiled against the previous generated header.
        # Apply the same conservative platform-header rule before linking again.
        echo "bridge header changed; rebuilding native shims"
        rebuilt_shims=()
        for src in "$GW_MELEE"/pc/platform/*.c "$GW_MELEE"/pc/platform/*.cpp; do
            [ -e "$src" ] || continue
            name="$(basename "$src")"
            case "$name" in *_linux.c|*_linux.cpp) continue ;; esac
            if [ "$name" != "gw_mex_bridge.c" ]; then
                rebuilt_shims+=(--shim "$name")
            fi
        done
        if [ ${#rebuilt_shims[@]} -gt 0 ]; then
            python "$GW_ROOT/tools/port/build_objects.py" shim --jobs "$jobs" "${rebuilt_shims[@]}" ||
                gw_die "bridge-dependent shim compilation failed"
        fi
        linked_bridge_header="$generated_bridge_header"
    fi
    generated_bridge_source="$(sha256sum "$bridge_c" "$bridge_h")"
    if [ "$bridge_trusted" = "1" ] && [ "$generated_bridge_source" = "$linked_bridge_source" ]; then
        bridge_stable=1
        break
    fi
    [ "$pass" -lt "$max_bridge_passes" ] ||
        gw_die "bridge did not reach a fixpoint after $max_bridge_passes regeneration checks; do not run this EXE"
    echo "bridge changed or linked object unverified; rebuilding"
    gw_build_shim gw_mex_bridge.c
    python "$GW_ROOT/tools/port/build_objects.py" record-shims --shim gw_mex_bridge.c ||
        gw_die "could not record bridge object inputs"
    echo "link  $((pass + 1)) (bridge)"
    gw_link
    linked_bridge_source="$generated_bridge_source"
    bridge_trusted=1
done
[ "$bridge_stable" = "1" ] || gw_die "bridge fixpoint check ended unexpectedly; do not run this EXE"

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
# The exe must carry the source identity netplay compares (gw_netplay.c np_build_id): an object compiled before
# the header existed does not depend on it and would silently fall back to the whole-file hash.
python "$GW_ROOT/tools/port/check_build_id.py" --melee "$GW_MELEE" --exe "$GW_EXE" ||
    gw_die "this exe does not carry the current build id; run: build.sh --shim gw_netplay.c"
sha256sum "$bridge_c" "$bridge_h" "$bridge_obj" >"$bridge_stamp.tmp"
mv -f "$bridge_stamp.tmp" "$bridge_stamp"
python "$GW_ROOT/tools/port/build_provenance.py" --melee "$GW_MELEE" \
    --build "$GW_BUILD_ROOT" --expect-source "$source_token" ||
    gw_die "could not bind this build to its source inputs"
echo "OK    $GW_EXE"
