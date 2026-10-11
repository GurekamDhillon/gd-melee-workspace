#!/bin/bash
# usage: run_parity.sh <run-name> <p1-token> [only-scenarios,comma-separated|all] [detail]
#   p1-token  captain            retail Captain Falcon
#             geno:geno-falcon   the standalone Geno Falcon (mods folder must hold geno-lab and geno-falcon)
# Runs falcon_parity.lua in the LAB against Mario, headless (turbo, offscreen, muted). Needs GW_MELEE / GW_BUILD_ROOT exported and
# MELEE_MODS_DIR (a Windows path) naming the mods parent. Writes $GW_BUILD_ROOT/runs/<run-name>/parity.txt (the PF/PS lines).
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -W)"
GW_ROOT="${GW_ROOT:-E:/Projects/Melee Workspace}"
run="$1"; tok="$2"; only="${3:-all}"; detail="${4:-}"
out="$GW_BUILD_ROOT/runs_cfg"; mkdir -p "$out"
cfg="$out/$run.lua"
{
  printf 'CFG = {'
  if [ "$only" != "all" ]; then
    printf 'ONLY = {'; IFS=, read -ra a <<< "$only"; for n in "${a[@]}"; do printf '["%s"]=true,' "$n"; done; printf '},'
  fi
  [ -n "$detail" ] && printf 'DETAIL = true,'
  printf '}\n'
  cat "$HERE/falcon_parity.lua"
} > "$cfg"
# Reproducible runs: the seed pins the RNG. Even so, a run can differ at a knife-edge scenario when the 60 Hz pad alarm fires twice in one logic frame
# (the sample for the next frame is taken before the Lua step that sets its input; the game logs "pad: P1 hold frame saw 2 PADReads"). Seed 777 gives 407/407 for Falco.
export MELEE_TEST_SEED="${MELEE_TEST_SEED:-777}"
export MELEE_LOG=all,-render,-gobj,-heap,-dvd,-mex,-watchdog,-tex,-audio,-snap,-frontend   # all lifts the per-prefix flood limit (400 lines per 10 s) that would drop trace lines
scene="mode=lab;p1=$tok/hu;p2=mario/hu;stage=fd;items=off;time=0"
bash "$HERE/../moves_check/run_scene.sh" "$run" "$scene" "$cfg" "${PARITY_TIMEOUT:-1500}" 2>&1 | tail -3
log="$GW_BUILD_ROOT/runs/$run/melee-pc.log"
grep -E "script \[pad_script\] (PF|PS) " "$log" | sed -E 's/^\[frame=[0-9]+ ms=[0-9]+\] script \[pad_script\] //' > "$GW_BUILD_ROOT/runs/$run/parity.txt"
grep -c "^PF" "$GW_BUILD_ROOT/runs/$run/parity.txt"; grep -E "^PS (TOTAL|DONE|FAIL)" "$GW_BUILD_ROOT/runs/$run/parity.txt"
