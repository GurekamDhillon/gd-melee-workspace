#!/usr/bin/env bash
# Save a neutral grab state and verify all four throws in one native LAB process.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../../.."
. ./.env
: "${GW_ISO_ACE:?Set GW_ISO_ACE in .env}"
mods="${1:-_build/tmp/ultimate-kirby-throw-root-locked/mods}"
test -f "$mods/ultimate-kirby-additive-slot/slot-build.json"
export GW_MELEE="$(cd worktrees/kirby_native && pwd -W)"
export GW_BUILD_ROOT="$(pwd -W)/_build/agents/kirby_native"
export MELEE_MODS_DIR="$(cd "$mods" && pwd -W)"
export MELEE_SCENE='mode=lab;p1=ultimatekirby;p2=fox/hu;stage=fd'
export MELEE_PAD_SCRIPT="$(pwd -W)/ports/kirby-ultimate/probe/throw_matrix_live.lua"
export MELEE_INPUT=none MELEE_VOLUME=0 GW_RUNS_KEEP=100000
tools/port/run.sh ultimate-kirby-throw-matrix --iso "$GW_ISO_ACE"
