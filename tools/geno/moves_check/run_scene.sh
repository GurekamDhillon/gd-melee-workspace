#!/bin/bash
# usage: run_scene.sh <run-name> <scene> <lua-script> [timeout-s]
# Runs a pad script headless (turbo, offscreen, muted) in the given scene on the vanilla disc. Like run_moves_check.sh, but the scene
# and the script are arguments, so a fighter that is not a `geno:` define (the old Sora, an m-ex slot) can be run with the same scenarios.
# Needs GW_MELEE / GW_BUILD_ROOT / MELEE_MODS_DIR exported (the lane's game worktree, build root and mods parent).
set -u
GW_ROOT="${GW_ROOT:-E:/Projects/Melee Workspace}"
cd "$GW_ROOT"
set -a; . ./.env; set +a
export MELEE_WINDOW_X=30000 MELEE_WINDOW_Y=30000 MELEE_WINDOW_W=640 MELEE_WINDOW_H=360
export MELEE_VOLUME=0 MELEE_PAD_IGNORE_ADAPTER=1 MELEE_TURBO=1 MELEE_FPS=u MELEE_TURBO_RENDER=0 MELEE_SCRIPT_MS=500
export MELEE_PAD_SCRIPT="$3"
export MELEE_SCENE="$2"
exec timeout "${4:-600}" bash tools/port/run.sh --max-seconds "${4:-600}" "$1" --iso "$GW_ISO_VANILLA"
