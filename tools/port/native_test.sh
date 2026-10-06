#!/bin/bash
# Invoked by build.sh --native-test NAME. Pure native protocol tests do not link
# the game or use its bridge; each output stays in the selected lane's build root.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
. ./portlib.sh

test_name="${1:-}"
sources=()
flags=(-std=c11 -ffunction-sections -I "$GW_MELEE/pc/platform")
libs=()
uses_enet=0
case "$test_name" in
roster-registry)
    sources=(pc/tests/roster_registry_test.c) ;;
slippi-pad)
    sources=(pc/tests/slippi_pad_test.c pc/platform/gw_slippi_pad.c) ;;
slippi-fixture)
    sources=(pc/tests/slippi_fixture_test.c pc/platform/gw_slippi_pad.c) ;;
slippi-rb)
    sources=(pc/tests/slippi_rb_test.c pc/platform/gw_slippi_pad.c) ;;
slippi-mode)
    sources=(pc/tests/slippi_mode_test.c) ;;
script-policy)
    sources=(pc/tests/script_policy_test.c) ;;
arena-spawn)
    sources=(pc/tests/arena_spawn_test.c) ;;
view-canvas)
    sources=(pc/tests/view_canvas_test.c) ;;
controls-remap)
    sources=(pc/tests/controls_remap_test.c pc/platform/gw_slippi_pad.c) ;;
profiler-core)
    sources=(pc/tests/profiler_core_test.c) ;;
pipeline-warm)
    sources=(pc/tests/pipeline_warm_test.cpp)
    flags=(-std=c++20 -ffunction-sections -I "$GW_MELEE/pc/platform") ;;
geno-items-registry)
    sources=(pc/tests/geno_items_registry_test.c) ;;
mex-items-query)
    sources=(pc/tests/mex_items_query_test.c) ;;
engine-data)
    sources=(pc/tests/engine_gaps_test.c) ;;
window-drag)
    sources=(pc/tests/window_drag_test.c) ;;
slippi-wire)
    sources=(pc/tests/slippi_wire_test.c pc/platform/gw_slippi_wire.c) ;;
slippi-peer)
    sources=(pc/tests/slippi_peer_test.c pc/platform/gw_slippi_peer.c pc/platform/gw_slippi_wire.c)
    uses_enet=1 ;;
slippi-match)
    sources=(pc/tests/slippi_match_test.c pc/platform/gw_slippi_match_json.c pc/platform/gw_slippi_match.c)
    uses_enet=1 ;;
atlas-tokens)
    sources=(pc/tests/atlas_tokens_test.c) ;;
atlas-layout)
    sources=(pc/tests/atlas_layout_test.c pc/platform/gw_ui_layout.c) ;;
atlas-focus)
    sources=(pc/tests/atlas_focus_test.c pc/platform/gw_ui_focus.c) ;;
atlas-input)
    sources=(pc/tests/atlas_input_test.c pc/platform/gw_ui_input.c pc/platform/gw_ui_focus.c) ;;
atlas-screen)
    sources=(pc/tests/atlas_screen_test.c pc/platform/gw_ui_screen.c pc/platform/gw_ui_val.c pc/platform/gw_ui_focus.c) ;;
atlas-stack)
    sources=(pc/tests/atlas_stack_test.c pc/platform/gw_ui_stack.c) ;;
*) gw_die "unknown native test: $test_name (slippi-pad, slippi-fixture, slippi-rb, slippi-mode, slippi-wire, slippi-peer, slippi-match, window-drag, script-policy, arena-spawn, view-canvas, profiler-core, pipeline-warm, atlas-tokens, atlas-layout, atlas-focus, atlas-input, atlas-screen, atlas-stack)" ;;
esac

if [ "$uses_enet" = 1 ]; then
    flags+=(-I "$GW_MELEE/extern/enet/include")
    for part in callbacks compress host list packet peer protocol win32; do
        sources+=("extern/enet/$part.c")
    done
    libs+=(-lws2_32 -lwinmm)
fi
absolute_sources=()
for source in "${sources[@]}"; do
    [ -f "$GW_MELEE/$source" ] || gw_die "native test source missing: $source"
    absolute_sources+=("$GW_MELEE/$source")
done

test_root="$GW_BUILD_ROOT/native-tests"
mkdir -p "$test_root"
if [ "$test_name" = geno-items-registry ]; then
    python "$GW_ROOT/tools/port/geno_items_fixture.py" "$test_root/geno_items_json_reader.inc"
    flags+=(-I "$test_root")
fi
if [ "$test_name" = script-policy ]; then
    python "$GW_ROOT/tools/port/script_policy_fixture.py" "$GW_MELEE/pc/platform/gw_script.c" \
        "$test_root/script_policy_functions.inc"
    flags+=(-I "$test_root")
fi
if [ "$test_name" = arena-spawn ]; then
    python "$GW_ROOT/tools/port/arena_spawn_fixture.py" "$GW_MELEE" "$test_root/arena_spawn_functions.inc"
    flags+=(-I "$test_root")
fi
test_exe="$test_root/$test_name.exe"
test_tmp="$test_root/$test_name.next.exe"
echo "native test  $test_name"
"$GW_CLANG" --target=i686-pc-windows-msvc "${flags[@]}" "${absolute_sources[@]}" \
    -o "$test_tmp" -Xlinker /OPT:REF "${libs[@]}"
# Replace only after successful compilation; a stale executable is never run.
mv -f "$test_tmp" "$test_exe"
if [ "$test_name" = profiler-core ]; then
    fixture_root="$test_root/profiler-core-output"
    mkdir -p "$fixture_root"
    (
        cd "$fixture_root"
        "$test_exe"
        python "$GW_MELEE/pc/tests/validate_profiler_fixture.py"
    )
elif [ "$test_name" = engine-data ]; then
    fixture_root="$(mktemp -d "$test_root/engine-data.XXXXXX")"
    "$test_exe" "$fixture_root"
else
    "$test_exe"
fi
