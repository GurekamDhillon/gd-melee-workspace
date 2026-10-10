#!/bin/bash
# usage: run_ledge2.sh <name> <modsdir> <p1token>   (ACE disc)
cd "E:/Projects/Melee Workspace"
set -a; source .env; set +a
export GW_BUILD_ROOT="E:/Projects/Melee Workspace/_build/agents/goku-polish" GW_MELEE="E:/Projects/Melee Workspace/worktrees/goku-polish"
export MELEE_MODS_DIR="E:/Projects/Melee Workspace/_build/timing-audit/$2"
export MELEE_SCENE="mode=lab;p1=$3/hu;p2=falcon/hu;stage=fd;items=off;time=0"
export MELEE_UNATTENDED=1 MELEE_MAX_SECONDS=150 MELEE_LAB_UI=0 MELEE_TURBO=1
export MELEE_WINDOW_X=40 MELEE_WINDOW_Y=40 MELEE_WINDOW_W=1280 MELEE_WINDOW_H=720 MELEE_RUN_LABEL=ledge-probe
bash tools/port/run.sh --max-seconds 150 "$1" --iso "$GW_ISO_ACE" > "_build/timing-audit/$1.run.txt" 2>&1
grep -a "LEDGE RESULT\|LEDGE FAIL\|scene:\|error" "$GW_BUILD_ROOT/runs/$1/melee-pc.log" | head -40
