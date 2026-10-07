#!/bin/bash
# usage (INSIDE the Ubuntu rootfs, via ~/lb2/enter.sh): run_linux.sh <build dir> <name> <frames> <seed> "<scene>" [VAR=val ...]
# One scripted offline match on the Linux build in <build dir> (contains melee, melee-pc.msvc.map, assets, ui);
# the run dir is <build dir>/../xp-<name>, with xh.csv (+ dumps) in it. Headless: SDL dummy video and audio.
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bin="$1"; name="$2"; frames="$3"; seed="$4"; scene="$5"; shift 5
case "${XP_DISC:-vanilla}" in
  ace) disc="${MELEE_ACE_ISO:?set MELEE_ACE_ISO}" ;; akaneia) disc="${MELEE_AKANEIA_ISO:?set MELEE_AKANEIA_ISO}" ;; *) disc="${MELEE_VANILLA_ISO:?set MELEE_VANILLA_ISO}" ;;
esac
run="$(dirname "$bin")/xp-$name"
rm -rf "$run"; mkdir -p "$run"
cp "$bin/melee" "$bin/melee-pc.msvc.map" "$run/"; cp -a "$bin/assets" "$bin/ui" "$run/"
for kv in "$@"; do export "$kv"; done
{ echo "DET = {frames=$frames, seed=$seed, bias=${DET_BIAS:-55}, ports=${DET_PORTS:-2}}"; cat "$here/det_input.lua"; } > "$run/det.lua"
mkdir -p "$run/nomods"
export MELEE_SCENE="$scene" MELEE_PAD_SCRIPT="$run/det.lua" MELEE_XHASH_LOG="$run/xh.csv"
export MELEE_TURBO="${MELEE_TURBO:-1}" MELEE_TURBO_RENDER="${MELEE_TURBO_RENDER:-0}" MELEE_VOLUME=0 MELEE_TEST_SEED="${MELEE_TEST_SEED:-777}"
export MELEE_PAD_IGNORE_ADAPTER=1 MELEE_SKIP_INTRO=1 MELEE_MODS_DIR="${MELEE_MODS_DIR:-$run/nomods}" MELEE_CACHE_DIR="$run"
# the same presentation settings run.sh gives the Windows build (the camera depends on the aspect)
export MELEE_WINDOW_W="${MELEE_WINDOW_W:-1920}" MELEE_WINDOW_H="${MELEE_WINDOW_H:-1080}" MELEE_RENDER_SCALE="${MELEE_RENDER_SCALE:-3}" MELEE_WIDESCREEN="${MELEE_WIDESCREEN:-1}"
export SDL_VIDEODRIVER="${SDL_VIDEODRIVER:-dummy}" SDL_AUDIODRIVER=dummy LD_LIBRARY_PATH="${GW_LIBDIR:-}"
cd "$run"
timeout --kill-after=5 "${XP_TIMEOUT:-1500}" ./melee --iso "$disc" > run.log 2>&1
rc=$?
sed -i "s|$disc|<disc>|g" run.log melee-pc.log 2>/dev/null
echo "== $name exit=$rc"
grep -a -E "DET:|FATAL|fatal|SIGSEGV|assert|xhash" run.log melee-pc.log 2>/dev/null | head -12 | cut -c1-200
wc -l "$run/xh.csv" 2>/dev/null
