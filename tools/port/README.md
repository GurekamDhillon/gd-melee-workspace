# tools/port

Build and run the native Windows game from the workspace. `portlib.sh` resolves `GW_ROOT` from
these scripts and reads `.env`; `GW_MELEE` selects the game checkout, and `GW_BUILD_ROOT` selects
its objects, link response file, EXE, map and run sandboxes. The default game is `GW_ROOT/melee`.
A docs-only worktree need not contain it: set `GW_MELEE` explicitly when using another checkout.

## Commands (Git Bash)

```bash
bash tools/port/build.sh
bash tools/port/build.sh --tu src/melee/ft/ftdata.c --shim shim_dvd.c
bash tools/port/run.sh play --iso "C:/path/game.iso"
bash tools/port/run.sh --test tests --iso "C:/path/game.iso"
bash tools/port/run.sh --test --realtime tests-rt --iso "C:/path/game.iso"
MELEE_FPS=u bash tools/port/run.sh uncapped --iso "C:/path/game.iso"
bash tools/port/run.sh --idle-cpus --realtime lab-check --iso "C:/path/game.iso"   # every CPU stands still (MELEE_CPU_IDLE=1)
MELEE_TURBO=1 MELEE_PAD_SCRIPT="C:/path/check.lua" bash tools/port/run.sh batch --iso "C:/path/game.iso"
python tools/port/gd_prompt.py                # type text -> in-game comm callouts (needs MELEE_CONSOLE_PORT)
```

`gd_prompt.py` needs a running game started with `MELEE_CONSOLE_PORT` (the environment passes
through; the socket is 127.0.0.1-only, so run the prompt on Windows). Plain lines become `comm`
callouts in game; `:raw <line>` sends any console command; `:help` lists the rest, including
`:who falco`, `:sound <id>`, `:clear`.

Wrapper flags `--test` and `--realtime` go **before the sandbox name**. `--test` exports
`MELEE_TURBO=1`; `--realtime` exports 0. The headless test runner has no paced game-frame loop,
so its turbo request is informational, not an accelerated simulation. Normal windowed runs
remain realtime unless explicitly requested otherwise.

`build.sh` scans stale game TUs with `scan_stale_tus.py` (timestamps, including Geno headers),
rebuilds stale native shims, links, regenerates the bridge from that map, and rebuilds/relinks it
as needed until stable (at most four regeneration checks). It audits the final EXE's bridge ABI.
An unchanged trusted bridge avoids the extra link. Do not use raw clang for game TUs or bypass
the fixpoint. `GW_JOBS` sets the compile jobs for game TUs and shims (default: physical cores, at most 12).
Staleness is by content: each object records a hash of its source, its depfile's headers, the
compile script and the tools, so a touched-but-unchanged file rebuilds nothing, a header rebuilds
only its consumers, a flag change rebuilds everything, and a revert restores the previous object.

## Runtime switches

| Switch | Meaning |
|---|---|
| `MELEE_FPS=u` | uncapped interpolated presentation; realtime game logic remains 60 Hz |
| `MELEE_FPS=120` | cap interpolated presentation at 120; not a faster simulation |
| `MELEE_TURBO=1`, game `--turbo` | virtual-clock simulation without realtime pacing; requires `MELEE_PAD_SCRIPT` or `MELEE_LAB_BATCH`; refuses netplay, Slippi and fake rollback sessions |
| game `--realtime` | disables a turbo request; wrapper `--realtime` sets the environment to 0 |
| `MELEE_TURBO_RENDER=N` | present every Nth game frame (default 8, 0 never; range 0-10000); hidden/minimised windows do not present |
| `MELEE_TURBO_DRAWS=1` | keep display lists and skinning on unpresented turbo frames; normally suppressed while render callbacks still run |
| `MELEE_TURBO_HASHLOG=path` | per-live-match-frame snapshot hashes for parity diagnostics |
| `MELEE_TEST_SEED=integer` | fixed boot RNG seed for scripted comparisons |
| `MELEE_MODS_DIR=path` | parent containing mod folders; use a Windows path (`pwd -W` in Git Bash) |
| `GW_DAWN_CACHE_SEED=0` | disable copying an existing inactive run's compiled shader cache into a fresh sandbox |
| `GW_RUNS_KEEP=N` | retain the N most recently started stamped sandboxes (default 50); unstamped ones are not pruned |

