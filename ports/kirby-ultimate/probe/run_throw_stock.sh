#!/usr/bin/env bash
# Compare unmodified Melee Kirby's live throw physics with the native port.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../../.."
. ./.env
: "${GW_ISO_ACE:?Set GW_ISO_ACE in .env}"
export GW_MELEE="$(cd worktrees/kirby_native && pwd -W)"
export GW_BUILD_ROOT="$(pwd -W)/_build/agents/kirby_native"
empty=_build/tmp/ultimate-kirby-throw-stock/mods
mkdir -p "$empty"
export MELEE_MODS_DIR="$(cd "$empty" && pwd -W)"
export MELEE_SCENE='mode=lab;p1=kirby;p2=fox/hu;stage=fd'
export MELEE_PAD_SCRIPT="$(pwd -W)/ports/kirby-ultimate/probe/throw_live.lua"
export MELEE_INPUT=none MELEE_VOLUME=0 GW_RUNS_KEEP=100000
tools/port/run.sh ultimate-kirby-throw-stock --iso "$GW_ISO_ACE"
