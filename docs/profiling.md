# Native profiling and repeatable benchmarks

Run from the workspace root after the integrator rebuilds Aurora with the carried
profiler patch and builds the game through the normal wrapper:

```powershell
python tools/bench/run.py baseline --iso C:/path/vanilla.iso --profiler both
python tools/bench/run.py steady_worst --iso C:/path/ace.iso --mods-dir C:/path/mods
python tools/bench/run.py rollback_worst --iso C:/path/ace.iso --mods-dir C:/path/mods
python tools/bench/run.py hitch_worst --iso C:/path/ace.iso --mods-dir C:/path/mods
python tools/bench/compare.py REPORT_A REPORT_B
python tools/bench/compare.py BASELINE_OFF BASELINE_ON --legacy
```

Use `--plan` to prepare assets and inspect launch configuration without launching.
Defaults are 1800 logic frames and seed12345, visible1066x600 at(-1080,-360), turbo
off and uncapped presentation. A60Hz logic frame differs from an interpolated
120Hz present. Read [the harness guide](../tools/bench/README.md) for roster
admission, CPU control, scenario configuration, timeout handling and partial coverage.

Results include report.json, profile.json, summary.txt, logs and event/hitch traces
under `_build/bench/<scenario>/<timestamp>-on|off-a<attempt>/`. Bench metadata records
requested and achieved features. Refusal, timeout and incomplete frames are not a
passing measurement; compare rejects them. Synthetic lit/glass geometry is original.
The fallback roster is configured, not proof of the globally heaviest possible set.

## Reading measurements

Reports declare schema_version1. Zones are milliseconds; counters use their native
units (heap/snapshot bytes, instructions, rollback frames). Count, mean and max are
exact. Nearest-rank p50/p95/p99 are exact up to4096 samples per ID/256 per identity,
then estimates from deterministic Algorithm R reservoirs over the whole run.
`percentile_scope=deterministic_run_reservoir` states that distinction. When named
identity storage fills, later identities contribute to a per-zone mixed distribution
with `detail=4294967295`; this is an aggregate bucket, not an object ID. Its count,
mean and max remain exact for those mixed observations, and its percentiles use the
same reservoir rule. `detail_aggregated` counts observations routed there;
`detail_overflow` counts observations that could not be stored. `label_omitted`
counts name registrations omitted when label storage fills; existing names stay
stable. Inspect these diagnostics, trace sampling/overwrites, GPU dropped zones
and GPU dropped frames. Missing GPU measurements mean unavailable or unobserved,
not zero milliseconds. Fighter phase details encode `(port<<16)|character`, ports1..6.

Zone times are inclusive. Recursive animation and fighter phases nest; render/audio
threads overlap the game thread. Do not sum parents and children or parallel threads.
Draw statistics describe callback walks; render-worker samples describe queue jobs,
not necessarily one whole rendered frame. `frame` is content-frame wall time;
`frame_work` subtracts same-thread intentional pacing. Hitch detection uses work time,
default16.6667ms, so ordinary60Hz pacing does not repeatedly trigger a120Hz alarm.
The8.33ms subsystem allocation in tools/bench/budgets.json is a proposal.

GPU frame/pass durations use optional WebGPU timestamp queries. This local Dawn's
D3D11 backend does not expose TimestampQuery; D3D12 conditionally does. D3D12 has an
existing32-bit instability warning: backend acceptance remains an integrator check.
CPU submit/wait never substitutes for GPU execution. Pass labels identify custom
post shaders; EFB includes combined surface/material work, not independent timing
of each fighter shader. Upload passes expose texture and mesh/uniform GPU duration.

Aurora results arrive asynchronously. Their CPU X slices end at callback receipt;
GPU C counter tracks contain duration_ms and source render_frame, without inventing
GPU/CPU clock synchronization. Reset excludes synchronous scopes from the earlier
generation, but queued Aurora work/readbacks arriving after reset can enter the new
measurement. Thus the benchmark boundary for those external samples is callback
arrival, and initial samples may include warmup work. Report commands produce live
views rather than one atomic snapshot. Late readbacks cannot enter an already dumped
hitch trace.

## Controls and traces

`MELEE_PROFILER=1` enables the default native collector. Set MELEE_PROF_REPORT and
MELEE_PROF_TRACE to output paths, MELEE_PROF_HITCH_MS to a threshold. Profiling/GPU
feature requests must be present at startup for timestamp capability negotiation.
The Quickref environment table also lists MELEE_PROF_GPU, MSAA and test rollback.

