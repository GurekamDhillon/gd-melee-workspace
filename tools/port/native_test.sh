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
script-budget)
    sources=(pc/tests/script_budget_test.c) ;;
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
atlas-parts)
    sources=(pc/tests/atlas_parts_test.c pc/platform/gw_ui_parts.c pc/platform/gw_ui_layout.c) ;;
atlas-render)
    sources=(pc/tests/atlas_render_test.c pc/platform/gw_ui_render.c pc/platform/gw_ui_room.c pc/platform/gw_ui_online_parts.c pc/platform/gw_ui_parts.c pc/platform/gw_ui_layout.c pc/platform/gw_ui_screen.c pc/platform/gw_ui_val.c pc/platform/gw_ui_focus.c pc/platform/gw_ui_input.c pc/platform/gw_ui_stack.c) ;;
atlas-tiles)
    sources=(pc/tests/atlas_tiles_test.c pc/platform/gw_ui_render.c pc/platform/gw_ui_room.c pc/platform/gw_ui_online_parts.c pc/platform/gw_ui_parts.c pc/platform/gw_ui_layout.c pc/platform/gw_ui_screen.c pc/platform/gw_ui_val.c pc/platform/gw_ui_focus.c pc/platform/gw_ui_input.c pc/platform/gw_ui_stack.c) ;;
atlas-registry)
    sources=(pc/tests/atlas_registry_test.c pc/platform/gw_ui_registry.c pc/platform/gw_ui_menus_json.c) ;;
atlas-policy)
    sources=(pc/tests/atlas_policy_test.c pc/platform/gw_ui_policy.c) ;;
atlas-retail)
    sources=(pc/tests/atlas_retail_test.c pc/platform/gw_ui_retail.c) ;;
atlas-hud)
    sources=(pc/tests/atlas_hud_test.c pc/platform/gw_ui_hud.c pc/platform/gw_ui_parts.c pc/platform/gw_ui_layout.c pc/platform/gw_ui_stack.c pc/platform/gw_ui_val.c) ;;
atlas-binding|atlas-select-adapter|atlas-settings-host|atlas-settings|atlas-room-host)
    sources=(pc/tests/atlas_binding_test.c pc/platform/gw_ui_css.c pc/platform/gw_ui_css_profile.c pc/platform/gw_ui_sss.c pc/platform/gw_ui_render.c pc/platform/gw_ui_room.c pc/platform/gw_ui_online_parts.c pc/platform/gw_ui_parts.c pc/platform/gw_ui_layout.c pc/platform/gw_ui_screen.c pc/platform/gw_ui_val.c pc/platform/gw_ui_focus.c pc/platform/gw_ui_input.c pc/platform/gw_ui_stack.c pc/platform/gw_ui_registry.c pc/platform/gw_ui_menus_json.c pc/platform/gw_ui_policy.c pc/platform/gw_ui_retail.c pc/platform/gw_ui_hud.c pc/platform/gw_ui_item.c)
    for lua_file in lapi lauxlib lbaselib lcode lcorolib lctype ldblib ldebug ldo ldump lfunc lgc linit liolib llex lmathlib lmem loadlib lobject lopcodes loslib lparser lstate lstring lstrlib ltable ltablib ltm lundump lutf8lib lvm lzio; do
        sources+=("pc/third_party/lua-5.4.7/src/$lua_file.c")
    done
    # the select screens' host half is tested through the same stand-ins and the same real units (gw_script_ui_sel.inc is included by gw_script_ui.inc)
    [ "$test_name" = atlas-select-adapter ] && sources[0]=pc/tests/atlas_select_adapter_test.c
    [ "$test_name" = atlas-settings-host ] && sources[0]=pc/tests/atlas_settings_host_test.c
    [ "$test_name" = atlas-settings ] && sources[0]=pc/tests/atlas_settings_test.c
    [ "$test_name" = atlas-room-host ] && sources[0]=pc/tests/atlas_room_host_test.c
    flags=(-std=gnu11 -w -ffunction-sections -I "$GW_MELEE/pc/platform" -I "$GW_MELEE/pc/third_party/lua-5.4.7/src") ;;
