# Codex packet T: hung and orphaned game detection (2026-10-03)

Workspace `<workspace>`; game checkout `melee/` (read `CLAUDE.md`, `melee/CLAUDE.md`,
`melee/pc/platform/CLAUDE.md`, `melee/pc/docs/PORT_DEV_QUICKREF.md`, `tools/CLAUDE.md`, `tools/port/README.md`,
`tools/port/run.sh`, `tools/port/portlib.sh`). Both trees are deliberately dirty: do NOT commit, reset, stash, revert or
reformat. Do NOT run `tools/port/build.sh`, do NOT launch the game. Keep every file compilable. Several other Codex jobs are
editing engine C (`melee/pc/geno/`, `pc/gameworld/script_stage_slots*`, `gw_script_items.inc`, `gw_shader_models.inc`) and
Lua mods: work in NEW files where possible, touch shared files last and small, after re-reading them.

## The owner's ask (verbatim)
"We need better hung game detection"

## What went wrong today (the cases to cover; evidence in `_build/runs/` and `docs/HANDOFF-2026-10-03-ENGINE-DAY.md`)
1. A test game process stayed alive for 25 minutes after the agent that launched it reported "nothing left running"
   (`_build/runs/drv-sa2a`): the launch was wrapped in `timeout`, which ended the wrapper shell but not the game process.
2. A window that is hidden makes the game stall (known: `MELEE_WINDOW_HIDE`), holding the GameCube adapter.
3. A script waited forever in a silent loop (a mission "staging" that never finished): the game kept presenting frames,
   so nothing looked hung, but no progress was made.
4. A game was left running on the wrong monitor / holding the adapter while the owner wanted to play.
5. Earlier in the project: silent exits with no fault line (fastfail) and deadlocks where a game-side spin calls no shim.
Up to 8 games now run at once, launched by several agents and by the owner; each must be attributable and reapable by its
launcher without touching anyone else's.

## Build
A. **In the game: a watchdog and a heartbeat** (native, `melee/pc/platform/`, new file; registered in the link list as the
   platform CLAUDE.md says):
   - A heartbeat file in the run directory (`heartbeat.json`, rewritten about once a second from a small native thread,
     atomically): pid, start time, run label, wall clock, presented-frame counter, logic-frame counter, scene, whether the
     game is intentionally paused (script pause, LAB pause, console step, hitstop/freeze, debugger attached), whether the
     window is minimised/hidden/occluded, the last log line's time, the script watchdog's state (item C).
   - A watchdog thread: if the main loop has not ticked for N seconds (default 10, `MELEE_WATCHDOG_SECS`, 0 disables;
     disabled automatically under a debugger and while a modal/system dialog is up) it writes a diagnosis to the log and to
     `hang.txt`: which thread is stuck and where if it can be had cheaply (the main thread's instruction pointer resolved
     through the existing fault handler's map lookup: see how `gw: test fault pc ... rva` is produced; a stack walk if the
     existing crash path can do one), the last scene, the last script callback running (and its instruction count), the
     last shim entered; then, by policy (`MELEE_WATCHDOG_ACTION=log|dump|exit`, default `log` for interactive runs and
     `exit` under `run.sh --test` and when `MELEE_UNATTENDED=1`), writes a minidump and exits with a DISTINCT exit code.
   - Distinguish "not presenting" from "logic not advancing" from "intentionally paused" and say which in the log.
   - Silent-exit coverage: make sure every exit path writes a final line with the reason and code (the handoff's "silent
     exits need cdb" trap: improve what can be improved without a debugger; say what still needs one).
   - Zero cost on the hot path (one counter increment per tick); no effect on simulation.
B. **In the launcher: lifetime ownership and reaping** (`tools/port/run.sh`, `portlib.sh`, a new `tools/port/runs.py`):
   - Every run writes a `run.json` in its sandbox (pid, launcher's parent pid and name, label, start, command, timeout,
     owner tag from `MELEE_RUN_OWNER` or the label) and the game is started so that ending the wrapper ENDS THE GAME: a
     Windows Job Object with kill-on-close (a small helper, or PowerShell/ctypes in `runs.py`) so that `timeout`, Ctrl+C, a
     closed terminal or a dead agent cannot orphan it. Verify by design that `timeout N bash run.sh ...` now kills the game.
   - `run.sh` gets `--max-seconds N` (default for unattended runs; none for the owner's interactive windows) and uses the
     heartbeat: no heartbeat progress for the watchdog interval + margin = the run is declared HUNG, diagnosed (copy
     `hang.txt`, the last 200 log lines, the heartbeat) and ended, with exit status and a one-line verdict the caller can
     read (`OK`, `TIMEOUT`, `HUNG presenting=.. logic=..`, `CRASH code`, `SILENT_EXIT`).
   - `python tools/port/runs.py status` lists every live game: pid, sandbox, owner, age, monitor/window position, state from
     its heartbeat (running, paused, hung, hidden), memory; `runs.py reap --owner X` / `--sandbox NAME` / `--hung` /
     `--older-than` ends only matching runs (never others), and `runs.py wait NAME` blocks until a run is gone and prints
     its verdict. `status` also warns when available memory is under 2 GB or 8 games are running (the current cap).
   - Document the pattern agents must use (launch through `run.sh` with an owner tag; finish with `runs.py wait`; check
     `runs.py status --owner X` is empty before reporting) in `tools/port/README.md` and `PORT_DEV_QUICKREF.md`.
C. **Script-level stalls** (the staging loop case): a per-script progress watchdog in the Lua host: a script (or the
   console) can open a named deadline (`gd.deadline("staging maze", frames)` / `gd.deadline_done(name)`), and an expired
   deadline logs once with the name, owner script and frames waited, raises `on_deadline` and shows in the heartbeat; the
   missions mod is not yours to edit: report the two-line change it should make. Also log when one script callback has
   been failing or refusing every frame for N seconds (rate-limited), since "refused" loops were silent today.
Tests: headless tests for the heartbeat contents and the watchdog firing on a deliberately stalled test loop (with the
action set to log so the suite continues), the paused/hidden distinctions, deadlines; Python tests for `runs.py` (status
parsing, owner filtering, never touching non-matching runs, verdict classification) with fake run directories.
Report `_build/tmp/codex-hung-game-detection-report.md`: what each part detects and what it cannot, file:line, how the
job object is created and why it cannot orphan, the exit codes, the agent launch pattern, and a native test plan
(deliberate hang via a console command you add for testing only, a hidden window, a killed wrapper, a stalled script).
