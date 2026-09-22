# Rollback netcode for the native Melee PC port: research and design

Status: research and design only. Nothing under `melee/`, `_build/` or `C:/iso` was changed, built or run.
Date: 2026-09-19. Claims are tagged **VERIFIED** (I read the code or source) or **INFERRED** (reasoned,
not observed). All `file:line` references are to this tree (`C:/gdm`) unless they name an upstream repo.

---

## 0. TL;DR

- **The port is better suited to rollback than Dolphin was.** Melee's own scene loop already runs
  N logic frames and then renders once (`src/melee/gm/gmscene.c:292-376`). Slippi's rollback is
  built on that same loop through two ASM hooks (at `0x801a4de4` and `0x801a5014`, both inside
  `gm_801A4D34`). In C this becomes a pair of `#ifdef TARGET_PC` hooks. There is no emulator core
  to snapshot: a savestate is MEM1 plus the game's native `.data/.bss` plus a small amount of shim state.
- **Snapshot size:** Slippi saves about 8 MB of guest memory for each savestate. Here the upper
  bound is the 24 MB MEM1 block plus about 1.0 MB of game globals. Copying that per frame costs
  about 2-4 ms (INFERRED) and fits in the frame budget, because game logic takes well under 1 ms per
  frame (measured, `pc/platform/shim_vi.c` comment above `gw_pace_field`). Windows write-watch
  (`MEM_WRITE_WATCH` on the existing `VirtualAlloc`, `pc/platform/gw_runtime.c:51`) makes
  dirty-page snapshots nearly free.
- **Determinism is plausible for two copies of the same exe, but not free.** Game code is compiled
  once to fixed SSE2 x86 (`gwtool.cpp:81-83`, pentium4, no FMA), so the arithmetic is bit-identical
  on every x86 CPU. The known hazards are:
  - `sinf/cosf/tanf/atanf/logf` are forwarded to the OS's UCRT (`pc/platform/shim_libc.c:83-87`).
  - Time is wall-clock based (`shim_vi.c` `gw_time_ticks`), so alarms, pad sampling and deferred
    DVD callbacks fire on real time.
  - The audio synth ticks at the audio device's rate.
  - The pad queue is filled from an alarm.
  - The RNG is seeded from `OSGetTick()` (`src/melee/gm/gmmain.c:163`).
  - Uninitialised heap memory differs with each machine's menu history.
- **Slippi interop is not realistic.** The wire protocol only carries inputs, so the barrier is not
  the state layout. It is that the port does not reproduce console arithmetic bit for bit: it uses
  unfused FP where the Gekko fuses, CRT trig, and so on. Slippi also expects its own online codeset
  and servers.
- **Recommended first step:** a deterministic "lockstep replay" mode in which the virtual clock is
  a function of the logic-frame count and inputs are injected per logic frame. Hash the curated
  state every frame and run the same input log twice. `tools/replay/README.md` already names
  retrace-driven time as the prerequisite.

---

## 1. Prior art

### 1.1 Slippi (Project Slippi's Ishiiruka/Dolphin fork plus `slippi-ssbm-asm`)

**Who drives the resimulation: game code, not Dolphin.** (VERIFIED, `slippi-ssbm-asm/Online/Core/*.asm`)
- `StartEngineLoop.asm` hooks `0x801a4de4`, where `HSD_PerfSetStartTime` is called at the top of
  each logic iteration. `LoopEngineForRollback.asm` hooks `0x801a5014`, the loop-back branch in the
  same function. That function is `gm_801A4D34` in this tree (`gmscene.c:271`). The game's own "run
  `pad_queue_count` logic frames, then render once" loop becomes the resimulation loop.
- The helper hooks are:
  - `ForceInputRefetchOnAdvance.asm` and `SkipNewInputFetchOnRollback.asm` choose which inputs a
    frame sees.
  - `Hacks/PreventPadAlarmDuringRollback.asm` hooks `0x80019608` (inside `fn_800195FC`, our
    `lb_0195.c:52`). It stops the VI pad alarm from renewing inputs during a rollback and sets a
    "renew later" flag instead.
- Dolphin (`EXI_DeviceSlippi.cpp`) serves EXI commands from the ASM: capture savestate, load
  savestate, get the remote inputs for frame N, send the local pad.

**Savestates:** `Source/Core/Core/Slippi/SlippiSavestate.cpp` (VERIFIED, fetched).
- Plain `memcpy` of four guest regions into 64-byte-aligned buffers. There is no dirty tracking and
  no threads:
  - `0x80005520-0x80005940`: data sections 0 and 1.
  - `0x803b7240-0x804DEC00`: data sections 2-7 plus bss, about 1.16 MB.
  - `0x8065c000-0x8071b000`: about 0.75 MB.
  - `0x80bd5c40-0x811AD5A0`: the heap, about 6.1 MB. Its bounds are read at runtime from
    `0x804d76b8/bc`.
- Total is about 8 MB. The region between them (about 4.8 MB, INFERRED to be the preloaded
  file data) is **not** saved. The design assumes loaded file data is immutable during a match.
- An `excludeSections` list of about 24 ranges (sound/synth globals `0x804031A0...`, and the
  XFB/VI state at `0x804c0980`, size `0x15F8`) is cut out of the backup ranges.
- `Load()` takes a list of "preserve blocks". It copies them aside, restores the whole snapshot,
  then puts them back. This is how data that must survive a rollback (for example the online data
  buffer) is kept.
- Audio state serialisation is present but commented out. Audio is not rolled back.

