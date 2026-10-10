#!/bin/bash
# Run hitbox_timeline_dump.lua once per fighter and collect timeline.jsonl files OUTSIDE git.
#
#   GW_MELEE=<game worktree> GW_BUILD_ROOT=<own build root> bash tools/research/ace_hitbox_batch.sh OUTDIR
#
# Needs a built melee-pc.exe in GW_BUILD_ROOT and GW_ISO_ACE / GW_ISO_VANILLA in the workspace .env.
# Game windows are offscreen (MELEE_WINDOW_X/Y=30000) and the run is turbo. OUTDIR must not be in git:
# the dumps are gameplay numbers but the raw logs are not worth committing.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${GW_ROOT:-$(cd "$HERE/../.." && pwd)}"
case "$ROOT" in */worktrees/*) ROOT="${ROOT%%/worktrees/*}" ;; esac
cd "$ROOT" || exit 1
set -a; . ./.env; set +a
: "${GW_MELEE:?}" "${GW_BUILD_ROOT:?}"
OUT="${1:?usage: ace_hitbox_batch.sh OUTDIR}"; mkdir -p "$OUT"
export MELEE_WINDOW_X=30000 MELEE_WINDOW_Y=30000 MELEE_UNATTENDED=1 MELEE_RUN_OWNER=acehb MELEE_TURBO=1
export MELEE_PAD_SCRIPT="$HERE/hitbox_timeline_dump.lua"
export MELEE_LAB_MAXM="${MAXM:-700}"

one() { # name iso token
  local n="$1" iso="$2" tok="$3"
  [ -s "$OUT/$n.jsonl" ] && return
  MELEE_SCENE="mode=vs;p1=$tok;p2=none;stage=fd" timeout 400 bash tools/port/run.sh --max-seconds 120 "$n" --iso "$iso" > "$OUT/$n.out" 2>&1
  cp "$GW_BUILD_ROOT/runs/$n/scripts-data/pad_script/timeline.jsonl" "$OUT/$n.jsonl" 2>/dev/null
}

# added m-ex fighters: INTERNAL ids 27..58 (34 has no Pl file)
for i in $(seq 27 58); do [ "$i" = 34 ] && continue; one "ace_mex$i" "$GW_ISO_ACE" "mex:$i"; done
# retail fighters on both discs (CharacterKind 0..25)
for k in $(seq 0 25); do
  one "ace_ck$k" "$GW_ISO_ACE" "ck:$k"
  one "van_ck$k" "$GW_ISO_VANILLA" "ck:$k"
done
echo done > "$OUT/ALLDONE"
