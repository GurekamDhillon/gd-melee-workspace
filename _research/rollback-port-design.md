# Rollback in this port: what must be snapshotted, what it costs, what is not rollback-able

Status: **design only**. Nothing under `src/` or `pc/platform/` was modified. Date: 2026-09-19.
Companion to [`rollback-netcode.md`](rollback-netcode.md), which is the general background (Slippi,
GGPO, determinism hazards). This document does not repeat it. It answers four port-specific
questions with numbers.

Every number below is tagged **[M]** measured, **[D]** derived by arithmetic from a constant read
out of this tree, or **[E]** estimated. Method for each class of measurement is in §0.

---

## 0. How the numbers were obtained

**[M] Static sizes** come from `C:/gdm/_build/melee-pc.map` (link of 2026-09-19 15:55, the same
commit as this worktree). A script read every symbol in section `0003` (`.data` + `.data$r` +
`.data$rs` + `.bss`), sized each as the distance to the next symbol, and attributed it to its
object file. That is **4,812 symbols totalling 1,548,860 bytes** — an exhaustive partition of the
section, not a sample. Section 4 (`.gwfix`, 0x13458 bytes) is the link-time fixup table, read-only
after `gw_apply_fixups` (`gw_runtime.c:30`).

**[M] Timings** come from four small test programs built with the port's own compiler and target
(`C:/gdm/_toolchains/llvm/bin/clang.exe --target=i686-pc-windows-msvc -O2`, and
`/LARGEADDRESSAWARE` where it matters) and run on this machine. They measure: `memcpy` at the
sizes this design actually uses, a scalar 64-bit FNV-1a hash, `GetWriteWatch`, and a DEP
execute-fault round trip. Best-of-N is reported, so these are the *optimistic* end — a real frame
runs with a cold cache and a GPU driver in the process.

**[D] MEM1 layout** is arithmetic over the heap descriptors in `src/melee/lb/lbheap.c:26-44`, the
XFB/FIFO parameters in `src/melee/gm/gmmain.c:147-161`, and the arena bounds in
`pc/platform/shim_os.c:47-70`. The result reproduces the "~11.3 MB main heap" figure written from
observation in `lbheap.c:31-36`, which is a useful cross-check.

**No gameplay run was made.** Two of the numbers this design most wants — interpreted guest
instructions per frame, and dirty MEM1 bytes per frame — can only come from a windowed run with
counters compiled in. Both are flagged **[E]** and §4 milestone 0 is how to turn them into **[M]**.

---

## 1. The snapshot set

### 1.1 The address-space argument (why this set is complete, not merely plausible)

Slippi's savestate is four hand-found guest ranges plus an exclusion list discovered by debugging.
This port can do better, because **it has only four writable arenas, and three of them are
enumerable to the byte**:

| # | Arena | Created at | Enumerable? |
|---|---|---|---|
| 1 | MEM1, 24 MB at a fixed `0x80000000` | one `VirtualAlloc`, `gw_runtime.c:50-51` | yes — and `GetWriteWatch` can name every page written |
| 2 | ARAM, 16 MB | one `calloc`, `gw_runtime.c:63` | yes, same trick if it is re-allocated with `VirtualAlloc` |
| 3 | The exe's `.data`/`.bss` | linker, fixed `/BASE:0x10000000 /DYNAMICBASE:NO` | yes — 4,812 symbols in the map, each with a name and an owning object file |
| 4 | The CRT heap and the native stack | `malloc` inside shims, Aurora, Dawn, SDL3, sqlite, freetype | **no** |

Arena 4 is the only one that cannot be enumerated, and §3.6 argues it holds no simulation state
today — but "argues" is the weak word, and milestone 1 replaces the argument with a test.

So "complete" is a finite, checkable claim: a decision for each of the 4,812 section-3 symbols and
for each page of MEM1 and ARAM. Three independent oracles keep it honest:

1. **Enumeration** (static, runs in CI). Every section-3 symbol is classified include/exclude by a
   rule over its object file plus a small explicit symbol list. A new global in a new object file
   fails the build until it is classified. This is the part that stops the set rotting.
2. **Write-watch differential** (dynamic, cheap). Run one logic frame; `GetWriteWatch` reports
   every MEM1 page written. Any page written but outside the snapshot set is a hole in the set.
   **[M]** This works here for kernel writes too: `fread` and `ReadFile` into a write-watch region
   both register their pages dirty (tested at the real `0x80000000` base in a 32-bit
   `/LARGEADDRESSAWARE` process), so the DVD path cannot sneak past it.
3. **Restore-and-replay** (dynamic, authoritative). Save at frame N, run to N+k, restore N, replay
   the same inputs; every per-frame hash must match the first pass. This is the only oracle that
   catches *native* state that was forgotten, because forgotten native state is exactly what makes
   the replay diverge.

Oracle 2 covers MEM1 exhaustively. Oracle 3 covers everything, but only tells you *that* something
is wrong; the map turns a differing byte into a symbol name, which is what makes it debuggable.

### 1.2 MEM1 — [D] exact carve

| Region | Bytes | Snapshot? |
|---|---:|---|
| lomem OS globals `0x80000000 +0x3100` | 12,544 | no — written once by `gw_init_lomem` (`gw_runtime.c:76+`), constant thereafter |
| 2 × XFB (`GXNtsc480IntDf`, `gmmain.c:159`) | 1,228,800 | **no** — the port presents through Aurora; these are vestigial |
| GX FIFO (`0x40000`, `gmmain.c:160`) | 262,144 | **no** |
| SisLib font work area (`0xC000`, `gmmain.c:188`) | 49,152 | no |
| heap 2 "Seq" (`0x800`) | 2,048 | yes |
| heap 3 "Stay" (`0x51A690`) — IfAll / ItCo / EfCoData preloads | 5,351,056 | **open** — see §3.7 |
| heap 4 "AllM" (`0x64B400`) — lbMemory file cache | 6,599,168 | **open** — see §3.7 |
| heap 6 "Scene" (`0x20`, the m-ex addition) | 32 | yes |
| **main heap** (whatever remains; HSD_MemAlloc, GObjs, fighters, JObjs, particles) | **11,267,664** | **yes** |
| m-ex persist region (`GW_MEX_PERSIST_SIZE`, `shim_os.c:62`) | 393,216 | yes, with a caveat (§3.4) |
| heap 5 "AllA" (`0x96C800`) lives in ARAM, not MEM1 | 9,881,600 | no |