**Numbers:** `SlippiNetplay.h` (VERIFIED) has `ROLLBACK_MAX_FRAMES 7`,
`SLIPPI_ONLINE_LOCKSTEP_INTERVAL 30`, and up to 3 remote players. The default online input delay is
2 frames (user setting; INFERRED from Slippi's UI, not read in source).

**Desync detection:** VERIFIED. `StartEngineLoop.asm` has `FN_COMPUTE_CHECKSUM`, which walks the
player static blocks from `0x80453080` to `0x80455C30`. For each player's main and secondary entity
it folds fighter fields and a float sum into a u32. The checksums are exchanged
(`ChecksumEntry remote_checksums[]` in `SlippiNetplay.h`). A mismatch prints "DESYNC DETECTED"
on-screen, and `SlippiDesyncRecoveryResp` / `SlippiSyncedGameState` support a recovery path.

**Audio during resimulation:** VERIFIED (`Online/Core/Sound/*.asm`).
- `PreventDuplicateSounds.asm` hooks `SFX_PlaySFX` (`0x8038d0b0`). It keeps a per-frame ring of the
  sounds played, `ROLLBACK_MAX_FRAME_COUNT` deep. A sound replayed during resimulation of a frame
  that already played it is suppressed, and its instance id is reused.
- `LoopEngineForRollback.asm` kills sounds that were in the "stable" log but not re-emitted after a
  rollback: actions that got cancelled.
- `AssignSoundInstanceId.asm` and `NoDestroyVoice*.asm` make sound handles deterministic.
- Music has its own hooks (`Online/Core/Music/*`). File-load alarms are neutralised
  (`PreventFileAlarms/*`), and Stadium transformation files are loaded synchronously over EXI
  (`Hacks/Stadium/StadiumFileLoad.asm`, `EXIFileLoad/*`).

**Rendering:** there is nothing special to do. Resimulated frames are extra logic iterations
before the single render pass.

**Game-logic determinism fixes:** Slippi needed some even on real-hardware semantics. For example,
`Hacks/FD/DesyncProofBGTransformations.asm` saves and restores the RNG seed (`0x804D5F90`) around
the FD background think, because a per-user visual option consumed RNG. The general lesson:
**anything user-configurable that consumes the RNG is a desync**.

### 1.2 GGPO and GGRS

- **GGPO** (pond3r/ggpo, MIT since 2019; INFERRED from memory, not re-read). The game supplies
  callbacks: `save_game_state`, `load_game_state`, `advance_frame` (the library calls it during
  resimulation), `free_buffer` and `on_event`. Prediction repeats the last known input. It
  exchanges inputs over UDP with redundancy (sends all unacked inputs). Time sync uses "frame
  advantage": the side that is ahead is told to wait N frames. It includes `ggpo_start_synctest`,
  which rolls back every frame and compares checksums. That is the local determinism test for
  free. It is C++ with a C API and works on Windows.
- **GGRS** (Rust, MIT/Apache-2.0) is the same model with a request-based API. Each tick returns a
  list of `SaveGameState` / `LoadGameState` / `AdvanceFrame` requests for the game to execute. It
  has P2P, spectator and SyncTest sessions, and checksum-based desync detection. Using it from C
  needs an FFI crate; `i686-pc-windows-msvc` is a supported Rust target.
- **GekkoNet** (HeatXD/GekkoNet, BSD-2-Clause, VERIFIED via search) is a C++ SDK with a C API
  modelled on GGRS. It is used by an N64 emulator's rollback work.

### 1.3 What transfers to a native port

| Slippi / emulator mechanism | Native port equivalent |
|---|---|
| ASM hooks in `gm_801A4D34` | C hooks under `TARGET_PC` in `gmscene.c` (VERIFIED the loop exists: `gmscene.c:292-360`) |
| EXI commands to Dolphin | A direct C call into a `pc/platform/gw_netplay.c` module |
| Hand-found guest address ranges | **Symbol-exact ranges from `melee-pc.map`**. The port knows every global's name and object file (see 2.2). |
| Dolphin copying guest RAM | `memcpy` of MEM1 and the native `.data/.bss` sub-ranges, or dirty pages via write-watch |
| Excluding audio and XFB | Same idea: exclude synth, lbAudioAx, AX shim, VI/XFB, pad queue, card and perf globals |
| Emulated CPU clock (deterministic) | **Not free.** The port's clock is wall-clock QPC (`shim_vi.c`, `gw_time_ticks`) and must be virtualised in netplay mode. |
| Deterministic emulated FP (same JIT/interpreter) | Same exe everywhere, SSE2 only; the CRT libm calls must be replaced (4.2) |
| SFX dedupe, sound instance ids | Needed as-is, written in C around `HSD_SynthSFX*` / `lbAudioAx_*` |

Emulator-specific parts that do not transfer: CPU/JIT cache invalidation, DSP/EXI/DVD hardware
state, and the fastmem/MMU bookkeeping. Dolphin savestates of the full hardware state (about
30+ MB, slow) were never used by Slippi's rollback anyway.

---

## 2. What is the simulation state in this port?

### 2.1 MEM1: 24 MB at `0x80000000`

VERIFIED: `gw_runtime.c:46-62` does `VirtualAlloc(0x80000000, 24 MB, MEM_RESERVE|MEM_COMMIT)`, and
the address is fatal if unavailable. Layout:
- `0x80000000-0x80003100`: the lomem globals written by `gw_init_lomem`
  (`__OSBusClock` and so on). Static; `shim_os.c:45`.
- Arena from `+0x3100` to `24 MB - GW_MEX_PERSIST_SIZE` (`shim_os.c:63-75`). The top 256 KB is the
  m-ex persistent region: mexData, the interpreter's guest stack, and the `Arch_FighterFunc`
  holder (`shim_os.c:49-60`).
- Heap bookkeeping lives in MEM1, not in native memory. Aurora's `OSInitAlloc` places `sHeapArray`
  at `arenaStart` (`extern/aurora/lib/dolphin/os/OSAlloc.cpp:254`), and the cell headers are inline.
  Its statics `sHeapArray/sNumHeaps/sArenaStart/sArenaEnd` (`OSAlloc.cpp:35-38`) are fixed after
  boot. VERIFIED.
- The game carves the following from the arena: 2 XFBs (`gmmain.c:159`, `HSD_AllocateXFB`), a
  256 KB GX FIFO (`gmmain.c:160`), the audio heap, and lbHeap's heaps (`lbheap.c:38-39`):
  - heap 2: 2 KB
  - heap 3: about 5.1 MB of item/effect preloads (IfAll, ItCo, EfCoData)
  - heap 4: about 6.3 MB, lbMemory's file cache
  - heap 5: ARAM, 9.4 MB
  - heap 6: m-ex
  - the main heap: whatever remains, about 11.3 MB, with only about 35 KB in use at match setup
    (`lbheap.c:31-36` comment)

  The main heap is where HSD objects (GObjs, fighters, particles, JObj trees for spawned things)
  come from. VERIFIED for the layout; INFERRED for what lives where during a match.
- **Sim-relevant:** the main heap and every HSD ObjAlloc pool, the m-ex persist region (the guest
  stack is dead at frame boundaries, but copying it is cheap), and heap-resident file data *if*
  anything writes to it mid-match. Slippi bets that nothing does.
- **Not sim-relevant:** the XFBs and FIFO (the port renders through Aurora; INFERRED unused) and
  the audio heap. The audio heap must be excluded, not just ignored: restoring it would corrupt the
  live synth.

### 2.2 The game's native `.data/.bss`, inside the exe

VERIFIED: `pc/platform/gw_ppc.c:105-111`. Game statics live in the native image, not in MEM1. The
image is fixed at `/BASE:0x10000000 /DYNAMICBASE:NO` (`_build/build_melee_pc.bat:11-17`).

From `_build/melee-pc.map`, section 3 is `.data` (`0x6a5f8`) + `.data$r` + `.data$rs` + `.bss`
(`0xedc7c`), about 1.4 MB in total. I attributed each public symbol to its object file (size =
distance to the next symbol):

| Origin | Bytes | Notes |
|---|---|---|
| `src_melee_*` / `src_sysdolphin_*` objects | ~788 KB | game globals. Include, minus the exclusions below. |
| `<common>` (mostly `gw_*` game commons such as `gw_gmMainLib_8045A6C0` 68 KB, `gw_player_slots` 22 KB) | ~205 KB | game globals. Include. |
| `shim_*.obj`, `main.obj`, `gc_adapter` | ~303 KB | mostly *exclude*: `gw_script` 98 KB (pad script), `gw_ax_ring` 64 KB, `gw_ax_voices` 32 KB, `gw__stack_end` 64 KB |
| `gw_*.obj` (runtime, m-ex, interpreter) | ~49 KB | mostly load-time tables. Include only the m-ex bits the sim mutates (INFERRED: none per frame). |
| Aurora (`aurora_gx` 25 KB, `g_gxState`), sqlite, freetype, absl, CRT | ~40 KB | **never restore**. These are renderer and library internals, and they hold heap pointers. |
| `libs_dolphin_*` (THP work buffer, etc.) | ~16 KB | exclude (movie player) |

So the game-owned globals are about **1.0 MB**, in line with Slippi's 1.16 MB. They are *not*
contiguous: `<common>` lands at the end of `.bss`, interleaved with the others. Two ways to get the
ranges:
1. **Generate a range table from the map at build time.** Group consecutive symbols from the
   included objects, subtract a per-symbol exclusion list, and emit `gw_snap_ranges.inc`. This is
   cheap and works today.
2. **Cleaner:** have gwtool put every game global into dedicated sections (`.gwdat$a/.gwbss$a`).
   gwtool already emits a custom `.gwfix$m` section, so the mechanism exists. The linker then groups
   them into one or two contiguous ranges, bracketed by `$a`/`$z` markers like `.gwfix`. Exclusions
   stay a small symbol list. This needs `-fno-common` or explicit handling of commons.

**Exclusions** (native globals that must not be rolled back; this is the Slippi `excludeSections`
analogue). The first-pass list is INFERRED; phase (a) would confirm it by diffing:
- Audio:
  - all globals of `synth.c`, e.g. `hsd_SynthSFXNodes` 5 KB
  - `lbaudio_ax.c`, e.g. `lbl_80441064` 72 KB and `lbl_80433C64` 54 KB
  - `shim_ax.c`
- The pad queue: `HSD_PadLibData` and the `gmMain_8046B108` queue storage (`gmmain.c:46`). The pad
  alarm writes these asynchronously (`lb_0195.c:52-56`, `controller.c:55-116`).
  `HSD_PadMasterStatus/GameStatus/CopyStatus` *are* sim state and must be kept.
- VI/XFB state in `video.c` (e.g. `garbage` 5 KB), `HSD_Perf*` counters, the debug console, devcom.
- Memory card: `lbcardgame.c`, `lbcardnew.c`, and `shim_card.c`'s `gw_card_ready`.
- `lbmthp.c` (movies), lbSnap.
- The DVD/ARQ queues, if they are idle during a match (see 2.4).

### 2.3 Other simulation state

| Item | Where | Size | Rollback? |
|---|---|---|---|
| RNG seed | `static u32 seed` plus pointer `HSD_RandSeedPtr` in `sysdolphin/baselib/random.c:3-4` (native `.bss`); a single LCG `214013/2531011`. Also used by particles (`particle.c:577,1271...`) and lbAudioAx (`lbaudio_ax.c:1313`). | 8 B | yes. **Sync the seed at match start**: it is seeded from `OSGetTick()` at `gmmain.c:163`. |
| HSD ObjAlloc pools, GObj lists, JObj/particle pools | pools in main-heap MEM1; `HSD_ObjAllocData` headers in native `.bss` | in the above | yes, and both halves must be restored together |
| Scene-loop state `gm_80479D58` (logic counter `unk_0`, render counter `unk_4`, `unk_C` exit flag) | native `.bss` | small | yes, except render counters (INFERRED) |
| PPC interpreter `gw_ppc_m` (`gw_ppc.c:39`), depth and entries | native, shim | ~1 KB | **no**. It is saved and restored around every `gw_ppc_call` (`gw_ppc.c:36-38` comment), so it is idle at frame boundaries (INFERRED). Assert `gw_ppc_depth == 0` at snapshot time. |
| m-ex runtime (`gw_mex_ff`, thunks, article tables, `gw_mexdt*`, `gw_ftfunction_runtime.c:97-175, 610-657, 912`) | native, shim | ~40 KB | no. These are load-time and relocated once. Their guest-side data sits in the MEM1 persist region. |
| Deferred-callback queue `gw_deferred[256]` (`shim_vi.c` `gw_defer`) | native, shim | 4 KB | **must be empty at snapshot and restore time** (drain it at the logic-frame boundary); see 2.4 |
| Alarms `gw_alarms[16]` with wall-clock `fire_at` (`shim_os.c:241-...`) | native, shim | <1 KB | in netplay mode alarms must be on virtual time. The pad alarm is disabled entirely. |
| AX voice pool `gw_ax_voices/gw_ax_in_use` (`shim_ax.c`) | native, shim | 32 KB | **no**. It pairs with the non-rolled-back synth. The synth reads back `pb.state`, `currentVolume` and `currentAddress` (`shim_ax.c` header comment). |
| ARAM, 16 MB via `calloc` (`gw_runtime.c:63`), and `shim_ar.c`'s `gw_ar_top`/stack | native heap | 16 MB | no, assuming ARAM is only sound banks and preloads during a match. Verify with hashing in phase (a). |
| DVD state (`shim_dvd.c:45-51`, FILE*, FST) | native | - | never |
| Aurora GX state, texture caches, Dawn/SDL | native / DLL | - | never. They are renderer-only; texture caches keyed by MEM1 address see identical content after a restore. |

**Estimated snapshot size:**
- Upper bound: 24 MB MEM1 + about 1 MB globals.
- Realistic, Slippi-style: main-heap span in use + ObjAlloc pools + m-ex persist + about 1 MB
  globals, so about **4-8 MB** (INFERRED).
- Dirty bytes per frame: unknown. It is the first thing to measure (section 3).

### 2.4 Asynchronous things that touch simulation memory

VERIFIED, all in `shim_*.c`:
- **The pad alarm.** `lb_80019628` (`lb_0195.c:62-114`) arms a periodic OS alarm with period
  `x40`, 1/60 s in virtual ticks. It calls `fn_800195FC`, which runs `HSD_PadRenewRawStatus` →
  `PADRead` → `gw_PADRead`, then the card probe `lb_8001C600` and `lbSnap_8001D2BC`. The port fires
  alarms from `gw_os_run_alarms`, called in `gw_frame_tick`, `gw_wait_idle` and inside the pacing
  wait (`shim_vi.c`, `gw_pace_field` and `gw_frame_tick`). **That is wall-clock timing.**
- **DVD/ARQ/card completions.** `gw_DVDReadAsyncPrio` reads synchronously with `fread` into guest
  memory, then `gw_defer(gw_dvd_complete, ...)` (`shim_dvd.c:527-572`). ARQ does the same
  (`shim_ar.c:124`), and so does the card (`shim_card.c:156`). The callbacks run at the next pump:
  wall-clock gated (`gw_wait_idle` once per ms) or per VI tick.
- **lbMemory's chunked copy.** It re-arms a one-shot alarm 3 ms out (`shim_os.c` comment in
  `gw_os_run_alarms`), so the number of chunks per logic frame depends on wall time.
