#!/bin/bash
# usage: run_shots.sh <run> <p1 token>   (visible, realtime)
set -u
export GW_ROOT="E:/Projects/Melee Workspace" GW_MELEE="E:/Projects/Melee Workspace/worktrees/falcon-geno" GW_BUILD_ROOT="E:/Projects/Melee Workspace/_build/agents/falcon-geno"
cd "$GW_ROOT"; set -a; . ./.env; set +a
export MELEE_MODS_DIR="$GW_BUILD_ROOT/mods" MELEE_WINDOW_X=700 MELEE_WINDOW_Y=40 MELEE_WINDOW_W=960 MELEE_WINDOW_H=540 MELEE_VOLUME=0 MELEE_PAD_IGNORE_ADAPTER=1
export MELEE_TURBO=1 MELEE_TURBO_RENDER=1 MELEE_FPS=u MELEE_TURBO_DRAWS=1
export MELEE_PAD_SCRIPT="$GW_BUILD_ROOT/shots.lua" MELEE_SCENE="mode=vs;p1=$2/hu/c${C:-0};p2=captain/hu/c0;stage=fd;items=off;time=0"
timeout 150 bash worktrees/ws-falcon-geno/tools/port/run.sh --max-seconds 120 "$1" --iso "$GW_ISO_VANILLA" > /dev/null 2>&1
grep -a "SHOT" "$GW_BUILD_ROOT/runs/$1/melee-pc.log" | sed 's/.*SHOT/SHOT/'
