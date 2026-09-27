# Aurora indexed-array comparisons on the FIFO worker

**2026-09-26 — source investigation and proposed patch only.** This note supplements
`_research/pc-matrix-palette.md` and the older `_research/perf-baseline-2026-09-21.md`.
The latter measured an older, whole-snapshot `reuse_array_upload`; the current source
already compares only the required prefix and has an SSE2 `bytes_equal`. Current local
source baseline: workspace `7de8c64e0169243f4699f16ff0f74639875146d5`, game
`960cf3da817f719f682e6bc7ccaa3193cfc69c7c`. Runtime timings below are from the
user's alpha profile and existing sample files; no build or game run was made here.
Only this note was written.

## Finding

`fifo::bytes_equal` compares **indexed GX attribute-array memory** against a byte
snapshot in the current Aurora frame's GPU storage staging arena. It does not compare
display-list bytes, cache parsed display lists, or deduplicate draw commands. The
purpose is to reuse a prior storage upload when `GXSetArray` switches back to an
array, or to retain an upload after `GXInvalidateVtxCache` if its source bytes are
still equal. This saves storage capacity and upload work, including a documented
ACE GrMe case where repeated copies of one 100 KiB array exceeded the 8 MiB frame
storage limit (`command_processor.cpp:469-478`).

### Exact path (paths below are under `melee/`)

| Step | Source | Effect |
|---|---|---|
| Game submits a piece | `src/sysdolphin/baselib/pobj.c:1278-1284` | `setupArrayDesc` binds indexed arrays; `GXCallDisplayList` submits that POBJ's command bytes. |
| Array binding | `src/sysdolphin/baselib/pobj.c:450-455`; `pc/platform/shim_gx.c:647-658`; `extern/aurora/lib/dolphin/gx/GXGeometry.cpp:218-235` | The shim supplies the pointer, stride, big-endian flag, and a bound of `[base, end of MEM1)` for MEM1 (otherwise `UINT32_MAX`). That bound is **not** the amount a draw reads. |
| FIFO submission and worker | `extern/aurora/lib/dolphin/gx/GXDispList.cpp:49-62`; `extern/aurora/lib/gx/fifo.cpp:68-100,111-119`; `extern/aurora/lib/gx/command_processor.cpp:250-256,338-347` | Display-list bytes are copied into the FIFO and published; the worker parses them. The `GX_CMD_CALL_DL` case at `command_processor.cpp:312-317` ignores nested calls, so it is not a display-list cache. |
| Invalidation | `src/melee/gm/gmscene.c:1046-1057`; `src/sysdolphin/baselib/pobj.c:303-304`; `extern/aurora/lib/dolphin/gx/GXGeometry.cpp:375`; `extern/aurora/lib/gx/command_processor.cpp:319-330` | The normal render path issues `GXInvalidateVtxCache` before scene drawing. Aurora marks existing array snapshots stale. `PObjLoad` has only a commented-out per-POBJ invalidation; the Aurora comment saying “nearly every PObj” is not established by these call sites. An opcode counter or FIFO trace must settle the actual frequency, including any raw `0x48` in display lists. |
| Draw's byte requirement | `extern/aurora/lib/gx/command_processor.cpp:448-466,555-599` | For each indexed attribute `GX_VA_POS..GX_VA_TEX7`, scan the draw's index stream; `needed = maxIndex * stride + attributeElementBytes`. `revalidate_array` runs, then a short local cache uses its range; otherwise `reuse_array_upload` tries a prior upload by source pointer. Failed reuse copies `pushSize` bytes, geometrically grown for bounded MEM1 arrays. |
| Comparison A | `extern/aurora/lib/gx/command_processor.cpp:516-538` | `sArrayUploads[array.data]` points at an earlier storage upload. `bytes_equal(snapshot + from, live + from, needed - from)` checks the required prefix, excluding a prefix already validated for this `AttrArray` and storage offset. The map key is just the native pointer; content comparison protects reused addresses and modified data. |
| Comparison B | `extern/aurora/lib/gx/command_processor.cpp:540-550` | After invalidation, `bytes_equal(snapshot, live, cachedRange.size)` revalidates the entire local cached prefix. Failed equality discards that range. |
| Equality implementation | `extern/aurora/lib/gx/command_processor.cpp:480-514` | Four unaligned SSE2 16-byte loads per 64-byte iteration, then 16-byte chunks and a `memcmp` tail; an early difference stops the scan. Equal static data forces a full scan. |
| Lifetime | `extern/aurora/lib/gfx/recording.cpp:603-605,1209-1223`; `extern/aurora/lib/gx/fifo.cpp:175-180,370-405` | `storage_data` resolves a range in the **current** frame packet. Per-array `cachedRange` clears at recording end and around frame replay. `sArrayUploads` itself currently persists; an old offset can accidentally address unrelated bytes in a later frame packet. The proposed patch scopes it to one frame. |

The raw indexed vertex stream inside each display list is independently uploaded
by `draw_prim` (`command_processor.cpp:716-766`). The comparison concerns the
**array values addressed by that stream**, such as position, normal and texcoord
records, not the stream itself. `max_index_for_attr` scans the stream and is the
next reported hotspot; `copy_xf_data` (`command_processor.cpp:285-309`) copies
indexed transform data and does not call `bytes_equal`.