- **Audio.** `gw_ax_frame_tick` runs `HSD_SynthCallback` 0..N times per VI tick, depending on the
  **audio device's ring fill** (`shim_ax.c:1151-1188`). The synth's state is therefore a function
  of the sound card clock. It is correctly excluded from the snapshot, but it means anything game
  logic reads from the synth is nondeterministic (see 4.6).

Mid-match loads do happen in Melee: Kirby copy hats, Stadium transformations (Slippi special-cases
this), some items and effects. INFERRED. In netplay mode:
1. Run `gw_run_deferred` exactly once at the start of each logic frame, and never from the pacing
   loop.
2. Advance virtual time by exactly one field per logic frame.
3. Fire alarms only at logic-frame boundaries.

A load issued on frame F then completes on frame F+1 on both peers, including during
resimulation, and the queue is empty at every snapshot point.

---

## 3. Snapshot cost and strategy

**Budget.** The game-thread CPU for game logic plus GPU submit is "well under 1 ms" per frame
(VERIFIED, a measured comment in `shim_vi.c` above `GW_PACE_SPIN_TICKS`). A worst-case rollback
of 7 frames therefore costs about 7 ms of logic plus snapshot overhead, inside 16.67 ms.

**Options** (bandwidth figures INFERRED from typical single-thread memcpy of about 10-20 GB/s on
modern desktops, before counting cache misses):

