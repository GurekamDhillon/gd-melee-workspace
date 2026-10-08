#!/bin/bash
# usage: run_moves_check.sh <run-name> <geno-key> [timeout-s]
# Runs moves_check.lua headless (turbo, offscreen window, muted) for one Geno fighter against Mario in the LAB, on the
# vanilla disc. Needs GW_MELEE / GW_BUILD_ROOT exported (the lane's game worktree and build root) and MELEE_MODS_DIR
# naming a parent that holds geno-lab, the fighter's folder and an enabled.txt listing them (use make_mods.sh).
# The run's log is $GW_BUILD_ROOT/runs/<run-name>/melee-pc.log; moves_report.py reads the MOVECHK lines from it.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -W)"
ROOT="$(cd "$HERE/../../.." && pwd -W)"
GW_ROOT="${GW_ROOT:-E:/Projects/Melee Workspace}"
cd "$GW_ROOT"
set -a; . ./.env; set +a
export MELEE_WINDOW_X=30000 MELEE_WINDOW_Y=30000 MELEE_WINDOW_W=640 MELEE_WINDOW_H=360
export MELEE_VOLUME=0 MELEE_PAD_IGNORE_ADAPTER=1 MELEE_TURBO=1 MELEE_FPS=u MELEE_TURBO_RENDER=0 MELEE_SCRIPT_MS=500
export MELEE_PAD_SCRIPT="${MOVECHK_LUA:-$HERE/moves_check.lua}"
export MELEE_SCENE="mode=lab;p1=geno:$2/hu;p2=mario/cpu0;stage=fd"
exec timeout "${3:-600}" bash tools/port/run.sh --max-seconds "${3:-600}" "$1" --iso "$GW_ISO_VANILLA"
