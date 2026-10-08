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
bash tools/port/bench.sh retail2                              # one benchmark scene, 60 Hz, judged (below)
bash tools/port/bench.sh ported1 --mods "C:/path/mods"        # a ported fighter v retail (needs its slot mod)
bash tools/port/bench.sh retail2 --update-baseline            # the ONLY way a baseline is written (quiet machine)
python tools/port/runs.py perf _build/runs/<name>             # judge any finished run's perf.json
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

## The perf record, and how a lane reads the verdict

Every launch writes a **perf record** (`perf.json` in the run folder, beside `run.json`, and one
`perf:` line per scene in `melee-pc.log`) from the engine's always-on **summary** (`gw_profiler.c`).
It costs nothing you can measure (turbo, retail Fox v Marth, five 9,000-frame runs: 1.790 ms a frame
with it off, 1.784 on, the full `MELEE_PROFILER=1` 1.898; target was under 0.05 ms). It keeps, per scene:
frames and wall time; frame work mean / p95 / p99 / worst; every bucket's mean per frame (logic, draw
recording, render worker, submit, animation, object callbacks, script, rewind, skinning, queue wait,
fighter, ...); hitch count and length over 16.7 ms; draw calls a frame (mean, max); per-frame event
counts (envelope slots set up and reused, pobj draws, GX begins and display lists); script time per mod;
peak memory; present rate. The first 600 frames of a scene (`first_use`, where every first-use hitch
lives) are reported apart from `steady`. `run.sh` prints one verdict line when a windowed run ends.

