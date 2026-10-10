#!/bin/bash
# Boot each added m-ex fighter for a few seconds and keep the "interp:" lines (which ftFunction slots the
# port dispatches, which it ignores, how many overrides were installed).
#   GW_MELEE=... GW_BUILD_ROOT=... bash tools/research/ace_interp_scan.sh OUTFILE
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${GW_ROOT:-$(cd "$HERE/../.." && pwd)}"
case "$ROOT" in */worktrees/*) ROOT="${ROOT%%/worktrees/*}" ;; esac
cd "$ROOT" || exit 1
set -a; . ./.env; set +a
: "${GW_MELEE:?}" "${GW_BUILD_ROOT:?}"
OUT="${1:?usage: ace_interp_scan.sh OUTFILE}"; : > "$OUT"
export MELEE_WINDOW_X=30000 MELEE_WINDOW_Y=30000 MELEE_UNATTENDED=1 MELEE_RUN_OWNER=acehb MELEE_TURBO=1
unset MELEE_PAD_SCRIPT
for i in $(seq 27 58); do
  [ "$i" = 34 ] && continue
  n="interp_mex$i"
  MELEE_SCENE="mode=vs;p1=mex:$i;p2=none;stage=fd" timeout 60 bash tools/port/run.sh --max-seconds 12 "$n" --iso "$GW_ISO_ACE" > /dev/null 2>&1
  echo "== mex$i" >> "$OUT"
  grep -a "interp:" "$GW_BUILD_ROOT/runs/$n/melee-pc.log" | sed 's/^\[[^]]*\] //' >> "$OUT"
done