## Frequency and bytes: what the evidence does and does not measure

The saved alpha samples, resolved read-only with `tools/port/prof_report.py`, show
the Aurora FIFO thread at 71.7% busy for `alpha-prof-sora-idle` and 16.5% for
`alpha-prof-marth-idle`. Of busy samples, `bytes_equal` has **5,459/8,346 = 65.4%**
for Sora and **754/1,897 = 39.7%** for Marth. Sora's next named functions are
`max_index_for_attr` **4.86%**, `push_gx_draw` **2.36%**, and `copy_xf_data`
**2.22%**. The user's reported approximately **12 ms/frame** versus **1 ms/frame**
is a separate timing estimate, consistent in direction with those samples; sample
percentages alone do not give exact per-frame milliseconds.

The current asset report `_build/tmp/codex-palette/sora-default-final-report.json`
contains **804 POBJs / 804 primitives** across the whole Sora asset after batching,
including **619** POBJs and **46,011 corners** for `body_highShape` submesh 0.
Those are asset totals, not a measured count of visible calls in one frame; hidden
eyes, mouths, alternate parts, culling and render passes affect the actual count.
Each processed draw can examine each enabled indexed attribute. Therefore the
opportunity scales with processed primitive calls × indexed attributes × rebinding
or invalidation events, rather than with 804 alone.

More precisely, `reuse_array_upload` can run at most once per enabled indexed
attribute per unmerged draw, and only when its local cached prefix is shorter
than `needed`. `revalidate_array` is called for those attributes (also in the
merge check at `command_processor.cpp:746-763`), but enters `bytes_equal` only
when that particular bound array was marked stale. For illustration, **804
visible, single-pass pieces with exactly three indexed attributes** would allow
up to **2,412** reuse attempts before cache hits; neither the visibility/pass
assumption nor the three-attribute assumption is measured for this scene.

The **exact compared-byte formulas** are:

```
reuse_array_upload:  n = needed - from
  needed = max_index_for_attr(...) * array.stride + attribute element bytes
  from = cachedRange.size only when that local cache points at the same upload;
         otherwise 0
revalidate_array:    n = cachedRange.size, once when that array is stale
frame total:         sum(n) over both call sites, including repeated equal scans
```

`pushSize` may be much larger than `needed` because of geometric growth, but
current `reuse_array_upload` compares only `needed - from`; the 2026-09-21
whole-snapshot megabyte comparison is already fixed. Neither the sample file nor
the asset reports record comparison calls, per-array strides/max indices, equal
versus unequal outcomes, or `sum(n)` per frame. Thus **there is no defensible
numeric bytes-per-frame or calls-per-frame result yet**. Do not turn 12 ms into
a byte count using an assumed bandwidth. A follow-up profile should count, per
real frame and per call site: calls, bytes requested, bytes actually scanned to
the first mismatch, equal calls, and reuse hits; include array pointer and
attribute only in an optional diagnostic trace. Count replay frames separately.

## Proposed fix and correctness argument

Use a **frame- and GX-invalidation-scoped validated-prefix table** alongside the
existing upload map. An upload validates all bytes copied. After an invalidation,
the first use of a `(source pointer, storage offset, prefix)` still compares live
bytes; subsequent POBJ rebindings in that same invalidation epoch can reuse the
verified prefix without scanning it again. If a later draw reaches farther into
the snapshot, compare just the new tail. Clear both tables at the frame boundary;
a prior frame's storage offset must never be treated as a current-frame snapshot.
This directly addresses repeated equal comparisons and keeps the existing exact
byte check when data may have changed.

The contract is important: **every CPU rewrite of a currently bound indexed
array before another draw must issue `GXInvalidateVtxCache`**, or bind a different
source/version. That is already necessary for the existing local `cachedRange`
fast path, which skips comparisons until invalidated. The proposal does not use
a hash as proof of equality: a hash-first/full-compare scheme still reads every
byte on equal static arrays, then reads it again on a match, so it is likely
worse for this profile. Pointer alone cannot prove content stability across an
invalidation or frame. If an asset path cannot satisfy the invalidation contract,
keep its exact comparison path (or introduce an explicit owner-held immutable
token plus generation bumped on every write/free); never silently classify all
MEM1 pointers as immutable. `GXInvalidateVtxCache` is coarse, so the first check
after it remains conservative.

### Proposed diff (illustrative, **not applied**)

