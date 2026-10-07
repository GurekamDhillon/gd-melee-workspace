# tools/sweep: the crash sweep

`crash_sweep.py` loads every stage and every fighter on each disc (one VS match per run, no menus) and
reports what crashes, hangs or exits. `python tools/sweep/crash_sweep.py --plan` lists the runs and starts
nothing. Results land in `<out>/results.md` and `results.json`; each run keeps its sandbox (log, crash log)
under `<out>/runs/<tag>/`. Read that log before believing the verdict (`docs/HANDOFF.md` §6).
`onep_sweep.py` is the one-player variant. Tests: `python tools/sweep/test_crash_sweep.py`.

Run it from a worktree with `GW_ROOT` pointing at the main checkout (that is where `.env` and `_build/SDL3.dll`
live); the discs come from `.env`, and no disc path is ever printed.

## Options

| option | what |
|---|---|
| `--exe`, `--out` | the build to test, and where results go |
| `--discs`, `--only stages\|fighters`, `--match TEXT` | which runs |
| `--secs N` | length of a stage run (fighter runs +5). In turbo these are GAME seconds (N*60 logic frames); with `--realtime` they are wall-clock seconds |
| `--realtime` | 60 fps instead of turbo |
| `--skip TAG,TAG` | leave these run tags out |
| `--resume results.json` | leave out every run already in an earlier results file and carry its rows into the new results |
| `--max-games N` | hold each launch while N or more `melee-pc.exe` are running, anyone's (default 3, 0 = no gate) |
| `--parallel N` | concurrent windows (default 4; the gate still applies) |
| `--monitor2` | tile the windows on the second monitor (origin -1080,-360) instead of the primary |

## Turbo

Turbo is on by default. The game refuses `MELEE_TURBO=1` without a pad script, so each run is given
`tools/sweep/empty_pad.lua`, a script that drives no pad channel. `MELEE_INPUT=none` is already set, and the
CPU players come from the scene (`cpu9`), not from the pad, so they play as before. Checked in a 14 s realtime
A/B of Fox vs Falco level 9 on Battlefield, with and without the script: the draw counts (`prim`, `dlist` in
the heartbeat) grow at the same rate once the match starts, which they would not if the CPUs stood still.
A turbo run finishes at `secs*60` logic frames or a wall cap of `max(60, 4*secs)` seconds. The progress
grace for a stalled heartbeat is 30 s of wall clock.

## Etiquette

Windows are muted (`MELEE_VOLUME=0`). Another agent's games count toward `--max-games`. Stop only the PIDs
you started; never kill `melee-pc.exe` by name.
