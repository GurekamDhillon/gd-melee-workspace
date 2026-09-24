#!/bin/bash
# mkrun.sh <geno|main> <sandbox> <scene> [mods-dir|-] - start a visible run (3% volume, console on $PORT,
# default 51777) in the background, like _build/agents/alpha/tools/heaprun.sh. Exes are COPIES in
# ports/halberd/_run/<root>/ (beta's Geno exe / the main exe), so neither original is touched.
# Prints the PID of the game process started (kill only that one: taskkill //PID <pid> //F).
MK="C:/Users/Gurek/Desktop/GD's Melee/ports/halberd"
root="$1"; name="$2"; scene="$3"; mods="${4:-$MK/_run/mods}"
export GW_BUILD_ROOT="$MK/_run/$root"
export MELEE_RUN_LABEL="${LABEL:-metaknight / $root ($name)}"
export MELEE_VOLUME=3
export MELEE_SCENE="$scene"
export MELEE_CONSOLE_PORT="${PORT:-51777}"
export MELEE_LOG="${LOGCATS:-dvd,mex}"
[ -n "${LAB:-}" ] && export MELEE_LAB=1
if [ -n "${KBONLY:-}" ]; then export MELEE_INPUT=keyboard SDL_JOYSTICK_HIDAPI_GAMECUBE=0; fi
if [ "$mods" != "-" ]; then export MELEE_MODS_DIR="$mods"; fi
mkdir -p "$GW_BUILD_ROOT/runs"
nohup bash "C:/Users/Gurek/Desktop/GD's Melee/tools/port/run.sh" "$name" --iso "C:/iso/SSBM ACE Build v2.0.0.iso" \
    >"$GW_BUILD_ROOT/runs/$name.out" 2>&1 </dev/null &
sleep 4
# the game's PID: the melee-pc.exe whose image path is this sandbox
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='melee-pc.exe'\" | Where-Object { \$_.ExecutablePath -like '*halberd*_run*$root*runs*$name*' } | ForEach-Object { \$_.ProcessId }"
