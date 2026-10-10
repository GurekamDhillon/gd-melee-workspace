#!/bin/bash
# Run special_probe.lua for every added m-ex fighter (ACE disc): live items/projectiles and connected hits.
#   GW_MELEE=<game worktree> GW_BUILD_ROOT=<own build root> bash tools/research/ace_hitbox_probe_batch.sh OUTDIR
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${GW_ROOT:-$(cd "$HERE/../.." && pwd)}"
case "$ROOT" in */worktrees/*) ROOT="${ROOT%%/worktrees/*}" ;; esac
cd "$ROOT" || exit 1
set -a; . ./.env; set +a
: "${GW_MELEE:?}" "${GW_BUILD_ROOT:?}"
OUT="${1:?usage: ace_hitbox_probe_batch.sh OUTDIR}"; mkdir -p "$OUT"
export MELEE_WINDOW_X=30000 MELEE_WINDOW_Y=30000 MELEE_UNATTENDED=1 MELEE_RUN_OWNER=acehb MELEE_TURBO=1
export MELEE_PAD_SCRIPT="$HERE/special_probe.lua"
for i in $(seq 27 58); do
  [ "$i" = 34 ] && continue
  n="probe_mex$i"
  [ -s "$OUT/$n.txt" ] && continue
  MELEE_SCENE="mode=vs;p1=mex:$i;p2=mario;stage=fd" timeout 300 bash tools/port/run.sh --max-seconds 200 "$n" --iso "$GW_ISO_ACE" > "$OUT/$n.out" 2>&1
  cp "$GW_BUILD_ROOT/runs/$n/scripts-data/pad_script/probe.txt" "$OUT/$n.txt" 2>/dev/null
done
echo done > "$OUT/ALLDONE"