Turbo mutes audio. Use realtime runs for controller, sound and presentation checks. Lua
`gd.input(..., frames)` counts completed logic frames even while stepping; text pad scripts
still consume one frame per PADRead. See [scripting.md](../../docs/scripting.md).

### Positioning and driving an opponent in a test

Brief every game-driving lane with this. Use the LAB (`mode=lab`), never training, and give every
CPU you do not script `cpus=idle` (or `--idle-cpus`). A CPU you do need to act is put in
`gd.cpu_mode(port, "script")`: the retail AI then writes nothing and the script writes the CPU's
virtual controller (`fp->cpu.*`), which `gd.input` cannot reach.

- Place it: `gd.teleport(port, x, y)` then wait for `Wait` on the floor; or, with no teleport,
  `gd.cpu_goto(port, x, y)` and wait for `gd.cpu_script_done(port)` (`gd.cpu_goto_status` says
  `arrived`, `blocked` or `fell`).
- Drive it: `gd.cpu_pad(port, {x=,y=,cx=,cy=,l=,r=,buttons=}, frames)` for a held sample;
  `gd.cpu_script(port, {{"press_x"},{"wait",1},{"release_x"}})` for the retail command language;
  `gd.cpu_macro(port, "wavedash"|"short_hop"|"full_hop"|"dash"|"dash_dance"|"waveland"|
  "lcancel_aerial"|"shield"|"perfect_shield"|"tech"|"jump_cancel_grab", {dir=...})` for
  technique timed from the fighter's own attributes (`gd.cpu_attrs(port)`).
- Read it back, do not look: `gd.player(port).action` / `.action_frame`, `gd.cpu_script_status(port)`
  (the controller as the engine will read it), the `on_perfect_shield` / `on_grab` hooks.
- Step it: `gd.pause()` and `gd.step(n)` are frame exact. A script runs one logic frame after the
  call that started it. A `gd.run` task started from the console ends when the console client
  disconnects: load a script file (`load <path>`) for anything that must outlive the call.
- Reference: [scripting.md](../../docs/scripting.md), "The CPU's virtual controller".

## Isolation and evidence

`--idle-cpus` sets `MELEE_CPU_IDLE=1`: every CPU-controlled fighter idles for the whole process (agent test runs should pass it; `--test` and `MELEE_PAD_IGNORE_ADAPTER=1` do not imply it). The run is recorded as `idle_cpus` in `run.json`.

`run.sh` copies the EXE and map into `GW_BUILD_ROOT/runs/<name>/`, supplies runtime DLLs and
caches, and leaves the log there. Reusing a name replaces that sandbox's build: use distinct
names for concurrent runs. A live copy is not updated by a later build.

