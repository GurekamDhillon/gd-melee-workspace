#!/usr/bin/env bash
# Run the ignored, separately staged dedicated-slot visual mod in LAB.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../../.."
. ./.env
: "${GW_ISO_ACE:?ACE ISO required}"
export GW_MELEE="$(pwd -W)/worktrees/kirby_native"
export GW_BUILD_ROOT="$(pwd -W)/_build/agents/kirby_native"
export MELEE_MODS_DIR="$(pwd -W)/_build/tmp/ultimate-kirby-anim-phase-lab/mods"
export MELEE_SCENE='mode=lab;p1=ultimatekirby;p2=fox/hu;stage=fd'
export MELEE_INPUT=none
export MELEE_PAD_SCRIPT="$(pwd -W)/ports/kirby-ultimate/animations/probe_phase.lua"
export MELEE_VOLUME=0
export GW_RUNS_KEEP=100000
tools/port/run.sh ultimate-kirby-animation-phase --iso "$GW_ISO_ACE"