| Strategy | Save / frame | Load | Complexity | Notes |
|---|---|---|---|---|
| A. Full copy: 24 MB MEM1 + 1 MB globals | ~1.5-3 ms | ~1.5-3 ms | trivial | Saves every frame, so the worst case (7 resim frames, each saved) is about 7×(1+2.5)+2.5 ≈ 27 ms. **Too slow at full 7-frame depth**, fine for 2-3 frames. |
| B. Region copy, Slippi-style (~4-8 MB) | ~0.3-0.8 ms | same | low | Needs the exclusion list anyway. 7-frame worst case ≈ 7×1.5+0.8 ≈ 11 ms. Feasible. |
| C. **Write-watch dirty pages + undo log** | ∝ dirty pages (plus a `GetWriteWatch` call, tens of µs for 6144 pages) | ∝ pages dirtied since target frame | medium | Add `MEM_WRITE_WATCH` to `gw_runtime.c:51`. Keep a shadow copy S = the state at the last save. At save f: for each dirty page p, append `(p, S[p])` to `undo[f]`, then set `S[p] = MEM1[p]` and reset the watch. Restore to k: first restore pages dirtied since the last save from S, then replay `undo[latest..k]` backwards; reset the watch after the restore. The globals (~1 MB) are memcpy'd each frame (~0.1 ms). |
| D. Heap-block-level (copy only allocated cells) | small | small | high | Walks OSAlloc/ObjAlloc lists. Fragile; not recommended. |

