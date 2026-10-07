#!/bin/bash
# usage (INSIDE the Ubuntu rootfs, via ~/lb2/enterD.sh): run_linux_net.sh <build dir> <name> <seconds> [VAR=val ...]
# One REAL-TIME netplay client on the Linux build in <build dir> (melee, melee-pc.msvc.map, assets, ui). The
# run dir is <build dir>/../xpn-<name>; the game's own hash log is hashes.csv there. Stops itself after <seconds>.
set -uo pipefail
bin="$1"; name="$2"; secs="$3"; shift 3
case "${XP_DISC:-vanilla}" in
  ace) disc="${MELEE_ACE_ISO:?}" ;; akaneia) disc="${MELEE_AKANEIA_ISO:?}" ;; *) disc="${MELEE_VANILLA_ISO:?}" ;;
esac
run="$(dirname "$bin")/xpn-$name"
rm -rf "$run"; mkdir -p "$run/nomods"
cp "$bin/melee" "$bin/melee-pc.msvc.map" "$run/"; cp -a "$bin/assets" "$bin/ui" "$run/"
export MELEE_VOLUME=0 MELEE_PAD_IGNORE_ADAPTER=1 MELEE_SKIP_INTRO=1 MELEE_MODS_DIR="${MELEE_MODS_DIR:-$run/nomods}" MELEE_CACHE_DIR="$run"
export MELEE_RB_HASHLOG="$run/hashes.csv" MELEE_RB_LOG=0
export MELEE_WINDOW_W="${MELEE_WINDOW_W:-960}" MELEE_WINDOW_H="${MELEE_WINDOW_H:-540}"
export SDL_VIDEODRIVER="${SDL_VIDEODRIVER:-x11}" SDL_AUDIODRIVER=dummy LD_LIBRARY_PATH="${GW_LIBDIR:-}"
for kv in "$@"; do export "$kv"; done
cd "$run"
timeout --kill-after=5 "$secs" ./melee --iso "$disc" > run.log 2>&1
rc=$?
sed -i "s|$disc|<disc>|g" run.log melee-pc.log 2>/dev/null
echo "== $name exit=$rc"
