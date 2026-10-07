#!/bin/bash
# usage: run_win.sh <name> <frames> <seed> "<scene>" [extra VAR=val ...]
# One scripted offline match on the Windows build of this lane; writes <runs>/<name>/xh.csv (+ dumps).
# Needs GW_MELEE and GW_BUILD_ROOT exported (the lane's), like tools/port/run.sh.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -W)"
name="$1"; frames="$2"; seed="$3"; scene="$4"; shift 4
set -a; . "$GW_ROOT_ENV/.env"; set +a
sandbox="$GW_BUILD_ROOT/runs/$name"
mkdir -p "$sandbox"
for kv in "$@"; do export "$kv"; done
{ echo "DET = {frames=$frames, seed=$seed, bias=${DET_BIAS:-55}, ports=${DET_PORTS:-2}}"; cat "$here/det_input.lua"; } > "$sandbox/det.lua"
export MELEE_SCENE="$scene" MELEE_PAD_SCRIPT="$(cd "$sandbox" && pwd -W)/det.lua"
export MELEE_TURBO="${MELEE_TURBO:-1}" MELEE_TURBO_RENDER="${MELEE_TURBO_RENDER:-120}" MELEE_VOLUME=0 MELEE_TEST_SEED="${MELEE_TEST_SEED:-777}"
export MELEE_MAX_SECONDS="${MELEE_MAX_SECONDS:-1200}" MELEE_PAD_IGNORE_ADAPTER=1 MELEE_SKIP_INTRO=1 MELEE_XHASH_LOG="$(cd "$GW_BUILD_ROOT" && pwd -W)/runs/$name/xh.csv"
export MELEE_MODS_DIR="${MELEE_MODS_DIR:-$(cd "$GW_ROOT_ENV/_build" && mkdir -p nomods && cd nomods && pwd -W)}"
mkdir -p "$sandbox"; rm -f "$sandbox/xh.csv"
case "${XP_DISC:-vanilla}" in
  ace) iso="$GW_ISO_ACE" ;; akaneia) iso="$GW_ISO_AKANEIA" ;; *) iso="$GW_ISO_VANILLA" ;;
esac
exec bash "$GW_ROOT_ENV/tools/port/run.sh" "$name" --iso "$iso"