The main-heap figure is a residual: `25,165,824 − 12,544 − 393,216` arena, minus the XFB, FIFO,
SisLib, heaps 2/3/4/6 above, leaves **11,267,664 bytes**. `lbheap.c:31-36` records "about 11.3 MB,
with only about 35 KB in use at match setup" from observation, which agrees.

**Tier 1 snapshot** (main heap + heaps 2 and 6 + persist) = **11,662,960 bytes**.
**Tier 2** adds heaps 3 and 4 = **23,613,184 bytes**, i.e. effectively all of MEM1.

### 1.3 The native game globals — [M] three contiguous runs, 644 KB after exclusions

This is the finding that most changes the shape of the implementation.

Grouping the 4,812 section-3 symbols into runs by origin gives **five runs total, of which exactly
three are game-owned**, because the linker lays out object-file contributions in response-file
order and every `src_*` object is contiguous:

| Run | Offset range in section 3 | Bytes | Contents |
|---|---|---:|---|
| 1 | `0x000000 – 0x065f40` | 417,600 | game `.data` |
| 2 | `0x06ca00 – 0x0d1a40` | 413,760 | game `.bss` |
| 3 | `0x1480a0 – 0x17a23c` | 205,212 | game `<common>` (tentative definitions: `gw_gmMainLib_8045A6C0` 68,160 B, `gw_player_slots` 22,368 B, `gw_lbMemory_804318B0` 1,792 B, …) |

**Total game-owned: 1,036,572 bytes.** The remaining 512,288 bytes are shims, `gw_*` runtime,
Aurora, sqlite, freetype, absl, the CRT and `libs_dolphin` — none of it game state.

**No generated range table is needed.** `rollback-netcode.md` §2.2 proposed either generating
`gw_snap_ranges.inc` from the map or teaching gwtool to emit `.gwdat`/`.gwbss` sections. Neither is
necessary: three `$a`/`$z` bracket symbols in the right objects, or simply three linker-visible
markers, give the ranges directly. What the map *is* still needed for is the **CI check** that the
runs are still three and still contain exactly the expected objects — the contiguity is a property
of the hand-maintained `melee_link_objects.rsp` ordering (`_research/port-dev-quickref.md` warns
that file is hand-maintained), so it must be asserted, not assumed.

**Exclusions.** Fourteen game TUs hold state that must not be rolled back; they account for
**376,704 bytes in 19 coalesced sub-ranges** inside the three runs:

| Bytes | Object | Why excluded |
|---:|---|---|
| 146,944 | `sysdolphin/baselib/sislib_font.c` | glyph/render work area, not simulation |
| 137,184 | `melee/lb/lbaudio_ax.c` | audio, advances on the device clock (§3.1) |
| 33,344 | `sysdolphin/baselib/devcom.c` | host debug transport |
| 25,632 | `melee/if/soundtest.c` | menu-only; excluded to shrink the hash, not for correctness |
| 8,480 | `sysdolphin/baselib/synth.c` | audio |
| 8,192 | `sysdolphin/baselib/axdriver.c` | audio |
| 5,632 | `sysdolphin/baselib/card.c` | host memory card |
| 5,184 | `sysdolphin/baselib/video.c` | VI/XFB |
| 2,432 | `melee/lb/lbdvd.c` | host file I/O |
| 2,240 + 320 | `lbcardnew.c`, `lbcardgame.c` | host memory card |
| 640 / 320 / 160 | `lbmthp.c`, `perf.c`, `lbsnap.c` | movie / perf counters / screenshot |

**Game globals to snapshot: 1,036,572 − 376,704 = 659,868 bytes (644 KB) in about 22 ranges.**

Two exclusions are provisional and milestone 1 must confirm them by differencing, not by reading:
`lbaudio_ax.c` is 137 KB of mixed state and certainly contains some things gameplay reads back
(§3.1); and `sislib_font.c`'s 147 KB is one symbol, so it is all-or-nothing.

### 1.4 The PPC interpreter — [M] 2,904 bytes, and the registers do not need saving

`pc/platform/gw_ppc.c` keeps **all** of its out-of-guest state in section 3, and the map sizes it
exactly:

| Symbol | Bytes | Rollback? |
|---|---:|---|
| `gw_ppc_range_lo` / `gw_ppc_range_hi` (`GW_PPC_MAX_CODE_RANGES` 256) | 2,048 | **yes** — mutable at runtime (§3.3) |
| `gw_ppc_m` (`gw_ppc_machine`: 32 GPR + 32 × 64-bit FPR + LR/CTR/XER/CR/PC + resolver, ctx, code_lo, code_hi) | 424 | see below |
| `gw_ppc_describe.buf` | 320 | no (log formatting) |
| `gw_ppc_entry[16]` | 68 | no (diagnostic call chain) |
| `gw_ppc_range_count`, `gw_ppc_depth`, `gw_ppc_depth_logged`, `gw_ppc_symbolizer`, `gw_ppc_trace_fp`, … | 44 | mixed |

**The register file is not simulation state at a frame boundary, and the code says why.**
`gw_ppc_call` (`gw_ppc.c:1416`) opens with `gw_ppc_machine saved = gw_ppc_m;` and closes with
`gw_ppc_m = saved;` — a full save/restore for re-entrancy — and it `memset`s the context before
every entry (`gw_ppc.c:1462`). So outside a call, `gw_ppc_m.cpu` is dead: whatever it holds is the
residue of the last call, and the next call overwrites it. The snapshot therefore does not need
it, **provided the snapshot point is one where no interpreted call is on the stack**. That is a
one-line invariant, and it should be an assert, not a comment:

