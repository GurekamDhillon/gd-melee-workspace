#!/usr/bin/env bash
# Shield, damage, roll, and save/load checks in one additive-slot LAB match.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../../.."
. ./.env
: "${GW_ISO_ACE:?Set GW_ISO_ACE in .env}"
mods="${1:-_build/tmp/ultimate-kirby-hammer-exact/mods}"
test -f "$mods/ultimate-kirby-additive-slot/slot-build.json"
export GW_MELEE="$(cd worktrees/kirby_native && pwd -W)"
export GW_BUILD_ROOT="$(pwd -W)/_build/agents/kirby_native"
export MELEE_MODS_DIR="$(cd "$mods" && pwd -W)"
export MELEE_SCENE='mode=lab;p1=ultimatekirby;p2=fox/hu;stage=fd'
export MELEE_PAD_SCRIPT="$(pwd -W)/ports/kirby-ultimate/probe/native_regression.lua"
export MELEE_INPUT=none MELEE_VOLUME=0 GW_RUNS_KEEP=100000
tools/port/run.sh ultimate-kirby-native-regression --iso "$GW_ISO_ACE"
