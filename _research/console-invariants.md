# Console invariants

Audit of every hardware assumption the game makes that the PC port must reproduce, so the next
class of boot bug is pre-empted rather than discovered one crash at a time. This is a living
document: sections B and C are written by todos 14 and 15 and appended after this one.

Conventions:

- `status` is one of `OK` (writer/reader cited), `VIOLATED` (no writer, or a writer that writes
  the wrong value), `UNKNOWN` (no writer and no follow-up yet — every UNKNOWN carries a note), or
  `regression-check` (an invariant already fixed before this audit; the row only points at the fix,
  nothing is re-fixed here).
- `evidence` is `file:line` of the current source — never a DEVLOG claim. The audit reads the
  files, not the docs.
- The PC build's unit set is `_build/masstest/files.txt` (989 TUs). Its only `extern/dolphin/src`
  entry is `mtx44.c`; every other SDK `.c` (OSMemory.c, OSThread.c, OSReset.c, OSExi.c, vi.c, OS.c,
  GXInit.c, CARDWrite.c, ar.c, …) is **replaced by a shim in `melee/pc/platform/`**, so a fixed
  address read inside those SDK files is not reachable in the PC build unless a shim or game file
  reproduces it.

---

## A. Fixed-address & low-memory reads

On a GameCube the IPL writes a block of OS globals into the bottom of MEM1 (physical 0x0 →
cached 0x80000000) before the game runs. `dolphin/os.h` reads them through absolute-address
declarations and raw-pointer macros. On the PC port MEM1 is mapped at `0x80000000`
(`gw_runtime.c:50-52`), so those addresses exist — but they are zero unless something fills them in.

### A.1 Low-memory OS globals (fixed-address reads reachable from `dolphin/os.h`)

Every global in `melee/extern/dolphin/include/dolphin/os.h:63-76` that names a fixed address,
plus the two pointer macros the clang (non-MWERKS) build actually uses (`os.h:74-75`).

| name | address | reads it (`file:line`) | writes it on PC (`file:line`) | status | evidence |
|---|---|---|---|---|---|
| `__OSBusClock` | 0x800000F8 | tick conversions via `OS_TIMER_CLOCK` (`os.h:79,81-88`); e.g. `lb_0195.c:77,85,96`, `hsd_3933.c:82`, `gm_1884.c:514` | `gw_init_lomem` — 162 MHz, big-endian | OK | `gw_runtime.c:92` |
| `__OSCoreClock` | 0x800000FC | `OS_CORE_CLOCK` (`os.h:78`); no game-code reader on PC (only SDK `perfdraw.c` / Aurora, not linked) | `gw_init_lomem` — 486 MHz | OK | `gw_runtime.c:93` |
| `__OSTVMode` | 0x800000CC | `VIGetTvFormat()` → shim returns constant `VI_NTSC` (console reader `vi.c:698` not linked) | `gw_init_lomem` — 0 = NTSC | OK | `gw_runtime.c:96`; reader `shim_vi.c:288` |
| `__OSPhysicalMemSize` | 0x80000028 | `OSGetPhysicalMemSize()` → shim returns `gw_mem1_size` (console reader `OSMemory.c:13` not linked) | `gw_init_lomem` — 24 MB | OK | `gw_runtime.c:94`; reader `shim_os.c:128` |
| `__OSSimulatedMemSize` | 0x800000F0 | `OSGetConsoleSimulatedMemSize()` → shim returns 24 MB (console reader `OSMemory.c:23` not linked) | `gw_init_lomem` — 24 MB | OK | `gw_runtime.c:95`; reader `shim_os.c:131` |
| `__gUnkThread1` | 0x800000D8 | `OSThread.c:136` (SDK, **not linked**) | none | UNKNOWN | — |
| `__OSActiveThreadQueue` | 0x800000DC | `OSThread.c`, `OSReset.c:134` (SDK, **not linked**) | none | UNKNOWN | — |
| `__gCurrentThread` | 0x800000E4 | `OSThread.c` (SDK, **not linked**) | none | UNKNOWN | — |
| `__EXIProbeStartTime[2]` | 0x800030C0 | `OSExi.c:275-689` (SDK, **not linked**) | none | UNKNOWN | — |