`agent_new.sh <name>` creates a game worktree and build root; `agent_rm.sh <name>` removes it
only when clean and retains the branch. Baseline objects are hardlinked: the local game-TU
writer must replace outputs rather than truncate shared files. Shared Aurora/Dawn/SDL libraries
are outside lane isolation. Read [HANDOFF.md section 6](../../docs/HANDOFF.md#6-traps) before parallel builds.

Read the run's log and crash logs as well as the test summary. Record EXE/game revision, disc,
mods, run directory and switches with any result. A successful older run is not a HEAD check.

## Owned runs and hang diagnosis

Use native Windows Python (Windows 10+), including from Git Bash. `run.sh` creates a
suspended child **inside** a kill-on-close Windows Job Object using
`PROC_THREAD_ATTRIBUTE_JOB_LIST`, writes `run.json`, then resumes it. Only its
Python supervisor holds the job handle; the child cannot inherit it. Killing the
supervisor closes the job in the kernel. If `timeout N bash run.sh ...` ends only
bash, the supervisor notices its native parent handle signalled within 250 ms and
ends its own child. It never owns or kills another run's job.

Agents must use an owner tag and a distinct sandbox, wait for completion, then
verify their inventory is empty before reporting that nothing remains running:

```bash
MELEE_RUN_OWNER=alpha MELEE_UNATTENDED=1 bash tools/port/run.sh --max-seconds 180 alpha-check --iso "$GW_ISO_ACE"
python tools/port/runs.py wait alpha-check
python tools/port/runs.py status --owner alpha
```

`--max-seconds N` goes before the sandbox name. `--test` sets unattended policy;
unattended runs default to 300 seconds and interactive runs to no time limit.
Explicit `--max-seconds 0` removes the overall limit. `MELEE_MAX_SECONDS` supplies
the wrapper default. The native watchdog defaults to 10 seconds without a main
tick (`MELEE_WATCHDOG_SECS=0` disables it), with `MELEE_WATCHDOG_ACTION=log|dump|exit`:
interactive default `log`, unattended default `exit`. Both `dump` and `exit` attempt
a minidump; `exit` terminates with code 86 after a bounded dump wait. The supervisor
also enforces unattended heartbeat/main-tick progress with a five-second margin.
It detects absent heartbeats too; use a freshly integrated EXE, not an old copy.

`heartbeat.json` records main, completed-present and logic counters; scene; script,
LAB/step and timed-freeze intent; debugger/system-modal state; hidden/minimized/DWM
cloaked state; last normal log time; active Lua callback/instruction count; and
script deadlines. A stalled main loop is fatal under exit policy even if the last
published intent said paused. Live main ticks with stalled logic, absent presents,
intentional pause, or hidden windows are distinct diagnostic states. Hiding a
window releases its adapter when it loses foreground ownership. Fully covering a window with another app is
not reliably detectable; `occlusion_known=false` states that limitation.

```bash
python tools/port/runs.py status
python tools/port/runs.py reap --owner alpha
python tools/port/runs.py reap --owner alpha --hung
python tools/port/runs.py reap --sandbox alpha-check --older-than 600
python tools/port/runs.py --root "C:/path/lane/runs" wait alpha-check
```

Selectors combine with AND. Reaping requires an explicit selector and only acts
on matching tracked runs after rechecking PID, creation time and executable path
through the same handle used for termination. Untracked games appear in status
but are never automatically reaped. `status` includes monitor/position and memory,
and warns below 2 GiB available RAM or at eight live games. `--root` narrows a
search; the default searches all lanes under `_build`. Ambiguous wait names fail.

CIM creation times are matched within 1 ms of the native FILETIME, with PID and
executable path still checked. Reaping no matching games prints an explicit
message and exits 1. Disc paths are replaced with `<disc>` in run metadata,
diagnostic copies, native logs and crash reports; the executable receives the
real path. Cache seeding uses an inactive source's atomic run claim and skips
seeding if process inventory fails.

Unattended volume defaults to 0; interactive volume defaults to 3. An explicit
`MELEE_VOLUME` wins. `MELEE_PAD_IGNORE_ADAPTER=1` and unattended policy prevent
adapter device opens. Only the foreground interactive game may claim it; the
scanner releases background handles independently of rendering. SDL's GameCube
driver is disabled so it cannot bypass this policy (`MELEE_SDL_GAMECUBE=1` and
`MELEE_PAD_RELEASE_ON_BLUR=0` no longer reserve the device).

`gd.scene_launch` publishes `scene-transition` / `expected_operation` for at most
30 seconds, ending at the first completed logic frame in the new scene. A stalled
main loop remains a hang throughout. Pause entry lines are capped at one per
30 seconds, with summaries of pause episodes and sampled duration; resume chatter
is suppressed.

The supervisor leaves `verdict.json` and prints `OK`, `TIMEOUT`, `HUNG`,
`HUNG presenting=.. logic=..`, `CRASH code=..`, `SILENT_EXIT`, or another explicit
termination reason. Forced termination saves `diagnosis.json`, the last 200 log
lines, and a copy of available `hang.txt`; the native watchdog writes `hang.txt`
and optionally `hang.dmp`. Exit codes: 86 hang, 124 overall timeout, 125 wrapper
death/reap/launch error, 130 interrupt; normal game/test codes remain intact. The
actual unsigned Windows fault code is retained in the verdict even when the shell
can only return 1. `wait` returns 0 only for `OK`.

Scripts and the console can use `gd.deadline("staging maze", 600)` before work,
and `gd.deadline_done("staging maze")` on completion. Deadlines count live logic
frames, pause during pause/hitstop, and skip rewind/resimulation. Names belong to
one script generation. Opening an existing deadline returns false and does not
extend it; done/unload cancels it. Expiry logs once, stays in heartbeat until done,
and calls that owner's `on_deadline(name, frames_waited)`. Refusing/failing callbacks
get a rate-limited summary after `MELEE_SCRIPT_WATCHDOG_SECS` (default 10 seconds).
False predicates without a reason string are not classified as refusals.

For explicit diagnostic testing only, set `MELEE_WATCHDOG_TEST=1` and use console
`watchdog-stall 12` with action `log` to let the game recover, or `exit` to verify
code 86. Native acceptance remains necessary after integration; source checks do
not establish that a copied EXE has these features.
