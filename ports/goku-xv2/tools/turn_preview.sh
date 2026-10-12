#!/usr/bin/env bash
# Goku's Turn / TurnRun / RunBrake: bake Goku's current rows and the cross-ported locomotion sets, then build the side-by-side Blender preview.
#   ports/goku-xv2/tools/turn_preview.sh [sets...]        default sets: falcon marth fox
# Needs .env (GW_ISO_VANILLA), GW_MELEE (the game checkout, for tools/geno), Blender. Output: _build/goku-xv2/turn-preview/ (disc-derived, git-ignored):
#   <set>/goku.blend ...   one reduced artist bake per set (GOKU_LOCO_SET=<set> GOKU_AUTHOR=turn-preview/<set>)
#   goku_turn_preview.blend, sheets/grid_NN.png, turn_preview_metrics.json
# The shipped build is untouched: cross-port clips for the three rows are solved into _build/goku-xv2/cross-port and removed again afterwards.
set -euo pipefail
cd "$(dirname "$0")/../../.."
ROOT=$PWD
if [ -f .env ]; then . ./.env
else COMMON=$(git rev-parse --git-common-dir); [ -f "$COMMON/../.env" ] && . "$COMMON/../.env"; fi   # a worktree has no .env of its own: the main checkout's
: "${GW_ISO_VANILLA:?source .env (GW_ISO_VANILLA)}"
[ -d "$ROOT/melee" ] && : "${GW_MELEE:=$ROOT/melee}"
: "${GW_MELEE:=$(git rev-parse --git-common-dir)/../melee}"   # a worktree has no game checkout of its own
export GW_MELEE
BLENDER="${BLENDER:-D:/SteamLibrary/steamapps/common/Blender/blender.exe}"
SETS=("$@"); [ ${#SETS[@]} -gt 0 ] || SETS=(falcon marth fox)
OUT=_build/goku-xv2/turn-preview
mkdir -p "$OUT"
bake() {   # $1 = set name or "current"
  local s=$1
  rm -rf _build/goku-xv2/cross-port/{Turn,TurnRun,RunBrake}
  if [ "$s" = current ]; then unset GOKU_LOCO_SET; else
    export GOKU_LOCO_SET=$s; python ports/goku-xv2/tools/cross_port.py --set "$s" > "$OUT/solve-$s.log"
  fi
  GOKU_AUTHOR=turn-preview/$s python ports/goku-xv2/tools/xv2_to_artist.py --no-library --blend > "$OUT/bake-$s.log" 2>&1
}
for s in current "${SETS[@]}"; do bake "$s"; done
rm -rf _build/goku-xv2/cross-port/{Turn,TurnRun,RunBrake}
GW_SITE="${GW_SITE:-$ROOT/_build/wbnla-site}" "$BLENDER" -b "$OUT/current/goku.blend" --python ports/goku-xv2/tools/turn_preview_blend.py -- \
  --project ports/goku-xv2 --sets "$(IFS=,; echo "${SETS[*]}")" --save "$OUT/goku_turn_preview.blend" --sheets "$OUT/sheets" > "$OUT/preview.log" 2>&1
tail -2 "$OUT/preview.log" | cut -c1-200
