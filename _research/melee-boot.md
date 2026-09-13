# Melee boot & runtime structure (doldecomp/melee) — for the native Windows port

All paths relative to `C:\gdm\melee`. Line numbers from the current checkout.

---

## 1. `main()` and the init sequence

**`src/melee/gm/gmmain.c:130` `int main(void)`**. Exact order (line numbers):

| # | Call | Line | Notes |
|---|---|---|---|
| 1 | `OSInit()` | gmmain.c:135 | |
| 2 | `VIInit()` | :136 | |
| 3 | `DVDInit()` | :137 | |
| 4 | `PADInit()` | :138 | |
| 5 | `CARDInit()` | :139 | |
| 6 | `OSInitAlarm()` | :140 | |
| 7 | `db_GetGameLaunchButtonState()` | :141 | `src/melee/db/dbinit.c:31` — **blocking**: loops `VIWaitForRetrace(); PADRead(status)` until no pad returns err -2/-3, then loops `while (CARDProbeEx(0,&memSize,&sectorSize) == -1) VIWaitForRetrace();`. **First hang risk.** |
| 8 | `gmMain_8015FDA4()` | :142 (defn :61) | `DVDConvertPathToEntrynum("/develop.ini")`; if absent → `DbLevel = DbLKind_Master`. Retail ISO has no develop.ini. |
| 9 | 48 MB check | :143-145 | `if (OSGetConsoleSimulatedMemSize()/(1024*1024) == 48) OSAllocFromArenaHi(0x01800000, 4);` — steals 24 MB back on a devkit so the game still sees a 24 MB arena. |
| 10 | `arena_size = OSGetArenaHi() - OSGetArenaLo()` | :146 | Only used for the `OSReport` banner. |
| 11 | `HSD_SetInitParameter(XFB_MAX_NUM, 2)` | :147 | |
| 12 | `HSD_SetInitParameter(RENDER_MODE_OBJ, &GXNtsc480IntDf)` | :148 | |
| 13 | `HSD_SetInitParameter(FIFO_SIZE, 0x40000)` | :149 | 256 KB |
| 14 | `HSD_SetInitParameter(HEAP_MAX_NUM, 4)` | :150 | passed to `OSInitAlloc` |
| 15 | `db_SetupCrashHandler()` | :151 | `src/melee/db/dberror.c:62`. `DBIsDebuggerPresent()`; `OSAllocFromArenaLo(0x2000,4)`; `OSSetErrorHandler(x, …)` for x in 0..15 except 4,7,8,9. |
| 16 | `HSD_AllocateXFB(2, &GXNtsc480IntDf)` | :152 | `baselib/initialize.c:85` — carves 2 XFBs out of ArenaLo, `OSSetArenaLo`. fb_size = `roundup16(fbWidth)*xfbHeight*2`. |
| 17 | `HSD_GXSetFifoObj(GXInit(HSD_AllocateFifo(0x40000), 0x40000))` | :153 | fifo also carved from ArenaLo (`initialize.c:118`). |
| 18 | `HSD_InitComponent()` | :154 | `initialize.c:50` → `HSD_OSInit()`, `HSD_VIInit()`, `HSD_GXInit()`, `HSD_DVDInit()` (empty, :82), `HSD_IDSetup()`, **`VIWaitForRetrace()`**, `HSD_ObjInit()`, `HSD_LogInit()`. |
| 19 | `GXSetMisc(1, 8)` | :155 | |
| 20 | `*seed_ptr = OSGetTick()` | :156 | RNG seed |
| 21 | **`lbAudioAx_8002838C()`** | :157 | `src/melee/lb/lbaudio_ax.c:2090` — **audio + ARAM init**: `ARInit(ar_stack,16)`, `ARQInit()`, `AIInit(NULL)`, computes bank sizes, `AXDriver_8038E498(AX_MAX_VOICES,0,0x40,total)` → `HSD_SynthInit` (`baselib/synth.c:1469`: `AXInit()`, `AISetDSPSampleRate(0)`, `ARAlloc(0x500)`, `ARAlloc(bank_size)`, `AXRegisterCallback(HSD_SynthCallback)`), then `AXDriver_8038E30C` for reverb-std (53 KB static) and delay (71 KB static) aux buffers, then 3× `HSD_SynthSFXAllocateBank`. |
| 22 | `lb_80019AAC(&gmMain_8015FD24)` | :158 | pad/timing init (§3). The callback (`gmmain.c:42`) does `PADSetSpec(5)`, `HSD_PadInit(5, …, 12, …)` and sets stick/trigger clamp params. |
| 23 | `HSD_VISetUserPostRetraceCallback(&gmMain_8015FDA0)` | :159 | empty stub (`gmmain.c:57`). |
| 24 | `HSD_VISetUserGXDrawDoneCallback(&HSD_VIDrawDoneXFB)` | :160 | **critical** — this is what advances XFB state machine (§3). |
| 25 | `HSD_VISetBlack(0)` | :161 | |
| 26 | `lbMemory_8001564C()` | :162 | ARAM allocator init (§2) |
| 27 | `lbHeap_80015F3C()` | :163 | heap layout compute (§2) |
| 28 | `lbDvd_80018F68()` | :164 | preload cache init |
| 29 | `lbArq_80014D2C()` | :165 | `lb/lbarq.c:158` — 10-node ARQ request pool |
| 30 | `lb_8001C5BC()` | :166 | |
| 31 | `lb_8001D21C()` | :167 | `lb/lbcardgame.c:298` — `_p(x0) = CARDProbe(0)` |
| 32 | `lbSnap_8001E290()` | :168 | screenshot lib |
| 33 | `gmMainLib_8015FCC0()` | :169 | `gmmain_lib.c:1361` — **`skip_intro = (OSGetResetCode() == 0x80000000)`**, `resetting=false`, `x10 = lbTime_GetTimeInSeconds()`. |
| 34 | `lbMthp_8001F87C()` | :170 | THP/MTH player init |
| 35 | `HSD_SisLib_803A6048(0xC000)` | :171 | text/SIS heap, 48 KB via `HSD_MemAlloc` (`baselib/sislib.c:459`). |
| 36 | `gmMainLib_8015FBA4()` | :172 | `gmmain_lib.c:1328` — zeroes 0x10A30 of save state, `DVDConvertPathToEntrynum("/usa.ini")` to pick US vs JP language, installs default `GameRules`, then **`lbAudioAx_80028690()`** which is the big SSM/SEM loader (§5). |
| 37 | USB/dev-server loop | :174-181 | Only if `DbLevel != Master && launch buttons & R`. Skipped on retail. |
| 38 | `db_InitScreenshot()` | :183 | |
| 39 | `OSReport` banner | :184-206 | Includes `lbMemory_800154BC` (ARAM free), `lbTime_GetTimeInSeconds` → `gm_801692E8` calendar. |
| 40 | `db_EnableItemSpawns()` | :211 | |
| 41 | `init_spr_unk()` | :214 | `mtspr 0x392..0x395` — **MWERKS/Gekko only**, `#ifdef MWERKS_GEKKO`, no-op for the port (gmmain.c:100). |
| 42 | `db_ClearFPUExceptions()` | :217 | `dberror.c:16` — `PPCMtmsr(PPCMfmsr() | 0x900)`, save/load FPU context, clear FPSCR. Must become a no-op. |
| 43 | **`gm_801A4510()`** | :218 | never returns — the scene loop (§3/§9). |

