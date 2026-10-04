# Aurora GD no-hitch v1 incremental carried patch (2026-10-03)

Upstream Aurora is MIT, vendored revision `cb0e279`. This patch applies to the
port tree at game commit `378d79b20c46452cf43aec45c2d622471ed3a5e6`, **after**
existing surface and profiler patches, rather than to pristine upstream.
It is already reflected in this workspace. Do not apply it twice.

Unlike the older surface/profiler patch files, paths in this patch are relative
to the **game repository root** (`extern/aurora/...`). Commands from workspace:

```powershell
git -C melee apply --reverse --check ../_build/patches/aurora-gd-no-hitch-v1.patch
```

That read-only check passed on the current source (five files, 248 inserted and
15 removed lines). The check performs no writes and no builds. On a separate,
matching fresh game checkout with prior patches already applied:

```powershell
git -C melee apply --check ../_build/patches/aurora-gd-no-hitch-v1.patch
git -C melee apply ../_build/patches/aurora-gd-no-hitch-v1.patch
```

The second pair is a future integrator recipe; this task did not run it. Keep
prior dirty changes. Do not use this patch to replace a directory or reset files.

## Scope and dependencies

- `lib/gfx/pipeline_cache.cpp`: declaration capture/labels, actual CORE seed
  membership/readiness, background tagged prewarming, core/scene-before-offscreen
  scheduling, default asynchronous skip with retained opt-in blocking logs,
  content-origin persistence, immutable learned SQLite snapshot publication/import.
- `lib/gfx/pipeline_cache.hpp`: two capture helper declarations.
- `include/aurora/gfx.h`: CORE tag, warm capture/label/pending/release API and core
  pending/count API, background prewarm documentation.
- `lib/gx/command_processor.cpp`: only the two-line captured-material traversal
  early return. Existing surface support is context, not introduced by this patch.
- New `include/aurora/pipeline_warm.hpp`: generation-safe host-only capture registry.

The baseline was reconstructed from game HEAD plus existing profiler sink header,
profiler include/wait duration call, and current non-capture command processor.
Existing surface, profiler, SSE/palette and other unrelated hunks are excluded.
The no-hitch code uses existing `surfaceProgram` support and `gpu_prof::emit_cpu`;
its prior surface/profiler dependencies must be present and must not be removed.
`PORT_PATCHES.md` records this incremental patch separately.

## Rebuild and acceptance

A matching Aurora rebuild is required before the game link: new capture/core
symbols have no readiness-faking compatibility fallback. Use the workspace's
existing Aurora build wrapper and `tools/port/build.sh` during the authorized
integrator build, preserving bridge fixpoint handling. This task ran neither.

After rebuild, verify matching EXE strings and the full engine no-hitch report's
native plan. Cold maze seed7 walks require zero pipeline-wait lines with default
skip behavior, measured room-entry frames, and readiness release rather than
ceiling. Test declared warm completion, explicit failure/stale-handle cleanup,
core membership only from bundled seed ranks, cross-sandbox learned import and
non-fighter late-draw visibility. `MELEE_PIPELINE_SKIP=0` deliberately enables
legacy blocking for diagnosis; it is not the no-hitch acceptance configuration.
Warm traversal still runs a bounded descriptor preparation on the game thread;
no runtime latency/visual success is claimed by patch reverse-check alone.