```c
assert(gw_ppc_depth == 0);   /* at every gw_snap_save / gw_snap_load */
```

`gw_ppc_depth` is zero at the top of a logic frame today, because every entry into the interpreter
is a hook dispatched from inside a GObj proc and returns before the proc does. Nothing enforces it.

`gw_ppc_m.code_lo/code_hi` and the resolver pointer *are* live state — they are set by
`gw_ppc_set_bridge`, which the runtime calls once at install (`gw_mex_ftfunction_runtime.c:2103`,
with `code_lo = code_hi = 0` so all code lives in the added ranges). The range table is the live
part (§3.3).

**Verdict: 2,904 bytes, of which ~2,100 matter. The interpreter is the cheapest thing in this
design to snapshot and the most expensive thing to *re-execute* (§2.3, §3.3).**

### 1.5 The allocator — MEM1 does the work for us, except for four native words

`src/melee/lb/lbheap.c` runs two different allocators and they behave very differently under
rollback.

**Heap 0, the main heap — type 0, OSAlloc. Fully in-band.** `HSD_CreateMainHeap` →
`OSCreateHeap` → Aurora's `extern/aurora/lib/dolphin/os/OSAlloc.cpp`. Every allocation carries a
32-byte `Cell` header (`prev`, `next`, `size`, `owner`) immediately before the payload, and the
free list and allocated list are doubly-linked lists **of those in-heap cells**. `sHeapArray`
itself is placed at `arenaStart` — inside MEM1 (`OSAlloc.cpp:254`). Consequence:

> **Restoring MEM1 restores the main heap's free lists exactly, and un-doing an allocation costs
> nothing.** A rollback that removes an `HSD_MemAlloc` does not leak: the cell header, the free
> list links and the allocated list links are all bytes inside the snapshotted region, so they
> revert with it.

The only OSAlloc state outside MEM1 is four native words — `sHeapArray`, `sNumHeaps`,
`sArenaStart`, `sArenaEnd` (`OSAlloc.cpp:35-38`) — all fixed after boot, plus one that is **not**
fixed:

> `gw___OSCurrHeap` (`shim_os.c:29`, 4 bytes, in `shim_os.obj`) is the current-heap selector that
> `HSD_SetHeap`/`HSD_GetHeap` move. It is live simulation state, it sits in an object file that is
> otherwise entirely excluded, and it is four bytes. **It must be named explicitly in the include
> list.** It is balanced across a frame today (every `HSD_SetHeap` in `lbHeap_80015BD0` has a
> matching restore), so this is belt-and-braces — but it is exactly the kind of four-byte omission
> that produces a desync nobody can find.

**Heaps 2, 3, 4, 6 and the ARAM heap — type 1/2/3/4, lbMemory. Bookkeeping is native.**
`lbMemory_804318B0` is a `struct Allocator` of 0x6F0 bytes (`src/melee/lb/lbmemory.c:24-46`),
measured in the map as `gw_lbMemory_804318B0`, **1,792 bytes in `<common>`** — i.e. it is already
inside game run 3 and is snapshotted for free. It holds `x8_mem[0x83]` allocation records, the
free-handle and free-mem lists, `x630_num_allocs`, and the six heap handles. Rolling it back rolls
back those heaps' bookkeeping correctly.

Except: `struct Allocator` embeds `struct LBMgr x6A0_mgr`, whose first member is an **`OSAlarm`** —
the chunked background copy. See §3.5; this is a real problem, not a footnote.

**HSD ObjAlloc pools.** The pools themselves are main-heap MEM1 (`objalloc.c:50`, `HSD_MemAlloc`),
the per-type `HSD_ObjAllocData` headers and `alloc_datas` are native and live in run 1/2
(`objalloc.c` 96 B, `gobj.c` 96 B). Both halves are in the set, and they must be restored together
or the free-list head points into a pool with different contents.

### 1.6 Host-side state that has drifted out of the guest

Everything in this table is native, none of it is in the three game runs, and each entry is a
deliberate decision.

| State | Where | Bytes [M] | Snapshot? |
|---|---|---:|---|
| `gw_mex_kinds[31]` (per-kind m-ex runtime: `gw_ftfunction` blob record, `installed`, MoveLogic table + 64×4 preserved guest callbacks, 16 article ranges, 64 article symbols) | `gw_mex_ftfunction_runtime.obj` | **85,312** (2,752/kind) | **no** — load-time only, *if* §3.4 holds |
| `gw_mex_k` (the currently-selected kind, moved by `gw_Mex_SelectKind`/`RestoreKind`) | same | 4 | yes — a pointer into a fixed-base array, so it is stable across processes; balanced at a frame boundary, assert it |
| `gw_mex_thunk_guest[64]` + `gw_mex_thunk_count` | same | 260 | **yes** (§3.4) |
| `gw_mex_trap_seen`/`_count`/`_n`, `gw_mex_trap_target` (TLS) | same | 260 | no — diagnostics only; the TLS word is live only inside one trap |
| `gw_mex_r2`, `gw_mex_stack_top`, `gw_mexdt*` | same | 20 | no — fixed at install |
| `gw_mex_gobj_hooks`, `gw_mex_gobj_hooks2`, `gw_mex_pred_hooks` (6,400 each) | `gw_runtime.obj` | 19,200 | no — dispatch tables, written at install |
| `gw_mex_hook_active[event][kind]` | `gw_runtime.obj` | 1,600 | no — a re-entrancy flag matrix, set and cleared inside one dispatch (`gw_runtime.c:1082-1124`). **Assert all-zero at the snapshot point.** |
| `gw_mex_features` (env-driven opt-ins) | `gw_runtime.obj` | 3,072 | no — but it is a **handshake input**: two peers with different `MELEE_*` settings desync |
| `gw_stubs`, `tt_levels` | `gw_runtime.obj` | 24,832 | no |
| `gw_deferred[256]` + count (`gw_defer`) | `shim_vi.obj` | 4,100 | **must be empty**, not snapshotted (§3.5) |
| `gw_alarms[16]` (wall-clock `fire_at`) | `shim_os.obj` | 512 | **must be virtualised**, not snapshotted (§3.5) |
| `gw_prof_*` (profiler) | `shim_vi.obj` | ~4,850 | no |
| `gw_ax_voices`, `gw_ax_in_use`, `gw_ax_ring` and the rest of `shim_ax.obj` | `shim_ax.obj` | 121,796 | **no** (§3.1) |
| `gw_script` (pad script) and the rest of `shim_pad.obj` | `shim_pad.obj` | 98,352 | no — replaced by the netplay input source (§3.2) |
| `gw_ar_top`, `gw_ar_stack_base`, `gw_ar_blocks_*` | `shim_ar.obj` | 28 | yes if ARAM is ever written mid-match; 28 bytes, include it |
| DVD: `FILE*`, FST, the mods overlay (`shim_dvd.c:159-290`) | `shim_dvd.obj` | 4,180 | **never** (§3.6) |
| Aurora GX state, texture caches, Dawn, SDL3, sqlite, freetype | arena 3 and 4 | ~50,600 + heap | **never** (§3.6) |

