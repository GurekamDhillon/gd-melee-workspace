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
slippi-pad)
    sources=(pc/tests/slippi_pad_test.c pc/platform/gw_slippi_pad.c) ;;
slippi-fixture)
    sources=(pc/tests/slippi_fixture_test.c pc/platform/gw_slippi_pad.c) ;;
slippi-rb)
    sources=(pc/tests/slippi_rb_test.c pc/platform/gw_slippi_pad.c) ;;
slippi-mode)
    sources=(pc/tests/slippi_mode_test.c) ;;
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
*) gw_die "unknown native test: $test_name (slippi-pad, slippi-fixture, slippi-rb, slippi-mode, slippi-wire, slippi-peer, slippi-match, window-drag)" ;;
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
test_exe="$test_root/$test_name.exe"
test_tmp="$test_root/$test_name.next.exe"
echo "native test  $test_name"
"$GW_CLANG" --target=i686-pc-windows-msvc "${flags[@]}" "${absolute_sources[@]}" \
    -o "$test_tmp" -Xlinker /OPT:REF "${libs[@]}"
# Replace only after successful compilation; a stale executable is never run.
mv -f "$test_tmp" "$test_exe"
"$test_exe"