Notes on the UNKNOWN rows: all four are scheduler/EXI state owned by SDK files that are not in
`files.txt`. The game is single-threaded on retail (`_research/melee-boot.md` §8: the only
`OSCreateThread` is DbLevel-gated debug-console code) and EXI is not shimmed, so no reader is
reachable in the PC build. They need writers **only if** a future milestone adds threads or EXI;
they are not boot blockers and are left unfixed here by scope.

Note on `__OSTVMode`/`__OSPhysicalMemSize`/`__OSSimulatedMemSize`: the console *reader* is a
dereference inside the SDK (`vi.c:698`, `OSMemory.c:13/23`), which is not linked. On PC the game
reaches these values through the shims (`shim_vi.c:288`, `shim_os.c:128,131`), which return the
value directly rather than reading the fixed address. The `gw_init_lomem` writes are therefore a
belt-and-suspenders mirror of the shims, not the actual read path — the row stays `OK` because a
writer *is* cited, and the value the shims return matches.

### A.2 `0x8000` / `0xC000` literals in `melee/src` (classification)

A grep for `0x8000…` / `0xC000…` in `melee/src` returns 116 hits across 65 files. Almost all are
bit masks, flags, or stage colour constants — **not** memory dereferences. The genuinely
address-related ones:

| location | literal | what it is | status | evidence |
|---|---|---|---|---|
| `lbmemory.c:68,281` | `< 0x80000000` | ARAM-vs-MRAM test (the game's own rule) | regression-check | `shim_ar.c:94-106` (`gw_ar_addr`) + image base `build_melee_pc.bat:17` |
| `lbfile.c:126` | `>= 0x80000000` | same test, picks DevCom type 0x21 vs 0x23 | regression-check | `shim_ar.c:94-106` |
| `gmmain_lib.c:1364` | `OSGetResetCode() == 0x80000000` | skip-intro magic | OK | shim returns it: `shim_os.c:324` |
| `leak.c:68` | `OSGetConsoleSimulatedMemSize() + 0x80000000` | computed MEM1 start, via shim | OK | `shim_os.c:131` |
| `debugconsole_main.c:837,840,1665,1693,1754,1764,1774,1784,1913` | `0x80000000` stack-walk math | DbLevel-gated; retail runs `DbLevel == Master` | OK (gated) | `_research/melee-boot.md` §2 |
| `MetroTRK/targimpl.c:29,79`, `dolphin_trk.c:15` | `0x80000000` BOOTINFO | MetroTRK, **not in `files.txt`** | UNKNOWN | — (not linked) |
| `lbaudio_ax.c:1754`, `vi0501.c:130`, `vi0502.c:115` | `0x800003FFFFFFC0ULL` / `0x80000004000` | DSP/sample-rate constants, not addresses | OK | — |

Everything else (MSL `trigf.c`/`math.c`/`limits.h` sign bit `0x80000000`; `cobj.c`/`robj.c`/`jobj.c`/
`mtx.h` flag bits; `gr*/` stage `0xC0000000`/`0x80000000` colour masks; `axdriver.h` SMSTATE_MASK;
`controller.c` rumble masks `0x80000` etc.) is a scalar bit pattern and carries no address meaning.

**Conclusion of A.2:** there are no raw fixed-address *dereferences* of MEM1 below `0x80000000` in
`melee/src` other than the OS globals enumerated in A.1. The ARAM-vs-MRAM comparisons are the
already-fixed pointer-disambiguation invariant (see A.3).

### A.3 Regression-check rows (already-fixed invariants — do NOT re-fix)

These invariants were fixed before this audit and are only verified here. Each row points at the
fix site.

| invariant | fix site (`file:line`) | status | notes |
|---|---|---|---|
| ARAM base `0x4000` (reserve low 16 KB) | `shim_ar.c:30,37-42` (`GW_AR_BASE`, `ARInit` returns it) | regression-check | `ar.c:117` on console; `lbmemory.c:342` probes it |
| Arena start offset `0x3100` (above OS globals/vectors/bootinfo) | `shim_os.c:47,52-57` (`GW_ARENA_LO_OFFSET`, `gw_arena_ensure`) | regression-check | starting at 0 overwrote `gw_init_lomem`'s globals (DEVLOG §6.1) |
| Image base `0x10000000` (pointers always ≥ 16 MB → never misread as ARAM offsets) | `build_melee_pc.bat:17` (`/BASE:0x10000000 /DYNAMICBASE:NO`); `gw_runtime.c:227` | regression-check | pairs with `gw_ar_addr` bound in `shim_ar.c:94-106` |
| 32-byte global widening (DMA alignment, `devcom.c:420-423`) | `gwtool.cpp:580-588` | regression-check | widens every global definition to `Align(32)` |
| Low-memory OS globals (bus/core clock, mem sizes, TV mode) | `gw_runtime.c:86-99` (`gw_init_lomem`) | regression-check | detail rows in A.1; all five written big-endian |

---

## B. Hardware guarantees

The GameCube makes a set of hardware promises that game code relies on *implicitly* — no fixed
address, just "the hardware guarantees this". Every one of them has bitten or could bite the port,
because the PC runtime supplies none of them for free. Each row cites where the game assumes the
guarantee, where the port reproduces it, and the current-source evidence (never a DEVLOG claim).

| invariant | where assumed/used (`file:line`) | how the port satisfies it (`file:line`) | status | evidence |
|---|---|---|---|---|
| 32-byte DMA alignment of globals | `devcom.c:422-424` asserts `src % 32 == 0`, `dest % 32 == 0`, `size % 32 == 0`; `devcom.c:148-151` DCStoreRange + `ARQPostRequest` on `HSD_DevCom_804C6330_bufs`; `synth.c:191` passes `hsd_SynthSFXLoadBuf` as a DVD/DevCom destination | gwtool widens every global *definition* to `Align(32)` (`gwtool.cpp:580-588`, the `fixAttributes` pass) | OK | `gwtool.cpp:587-588`; map symbol addresses both 32-aligned: `_HSD_DevCom_804C6330_bufs` = `0x10716de0` (%32==0), `_hsd_SynthSFXLoadBuf` = `0x10721140` (%32==0) |
| ARAM rules: 16 MB window, offsets `< 0x80000000`, `gw_ar_addr` bound, image base above ARAM | the game's own ARAM-vs-MRAM test `lbmemory.c:68` (`arenaLo < 0x80000000`), `lbfile.c:126`; ARQ source/dest are ARAM offsets or MEM1/native pointers | 16 MB buffer `gw_runtime.c:48,63-67`; `gw_ar_addr` bounds by `gw_aram_size` (`shim_ar.c:94-106`); image pinned at `/BASE:0x10000000 /DYNAMICBASE:NO` (`build_melee_pc.bat:17`, `gw_runtime.c:227`) so no real pointer is ever below the ARAM window | OK | `gw_runtime.c:48`; `shim_ar.c:94-106`; `build_melee_pc.bat:17` |
| Timebase coherence (40.5 MHz; `OS_TIMER_CLOCK` = bus/4; seconds↔ms round-trip) | `os.h:79` `OS_TIMER_CLOCK (OS_BUS_CLOCK/4)`; real readers `lb_0195.c:77,85-86` (`OSSecondsToTicks`) and `:96` (`OSTicksToMilliseconds`), plus `lbtime.c:56`, `perf.c`, `hsd_392C.c:205` | virtual clock `GW_TIMER_CLOCK = 40500000` (`shim_vi.c:42`); `__OSBusClock` written 162 MHz (`gw_runtime.c:92`), so `OS_TIMER_CLOCK` = 40.5 MHz matches the actual `gw_time_ticks()` rate (`shim_os.c:135` → `gw_OSGetTime`) | OK | `shim_vi.c:42`; `gw_runtime.c:92`; `os.h:79`; round-trip `OSSecondsToTicks(1)`=40500000 → `OSTicksToMilliseconds`=1000 ms exact |
| Arena/heap layout: start `0x3100`, XFB/FIFO/audio-heap sizes, fb math | `HSD_OSInit` carves the arena (`initialize.c:161-187`): XFB `fb_size = ((fbWidth+0xF)&0xFFF0)*xfbHeight*2` (`initialize.c:97`), audio heap `HSD_DEFAULT_AUDIO_SIZE = 512 KB` (`initialize.h:12`, `initialize.c:177-179`), main heap = remainder (`initialize.c:182`); FIFO 256 KB (`initialize.h:10`, `gmmain.c:150`) | arena lo = `gw_mem1 + 0x3100` (`shim_os.c:47,52-57`), above the OS globals/vectors the arena must not cover; XFB 2 buffers of 640×480×2 = 0x96000 each (`gmmain.c:159`) | OK | `shim_os.c:47`; `initialize.c:97,177-179,182`; `initialize.h:10-12` |
| 24 MB simulated memsize (retail) | `gmmain.c:143` branches on `OSGetConsoleSimulatedMemSize()/1 MB == 48` (devkit reserve); `leak.c:68` computes MEM1 start from it | `gw_OSGetConsoleSimulatedMemSize` returns `24*1024*1024` (`shim_os.c:131`), so the devkit 48 MB path is never taken; also written to `__OSSimulatedMemSize` lomem slot (`gw_runtime.c:95`) | OK | `shim_os.c:131`; `gmmain.c:143` |

### B.1 Finding — "Arena Size 23 MB" vs DEVLOG §5's "24 MB" (correct; do NOT fix)

The current build's banner prints `# Arena Size 23 MB` (`melee-pc.log:61`), while DEVLOG §5 records
`24 MB`. The 23 is **correct**; §5 was written before the arena-offset fix. `arena_size` is
`OSGetArenaHi() - OSGetArenaLo()` (`gmmain.c:146`): `OSGetArenaHi()` = `gw_mem1 + 24 MB`, and
`OSGetArenaLo()` = `gw_mem1 + 0x3100` (`shim_os.c:47,52-57`), so the arena is `24 MB − 0x3100` =
25,153,280 bytes, which integer-divides to 23 MB. The whole delta is exactly the 0x3100 (12,544 B)
low region the arena deliberately no longer covers (the §6.1 fix: OS globals + exception vectors +
boot info). Nothing to fix — this is the invariant working as intended, not a regression.

### B.2 Open question — the banner's "GC Calendar Year 0"

The banner also prints (`melee-pc.log:67-69`):

```
# GC Calendar Year 0 Month 1 Day 0
#             Hour 0 Min 0 Sec 59
```

The call chain is `gmmain.c:208-213` → `gm_801692E8` (`gm_1601.c:4197`) →
`lbTime_8000B028` (`lbtime.c:63-65`) → `OSTicksToCalendarTime`, which the shim forwards unmodified
to Aurora (`shim_os.c:139-141`). `lbTime_GetTimeInSeconds` feeds it `OSTicksToSeconds(OSGetTime())`
(`lbtime.c:54-56`), i.e. seconds since boot (≈0 at the banner).

Both the console and Aurora should yield **year 2000** here, not 0: the console `OSTicksToCalendarTime`
adds `BIAS = 0xB2575` (730,997 days — the GameCube epoch offset; `OSTime.h:32`, `OSTime.c:180`), and
Aurora converts against `kGcnEpochUnix = 946684800s` = 2000-01-01 (`OSTime.cpp:18,115,128`). A year-0
answer is impossible for either, so the printed `Year 0` (and `Sec 59`, which `gm_801692E8` only
produces by clamping a `tm.sec > 59`) indicates the `OSCalendarTime` out-param is crossing the
endianness boundary garbled.

Most likely cause (hypothesis, not yet proven): Aurora writes the ten `int` fields of `OSCalendarTime`
in native little-endian byte order (`OSTime.cpp:123-136`), while game code reads them through gwtool's
big-endian byte-swap — and `gw_OSTicksToCalendarTime` (`shim_os.c:139-141`) passes the game's `td`
through with no swap. The two `OSCalendarTime` definitions are layout-identical (`os.h:105-116` in both
trees), so a byte-order mismatch on the out-param is the remaining explanation. This is **cosmetic**
(the banner date plus snapshot/save timestamps in `lbsnap.c:344-365` / `lbcardgame.c:51-57`), not on
the boot critical path, so it is recorded here as an open question rather than fixed in this audit.
Note the banner's own `DATE Feb 13 2002 TIME 22:06:27` line is the compile-time `__DATE__`/`__TIME__`
(`db_build_timestamp`, `gmmain.c:206`) and is unrelated to the calendar.

## C. Async / callback contracts

Sections A and B cover values the game reads at fixed addresses and guarantees the hardware makes
about memory and time. This section covers the *ordering* contracts: on the console, every async
completion arrives later, from an interrupt (VI retrace, GX draw-done, DVD/ARQ DMA), and the game's
state machines are written around that "call me back later, never re-enter me" shape. The port has
no interrupts, so every one of these is reproduced by the frame driver (`gw_frame_tick`) and the
`gw_defer`/`gw_os_run_alarms` queues it drains. A row is OK only when both the assumption site (game
`file:line`) and the satisfying code (shim `file:line`) are cited from current source.

| contract | where assumed/used (`file:line`) | how the port satisfies it (`file:line`) | status | evidence |
|---|---|---|---|---|
| VI pre/post-retrace ordering + draw-done callback clears HSD's waiting flag | `HSD_VIWaitXFBDrawEnable` spins `HSD_VIGetXFBDrawEnable()` until an XFB is FREE/DRAWING, pumping `VIWaitForRetrace` (`video.c:186-200`); `HSD_VIGXSetDrawDone` spins `GXWaitDrawDone` while `drawdone.waiting`, then sets `waiting=1` + `GXSetDrawDone()` (`video.c:267-275`); the waiting flag is cleared by `HSD_VIGXDrawDoneCB` (`video.c:142-149`), registered via `GXSetDrawDoneCallback(HSD_VIGXDrawDoneCB)` (`video.c:429`); XFB rotation happens in `HSD_VIPreRetraceCB`/`HSD_VIPostRetraceCB` (`video.c:63-115,117-140`) | `gw_VIWaitForRetrace` → `gw_frame_tick` (`shim_vi.c:263`), which presents, drains alarms+deferred, then calls `gw_pre_retrace_cb` **before** `gw_post_retrace_cb` (`shim_vi.c:194-199`) — the console's pre→swap→post order; callbacks stored by `gw_VISetPre/PostRetraceCallback` (`shim_vi.c:269-279`); `gw_gx_set_draw_done`/`gw_gx_wait_draw_done` flush Aurora then fire `gw_draw_done_cb` synchronously (`shim_vi.c:229-241`), so `HSD_VIGXDrawDoneCB` clears `waiting` and `HSD_VIGXSetDrawDone`'s spin exits instead of deadlocking; routed by `gw_GXSetDrawDone`/`gw_GXWaitDrawDone`/`gw_GXSetDrawDoneCallback` (`shim_gx.c:94-96`) | OK | `video.c:186-200,267-275,142-149,429,63-140`; `shim_vi.c:194-199,229-241,263,269-279`; `shim_gx.c:94-96` |
| DVD drive-status mapping + async read-callback result semantics | `lb_80019230` maps `DVDGetDriveStatus()`: 5→0, 4→1, 6→2, 11→3, -1→4, 1→5, default→-1 (`lb_0192.c:89-107`); `lb_800192A8` shows a message only for `i != -1 && i != 5` (`lb_0192.c:119`); devcom's DVD callbacks treat `result == -1` as a fatal disc error and set `HSD_DevCom_804D7804` (`devcom.c:242-244,275-277`) | `gw_DVDGetDriveStatus` returns `GW_DVD_STATE_END` (0) after `gw_wait_idle()` (`shim_dvd.c:129-132`) — 0 hits the `default` → -1 arm of `lb_80019230`, so no spurious disc-error message ever appears; reads complete synchronously (`shim_dvd.c:241-245`) and the callback is queued through `gw_defer` so it runs after devcom sets its in-flight flag (`shim_dvd.c:250`); the callback passes `(int)(int32_t)result` where 0=ok, -1=fail (`shim_dvd.c:205-209,238,244,247`), matching devcom's `-1` error test; a NULL destination is reported and turned into `result=-1` instead of faulting the CRT (`shim_dvd.c:233-239`) | OK | `lb_0192.c:89-107,119`; `devcom.c:242-244,275-277`; `shim_dvd.c:129-132,205-209,233-245,250` |
| ARQ completion deferred until after devcom sets its in-flight flag | `HSD_DevComARAMWakeUp` posts `ARQPostRequest(..., HSD_DevComARAMCallback)` **then** sets `aramstate = 1` (`devcom.c:150-155`, and `:156-167,168-194` for the other types); `HSD_DevComStdCallback` clears `aramstate = 0` and re-wakes both queues (`devcom.c:42-57`); the DVD path sets `HSD_DevCom_804D77F5 = 1` after `DVDReadAsyncPrio` (`devcom.c:346-349,356-359`) | `gw_ARQPostRequest` does the memcpy inline then queues `gw_arq_complete` through `gw_defer` (`shim_ar.c:113-123`), so the callback never runs inside the `ARQPostRequest` call frame — by the time `gw_run_deferred` drains it (`shim_vi.c:192` in `gw_frame_tick`, `:221` in `gw_wait_idle`), `aramstate`/`HSD_DevCom_804D77F5` are already 1 and the node is not freed under the outer frame (the DEVLOG §1.20 `HSD_DevComARAMWakeUp+0x1E1` crash) | OK | `devcom.c:42-57,150-155,346-359`; `shim_ar.c:113-123`; `shim_vi.c:192,221` |
| Alarm re-entrancy / catch-up / cancel-and-re-arm semantics | the pad heartbeat arms a periodic alarm and re-arms by `OSCancelAlarm`+`OSCreateAlarm`+`OSSetPeriodicAlarm` (`lb_0195.c:106-112`); one-shot alarms are load-bearing (3 ms in `lmemory.c`, DEVLOG §1.2); a handler may itself reach `gw_wait_idle` via `DVDGetDriveStatus` (`shim_dvd.c:130`) | `gw_os_run_alarms` is guarded non-re-entrant (`shim_os.c:249-253`, mirroring a timer interrupt that cannot preempt itself); a `while (ticks >= fire_at)` catches up multiple periods (`shim_os.c:256,271`); it detects a handler that cancelled or re-armed the alarm (`a->handler != handler` → break, `:263-265`) and clears one-shots vs advancing periodics (`:266-271`); `OSCancelAlarm`/`OSSetAlarm`/`OSSetPeriodicAlarm` manage the same slots (`shim_os.c:196-229`) | OK | `lb_0195.c:106-112`; `shim_os.c:196-229,244-275`; `shim_dvd.c:130` |
| CARD async pending counter settles (never left dangling) | `lb_8001A184` zeroes `_p(x8AC)`, then bumps it only when an async mount is *accepted* (`lbcardnew.c:246,264`), and the completion callbacks decrement it (`lbcardnew.c:183,229`); a nonzero count returns `0xB` (busy) instead of settling (`lbcardnew.c:267-274`) | every CARD async entry returns `CARD_RESULT_NOCARD` (-3) synchronously and never calls back (`shim_card.c:61-160`, mount at `:133-139`); `lb_80019BB8(-3)` → 0xF (`lbcardnew.c:19-22`), so the accept path is skipped, `_p(x8AC)` stays 0, and the spin at `lbcardnew.c:272` never engages | OK | `lbcardnew.c:246,264,183,229,267-274,19-22`; `shim_card.c:133-139` (and `:23-32` for the probe) |

### C.1 Regression-check rows (already-fixed invariants — do NOT re-fix)

| invariant | fix site (`file:line`) | status | notes |
|---|---|---|---|
| Pad-alarm `period == 0` never arms (the black-window spin) | `gw_init_lomem` writes `__OSBusClock` = 162 MHz (`gw_runtime.c:92`), so `OSSecondsToTicks(1/60)` in `lb_0195.c:85` is nonzero | regression-check | `lb_0195.c:77-93`: with a zero bus clock the period computes to 0, `lb_0195.c:89` (`x40 == period`) returns early and the pad alarm is never armed, leaving `lb_80019894()` empty and `gmscene.c:292` spinning (DEVLOG §6.1). Verified only — `__OSBusClock` is already written, nothing re-fixed here. |

Notes on the C-table rows:

- **DVD status (row 2)**: `GW_DVD_STATE_END = 0` is returned *after* `gw_wait_idle()` drains alarms and
  deferred callbacks, which is what lets the pad-wait spin (`lb_0195.c` → `lb_800195D0` →
  `lb_800192A8` → `lb_80019230`) double as the pump for DVD/ARQ completions. The `0` value itself is
  not load-bearing beyond mapping to "no error message".
- **Draw-done (row 1)**: the shim fires the draw-done callback synchronously inside
  `GXSetDrawDone`/`GXWaitDrawDone` (the port renders synchronously), which is the one place it is
  *not* deferred. That is required: `HSD_VIGXSetDrawDone` (`video.c:269`) spins on `GXWaitDrawDone`
  until the callback clears `waiting`, so deferring it would deadlock. The deferred queue is only
  for callbacks the game expects to arrive *between* fields (DVD/ARQ), never for the in-call draw-done.
- **Alarm cadence caveat (row 4)**: §7.3 of the last DEVLOG session notes `alarms fired` only
  reaches ~120 before the (then-unfixed) crash even with the free-running clock. That is a symptom
  of the boot not returning to a waiting shim, not an alarm-semantics violation, so it is left as a
  note rather than a row; the alarm contract here (re-entrancy, catch-up, cancel/re-arm) is satisfied.