**HSD object graphs need no special handling.** GObjs, JObj trees, particles and their pools are
main-heap MEM1 plus native `HSD_ObjAllocData` heads, both of which are in the set. Because MEM1 is
at a fixed address and the exe has a fixed base, every pointer stored in a GObj — including the
native function pointers in `HSD_GObj` procs and the `gw_mex_thunks[k]` addresses guest code
installs — is bit-identical across two processes running the same build. This is the single
biggest advantage the port has over an emulator, and it is why "snapshot" here can be a `memcpy`
rather than a serialisation.

### 1.7 The set, in one place

```
SAVE:
  MEM1 main heap            11,267,664   [D]
  MEM1 heaps 2 and 6             2,080   [D]
  MEM1 m-ex persist region     393,216   [D]   (see §3.4)
  native game globals          659,868   [M]   ~22 ranges, 3 runs minus 19 holes
  gw___OSCurrHeap                    4   [M]
  gw_ppc range table + count     2,052   [M]
  gw_mex_thunk table + count       260   [M]
  gw_ar_* bookkeeping               28   [M]
                              ----------
  Tier 1 total              12,325,172 bytes  ~11.75 MB

  + MEM1 heaps 3 and 4      11,950,224   [D]   -> Tier 2, 23.2 MB   (see §3.7)

ASSERT at save and at load:
  gw_ppc_depth == 0
  gw_deferred_count == 0
  gw_mex_hook_active all zero
  MXCSR == the pinned value
```

---

## 2. What it costs per frame

### 2.1 Measured primitives (this machine, 32-bit, best-of-N, hot cache)

| Operation | Time [M] | Rate |
|---|---:|---|
| `memcpy` 64 KB | 0.7 µs | 94 GB/s |
| `memcpy` 644 KB | 8.4 µs | 79 GB/s |
| `memcpy` 1 MB | 13.4 µs | 78 GB/s |
| `memcpy` 4 MB | 179 µs | 23 GB/s |
| `memcpy` 8 MB | 347 µs | 24 GB/s |
| `memcpy` 12 MB | 520 µs | 24 GB/s |
| `memcpy` 24 MB | 1,495 µs | 17 GB/s |
| 22 scattered ranges totalling 644 KB | 13.0 µs | — |
| copy 1,024 scattered 4 KB pages (4 MB) | 161 µs | 25 GB/s |
| `GetWriteWatch` + RESET over 24 MB, 64 / 1,024 / 6,144 pages dirty | 39 / 36 / 99 µs | — |
| scalar FNV-1a u64 hash, 644 KB / 8 MB / 24 MB | 103 / 1,487 / 4,091 µs | 6.4 GB/s |
| DEP execute-fault round trip (`gw_mex_exec_trap` shape) | **4.63 µs/call** | — |
| the same call as a plain indirect call | 0.0003 µs | 15,000× cheaper |
| bridge binary search, miss, 17,677 entries | **8.6 ns** | — |

The `memcpy` curve has a clear knee between 1 MB and 4 MB: inside the last-level cache it is
78 GB/s, outside it is 24 GB/s and then 17 GB/s once both source and destination exceed it. Any
snapshot above a couple of megabytes runs at the 17–24 GB/s figure, so **~45 µs per megabyte** is
the number to plan with.

### 2.2 Snapshot cost, by strategy

| Strategy | Bytes/frame | Save [M-derived] | Restore | Verdict |
|---|---:|---:|---:|---|
| **A. Everything**: 24 MB MEM1 + 644 KB globals | 25.2 MB | ~1,510 µs | ~1,510 µs | 7-frame worst case ≈ **12 ms of pure `memcpy`**. Dead on arrival. |
| **B. Tier 1** (§1.7): 11.75 MB | 12.3 MB | **~535 µs** | ~535 µs | 3.2 % of a 16.67 ms frame. 7-frame worst case ≈ 4.3 ms of copying. **Feasible, and this is what to build first.** |
| **B2. Tier 2**: 23.2 MB | 23.2 MB | ~1,050 µs | ~1,050 µs | Only if §3.7 says heaps 3/4 are mutable. Then go straight to C. |
| **C. Write-watch + undo log** over all of MEM1 | dirty set only | **~40–100 µs enumerate + ~45 µs/MB dirty** | same | If the dirty set is ≤ 1 MB/frame — likely, since most of MEM1 is immutable file data — this is **~130 µs/frame and covers Tier 2 for less than Tier 1 costs**. It also removes the bet in §3.7 entirely. |

