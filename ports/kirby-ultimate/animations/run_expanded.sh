#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../../.."
. ./.env
: "${GW_ISO_ACE:?ACE ISO required}"
export GW_MELEE="$(pwd -W)/worktrees/kirby_native"
export GW_BUILD_ROOT="$(pwd -W)/_build/agents/kirby_native"
export MELEE_MODS_DIR="$(pwd -W)/_build/tmp/ultimate-kirby-anim-complete-lab/mods"
export MELEE_SCENE='mode=lab;p1=ultimatekirby;p2=fox/hu;stage=fd'
export MELEE_INPUT=none
case "${1:-expanded}" in
  expanded) probe=probe_expanded.lua; run=ultimate-kirby-animation-complete ;;
  phase) probe=probe_phase.lua; run=ultimate-kirby-animation-complete-phase ;;
  joints) probe=probe_joints.lua; run=ultimate-kirby-animation-complete-joints ;;
  *) echo "usage: $0 [expanded|phase|joints]" >&2; exit 2 ;;
esac
export MELEE_PAD_SCRIPT="$(pwd -W)/ports/kirby-ultimate/animations/$probe"
export MELEE_VOLUME=0
export GW_RUNS_KEEP=100000
tools/port/run.sh "$run" --iso "$GW_ISO_ACE"