**SDK callbacks registered by the game (must be dispatched by the shim):**
- `VISetPreRetraceCallback(HSD_VIPreRetraceCB)` + `VISetPostRetraceCallback(HSD_VIPostRetraceCB)` — `baselib/video.c:425-426`.
- `GXSetDrawDoneCallback(HSD_VIGXDrawDoneCB)` — `video.c:429`.
- HSD user hooks: post-retrace = `gmMain_8015FDA0` (no-op), GX-drawdone = `HSD_VIDrawDoneXFB`.
- `AXRegisterCallback(HSD_SynthCallback)` — `synth.c:1477` (AX 5 ms frame from DSP/AI interrupt).
- `OSSetPeriodicAlarm(&alarm, period, period, fn_800195FC)` — `lb/lb_0195.c:109`; `fn_800195FC` (`lb_0195.c:56`) = `HSD_PadRenewRawStatus(0); lb_8001C600(); lbSnap_8001D2BC();`. **This alarm is the game's heartbeat** (see §3).
- `OSSetPeriodicAlarm` for the MTH movie decoder — `lb/lbmthp.c:544` (`fn_8001F2A4` at 1/60 s).
- `OSSetAlarm(&p->alarm, OSMillisecondsToTicks(3), fn_80015184)` — `lb/lbmemory.c:207/230`, chunked ARAM→MRAM memcpy.
- `OSSetErrorHandler` × 12 and `HSD_SetPanicCallback` — `dberror.c:62`.
- DVD: `DVDReadAsyncPrio(..., HSD_DevComDVDCallback / HSD_DevComDVDMemCallback, 2)` — `baselib/devcom.c:341/352`.
- ARQ: `ARQPostRequest(..., HSD_DevComARAMCallback / HSD_DevComStdCallback / HSD_DevComDVDARAMEndCallback)` — `devcom.c` throughout; `lbArq_80014BD0` → `ARQPostRequest(..., lbArq_80014AC4)` (`lbarq.c:133`).
- CARD: `CARDMountAsync/CheckAsync/FormatAsync/DeleteAsync/RenameAsync(..., fn_8001A008)` — `lb/lbcardnew.c:257,290,429,459,486`.

---

## 2. Memory model

### Arena acquisition
`HSD_OSInit()` (`baselib/initialize.c:159`) is the whole story:
```
old_lo = OSGetArenaLo(); old_hi = OSGetArenaHi();
old_lo = OSInitAlloc(old_lo, old_hi, iparam_heap_max_num /*=4*/);
OSSetArenaLo(old_lo);
new_lo = OSRoundUp32B(old_lo); new_hi = OSRoundDown32B(old_hi);
HSD_Synth_804D6018 = OSCreateHeap(new_lo, new_lo + iparam_audio_heap_size);  // 512 KB audio heap
new_lo += 512K;
hsd_heap_next_arena_lo = new_lo; hsd_heap_next_arena_hi = new_hi;
current_heap = OSCreateHeap(new_lo, new_hi); OSSetCurrentHeap(current_heap);
HSD_ObjSetHeap(new_hi - new_lo, NULL);
OSSetArenaLo(new_hi);   // arena fully consumed
```
`HSD_DEFAULT_AUDIO_SIZE = 512*1024`, `HSD_DEFAULT_FIFO_SIZE = 256*1024` (`baselib/initialize.h:10-12`). Order matters: XFB (2 × 640×480×2 = 1.2 MB) and FIFO (256 KB) are bump-allocated from ArenaLo *before* `OSInitAlloc`, by `HSD_AllocateXFB`/`HSD_AllocateFifo`.

`HSD_GetNextArena(&lo,&hi)` (`initialize.c:198`) hands the post-audio-heap range to `lbHeap`.
`HSD_CreateMainHeap(lo,hi)` (`initialize.c:204`) destroys/recreates the current OSHeap over a new range and calls the `_HSD_*ForgetMemory` callbacks — **called every scene transition** from `lbHeap_80015900`.

### lbHeap layout (`src/melee/lb/lbheap.c`)
Descriptor table `lbHeap_803BA380[5]` at **lbheap.c:21-23** — `{idx, type, prev_idx, size}`:
```
{ 2, type 1 (from arena LO),  prev 6(none), 0x800     }   // 2 KB
{ 3, type 1 (from arena LO),  prev 2,       0x4F8800  }   // 5,212,160 B ≈ 4.97 MB
{ 4, type 2 (from arena HI),  prev 6(none), 0x64B400  }   // 6,599,168 B ≈ 6.29 MB
{ 5, type 4 (from ARAM LO),   prev 6(none), 0x96C800  }   // 9,881,600 B ≈ 9.42 MB  (in ARAM)
{ 6, 0, 0, 0 }                                            // terminator
```
Types: 0 = OSHeap, 1 = grows up from arena_lo, 2 = grows down from arena_hi, 3 = ARAM handle heap, 4 = ARAM-resident.
- Heap **0** = "main heap" = `HSD_CreateMainHeap(arena_lo, arena_hi)` over whatever is left after the transient heaps (`lbheap.c:154-159`).
- Heap **1** = ARAM heap handle (`lbMemory_800154D4(aram_lo, aram_hi)`, `lbheap.c:163-167`).
- Heaps **2..5** are created/destroyed per scene by `lbHeap_80015900` (`lbheap.c:88`) according to each heap's `transient` flag, which `lbDvd_80018CF4` sets from the scene's `preload` level (`lbdvd.c:765-822`).
- `lbHeap_80015F3C` (`lbheap.c:280`) computes the `start` fields once at boot from `HSD_GetNextArena` + `lbMemory_800154BC`.