**Recommendation.**
1. Build B first. It is simple, debuggable, and matches proven prior art.
2. Instrument C's `GetWriteWatch` in phase (a) *just to measure* dirty bytes per frame.
3. If dirty bytes per frame are ≪ 4 MB, which is likely because most of MEM1 is immutable file
   data, move to C and snapshot *all* of the arena except the explicit exclusions. That removes the
   "is file data really immutable?" bet Slippi makes.

Keep a ring of `MAX_ROLLBACK+2` snapshots. Hash snapshots with xxh3 or CRC32C: about 10+ GB/s,
so hashing 8 MB takes under 1 ms. That hash is also the desync checksum. Dirty-page hashing can be
incremental.

**Is 60 Hz × N feasible?** Yes. With B, N=7 is about 11 ms worst case. With C, and a typical
1-2 frame rollback, well under 5 ms. INFERRED; phase (b) must measure it.

---

## 4. Determinism

**The goal is PC↔PC determinism of the same exe and the same ISO.** PC↔console equivalence is a
separate, harder goal (section 7).

### 4.1 Floating point in game code: low risk
- VERIFIED: gwtool retargets to `i686-pc-windows-msvc`, `-mcpu=pentium4`,
  `+sse,+sse2,+cmov,+cx8,+mmx,+fxsr`, with default `TargetOptions`, so `AllowFPOpFusion=Standard`
  (`gwtool.cpp:81-83, 660-671`). There is no FMA feature, so `llvm.fmuladd` (clang's default
  `-ffp-contract=on`) is lowered to a separate mul and add. That result is the same on every x86 CPU.
- `f32`/`f64` arithmetic goes through SSE2 scalar ops, which are exactly IEEE-rounded. The x87 unit
  is only used for 32-bit ABI float returns (`fld`/`fstp`, which is exact). `long double` is
  rejected (`gwtool.cpp:540`).
- Because the codegen is fixed in the binary, **one exe gives the same bits on Intel, AMD and any
  Windows version**, as long as MXCSR matches. Pin MXCSR (round-to-nearest, FTZ/DAZ off) at the
  start of every logic frame in netplay mode; a driver or DLL could in principle change it
  (INFERRED low risk). Assert or restore it.
- `__frsqrte` is emulated bit-exactly in game-world code (`pc/gameworld/gekko_fp.c`), and the
  paired-single matrix routines are plain C with the operand order preserved
  (`pc/gameworld/mtx_pc.c` header). Both are deterministic.
- The PPC interpreter (`gw_ppc.c:1230-1330`) computes Gekko FP in double and rounds for the single
  forms. It is compiled once into the exe, so it is deterministic.

### 4.2 The host CRT math: real risk
VERIFIED:
- `shim_libc.c:83-87` forwards `sinf/cosf/tanf/atanf/logf` to the MSVC CRT. The exe links
  `MSVCRT`, meaning the dynamic `ucrtbase.dll` that ships with Windows.
- `gw_sinf` resolves to `shim_libc.obj` in the map. The game's own `src/MSL/trigf.c` `sinf` is not
  what runs.
- `atan2f`/`acosf` are game-world (`src/melee/lb/lbtrigf.c:22,45`), but they may call `atanf`.
- The imports list shows 74 `sinf`, 75 `cosf` and 84 `atan2f` call sites, covering fighter physics,
  knockback angles and camera.

**The risk** (INFERRED, but a well-known class of problem): `ucrtbase` differs between Windows 10
and 11 builds and can dispatch on CPU features. Different last-bit results then give a slow
divergence in positions, which becomes a desync.

**The fix:** make these game-world functions. Compile MSL `trigf.c`/`math.c`, or a vetted
fdlibm/musl `sinf`, through gwtool, so the exe carries its own implementation. MSL is also closer
to console behaviour (the `MSL_TrigF_80400770/774` tables are already noted in the
`shim_libc.c:8-10` header). Audit every other host call that returns data into the sim: `memcpy`,
`strcmp` and the like are fine; `qsort` stability, if used, needs a check.

### 4.3 Time
VERIFIED: `OSGetTime`/`OSGetTick` return `gw_time_ticks()`, the free-running QPC clock
(`shim_os.c` "time" section, `shim_vi.c` `gw_time_ticks`). Uses inside game code:
- The RNG seed (`gmmain.c:163`).
- `lbtime.c:56`, which is play-time/record stats.
- lbsnap and lbmthp.
- `HSD_PerfSet*`, perf counters only.
- Alarm scheduling, which covers the pad sampling cadence and the lbMemory copy.

**Required:** a "deterministic time" mode in which the virtual clock is `logic_frame × 675000`
(40.5 MHz / 60) and nothing is wall-clock. `tools/replay/README.md` ("Prerequisite: deterministic
time") already asks for exactly this.

### 4.4 Pointers and addresses: low risk, with one caveat
- The exe has a fixed base (VERIFIED), so native function and global pointers stored in MEM1 are
  identical across machines for the same build. MEM1 is fixed at `0x80000000` (VERIFIED), so heap
  pointers are identical *given the same allocation history*.
- ARAM is `calloc`'d, so its address varies. The game addresses ARAM by offset (`shim_ar.c`
  `gw_ar_addr`; INFERRED that no raw host ARAM pointer reaches sim state).