Strategy C's enumeration cost is flat in the region size and nearly flat in the dirty count
(39 µs at 64 dirty pages, 36 µs at 1,024, 99 µs at 6,144), so it is a fixed ~40–100 µs tax. It
requires exactly one code change: adding `MEM_WRITE_WATCH` to the flags at `gw_runtime.c:51`.
**[M] That has been verified to work at the real fixed base**: `VirtualAlloc(0x80000000, 24 MB,
MEM_RESERVE|MEM_COMMIT|MEM_WRITE_WATCH)` succeeds in a 32-bit `/LARGEADDRESSAWARE` process, with
4,096-byte granularity, and `fread`/`ReadFile` writes into the region are reported dirty.

**Recommendation: build B, instrument C's `GetWriteWatch` at the same time to get the dirty-page
histogram for free, and switch to C once the histogram is known.** That is the same recommendation
`rollback-netcode.md` §3 reached, now with the numbers to back it and with the fixed-base and
kernel-write questions answered.

### 2.3 The cost that is *not* the snapshot

Resimulating k frames costs k × (one logic frame). For natively compiled game code that is cheap:
the port measures game-thread logic plus GPU submit at "well under 1 ms" (`shim_vi.c`, the comment
above `GW_PACE_SPIN_TICKS`), and resimulation draws nothing, because presentation, pacing, alarms,
deferred work and audio all live in `gw_frame_tick` → `VIWaitForRetrace`, reached from the render
path and not from the inner logic loop (`gmscene.c:292-376`).

**For interpreted m-ex content it is not cheap, and this is the part the general literature does
not cover.** Every resimulated frame re-executes every m-ex fighter's `onFrame`, MoveLogic
callbacks and action-state hooks through `gw_ppc_run`. Three measured facts bound it:

- **[M]** A synthetic dispatch loop of the same shape as `gw_ppc_execute` (big-endian fetch,
  bounds check, primary-opcode switch, extended-opcode sub-switch, GPR writeback) runs at
  **1,065 M instructions/s**. That is a hard *upper* bound and a very optimistic one: no CR
  updates, no XER, a tiny hot loop, perfect branch prediction.
- **[M]** The real interpreter pays an extra **8.6 ns on every load and store** that touches an
  address ≥ `0x80300000`, because `gw_ppc_static_native` (`gw_ppc.c:112-127`) calls
  `gw_mex_bridge_lookup`, a binary search over **17,677 entries** (~212 KB of table). The gate at
  `0x80300000` was written on the assumption that "the interpreter's heap/stack/code all live
  below" it — but **[D] the main heap starts around `0x806A0000`**, so *every* interpreted access
  to a fighter struct, a GObj or a JObj takes the full ~15-probe search. If loads and stores are
  30 % of the instruction mix, effective throughput falls to roughly **[E] 100–300 M insn/s**.
  (Worth noting independently of rollback: a direct-mapped cache in front of that search, or
  raising the gate to the real static base `0x803B7280`, would speed up all m-ex content.)
- **[M]** Every native call into guest code that is not routed through the thunk pool costs a
  **4.63 µs DEP execute-fault round trip** (`gw_mex_exec_trap`,
  `gw_mex_ftfunction_runtime.c:1379`). The code comment already says this is "fine for event
  callbacks but not for anything per-frame". Under rollback the budget is multiplied by the
  resimulation depth: at a 7-frame rollback, ten trapped calls per frame is **324 µs**, and one
  per-frame trapped callback per fighter is enough to dominate the snapshot cost.

**[E]** If an m-ex fighter's per-frame guest work is on the order of 20,000 instructions, a single
interpreted frame costs 70–200 µs, and a 7-frame rollback with two m-ex fighters costs 1–3 ms of
interpretation. That is survivable but it is the largest single term after the snapshot, and it is
the one number here that is a guess. **Measuring it is milestone 0** and costs one counter in
`gw_ppc_run` plus one scheduled gameplay run.

### 2.4 Hashing is more expensive than copying — do not hash the whole state

**[M]** The scalar FNV-1a hash runs at 6.4 GB/s: 103 µs for 644 KB, 1,487 µs for 8 MB, 4,091 µs
for 24 MB. Copying 8 MB costs 347 µs; hashing it costs 1,487 µs. A per-frame whole-state hash is
therefore **four times more expensive than the snapshot it is checking**.

Consequences:

- The **desync checksum sent over the wire** must be over a small canonical subset — the player
  static blocks and the RNG seed, as Slippi does — not the whole state. 22 KB of `gw_player_slots`
  hashes in ~3.5 µs.
- The **whole-state hash** belongs in the offline determinism harness (milestone 1), where 4 ms a
  frame does not matter, not in the netplay loop.
- If a fast whole-state hash is ever wanted in the loop, it needs a hardware CRC32C or an
  xxh3-class implementation (10–30 GB/s), not a scalar FNV. Under strategy C it can also be made
  incremental over dirty pages, which is the right answer.

---

## 3. What is not safely rollback-able as the port stands today

Ordered by how likely each one is to be the thing that stops the project.

### 3.1 Audio — the synth runs on the sound card's clock and hands values back into fighter structs

**Severity: blocker for correctness of the state hash; not a blocker for playability.**

`gw_ax_frame_tick` runs `HSD_SynthCallback` zero-to-N times per VI tick depending on the output
ring's fill level (`shim_ax.c:1151-1188`). The synth's state is therefore a function of the audio
device clock, which is not the game clock and is not the same on two machines. Correctly, all
121 KB of `shim_ax.obj` and all 154 KB of `lbaudio_ax.c` + `synth.c` + `axdriver.c` are excluded
from the snapshot.

The problem is that the exclusion is not a firewall in one direction:

```c
/* src/melee/ft/ft_0877.c:470 */
fp->x2160 = lbAudioAx_800237A8(sfx_id, sfx_vol, sfx_pan);
```

