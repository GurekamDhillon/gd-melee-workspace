# Perf baseline — 2026-09-21

The first profile of the port. Deliverable is the measurement; nothing was optimised.

**Headline: the port runs at ~56 fps on vanilla and ~52 fps on Akaneia, not 60.** The game
thread does ~1.3 ms of game logic per frame and then waits. The long pole is aurora's FIFO
command-processor thread, and ~85% of *that* is one function: `fifo::reuse_array_upload`,
which memcmps whole multi-megabyte vertex-array snapshots on every cache miss.

## How it was measured

Build: melee `agent/perf` (pc-port `b9e4d27f5` + instrumentation), aurora RelWithDebInfo
(`/O2 /Ob1 /DNDEBUG`) from the shared `_build/ax86m`. Machine: RTX 5070, 144 Hz primary display,
no other game running.

Scenes (45–50 s runs, sampling from 15 s in, i.e. mid-match), via `_build\selftest.ps1 -ExeDir`:

* vanilla: `mode=vs;p1=fox/cpu9;p2=falco/cpu9;p3=marth/cpu9;p4=ganondorf/cpu9;stage=battlefield`, `-NoMods`
* Akaneia: `mode=vs;p1=ck:38/cpu9;p2=ck:39/cpu9;p3=ck:36/cpu9;p4=fox/cpu9;stage=battlefield`
  (Sonic, King Dedede, Charizard: three interpreted m-ex movesets)

Instruments (all env-gated, off by default):

* `MELEE_PROFILE=1` — the existing frame profiler (`shim_vi.c`): percentiles, split, histogram
  every 180 frames. Extended this session with a `present` split (`pace_wait` vs `submit` =
  `aurora_end_frame`) and `texobj inits/frame`.
* `MELEE_PROFILE_SAMPLE=<start s>` — **new**: a sampler thread that suspends every thread of the
  process ~1000×/s, records EIP (plus, for samples outside the exe, the nearest melee-pc.exe
  return address on the stack, so waits are attributed to their caller) and rewrites
  `melee-pc.samples` every 5 s.
* `tools/port/prof_report.py <samples>` — **new**: resolves against `melee-pc.map`, per thread,
  with idle (ntdll/KERNELBASE) separated from busy.

## Frame time

| | p50 | p95 | p99 | max | ≈ fps (1000/p50) |
|---|---|---|---|---|---|
| vanilla, 4 CPUs | 17.8–18.0 ms | 18.8–19.6 | 21.1–23.8 | 30–33 | **56** |
| Akaneia, 3 m-ex + Fox | 19.3–19.4 ms | 20.8–20.9 | 27.7 | 33.1 | **52** |

Ranges are across successive 600-frame windows (runs 2 and 3). The histogram has **zero** frames
under 16 ms on either disc. The frame driver's own comment records p50 = 16.67 when the pacing
landed, so this is a regression since then, not how the port has always been.

Split (vanilla; Akaneia is the same shape):

```
game=1.24  present=16.56  events=0.01  begin=0.05
present:  pace_wait=0.00  submit=16.55     <- aurora_end_frame blocks
texobj:   inits/frame=313 (Akaneia 296)
```

`pace_wait = 0` means `gw_pace_field` never waits: by the time it runs, the previous
`aurora_end_frame` has already eaten the whole budget. The port's own pacing is not the problem.
(`game_cpu` in the existing report is meaningless: `GetThreadTimes` has 15.6 ms granularity, so it
reads 0 or 15.62. Use `QueryThreadCycleTime` if that line is to be kept.)

## CPU profile, per thread

### vanilla

| thread | busy | what |
|---|---|---|
| aurora FIFO / command processor | **80.9%** ≈ 14.5 ms/frame | `fifo::reuse_array_upload` **85.6%** of busy (≈ 12.4 ms/frame); `max_index_for_attr` 0.8, `push_gx_draw` 0.7, XXH3 ~1 |
| game (frame) thread | 20.6% ≈ 3.7 ms/frame | `texture::sweep_object_caches` 32.8% + absl iterator helpers under it (`CrashIfIteratorIsInvalid` 10.0, `assert_is_full` 5.2, `operator==` 4.2, `AssertSameContainer` 2.4) = **~55% ≈ 2.0 ms/frame**; `gw_pace_field` 7.3; `__aulldiv` 6.8; `gw_os_run_alarms` 1.6; `PSMTXConcat` 1.4 |
| Dawn render worker | 9.5% | webgpu_dawn 82%, d3d11 6% |
| d3dcompiler (pipeline warm-up) | **97.8%** | `d3dcompiler_47.dll` 94% — the seed warm-up compiling its 4814 pipelines in the background for minutes |
| NVIDIA driver thread | 2.6% | `nvwgf2um.dll` |

Game-thread idle, by nearest caller: **71% in `std::atomic::wait`** (aurora waiting for the FIFO
thread to drain), 25% in `gw_pace_field`'s Sleep.

### Akaneia

| thread | busy | what |
|---|---|---|
| aurora FIFO | **84.1%** ≈ 16.3 ms/frame | `reuse_array_upload` **83.5%** (≈ 13.6 ms/frame) |
| game thread | 17.5% ≈ 3.4 ms/frame | sweep family ~58% ≈ 2.0 ms; `PSMTXConcat` 5.3; `SetupEnvelopeModelMtx` 1.7 |
| d3dcompiler | 98.0% | as above |

**The PPC interpreter is ~0.2% of the game thread's busy time** (`gw_ppc_*` + `gw_mex_*` ≈ 4 of
~1750 busy samples) with three interpreted fighters on screen. The extra ~1.5 ms/frame Akaneia
costs is the FIFO thread doing more of the same, not the interpreter.

