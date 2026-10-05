#!/bin/bash
# Run melee-pc.exe in its own sandbox directory.
#
#   tools/port/run.sh sonic --iso ${GW_ISO_AKANEIA}
#   MELEE_TRAINING=38 MELEE_PAD_SCRIPT=pad_specialhi.txt tools/port/run.sh sonic --iso ...
#   tools/port/run.sh --test tests --iso "${GW_ISO_VANILLA}"
#
# Why a sandbox at all: the game writes melee-pc.log, crashlogs/ and its memory card relative to
# the directory it runs in, and looks for mods/ next to its own executable. Two runs in
# $GW_ROOT/_build therefore fight over all four. Worse, a running game holds melee-pc.exe open, so
# it blocks the next link with LNK1104 - which is exactly what happened mid-session once.
#
# So each run gets _build/runs/<name>/ with its OWN COPY of the exe (7.6 MB, a moment to copy).
# The build's exe is then never open, and a play-test can run for as long as it likes while the
# next build links underneath it. The map is copied alongside so a crash log's RVAs can still be
# resolved against the exact build that produced them.
#
# The log is left in the sandbox and printed at the end; this run's sandbox is never cleaned up,
# because the log of a run that just crashed is the whole point. Old sandboxes are pruned (below).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
. ./portlib.sh