`lbAudioAx_800237A8` returns a sound instance id, and the fighter **stores it in the fighter
struct** — which is main-heap MEM1, which *is* snapshotted. So a non-deterministic value produced
by an excluded subsystem is written into rolled-back state every time a fighter starts a looping
sound. `ftcrazyhandpoke.c:121-123` and `ftmasterhandfingerbeam.c:119-121` do the same into three
fields each. Resimulation replays those calls, so the counter advances differently on each peer
and after every rollback.

For gameplay this is benign (the id is only used to stop the sound later). For a state hash it is
fatal: two peers in perfect agreement will report different checksums.

**Cost to fix.** Slippi's solution, re-expressed in C rather than ASM: (a) deterministic instance
ids — allocate them from a logic-frame-driven counter that is *inside* the snapshot, and map them
to real synth voices through a side table that is not; (b) a per-frame ring of sounds played,
`MAX_ROLLBACK` deep, so a sound re-emitted during resimulation of a frame that already played it
is suppressed; (c) kill sounds that were in the stable log but not re-emitted after a rollback.
**[E] 1–2 weeks**, and it cannot be skipped, because (b) is also what stops resimulation from
machine-gunning the same hit sound seven times.

Partial mitigation available immediately and worth doing first: exclude the fighter fields that
hold sound handles from the *hash* while keeping them in the *snapshot*. That is a small list of
offsets and it unblocks milestone 1 without solving the audio problem.

### 3.2 Time, alarms and the pad queue — the simulation is paced by wall-clock QPC

**Severity: blocker. Nothing else can be tested until this is done.**

Already argued in `rollback-netcode.md` §4.3 and §5; restated here only to place it in the
dependency order. `OSGetTime`/`OSGetTick` return `gw_time_ticks()`, a free-running QPC clock
(`shim_vi.c`). The pad alarm (`lb_0195.c:62-114`) samples input on that clock, `gw_os_run_alarms`
fires from three different places including inside the pacing spin, and `MELEE_PAD_SCRIPT` injects
at `PADRead` — one script frame per *alarm sample*, not per logic frame, so it is not a
determinism oracle.

**Cost to fix. [E] 1.5–2.5 weeks**, unchanged from the earlier estimate. It is milestone 1 and
everything else depends on it.

### 3.3 The PPC interpreter — three specific things, none of them the registers

**Severity: medium. All three are cheap to fix and expensive to discover late.**

1. **Nothing asserts `gw_ppc_depth == 0` at a frame boundary.** The whole argument that the
   register file need not be snapshotted (§1.4) rests on it. It is true today by construction and
   nothing keeps it true. **Cost: one assert.**
2. **The code-range table is live, mutable state.** `gw_ppc_add_code_range` /
   `gw_ppc_remove_code_range` (`gw_ppc.c:383-408`) are called from `gw_mex_load_items` /
   `gw_mex_unload_items` at fighter-data load (`gw_mex_ftfunction_runtime.c:971, 1058, 2121,
   2157`). Removal is a **swap-with-last** compaction, so the table's *order* depends on the
   history of loads and unloads. Two peers that reached the match by different menu paths can end
   up with the same set of ranges in a different order — harmless for behaviour (the lookup is a
   linear scan for membership) but it makes the 2 KB table a false-positive source in any hash that
   covers it. **Cost: snapshot the 2,052 bytes, and either sort the table or keep it out of the
   hash. A day.**
3. **The DEP exec-trap costs 4.63 µs per call and is multiplied by the rollback depth** (§2.3).
   The existing mitigation — the log line in `gw_mex_trap_note` that fires every 600 calls
   suggesting "an explicit route if this is per-frame" — becomes load-bearing under rollback.
   **Cost: route each hot trapped callback explicitly, as `accessory4_cb` already is in
   `fighter.c`. Per-callback, an hour; the risk is that the list is content-driven and grows with
   every new m-ex fighter.**

What is *not* a problem, and is worth saying plainly: the interpreter is **deterministic**. It is
compiled once into the exe, it computes Gekko single-precision by rounding a double
(`gw_ppc.c:1237+`), and `gekko_fp.c` emulates `__frsqrte` bit-exactly. Two copies of the same exe
interpreting the same blob produce the same bits. The hybrid — interpreted fighter code calling
natively compiled engine code through a fixed-base bridge table, and native engine code calling
back into interpreted code through fixed-address thunks — is *more* deterministic than an
emulator, because there is no JIT, no code cache and no address-space randomisation anywhere in
the path.

### 3.4 The m-ex runtime's load-time state is only load-time by assumption

**Severity: high, and under-appreciated.**

`gw_mex_kinds[31]` is 85,312 bytes of native state that §1.6 excludes on the grounds that it is
written once at fighter load. That is true *if* fighter data is only ever loaded at scene setup.
The path is `ftData_8008572C` → `Mex_FtFunctionInstall` (`src/melee/ft/ftdata.c:1907-1909`) →
`gw_Mex_FtFunctionInstall` (`gw_mex_ftfunction_runtime.c:2062`), which on each call:

- calls `gw_mex_unload_items()` and `gw_ppc_remove_code_range` (lines 2121, 971),
- re-reads the fighter's `.dat` **from disc**,
- relocates the blob and calls `gw_ppc_add_code_range` (2157, 1058),
- fills `gw_mex_kinds[slot]` including the 1,024-byte preserved-callback table,
- and allocates from `gw_mex_persist_alloc` — **a bump allocator that never frees**
  (`gw_mex_ftfunction_runtime.c:212-237`), which panics with "persistent guest memory exhausted"
  when the 384 KB region runs out.

If that ever runs mid-match — Kirby copying an m-ex fighter's hat is the obvious candidate, and
Stadium transformations are the vanilla precedent Slippi had to special-case — then **a rollback
across it is not possible**: it did host file I/O, it mutated native tables that the snapshot does
not cover, and it consumed persist-region bytes that cannot be given back.