## The two hot spots, explained

### 1. `fifo::reuse_array_upload` (aurora `lib/gx/command_processor.cpp:448`) — port-added code

For every indexed attribute of every draw whose cached range is shorter than the max index it
references, it looks the array up in `sArrayUploads` and then
`memcmp(snap, array.data, it->second.size)` — the **whole stored snapshot**. The port's
`GXSetArray` shim reports a MEM1 array's size as "to the end of MEM1", and `push_gx_draw` grows
snapshots geometrically (×2) up to that size, so snapshots are routinely megabytes. The sampled
EIP confirms it: 6,898 of 6,900 samples land on a single instruction, an inlined word-compare loop
(`mov eax,[ecx]; cmp eax,[edx]; jne`).

**Fix (not applied — needs an aurora rebuild in the shared `_build/ax86m`):** compare only the
`needed` bytes and cache that sub-range:

```cpp
if (snap == nullptr || std::memcmp(snap, array.data, needed) != 0) return false;
array.cachedRange = {it->second.offset, needed};   // not the whole snapshot
```

Same semantics (reuse only when every referenced byte is identical; a later draw that needs more
re-checks the larger prefix), O(needed) instead of O(snapshot).

### 2. `texture::sweep_object_caches` (aurora `lib/gx/texture.cpp:468`)

`HSD_TObjSetup` builds a stack `GXTexObj` and calls `GXInitTexObj` for every textured draw every
frame; aurora mints a fresh `texObjId` per init (`GXTexture.cpp:58`) and keeps a cache entry per id
for `ObjectCacheIdleFrames = 600`. At ~313 inits/frame that is **~188k live entries**, all walked
by `sweep_object_caches` every frame, and `/Ob1` leaves absl's per-step iterator helpers as real
calls. ~2 ms/frame on the game thread; hidden today behind the FIFO wait, and pure waste either way.

## Recommendations, ranked by expected win

1. **Fix `reuse_array_upload` (above).** Expected: FIFO thread from ~14–16 ms to ~2–4 ms per
   frame, which puts the frame back under 16.67 and the port back on its pacing: **56/52 → 60 fps**.
   Three lines; verify with the ACE ext:338 (GrMe) case the code was written for.
2. **Stop churning the texture object cache.** Cheapest: sweep every 60 frames (or a bounded slice
   per frame) instead of the whole map every frame. Better: have `HSD_TObjSetup` reuse a persistent
   `GXTexObj` per TObj (re-init only when image/format/wrap/filter change), which removes the
   188k-entry map entirely. ~2 ms/frame game-thread CPU.
3. **Build aurora with `/Ob2`** (RelWithDebInfo defaults to `/Ob1`, which inlines only
   `__inline`-marked functions; absl and aurora's containers assume real inlining). Broad,
   low-risk win on both aurora threads. One cmake flag; needs the full aurora relink.
4. **Throttle the pipeline-seed warm-up.** It holds one core at ~98% in `d3dcompiler_47` for
   minutes. Fine on this machine; on a 4-core laptop it competes with the FIFO and render workers
   during the first matches. Lower its thread priority, or stop warming once a match starts.
5. **Replace `game_cpu` in the PROF report** with `QueryThreadCycleTime` — the current number is
   quantised to 15.6 ms and misleads.
6. **Leave the PPC interpreter alone.** ~0.2% of the game thread. See the gate verdict below.

## `gw_ppc_static_native`'s 0x80300000 gate — verdict

What it does: before every interpreted load/store (and every pointer argument crossing the
bridge), `gw_ppc_static_native(ea)` decides whether `ea` is a game static (whose storage lives
in the native exe, not MEM1). Below 0x80300000 it returns at once; above it, it binary-searches
the bridge table for an exact data-object match and then `gw_mex_bridge_guest_data` for an
interior match (itself range-gated to 0x803B7280..0x804DEA9C). `docs/HANDOFF.md` §1 notes the main
heap starts near 0x806A0000, so every fighter-struct access pays the search.

**Perf: irrelevant.** The whole interpreter is ~0.2% of the game thread with three m-ex fighters
active. Tightening the gate to the statics' actual range `[0x803B7280, 0x804DEA9C)` (both bounds)
would be correct and trivially cheaper, but it would not move any frame-time number.

**Correctness — worth a follow-up, out of scope here:** the arena starts at `gw_mem1 + 0x3100`
(`shim_os.c`), so MEM1 *below* the main heap, including 0x803B7280..0x804DEA9C, is ordinary
allocatable memory in the port (framebuffers, FIFO, audio and the fixed heaps are carved from the
arena). On hardware that range *is* the statics and is never handed out. Anything interpreted
code touches inside that window is silently redirected to a native static. No log line in these
runs shows a guest address there, so there is no evidence it fires today; the robust fix is to
reserve that window out of the arena (it mirrors hardware exactly, where `__OSArenaLo` sits past
the DOL's `.bss`).

## Reproduce

```powershell
$env:MELEE_PROFILE="1"; $env:MELEE_PROFILE_SAMPLE="15"
.\_build\selftest.ps1 -Scene "mode=vs;p1=fox/cpu9;p2=falco/cpu9;p3=marth/cpu9;p4=ganondorf/cpu9;time=180;stage=battlefield" `
  -Disc vanilla -NoMods -Seconds 45 -Tag perf-vanilla -ExeDir C:\gdm\_build\agents\perf
python tools/port/prof_report.py _build/runs/perf-vanilla/melee-pc.samples -n 25
```