| verdict | meaning |
|---|---|
| `PASS` | every check that applies held |
| `WARN` | a hitch after warm-up, or the mean/p99 moved past the warn line against the baseline |
| `FAIL` | a budget broke (script over 1 ms a frame; frame-work p95 over 8.33 ms in a benchmark scene; a hitch over 100 ms after warm-up; draw calls over the scene's ceiling) or a regression passed the fail line |
| `NOISY` | **not judged**: another `melee-pc` was running at the start or end of the scene, or other processes used more than 35% of the CPU on average (70% peak). Timings are only comparable under the same conditions, so a noisy run proves nothing either way: rerun when the machine is quiet. `--judge-noisy` prints a verdict anyway, marked `*` |
| `N/A` | no scene reached 120 frames, or the run did not end cleanly (`in_progress`) |

Conditions are stored with the numbers (clock realtime/turbo, `MELEE_TURBO_RENDER`, fps cap, vsync,
window, render scale, build id, mod set, scene token, instance counts at start and end, other-process
CPU load). A baseline is only used when clock, fps cap, window, render scale and turbo render match.

`bench.sh <scene>` runs one fixed scene (`retail2`: two retail fighters; `ported1`: one ported fighter v
retail; `ported2`; `mixed4`: two ported and two retail), 60 Hz by default, warms 900 frames, measures 1,800,
quits the game through its own console, and judges the window. Ported scenes need `--mods DIR` or
`GW_BENCH_MODS` (the fighter's slot mod, used in place, read-only) and are skipped without. Baselines are
per machine in `_build/perf-baselines/<machine>/` (git-ignored), written only by `--update-baseline` from a
complete, quiet window. Regression thresholds, from the measured run-to-run spread (about 2-3% on a quiet
machine): warn at +10% or +0.5 ms on the mean (whichever is larger), fail at +20% or +1.0 ms; p99 warns at
x1.3 and fails at x1.6 of the baseline. All numbers are inclusive and per frame; render_worker and
pipeline_compile run on other threads and are never part of frame work. Thresholds live in
`tools/port/perfjudge.py`.

Switches: `MELEE_PERF_SUMMARY=0` turns the summary off entirely; `MELEE_PROFILER=1` keeps today's full
behaviour (events, details, hitch traces) and also feeds the perf record; `MELEE_PERF_PATH`,
`MELEE_PERF_HITCH_MS`, `MELEE_PERF_WINDOW=<warm>,<frames>` (what bench.sh sets). `prof perf` in the game
console writes `perf.json` now and prints the status. What a headless `--test` run can and cannot see:
it has no GPU and no paced loop, so it cannot time anything or count a real draw; the suite's
`perf_summary_accounting` pins the arithmetic of the record, and the draw-call ceilings are enforced by
`bench.sh` on a real scene.

## Runtime switches

| Switch | Meaning |
|---|---|
| `MELEE_FPS=u` | uncapped interpolated presentation; realtime game logic remains 60 Hz |
| `MELEE_FULLSCREEN=1` | borderless desktop fullscreen at start (F11 / Alt+Enter toggle in game; video.cfg `fullscreen`) |
| `MELEE_FPS=120` | cap interpolated presentation at 120; not a faster simulation |
| `MELEE_TURBO=1`, game `--turbo` | virtual-clock simulation without realtime pacing; requires `MELEE_PAD_SCRIPT` or `MELEE_LAB_BATCH`; refuses netplay, Slippi and fake rollback sessions |
| game `--realtime` | disables a turbo request; wrapper `--realtime` sets the environment to 0 |
| `MELEE_TURBO_RENDER=N` | present every Nth game frame (default 8, 0 never; range 0-10000); hidden/minimised windows do not present |
| `MELEE_TURBO_DRAWS=1` | keep display lists and skinning on unpresented turbo frames; normally suppressed while render callbacks still run |
| `MELEE_TURBO_HASHLOG=path` | per-live-match-frame snapshot hashes for parity diagnostics |
| `MELEE_TEST_SEED=integer` | fixed boot RNG seed for scripted comparisons |
| `MELEE_MODS_DIR=path` | parent containing mod folders; use a Windows path (`pwd -W` in Git Bash) |
| `GW_DAWN_CACHE_SEED=0` | disable copying an existing inactive run's compiled shader cache into a fresh sandbox |
| `MELEE_PERF_SUMMARY=0` | switch the always-on perf record off (default on; see "The perf record") |
| `MELEE_ENV_CACHE=1` / `compare` | opt-in per-frame memo of envelope skinning matrices; `compare` checks every hit against fresh arithmetic and logs `ENVCACHE` lines (default off: gain was only ~0.3-0.5 ms a legacy fighter) |
| `MELEE_POBJ_DIAG=1` | log what a frame's envelope draws are made of (`POBJDIAG`: pobj draws v distinct, slots, joint terms, distinct envelopes, render passes) |
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

## Defeating an opponent in a test (the debug cursor)

Lane briefs: to take a stock from an idle opponent, fly P1 and hold the cursor attack; do not script a separate launching
hit. Offline only (`gs_require_offline`):

```lua
gd.cpu_mode(2, "stand")          -- an idle CPU still needs this in the LAB
gd.fly_attack(1, true)           -- burst mode: damage 3, radius 6, active 3 / gap 24 frames, bkb 30, kbg 100, angle 45
-- every few frames: gd.fly_target(1, gd.player(2).x, gd.player(2).y)
```

Burst mode (default since 2026-10-05) is one hit instance per 27 logic frames, so hitlag ends and knockback carries the
victim before the next one. Measured on Final Destination, Mario against idle Fox: first KO at 216-259 logic frames
(about 4 s); a team of three (Fox, Falco, Marth) went down at 216, 603 and 1163 frames. Options:
`gd.fly_attack(1, true, {damage=, radius=, active=, gap=, kb=, kbg=, angle=})`; `every_frame=true` restores the old hit on
every frame (the same Fox needed 547 frames and 216% before it left the stage). Details: `docs/scripting.md`, `gd.fly_attack`.

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

## Atlas checks (the menu migration)

```bash
python tools/port/atlas_gate.py --step 6                 # have the earlier Atlas steps delivered what step 6 needs? (exit 1 lists what is missing and whose it is)
bash tools/port/check_atlas_online.sh                    # the online room's netplay isolation (below)
python tools/port/check_atlas_online_text.py             # the ONLINE PLAY rows' strings against the explainer and the row (label 18, help 3 lines)
```

```bash
python tools/port/atlas_gate.py --step 8                 # step 8 (the retail data screens): what steps 2 to 5 must have built
python tools/port/retail_screens.py                      # which retail screens are still retail (the Language-row question); --json is retail_screens_expected.json
python tools/port/check_no_disc_text.py                  # decoded retail text never reaches a log (counts only)
python -m unittest tools/port/test_fe_atlas_data.py tools/port/test_fe_atlas_results.py tools/port/test_sis_probe.py tools/port/test_check_no_disc_text.py
set -a; . ./.env; set +a; python tools/port/sis_probe.py --melee <game checkout>     # the text gate: counts and a verdict per source, from a disc in memory
bash tools/port/build.sh --native-test atlas-retailtext   # also atlas-data, atlas-models, atlas-results, atlas-data-host
bash tools/port/build.sh --native-test geno-lua            # the fighter-Lua sandbox (Geno slice 5): no game, no bridge
```

`sis_probe.py` reads one SIS archive out of the disc named by an environment variable (`GW_ISO_VANILLA` by default, never printed), decodes every string with the
same rules as `gw_ui_retailtext.c` and prints strings, characters, unknown glyphs and a GO, PARTIAL or NO-GO verdict per source. Nothing decoded is printed or
kept. The two Atlas data guards (`test_fe_atlas_data.py`, `test_fe_atlas_results.py`) read the adapter's source: the adapter owns the cursor, B returns to the
item that opened the screen, the allow-list of save writes (the event start's selection, nothing else), the results side-effect table.

`check_atlas_online.sh` is textual on purpose and pins that the online room is DRAWING ONLY: no pure Atlas unit (`pc/platform/gw_ui_*`) includes a
netplay header or names a netplay function; the game-side adapter (`gmfrontend_atlas_online.inc`) calls only an allow-list of reads, nothing the legacy
lobby did not already call, and turns each mouse or keyboard intent into the one `MenuInput_` bit the equivalent pad press has (one line per intent);
the pad term of the lobby's input (`mn_80229624(4)`) stays the legacy read; no Atlas online file touches the input mask; the opponent's blind pick is
read only after the legacy `fl_card_portrait` test; the room door writes game memory only through `gs_ui_put_be32`. Run it after touching the adapter,
the room door or `gmfrontend_online.inc`. It takes the game checkout as an argument (default `$GW_MELEE`).