Console commands: `prof on`, `prof off`, `prof reset`, `prof report`, `prof trace 8`,
`prof hitch 20`. Lua uses `gd.prof("trace 8")`; gd.perf retains old fields and adds
`profiler` with nested zone/counter/identity distributions. Use `gd.perf(n, false)`
for frequent frame-history sampling: it retains the legacy frame, FPS, target and
shader fields but omits `profiler`, avoiding reservoir copies, percentile sorting
and identity-table construction. For example, `gd.perf(1, false).frames[1]` reads
the latest frame. Full `gd.perf(n)` and `prof report` belong at report boundaries
or coarse intervals; the cheap path still constructs the requested legacy tables,
and its runtime cost has not been measured.

An explicit trace selects recent content frames; automatic hitches retain two neighbours on each side when
available, rate limited to one per120 frames. Native event history is bounded to
131072 admitted events/120 content frames. To preserve hitch neighbourhoods under
repetitive callback traffic, the collector retains the first eight events below
0.25 ms per ID/content frame, every span of at least 0.25 ms, and every frame span.
This samples trace events only: zone/counter aggregates and detail distributions
still receive every observation. `event_sampled` counts intentional omissions;
`event_overwrites` counts admitted events evicted after capacity is exhausted.
A sufficiently dense stream of significant spans can still overwrite history.
Trace metadata records `small_event_limit_per_id_frame=8` and
`always_retain_ms=0.25`.

Retained events include `last_script_call`, `last_spawn` and `last_area` when known.
These strings name the last observed Lua API and spawn/area request at event
collection, truncated to 63 bytes. They help correlate a hitch with room loading
or an enemy, but do not prove that request caused it. Asynchronous Aurora samples
use context at callback arrival, which can differ from the initiating frame.
Numeric requests may carry the API name rather than an object name.

The `pipeline_skips` and `pipeline_waits` counters count Aurora skip/wait callbacks
while collection is enabled. Each callback records value 1, so the counter's
`count` is the number of occurrences, rather than its mean or max. Wait duration
also contributes to the pipeline compile timing zone. A skip means compilation
continued asynchronously and the draw could appear later; it is not a completed
warm-up. Correlate these counters with `pipeline skip`/`pipeline wait` log lines.

Game log lines carry `[frame=N ms=M]`, including when profiling is disabled.
`N` advances at the content-frame begin hook; `M` is monotonic elapsed milliseconds
since logger initialization. `prof reset` restarts the diagnostic frame counter,
so timestamps remain useful across that boundary. Log parsers that match the start
of a message should allow this prefix. Crash-tail lines retain it too.

Open the JSON using Perfetto's Open trace file
at https://ui.perfetto.dev or a Chrome Trace Event compatible viewer.

## Extending instrumentation

Add a stable numeric ID/name to pc/platform/gw_profiler.h and gw_profiler.c. Native C
uses GW_PROF_ZONE(ID), or balanced gw_prof_begin(ID,detail)/gw_prof_end(). Native C++
needs an RAII wrapper. Game code uses profiler_game.h scalar ProfBegin/ProfEnd calls;
never send strings/native pointers across the PPC boundary. Gate identity work with
ProfEnabled. Register native identity labels with gw_prof_detail_name. Native host
code can call `gw_prof_context(kind, name)` before a diagnostic request: kind 0 is
the last Lua API, 1 the last spawn, and 2 the last area operation. The collector
copies these names into retained events; keep them descriptive and avoid private
paths. Realtime audio
uses gw_prof_try_cpu_completed and drops samples on contention rather than blocking.

New scenario JSON files go in tools/bench/scenarios. Specify roster, mode, stage,
features/setup and frame-indexed events using the Lua driver's allowlist. Extend the
allowlist/driver when adding an API, retain requested/applied/refused statuses and
report the achieved roster. Avoid treating a request as proof that a load admitted.

Tracy0.14.1 client is vendored under pc/third_party/tracy. GW_PROF_TRACY=1 opts into
the development build backend. Default builds start no Tracy worker. GW_RELEASE_BUILD
rejects it and release scanning rejects its embedded marker. Native bounded collection
is independent of Tracy. Its optional allocator/thread/network overhead is additional.

## Acceptance

Headless checks: Python harness tests, Lua test_driver.lua, profiler contract tests,
and libclang syntax parsing. Native fixture/registered tests, on/off replay/SyncTest
parity, six-fighter admission, shader execution, GPU timing and measured overhead
require the integrator's builds/runs. The disabled path returns before clocks, locks,
TLS access and allocations for zone/counter collection, but still executes a
load/branch and scalar game shims. The content-frame begin hook also advances the
diagnostic log frame counter while collection is disabled.
Enabled uncontended pairs are estimated sub-microsecond; no measured cost is claimed.
See `_build/tmp/codex-profiler-bench-report.md` for evidence and exact acceptance steps.
