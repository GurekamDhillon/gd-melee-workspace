#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../../.."
. ./.env
: "${GW_ISO_ACE:?ACE ISO required}"
export GW_MELEE="$(pwd -W)/worktrees/kirby_entry"
export GW_BUILD_ROOT="$(pwd -W)/_build/agents/kirby_entry"
export MELEE_MODS_DIR="$(pwd -W)/_build/tmp/ultimate-kirby-entry-native-candidate/mods"
export MELEE_SCENE='mode=lab;p1=ultimatekirby;p2=fox/hu;stage=fd'
export MELEE_INPUT=none
export MELEE_PAD_SCRIPT="$(pwd -W)/ports/kirby-ultimate/animations/probe_entry_native.lua"
export MELEE_VOLUME=0
export GW_RUNS_KEEP=100000
tools/port/run.sh ultimate-kirby-entry-native --iso "$GW_ISO_ACE"
