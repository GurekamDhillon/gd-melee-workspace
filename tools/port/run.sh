#!/bin/bash
# Run melee-pc.exe in its own sandbox directory.
#
#   tools/port/run.sh sonic --iso C:/iso/Akaneia.iso
#   MELEE_TRAINING=38 MELEE_PAD_SCRIPT=pad_specialhi.txt tools/port/run.sh sonic --iso ...
#   tools/port/run.sh --test tests --iso "C:/iso/Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso"
#
# Why a sandbox at all: the game writes melee-pc.log, crashlogs/ and its memory card relative to
# the directory it runs in, and looks for mods/ next to its own executable. Two runs in
# C:/gdm/_build therefore fight over all four. Worse, a running game holds melee-pc.exe open, so
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
if [ "${1:-}" = "--test" ]; then
    test_mode=1
    shift
fi
name="${1:-}"
[ -n "$name" ] || gw_die "usage: run.sh [--test] <sandbox-name> [game args...]"
shift

[ -f "$GW_EXE" ] || gw_die "no exe at $GW_EXE - run tools/port/build.sh first"

sandbox="$GW_BUILD_ROOT/runs/$name"
mkdir -p "$sandbox"
# Each sandbox holds its own exe copy, so they add up (1,656 of them once reached 49 GB). Stamp
# this run, then keep only the GW_RUNS_KEEP (default 50) most recently STARTED sandboxes. The
# stamp, not the directory mtime, orders them: directory dates drift (a bulk copy once re-dated
# every sandbox to one day). Unstamped sandboxes (made by other launchers, e.g. netplay_local.ps1,
# possibly with a game still running in them) are never touched; nor is this run's.
touch "$sandbox/.last_run"
(
    cd "$GW_BUILD_ROOT/runs" || exit 0
    for d in */; do
        d="${d%/}"
        [ -f "$d/.last_run" ] && echo "$(date -r "$d/.last_run" +%s) $d"
    done | sort -rn | tail -n +"$(( ${GW_RUNS_KEEP:-50} + 1 ))" | while read -r _ d; do
        [ "$d" = "$name" ] || rm -rf "./$d"
    done
) || true
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

# mods/ is found next to the executable, so a sandbox sees no mods unless it is told where they
# are. The default is the shared _build/mods folder, which is kept EMPTY so a test on a disc tests
# that disc: it once held an old Akaneia Sonic mod that silently mounted over ACE in every run
# (moved to _build/mods-legacy). To test mods, set MELEE_MODS_DIR (e.g. _build/mods-split/ace).
export MELEE_MODS_DIR="${MELEE_MODS_DIR:-$GW_ROOT/_build/mods}"

# The caption drawn on the window (gw_overlay.cpp run_label). With several lanes' windows open at
# once an unlabelled one is anonymous, so default it to "<lane> / <sandbox>"; callers that know
# more (the test, the disc, the fighters) set MELEE_RUN_LABEL themselves.
lane="$(basename "$GW_BUILD_ROOT")"; [ "$lane" = "_build" ] && lane="main"
export MELEE_RUN_LABEL="${MELEE_RUN_LABEL:-$lane / $name}"

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
for v in $(compgen -v | grep "^MELEE_" || true); do
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
    ( cd "$sandbox" && ./melee-pc.exe --test "$@" ) | tail -4
    rc=${PIPESTATUS[0]}
else
    ( cd "$sandbox" && ./melee-pc.exe "$@" ) >/dev/null 2>&1
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