### ARAM
`lbMemory_8001564C` (`lbmemory.c:314`):
```
a_arenaLo = ARAlloc(0x20); ARFree(&size[2]);
a_arenaHi = (ARGetSize() > 0x01000000U) ? 0x01000000U : ARGetSize();
```
→ **ARAM window is clamped to 16 MB** and addresses are *ARAM-space* (0-based), not MRAM. 0x83-entry free-list `MemEntry` pool, 6 `Handle`s.

**What lives in ARAM:** heap 5 (9.42 MB) holds preloaded DAT archives/raw data whose `heap` id is 4 or 5; `HSD_SynthInit` `ARAlloc`s 0x500 (DSP/zero buffer) plus the SFX bank region (`hsd_SynthSFXBankHead[0]`, size = sum of the three `HSD_SynthSFXAllocateBank` sizes computed in `lbAudioAx_8002838C`) — i.e. **all .ssm sample data is resident in ARAM**.

**How ARAM comes back:**
- `lbArq_80014BD0(src_aram, dst_mram, len, cb, arg)` (`lbarq.c:106`) — `DCInvalidateRange(dest,len)` then `ARQPostRequest(..., ARAM→MRAM, lbArq_80014AC4)`. If `callback == NULL` it **spins**: `while (lbArq_80014ABC(rp) != LB_ARQ_STATE_DONE) {}` (lbarq.c:143) with interrupts *restored*. A no-op ARQ that never fires the callback hangs here forever.
- `HSD_DevComRequest` types (`baselib/devcom.c`): `0x03` = zero-fill ARAM, `0x0B` = MRAM→ARAM, `0x19` = ARAM→MRAM direct, `0x1A` = ARAM→relay buffer, `0x1B` = ARAM→ARAM via relay, `0x21` = DVD→MRAM, `0x22` = DVD→relay buffer, `0x23` = DVD→ARAM via relay. Relay buffers are 2 × `DEVCOM_BUF_SIZE` (0x4000, from the `for (i=0x1000; i>0; i--) *p++ = 0;` zeroing at devcom.c:141).
- `lbMemory_8001529C` / `lbMemory_80015320` (`lbmemory.c:245/265`) — ARAM heap **defragmenter**. If the handle address is `< 0x80000000` it issues a DevCom type-`0x1B` ARAM→ARAM move; otherwise it does a chunked `memcpy` at 0x19000 bytes per 3 ms alarm tick (`fn_80015184`, lbmemory.c:184).

### Every hardcoded address/size assumption in *game* code
Greps over `src/melee` + `src/sysdolphin` found surprisingly few. The port-relevant ones:
- `gmmain.c:143` — `OSGetConsoleSimulatedMemSize()/(1024*1024) == 48` → `OSAllocFromArenaHi(0x01800000, 4)`. **0x01800000 = 24 MB.** Shim: report 24 MB simulated size (or 48 and honour the alloc) so the arena is retail-sized.
- `lbmemory.c:68` — `if (((u32)arenaLo < 0x80000000U) && ((u32)arenaHi < 0x80000000U))` — the *only* thing that distinguishes ARAM addresses from MRAM addresses. **The port must keep ARAM addresses below 0x80000000 and MRAM addresses at/above it.**
- `lbmemory.c:281` — `if ((u32)handle->x4_lo < 0x80000000U)` — same ARAM-vs-MRAM test, selects DevCom vs memcpy path.
- `lbfile.c:126` — `type = (dst >= 0x80000000) ? 0x21 : 0x23;` — DVD→MRAM vs DVD→ARAM, same test.
- `lbmemory.c:318` — ARAM hi clamped to `0x01000000` (16 MB).
- `lbheap.c:21-23` — the four heap sizes above.
- `gmmain_lib.c:1364` — `OSGetResetCode() == 0x80000000` (the "reset via reset button" magic) → `skip_intro`.
- `baselib/debugconsole_main.c:837/840/1665` — `sp < 0x80000000u`, `>= OSGetPhysicalMemSize() + 0x800000000`, `% memsize + 0x80000000`. Debug-console stack-trace only; DbLevel-gated, harmless.
- `gmmain_lib.c:1329` — `memzero(gmMainLib_804D3EE0, 0x10A30)` (save-state block size).
- **No `0x800000xx` / `0x800030xx` low-memory global reads in game code** — the game only touches them through `OSGetPhysicalMemSize`, `OSGetConsoleSimulatedMemSize`, `OSGetResetCode`, `OSGetProgressiveMode`, `OSGetConsoleType`, `OSGetSoundMode`, `OSGetTime`, `OSGetTick`. Those are all SDK accessors the shim implements; no direct absolute-address dereference. **`0x817FFFFF`/24 MB end-of-RAM comparisons do not appear in game code at all.**

---

## 3. Main loop and per-frame sequence

Three nested levels:

**Level 1 — `gm_801A4510()`** (`src/melee/gm/gm_1A3F.c:329`, aka `Scene_Main`):
zero the state machine, call every `GameMode::on_init`, then:
```c
if (VIGetDTVStatus() != 0 && (db_gameLaunchButtonState & HSD_PAD_B || OSGetProgressiveMode() == 1))
    routing.curr_mode = GM_PROGRESSIVE_SCAN;      // gm_1A3F.c:345
else
    routing.curr_mode = GM_BOOT;                  // gm_1A3F.c:348
while (true) { next = runGameMode(curr_mode); prev_mode = curr_mode; curr_mode = next; }
```
→ **`VIGetDTVStatus()` must return 0** in the shim, or you land in the progressive-scan prompt instead of boot.

**Level 2 — `runGameMode`** (`gm_1A3F.c:287`) walks the mode's `GameModeState[]` table calling `gm_801A4014` until `pending_mode_change`.

**Level 2.5 — `gm_801A4014`** (`gm_1A3F.c:126`): `findState` → `preloadState(state)` (`gm_1A3F.c:50`: `lbDvd_80018CF4(state->preload)`, `HSD_SisLib_803A6048(0xC000/0x2400/0x4800)`, `lbDvd_80018254()`, per-subsystem resets) → `state->on_enter` → `gm_801A4BD4()` (GObj lib re-init, `gmscene.c:221`) → `scene->on_enter` → **`gm_801A4D34(scene->on_frame, info)`** → exits.