- Stack addresses vary. A native stack address stored in persistent game state would be a bug
  anyway.
- DLL (Dawn/SDL) pointers never enter game state (INFERRED).
- **Caveat: allocation history.** The two peers reach the match through different menu sequences,
  so heap layout and uninitialised heap contents can differ. `-ftrivial-auto-var-init=zero`
  (`pipe_win.sh`) fixes uninitialised *locals* only. `OSAllocFromHeap` does not zero. Mitigations,
  in increasing strength:
  1. On entering the netplay in-game scene, both peers destroy and recreate the scene heaps and
     `memset` them to zero. Melee already resets heaps per scene (`lbheap.c`).
  2. Make the host's snapshot of the sim state at match start authoritative and send it
     compressed. That is possible only because both peers run the same exe, and it guarantees an
     identical start.

  Slippi lives with option 1-ish, since its clients take the same scene path from CSS.

### 4.5 Threads
VERIFIED: the game is single-threaded (`shim_os.c` "threads and contexts" comment). Thread
creation reports failure, and interrupts are no-ops. The Aurora render worker and the SDL audio
callback never touch game memory (`shim_vi.c` profiler comment; `shim_ax.c` header). The GC
adapter reader feeds `PADRead` only. **Low risk.**

### 4.6 Audio feeding back into logic: medium risk
- The synth advances at the device rate (2.4), and the audio globals are excluded from rollback.
  Any game-logic read of synth state becomes nondeterministic: "is this SFX still playing",
  voice-steal results, or the **sound instance ids** that fighters store in order to stop looping
  sounds.
- Resimulation replays `SFX_PlaySFX` calls, which advances synth id counters differently on each
  peer. The effect is benign for gameplay but pollutes the state hash.
- The fix is Slippi's: deterministic instance ids, plus dedupe and kill logic around the synth
  entry points (1.1). Fighter fields holding sound handles may need to be excluded from the hash.

### 4.7 Configuration: must be identical and exchanged in the handshake
- The exe hash and the ISO hash (plus `mods/` contents: Sonic/m-ex, Target Test mods from
  `gw_TTMod_Count`).
- m-ex opt-in features read from the environment, e.g. `Mex_Enabled("xy_disables_start")` inside
  `HSD_PadRenewMasterStatus` (`controller.c:368-386`), the heap sizes (`lbheap.c:38`), UCF and
  similar toggles, and the match rules.
- Any per-user visual option that consumes the RNG is a desync (the FD background precedent).

### 4.8 Verdict

Cross-machine determinism of the same exe is **plausible**. The arithmetic is already fixed, and
the fixes for the remaining hazards are well bounded:
1. Own libm.
2. Virtual time.
3. Deterministic deferred work.
4. Per-frame input injection.
5. A synced seed.
6. Scene-heap zeroing.
7. An audio firewall.
8. A config handshake.

Phase (a) is what proves it.

---

## 5. Input

**Path today** (VERIFIED):
1. The pad alarm fires `fn_800195FC` (`lb_0195.c:52`), which calls `HSD_PadRenewRawStatus(0)`
   (`controller.c:55`). That calls `PADRead(now.stat)`, i.e. `gw_PADRead` (`shim_pad.c`).
2. `gw_PADRead` calls Aurora `PADRead`, byte-swaps the buttons, overlays the raw GC adapter
   (`gc_adapter.c`) and the keyboard (W/A/S/D/J/K/Enter/F1/arrows via `GetAsyncKeyState`), then
   applies `MELEE_PAD_SCRIPT` and `MELEE_PAD_LIVE` to channel 0.
3. The sample is pushed into a 5-deep raw queue (`HSD_PadInit(5, gmMain_8046B108, ...)` at
   `gmmain.c:46`). When the queue is full, `qtype 0` *merges* buttons into the oldest entry
   (`controller.c:78-90`).
4. The scene loop reads `pad_queue_count` (`gmscene.c:292`, via `lb_80019894`). Each logic frame
   pops one entry with `HSD_PadRenewMasterStatus` (`gmscene.c:304` → `controller.c:346-...`), then
   `lb_80019900` does `HSD_PadRenewGameStatus/CopyStatus` (`gmscene.c:314`).

**`MELEE_PAD_SCRIPT` injects at the wrong layer for determinism.** It consumes one script frame per
`PADRead` (`shim_pad.c` `gw_pad_script_apply`), which is one per alarm sample on wall-clock time.
Samples can be merged by a full queue or batched across render frames, so the same script is not
guaranteed to produce the same per-logic-frame inputs. It is fine for smoke tests, but not a
determinism oracle.

**Netplay and replay injection point.**
- In netplay/replay mode, bypass the raw queue entirely. The netplay module owns
  `pad_queue_count`, which is the number of logic frames to run this render tick including
  resimulation. For each logic frame it supplies the four `PADStatus` records, the pre-clamp raw
  bytes, straight into the pop in `HSD_PadRenewMasterStatus`. That is a `TARGET_PC` hook where
  `qread` is chosen (`controller.c:359-362`).
- Local input is still sampled through `gw_PADRead` once per *new* frame, i.e. the "local input
  for frame F+delay".
- Remote input comes from the network. Prediction is "repeat last" (GGPO default, Slippi-like).
- The wire format is the 8 significant bytes of `PADStatus` per port:
  - `button` u16
  - `stickX` / `stickY`
  - `substickX` / `substickY`
  - `triggerL` / `triggerR`
  - the analog bytes / `err` as needed

  Including `err` matters: the connected state is sim state.
