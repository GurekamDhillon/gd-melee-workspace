#!/bin/bash
# With the DIAG build (logs "DIAG4 ... create_hitbox id>=4" from the fighter and item hitbox-create handlers),
# run special_probe.lua for ACE m-ex fighters FROM..TO and collect the DIAG4 lines per run.
#   GW_MELEE=<diag game worktree> GW_BUILD_ROOT=<its build root> bash tools/research/ace_diag4_sweep.sh OUTDIR FROM TO
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${GW_ROOT:-$(cd "$HERE/../.." && pwd)}"
case "$ROOT" in */worktrees/*) ROOT="${ROOT%%/worktrees/*}" ;; esac
cd "$ROOT" || exit 1
set -a; . ./.env; set +a
: "${GW_MELEE:?}" "${GW_BUILD_ROOT:?}"
OUT="${1:?OUTDIR}"; FROM="${2:?FROM}"; TO="${3:?TO}"; mkdir -p "$OUT"
export MELEE_WINDOW_X=30000 MELEE_WINDOW_Y=30000 MELEE_UNATTENDED=1 MELEE_RUN_OWNER=aceslot4 MELEE_TURBO=1
export MELEE_PAD_SCRIPT="$HERE/special_probe.lua"
for i in $(seq "$FROM" "$TO"); do
  [ "$i" = 34 ] && continue
  n="d4_mex$i"
  MELEE_SCENE="mode=vs;p1=mex:$i;p2=mario;stage=fd" timeout 300 bash tools/port/run.sh --max-seconds 200 "$n" --iso "$GW_ISO_ACE" > "$OUT/$n.out" 2>&1
  { echo "== mex$i"; grep -a "DIAG4" "$GW_BUILD_ROOT/runs/$n/melee-pc.log" | sort | uniq -c; } >> "$OUT/diag4_$FROM-$TO.txt"
done
echo done > "$OUT/DONE_$FROM-$TO"