**Level 3 — the frame loop, `gm_801A4D34`** (`src/melee/gm/gmscene.c:271`):
```c
lb_80019880(OSSecondsToTicks(1.0f/60));      // (from gm_801A4BD4, gmscene.c:228) target period
HSD_PadFlushQueue(HSD_PAD_FLUSH_QUEUE_LEAVE1);
while (unk_C == 0) {
    hsd_80392E80();
    while ((pad_queue_count = lb_80019894()) == 0)   // <-- BLOCKS until pad alarm fires
        lb_800195D0();
    lb_800195D0();
    if (HSD_PadGetResetSwitch()) { resetting = true; break; }
    for (i = 0; i < pad_queue_count; i++) {           // logic ticks, one per queued pad sample
        HSD_PerfSetStartTime();
        lb_800198E0();                                // HSD_PadRenewMasterStatus
        if (DbLevel >= DbLKind_DebugRom) gm_801A4970(&db_input);
        ... unk_38_0 = (framestep || !paused)
        if (unk_38_0) {
            lb_80019900();                            // advance the two logic clocks; HSD_PadRenewGame/CopyStatus
            if (lb_80019A30(0)) gm_EvaluateAllControllerInputs();
            if (lb_80019A30(0) && on_frame) on_frame();   // <-- THE GAME LOGIC
        }
        ...
        lbAudioAx_80027DF8();                         // per-frame audio tick
        if (pre_gobj_proc) pre_gobj_proc();
        HSD_GObj_RunProcs();
        HSD_PerfSetCPUTime();
        if (DbLevel >= DbLKind_DebugRom) OSCheckActiveThreads();
        if (unk_C != 0) break;
    }
    if (unk_C == 2) break;
    lb_800195D0();
    GXInvalidateVtxCache(); GXInvalidateTexAll();
    HSD_StartRender(HSD_RP_SCREEN);
    HSD_GObj_80390FC0();                              // render all GObj gxlinks
    HSD_Init_803755A8();
    HSD_PerfSetDrawTime();
    HSD_VICopyXFBAsync(HSD_RP_SCREEN);                // <-- present
    db_TakeScreenshotIfPending();
    HSD_PerfSetTotalTime(); HSD_PerfInitStat();
}
HSD_VIWaitXFBFlush();                                 // drain before leaving scene
```

**`HSD_VICopyXFBAsync`** (`baselib/video.c:292`):
`HSD_VIWaitXFBDrawEnable()` → **spins `while ((idx = HSD_VIGetXFBDrawEnable()) == -1) VIWaitForRetrace();`** (video.c:186) → `HSD_VICopyEFB2XFBPtr` (→ `GXCopyDisp(buffer, GX_TRUE)`, video.c:235/243/254/257) → `HSD_VISetXFBWaitDone(idx)` → `HSD_VIGXSetDrawDone(idx)` which does `while (HSD_VIGetDrawDoneWaitingFlag()) GXWaitDrawDone();` then `GXSetDrawDone()`.

**XFB state machine** — three interrupt-driven transitions, all required:
- `HSD_VIGXDrawDoneCB` (video.c:142, from `GXSetDrawDoneCallback`) clears `waiting` and calls the user cb = `HSD_VIDrawDoneXFB`, which flips WAITDONE → DRAWDONE/NEXT (video.c:307).
- `HSD_VIPreRetraceCB` (video.c:63) finds a NEXT buffer, `VISetNextFrameBuffer`, optional `VIConfigure`/`VISetBlack`, `VIFlush()`.
- `HSD_VIPostRetraceCB` (video.c:117) rotates NEXT→DISPLAY, DISPLAY→FREE, DRAWDONE→NEXT.

**If GX drawdone or VI retrace callbacks never fire, `HSD_VIWaitXFBDrawEnable` / `HSD_VIGXSetDrawDone` / `HSD_VIWaitXFBFlush` (video.c:340) all spin forever.** These are the #1 hang points for the port.

**Timing/frame pacing** — `src/melee/lb/lb_0195.c`:
- `lb_80019AAC` (lb_0195.c:171) initialises two logic clocks at 1/60 s and calls `lb_80019628`.
- `lb_80019628` (lb_0195.c:61) picks `period = min(clock periods, 1/60 s)`, sets `PADSetSamplingRate(clamp(OSTicksToMilliseconds(period), ≤11))`, and installs **`OSSetPeriodicAlarm(&alarm, period, period, fn_800195FC)`** (lb_0195.c:109).
- `fn_800195FC` (lb_0195.c:56) runs **from interrupt context**: `HSD_PadRenewRawStatus(0)` (this is what makes `HSD_PadGetRawQueueCount()` non-zero), `lb_8001C600()` (CARDProbe polling), `lbSnap_8001D2BC()`.
- `lb_80019894` (lb_0195.c:118) reads `HSD_PadGetRawQueueCount()` under `OSDisableInterrupts`. **The outer `while (lb_80019894()==0) lb_800195D0();` is the frame gate: if the periodic alarm never fires, the game never runs a frame.**
- Frame skipping is implicit: `pad_queue_count` > 1 → multiple logic ticks per render; `lb_80019A30(0)`/`(1)` gate logic vs. rendering off the two clocks.
- `lb_800195D0` (lb_0195.c:47) = `lb_800192A8(lb_8001955C)` (disc-error screen, `lb/lb_0192.c:106`; it keeps rendering XFBs in its own loop while the drive is bad) + `lb_8001CC84()` (memory-card task pump). **This is the universal "yield" used in every blocking wait in the codebase.** `lb_8001955C` (lb_0195.c:31) also handles the reset switch (`VISetPostRetraceCallback(0)`, `VIFlush`, 2× `VIWaitForRetrace`, `OSResetSystem`).
- `lb_80019230` (lb_0192.c:87) maps `DVDGetDriveStatus()`: 5→0 (cover open), 4→1 (no disc), 6→2 (wrong disc), 11→3 (read error), -1→4 (fatal), 1→5 (reading), default → **-1 = OK**. **The shim's `DVDGetDriveStatus()` must return something that maps to -1 (e.g. 0 or 2) or the game shows a disc-error screen forever.**

---

## 4. File I/O

**Stack:** game → `lbFile`/`lbArchive`/`lbDvd` → `HSD_DevComRequest` → `DVDReadAsyncPrio` (+ `ARQPostRequest` when the destination is ARAM).