- The same hook implements `MELEE_REPLAY_SCRIPT` from `tools/replay/README.md` (frame-indexed input
  per port) and an input *recorder* (`MELEE_INPUT_LOG`). Together they give the determinism
  harness its inputs.
- Rumble (`HSD_PadRumbleInterpret` in the raw path, `HSD_Rumble*` from logic) must be suppressed
  during resimulation and applied only for confirmed frames. Slippi has `HandleRumble.asm`.

---

## 6. Frame loop control and fast-forward resimulation

VERIFIED: `gm_801A4D34` (`gmscene.c:271-380`) has the following shape:

```
loop:
  wait until pad_queue_count > 0          (292-295)
  for i in 0..pad_queue_count:            (302)
     HSD_PerfSetStartTime; renew master pad; renew game/copy pad
     gm_EvaluateAllControllerInputs; on_frame()
     lbAudioAx_80027DF8; pre_gobj_proc; HSD_GObj_RunProcs      (343-347)
  render once: HSD_StartRender, GObj render procs, HSD_VICopyXFBAsync (372-376)
```

Presentation, pacing, event pumping, alarms, deferred work and audio mixing all happen in
`gw_frame_tick` → `VIWaitForRetrace` (`shim_vi.c`), which is reached from the render/XFB path, not
from the logic loop. **Fast-forward is therefore native: running k extra iterations of the inner
loop draws nothing.**

What needs gating in netplay mode:
1. **The wait at 292-295.** Replace it with the netplay scheduler: time sync and frame advantage
   decide whether to advance 0 or 1 new frame, plus the resimulation count.
2. **Snapshot hooks:**
   - at the top of each inner iteration: the save point, Slippi's `0x801a4de4`
   - at the loop-back: Slippi's `0x801a5014`
   - a restore before the first resimulated iteration
3. **Audio:** the SFX dedupe, kill and instance-id layer (4.6). Mixing needs no change, since
   `gw_ax_frame_tick` runs per VI tick.
4. **Rumble and any other host side effects from logic:** card writes (end of match only), lbSnap
   screenshots and debug output. Suppress them during resimulation.
5. **`gw_run_deferred` and `gw_os_run_alarms`:** move them to the logic-frame boundary in netplay
   mode (2.4). Remove them from `gw_pace_field`'s pump.
6. **Pacing:** `gw_pace_field` targets 60 Hz on QPC. Netplay time sync nudges it: GGPO-style "wait
   N frames" when ahead, or Slippi-style small period adjustments. `lb_80019880(u64)` already sets
   the desired pad period (`lb_0195.c:117-120`), but pacing belongs in the shim, not in the game's
   alarm.

For headless determinism runs, also add a "no pacing, no present" mode. `--test` already runs
without a window (`main.c`), so the plumbing exists.

---

## 7. Networking layer options

| Option | License | Fit |
|---|---|---|
| **GGPO SDK** (pond3r/ggpo) | MIT (INFERRED from memory) | C API, Windows-native, built-in UDP and SyncTest. It is old and unmaintained, but small and battle-tested. Builds 32-bit. |
| **GekkoNet** | BSD-2-Clause (VERIFIED via search) | Modern C++ with a C API, GGRS-style request model, pluggable transport. Needs a 32-bit build check. |
| **GGRS** | MIT / Apache-2.0 | Best-maintained, but Rust. Needs a C FFI crate and an `i686-pc-windows-msvc` staticlib linked into a C exe. |
| Hand-rolled (UDP + input ring + frame advantage) | - | About 1-2k lines. Worth it only if the libraries' session models fight the scene loop. |

**Recommendation:** GGRS-style request semantics (GekkoNet or GGPO) mapped onto the hooks in
section 6. Use the library's SyncTest in phase (c) before any socket exists. Transport is UDP (with
`WSAStartup`) and needs NAT traversal and a relay later. Matchmaking is out of scope. The
handshake must carry the exe hash, ISO and mod hashes, config and rules, and the RNG seed.

**Slippi compatibility.** Talking to Slippi Dolphin is **not realistic**, and the reason is not the
state layout. Each Slippi client keeps its savestates private; only inputs, frame numbers and
checksums cross the wire (`SlippiNetplay.h`). Interop would require all of the following:
1. The port's simulation must be **bit-identical to console Melee running Slippi's online
   codeset**. The online codeset changes gameplay: `FreezeDeadUpFallPhysics`,
   `WhispyBlowDirFix`, the FD background RNG fix, UCF, and so on. The port differs from console
   arithmetic on purpose or by construction:
   - Gekko fuses `fmadds`; here mul+add are separate (4.1).
   - Trig runs on the host CRT (4.2).
   - Gekko's single-precision quirks.
2. Slippi's netplay protocol (ENet), versioning, its matchmaking/auth servers, and the checksum
   algorithm, which folds fighter fields at console addresses.
3. The same menu/scene flow.

(1) is the blocker. `tools/replay/` (a Slippi `.slp` vs port-trace differ) is exactly the tool that
would measure it. If the port ever replays full `.slp` matches frame-exactly, that is necessary but
not sufficient evidence, and interop becomes a (large) protocol project. Plan for port↔port only.

---

## 8. Phased plan

**(a) Determinism harness.** Estimated 1.5-2.5 weeks.
1. A `MELEE_DETERMINISTIC=1` mode:
   - virtual clock = logic frames × 675000 ticks
   - alarms and deferred work only at logic-frame boundaries
   - the pad alarm disabled
   - the RNG seed from the environment
   - no pacing
2. Input injection at the `HSD_PadRenewMasterStatus` pop, from a per-logic-frame log
   (`MELEE_REPLAY_SCRIPT`), plus a recorder (`MELEE_INPUT_LOG`).
3. A per-frame state hash. First the Slippi-style player checksum and the RNG seed, then a
   whole-candidate-state hash (MEM1 arena minus exclusions, plus the game-globals range table
   generated from the map). Also `MELEE_STATE_TRACE` (`tools/replay/README.md`).
