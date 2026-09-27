#!/usr/bin/env bash
# Visible native LAB showcase; stays open for the user to inspect and play.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../../.."
. ./.env
: "${GW_ISO_ACE:?Set GW_ISO_ACE in .env}"
mods="${1:-_build/tmp/ultimate-kirby-hammer-native-visual-lab/mods}"
test -f "$mods/ultimate-kirby-additive-slot/slot-build.json"
export GW_MELEE="$(cd worktrees/kirby_native && pwd -W)"
export GW_BUILD_ROOT="$(pwd -W)/_build/agents/kirby_native"
export MELEE_MODS_DIR="$(cd "$mods" && pwd -W)"
export MELEE_SCENE='mode=lab;p1=ultimatekirby;p2=fox/cpu0;stage=fd'
export MELEE_PAD_SCRIPT="$(pwd -W)/ports/kirby-ultimate/probe/side_b_showcase.lua"
export MELEE_VOLUME=3 GW_RUNS_KEEP=100000
unset MELEE_INPUT
tools/port/run.sh ultimate-kirby-side-b-showcase --iso "$GW_ISO_ACE"