atlas-style)
    sources=(pc/tests/atlas_style_test.c pc/platform/gw_ui_parts.c pc/platform/gw_ui_layout.c) ;;
atlas-profile)
    sources=(pc/tests/atlas_profile_test.c pc/platform/gw_ui_css_profile.c) ;;
atlas-css)
    sources=(pc/tests/atlas_css_test.c pc/platform/gw_ui_css.c pc/platform/gw_ui_css_profile.c) ;;
atlas-select-render)
    sources=(pc/tests/atlas_select_render_test.c pc/platform/gw_ui_render.c pc/platform/gw_ui_room.c pc/platform/gw_ui_online_parts.c pc/platform/gw_ui_parts.c pc/platform/gw_ui_layout.c pc/platform/gw_ui_screen.c pc/platform/gw_ui_val.c pc/platform/gw_ui_focus.c pc/platform/gw_ui_input.c pc/platform/gw_ui_stack.c) ;;
atlas-sss)
    sources=(pc/tests/atlas_sss_test.c pc/platform/gw_ui_sss.c pc/platform/gw_ui_css.c pc/platform/gw_ui_css_profile.c) ;;
atlas-walker)
    sources=(pc/tests/atlas_walker_test.c pc/platform/gw_ui_item.c) ;;
atlas-erase)
    sources=(pc/tests/atlas_erase_test.c) ;;
atlas-remap)
    sources=(pc/tests/atlas_remap_test.c) ;;
atlas-items)
    sources=(pc/tests/atlas_items_test.c pc/platform/gw_ui_item.c pc/platform/gw_ui_screen.c pc/platform/gw_ui_val.c pc/platform/gw_ui_focus.c pc/platform/gw_ui_layout.c) ;;
atlas-lint)
    sources=(pc/tests/atlas_lint_test.c pc/platform/gw_ui_parts.c pc/platform/gw_ui_layout.c) ;;
atlas-online-parts)
    sources=(pc/tests/atlas_online_parts_test.c pc/platform/gw_ui_online_parts.c pc/platform/gw_ui_parts.c pc/platform/gw_ui_layout.c) ;;
atlas-room)
    sources=(pc/tests/atlas_room_test.c pc/platform/gw_ui_room.c pc/platform/gw_ui_online_parts.c pc/platform/gw_ui_render.c pc/platform/gw_ui_parts.c pc/platform/gw_ui_layout.c pc/platform/gw_ui_screen.c pc/platform/gw_ui_val.c pc/platform/gw_ui_focus.c pc/platform/gw_ui_input.c pc/platform/gw_ui_stack.c) ;;
*) gw_die "unknown native test: $test_name (slippi-pad, slippi-fixture, slippi-rb, slippi-mode, slippi-wire, slippi-peer, slippi-match, window-drag, script-policy, script-budget, arena-spawn, view-canvas, profiler-core, pipeline-warm, atlas-tokens, atlas-layout, atlas-focus, atlas-input, atlas-screen, atlas-stack, atlas-parts, atlas-render, atlas-tiles, atlas-registry, atlas-policy, atlas-retail, atlas-hud, atlas-binding, atlas-style, atlas-profile, atlas-css, atlas-select-render, atlas-sss, atlas-select-adapter, atlas-items, atlas-walker, atlas-settings-host, atlas-settings, atlas-erase, atlas-remap, atlas-lint, atlas-online-parts, atlas-room, atlas-room-host)" ;;
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
elif [[ "$test_name" == atlas-* ]]; then
    # the atlas tests read files by game-repo-relative path (the Envoy manifest)
    ( cd "$GW_MELEE" && "$test_exe" )
else
    "$test_exe"
fi
