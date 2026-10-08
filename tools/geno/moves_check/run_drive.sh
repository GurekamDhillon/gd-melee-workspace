#!/bin/bash
# usage: run_drive.sh <run-name> <win|lose> <timeout-s> "<MELEE_SCENE>"
# Headless whole-mode run with a Geno fighter (see drive.lua). Needs GW_MELEE, GW_BUILD_ROOT, MELEE_MODS_DIR as for
# run_moves_check.sh. The log is $GW_BUILD_ROOT/runs/<run-name>/melee-pc.log; grep it for DRIVE, assert, PANIC, interpreter.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -W)"
GW_ROOT="${GW_ROOT:-E:/Projects/Melee Workspace}"
cd "$GW_ROOT"
set -a; . ./.env; set +a
LUA="$GW_BUILD_ROOT/drive-$1.lua"
{ echo "local MODE = '$2'"; echo "TRACE = true"; cat "$HERE/drive.lua"; } > "$LUA"
export MELEE_WINDOW_X=30000 MELEE_WINDOW_Y=30000 MELEE_WINDOW_W=640 MELEE_WINDOW_H=360
export MELEE_VOLUME=0 MELEE_PAD_IGNORE_ADAPTER=1 MELEE_TURBO=1 MELEE_FPS=u MELEE_TURBO_RENDER=0 MELEE_SCRIPT_MS=500
export MELEE_PAD_SCRIPT="$(cd "$GW_BUILD_ROOT" && pwd -W)/drive-$1.lua"
export MELEE_SCENE="$4"
exec timeout "$3" bash tools/port/run.sh --max-seconds "$3" "$1" --iso "$GW_ISO_VANILLA"