```diff
diff --git a/extern/aurora/lib/gx/command_processor.cpp b/extern/aurora/lib/gx/command_processor.cpp
--- a/extern/aurora/lib/gx/command_processor.cpp
+++ b/extern/aurora/lib/gx/command_processor.cpp
@@
 DrawCache sDrawCache;
+// Valid only in this recording frame and since the last GXInvalidateVtxCache.
+struct ValidatedArrayPrefix { u32 offset; u32 size; };
+static std::unordered_map<const void*, ValidatedArrayPrefix> sValidatedArrayPrefixes;
@@
     case CP_CMD_INVAL_VTX: {
+      sValidatedArrayPrefixes.clear();
       for (auto& array : g_gxState.arrays) {
@@
 static bool reuse_array_upload(AttrArray& array, u32 needed) noexcept {
   const auto it = sArrayUploads.find(array.data);
@@
   const uint8_t* snap = gfx::storage_data(it->second);
-  u32 from = 0;
-  if (array.cachedRange.size != 0 && array.cachedRange.offset == it->second.offset) {
-    from = array.cachedRange.size;
-  }
+  const auto valid = sValidatedArrayPrefixes.find(array.data);
+  const u32 verified = valid != sValidatedArrayPrefixes.end() &&
+                               valid->second.offset == it->second.offset ? valid->second.size : 0;
+  const u32 from = std::min(verified, needed);
   if (snap == nullptr ||
       !bytes_equal(snap + from, static_cast<const uint8_t*>(array.data) + from, needed - from)) {
     return false;
   }
+  sValidatedArrayPrefixes[array.data] = {it->second.offset, std::max(verified, needed)};
   array.cachedRange = gfx::Range{it->second.offset, needed};
@@
 static void revalidate_array(AttrArray& array) noexcept {
@@
   array.stale = false;
   const uint8_t* snap = gfx::storage_data(array.cachedRange);
-  if (snap == nullptr ||
-      !bytes_equal(snap, static_cast<const uint8_t*>(array.data), array.cachedRange.size)) {
+  const auto valid = sValidatedArrayPrefixes.find(array.data);
+  const bool known = valid != sValidatedArrayPrefixes.end() &&
+                     valid->second.offset == array.cachedRange.offset &&
+                     valid->second.size >= array.cachedRange.size;
+  if (snap == nullptr ||
+      (!known && !bytes_equal(snap, static_cast<const uint8_t*>(array.data), array.cachedRange.size))) {
     array.cachedRange = {};
+    return;
   }
+  sValidatedArrayPrefixes[array.data] = {
+      array.cachedRange.offset, known ? valid->second.size : array.cachedRange.size};
@@
       array.cachedRange = gfx::push_storage(static_cast<const uint8_t*>(array.data), pushSize);
+      sValidatedArrayPrefixes[array.data] = {array.cachedRange.offset, pushSize};
       if (sArrayUploads.size() > 4096) {
@@
 void clear_draw_cache() noexcept {
+  // Frame-packet storage offsets and validated source bytes cannot cross frames/replays.
+  sArrayUploads.clear();
+  sValidatedArrayPrefixes.clear();
   if (g_palette.active) {
```

The intended validation gate before applying that diff is to audit dynamic array
writes for the invalidation contract, then compare deterministic draw digests and
per-frame attribute-array bytes across vanilla, Sora idle/moves, shape animations,
ACE GrMe, and frame replay. A write after FIFO publication also needs the existing
drain/lifetime discipline: a generation number cannot repair a race with a live
source pointer. Record exact comparison counters and storage bytes before/after;
the patch is a hypothesis until those checks and an Aurora rebuild/run pass.

## What the 64-matrix palette can save independently

`_research/pc-matrix-palette.md:245-255` predicts **619 → 52 body pieces**, a
**91.60%** reduction in body POBJ calls. The later asset report
`_build/tmp/codex-palette/sora-palette64-final-report.json` also reports
**804 → 148 total** POBJs/primitives, an **81.59%** total reduction; body submeshes
1 and 2 go **38 → 4** and **20 → 2**. Total submitted asset vertices remain
**222,684** and main-body corners remain **46,011**. The palette therefore cuts
per-piece binding, max-index scans, XF/setup and comparison *opportunities*, but
does not remove the bytes needed for unique geometry or guarantee equal savings
in `bytes_equal`.

An explicitly **illustrative** linear-per-POBJ model applied to the user's
12 ms Sora cost gives `12 * (148/804) = 2.21 ms` remaining, or **9.79 ms saved**;
applied only to the approximately 11 ms Sora-minus-Marth increment, it gives
`1 + 11 * (148/804) = 3.03 ms` remaining, or **8.97 ms saved**. A body-only
linear model yields a 91.6% cut in the body's share. These are ceilings for
piece-proportional work, **not forecasts**: visibility, multiple passes, indexed
array identity, `needed` length, repeated scanning of large shared prefixes,
and fixed stage/Fox cost could make the actual gain much smaller. The correct
before/after metric is the measured per-frame `bytes_equal` call/byte count and
worker time with identical scenes. Palette repacking and validated-prefix caching
are complementary; the latter still matters for stage/other fighters and for
the 148-piece Sora asset.

## Five-line summary

1. `bytes_equal` compares live indexed GX arrays with Aurora storage snapshots, not display lists or draws.
2. Two call sites compare `needed - from` bytes on upload reuse and `cachedRange.size` after invalidation.
3. Existing samples support the ~12 ms Sora hotspot; exact comparisons and bytes per frame were not recorded.
4. The proposed frame/invalidation-scoped prefix table removes repeated equal scans while retaining required checks.
5. The 64-slot palette reduces asset pieces 804 → 148 (body 619 → 52); timing savings remain unmeasured.