**Cost to fix.** First, *find out*: log every `Mex_FtFunctionInstall` with the frame number in a
real match and see whether any fires after the match starts. **[E] one gameplay run.** If none
does, the fix is an assert and this whole item collapses to nothing. If one does, the options are
(a) preload every fighter kind that can appear in the match at match setup and forbid mid-match
installs — the same answer Slippi reached for Stadium — or (b) make the persist allocator
rollback-aware, which means a watermark-and-truncate discipline and is only sound because nothing
ever frees. **[E] (a) is a few days; (b) is a week and is the wrong shape.** Prefer (a).

A smaller relative of the same problem: `gw_mex_thunk_guest[64]`
(`gw_mex_ftfunction_runtime.c:1220`) binds thunk slots to guest addresses on first use,
deduplicated by address. Dedup makes it idempotent under resimulation — the same callback
re-registered gets the same slot — so the guest pointers stored into MEM1 are stable. But the
binding is created by a *side effect* of a frame that a rollback can erase, so the 260 bytes
belong in the snapshot for the same belt-and-braces reason as `gw___OSCurrHeap`.

### 3.5 Deferred work, alarms and DVD I/O straddle the snapshot boundary

**Severity: high, and one instance is hiding inside a snapshotted structure.**

`gw_DVDReadAsyncPrio` reads synchronously with `fread` into guest memory and then
`gw_defer(gw_dvd_complete, ...)` (`shim_dvd.c:527-572`); ARQ (`shim_ar.c:124`) and the card
(`shim_card.c:156`) do the same. The callbacks run at the next pump, which is wall-clock gated. So
a deferred callback issued on logic frame F can land on frame F, F+1 or F+3 depending on how fast
the machine is, and it writes into MEM1 when it lands.

The fix is the one §3.2 already requires — run `gw_run_deferred` exactly once at the start of each
logic frame, never from the pacing loop, and assert `gw_deferred_count == 0` at the snapshot point
— so this costs nothing extra *once §3.2 is done*. Before that it is an unbounded source of
non-reproducibility.

**The instance that is hiding:** `struct LBMgr` inside `lbMemory_804318B0` begins with an
`OSAlarm` (`src/melee/lb/lbmemory.c:18-26`), and `lbMemory_804318B0` is 1,792 bytes **inside game
run 3**, i.e. inside the snapshot. lbMemory's chunked copy re-arms that one-shot alarm ~3 ms out,
so the number of chunks completed per logic frame is a function of wall time. A snapshot therefore
captures a *partially restored* alarm: the alarm object's bytes revert, but the shim's
`gw_alarms[16]` queue (`shim_os.c`, 512 bytes, excluded) does not. After a restore the alarm can
be queued-but-reverted or reverted-but-queued. Both are silent corruption.

**Cost to fix. [E] a few days**, and the fix is structural rather than fiddly: in netplay mode,
alarms run on virtual time and fire only at logic-frame boundaries, so the alarm queue and the
alarm objects inside the snapshot agree by construction. Either include `gw_alarms` in the
snapshot and drive it from the frame counter, or drain lbMemory's copy synchronously at the frame
boundary so no alarm is ever pending across one. The second is simpler and should be tried first.

### 3.6 The host: GPU, audio device, files — and the one arena that cannot be enumerated

**Severity: low for GPU, already covered for audio, medium for the un-enumerable heap.**

**GPU.** Structurally fine, and for a reason specific to this port: the scene loop runs
`pad_queue_count` logic iterations and *then* renders once (`gmscene.c:292-376`). Resimulation
adds logic iterations, and logic never touches Aurora. Aurora's GX state (~13.7 KB in `aurora_gx`),
its texture cache and Dawn's resources are never restored and never need to be — they are rebuilt
from whatever MEM1 holds at render time, and after a restore MEM1 holds the same bytes it would
have held anyway. The only way this breaks is if a GObj *render* proc mutates simulation state;
that is already flagged as open question 2 in `rollback-netcode.md` and the write-watch
differential (§1.1 oracle 2) answers it directly — run a render tick with logic disabled and see
whether any snapshotted page goes dirty. **Cost: one measurement, not a fix.**

**Files and the mods layer.** `shim_dvd.c` holds a `FILE*`, the FST, and the mods overlay built by
`gw_mods_scan` / `gw_mods_load` (lines 195-290). None of it is per-frame state and none of it is
snapshotted. It *is* a handshake input: the overlay is built by scanning `mods/` and sorting by
name, so two peers with different `mods/` directories — or different `MELEE_MODS*` settings —
silently run different content. The handshake must carry a hash of the exe, the ISO and the
resolved mods overlay, and `gw_mex_features` (§1.6) with it.

**The un-enumerable arena.** Arena 4 — the CRT heap and native stack used by shims, Aurora, Dawn,
SDL3, sqlite and freetype — is the only place a hidden piece of simulation state could live where
no static analysis will find it. ARAM is the concrete instance: 16 MB from `calloc`
(`gw_runtime.c:63`), so its address varies between processes. Game code addresses ARAM by offset
(`gw_ar_addr`), so no raw host pointer should reach sim state — but "should" is doing work in that
sentence, and the only thing that proves it is oracle 3. **Cost: nothing to fix now; the cost is
that milestone 2 must be taken seriously rather than declared done when it first passes.**

### 3.7 The bet on heaps 3 and 4 (11.95 MB)

**Severity: decides the whole cost model, and is the cheapest thing on this list to resolve.**