4. A "diff dump": on the first mismatching frame, dump both snapshots and attribute the differing
   bytes to symbols through `melee-pc.map` and to heap cells. This is how the exclusion list gets
   *discovered* rather than guessed.
5. Instrument write-watch to measure dirty bytes per frame.
6. Replace the CRT `sinf/cosf/tanf/atanf/logf` with game-world code.
7. Run the same log twice on one machine, then on two machines (for example Win10 AMD vs
   Win11 Intel).

**(b) In-process savestates.** Estimated 1.5-3 weeks.
- `gw_snap_save(slot)` / `gw_snap_load(slot)` over the range table (strategy B), with asserts: the
  deferred queue is empty, `gw_ppc_depth == 0`, and the tick is at the logic boundary.
- Test: save at frame N, run to N+120, load N, rerun with the same inputs. The hashes at every
  frame must equal those of the first pass. Repeat at random N across many scenes (VS, items,
  Kirby, Stadium, Ice Climbers, Sonic/m-ex).
- Then measure cost. Move to write-watch (strategy C) if needed.

**(c) Local rollback.** Estimated 2-3 weeks.
- Scene-loop hooks (section 6).
- A SyncTest mode that rolls back k frames every frame and compares hashes.
- A fake-latency mode: port 2 is driven by a delayed and jittered input source with "repeat last"
  prediction.
- SFX dedupe, kill and instance ids; rumble gating.
- Verify visually and audibly that there are no duplicate or ghost sounds.

**(d) Networking.** Estimated 3-6 weeks for a direct-IP MVP.
- Integrate the library, UDP transport, handshake (hashes, config, seed, rules), time sync, input
  delay setting, and checksum exchange with an on-screen desync notice.
- Disconnect handling and a minimal "connect to IP, then both go to CSS/stage" flow.
- Lobby, NAT traversal, relays and spectators come later.

**Riskiest unknowns, in order:**
1. Audio and logic coupling: how much game logic reads synth state or stores sound handles.
2. Mid-match async loads and alarms: Kirby hats, Stadium, item and effect loads, lbMemory copy
   chunking. All of them must become frame-deterministic.
3. File data in heaps 3 and 4 being mutated mid-match. This decides whether the snapshot can
   skip it.
4. Dirty bytes per frame. This decides between strategies B and C.
5. Hidden native state inside shims that the sim reads back:
   - `gw_ax_*`, whose voice-steal results feed the synth
   - `gw_ar_*`
   - `gw___OSCurrHeap`
   - Aurora `OSAlloc` statics if heaps get recreated mid-match
6. The m-ex interpreter path (Sonic): whether it keeps any per-frame state outside MEM1 and
   fighter structs.
7. Uninitialised heap reads that make menu history leak into the match.

---

## 9. Recommended first step

Build the **deterministic replay mode (phase (a) items 1-3)** and nothing else:
- a virtual clock driven by logic frames
- alarms and deferred work at frame boundaries
- injection at the `HSD_PadRenewMasterStatus` pop from a per-logic-frame input log
- the RNG seed from the environment
- a per-frame CRC of the RNG seed, the player blocks and the game `.data/.bss` range table

Run one recorded 1v1 two times on one machine and diff. Every later phase depends on that run
being clean. It is also exactly the work `tools/replay/README.md` already lists as the port-side
prerequisite, so it pays off for replay debugging even if netplay never ships.

## 10. Open questions

1. Which native globals does gameplay read that are updated off the logic path? Candidates are
   perf, VI, card, the pad queue, and synth "is playing" queries. Phase (a)'s diff dump answers it.
2. Does any game-logic path consume `HSD_Rand` from render or draw callbacks (in
   `HSD_GObj_80390FC0` render procs) or from the audio callback? If so, the RNG advances with
   render or audio cadence, not logic. `particle.c` uses RNG heavily; confirm it runs only in
   GObj *procs*.
3. Are the ARAM (heap 5) contents or `gw_ar_*` state modified during a match?
4. Exact dirty bytes per logic frame in a busy 4-player match with items.
5. Does anything in the logic loop call `VIWaitForRetrace` or a GX function? That would present or
   pace mid-resimulation. `lbSnap` and debug paths are suspects.
6. Which is simpler to keep correct: excluding audio globals by symbol, or moving the audio
   globals into their own gwtool section?
7. Can gwtool place game globals in dedicated sections (`.gwdat/.gwbss`) without disturbing the
   `.gwfix` fixups and the `<common>` handling? That would make the snapshot range 1-2 contiguous
   spans.
8. Is scene-heap zeroing at netplay match entry enough, or is a host-authoritative initial state
   transfer needed?
9. Does GGPO/GekkoNet build cleanly as 32-bit with the MSVC toolset used by `build_melee_pc.bat`?
   Otherwise, go hand-rolled.
10. The long-term question: frame-exact `.slp` replay against console. It is a prerequisite for any
    Slippi-interop discussion, and a strong correctness signal for the port on its own.

Sources:
- [Ishiiruka SlippiSavestate.cpp](https://github.com/project-slippi/Ishiiruka/blob/slippi/Source/Core/Core/Slippi/SlippiSavestate.cpp)
- [Ishiiruka SlippiNetplay.h](https://github.com/project-slippi/Ishiiruka/blob/slippi/Source/Core/Core/Slippi/SlippiNetplay.h)
- [Ishiiruka EXI_DeviceSlippi.cpp](https://github.com/project-slippi/Ishiiruka/blob/slippi/Source/Core/Core/HW/EXI_DeviceSlippi.cpp)
- [slippi-ssbm-asm Online/Core](https://github.com/project-slippi/slippi-ssbm-asm/tree/master/Online/Core)
- [GekkoNet](https://github.com/HeatXD/GekkoNet)
