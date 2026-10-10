#!/bin/bash
# Measured frame/hitbox export (the Geno LAB's headless MELEE_LAB_BATCH, docs/geno.md 14.11) for every
# added m-ex fighter on the ACE disc and every retail fighter on ACE and vanilla. Live gd.hitboxes
# samples, so code-driven hitboxes (m-ex ftFunction) show up here even though no ftcmd script made them.
#
#   GW_MELEE=<game worktree> GW_BUILD_ROOT=<own build root> bash tools/research/ace_hitbox_lab_batch.sh OUTDIR
#
# OUTDIR gets <name>/framedata.json, hitboxes.csv, moves.csv (gameplay numbers; keep out of git).
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${GW_ROOT:-$(cd "$HERE/../.." && pwd)}"
case "$ROOT" in */worktrees/*) ROOT="${ROOT%%/worktrees/*}" ;; esac
cd "$ROOT" || exit 1
set -a; . ./.env; set +a
: "${GW_MELEE:?}" "${GW_BUILD_ROOT:?}"
OUT="${1:?usage: ace_hitbox_lab_batch.sh OUTDIR}"; mkdir -p "$OUT"
MODS="$GW_BUILD_ROOT/labmods"; mkdir -p "$MODS"
[ -d "$MODS/geno-lab" ] || cp -r "$GW_MELEE/pc/geno/mods/geno-lab" "$MODS/"
export MELEE_WINDOW_X=30000 MELEE_WINDOW_Y=30000 MELEE_UNATTENDED=1 MELEE_RUN_OWNER=acehb MELEE_TURBO=1
export MELEE_MODS_DIR="$(cygpath -m "$MODS")"
unset MELEE_PAD_SCRIPT

one() { # name iso token
  local n="lab_$1" iso="$2" tok="$3"
  [ -s "$OUT/$1/hitboxes.csv" ] && return
  MELEE_SCENE="mode=lab;p1=$tok;stage=fd" MELEE_LAB_BATCH=v1 MELEE_LAB_BATCH_QUIT=1 \
    timeout 400 bash tools/port/run.sh --max-seconds 240 "$n" --iso "$iso" > "$OUT/$1.out" 2>&1
  mkdir -p "$OUT/$1"
  cp "$GW_BUILD_ROOT/runs/$n/scripts-data/geno-lab_lab/framedata/"*/v1/* "$OUT/$1/" 2>/dev/null
}

for i in $(seq 27 58); do [ "$i" = 34 ] && continue; one "ace_mex$i" "$GW_ISO_ACE" "mex:$i"; done
for k in $(seq 0 25); do
  one "ace_ck$k" "$GW_ISO_ACE" "ck:$k"
  one "van_ck$k" "$GW_ISO_VANILLA" "ck:$k"
done
echo done > "$OUT/ALLDONE"
