# Benchmark harness

Run from the workspace root with a built, current game executable and local disc:

```powershell
python tools/bench/run.py baseline --iso C:/path/vanilla.iso --profiler both
python tools/bench/run.py steady_worst --iso C:/path/ace.iso --mods-dir C:/path/mods
python tools/bench/run.py rollback_worst --iso C:/path/ace.iso --mods-dir C:/path/mods
python tools/bench/run.py hitch_worst --iso C:/path/ace.iso --mods-dir C:/path/mods
python tools/bench/compare.py REPORT_A REPORT_B
python tools/bench/compare.py BASELINE_OFF BASELINE_ON --legacy
```

`--frames` defaults to 1800, `--seed` to 12345. The runner invokes `run.sh --realtime`,
never the executable directly, and forces a visible 1066x600 second-monitor window,
uncapped presentation and turbo off. `--plan` generates bundles/launch plans without
launching; its reports are not benchmark results. `--timeout` defaults to 300 seconds.
On timeout the labelled game window is retained for diagnosis; close it before retrying.

Results live in `_build/bench/<scenario>/<UTC timestamp>-on|off-a<admission index>/`.
`profile.json` is native profiler output. `report.json` adds bench metadata, actual
roster, setup/refusal outcomes, completed logic frames, backend, disc stamps and mod
stamps. `summary.txt` is compact text. Retained logs accompany failed admissions.
Profiler metrics cover the reset at the end of setup through shutdown; the initial
reset frame and final report frame can be partial. The report's native frame count
must be considered separately from completed scripted logic frames.

The steady scenario tries six distinct heavy retail fighters, including Ice Climbers,
then configured lower-diversity fallback rosters. Enabled installed fighter mods with
`INSTALL.json` names are discovered; the first candidate replaces P2, with actual
character identity reported after admission. This is a configured ranking, not a
proof of the globally heaviest possible roster. Pass `--config` with an explicit
`roster` to select other fighters; explicit choices override auto-discovery. P1-4
are human scripted slots; P5-6 are CPUs with explicit stand mode and virtual claims.

Steady uses maximum render scale 8 and requested MSAA 4, 32 item enemies replenished
on a 30-frame cadence, item frequency 4, contact trace/overlay, sample post-processing,
fighter surface shaders and original lit/glass grid instances up to the shared 256
instance cap. Real `on_clank` events trigger passes; the report gives achieved clanks.
The generated mission and its streaming/HUD/runtime use the existing mission modules
and room kit (`--kit` overrides its location). Preparation failure and native refusal
are reported. Changing mission geometry while the global instance pool is full may
refuse; that is a measured admission limitation.

Rollback requests the existing maximum deployed depth 12 using test-only
`MELEE_SYNCTEST_BENCH=1` and `MELEE_SYNCTEST=12`. Warmup and render-pool safety pauses
remain. Inspect achieved `rollback.frames` and rollback diagnostics; requested depth
alone does not establish that every frame reached it.

Hitch starts without a reused Dawn cache, then separates first-use shader/material
uploads, bench/call, save/load, generated maze movement/reload and LAB rewind tests.
If a ported fighter is discovered, four special input sequences are attempted.
`event-*.trace.json` retains eight native frames around each event, with the largest
neighbouring frame zone in `bench.event_traces`. Automatic threshold hitch files are
also retained. Frame zones may contain pacing; async render/GPU attribution requires
reading the trace. Latest-presented sample windows are explicitly labelled as
observations, not exact event timings. Coverage is the project's sample shader suite
and scripted fighter specials, not an exhaustive invocation of every mod effect.

A scenario JSON has `roster`, `mode`, `stage`, `items`, `env`, `features`, `setup` and
`events`. Steps contain `feature`, `api`, `args`; events add a 1-based logic `frame`.
The allowlist is in `scripts/main.lua`; `mission_command` invokes the copied mission
runtime. Shallow `--config` overrides replace these lists. Asset paths resolve against
the generated benchmark mod; add assets to the source benchmark folder before running.
Unconfigured feature requests are explicitly marked unsupported.

Budgets are a proposal: input 0.25 + logic 4.75 + draw recording 3.33 = 8.33 ms.
They are not acceptance measurements. Compare checks p95 budget overruns and
regressions greater than 5% or 0.02 ms, rejects missing budget zones, failed/incomplete
runs and unlike scenario/seed/frame/roster/backend/disc/mod/feature metadata. Parallel
worker/GPU durations and nested child zones must not be summed with CPU parent zones.
`--legacy` compares callback-sampled built-in diagnostics for the off/on overhead
experiment; those samples can repeat or skip presented frames and include the same
observer overhead in both runs.

Source checks (no game launch):

```powershell
python -m unittest discover -s tools/bench -p 'test_*.py' -v
lua tools/bench/test_driver.lua
```

Inherited MELEE workload switches are removed, including replay/netplay/training and
shader-test hooks. The selected MELEE_BACKEND is retained; every scenario starts at
render scale 1/MSAA 1 and overrides those only through its data file. Reports include
a workload fingerprint of effective environment, full scenario configuration
(including setup/events) and benchmark bundle file contents. Unlike or missing
fingerprints fail comparison; profiler enable/output paths are excluded for off/on.
