# Console invariants

Audit of every hardware assumption the game makes that the PC port must reproduce, so the next
class of boot bug is pre-empted rather than discovered one crash at a time. This is a living
document: sections B and C are written by todos 14 and 15 and appended after this one.

Conventions:

- `status` is one of `OK` (writer/reader cited), `VIOLATED` (no writer, or a writer that writes
  the wrong value), `UNKNOWN` (no writer and no follow-up yet — every UNKNOWN carries a note), or
  `regression-check` (an invariant already fixed before this audit; the row only points at the fix,
  nothing is re-fixed here).
- `evidence` is `file:line` of the current source — never a HANDOFF claim. The audit reads the
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
| Arena start offset `0x3100` (above OS globals/vectors/bootinfo) | `shim_os.c:47,52-57` (`GW_ARENA_LO_OFFSET`, `gw_arena_ensure`) | regression-check | starting at 0 overwrote `gw_init_lomem`'s globals (HANDOFF §6.1) |
| Image base `0x10000000` (pointers always ≥ 16 MB → never misread as ARAM offsets) | `build_melee_pc.bat:17` (`/BASE:0x10000000 /DYNAMICBASE:NO`); `gw_runtime.c:227` | regression-check | pairs with `gw_ar_addr` bound in `shim_ar.c:94-106` |
| 32-byte global widening (DMA alignment, `devcom.c:420-423`) | `gwtool.cpp:580-588` | regression-check | widens every global definition to `Align(32)` |
| Low-memory OS globals (bus/core clock, mem sizes, TV mode) | `gw_runtime.c:86-99` (`gw_init_lomem`) | regression-check | detail rows in A.1; all five written big-endian |

---

## B. (pending)

To be appended by todo 14 (hardware guarantees: 32-byte DMA alignment of globals, ARAM rules,
timebase coherence, arena/heap layout, 24 MB simulated memsize).

## C. (pending)

To be appended by todo 15 (async/callback contracts: VI/XFB transitions, DVD status mapping, ARQ
completion + `gw_defer` ordering, alarm re-entrancy, pad sampling, CARD pending-counter).