- **`HSD_DevComRequest(file, src, dest, size, type, pri, cb, args)`** — `baselib/devcom.c:377`. Four priority queues (`pri & 3`, queue 3 = ARAM-only). Asserts `src%32 == 0`, `dest%32 == 0`, `size%32 == 0`, `size != 0` (devcom.c:394-397). Returns a `dcReq` handle. `HSD_DevComCancelEx` at devcom.c:443.
- `HSD_DevComIsBusy(idx)` (devcom.c:7) — polled by `gm_801A4014` on reset: `while (HSD_DevComIsBusy(1));` (gm_1A3F.c:181).
- **`lbFile_800161C4`** (`lb/lbfile.c:37`) — synchronous DevCom: sets `cancel=false`, issues the request with `lbFile_8001615C` as callback, then `waitForDisc()` = `do {} while (!discIsDone());` where `discIsDone()` calls `lb_800195D0()` (lbfile.c:28-42). **Blocking, yields to interrupts.**
- `lbFileGetFullName` (lbfile.c:53) appends `.usd` (US) or `.dat` (JP) when the basename ends in `.` or has no extension.
- `lbFile_8001634C` (lbfile.c:88) — `DVDFastOpen`/`DVDClose` under `OSDisableInterrupts` to get file length.
- `lbFile_800164A4` (lbfile.c:118) — `type = (dst >= 0x80000000) ? 0x21 : 0x23`, size rounded up to 32.
- `lbFile_80016580` / `_8001668C` / `_80016760` / `_800168A0` (lbfile.c:128-176) — name→entrynum→load, optionally allocating from an lbHeap and optionally hitting the preload cache first.
- **`lbArchive`** (`lb/lbarchive.c`) — `lbArchive_80016DBC(name, &out, symbol, flags)` and `lbArchive_LoadSymbols(...)` wrap `HSD_ArchiveParse` over a loaded DAT.
- **`lbDvd` preload cache** (`lb/lbdvd.c`) — `preloadCache.entries[]`, `lbDvd_80017740` (lbdvd.c:111) registers an entry; `lbDvd_80018254` runs the loads; `lbDvd_8001819C` (lbdvd.c:459) looks a basename up in the cache and (non-Master) **asserts if it was not preloaded**. `lbDvd_80018CF4` (lbdvd.c:765) sets heap persistence from the scene's `lbDvdPreload_0..3` level and then `lbHeap_80015900()` rebuilds the heaps. Waits: `while (lbDvd_80017598(2) != 0) lb_800195D0();` (lbdvd.c:811,816), `lbDvd_80018C2C` → `while (lbDvd_80018A2C(arg0)==1) lb_800195D0();` (lbdvd.c:706).

**Files touched from boot through the title screen** (in order):
1. `/develop.ini` — `DVDConvertPathToEntrynum` only (gmmain.c:63). Absent on retail → DbLevel = Master.
2. `/usa.ini` — same, language select (gmmain_lib.c:1330).
3. `audio/smash2.sem` — `AXDriver_8038DA70(cur_ssm_file, lb_800195D0)` (lbaudio_ax.c:2183), **blocking `DVDReadAsyncPrio` + `while (flag==0) callback();`** (axdriver.c:829-834).
4. `audio/us/smash2.ssm` … i.e. `ssm_files[0]` = **`main.ssm`**, then `ssm_files[0x33]` = `1pend.ssm`… — precisely: index 0 (`main.ssm`, bank 0), 0x33, 1 (`pokemon.ssm`), 0x36, 2 (`nr_title.ssm`) — all via `HSD_SynthSFXLoad` + `HSD_SynthSFXWaitForLoadCompletion(lb_800195D0)` (lbaudio_ax.c:2175-2224). Name table at `lb/lbaudio_ax.static.h:234-247`.
5. `.hps` BGM streams (`lbaudio_ax.static.h:251+`), streamed via `HSD_SynthPStream` / DevCom type `0x22`.
6. Preload set for `lbDvdPreload_*`: `LbRb.dat` (lbdvd.c:427), `EfMnData.dat`, `EfCoData.dat`, `ItCo.` , `IfAll` (lbdvd.c:449-452).
7. `MvOpen.mth` — `lbMthp_8001F410("MvOpen.mth", gm_803DBFB4, 0, 0, 0)` (gmopening.c:187).
8. `GmTtAll.dat` / `GmTtAll.usd` — title screen, `lbArchive_LoadSymbols` (gmtitle.c:238-241).
9. `LbMcGame.` + `NtMemAc` — memory-card icon/scene archives (lbcardgame.c:277-278), only when the card prompt is entered.
10. `DbCo.dat` — debug symbols, only if `DbLevel >= DbLKind_DebugRom` (dbinit.c:78).

---

## 5. Audio — what blocks, and what stubs must return

Stack: game (`lbaudio_ax`) → `AXDriver`/`HSD_Synth` (`baselib/axdriver.c`, `baselib/synth.c`) → `AX` + `AI` + `ARAM` (samples) + `DSP`. `.ssm` = sample banks resident in ARAM, `.sem` = the sound-effect index, `.hps` = streamed BGM (DVD → `HSD_SynthPStream`).

**Blocking waits in the boot path (all yield via `lb_800195D0`):**
1. **`AXDriver_8038DA70`** (axdriver.c:803, loads `smash2.sem`): `DVDReadAsyncPrio(...)` then `while (AXDriver_804D77EC == 0) callback();`. The flag is set by the DVD read callback `fn_8038DA5C` — **DVD-driven, not DSP-driven.** Safe as long as DVD callbacks fire.
2. **`HSD_SynthSFXWaitForLoadCompletion(cb)`** (synth.c:226): `while (HSD_Synth_804D772C != 0) callback();`. `HSD_Synth_804D772C` is decremented in `HSD_SynthSFXSampleLoadCallback` (synth.c:142), which runs off `HSD_DevComRequest` DVD→ARAM (type 0x23) completion — i.e. **DVD callback → ARQ callback chain**. A no-op `ARQPostRequest` that never calls its callback hangs here permanently. **This is the single most important hang risk in the audio path.**
3. **`HSD_SynthSFXLoad`** (synth.c:197): `while (HSD_Synth_804D772C >= 6) {}` — a *bare* spin with no yield. Only trips if 6 loads queue up.
4. **`lbAudioAx_80027648`** (lbaudio_ax.c:1846): `while (fn_80027488() == 1) HSD_SynthSFXWaitForLoadCompletion(lb_800195D0);` — called from `gm_Scene_Opening_OnEnter` (gmopening.c:183) and every scene that swaps SSM banks.
5. `lbArq_80014BD0` with `callback == NULL` (lbarq.c:143) — bare spin on `state != DONE`.