test_mode=0
realtime=0
max_seconds="${MELEE_MAX_SECONDS:-}"
# --test runs turbo by default (MELEE_TURBO=1: virtual clock, no pacing; see PORT_DEV_QUICKREF);
# --realtime keeps 60 Hz. A plain window run keeps its default (realtime) unless the caller sets it.
while [ "${1:-}" = "--test" ] || [ "${1:-}" = "--realtime" ] || [ "${1:-}" = "--max-seconds" ] || [ "${1:-}" = "--idle-cpus" ]; do
    case "$1" in
        --test) test_mode=1 ;;
        --realtime) realtime=1 ;;
        --idle-cpus) export MELEE_CPU_IDLE=1 ;; # every CPU-controlled fighter stands still (agent test runs)
        --max-seconds) [ $# -ge 2 ] || gw_die "--max-seconds needs N"; max_seconds="$2"; shift ;;
    esac
    shift
done
if [ "$test_mode" = 1 ]; then
    if [ "$realtime" = 1 ]; then export MELEE_TURBO=0
    else export MELEE_TURBO=1
    fi
elif [ "$realtime" = 1 ]; then
    export MELEE_TURBO=0
fi
name="${1:-}"
[ -n "$name" ] || gw_die "usage: run.sh [--test] [--realtime] [--idle-cpus] [--max-seconds N] <sandbox-name> [game args...]"
case "$name" in .|..|*/*|*\\*) gw_die "sandbox name must be one directory name" ;; esac
shift

[ -f "$GW_EXE" ] || gw_die "no exe at $GW_EXE - run tools/port/build.sh first"

sandbox="$GW_BUILD_ROOT/runs/$name"
mkdir -p "$sandbox"
mkdir "$sandbox/.active-run" 2>/dev/null ||
    gw_die "sandbox is active or retained a launch marker; choose a new sandbox name"
trap 'rmdir "$sandbox/.active-run" 2>/dev/null || true' EXIT
# Each sandbox holds its own exe copy, so they add up (1,656 of them once reached 49 GB). Stamp
# this run, then keep only the GW_RUNS_KEEP (default 50) most recently STARTED sandboxes. The
# stamp, not the directory mtime, orders them: directory dates drift (a bulk copy once re-dated
# every sandbox to one day). Unstamped sandboxes (made by other launchers, e.g. netplay_local.ps1,
# possibly with a game still running in them) are never touched; nor is this run's.
touch "$sandbox/.last_run"
python "$GW_ROOT/tools/port/prune_runs.py" --root "$GW_BUILD_ROOT/runs" \
    --keep "${GW_RUNS_KEEP:-50}" --current "$name" || gw_die "sandbox safety check failed"
cp -f "$GW_EXE" "$sandbox/melee-pc.exe"
if [ -f "$GW_MAP" ]; then cp -f "$GW_MAP" "$sandbox/melee-pc.map"; fi

# SDL3 and Dawn are loaded from the executable's own directory, so the sandbox needs them too.
# Without them Windows fails the load before main() and the shell reports a bare 127 with no log
# at all, which looks exactly like a missing exe.
for dll in SDL3.dll webgpu_dawn.dll; do
    [ -f "$GW_ROOT/_build/$dll" ] || gw_die "missing $GW_ROOT/_build/$dll"
    if [ "$GW_ROOT/_build/$dll" -nt "$sandbox/$dll" ]; then
        cp -f "$GW_ROOT/_build/$dll" "$sandbox/$dll"
    fi
done
# The pipeline seed (tools/port/build_pipeline_seed.py), optional, also next to the exe.
seed="$GW_ROOT/_build/initial_pipeline_cache.db"
if [ -f "$seed" ] && [ "$seed" -nt "$sandbox/initial_pipeline_cache.db" ]; then
    cp -f "$seed" "$sandbox/initial_pipeline_cache.db"
fi
if [ -f "${seed%.db}.core" ]; then
    cp -f "${seed%.db}.core" "$sandbox/initial_pipeline_cache.core"
fi
# Dawn's compiled-shader cache (dawn_cache.db) lives in the sandbox. A new sandbox starts cold, so
# warming the seed's ~6,000 pipelines keeps 8 d3dcompiler threads at ~98% for minutes: every perf
# run on a fresh sandbox measured the game next to a compile storm. Start a new sandbox from the
# largest cache of this build root whose game is not running (a live one may be mid-write).
# GW_DAWN_CACHE_SEED=0 keeps the old cold start (e.g. to measure a first launch).
if [ ! -f "$sandbox/dawn_cache.db" ] && [ "${GW_DAWN_CACHE_SEED:-1}" != 0 ]; then
    python "$GW_ROOT/tools/port/runs.py" --root "$GW_BUILD_ROOT/runs" seed-cache --sandbox "$sandbox" ||
        echo "cache seed skipped: process inventory or cache copy failed" >&2
fi

# mods/ is found next to the executable, so a sandbox sees no mods unless it is told where they
# are. The default is the shared _build/mods folder, which holds NO mods (only targettest/ layouts,
# which the loader skips) so a test on a disc tests
# that disc: it once held an old Akaneia Sonic mod that silently mounted over ACE in every run
# (moved to _build/mods-legacy). To test mods, set MELEE_MODS_DIR (e.g. _build/mods-split/ace).
export MELEE_MODS_DIR="${MELEE_MODS_DIR:-$GW_ROOT/_build/mods}"

# The caption drawn on the window (gw_overlay.cpp run_label). With several lanes' windows open at
# once an unlabelled one is anonymous, so default it to "<lane> / <sandbox>"; callers that know
# more (the test, the disc, the fighters) set MELEE_RUN_LABEL themselves.
lane="$(basename "$GW_BUILD_ROOT")"; [ "$lane" = "_build" ] && lane="main"
export MELEE_RUN_LABEL="${MELEE_RUN_LABEL:-$lane / $name}"
export MELEE_RUN_OWNER="${MELEE_RUN_OWNER:-$MELEE_RUN_LABEL}"
if [ "$test_mode" = 1 ]; then export MELEE_UNATTENDED=1; fi
if [ "${MELEE_UNATTENDED:-0}" = 1 ]; then
    max_seconds="${max_seconds:-300}"
    export MELEE_WATCHDOG_ACTION="${MELEE_WATCHDOG_ACTION:-exit}"
fi
max_seconds="${max_seconds:-0}"
export MELEE_MAX_SECONDS="$max_seconds"

# Test windows play quietly: MELEE_VOLUME is the game's master volume in percent. The user plays
# while lanes test; a full-volume window is the first complaint. Callers can override it.
if [ "${MELEE_UNATTENDED:-0}" = 1 ]; then
    export MELEE_VOLUME="${MELEE_VOLUME:-0}"
    export MELEE_PAD_IGNORE_ADAPTER=1
else
    export MELEE_VOLUME="${MELEE_VOLUME:-3}"
fi

# GD's window defaults (2026-09-28): a 16:9 window and a 1440p-class internal image. render_scale 3
# makes the framebuffer follow the window's aspect, so a 16:9 window renders 2560x1440 internally
# (see Aurora's scale_frame_buffer_to_aspect / MELEE_RENDER_SCALE in shim_vi.c). Widescreen defaults
# on so runs show the wide picture; MELEE_WIDESCREEN=0 (or any of these) overrides per run.
export MELEE_WINDOW_W="${MELEE_WINDOW_W:-1920}"
export MELEE_WINDOW_H="${MELEE_WINDOW_H:-1080}"
export MELEE_RENDER_SCALE="${MELEE_RENDER_SCALE:-3}"
export MELEE_WIDESCREEN="${MELEE_WIDESCREEN:-1}"

# Pad scripts are named relative to the working directory, and they all live in _build. Resolve a
# bare name against that so callers can keep writing MELEE_PAD_SCRIPT=pad_specialhi.txt.
if [ -n "${MELEE_PAD_SCRIPT:-}" ] && [ ! -f "$sandbox/${MELEE_PAD_SCRIPT}" ] &&
    [ -f "$GW_ROOT/_build/${MELEE_PAD_SCRIPT}" ]; then
    export MELEE_PAD_SCRIPT="$GW_ROOT/_build/${MELEE_PAD_SCRIPT}"
fi

# A Windows binary launched from WSL does NOT inherit a WSL shell variable unless the variable
# is named in WSLENV. That is a silent failure: the game starts, reads nothing, and boots
# normally, which looks exactly like a broken hook. Name every MELEE_* variable that is
# currently set. Harmless from Git Bash or PowerShell, where the environment is already shared.
for v in $(compgen -v); do
    case "$v" in MELEE_*|GW_ISO*) export "$v" ;; *) continue ;; esac
    case ":${WSLENV:-}:" in
    *":$v:"* | *":$v/"*) ;;
    *) WSLENV="${WSLENV:+$WSLENV:}$v" ;;
    esac
done
export WSLENV

echo "sandbox   $sandbox"
echo "log       $sandbox/melee-pc.log"
set +e
if [ "$test_mode" = "1" ]; then
    gw_run_owned "$sandbox" "$max_seconds" --test "$@"
    rc=$?
else
    gw_run_owned "$sandbox" "$max_seconds" "$@"
    rc=$?
fi
set -e
echo "exit      $rc"
if [ -f "$sandbox/melee-pc.log" ]; then
    n="$(grep -c FATAL "$sandbox/melee-pc.log" || true)"
    echo "FATAL     $n"
    if [ "$n" != "0" ]; then grep -A 6 FATAL "$sandbox/melee-pc.log" | head -20; fi
fi
exit "$rc"