Slippi does not save the ~4.8 MB of preloaded file data between its saved ranges, betting that
loaded file data is immutable during a match. Tier 1 here makes the same bet about heap 3
(5.35 MB of IfAll/ItCo/EfCoData preloads) and heap 4 (6.60 MB of lbMemory's file cache).

There is one known counter-example in this tree, and it is instructive: `ftdata.c:1885-1896`
**writes into the loaded archive** — it rewrites `x10_animCurrFlags` in the fighter's demo-motion
table in place. That happens at load, not per frame, but it proves the archive region is not
treated as read-only by the port. Whether anything writes it *during* a match is unknown.

**Cost to resolve: nothing, if strategy C is instrumented from the start.** `GetWriteWatch` over
all 24 MB reports exactly which pages are written per frame; if no page inside heaps 3 or 4 is ever
dirty during a match, the bet is proven rather than assumed, and if some are, strategy C covers
them for **[M] ~45 µs per dirty megabyte** instead of the ~515 µs Tier 2 would cost. This is the
strongest argument for going to write-watch early.

---

## 4. A staged plan

The milestones are ordered so that each one is independently useful even if the next never
happens — `tools/replay/` wants milestone 1 regardless of whether netplay ships.

### Milestone 0 — measure the two unknown numbers (days)

Not a feature. Two counters and one scheduled gameplay run, which turns the two **[E]** figures in
this document into **[M]**:

1. `MEM_WRITE_WATCH` on the `VirtualAlloc` at `gw_runtime.c:51`, plus a `GetWriteWatch` at the top
   of each logic frame logging dirty-page count and whether any dirty page lies in heaps 3/4.
   Answers §3.7 and decides strategy B vs C. Cost: ~40–100 µs/frame, invisible.
2. An instruction counter in `gw_ppc_run` and a call counter in `gw_mex_trap_note`, logged per
   frame. Answers §2.3 — how much a resimulated frame actually costs with an m-ex fighter on
   screen.
3. Log the frame number at every `Mex_FtFunctionInstall`. Answers §3.4.

**This needs one windowed gameplay run with an m-ex fighter (Sonic) in a VS match — request it
from the orchestrator; do not launch it unilaterally.** Everything else in milestone 0 is
`--test`-able.

### Milestone 1 — deterministic replay (1.5–2.5 weeks)

Unchanged in substance from `rollback-netcode.md` §8(a), and it is still the right first
milestone — but the *proof obligation* should be stated more sharply than "run it twice":

- `MELEE_DETERMINISTIC=1`: virtual clock = logic frames × 675,000 ticks; alarms and deferred work
  only at logic-frame boundaries; the pad alarm disabled; RNG seed from the environment; no pacing.
- Input injection at the `HSD_PadRenewMasterStatus` pop (`controller.c:359-362`), from a
  per-logic-frame log, plus a recorder.
- A per-frame whole-state hash over the Tier 1 set. 4 ms a frame is fine here (§2.4).
- **The byte differ is the deliverable, not the hash.** On the first mismatching frame, dump both
  snapshots and attribute every differing byte to a symbol through `melee-pc.map` and to a heap
  cell through the OSAlloc `Cell` headers. This is what *discovers* the exclusion list instead of
  guessing it, and it is what makes §3.6's un-enumerable arena tractable.
- Replace the host CRT `sinf/cosf/tanf/atanf/logf` (`shim_libc.c:83-87`) with game-world code.

**Exit test:** the same recorded 1v1 replayed twice on one machine produces identical per-frame
hashes for 60 seconds, with an m-ex fighter on screen for part of it. Then the same on a second
machine.

### Milestone 2 — in-process savestates (1.5–3 weeks)

- `gw_snap_save(slot)` / `gw_snap_load(slot)` over the §1.7 set, strategy B, with the four asserts.
- The three linker markers bracketing the game-global runs, plus a CI check over `melee-pc.map`
  that the runs are still exactly three and contain exactly the expected objects (§1.3).
- **Smallest honest first milestone, and the thing to aim at:** *save at frame N, immediately
  restore, and continue — and prove that the next 600 frames hash identically to a run that never
  saved.* That is strictly weaker than a real rollback and it catches the entire class of "we
  forgot a native global", because a forgotten global survives the restore and diverges. It is
  also implementable in an afternoon once milestone 1 exists.
- Then the real test: save at N, run to N+120, restore N, replay. Repeat at random N across VS,
  items, Kirby, Stadium, Ice Climbers, and Sonic/m-ex — the last one specifically to exercise §3.3
  and §3.4.
- Measure. Switch to strategy C if milestone 0's histogram says so.

### Milestone 3 — local rollback (2–3 weeks)

Scene-loop hooks at the two points Slippi uses; a SyncTest mode that rolls back k frames every
frame and compares hashes; a fake-latency mode with "repeat last" prediction; the audio firewall
from §3.1; rumble gating. The audio work is the long pole and should start during milestone 2.

### Milestone 4 — networking (3–6 weeks for a direct-IP MVP)

As in `rollback-netcode.md` §8(d). The only thing this document adds: the handshake must carry
hashes of the exe, the ISO, the resolved `mods/` overlay and `gw_mex_features`, because §3.6 makes
all four silent desync sources.

---

## 5. Summary

- **Snapshot set: 11.75 MB** — the 11.27 MB main heap, the 384 KB m-ex persist region, two small
  heaps, **644 KB of native game globals in about 22 ranges carved out of exactly three contiguous
  linker runs**, and 2.3 KB of shim and interpreter bookkeeping. MEM1 restores the main heap's free
  lists for free, because OSAlloc's cell headers and lists are all in-band.
- **Cost: ~535 µs to save and ~535 µs to restore** — 3.2 % of a frame. A 7-frame rollback costs
  ~4.3 ms of copying plus the resimulation itself. Write-watch dirty-page snapshotting would cut
  that to **~130 µs/frame while covering *all* of MEM1**, and it has been verified to work at the
  port's fixed `0x80000000` base including for `fread` writes.
- **Top three blockers: audio handles written into fighter structs; wall-clock time driving the pad
  alarm, deferred DVD work and lbMemory's embedded `OSAlarm`; and the m-ex runtime's never-freeing
  persist allocator plus mutable interpreter range table if fighter data is ever loaded
  mid-match.**
- **First milestone: prove a save-and-immediately-restore is a no-op over 600 frames.** It is the
  cheapest test that fails when a native global has been forgotten, and forgetting a native global
  is the failure mode this port has that an emulator does not.
