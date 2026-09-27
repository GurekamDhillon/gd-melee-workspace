#!/usr/bin/env bash
# Run native-slot swallow/copy routes in isolated LAB run directories.
# Default set covers projectile, charge, and spawned-item copy families.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../../.."
. ./.env
: "${GW_ISO_ACE:?Set GW_ISO_ACE in .env}"
test -f "$GW_ISO_ACE"
mods=_build/tmp/ultimate-kirby-rapid-corrected-native-lab/mods-v2
test -f "$mods/ultimate-kirby-slot/slot-build.json"
export GW_MELEE="$(cd worktrees/kirby_copy && pwd -W)"
export GW_BUILD_ROOT="$(pwd -W)/_build/agents/kirby_copy"
export MELEE_MODS_DIR="$(cd "$mods" && pwd -W)"
export MELEE_PAD_SCRIPT="$(pwd -W)/ports/kirby-ultimate/probe/copy_matrix.lua"
export MELEE_INPUT=none MELEE_VOLUME=0 GW_RUNS_KEEP=100000

if (( $# == 0 )); then set -- samus link donkey gamewatch; fi
if (( $# == 1 )) && [ "$1" = --all ]; then
    set -- 0 1 2 3 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25
fi
fighters=("$@")
failures=0
for fighter in "${fighters[@]}"; do
    scene_fighter="$fighter"
    if [ "$scene_fighter" = donkey ]; then scene_fighter=dk; fi
    if [[ "$scene_fighter" =~ ^[0-9]+$ ]]; then scene_fighter="ck:$scene_fighter"; fi
    export MELEE_SCENE="mode=lab;p1=ultimatekirby;p2=$scene_fighter/hu;stage=fd"
    name="ultimate-kirby-copy-$fighter"
    if ! tools/port/run.sh "$name" --iso "$GW_ISO_ACE"; then
        echo "game run failed: $fighter ($GW_BUILD_ROOT/runs/$name/melee-pc.log)" >&2
        failures=$((failures + 1))
        continue
    fi
    if ! grep -q 'ultimate-kirby copy-matrix RESULT PASS' "$GW_BUILD_ROOT/runs/$name/melee-pc.log"; then
        echo "copy route failed: $fighter ($GW_BUILD_ROOT/runs/$name/melee-pc.log)" >&2
        failures=$((failures + 1))
    fi
done
echo "copy matrix: $((${#fighters[@]} - failures))/${#fighters[@]} passed"
test "$failures" -eq 0