**Minimum viable stub contract to keep boot moving:**
| API | Must do |
|---|---|
| `ARInit`, `ARQInit`, `AIInit`, `AXInit`, `AISetDSPSampleRate`, `AXRegisterCallback`, `AISetStreamVolLeft/Right`, `AXFXSetHooks` | return, record nothing needed |
| `ARGetSize()` | return ≥ 0x01000000 (16 MB) — anything smaller shrinks heap 5 and may trip `lbHeap` asserts |
| `ARAlloc(len)` | return a real, distinct, 32-byte-aligned ARAM-space offset **< 0x80000000** from a simple bump allocator over a 16 MB host buffer; `ARFree` can be a stack pop |
| **`ARQPostRequest(req, owner, type, pri, src, dst, len, cb)`** | perform the copy (host ARAM buffer ↔ game RAM) and then **invoke `cb(req)`**, ideally deferred to the next frame/interrupt-equivalent rather than synchronously (the callbacks re-enter `HSD_DevComARAMWakeUp`, which is written to be re-entrant but assumes it is not on the caller's stack while `aramstate==1`). Never a silent no-op. |
| `DVDReadAsyncPrio` | must call its callback with `result != -1` (a `-1` sets `HSD_DevCom_804D7804=1` which suppresses all user callbacks, devcom.c:239) |
| `AXDriver_*` / `HSD_Synth*` voice ops | can return "voice failed" (0 / -1); `lbAudioAx_80027DF8` (lbaudio_ax.c:1996) handles `AXDriver_8038D9D8(id)==0` by retrying, which is harmless |
| `HSD_SynthSFXLoad` path | **cannot** be shortcut without also decrementing `HSD_Synth_804D772C` — if you stub the DevCom layer, stub `HSD_SynthSFXLoad`/`WaitForLoadCompletion` together |
| `AXFXReverbStdInit/HiInit`, `AXFXGetReverb…HeapSize` | return sizes < 53 KB / 71 KB respectively or `HSD_ASSERT` at lbaudio_ax.c:2131/2137 fires |

Note `lbAudioAx_80027DF8` is called *every logic tick* from `gm_801A4D34` (gmscene.c:335) and only manipulates plain state + voice handles — safe with dumb stubs.

---

## 6. Memory card at boot

Flow: `main` → `lb_8001D21C()` (`lb/lbcardgame.c:298`) sets `_p(x0) = CARDProbe(0)`. Then at the very start, `db_GetGameLaunchButtonState` **spins** `while (CARDProbeEx(0,&memSize,&sectorSize) == -1) VIWaitForRetrace();` (dbinit.c:58) — `-1` is `CARD_RESULT_BUSY`, so the stub must **not** return -1.

Per-frame the periodic alarm calls `lb_8001C600()` (lbcardgame.c:39): re-probes, and if the result changed sets `_p(x4)=1` (a "card state changed" flag). `lb_8001CAF4()` (lbcardgame.c:104) is the state machine: state 0 + change → state 1 (i.e. "card inserted/removed, show prompt").

`gmboot.c:78` installs `gm_SetGameModeOverride(lbCardGame_DecideGameMode)`. `lbCardGame_DecideGameMode` (lbcardgame.c:226) returns `GM_MEMCARD` whenever `_p(x8) != 0 && _p(x8) != 4`, else `GM_COUNT` (= no override). The override is consulted every iteration of `runGameMode` (gm_1A3F.c:308).

Error mapping `lb_80019BB8` (lbcardnew.c:16): `CARD_RESULT_NOCARD (-3)` / -1 / -2 → `0xF`; `-4` → 4; `0` → 0; `-5`/`-128` → 0xE; `-6`/`-13` → 9; default → 0xD.

Also: `lb_8001CDB4()` at the end of every scene (gm_1A3F.c:170) does `while (_p(xC) || _p(x10)) lb_8001CC84();` — a save in flight blocks the scene transition. And `lb_8001B760(11)` (gm_1A3F.c:171) → `lb_8001B6F8()` spins while the card task machine returns 11 (BUSY).

**Simplest stub that lets the game proceed (no card present):**
- `CARDInit()` → return.
- `CARDProbe(chan)` → **0** (constant, never changing) so `lb_8001C600` never sets the change flag and `_p(x8)` stays 0 → `lbCardGame_DecideGameMode` returns `GM_COUNT`, so **the memcard scene is never entered**.
- `CARDProbeEx(chan, &memSize, &sectorSize)` → return **`-3` (NOCARD)**, write 0s. Not -1 — that hangs `db_GetGameLaunchButtonState`.
- Everything else (`CARDMountAsync`, `CARDCheckAsync`, …) → return `-3` synchronously and **do not** increment the pending counter (`_p(x8AC)`), so `lb_8001A184` returns the error rather than `0xB`/BUSY. Never call the callback if you returned an error (`lb_8001A184` only bumps `x8AC` when the return code maps to 0 — lbcardnew.c:259-262).
- `CARDGetStatus`, `CARDFreeBlocks`, `CARDOpen` → non-zero error.

(Alternative: emulate a real card backed by a file; `lbcardnew.c` uses the standard `CARDOpen/Read/Write/Close`, `CARDFormatAsync`, `CARDDeleteAsync`, `CARDRenameAsync` set — but nothing on the critical boot path requires it.)

---

## 7. Movies (THP/MTH) at boot

`src/melee/lb/lbmthp.c` — a single static `THPDecComp MoviePlayer` decoding `.mth` (Melee's THP variant) via `dolphin/thp`.

- `lbMthp_8001F87C()` at boot (lbmthp.c:656) initialises it.
- `lbMthp_8001F410(filename, rate_table, buf, heap_size, loop)` (lbmthp.c:520) — **non-blocking**: opens the file, `fn_8001EBF0` computes the buffer size, `HSD_MemAlloc`s it, then `OSCreateAlarm` + `OSSetPeriodicAlarm(1/60 s, fn_8001F2A4)`. All decoding happens on that alarm; DVD refills go through `HSD_DevComRequest` with callback `fn_8001E910` (lbmthp.c:96, `HSD_ASSERT(328, !cancelflag)`).
- `lbMthp_8001F800()` (lbmthp.c:637) — called at the end of *every* `gm_801A4014` (gm_1A3F.c:172): if a movie is running, `while (fn_8001F294()) {}` — **bare spin** on `MoviePlayer.unk_110`, then `OSCancelAlarm`, `HSD_VIWaitXFBFlush()`, free. A stubbed THP decoder that leaves `unk_110` non-zero hangs here.
- `lbMthp_8001F604()` returns the "movie finished" flag; `gm_Scene_Opening_OnFrame` (gmopening.c:200) polls it.

**Boot movie path:** `GM_BOOT` → `bootOnLoad` (gmboot.c:49) → if `!skip_intro`, `gm_801BF708(0)` and `mode_id = GM_OPENING_MV`; the `GM_OPENING_MV` mode state 0 is `GS_MOVIE_OPENING` (`gmopeningmode.c:57-68`), whose `on_enter` is `gm_Scene_Opening_OnEnter` (gmopening.c:141) which calls `lbMthp_8001F410("MvOpen.mth", …)`.

**How to skip:**
1. **Cleanest: set `gmMainLib_8046B0F0.skip_intro = true`.** `gmboot.c:55` then sets `mode_id = GM_TITLE` and the movie mode is never entered. It is normally set by `OSGetResetCode() == 0x80000000` (gmmain_lib.c:1364) — so **a shim `OSGetResetCode()` returning `0x80000000` skips the intro movie on every boot with zero source changes.** (Also set after a soft reset, gm_1A3F.c:186.)
2. In-scene: `gm_Scene_Opening_OnFrame` exits on START or A (gmopening.c:269-278) and on `gmMainLib_8046B0F0.xC` (set by the disc-error path).
3. Later attract-mode movies (`GS_MOVIE_HOWTO`, `GS_MOVIE_OMAKE15`, the `GS_CUTSCENE_*` and `GS_VS` demo states) all live in `gm_Mode_Opening_States[]` (gmopeningmode.c:56+) and are only reached from the title timeout.

---

## 8. OS assumptions

- **`OSDisableInterrupts`/`OSRestoreInterrupts`** — 33 sites in `src/melee` alone, plus heavy use in `devcom.c`, `video.c`, `synth.c`, `lbcardnew.c`. Always short critical sections around linked-list surgery and queue-count reads. A port can implement them as a recursive lock / atomic flag that suppresses the callback pump, but **`lbArq_80014BD0` deliberately re-enables interrupts before its spin** (lbarq.c:141) and `lbFile`'s `waitForDisc` relies on callbacks firing while spinning — so "interrupts" must be a real deferral mechanism, not a global freeze.
- **Alarms** — `OSInitAlarm` at boot (gmmain.c:140). Three periodic alarms in the codebase: pad/heartbeat (`lb_0195.c:109`, period = min(1/60 s, clocks)), MTH decoder (`lbmthp.c:544`, 1/60 s), and the one-shot chained ARAM memcpy (`lbmemory.c:207/230`, 3 ms). `OSCancelAlarm` used in `lb_80019A48` (lb_0195.c:159) and `lbMthp_8001F800`.
- **Callbacks from interrupt context** — `fn_800195FC` (pad renew + CARDProbe + snap), VI pre/post retrace, GX drawdone, AX 5 ms, ARQ completion, DVD completion, alarm handlers. Several of them re-enter the DevCom scheduler (`HSD_DevComDVDWakeUp`/`ARAMWakeUp`). The port needs an interrupt-equivalent dispatcher that can run these off the main thread's spin loops.
- **`OSThread`** — **the game does not create threads.** The only `OSCreateThread` in the tree is `baselib/debugconsole_main.c:2855` (debug console). `OSCheckActiveThreads()` is called per frame but only when `DbLevel >= DbLKind_DebugRom` (gmscene.c:344) — under retail `DbLevel == Master` it never runs. `gmscene.c` includes `dolphin/os/OSThread.h` but uses nothing from it in the hot path.
- **Locked cache** — **no `LCEnable`/`LCLoadData`/`LCQueueWait` anywhere in `src/`.** Nothing to emulate.
- **Cache maintenance** — `DCFlushRange` (lbrefract.c:101,592; lbsnap.c:384), `DCStoreRange` (devcom.c:148,157; lbmthp.c:344-346), `DCInvalidateRange` (lbarq.c:120; lbmthp.c:316-322; lb_01F8.c:94-99; devcom.c:163,169,176). **All are CPU↔DMA coherency for ARAM/DVD/GX; on a coherent x86 host they can be no-ops** — *except* that `DCStoreRange`/`DCInvalidateRange` mark the exact byte ranges that a DMA is about to touch, which is useful free metadata if you want to validate your ARQ/DevCom emulation. No `ICInvalidateRange` in game code.
- **`OSGetTime` / `OSGetTick`** — `OSGetTick` at gmmain.c:156 (RNG seed), lbmthp.c:106/125/404 (movie pacing, differences converted via `OSMillisecondsToTicks`). `OSGetTime` at lbcardgame.c:55, lbsnap.c:144/363, lbtime.c:56. Everything goes through `OSSecondsToTicks` / `OSTicksToSeconds` / `OSTicksToMilliseconds` / `OSMillisecondsToTicks`, so the shim only has to keep the bus-clock constant self-consistent. GC rate is 40.5 MHz (`OSBusClock/4`); keeping that exact value is simplest because `OSSecondsToTicks(1.0f/60)` is compared against real deltas in `lb_80019628`.
- **`OSGetResetCode()`** — gmmain_lib.c:1364, compared to `0x80000000`. See §7: returning `0x80000000` skips the intro movie.
- **`OSGetProgressiveMode()`** — gm_1A3F.c:345, `== 1` (with `VIGetDTVStatus() != 0`) routes to `GM_PROGRESSIVE_SCAN`. Return 0.
- **`OSGetConsoleType()`** — not referenced from `src/melee`; only the SDK/`OSGetConsoleSimulatedMemSize` path matters.
- **`OSGetSoundMode()`** — not referenced from game code in this checkout (audio mode comes from save data); safe to return `OS_SOUND_MODE_STEREO`.
- **`OSGetConsoleSimulatedMemSize()`** — gmmain.c:143; return 24 MB (0x01800000) to take the retail path, or 48 MB and honour `OSAllocFromArenaHi`.
- **`OSGetPhysicalMemSize()`** — `initialize.c:163` (memReport only) and debugconsole. Cosmetic.
- **`OSResetSystem`** — lb_0195.c:41 and gm_1A3F.c:178 (`if (DVDCheckDisk() == 0) OSResetSystem(1,0,0)`). Make `DVDCheckDisk()` return non-zero.
- **`PPCMtmsr`/`PPCMfmsr`/`OSSaveFPUContext`/`OSLoadFPUContext`** — only `db_ClearFPUExceptions` (dberror.c:16). No-op them.

---

## 9. Scene flow and bring-up shortcuts

### Enums
`GameModeKind` — `src/melee/gm/forward.h:16-62`. Key: `GM_TITLE=0x00`, `GM_MENU=0x01`, `GM_VS=0x02`, `GM_DEBUG=0x06`, `GM_DEBUG_SOUND_TEST=0x07`, `GM_DEBUG_VS=0x0E`, `GM_OPENING_MV=0x18`, `GM_PROGRESSIVE_SCAN=0x27`, `GM_BOOT=0x28`, `GM_MEMCARD=0x29`, `GM_COUNT=0x2D`.
`GameSceneKind` — `forward.h:65-116`. Key: `GS_TITLE=0x00`, `GS_MENU=0x01`, `GS_VS=0x02`, `GS_CSS=0x08`, `GS_SSS=0x09`, `GS_MOVIE_OPENING=0x1C`, `GS_MEMCARD=0x2A`, `GS_COUNT=0x2D`.

### Tables
- `GameMode[]` — `src/melee/gm/gmscdata.c` (`gm_GetAllGameModes`), entries around gmscdata.c:386-640.
- `GameScene[]` — `gmscdata.c:65+` (`gm_GetAllGameScenes`); `GS_TITLE`→`gm_Scene_Title_OnEnter/OnFrame`, `GS_MENU`→`mnMain_Scene_*`, `GS_CSS`→`mnCharSel_Scene_*`, `GS_SSS`→`mnStageSel_Scene_*`, `GS_VS`→`gm_Scene_Vs_*`, `GS_MOVIE_OPENING`→`gm_Scene_Opening_*` (gmscdata.c:255-261).

### Path
```
gm_801A4510            (gm_1A3F.c:329)   curr_mode = GM_BOOT (or GM_PROGRESSIVE_SCAN)
 └ GM_BOOT             (gmboot.c:33 gm_Mode_Boot_States, single state, scene GS_MEMCARD)
     bootOnLoad        (gmboot.c:49)  skip_intro ? GM_TITLE : (gm_801BF708(0), GM_OPENING_MV)
     bootOnLeave       (gmboot.c:63)  Pikmin-trophy check, gm_SetGameModeOverride(lbCardGame_DecideGameMode),
                                      gm_ChangeGameModeAfterCurrentScene(mode_id)
                                      // comment at gmboot.c:80: the Gekko "boot to CSS" code patches
                                      // this scene_id to a hardcoded 2 (GM_VS)
 └ GM_OPENING_MV       (gmopeningmode.c:56 gm_Mode_Opening_States)
     state 0 GS_MOVIE_OPENING  -> gm_Scene_Opening_OnEnter loads MvOpen.mth
             exit on START/A  -> GM_TITLE ; after ~0x157C frames START -> GM_MENU
     states 1..N: GS_VS demos, GS_TITLE, GS_MOVIE_HOWTO, GS_MOVIE_OMAKE15, cutscenes (attract loop)
 └ GM_TITLE            (gmtitlemode.c:20 gm_Mode_Title_States, preload lbDvdPreload_3)
     gmTitleMode_OnEnter -> lbDvd_SetupVsPreloadCache()
     onExit (gmtitlemode.c:39): if DbLevel >= DbLKind_DebugRom:
         A     -> GM_DEBUG_VS          <<< straight into a match
         START -> GM_MENU
         X     -> GM_DEBUG_SOUND_TEST
         Y     -> GM_DEBUG             <<< debug menu
         else  -> gm_801BF708(1); GM_OPENING_MV (attract)
     retail (Master): START -> GM_MENU, timeout -> GM_OPENING_MV
 └ GM_MENU             (gmmenumode.c:45 gm_Mode_Menu_States, single GS_MENU, preload lbDvdPreload_2)
 └ GM_VS               (gmvsmode.c:28 gm_Mode_Vs_States, all lbDvdPreload_3 except Approach/Prize = _2)
     gmVsMode_State_Css          -> GS_CSS   (onEnterCss/onExitCss)
     gmVsMode_State_Sss          -> GS_SSS
     gmVsMode_State_Vs           -> GS_VS    <<< the match
     gmVsMode_State_SuddenDeath  -> GS_SUDDEN_DEATH
     gmVsMode_State_Results      -> GS_RESULTS
     gmVsMode_State_Approach/ApproachVs/Prize
```

### Debug shortcuts useful for bring-up
1. **`DbLevel`** (`db/db.h:11-17`: Master=0, NoDebugRom=1, DebugDevelop=2, DebugRom=3, Develop=4). Set by `gmMain_8015FDA4` (gmmain.c:61): if `/develop.ini` exists → `db_804D6B20 = true` and X/Y at launch cycle the level; if absent → **`DbLevel = DbLKind_Master`**. For bring-up, either ship a `develop.ini` in the virtual FS or just force `DbLevel = DbLKind_DebugRom` — that unlocks the title-screen A/X/Y shortcuts, the pause/framestep handlers (`gm_801A4970`, gmscene.c:106), `db_CheckScreenshot`, and `OSCheckActiveThreads`.
2. **`GM_DEBUG_VS` (0x0E)** — `gm_Mode_DebugVs_States` (`gmvsmode.c:133`): state 1 = `GS_VS` with `gmVsMelee_StartData` directly, state 3 = `GS_RESULTS`. **Skips CSS and SSS entirely — this is the fastest path to a running match.** Reach it with title-screen A at `DbLevel >= DebugRom`, or by setting `state_machine.routing.curr_mode = GM_DEBUG_VS` in `gm_801A4510` (gm_1A3F.c:345-348).
3. **`GM_DEBUG` (0x06)** — `gm_Mode_Debug_States` → `GS_DEBUG_MENU` → `gm_Scene_DebugMenu_OnEnter` (`gmdebugmode.c`). The dev menu.
4. **`skip_intro`** — see §7; set it (or return `0x80000000` from `OSGetResetCode`) to boot straight to `GM_TITLE`.
5. **Boot directly into a mode** — the one-line change is `gm_1A3F.c:348`: replace `GM_BOOT` with e.g. `GM_DEBUG_VS` or `GM_TITLE`. Note `GM_BOOT` is also what installs the memory-card override (`gmboot.c:78`), so skipping it also skips the card prompt — convenient.
6. **`gm_Mode_HanyuCss_States` / `gm_Mode_HanyuSss_States`** (`GM_HANYU_CSS`=8, `GM_HANYU_SSS`=9, gmhanyucss.c/gmhanyusss.c) — standalone CSS/SSS modes, useful for testing menus without a match.
7. Pause/framestep in any scene at `DbLevel >= DebugRom`: `fn_801A46F4` = D-pad-Up + X toggles pause; `fn_801A47E4` = Z advances one frame (gmscene.c:64/76, wired by `gm_801A4B1C`).
