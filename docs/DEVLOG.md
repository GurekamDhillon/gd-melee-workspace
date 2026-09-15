# DEVLOG — Melee PC port

> **Handoff, current as of 2026-09-14.** The port boots, renders, plays VS matches, has working
> audio with effects, memory-card saves, GameCube-adapter input, hard 60 Hz pacing, and plays the
> pre-rendered cutscenes. This banner is the orientation; everything below is the running log,
> oldest first, and §8 onward supersedes the original 2026-09-12 handoff that follows it.
>
> **Read in this order.** `_research/port-dev-quickref.md` first (build/run commands, endianness
> contract, the conventions that have bitten people). Then, for whatever you are touching:
>
> | Area | Where |
> |---|---|
> | Build/run/relink, env vars | `_research/port-dev-quickref.md` |
> | Endianness (gwtool + `gw.h`) | quickref, plus the header comment of `pc/platform/gw.h` |
> | Boot gates, SDK behaviour | `_research/melee-boot.md`, `_research/console-invariants.md` |
> | Shim inventory + prototypes | `_research/shim_surface.md` |
> | Audio (AX mixer, aux buses, AXFX) | §19 |
> | Frame pacing / CPU cost | §20, and §13.1 for the original vsync fix |
> | THP cutscene decode | §21 |
> | Memory cards | §13.2, §18 |
> | Input (adapter, keyboard, pad scripts) | §13.4 |
> | Bug classes worth knowing before editing game source | §15, §16 (esp. §16.1) |
> | Known-bad things deliberately left alone | §17 |
>
> **The two bug classes that keep recurring**, both worth internalising before editing game source:
> the **GC-layout alias view** (§16.1 — code casts a pointer and indexes past a global assuming the
> console's contiguous symbol layout; on PC those are separate symbols, so it reads and writes
> unrelated memory), and **shim↔game endianness boundary violations** (quickref — any field a shim
> writes that game code can read must go through a `gw_*` accessor).
>
> **Open, known, not fixed:** §17 lists them. The live ones are the Zelda/Sheik double-respawn
> (§17.5, real VS bug), corrupted results-screen per-player stats (§17.2, deferred by request),
> the two single-player animation-descriptor crashes (§17.4), and a Dawn/WebGPU backend crash that
> is not game logic (§17.3). §16.3 and §16.4 list alias-view and audit findings that are identified
> but not yet fixed.
>
> **Not started:** netplay, replays, launcher/packaging, widescreen/upscaling, high-framerate sim.

## Original handoff, 2026-09-12 ~18:10 PDT

> **Stale — kept for the record.** This was written when the port had just linked for the first
> time and had not yet booted to a frame. Its environment notes (§0) are still broadly right but
> the quickref supersedes them; its status and next-steps are long since overtaken. §5 corrects
> two specific claims in §1 and §2.

**Milestone this session: the port now links and runs.** `_build/melee-pc.exe` launches, brings up
Aurora (D3D12 backend, 1280x960), maps MEM1 at 0x80000000, loads the disc FST, and boots far enough
to start audio/effect initialisation. The remaining work is boot debugging, not scaffolding — see §3
for the exact stopping point and the two candidate causes.

Written by opencode (WSL side) for the next agent, most likely Claude Code CLI on the Windows
side. Read this top to bottom before touching anything; the middle section lists facts that cost
real time to discover.

## 0. Environment / where things live

- Workspace root: `C:\gdm` (WSL: `/mnt/c/gdm`; `C:\gdm` is a junction to the checkout).
- `C:\gdm` is a junction to that root. All port docs/tooling use `C:\gdm\...`; use it too
  (it avoids the apostrophe in "GD's Melee").
- Game repo: `C:\gdm\melee` (doldecomp/melee). Port layer: `C:\gdm\melee\pc`.
- Toolchain: `C:\gdm\_toolchains\llvm\bin\clang.exe` (clang 23, runs fine from WSL directly).
- Aurora build: `C:\gdm\_build\build_aurora_melee.bat` → `C:\gdm\_build\ax86m`.
  `_build\build_aurora_extra.bat` builds the two libraries the simple example does not
  (`aurora_os.lib`, `aurora_pad.lib`, plus `aurora_si.lib`); both are needed to link the port.
- Port build/run (all in `C:\gdm\_build`):
  - `build_melee_pc.bat` — vcvars + `link` with `melee_link_objects.rsp` (all `masstest\out\*.obj`
    plus `masstest\shimobj\*.obj`) and `melee_link_libs.rsp` (the library set Aurora's own
    `examples/simple.exe` links, plus the three extra Aurora libs). Flags include
    `/LARGEADDRESSAWARE` (required — see §2) and `/MAP:melee-pc.map`.
  - `melee-pc.exe`, `melee-pc.pdb`, `melee-pc.map`, `melee-pc.log`.
  - `SDL3.dll` and `webgpu_dawn.dll` must sit next to the exe (copied from
    `ax86/_deps/sdl3_prebuilt-src/bin` and `ax86m/_deps/dawn-build`).
  - Run: `melee-pc.exe --iso "<path to GALE01 v1.02 iso>"`.
- gwtool: `C:\gdm\_build\gwtool\gwtool.exe` (build with `C:\gdm\melee\pc\tools\gwtool\build.bat`).
- Mass-compile scratch: `C:\gdm\_build\masstest`.
  - **`pipe_wsl.sh` is the current correct per-TU pipeline** (flags in §2). Run from `C:\gdm\melee`.
  - `files.txt` (984 TUs), `out/` (`.bc`/`.obj`/`.imports` per TU). **All 984 compile clean.**
  - `imports_all.txt` / `imports_data.txt`: regenerated authoritative external-symbol lists.
  - `unresolved_syms.txt`: **290** symbols referenced by game objects but not defined by them —
    the raw link obligation before the shims are linked in (includes the three MSL console
    functions pulled in by `ansi_files.c`).
  - `still_missing_syms.txt`: **0** — every external symbol is now provided, so the remaining work
    is linking and boot, not shimming (see §3). Note two entries resolve through linker directives
    rather than object symbols: `gw___setjmp`/`gw___longjmp` are `/alternatename` aliases to the CRT
    in `shim_libc.c`, so a plain `nm` audit will still list them as undefined while the link
    resolves them.
  - `newly_added_syms.txt` / `removed_syms.txt`: diff vs the previous snapshot
    (`imports_all.pre-opencode.txt`).
- Research reports: `C:\gdm\_research\{melee-boot,aurora,shim_surface}.md`. The first two are the
  boot-gate/API bibles; `shim_surface.md` is the curated external-symbol list with prototypes.
- Previous Claude Code session: `baee277b-47a0-4abc-8652-1166575f103e` ("gd-s-melee-05"), state
  kept on the Windows side under the Claude Code project directory for this checkout.

## 1. What was completed this session

Platform shims are in `melee\pc\platform`.

1. **`shim_gx.c` — DONE.** All 98 GX functions + 3 render-mode data images + the 2 helpers declared
   in `shim_gx.h`. Matrices/float arrays converted via `gw_read_mtx`/`gw_read_mtx44`; `GXGetProjectionv`/
   `GXGetViewportv` written back big-endian; `GXProject` converts in and out; `GXSetArray` 3-arg →
   Aurora 5-arg with size = bytes-to-end-of-MEM1, `le=false`; `GXInitFogAdjTable` ported from
   `extern/dolphin/src/dolphin/gx/GXPixel.c:97`; draw-done routes through `shim_vi.c`;
   `GXSetMisc`/`GXSetTevClampMode` are `GW_STUB()`; `GXCopyDisp` calls `gw_frame_mark_content()`.
   Coverage verified against `imports_all.txt`.
2. **`shim_os.c` + `shim_os.h` — DONE.** All 44 OS imports. This unblocks the platform build
   (`shim_vi.c` includes `shim_os.h` and calls `gw_os_run_alarms()`).
   - One timebase: `gw_OSGetTime`/`OSGetTick` return the port's virtual 40.5 MHz clock, and
     `gw_os_run_alarms` (called from `gw_frame_tick`) compares deadlines against it. Alarms:
     handlers are `void(void)` game functions cast to `OSAlarmHandler`, called with (handle, NULL).
     One-shot alarms are load-bearing (`lmemory.c`, 3 ms); periodic are the pad heartbeat
     (`lb_0195.c`, ~1/60 s) and the movie player.
   - `gw___OSCurrHeap` is game-visible data, stored **big-endian**; synced with Aurora's heap calls.
   - The arena is implemented here over `gw_mem1` (Aurora has `mem1Size=0`). Heap functions forward
     to Aurora's allocator, which works on the range handed to `OSInitAlloc` — always inside MEM1,
     preserving the game's "`>= 0x80000000` means main memory" invariant.
   - Interrupts no-op; threads/contexts inert. `OSGetResetCode()=0x80000000` skips the intro movie;
     `OSGetProgressiveMode()=0`.
3. **`shim_gxvert.c` — DONE.** 14 immediate-mode wrappers forwarding to Aurora (all the
   immediate-mode symbols the rebuilt game objects import).
4. **`shim_libc.c` — DONE (except `__va_arg`).** mem*/str*/printf family/math (with `sqrtf` keeping
   the Gekko Newton-Raphson over `gw___frsqrte`)/`__assert`/`__builtin_va_info`/`__cvt_dbl_usll`,
   the `__ctype_map` table (bits per `src/MSL/ctype.h`), stack-bound data symbols, and
   `__setjmp`/`__longjmp` **aliased at link time** to the CRT via
   `#pragma comment(linker, "/alternatename:...")` (verified present in `.drectve`). The alias is
   essential: a C wrapper would save the shim's frame, not the game caller's.
5. **`shim_pad.c` — DONE.** All 8 PAD imports; 7 forward to Aurora's SDL3 pad layer,
   `PADSetSamplingRate` is a stub (Aurora doesn't model it). `PADStatus` is 16 B in both trees.
6. **`shim_card.c` — DONE.** All 21 CARD imports report `CARD_RESULT_NOCARD (-3)` synchronously,
   never call back, `CARDProbe` returns 0. This is deliberate: boot spins on `CARDProbeEx` until it
   stops returning BUSY (-1), and async CARD calls must fail immediately or
   `lbcardnew.c`'s pending counter never settles. With no card, the card scene never opens.
7. **Game-source fixes** (write-gather pipe at `0xCC008000` does not exist on PC):
   - `melee/extern/dolphin/include/dolphin/gx/GXVert.h`: `#if DEBUG` →
     `#if defined(TARGET_PC) || DEBUG`, so TARGET_PC declares the vertex entry points extern.
   - `src/melee/gm/gm_1832.c`: raw quad → `GXPosition3f32` under TARGET_PC.
   - `src/sysdolphin/baselib/hsd_3915.c`: raw line vertex → `GXPosition2f32` under TARGET_PC.
   - `src/melee/lb/lb_01F8.c`: `ASSERT_SIZE(lbl_804335B8_t, 0xA0)` guarded with
     `#if !defined(TARGET_PC)` (GXTexObj is 64 B under TARGET_PC; the struct is file-local and all
     access is by field name).
8. **Full pipeline rebuild — DONE, zero failures.** 984 game TUs, plus `mtx44.c`,
   `pc/gameworld/mtx_pc.c` and `pc/gameworld/gekko_fp.c` appended to `files.txt` and compiled
   through the same pipeline (987 manifest entries). Import lists and the unresolved/still-missing
   audits were regenerated with the game-world objects included.
9. **`shim_misc.c` — DONE.** Data-cache maintenance no-ops (`DCFlushRange`/`DCStoreRange`/
   `DCInvalidateRange`), `DBIsDebuggerPresent`=0, `PPCMfmsr`/`PPCMtmsr` stubs, and the four AI
   entry points as no-ops (Aurora has no AI; audio is a later project).
10. **`shim_ar.c` — DONE.** ARAM bump/stack allocator over `gw_aram`
    (`ARInit`/`ARAlloc`/`ARFree`/`ARGetSize`, 16 MB) and `ARQPostRequest` as a synchronous memcpy
    plus callback. Synchronous on purpose: `lbarq.c`'s no-callback path spins on completion without
    pumping the frame driver, so a deferred ARQ callback could deadlock boot. This deliberately
    overrides `shim_vi.h`'s deferral advice for ARQ (documented in the file).
11. **`shim_dev.c` — DONE.** MCC (GBA link), FIO (developer file I/O) and THP (FMV decoder) entry
    points: MCC/FIO fail immediately (unused on PC), THP is inert (opening movie is skipped).
12. **`MTXLightFrustum`/`MTXLightOrtho`/`MTXLightPerspective` ported into
    `pc/gameworld/mtx_pc.c`** from the plain-C bodies in `extern/dolphin/src/dolphin/mtx/mtx.c`
    (that file does not compile for the port). `files.txt` now also lists `mtx44.c`, `mtx_pc.c` and
    `gekko_fp.c`, so the audit's defined-symbol set matches the intended build.
13. **`shim_dvd.c` — DONE, host-verified.** Reads the user's disc image directly (Aurora's DVD is
    OFF): parses the boot block (FST offset/size at 0x424/0x428), walks the FST to map paths to
    nodes, opens files, and services `DVDReadAsyncPrio` as seek+read with the completion queued
    through `gw_defer` (devcom sets its in-flight flag after the call, so an inline callback would
    see a half-updated request). Verified by compiling the shim with gcc against the real ISO and
    cross-checking every lookup against an independent Python FST walker — identical entry numbers
    (`/develop.ini` is genuinely absent from the retail FST; `/usa.ini` is a 0-byte file).
14. **`gw_wait_idle` added to `shim_vi.c`** (see §2): melee's pad-wait spin never reaches
    `VIWaitForRetrace`, so the frame-driven clock and alarm queue needed a second entry point.
15. **`shim_ax.c` — DONE.** All 35 AX imports. Everything is inert except the four FX init calls,
    which return 1 because `axdriver.c:981-1005` tests `== 1`; `AXAcquireVoice` reports "no voice"
    with NULL, which callers tolerate.
16. **Boot-critical varargs removed from the game source.** `HSD_SetInitParameter` is variadic and
    carries the render-mode pointer plus FIFO/heap sizes during `gmmain` boot, but clang lowers the
    port's `MSL/stdarg.h` to helpers that cannot recover arguments (see §2). Under `TARGET_PC` it is
    now `HSD_SetInitParameterU32` / `HSD_SetInitParameterPtr` (declared in `initialize.h`, call
    sites in `gmmain.c`); the original variadic body is kept for the matching build.
17. **Remaining data/library gaps closed.** `src/MSL/float.c` added to `files.txt` (defines the two
    `MSL_TrigF_*` constants), `src/MSL/ansi_files.c` added (defines `__files`, whose `write_proc`
    and `state` fields the debug code touches), the three MSL console functions stubbed in
    `shim_libc.c`, and `gw___va_arg` added there as a zero-returning placeholder.
18. **The port links.** `_build/build_melee_pc.bat` (plus the two generated response files) links
    `melee-pc.exe` from 1003 objects and the Aurora/Dawn/SDL3 libraries. Three fixes were needed:
    `aurora_os`/`aurora_pad`/`aurora_si` had to be built (the `simple` example never needed them);
    four shim functions were duplicated in game TUs (`memzero`, `__assert`, `expf`, `powf`) and were
    removed from `shim_libc.c`; and `gw_GXSetCopyClamp` had to be a stub because Aurora declares but
    does not define it.
19. **The port runs.** With `/LARGEADDRESSAWARE` and the two DLLs copied next to the exe, it brings
    up Aurora (backend 2, 1280x960), maps MEM1 at 0x80000000, byte-swaps 19702 link-time pointers,
    opens the disc image and parses the FST (1212 nodes), then boots into `gmmain` through VI/GX/PAD/
    CARD/OS init, HSD init, the DVD/ARQ load chain and into audio initialisation.
20. **Two runtime fixes along the way**: the by-value struct ABI (GXColor/GXColorS10 — see §2) and
    ARQ completion now goes through `gw_defer` (the inline callback re-entered HSD's ARAM state
    machine and freed the node the outer frame was still using — crash at
    `HSD_DevComARAMWakeUp+0x1E1` reading `aramDC`).

## 2. Hard-won facts — do not re-derive

- **Correct game-world compile flags** (in `_build/masstest/pipe_wsl.sh`): `-fgnu89-inline` and
  `-include src/MSL/math_ppc.h` (pulls in `src/MetroTRK/intrinsics.h`). Without the force-include,
  ~18 files calling `__frsqrte`/`sqrtf_accurate` fail: `__frsqrte` is not a clang builtin and
  `MSL/math.h` only includes `math_ppc.h` under `MWERKS_GEKKO`. Without `-fgnu89-inline`,
  `math_ppc.h`'s `extern inline sqrtf` emits a `gw_sqrtf` definition into every TU. This matches the
  intent documented in `src/placeholder.h`.
- **Post-rebuild import diff** (`newly_added_syms.txt`): 14 immediate-mode symbols (defined by
  `shim_gxvert.c`) + `gw___frsqrte` (provided by game-world `pc/gameworld/gekko_fp.c:93`, the real
  Gekko estimate table). `removed_syms.txt` entries are artifacts of TUs that previously failed.
- **Struct-by-value ABI (got this wrong once; it cost a crash)**: `imports_all.txt` shows these
  arguments as `ptr` because that is the LLVM `byval` representation, but at machine level the value
  is passed **inline** — 4 bytes for `GXColor`, 8 for `GXColorS10`. Because gwtool byte-swaps the
  caller's materialisation of the copy, the inline bytes are the raw big-endian game bytes again.
  Shim signatures therefore take the struct **by value**, exactly as melee's prototype declares it:
  `GXColor` (all u8) passes straight through, `GXColorS10` swaps each s16. Verified at a call site
  (`pushl %ecx` of the four colour bytes; `movq` of the 8-byte S10) and by disassembling
  `GXSetCopyClear`, where treating the value as a pointer faulted at `+0x9`.
- **`/LARGEADDRESSAWARE` is mandatory**: without it a 32-bit process only owns address space below
  0x80000000, `VirtualAlloc` for MEM1 fails (error 487) and the port falls back to a low address —
  which silently breaks the game's "`< 0x80000000` means ARAM" rule. The flag is in
  `build_melee_pc.bat`; verify with `gw: MEM1 24 MB at 80000000` in the log.
- **Game-world vs shim split**: `files.txt` includes the game TUs plus
  `extern/dolphin/src/dolphin/mtx/mtx44.c` and the port's game-world files
  (`pc/gameworld/mtx_pc.c`, `pc/gameworld/gekko_fp.c`). Everything else from the SDK is replaced by
  native shims. `DCFlushRange`/`DCStoreRange`/`DCInvalidateRange` are DMA-coherency only and are
  no-ops on x86; `PPCMfmsr`/`PPCMtmsr` are stubs (`shim_misc.c`).
- **`__va_arg` is the remaining libc unknown.** The port's `src/MSL/stdarg.h` defines
  `va_arg(ap,t)` as `*((t*)__va_arg(ap, _var_arg_typeof(t)))` with `_var_arg_typeof` = 0 for
  non-MetroWerks, and `va_start` only calls `__builtin_va_info`. Until `__va_arg` (and whatever
  `__builtin_va_info` must initialise) is implemented, variadic game functions are broken. Gwtool
  deliberately rejects clang's native `va_arg` IR instruction, so this cannot be bypassed. Identify
  which variadic game functions are on the boot path before launch.
- **Aurora build disables modules** (`build_aurora_melee.bat`): `AURORA_ENABLE_DVD=OFF`,
  `AURORA_ENABLE_CARD=OFF`, `AURORA_ENABLE_THP=OFF`. DVD/THP shims must be self-implemented; PAD
  and AR are available.
- **OS heap flow**: `HSD_OSInit` (`src/sysdolphin/baselib/initialize.c:167`) calls
  `OSInitAlloc(lo, hi, 4)` and uses the **return value as the new arena lo**, then carves the 512 KB
  audio heap and main heap. `__OSCurrHeap` is read by game code via the `OSAlloc`/`OSFree` macros —
  hence the big-endian storage.
- **Boot gates** (`_research/melee-boot.md`): `CARDProbeEx` never -1 (done, -3); XFB callback chain
  must run (VI shim owns it); the pad alarm heartbeat must fire (OS shim owns it); ARQ completion
  callbacks must fire or `HSD_SynthSFXWaitForLoadCompletion` hangs; `OSGetResetCode=0x80000000`
  skips `MvOpen.mth` (done).
- **Blocking-wait pump (boot-critical design point)**: melee's pad-update spin
  (`gm_801A4D34` -> `while (lb_80019894()==0) lb_800195D0();`) never reaches `VIWaitForRetrace`, so
  the frame-driven clock and alarm queue would never advance and boot would deadlock. The only shim
  that loop calls is `gw_DVDGetDriveStatus`, so it calls `gw_wait_idle()`: a rate-limited advance
  (one field per 16 ms of real time) of the virtual clock, followed by the due alarms and deferred
  callbacks. `gw_frame_tick` and `gw_wait_idle` share `gw_last_advance_ms` so the clock cannot run
  fast while frames are also ticking. If boot stalls in a wait loop, check this first.
- **Varargs are deliberately degraded.** clang compiles the port's `MSL/stdarg.h` into calls to
  `__builtin_va_info`/`__va_arg`, and `va_start` hands over only the address of the local `va_list`,
  so the helpers cannot recover the caller's arguments. The boot-critical caller
  (`HSD_SetInitParameter`) was converted to explicit parameters; every other variadic game function
  (e.g. `HSD_ForeachAnim`, the `efasync` effect creators, `dberror`) receives zeros from
  `gw___va_arg`, which logs once when first hit. Real support needs either gwtool to lower the
  va_list setup (it currently rejects `va_arg` IR) or those call sites ported to explicit
  parameters the way `HSD_SetInitParameter` was.
- **`psdisp.c` still has 36 raw FIFO sites.** Mapping: `GXWGFifo.u8` writes inside
  `if (kind & DispTexture)` are 1×8 texcoord indices → `GXTexCoord1x8`; `GXWGFifo.f32` pairs for
  s,t → `GXTexCoord2f32`. Guard with `#if defined(TARGET_PC)` keeping the originals. Needed for
  particles, not for first boot.
- **`imports_all.txt` includes game-to-game references.** Use `_research/shim_surface.md`'s module
  grouping to separate SDK obligations; `unresolved_syms.txt` already excludes game-defined symbols.

## 3. Where boot stops, and what to do next

The shim surface is complete and the port links and runs. Boot reaches `lbAudioAx_8002838C` (called
from `gmmain.c` right after `GXSetMisc`), i.e. past VI/GX/PAD/CARD/OS init, the DVD/ARQ load chain
and into audio/effect initialisation. Two observations from the last runs:

1. **`devcom.c:410` assert (`dest % 32 == 0`)** was the stopping point in the cleanest run. Every
   `ARAlloc` return was 32-aligned (`0x0`, `0x500`, `0x5F5EA0`, `0x625EA0`), so the offending `dest`
   is computed by a caller — likely the DSP-address doubling (`HSD_Synth_804D7784 *= 2`) or a
   caller-side offset. Re-add the temporary diagnostic used to chase this: a `TARGET_PC` `OSReport`
   of `file/src/dest/size/type` immediately before the asserts in `HSD_DevComRequest`, then read
   `melee-pc.log`.
2. **`efLib_Create +0x1FE` access violation** (in the run with that diagnostic present). `efLib_Create`
   is variadic and the effect creators read `Vec3*`/`f32*` arguments; with `gw___va_arg` returning
   zeros they dereference NULL. This is the varargs limitation (see §2) finally biting at runtime.
   Fix by porting that call family to explicit parameters, or by implementing real varargs.

After those: `psdisp.c`'s 36 raw FIFO sites (particles), the remaining boot gates in §2, then real
audio (AX is inert) and the usual acceptance work (determinism, rollback).

## 4. Reference commands

Syntax check / compile a native shim:

```
C:\gdm\_toolchains\llvm\bin\clang.exe --target=i686-pc-windows-msvc -fsyntax-only -DTARGET_PC \
  -Wall -Wextra -Wno-unused-parameter \
  -I C:/gdm/melee/extern/aurora/include -I C:/gdm/melee/pc/platform <file.c>
```

Compile one game TU through gwtool (prefer the script — it has the right flags):

```
cd C:\gdm\melee
bash C:\gdm\_build\masstest\pipe_wsl.sh src\melee\gm\gm_1832.c
```

Full rebuild (run from `C:\gdm\melee`, ~4 minutes at -P 4):

```
cat /mnt/c/gdm/_build/masstest/files.txt | xargs -P 4 -I{} bash /mnt/c/gdm/_build/masstest/pipe_wsl.sh {}
```

Regenerate the import aggregates and the unresolved list:

```
cd /mnt/c/gdm/_build/masstest/out
cat *.imports | grep '^F' | sed 's/^F\t//' | sort | uniq -c | sort -rn > ../imports_all.txt
cat *.imports | grep '^D' | sed 's/^D\t//' | sort -u > ../imports_data.txt
ls *.obj | xargs -n 40 $LLVM/bin/llvm-nm.exe | grep -E ' [TDBRCWVA] ' | awk '{print $3}' | sed 's/^_//' | sort -u > /tmp/defined.txt
cat *.imports | grep -E '^[FD]' | cut -f2 | sort -u > /tmp/imported.txt
comm -23 /tmp/imported.txt /tmp/defined.txt > ../unresolved_syms.txt
```

Check for leftover raw FIFO addresses in a transformed TU (expect 0 outside `psdisp.c`):

```
grep -c 3422584832 out.ll      # 3422584832 == 0xCC008000
```

Host-verify the DVD shim without the toolchain (this is how the FST parser was verified): compile
`shim_dvd.c` with gcc plus a small harness that stubs `gw_log`/`gw_iso_path`/`gw_defer`/
`gw_wait_idle` and prints `path -> entry, offset, length`, then diff against an independent Python
FST walker. The harness used last session was `/tmp/opencode/dvd_harness.c`.

Rebuild a shim and relink (the shim objects live in `_build\masstest\shimobj`):

```
C:\gdm\_toolchains\llvm\bin\clang.exe --target=i686-pc-windows-msvc -c -O2 -DTARGET_PC ^
  -I C:/gdm/melee/extern/aurora/include -I C:/gdm/melee/pc/platform ^
  C:/gdm/melee/pc/platform/<shim>.c -o C:/gdm/_build/masstest/shimobj/<shim>.obj
cmd.exe /c "cd /d C:\gdm\_build\ax86m && ..\build_melee_pc.bat"
```

Run it (keep it short — it is a GUI app; `timeout` works from WSL):

```
cd C:/gdm/_build && timeout 30s ./melee-pc.exe --iso "C:\\path\\to\\GALE01.iso"
```

Identify a crash: Windows records the fault offset, and the map file turns it back into a function.
The fault offset is an RVA, so add the image base (0x400000) before searching `melee-pc.map`:

```
powershell.exe -NoProfile -Command "Get-WinEvent -FilterHashtable @{LogName='Application'; ProviderName='Application Error'} -MaxEvents 1 | Select-Object -ExpandProperty Message"
# then find the map entry with the greatest address <= 0x400000 + offset
```

---

# 5. Session update, 2026-09-12 ~18:50 PDT

**Milestone: the game prints its own boot banner.** `main()` now runs to completion and enters
`gm_801A4510()`, the scene loop. Log:

```
gw: ARAlloc(1280) -> 0x4000
gw: ARAlloc(6248864) -> 0x4500
gw: ARAlloc(196608) -> 0x5F9EA0
gw: ARAlloc(32) -> 0x629EA0
# ---------------------------------------------
#    Super Smash Bros. Melee
# Distribution 1
# Language 1
# Arena Size 24 MB
# ARAM Free Size 9 MB
# DATE Feb 13 2002  TIME 22:06:27
```

Everything from `lbAudioAx_8002838C` (gmmain.c:165) through `gmMainLib_8015FBA4` and the banner
at gmmain.c:278 now runs. Reproducible across runs.

## 5.1 What was wrong

**ARAM base and `ARFree` (`shim_ar.c`).** `ARInit` returned 0; `ar.c:117` sets the stack pointer
to `0x4000` and returns it, reserving the low 16 KB. And `ARFree`'s argument is an **out**
parameter (`ar.c:88`) — the shim was reading it, so it consumed the uninitialised local that
`lbmemory.c:343` passes. Both fixed, with the real block-length stack kept in the game's
`ar_stack[0x10]` and written through `gw_w32`.

**ARAM vs pointer disambiguation (`shim_ar.c`, `gw_ar_addr`) — this was the big one.** The shim
classified any address below `0x80000000` as an ARAM offset. That is the game's own rule and it
holds for memory carved out of MEM1, but **statically linked game globals live in the exe image**,
far below that line. `devcom.c:151` hands ARQ exactly such an address (`&HSD_DevCom_804C6330_bufs[i]`,
a BSS array), so `memcpy` read ~20 MB past the end of ARAM. Now bounded by `gw_aram_size`, and the
image is linked at a fixed high base so no real pointer can ever be smaller than an ARAM offset.

**32-byte alignment of game globals (`gwtool.cpp`).** On hardware the DOL's data layout gave
DMA-touched globals 32-byte alignment and the SDK asserts it (`devcom.c:420-423`); MSVC gave 4.
gwtool now widens every global *definition* to 32. This is what cleared the `dest % 32 == 0`
assert that section 3 named as the stopping point. It costs a few hundred KB of padding.

## 5.2 Corrections to the sections above

- **Section 1.10 is stale.** It says `ARQPostRequest` is synchronous "on purpose", overriding
  `shim_vi.h`'s deferral advice. The code defers through `gw_defer`, and section 20 says so.
- **Section 2's varargs claim is wrong in an important way.** It says gwtool rejects clang's
  native `va_arg` IR "so this cannot be bypassed". True of `__builtin_va_arg`, which the PPC
  frontend expands inline — but **not of `llvm.va_start`**, which survives gwtool intact and is
  lowered correctly by the x86 backend. Verified: `leal 20(%esp), %eax; movl %eax, (%esp)`.
  That makes real varargs achievable; see 5.4.
- **TU count is 989**, not the 984/987 quoted in sections 0 and 1.8. (1003 objects is right.)
- `melee-pc.log` did not correspond to `melee-pc.exe` — the log predated the final link by a
  minute, which is why it showed one `ARAlloc` where section 3 describes four.

## 5.3 New tooling

- **Crash handler** (`gw_runtime.c`, installed first thing in `main`). Previously a fault just
  stopped the log mid-line, indistinguishable from a hang. Now logs exception code, faulting
  address resolved either to a `melee-pc.map` address or to `module+offset`, the access-violation
  target, registers, and a frame-pointer walk. Section 4's Event-Log procedure is no longer needed.
- **`/BASE:0x10000000 /DYNAMICBASE:NO`** — pins the image above ARAM (see 5.1) and makes runtime
  addresses equal the map's third column exactly.
- **`/OPT:NOICF`** — `/INCREMENTAL:NO` had turned on identical-COMDAT folding, which makes
  thousands of small game functions share an address and report the wrong name on lookup.
- **`_build/masstest/mapsym.sh <addr>`** — resolves a crash address to a symbol. It merges the
  map's *Publics by Value* **and** *Static symbols* tables; reading only the first attributes
  faults to whatever global precedes the real function, and most game functions are statics.
- **`_build/masstest/pipe_win.sh`** — Git Bash port of `pipe_wsl.sh`, same flags. No WSL needed,
  and a full rebuild of all 989 TUs takes **~30 seconds** at `-P 8`, not four minutes.
  `cc1.sh` and `pipe1.sh` are deleted; they were missing `-fgnu89-inline` and the `math_ppc.h`
  force-include and silently produced wrong objects.
- **Everything is now in git.** The port layer is four commits on `melee`'s `pc-port` branch; the
  build scripts, research and these notes are a separate repository at the workspace root.

## 5.4 Where it stops now, and the fix

`gw___va_arg` returns zeros, and the first caller is **`lbArchive_80017040`** (resolved via
`mapsym.sh`, `lbarchive.c:181`) — not `efLib_Create` as section 3.2 predicted. The zeroed section
names reach a CRT format routine as a NULL `%s` and it faults in `ucrtbase`.

This blocks **asset loading**, so it is the one thing standing between here and anything on
screen. `lbarchive.c`'s variadic loaders all share a shape: `va_start(args, symbols)` then forward
the `va_list` straight to `lbArchive_vLoadSections`/`Fatal`.

Design for the fix, given 5.2:

1. Under `TARGET_PC`, make `src/MSL/stdarg.h` use `__builtin_va_start` / `__builtin_va_end`
   (**not** `__builtin_va_arg`), and define `va_arg(ap, t)` as `*(t*)__va_arg(&(ap), sizeof(t))`.
2. Rewrite `gw___va_arg` in `shim_libc.c` to read the native pointer out of the `va_list`, advance
   it by `round4(size)`, and return a **byte-swapped** copy in a scratch buffer — game code does a
   swapped load on whatever it gets back.
3. Watch float promotion: the PPC frontend promotes `float` to `double` in variadic calls, so x86
   pushes 8 bytes where the game may ask for 4.

The `va_list` object itself must only ever be touched by the shim: `llvm.va_start` writes it
natively, so a swapped load from game code would read garbage. Same hazard as the `jmp_buf`.

After that: `psdisp.c`'s 36 raw FIFO sites, then real audio, then the GX path gets exercised for
the first time — nothing has drawn yet, so that is where the unknown-unknowns are.

---

# 6. Session update, 2026-09-12 ~19:30 PDT — the black screen

Boot got past the banner and into `gm_801A4510()`, and the window came up **black**. Cause found
and fixed; a different failure now sits behind it.

## 6.1 Why it was black

`gw_arena_ensure` (`shim_os.c`) started the arena at `gw_mem1` itself, i.e. `0x80000000`. A real
GameCube reserves the bottom of MEM1 for the OS globals, the exception vectors and the disc
header, and `OSInit` leaves `__OSArenaLo` above all of it. Starting at zero meant the game's first
allocation landed on that region. Nothing was filling it in either.

`dolphin/os.h` reads those globals through raw pointers -- `__OSBusClock` is literally
`*(u32*)0x800000F8` -- so on PC they were zero. `OS_TIMER_CLOCK` is `OS_BUS_CLOCK / 4`, so **every
`OSSecondsToTicks` and `OSMillisecondsToTicks` in the game evaluated to zero.** `lb_0195.c:87` then
computed a pad sampling period of 0, found it already equalled the stored period, returned early,
and never armed the pad alarm. With the pad queue permanently empty, the scene loop

```c
while ((pad_queue_count = lb_80019894()) == 0) { lb_800195D0(); }   /* gmscene.c:292 */
```

spun forever without reaching the rendering below it. No crash, no log, no frame — 3.2 billion
`gw_wait_idle` calls in twenty seconds.

Fixes: arena now starts at `+0x3100`; `gw_init_lomem` writes the bus clock (162 MHz), core clock,
memory sizes and TV mode, big-endian; and `gw_os_run_alarms` gained the re-entrancy guard
`gw_run_deferred` already had. The alarm now arms and fires.

**Note for §2 of the original handoff:** `melee-boot.md`'s claim that there are no `0x800000xx`
low-memory reads in game code is wrong. It is a grep-negative, and `dolphin/os.h` reaches them
through macros, not literals.

## 6.2 Diagnostics added

Because none of this produced any output, the tooling matters as much as the fix:

- **Watchdog thread** (`gw_start_watchdog`) samples the game thread's pc every two seconds and
  names it, flagging an unchanged pc as a spin. This is what found the loop.
- **Counters**, logged with each watchdog sample: retraces, frames actually presented,
  `gw_wait_idle` calls, alarms armed/fired, and `GXCopyDisp`/`GXBegin`/display-list counts. The
  line `retrace=2 presented=1 alarms armed=0 fired=0 prim=0` is what made the diagnosis obvious.
- **`_set_invalid_parameter_handler`**, since the CRT's fast-fail path bypasses SEH entirely.
- **`MELEE_PC_TRACE_OSREPORT=1`** logs every OSReport format string before it is expanded, for
  crashes inside the formatter. Off by default.

## 6.3 Where it stops now — unresolved

The process dies about 14 seconds in with **`0xC0000409` (STATUS_STACK_BUFFER_OVERRUN)**, faulting
module `ucrtbase.dll+0x2da71` per the Windows Application event log. `__fastfail` bypasses SEH, so
nothing is logged and no handler runs.

Ruled out:
- the CRT invalid-parameter handler is installed and never fires (release ucrtbase's
  `_invalid_parameter_noinfo_noreturn` calls `__fastfail` without consulting it);
- not OSReport formatting — with the trace on, the last format completes;
- not `fread` with a NULL destination — guarded in `shim_dvd.c`, never triggers.

Game objects carry no stack cookies (clang does not add them), so whatever failed the check
belongs to the CRT or to Aurora/Dawn. Two ways forward: install the Windows SDK debuggers and
catch it under `cdb`, or replace the CRT calls in `shim_libc.c` with bounded local implementations
so there is no CRT invalid-parameter path left to hit.

Still true: `prim=0`. **No geometry has ever been submitted**, so the GX path into Aurora remains
completely unexercised. Expect unknowns there once the game gets far enough to draw.

---

# 7. Session update, 2026-09-12 ~19:50 PDT — handing off mid-investigation

Two changes landed since §6, both committed and building. The port still dies; what changed is
that we now know where.

## 7.1 The clock is no longer call-driven

`gw_ticks` was only stepped inside `gw_frame_tick` and `gw_wait_idle`, so **game time stopped
whenever the game was computing rather than waiting** — a fourteen-second run advanced about two
seconds of game time. Every duration the game measured was short by however busy the frame had
been. `gw_time_ticks` now derives from `QueryPerformanceCounter` at read time, scaled to the same
40.5 MHz, with the conversion split into whole seconds plus remainder so a long session cannot
overflow. `gw_time_advance_field` is retained but does nothing. `gw_wait_idle` keeps a
once-per-millisecond gate so a tight spin does not hammer the alarm queue.

This is worth understanding before trusting any timing behaviour you see: it changed what the game
does, not just what it reports.

## 7.2 The watchdog now catches the crash site

Sampling moved from every 2 s to every 100 ms, and it logs only when the pc enters a different
function — so a spin stays quiet, but **the last line in the log names where the game was when it
died.** Use `_build/masstest/mapsym.sh 0x<addr>` to resolve it (it merges the map's *Publics by
Value* and *Static symbols* tables; reading only the first gives wrong answers).

## 7.3 What that immediately told us — and it contradicts §6.3

The remaining `0xC0000409` fast-fail leaves:

```
gw: at melee-pc.map rva 0x1025C190     ->  _gw_lb_800195D0+0x0   (lb_0195.c)
```

**The crash happens inside the pad-wait spin, not in asset loading.** §6.3 assumed the latter,
and the DVD `fread` guard added there never fires. `lb_800195D0` calls `lb_800192A8(lb_8001955C)`
and `lb_8001CC84`; `lb_8001955C` reaches `HSD_PadGetResetSwitch`, `lb_8001B6F8` and `lb_8001CC84`.
That is the code to instrument next.

Note also `alarms fired` still only reaches ~120 before death even with the free-running clock,
where 60/s over fourteen seconds should be many times that. Either the game leaves the spin
without returning to a waiting shim, or something is re-arming the alarm. Worth resolving — it is
the same class of bug as everything else that has bitten so far.

Still `prim=0`: **no geometry has ever reached Aurora.**

## 7.4 Not done

- **The debuggers were not installed.** The session ended first. `winget install
  Microsoft.WinDbg` (or the Windows SDK's Debugging Tools) then `cdb -g -G melee-pc.exe --iso ...`
  would catch the fast-fail live with a real stack, which is still the fastest way to close this
  out. Everything above was obtained without one, so treat it as a shortcut rather than a
  prerequisite.
- The **systematic sweep of console invariants** discussed as the better method than serial crash
  triage. Every blocker so far has been one of these — ARAM base `0x4000`, MEM1-vs-pointer
  classification, 32-byte DMA alignment, the low-memory OS globals, the arena start offset — and
  none was a logic bug in a shim. Walking `dolphin/os.h` and the decomp for every fixed-address
  read and every "the hardware guarantees this" assumption, in one pass, is likely higher yield
  than fixing the next crash and waiting for the one behind it.

---

# 8. Session update, 2026-09-12 ~21:50 PDT: first frame, D3D11 stable

**Milestone: the port reaches the visible Melee title screen and accepts keyboard input.** This
closes out `.omo/plans/melee-pc-boot-unblock.md`: boot is unblocked, D3D11 is the stable default
backend, and a keyboard bridge lets the game be driven by hand far enough to confirm it responds.

## 8.1 What changed (commits)

Three commits on `melee` `pc-port` (branch HEAD `8cd84fae4`):

1. `98e49e856 pc: gx: copy only the referenced extent of indexed vertex arrays`. The Aurora
   `push_gx_draw` array-copy fix that cleared the `0xC0000409` (`STATUS_STACK_BUFFER_OVERRUN`)
   fastfail from §6.3/§7.3: keep `array.size` as the bounds assert, copy only the indexed extent.
2. `616aab3af pc: default to the D3D11 backend (D3D12 hits a Dawn frame-encode AV)`. Workaround for
   the D3D12 present/encode AV (§8.3); D3D11 is stable.
3. `8cd84fae4 pc: add keyboard controls for testing (WASD/J/K/Enter)`. Keyboard bridge in
   `shim_pad.c`; user-confirmed by hand (drove the game from "No Memory Card" into the title screen
   and pressed Start).

## 8.2 Run it

```
cd C:/gdm/_build && timeout 45s ./melee-pc.exe --iso "C:\iso\Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso"
```

Controls (keyboard bridge on channel 0, marked `TARGET_PC test controls` in `shim_pad.c`, easy to
disable): **W/A/S/D** → analog stick (up/left/down/right), **J** = A, **K** = B, **Enter** = Start.

## 8.3 Known issues (evidence pointers)

- **D3D12 backend AV (ESCALATE to an Aurora/Dawn owner).** Deterministic access violation at
  `webgpu_dawn.dll+0x363548` in Aurora/Dawn's present/encode path, ~46 frames in. The port's frame
  contract is correct; the fault is D3D12-backend-specific. Worked around by defaulting to D3D11
  (§8.1). Proofs: `.omo/evidence/task-10-melee-pc-boot-unblock.log` and
  `.omo/evidence/task-10-d3d11-run1-melee-pc.log`.
- **Start-at-title crash.** Pressing Start at the title screen crashes. This is the next blocker.
  No dump was captured.

## 8.4 Verification gaps

The automated runtime-verification set is INCOMPLETE and its evidence unreliable: todos 8, 9, 11, 12
were cancelled or left unfinished because two workers collided over the single game instance (runs
killed; one log froze at `retrace=782`) and the screen capture grabbed the occluding terminal instead
of the game window. Recommendation: one clean single-worker pass with the game window foregrounded
and the captured image validated as the game before trusting any of it.

## 8.5 Start-at-title crash: FIXED

The §8.3 blocker is resolved. Root cause: `gw_AXAcquireVoice` returned NULL, and the menu-music
stream path `HSD_Synth_8038B5AC` dereferences `voice->index` immediately, faulting at NULL+0x18 on
the title→menu transition. Fix: a minimal 64-voice AX pool in `melee/pc/platform/shim_ax.c` (commit
`83d96fbc0`) that returns a distinct `AXVPB`-layout voice, `index` written big-endian via `gw_w32`,
stealing the lowest-priority voice when full. Audio stays inert. The game now reaches the visible
Main Menu (1-P Mode / VS. Mode / Trophies / Options / Data); evidence
`.omo/evidence/task-start-run4-after-mainmenu.png`, `.omo/evidence/task-start-crash-melee-pc-boot-unblock.log`.

---

# 9. Session update, 2026-09-13 ~00:20 PDT: in game, with a black screen

**Milestone: the port reaches an actual match.** Fight logic runs — damage lands both ways,
projectiles fire, a full match plays out with no crash. What it does not do is draw: the screen is
black while unpaused. That is now the single open blocker.

This section covers everything after §8.5, which was previously recorded only in
`.omo/start-work/ledger.jsonl`.

## 9.1 What changed (commits)

Four commits on `melee` `pc-port`, HEAD `7c84fb83a`:

1. `456be389e pc: unblock map loading (ARQ owner, re-armed alarms, ARQ spin)`.
2. `ceb3d0417 pc: route particle vertices through the named GX entry points`.
3. `031452c9b pc: address game globals directly where .bss contiguity was assumed`.
4. `7c84fb83a pc: gx: TEMPORARY diagnostics for the black-screen investigation` — **revert this
   one** once the black screen is closed out. It is instrumentation, not a fix.

## 9.2 The three map-load stalls (commit 1)

Each was found by freezing a user-supplied run log and resolving the fault through `melee-pc.map`.
They came out one behind the other: fixing each exposed the next.

- **`ARQ-OWNER-UNSET`.** `gw_ARQPostRequest` discarded its `owner` argument, so `ARQRequest.owner`
  (offset `0x04`) stayed zero and `lbArqHandle.node` read back NULL — an AV reading `0x4` in
  `lbArq_80014AC4+0x12`. Stored big-endian via `gw_w32`. Evidence:
  `.omo/evidence/user-mapload3-run-melee-pc.log`.
- **Re-armed alarms.** `gw_os_run_alarms` treated "handler unchanged after the callback" as "still
  idle", so a one-shot that re-arms itself from inside its own handler was cancelled after one
  firing. lbMemory's chunked memcpy (`fn_80015184`) does exactly that, rescheduling 3 ms out, so
  the copy and the preload heap compaction it drives stalled forever. Now compares `fire_at` too.
  Evidence: `.omo/evidence/user-mapload4-run-melee-pc.log` (spin at `lbDvd_800189EC`,
  `lbdvd.c:647`, retrace frozen at 759 over 15 samples).
- **The ARQ spin.** The callback-less path in `lbarq.c` spun with no shim call in the loop, so the
  deferred completion queue never drained. Pumps `wait_idle()` now.

## 9.3 Two classes of port bug worth generalising

Both of these will recur. Check for them first when something faults on garbage.

**Raw hardware-address stores.** `GXWGFifo` is the write-gather pipe at the fixed address
`0xCC008000` — real on a GameCube, unmapped here. `psdisp.c` had ~20 raw `GXWGFifo.f32 = ...`
stores emitting particle vertices straight into it. All are now named GX entry points
(`GXPosition3f32` / `GXTexCoord2f32` / `GXTexCoord1x8`), which `shim_gxvert.c` forwards to Aurora.
`GXVert.h` poisons the macro under `TARGET_PC`, so any surviving raw store is a self-documenting
**compile** error instead of a runtime AV. This is the same class as the fixed-address console
invariants in §7.4 — the systematic sweep proposed there is still the higher-yield method.

**Assumed `.bss` contiguity.** The port links each game global as its own symbol, so globals the
original `.bss` laid out adjacently no longer are. Any code that reaches one global by offsetting
from another through a struct view reads unrelated memory. Two instances fixed:
`particle.c`'s `hsd_8039D0A0` (cast `hsd_804D08E8` to get the list heads and the allocator — this
was the in-game AV reading `0x400AE148`) and `ftmaterial.c`'s `struct ft_MObjInfo* info = &ftMObj`.
Grep for casts of one global's address to a struct covering several.

## 9.4 The open blocker: black screen while unpaused

From `.omo/evidence/user-fight2-black.log` and the user's own testing of the current build:

- **(A)** The screen is black while the game is unpaused. Graphics appear **only when paused**.
- **(B)** Model geometry is corrupt when paused — and corruption was already visible on the
  "No Memory Card" screen, so it is **fundamental and pre-existing**, not fight-specific. Treat A
  and B as possibly separate bugs.
- The pipeline is **not** stalled: frames advance and present (`retrace 6362` / `presented 6360`),
  and the game is genuinely submitting geometry: roughly **291 `GXCallDisplayList` calls and 12
  `GXBegin` per frame**, which for Melee (whose stage and character geometry goes through display
  lists) is a real, populated scene. Only 3 no-op stubs are reached — `gw_GXSetCopyClamp`, `gw_GXSetMisc`,
  `gw_PADSetSamplingRate`).

### What has been ruled out

The DIAG instrumentation (commit 4) produced `.omo/evidence/user-diag-mtx.log` and
`user-diag-ingame.log`, which eliminate the two leading theories:

- **Transforms are sane.** Projection `2.235 / 2.637` with `-0.002 / -10.020` depth terms;
  `posmtx0` is identity at `z = -29`. Not garbage.
- ~~**The matrix-index path is unused.**~~ **WRONG -- see 9.7.** Those logs simply never reached a
  scene that used it. `PNMTXIDX` *is* configured, as `GX_DIRECT`, and multiple matrix slots are
  loaded per frame.

### The remaining lead

Present timing: `gw_frame_tick` / `gw_GXCopyDisp` `mark_content` versus Melee's XFB state machine
in `video.c`. "Visible only when paused" is a strong hint that content is being copied to, or
presented from, the wrong buffer for the normal double-buffered path, while the paused path happens
to land on the right one. Start there.

## 9.5 Standing directive: no input or capture tooling

**Agents must never build input-injection (`keybd_event`/`SendKeys`) or screen-capture harnesses.**
Every interactive step — navigating menus, pressing buttons — and every visual check is performed
by the human user, who supplies the reproduction and the log. Ask for a run; do not automate one.
This is recorded in `_research/port-dev-quickref.md`, which every worker prompt must say to read
first. `_research/scripts/capture_window.ps1` predates this directive and should be deleted.

## 9.6 State of the tree

`melee` `pc-port` is clean at `7c84fb83a`. The built `_build/melee-pc.exe` matches it and has been
run by the user: a full match, no crashes, black screen. The trailing
`webgpu_dawn.dll+0x363548` AV in `_build/melee-pc.log` is the **known shutdown-path Dawn fault**
fired when the window closes (§8.3), not a gameplay regression.

## 9.7 Black screen: what has been ruled out, with evidence

A long diagnostic session on 2026-09-13 did not find the cause, but eliminated most of the search
space. **Read this before forming a theory** -- several obvious ones are already dead, and two
claims in 9.4 above were disproved by it.

All instrumentation is temporary and reverts together: commits `7c84fb83a`, `b02a1c55a`,
`1044f0021`, `f2ee29190` (port side) plus an uncommitted Aurora-side dump in
`extern/aurora/lib/gx/command_processor.cpp` and the validation toggle in `lib/webgpu/gpu.cpp`.

### The central fact

**The GPU receives identical work whether the screen is black or not.** A paused/unpaused A/B in
one run (`.omo/evidence/user-fight3-pause-ab-drawcalls.log`) shows the paused stretch bit-identical
across ~510 consecutive samples, and the unpaused stretches varying only as animation would:

| State | display lists | Aurora draw calls | vertex bytes |
| --- | --- | --- | --- |
| Unpaused (black) | 384-409 | 367-393 | ~172.5k-174.9k |
| Paused (models visible) | 367 | 368 | 173,554 |

Same draws, same volume, same state. Only the *contents* differ. So the fault is not in what is
submitted; it is in the values, or in what happens to them after submission.

### Eliminated, each on evidence

1. **Present timing / XFB state machine.** Copies, presents and retraces run 1:1 (`presented` ~=
   `retrace` ~= `copydisp`). Would explain lag or tearing, not black.
2. **The `HSD_RP_BOTTOMHALF` garbage copy** (video.c:254-257). `GXSetCopyClamp` fires once per copy
   per frame, so the game is on the single-copy `HSD_RP_SCREEN` path; no garbage copy occurs.
3. **GX state.** `colorupd=1 alphaupd=1 zcmp=1 zupd=1 clear=1` on every sampled frame, always.
4. **Nothing drawn into the presented frame.** ~290-370 `GXCallDisplayList` per frame throughout.
5. **Display lists not executing.** Aurora issues ~360 real draw calls and ~173 KB of vertex data
   per frame (`aurora_get_stats()`, which the backend already exports -- no Aurora change needed).
6. **Mid-frame `GXCopyTex` wiping the EFB.** Melee issues exactly two per frame, both with clear,
   and a copy-with-clear does wipe the EFB -- but the segment breakdown is
   `[17 dlists] -> copytex -> [17 dlists] -> copytex -> [359 dlists] -> CopyDisp`. The bulk of the
   scene is submitted *after* the last clearing copy.
7. **Matrix lifetime.** `GXLoadPosMtxImm` writes all 12 floats into the FIFO by value at call time
   (`GXTransform.cpp:56-65`); the port's stack local cannot dangle.
8. **Wrong transforms.** Verified numerically, not by eye: every logged position matrix has row
   lengths of exactly 1.100 and pairwise dot products of 0.000 -- a valid orthogonal rotation with
   uniform scale -- translated to z about -100, inside the near=10/far=5010 frustum.
9. **Stale cached vertex uploads.** A dead end I pursued and reverted: `command_processor.cpp`
   re-uploads an indexed array only when its pointer, size or endianness changes, which looks like
   it would serve stale data to a game that animates in place. It does not, because
   `recording.cpp:569-571` clears every `cachedRange` at the end of each frame. The cache never
   survives a frame.
10. **Illegal GPU usage.** Aurora disables WebGPU validation and robustness in NDEBUG builds
    (`lib/webgpu/gpu.cpp:937-948`). Rebuilt with both ON: a full match runs with **zero** errors, so
    bindings and buffer sizes are legal and out-of-bounds reads now return zeros -- still black.
11. **The D3D11 backend.** Retested D3D12 (see 9.8): it still faults in Dawn at exactly the address
    documented in 8.3, so it cannot be compared -- but this was worth testing, see the live lead.
12. **Endianness and format decoding.** Read directly: `bswap16`/`bswap32` handle `le=false`
    correctly (shader.cpp:1632-1698), and `fetch_s16_3` sign-extends with `<<16 >>16` then divides
    by `2^frac` (shader.cpp:1867-1870) -- correct for Melee's `S16, frac=10` positions.

### The live lead

**Immediate-mode geometry renders; indexed geometry does not.** The HUD (stock icons, percentages,
timer, pause UI) is perfect throughout, and the "No Memory Card" screen renders at `dlist=5,
prim=27` -- essentially all immediate mode. The stage and characters are `dlist~370, prim~4` --
essentially all indexed display lists -- and are invisible. Aurora feeds indexed arrays to the GPU
through *storage buffers*, a different path from immediate attributes.

Since the binding of that path is now proven legal (10) and its decoding proven correct (12), the
open question is whether `GXSetArray`'s base pointer and stride actually point at the vertex data
the display list expects. The uncommitted `DIAGVTX` dump in `push_gx_draw` decodes the first two
positions exactly as the shader will and prints them with stride and frac. Sane model-space
coordinates (order of tens) mean the data is right and the fault is downstream; garbage, zeros or
huge values mean a port-side `GXSetArray` bug -- which would explain the invisibility *and* the
corrupt geometry seen on static screens.

### Also worth knowing

- **PNMTXIDX is `GX_DIRECT`**, and slots `posmtx0/3/6...` are loaded per frame. 9.4's claim that the
  matrix-index path is unused is wrong; those earlier logs never reached a scene that used it.
- `gw_gx_dlist_count` counts **calls**, not bytes. The ledger's "2.1 MB of display list" was a
  misreading.
- **Aurora's `GXCopyDisp` is an empty stub** (`GXFrameBuffer.cpp:210`) while `GXCopyTex` beside it is
  fully implemented. Harmless today, because Aurora clears the EFB itself each frame
  (`frame_packet.hpp:72-74`, `recording.cpp:546`) and presents the EFB directly -- but it is a clear
  sign that Aurora's GX coverage is shaped by the game it was imported for, which is the general
  shape to suspect here.

## 9.8 Platform-layer changes from the same session

Commit `e3300cc92`:

- **Letterboxing.** Aurora's halves disagreed at init: the GX side defaults to
  `AURORA_VIEWPORT_FIT` (`gx.hpp:396`) while the window side defaults `g_frameBufferAspectFit` to
  false (`window.cpp:47`), and the window only learns the policy via `AuroraSetViewportPolicy`.
  Nobody called it, so GX believed it was fitting while the window stretched. Called explicitly at
  startup; resizing now preserves 4:3.
- **`MELEE_BACKEND=d3d12|d3d11|auto|vulkan`** overrides the pinned backend with no rebuild, so 8.3's
  D3D12 crash can be retested whenever Dawn is updated. Retested 2026-09-13: still faults at
  `webgpu_dawn.dll+0x363548` about two seconds in, unchanged by `98e49e856`. The D3D11 pin stands.
  Vulkan is not compiled in (`-DDAWN_ENABLE_VULKAN=OFF`) and would need a Dawn rebuild.

## 9.9 The black screen produces ZERO FRAGMENTS -- start here

The single most useful measurement of the 2026-09-13 session, and the one to build on.

`GXPeekZ` is exported by Aurora (`GXCpu2Efb.cpp`) and reads the depth buffer, so the port can
sample depth **without anyone looking at the screen**. `shim_gx.c` reads a 7x5 grid across the
frame once every 30 copies. In a live match, every sample, every frame:

```
gw: DIAG   depth grid: distinct=1 min=0xFFFFFF max=0xFFFFFF
```

`0xFFFFFF` is the cleared value. The depth buffer is **completely untouched after ~350 draw
calls**. Depth writes are enabled (`zupd=1` on every sampled frame), so rasterised triangles would
have to leave varying depth behind. They leave none.

This is not a sampling artefact: `recording.cpp:1095` (`finish()`) sets `captureDepthSnapshot` on
the **final** render pass of the frame, so the snapshot is taken after every draw, not during the
early `GXCopyTex` passes. Evidence: `.omo/evidence/user-depthgrid-zero-fragments.log`.

### What this means

The problem is **not** colour, TEV, materials, textures, blending or presentation. Every one of
those assumes fragments exist. None do. Something kills the geometry between the vertex shader and
the rasteriser, for indexed 3D geometry only -- the HUD, which draws through the immediate path,
rasterises fine throughout.

### Refined by a follow-up A/B: it is PAUSE, not culling

`MELEE_FORCE_NOCULL=1` / `MELEE_FLIP_FRONTFACE=1` were added to `gx.cpp` (TEMP) to test culling.
The depth grid across both settings and both pause states:

| game state | culling | depth grid |
| --- | --- | --- |
| paused | off | `distinct=8`, min `0xFFB752` -- varies |
| unpaused | off | `distinct=1`, cleared |
| unpaused | on | `distinct=1`, cleared |

**Culling is exonerated.** Paused rasterises and unpaused does not, whatever the cull mode. Beware
the trap that caught this session: comparing "cull on, unpaused" against "cull off, paused" changes
two variables and looks like a culling fix. Always hold pause state constant.

So the mechanism is: **while the game is running, no triangle survives to the rasteriser; freezing
animation restores them.** Something recomputed per frame destroys the geometry.

### Shortlist, in the order worth testing

1. **Per-frame position matrices going bad (NaN, or huge).** Every vertex would land outside clip
   space, producing exactly zero fragments, and pausing would freeze the last good values and bring
   the scene back. Note the matrices validated as orthonormal in 9.7 came from a run whose pause
   state was never recorded, so that check may have measured a frozen scene and proved nothing
   about the animated case -- **re-verify with pause state held constant**. This may also connect to
   the `HSD_AObjSetFlags+0x12` NULL write seen in
   `.omo/evidence/agent-vertexcache-fix-run1.log`: `AObj` is HSD's *animation* object.
2. **Empty or wrong scissor/viewport** for the 3D pass specifically.
3. **Degenerate primitives** -- indices or primitive type decoded such that every triangle has zero
   area while animating.

### How to test cheaply

Force the suspect off and re-read the depth grid -- **the readout is automated**, so a run needs
someone to drive into a match but not to judge what is on screen. Log pause state alongside, or
capture a full unpaused -> paused -> unpaused sequence in one run, so the comparison is never
confounded.

Evidence: `.omo/evidence/user-nocull-depth-varies.log`, `.omo/evidence/user-nocull-pause-ab-depth.log`.

### Already ruled out by this measurement

Everything downstream of rasterisation. In particular, do not spend time on the present path, the
XFB state machine, TEV/material setup, or texture binding -- 9.7 lists what else is dead and why.

## 9.10 SOLVED (cause): the black screen is NaN position matrices

The hunt ends here. `shim_gx.c` now checks every position matrix as it is loaded and reports the
per-frame totals on the same sampled frames as the depth grid, so the two lines correlate without
any visual check. A single run, unpaused then paused:

| state | nan/inf elements | maxabs | rowlen | depth grid |
| --- | --- | --- | --- | --- |
| unpaused | **8013 of 9300 (86%)** | 9936.000 | [1.0000..10.0000] | `distinct=1`, nothing rasterises |
| paused | **0** | 417.051 | [0.5250..1.1000] | `distinct=8`, renders |

**While the game runs, 86% of every position-matrix element is NaN or infinite.** NaN vertices fail
every clip test, so no triangle reaches the rasteriser -- exactly the zero-fragment result of 9.9.
Pausing stops animation recomputing them, the matrices are clean, and the scene appears.

Evidence: `.omo/evidence/user-posmtx-nan-pause-ab.log`.

### Why every renderer theory failed

Nothing downstream was ever wrong. Aurora was faithfully drawing ~350 draw calls of NaN. The twelve
eliminations in 9.7 were all correct *and* all irrelevant: bindings, formats, endianness of vertex
data, culling, depth range, present timing and TEV are fine. **Do not reopen them.**

### What it also explains

- **Corrupt geometry on static screens** -- the same computation partially poisoned, where some
  matrices survive and others do not.
- **The `HSD_AObjSetFlags+0x12` NULL write** (`.omo/evidence/agent-vertexcache-fix-run1.log`):
  `AObj` is HSD's *animation* object, and the animation path is where this originates.
- **The corruption is graded, not binary.** Even the surviving unpaused matrices are inflated
  (`maxabs` 9936 vs 417 paused, row lengths to 10.0 vs 1.1), so this is a computation going
  progressively wrong rather than a single bad pointer.

### Where to look next

This is **game-side, in HSD's animation evaluation** feeding `HSD_JObjSetupMatrix` -- not the
renderer. Given that big-endian and struct-layout mistakes have been the recurring class in this
port (9.3, and the ARQ/alarm/particle fixes in 9.1-9.2), the first suspicion is animation keyframe
data (`FObj`) being read with the wrong endianness or stride: misread big-endian floats decode to
NaN readily, and that would poison animated joints while leaving static objects intact.

Instrument *upstream* of the matrix load -- at the point animation produces the value -- since
`gw_GXLoadPosMtxImm` already sees the damage after the fact. Remember the `TARGET_PC` rule: game
source changes stay behind `#if defined(TARGET_PC)` with the original kept, and the user's standing
directive is that agents do not change game logic without asking.

### Method worth keeping

The depth grid plus matrix health, logged together on the same frames, makes the failing and
working states **self-identifying** (`distinct=1` is the broken state). That removed the human
visual check from the loop entirely and is what finally isolated this after a dozen dead ends. When
comparing anything here, hold pause state constant -- see the trap in 9.9.

## 9.11 Tracing the NaN to its source: the camera's input vectors are garbage

Continuing from 9.10, which established that the black screen is NaN position matrices. The chain is
now traced end to end, each link measured rather than assumed:

```
garbage camera eye/interest  ->  NaN view matrix  ->  NaN modelview for ~87% of matrices
                             ->  NaN vertices     ->  zero fragments  ->  black screen
```

### The IK solvers are innocent

`HSD_JObjSetupMatrixSub` was instrumented (TARGET_PC-guarded, reads and counters only) to compare
the matrix straight out of `make_mtx` against the same matrix after the joint branch runs. In every
sample the two counts are identical -- `premake nan=197/6149  postjoint nan=197/6149` and so on --
so the IK branches change nothing.

**`resolveIKJoint1`'s uninitialised `var_f27`/`var_f28` (jobj.c:1102, flagged by a decomp `@todo`)
are NOT the cause.** They are still a genuine latent UB bug worth fixing one day, but confirming
before patching is what kept that from becoming another wasted cycle. Only the `default` branch runs
in a match; JOINT1/JOINT2/EFFECTOR never appear.

### The 4% -> 87% amplification points at a shared multiplier

| measurement | NaN rate |
| --- | --- |
| JObj matrices at setup | ~250 / 6100 = **~4%** |
| position matrices at `GXLoadPosMtxImm` | ~7900 / 9100 = **~87%** |

The matrix loaded for drawing is the modelview, camera view x joint world. Only a shared factor can
turn 4% into 87%, and that factor is the camera.

### What the camera probe found

A probe after `C_MTXLookAt` in `HSD_CObjSetupViewingMtx` (cobj.c) reports its inputs and output.
Evidence: `.omo/evidence/user-cobj-nan-inputs.log`.

```
cobj BAD eye=(-0.343, 27553183029345865826427879204847616.000, -0.000)
         up=(-0.021,-0.000,0.000)
         interest=(0.000,-nan,-3384079.500)
cobj BAD interest=(-29868203436192308749490308393214148608.000, 366838944113366031945514876928.000, ...)
```

`nan_inputs` is regularly non-zero while `nan_viewmtx` is often zero, so **`C_MTXLookAt` is not the
problem -- it is being fed garbage and faithfully producing garbage.** A degenerate-LookAt theory
(eye == interest, or up parallel to the view direction) was considered and is not what is happening.

Two distinct failure modes appear:

1. **Per-component corruption.** `eye.x = -0.343` is plausible while `eye.y = 2.7e34` is not, inside
   the same `Vec3`, and `up` is often entirely sane. Field-level, not a wild pointer -- a wild
   pointer corrupts uniformly. Magnitudes of 1e34/1e37 are the signature of misread floats, which is
   this port's recurring bug class (see the big-endian rule in `_research/port-dev-quickref.md` and
   the fixes in 9.1-9.3).
2. **Entirely zeroed cameras.** Some calls show `eye`, `up` and `interest` all `0.000` with a
   zeroed view matrix. A zero `up` and zero direction genuinely *is* degenerate for LookAt, so that
   one is uninitialised camera data rather than misread data.

### Next step

Find who writes `cobj->eyepos` and `cobj->interest` -- Melee's camera code, likely reading player or
bone positions -- and determine whether those sources are misread (endianness/offset/stride) or
genuinely uninitialised. Note the ~4% of joint matrices that are NaN *before* the camera is involved
is a second, smaller fault that will still need fixing after the camera is fixed.

## 9.12 Separate reproducible crash: itspawn.c

Independent of the black screen, and reproducible: a match crashes after roughly 20-25 seconds with

```
FATAL ACCESS_VIOLATION (0xC0000005) read of 0x00000000
_bisectValue+0x27   [src_melee_it_itspawn.c.obj]
```

Item spawning dereferences NULL. Seen twice at the identical address, with the diagnostics both
present and absent, so it is not an artefact of the instrumentation. Evidence:
`.omo/evidence/user-cobj-nan-inputs.log` and `.omo/evidence/agent-vertexcache-fix-run1.log`.
Reproducible bugs are cheap to fix; worth picking up once the renderer is unblocked.

## 9.13 Item-spawn crash fixed, and the camera traced one link further

### FIXED: the itspawn.c crash (commit `9b4e8d79e`)

The 9.12 crash is resolved. `HSD_MemAlloc` returns NULL for `size <= 0` (memory.c:18), so a pick
table built with a count of zero has NULL `x4`/`xC` as well as `size` 0. `bisectValue` is then
called as `(val, table, 0, 0)`, its base case `lo == hi - 1` is `0 == -1` and therefore false, so it
computes `mid = 0` and dereferences `xC[0]` at once. On a GameCube address 0 is mapped and readable,
so that returned garbage without faulting; under the port NULL is unmapped and it traps. **Same
class as the console invariants in 7.4** -- game code relying on low memory being readable.

Guarded at the two call sites (`it_8026C75C` in itspawn.c, and itdrop.c:151) rather than inside
`it_8026C65C`. Returning a sentinel kind from that function would flow into `spawn.kind` and index
the item tables -- a quieter and worse bug -- whereas both call sites already have a "nothing to
spawn" return (`-1` and `NULL`).

Verified: 1800 frames of a match with no fault, well past where two earlier runs died at the same
address. Evidence: `.omo/evidence/user-itemfix-gamecam-pause-ab.log`.

### The camera is a courier, not the culprit

A probe inside `Camera_8002AF68` -- the `CAMERA_STANDARD` path a normal match uses, so it reports
only the main game camera rather than all ~90 cobjs -- finds its source data already corrupt:

```
gamecam BAD interest=(16974681736908535496704.000, 2779265138848526907218464069386240.000, 0.000)
            position=(8339487532777472.000, -0.000, nan)
            translation=(0.000, 0.000, 0.000)
```

`game_camera`'s transform is garbage **before** the camera code touches it. `translation` is clean,
so the corruption is specifically in `transform->interest` and `transform->position`.

**Read the printed values, not the counters.** The `bad_*` counts flag only NaN and infinity, so
finite garbage like `1.7e22` passes as "good". The true corruption rate is higher than
`bad_position=2..4 of 60` suggests, and that mix of NaN with absurd-but-finite values is exactly
what produces `maxabs=9936` on surviving matrices alongside 86% outright NaN.

### Pausing takes a different camera branch -- a useful accident

While paused the `gamecam` lines disappear entirely: `game_camera.mode` becomes `CAMERA_PAUSE`,
which is a different branch of the switch and never calls `Camera_8002AF68`. That branch reads
**the same** `transform->position`/`interest` fields and produces clean matrices
(`nan/inf=0`, `maxabs=403.130`, `rowlen=[0.5250..1.1500]`, `depth grid distinct=8`).

So the transform is not permanently corrupt in memory, and this is **not** a struct-layout or
storage problem: the running camera update rewrites it with garbage every frame, and pausing simply
stops that update.

### The chain, and the one unknown left

```
???  ->  game_camera.transform (NaN + 1e33 magnitudes)  ->  view matrix
     ->  ~87% NaN modelview  ->  NaN vertices  ->  zero fragments  ->  black screen
```

Only the first link remains. Next probe goes on whatever writes `game_camera.transform` -- Melee's
per-frame camera tracking, which follows player positions. Since ~4% of joint matrices are NaN
*before* the camera is involved (9.11), one upstream fault in character position data would explain
both, and a single root cause is the outcome to bet on.

## 9.14 The NaN view matrix is STICKY -- this reconciles the numbers

The piece that makes the whole picture consistent, and the least obvious thing found all session.

### Read the counters correctly

The DIAG counters accumulate over the 30 frames between samples, **not per frame**. Dividing by 30:

| probe | per frame | NaN rate |
| --- | --- | --- |
| `gamecam` (Camera_8002AF68) | 2 calls | bad on roughly **1 frame in 15** |
| `posmtx` (GXLoadPosMtxImm) | ~25 loads | **87%, every frame** |
| `jobj` (JObjSetupMatrixSub) | ~215 setups | **3%** |

Two things follow. First, only ~25 of ~215 joint matrices are ever loaded for drawing, so the loaded
set is a small subset and the populations are not comparable. Second, and more importantly, an
**intermittently** bad camera cannot explain a **constant** 87% -- unless the damage persists.

### It persists

`HSD_CObjSetupViewingMtx` (cobj.c:469) only recomputes when `HSD_CObjMtxIsDirty(cobj)`. Once
`C_MTXLookAt` writes a NaN view matrix, **nothing cleans it**; it is reused every frame until
something marks the camera dirty with good inputs. And `ftparts.c` builds what actually gets loaded
as `PSMTXConcat(vmtx, pobj->u.jobj->mtx, tmp)` -- view x joint -- so a NaN view poisons every model
matrix regardless of how healthy the joints are.

So: **rare corruption, permanent consequence.** One bad frame in fifteen is more than enough. This
is why an earlier reading of "the camera is only occasionally bad, so it cannot be the cause" was
wrong; the cause is intermittent but the effect is sticky.

It also explains pausing precisely: `CAMERA_PAUSE` is a different branch that recomputes the view
matrix from frozen, clean values, so the scene returns.

### Still unknown

What writes garbage into `game_camera.transform` on those occasional frames. A probe was placed at
camera.c:2578 (`get_subject_x1C` / `target_interest`) and **never fired**, so that branch is not
used in this configuration -- do not re-probe it. The camera tuning constants are known good
(`cm_803BCCA0.x64 = 0.05`, `x6C = 29`, `x70 = 0.1`, `x3C = 0.15`), so the smoothing coefficient is
not the problem, and static float data reads correctly -- an earlier byte-swap theory is dead.

**Next instrument:** rather than guessing which branch is active, catch the *transition*. Log
whenever `game_camera.transform.interest`/`position` go from good to bad, printing old and new
values. That names the moment of corruption without needing to know the code path.

### Reproduction

All measurements from 9.9 onward used the same scene: **P1 (one character) vs CPU, Yoshi's Story**,
driven by the user. Keep to it -- the numbers above are comparable across runs only because the
scene never varied.

## 9.15 BLACK SCREEN FIXED -- and what is left

### The fix (commit `cae69e085`)

`Camera_ApplyQuake` (camera.c:943) casts `&cm_803BCB18` to a struct spanning **four separate
statics** -- callbacks, interest, eyepos, desc -- valid only because the original `.data` laid them
out contiguously at `0x3BCB18, +0x24, +0x14, +0x14`. The port links every global separately, so
`data->desc` landed in unrelated memory and read as zeros. Then:

```
aspect * (half_view_height / (0.5f * (xmax - xmin)))
  = 0 * (62.9 / 0) = 0 * inf = NaN          <- 0xFFC00000, the -nan(ind) seen everywhere
```

That NaN reaches `game_camera.translation.x/y`, which `Camera_8002AF68` adds into the camera's
interest and eye position -- **x and y only, which is why z stayed valid all the way down the
chain**. `C_MTXLookAt` turns those into a NaN view matrix; `HSD_CObjSetupViewingMtx` only recomputes
when dirty, so it sticks; every model matrix is view x joint, so ~87% of matrices reaching the GPU
were NaN, every vertex failed its clip test, nothing rasterised.

Verified in a live unpaused match: viewport `[0..640]x[0..480]`, aspect `1.21733`, posmtx
`nan/inf=0` (was 7836), maxabs `414.973` (was 9936), depth grid `distinct=8` (was 1). Evidence:
`.omo/evidence/user-BLACKSCREEN-FIXED.log`.

### Two more fixes from the same session

- **`9b4e8d79e`** -- itspawn.c: `HSD_MemAlloc` returns NULL for `size <= 0`, so an empty pick table
  has NULL `x4`/`xC`, and `bisectValue(val, table, 0, 0)` cannot match its base case (`0 == -1`) and
  dereferences `xC[0]`. Readable at address 0 on a GameCube, a trap here. Verified fixed.
- **`da88071cb`** -- gm_1798.c: `ResultsDisplayLayout` cast over `&lbl_8046E1B0` runs past it into
  `lbl_8046E38C`, `lbl_8046E39C` and `lbl_8046E3AC`. 40 of 48 field accesses were reading unrelated
  memory. **Untested** -- it is the results screen, which the current test loop never reaches.

### STILL BROKEN: geometry corruption (separate bug)

Survived the camera fix, so it was never the same problem. The symptom localises it precisely:
playing Mario, **the head renders correctly, the torso is wrong, and the legs spaghettify into
spiky balls** -- corruption scaling with depth through the envelope list.

`SetupEnvelopeModelMtx` (pobj.c:1125) has exactly that split: a single weight-1 joint is used as-is
(the head), while multi-joint parts accumulate `mtx += joint_mtx * weight` over the envelope list
(the limbs).

**Ruled out by measurement, not by reading -- do not redo these:**

- Per-vertex matrix indices are valid: `DIAGBOX pnmtx bad=0` on every draw, raw values `0..27`,
  every one a multiple of 3 and inside the 10 slots the game loads.
- Vertex indices stay within the uploaded extent (`outside=0`), and referenced positions have sane
  bounding boxes (a character part measures about `x[-8.7..8.7] y[0..4.7]`).
- `HSD_MtxScaledAdd` (mtx.c:437) computes the blend correctly.
- `calc_vtx_size` and `populate_pipeline_config` agree on vertex stride; `PNMTXIDX` is counted as
  1 byte in both.
- Forcing a fresh vertex-array upload at every draw made corruption **worse**, so a stale
  within-frame snapshot is not the cause (it was reverted).

**Envelope weights: RULED OUT (measured 2026-09-13 ~02:40).** The probe reports
`envelope: blends=7200 bad_weight_sum=0` every frame in a live match -- 7200 blends per frame, not
one with a weight sum outside 1.0 +/- 0.01. Evidence: `.omo/evidence/user-envelope-weights-clean.log`.
So the blend inputs' weights are correct and the scaling theory below is dead; the row length of
0.525 has some other explanation. **Start from the next paragraph, not here.**

~~Live hypothesis:~~ the envelope *weights*. They are floats from the DAT file, and if the weights
for one matrix slot do not sum to 1.0 the blended transform is scaled wrong and the limb stretches.
Note `posmtx health rowlen=[0.5250..1.1000]` -- a row length near 0.5 is what a half-weighted blend
looks like. Commit `52b772d76` adds the probe: `envelope: blends=N bad_weight_sum=N` per frame, plus
the first few offenders. **Run it and read that line first.**

**So the next suspects, in order:**

1. **`jobj->envelopemtx`** -- allocated and `memcpy`'d from `joint->mtx` at jobj.c:659-660, then
   used as `MTXConcat(jp->mtx, jp->envelopemtx, tmp)`. It is the inverse bind matrix; if it is
   wrong or stale, every blended vertex is displaced by a joint-dependent amount, and error would
   compound down a limb exactly as observed. A `memcpy` preserves byte order, so this is not an
   endianness question -- check *when* it is captured relative to the joint's own matrix setup.
2. **`_HSD_mkEnvelopeModelNodeMtx`** (displayfunc.c:256) -- computes the `right` matrix applied
   after the blend, and calls `MTXInverse`, which is a plausible place to produce a degenerate
   result.
3. The weight-1 branch is known good (Mario's head), so **diff the two branches**: whatever the
   blended path does that the rigid path does not is where the fault must be.

Measure before fixing. Every theory this session that merely fit the symptoms was wrong; every one
confirmed by a number first was right.

### Method notes that mattered

- **Read game memory through `gw_rf32`, never natively.** Four probes read it natively and produced
  convincing byte-swap garbage that cost several cycles chasing a bug that did not exist. The
  quickref's first convention; it is there for a reason.
- **Print raw bits, not `%.3f`.** A byte-swapped denormal prints as `0.000` and reads as a clean
  zero. That masked the real NaN in `game_camera.translation` and briefly exonerated the true cause.
- **Hold pause state constant when comparing.** `CAMERA_PAUSE` is a different branch that never
  calls `Camera_ApplyQuake`, so pausing changes the code path, not just the data.
- **`GXPeekZ` gives an automated render check** with no visual judgement: `distinct=1` means nothing
  rasterised. That measurement is what finally made the hunt tractable.

### Reproduction

P1 (Mario) vs CPU on Yoshi's Story. All measurements from 9.9 onward use this scene.

## 10. The geometry corruption: found, and it was never the matrices

`344e22d04`. **Fixed and confirmed in play** (Fountain of Dreams, the stage with the most
reflections and particles, renders correctly).

### The bug

Aurora merges consecutive draws by folding the second into the previous draw command. A merged
draw never reaches `push_gx_draw`, so it keeps that draw's immediates -- including `arrayStart[]`,
whose storage was uploaded to cover only the **first** draw's maximum index:

```c
const u32 needed = max_index_for_attr(i, fmt, vertexData, vtxCount) * array.stride + ...;
if (array.cachedRange.size < needed) {
  array.cachedRange = gfx::push_storage(array.data, needed);
}
```

When the merged draw indexed further into an array, those vertices read past the end of the
uploaded snapshot. A few vertices landed on garbage while their neighbours stayed correct: spikes
through otherwise sound geometry. Characters suffered most because skinned meshes are split into
many small consecutive POBJs that merge readily; stage platforms showed occasional spikes for the
same reason. The fix refuses to merge when the incoming draw reaches past what was uploaded.

### Why it took so long to find

Everything measured healthy, because everything *was* healthy. The array contents, the indices,
the matrices, the vertex data and the primitive topology were all correct; only the GPU's uploaded
copy was short. Every CPU probe read live memory using that draw's own `needed`, so none of them
could see a truncation that existed solely in the upload.

`AURORA_ASSERT(needed <= array.size)` should have caught it. It cannot, because `gw_GXSetArray`
passes everything from the array base to the end of MEM1 as the nominal size, so the assert can
never fire. **This is still true and worth tightening** -- it is a live hole that hides exactly
this class of bug.

### Corrections to section 9

- **The three ranked suspects in 9.15 are all disproven.** `jobj->envelopemtx` is a flawless
  orthonormal rotation (rows *and* columns measured exactly 1.0); `MTXConcat` is faithful;
  `_HSD_mkEnvelopeModelNodeMtx` is fine. The whole matrix pipeline is exonerated by a decisive
  experiment: with envelope blending replaced by the single highest-weight joint, the image was
  **unchanged**. If skinning maths cannot alter the picture, skinning maths is not the bug.
- **`MELEE_REUPLOAD_ARRAYS` was dead code.** `gw_force_array_reupload()` was defined and never
  called. The earlier conclusion that "forcing re-upload made it worse" came from a switch that
  did nothing, and wrongly retired the array-upload hypothesis -- which was, in the end, the right
  neighbourhood. **Verify a toggle actually engages before trusting a negative result from it.**
  Both diagnostic toggles added this session log a line on activation for this reason.
- **The `0.0463333` row collapse was a red herring.** Those joints genuinely have
  `scale = (1.1, 0.046, 1.1)` with rotation `(0, +/-pi/2, 0)` -- deliberately flattened model data,
  and only ~3% of slots, far too few to explain whole limbs.
- **An instrumentation bug produced a false result mid-session.** A mutation detector hashed
  `min(needed, 2048)` bytes while `needed` varied per draw, so differing lengths read as changed
  contents and it reported "35% of draws mutate". With a fixed 256-byte window: **zero** mutations
  in 320,000 checks. Vertex arrays do not change in-frame.

### Diagnostic left in place

`MELEE_NO_MERGE=1` disables draw merging entirely (`_build/run_nomerge.bat`). If geometry
corruption ever reappears, that toggle is the fastest way to confirm whether merging is involved.

### Incidental finding, unfixed

Joint matrices are stale. `rows pre=0/8060 post=0/8060` every frame -- no joint matrix is *made*
collapsed -- while the blend reads ~200 collapsed matrices per frame. Those were written during a
single burst frame and never recomputed, because `HSD_JObjSetupMatrix` is dirty-gated. Same
sticky-state class as the NaN view matrix in section 9. Benign for rendering as far as we know;
recorded because it is real.

## 11. Raw GameCube adapter input

`f404c5f8e`. **Working**: mapping correct, lag gone, calibration usable.

`pc/platform/gc_adapter.c` reads the WUP-028 adapter's report bytes directly and builds `PADStatus`
the way the console does, bypassing SDL's mapping table, deadzones, axis rescaling and trigger
emulation. Aurora's SDL path remains the fallback when no adapter opens.

Three things were needed beyond the decode:

- **Claim the device before SDL.** `gw_PADInit` opens the adapter before `PADInit()`, and `main()`
  sets `SDL_JOYSTICK_HIDAPI_GAMECUBE=0` before Aurora starts. Whichever side gets the handle locks
  the other out; this was the cause of the first "not found on WinUSB" failure even though the
  device was plainly there. `MELEE_SDL_GAMECUBE=1` hands it back to SDL.
- **Read on its own thread.** A timeout-bounded USB read on the game thread stalls for the whole
  timeout whenever the adapter is idle -- up to 32 ms per frame with the original drain loop, which
  is what "really laggy" was. The reader thread parks in the blocking read; the frame only copies
  the newest packet under a lock.
- **Calibrate at runtime.** Resting stick and trigger positions are sampled on first read; triggers
  are rescaled so rest reads 0 and full press still reaches 255; any button held at that instant is
  masked as stuck. A trigger with no usable travel (worn, or fitted with plugs -- this controller
  has both) reports as never pressed rather than permanently held. **F9 re-runs calibration**;
  release everything first.

`MELEE_PAD_DIAG=1` enables adapter enumeration plus raw report dumps (`DIAG gcraw`), which is how
any remaining mapping question should be settled -- against the actual report bytes, not by
guessing.

Build note: `gc_adapter.c` needs `hid.lib`, `winusb.lib` and `setupapi.lib`. The link response
files are **hand-maintained, not generated** -- a new shim must be added to
`_build/melee_link_objects.rsp` and any new import library to `_build/melee_link_libs.rsp`.
Note also that `main.c` needs the SDL3 include path
(`-I C:/gdm/_build/ax86/_deps/sdl3_prebuilt-src/include`), which the generic shim build line in the
quickref omits.

## 12. Open items

1. **Frame pacing is not smooth compared to Dolphin.** No profiler exists yet; cause unknown.
   Candidates worth separating before guessing: present/vsync pacing (section 5's present-timing
   lead), per-frame GPU cost, the FIFO processing cost per frame, and stalls from un-merged draws
   introduced by `344e22d04`. Needs measurement first -- a frame-time histogram distinguishes a
   uniformly slow frame from occasional long spikes, and those have entirely different causes.
2. **SFX bank crash on stage load.** `synth.c:165`,
   `hsd_SynthSFXBankHead[bankID + 1] - hsd_SynthSFXBank[bankID] >= hsd_SynthSFXLoadBuf[1]`.
   Reproducible after several stage loads, not on the first. ARAM is healthy (allocations succeed,
   9 MB free) and the sibling "bank overflow" assert at 0x158 never fires, so the region is
   allocated correctly. `hsd_SynthSFXBank[bankID]` is a write cursor that grows on every SFX load
   (`synth.c:135`) and is only rewound by the unload path (`synth.c:315`). That unload walks a list
   of `AXVPB` voices, and this port has no audio backend. **Hypothesis: the unload never runs
   between stage loads and the cursor creeps until the next load does not fit.** Cheap test: log
   `hsd_SynthSFXBank[2]` and `hsd_SynthSFXBankHead[3]` across several stage loads; if the cursor
   only ever climbs, confirmed.
3. **Memory card -- not started, mostly wiring.** Aurora ships a complete kabufuda-based
   implementation (`extern/aurora/lib/card/`, full `CARD*` API, `CARD_RAWIMAGE` and
   `CARD_GCIFOLDER` modes) that this build disables with `-DAURORA_ENABLE_CARD=OFF`. `shim_card.c`
   already stubs **every** CARD entry the game calls, so the surface is known. Work: enable the
   CMake option, link `aurora_card`, and marshal `CARDFileInfo`/`CARDStat` across the endianness
   boundary (Aurora writes them natively, the game reads them big-endian). Aurora's async calls
   invoke the callback synchronously, which satisfies the constraint `shim_card.c` was written
   around (see its header comment).
4. **Resize corrupts stage textures.** Resizing the window paints stretched black across parts of
   the stage. `gpu.cpp:1098` clears the EFB copy-texture cache on any size change; Melee copies
   some stage textures out of the framebuffer once and samples them for the rest of the match, so
   once discarded they are never regenerated. Predicts the damage is permanent until the stage
   reloads. Unverified.
5. **Load-time jank.** Brief hitching at the start of a stage load, resolved before control is
   handed over. Plausibly the first frames uploading arrays un-merged before caches warm. Cosmetic.
6. **`gw_GXSetArray` nominal size.** Passing "base to end of MEM1" defeats Aurora's out-of-range
   assert entirely. Tighten it to the array's real extent so the next bug of this class is caught
   rather than silent.
7. **Latent, unchanged:** `resolveIKJoint1` uses `var_f27`/`var_f28` uninitialised when the
   `temp_f31 > var_f5` branch is not taken (jobj.c, decomp `@todo`). Real UB, but the values only
   pick a sign on a vector that is zero in that branch, so it appears benign. Not the cause of
   anything found so far.

### Method note from this session

The one experiment that broke the deadlock removed a whole subsystem from the picture rather than
inspecting it: replacing the envelope blend with a single joint proved in one run that matrices
could not be the cause, after hours of measuring matrices that were all correct. When every
component measures healthy, stop measuring components and start disabling them.

---

# 13. Session update, 2026-09-13 ~12:00 PDT — vsync, memory cards, audio, input

Four workstreams landed and were verified with automated runs (the port now has a scripted pad
source, so most of this was self-tested without the user). All changes are uncommitted on
`melee` `pc-port`.

## 13.1 Vsync / frame pacing — FIXED

Symptom: bimodal frame times (p50 ≈ 15.6 ms, ~1 frame in 13 at ≈ 30.6 ms) = judder.

Root cause (Oracle diagnosis, confirmed by measurement): nothing held the game to 60 Hz.
`gw_VIWaitForRetrace`/`gw_frame_tick` never block — `aurora_end_frame` only enqueues to the render
worker, and the display is 144 Hz VRR, so `Fifo` Present gives no back-pressure. The game
free-ran at its own ~15.6 ms frame cost and the soft 1/60 pad alarm inserted one full stall every
~13 frames.

Fix: a hard field boundary in `shim_vi.c` (`gw_pace_field`), measured from the previous tick, with
catch-up, called before `aurora_end_frame`. Verified in a live match: `p50=16.67 p95=17.11`,
histogram `180/180` in `[16,17.5]`, zero spikes (was ~15 frames per window at 30–34 ms).

## 13.2 Memory cards — FIXED (two root-cause bugs)

Cards were brought up this session (`AURORA_ENABLE_CARD=ON`, `aurora_card.lib` linked,
`shim_card.c` marshalling, `lbcardnew.c` `wait_idle` pumps). Two bugs then blocked save creation:

1. **`.bss` contiguity (the §9.3 class).** The HSD card code casts `hsd_804D1138` to one
   contiguous `CardContext` (0x1510 bytes), but the port links its three original pieces
   (`hsd_804D1138[0x10]`, `hsd_804D1148[0x1200]`, `hsd_804D2348[0x300]`) as separate globals, so
   the command engine and its producers used different memory. Fix: size `hsd_804D1138` to the
   whole context and alias `hsd_804D1148`/`hsd_804D2348` into it (`hsd_3A94.c`, `hsd_3A94.h`,
   `hsd_4D11.c`, TARGET_PC-guarded).
2. **Charset overflow.** `lb_8001C658` (`lbcardgame.c`) `sprintf`s the save name into
   `_p(_1C)[0x40]`, which sits immediately before `_p(x5C)`. The Japanese literal is 46 bytes in
   the original Shift-JIS execution charset but **65 in UTF-8**, so it overflowed into `x5C` and
   the next `_p(x5C)[...]` faulted reading date digits (`read of 0x32303039`). Fix: format into a
   scratch buffer and cap the copy at `sizeof(_1C)` (TARGET_PC-guarded).

Also fixed in Aurora's `CardGciFolder`: `openFile` returned `NOCARD (-3)` for a missing save
instead of `NOFILE (-4)` (the game read that as "no card inserted"), the two `deleteFile` stubs
(later implemented), and `renameFile` now persists.

Verified: `Mount/Check/FreeBlocks/Open -> -4/Create -> 0`, then **11 × `WriteAsync(8192)` covering
all 90,112 bytes**; a restart shows `Open -> 0`, `GetStatus` enumeration and a full read,
40 s / `retrace=2402`, `FATAL=0`. Save lands at `_build/card/USA/Card A/*.gci`.

## 13.3 Audio — IMPLEMENTED (audible)

Aurora has no audio; the game's AX/AI surface (35 AX + 4 AI imports, zero DSP) was fully inert.
A backend was implemented entirely in the shims (no game-source changes):

- **`shim_ax.c` (rewritten) + `shim_ax.h` (new):** DSP-ADPCM decode (8-byte frames → 14 samples),
  64-voice mixer reading `AXPB` config from big-endian game memory, `ve` volume+delta, `AXPBMIX`
  L/R pan, `AXPBSRC` ratio resampling (nearest-neighbour for now), write-back of `pb.state`
  (0x146) and `pb.addr.currentAddress` (0x1B2) big-endian. DSP space = ARAM byte offset ×2 →
  `gw_aram + d/2`.
- **Output:** SDL3 `SDL_OpenAudioDeviceStream`, 32 kHz stereo s16; a lock-free SPSC ring buffer
  between the game thread and SDL's callback (the callback only copies).
- **Frame driver:** `gw_AXRegisterCallback` stores `HSD_SynthCallback`; `gw_ax_frame_tick`
  (called once from `gw_frame_tick`) invokes it per 5 ms sub-frame (160 samples) and mixes.
- **`shim_misc.c`:** the four AI entry points now track master volume / sample rate.

Verified: `AX: audio device open (32 kHz stereo s16)`, `first audible frame, 2 active voice(s),
peak=3198`, sustained `peak=12000–21000` for the whole run (menu music `.hps` stream + SFX),
no crash. FX (reverb/chorus/delay) remains stubbed returning 1 (aux buses only).

## 13.4 Input — programmatic + keyboard fix

- **`MELEE_PAD_SCRIPT=<file>`** (`shim_pad.c`): a text script — one segment per line,
  `<frames> <buttons_hex> [stickX stickY [trigL trigR]]` — drives channel 0 regardless of the
  physical adapter. This is the automated self-test path used above
  (`_build/pad_card_test.txt` + `_build/self_test_keys.ps1`).
- **Keyboard overlay fix:** it was gated on `!gw_gc_adapter_present()`, so with a GameCube adapter
  connected every key was ignored. The gate is removed; the keyboard now works alongside the
  adapter (W/A/S/D, J=A, K=B, Enter=Start; F9 recalibrates).

## 13.5 Test tooling added

- `shim_pad.c` `MELEE_PAD_SCRIPT` (above).
- `main.c` `MELEE_AURORA_VERBOSE=1` now logs Aurora INFO (present mode, adapter) — that is how the
  `Fifo` + 144 Hz VRR picture was established.
- `gw_runtime.c` crash handler gained a raw **stack scan** (image-range words from `esp`); the
  frame-pointer walk cannot unwind `-O2` frames.
- TEMP probes left in place (remove before the final commit): `diag_aobj_bad`, `diag_card_state`,
  `diag_card_pending`, `diag_card_dequeue`, `diag_card_read`, `diag_card_engine`,
  `diag_card_engine_read` (all `diag_*` shims live in `shim_gx.c`).

## 13.6 Remaining / not done

1. **Card `delete`/`rename`** were implemented in `CardGciFolder` but not exercised in-game.
2. **Audio FX** (reverb/chorus/delay) still return 1; **resampling** is nearest-neighbour.
3. **`HSD_AObjSetFlags` crash** (the 0x6 pointer) appeared twice before the pacing fix and did
   **not** recur under correct pacing across ~3 min of attract + matches; instrumented
   (`diag_aobj_bad`) but not root-caused.
4. The user reported an error "from loading a replay" that could not be reproduced or located (no
   replay feature exists in the code); likely the card crash above.
5. **Save-description date is garbage** (cosmetic). The created save's description reads
   `Super Smash Bros. Melee         Game Data -821624832/184549377/`, i.e. `time.year`/`time.mon`
   are huge. The shim's own `gw_OSTicksToCalendarTime` is correct when called
   (`gw: DIAG CALTIME ticks=121500000 year=1999 mon=11 day=31` = the GC epoch), and `lb_8001C658`'s
   create-time call is *not* among those logged calls — so that path reaches the SDK's
   `OSTicksToCalendarTime`/`OSGetTime` without going through the shim. Investigate the
   game-TU-vs-SDK symbol resolution for `OSTicksToCalendarTime`/`OSSecondsToTicks`/`OSTicksToSeconds`
   (`extern/dolphin/src/dolphin/os/OSTime.c`). The date is only used in the save name, so this does
   not affect the save itself.
6. Everything is **uncommitted**; commit once the user signs off.

# 14. Session update, 2026-09-13 (later) — attract-mode crash sweep

Committed (9 on `pc-port`, so the "uncommitted" note above is now stale): `0e76d563e`,
`650881218`, `fce9ef81a`, `ec397772a`, `d66c2c531`, `640dcee41`, `01e62e6cd`, `fa15afd5e`,
`de697938a`. Attract mode went from a FATAL at ~10 s to ~58 s with audio playing.

## 14.1 What was crashing, and why
- **SFX playback (`HSD_SynthSFXPlayWithGroup`, ~10 s, deterministic).** `HSD_SynthSFXBankDeflag`
  writes `HSD_Synth_804C2AE0[bank_id + 0x80/4]`, but the array was declared `[0x80/4]`, so the
  write landed one array past its end — on `HSD_Synth_804C29E0`'s bucket heads (adjacent in
  `.bss`) — storing a native deflag offset where a game pointer belongs. Fixed by declaring
  `[0x100/4]`.
- **SFX bank overflow.** Nothing rewound `hsd_SynthSFXBank[bankID]` between loads, so a later load
  stopped fitting and the overflow assert ended the game. Re-applied the reclaim (safe now that
  the unload's bucket unlink works).
- **Stream advance (`HSD_Synth_8038ADD0`, ~58 s).** `pos` is the stream-ring buffer index used to
  address `lbl_804C4540[3]`, derived from the voice's current address at `+0x1B2` — 0 until the
  stream is set up — so the unsigned difference wraps to `0x7FFF` and the read runs far past the
  array. Bounded `pos`. NOTE: the earlier "node `voice[0]` corruption" diagnosis was WRONG; the
  voice pointer was valid and the fault was this index.
- **Kirby hat NULL derefs.** `ft_80459B88.hats[kind]` is NULL on the attract path; sites are
  guarded individually but the root is 14.3.
- **AObj garbage DObj.** `grAnime` hands the AObj setters a DObj whose `aobj` is a small integer;
  guarded `SetFlags`/`SetRewindFrame`/`SetEndFrame`.

## 14.2 Endianness — the system already exists (do not build another)
Game TUs compile for PowerPC, then pass through `_build/gwtool/gwtool.exe`, which byte-swaps every
memory access; shims are native x86 and must swap by hand (`gw.h`). Policy + inventory are in
`_research/port-dev-quickref.md`.

## 14.3 FIXED: the Kirby hat preload (root of the remaining crashes)
`ftLib_80087610` loads each hat archive into `((HSD_Archive**)&ft_80459B88)[kind]` via
`ftKb_SpecialN_800EED50(Player_800325C8(i, 0), arg0)`, but its only caller is the VS-match setup
`gm_8017C838`, whose Kirby branch the attract path never reaches — confirmed empirically: a run
with a probe in `ftLib_80087610` logged **zero** calls. The hats therefore stayed all-NULL and the
first Kirby demo NULL-derefed in any of the ~33 `ft_80459B88.hats` consumers (seen in
`ftKb_SpecialN_800F03DC`, `ftCo_8009D4D4`, `ftCo_8009D074`). Fix (`d2a716caa`, `62a7d21f1`): call
`ftLib_80087610(0)` once from `Player_80031D2C` before any fighter is set up, and under TARGET_PC
load **every** valid kind — not just `gm_IsCKindUnlocked` ones, since attract demos include locked
characters like Koopa — with an exclusive `SELKIND_COUNT` bound. Verified: a full 300 s attract run
ends with **0 FATAL** (the timeout stops it, not a crash).

## 14.4 Tooling added
`gw_watch_page` / `gw_watch_tick` (`gw_runtime.c`, `gw.h`) — a `PAGE_GUARD` write watchdog that
logs the faulting instruction and address of accesses to a region, re-armed once per frame from
`gw_frame_tick`. Used to rule out a rogue writer into the audio node array.

# 15. Semantic audit (bug-class sweeps) — findings and fixes

Four parallel class-based audits over `melee/src` + `pc/platform`: (a) declared array size vs index
range, (b) unbounded computed indices, (c) loader-set pointer deref'd before/without a NULL check,
(d) shim↔game endianness boundary violations. Commits: `2586eccbc`, `bdcace0ab`, `eb1f568c6`.

## 15.1 Fixed
- **`shim_ax.c` AXVPB endianness siblings** (`2586eccbc`). `AXVPB.callback` and `AXVPB.userContext`
  were native while the game reads/writes both big-endian (`synth.c:420,425,441,453,456`) — the same
  miss already fixed for `priority`. Now `gw_wptr`/`gw_w32` stores + `gw_rptr` read.
- **`axdriver.c` use-after-free** (`2586eccbc`). `AXDriver_8038DCFC` freed `AXDriver_804D7798` but
  left the bank/sample tables `B0/B4/B8/BC` pointing into it; a free→reload→play with an early
  reload return dereferenced freed memory. Now cleared.
- **Every remaining raw `ft_80459B88.hats[...]` deref** (`bdcace0ab`). ~30 sites across
  `ftdynamics.c` + `ftkirbyspecial*`; guarded via the `ftCo_8009D4D4` template / `ftKb_hatTable`.
- **`efLib_Create` unloaded EF bank** (`eb1f568c6`). `efAsync_DatEntries[gfx_id/1000].data` is NULL
  until `efAsync_OnLoad`; now bounded + NULL-checked (also fixes the previously-unbounded bank
  index against the 51-entry table). This was the crash the hat guards had been masking.

**Verified:** a full 300 s attract run ends with **0 FATAL** (timeout, not a crash), retrace 17160,
audio playing. Evidence in `.omo/evidence/` (`audit-fix1.log`, `hatguard.log`, `eflib-fix-300s.log`).

## 15.2 Not yet fixed (lower confidence / needs per-site verification)
- `particle.c:1586` `hsd_804D08E8[*pc++ + pp->pJObjOfs]` (8-entry table) and `:1648`.
- `gmtoulib.c:2349` `lbl_80473AB8[i + 1]` where `i` can reach 64 (array is 64).
- `ftKb_SpecialN_800F16D0` (`ftkirby.c`) still derefs `g->hats[...]` / `g->x0->xC` raw (~19 sites,
  different syntactic form from the guarded ones).
- `shim_os.c` `gw_OSTicksToCalendarTime` forwards a game buffer to Aurora's native writer;
  `shim_pad.c`/Aurora `PADRead` writes `button`/`extButton` native (masked today by the GC-adapter
  path rewriting ch0 via `gw_w16`).
- `texp.c` `a_in[cnst->reg-4]`, `tobj.c` `imagetbl[...]`, `psdisp.c` palettes — signed/derived indices.

## 15.3 False positive
- Array-size audit's `table[...]` hit was a cross-file name collision, not an OOB. No definite new
  declaration/index mismatch remains (the canonical `synth.c` spot is already patched).

# 16. Directory-depth audit (ft/gr/gm) and the GC-layout alias-view class

After §15, three directory-depth agents swept `src/melee/{ft,gr,gm}` for classes §15 did NOT cover:
lifetime/ownership, state-machine sequencing, mode-gated init, and id-indexed function-pointer
tables. `ft` and `gr` reported; `gm` surfaced the biggest systemic finding.

## 16.1 THE CLASS: "GC-layout alias views" (important)
Code casts a pointer and indexes/offsets past a global assuming the original GameCube's contiguous
symbol layout. On PC the globals are separate, non-adjacent symbols, so the view reads/writes
**unrelated memory**. Already fixed before this session: `gmmain.c`, `gm_1798.c` (results screen),
`gm_1832.c`. This session fixed `ftdata.c` `ft_800852B0` (commit `5cfe0e05c`). Still to fix (confirmed,
real, mechanical - reference the real symbol under TARGET_PC):
| Site | Alias view | Intended symbol |
|---|---|---|
| `gm/gmtoumode.c:198` | `(MatchExitInfo*)(src+1)` past `gm_804876D8` | `gm_80487810.match_end` |
| `gm/gmclassic.c:607,694` | `(gmClassicSceneData*)gm_Mode_Classic_States` | `gmClassic_803DDEC8` |
| `gm/gmtoulib.c:2431` | `(TmData*)&((BracketData*)lbl_80473AB8)->srcs[3]` | `gm_804771C4` |
| `gm/gm_180A.c:95,252,312` | `state->ec8[4]` past `lbl_80472E48` | `lbl_80472EC8` |
| `gm/gm_181A.c:693,924` | `record` past `lbl_80472ED8` | `lbl_80473594` |
| `gm/gmcameramode.c:231` | preload entries not registered on state 3 | unknown (ordering holds) |
Symptom is not only crashes: Classic's matchup table, and the Homerun/Multiman records, silently
read/write wrong memory. A project-wide sweep for this pattern is in progress (ft+lb, gr+gm+mn,
sysdolphin+rest).

## 16.2 Other audit fixes landed (commit `5cfe0e05c`)
- `grpstadium.c` `grStadium_801D4548`: free+null `xD0` (the UnkArchiveStruct) instead of `xCC` (the
  persistent .dat staging buffer) - Pokemon Stadium use-after-free.
- `ground.c` `Ground_801BFFB0`: zero `Ground_804D6950` (per-map collision flags) on stage load.
- `ground.c`: NULL-check `stage_datas[pair->grkind]` at the unguarded dispatch entries (entries 23,
  26 are NULL; entry 26 is reachable via `stage_id_map[21]` = Akaneia).
- `ftcommon.c` `ftCommon_8007E83C`: bounds+NULL check before `parasol_table_3[arg1]`.

## 16.4 Alias-view sweep results (the class is wide, not just gm)
Three read-only sweeps (ft+lb / gr+gm+mn / sysdolphin+rest) over the four classes outside §15.
Each fixes the same way as `51db9bfe9`: reference the real symbol via a TARGET_PC macro. Real =
proven cross-symbol; likely = cross-symbol by declaration but order-dependent.

| Site | Alias view (source symbol) | Real symbol |
|---|---|---|
| `ty/toy.c` ~16 sites (1086,1225,2591,2622,3106,3337,4048,4763,5505,5553,5782,5875,6402,6430,6637,6659) | `_Toy_804A26B8` (12B) as Toy/Toy26B8 (0x404) | `Toy_804A284C`, `Toy_804A2AA8` — real |
| `ty/toy.c` 1879,2048,2333/2314,2388 | `_Toy_str_TyLight_dat` (12B string) as data tables | `_Toy_803FDDE4/A0/BC/3C/A8` — real |
| `it/itspawn.c:341,342,344` | `(ItemPickTable*)(&it_804A0E30 + 1)` | `it_804A0E50` — real |
| `it/kinds/itlinkarrow.c:684,692` | `(f32*)&it_803F6A28 + x9C` | `it_803F6A84` — real (correct form already at :127/:135) |
| `if/soundtest.c:766` | `un_803F9F28` (string) as `un_803F9F28_t` (0x200) | `un_803F9FA4` — real |
| `if/soundtest.c:988,1101,1116,1134,1152` | `un_803FA128` (int[76]) as `un_803FA128_t` (0x228) | `un_803FA258` — likely |
| `pl/player.c:359,447,491,1297,2054` | 9B string as `Unk_Struct_w_Array` (`vec_arr` +0x20) | `ftMapping_list` — real |
| `ft/kinds/ftKirby/ftkirbyspeciallw.c:150,196,602,648,693,765,815,864` | `ftKb_Init_803CB490` (0x5C) `->vec` at +0x74 | `ftKb_Init_803CB4EC.vec` — real |
| `gm/gmtoulib.c:1721` | `(CObjData*)&lbl_803D9DAC` | `lbl_803D9DD0` — real |
| `gm/gm_19EF.c:137,141,563` | `&lbl_80479A98 + 0x28` as `HSD_JObj**` | `lbl_80479B10` — likely |
| `gm/gm_17EB.c:88,175` | `lbl_80472CB0` (u8[0x78]) as UnkAllstarData (0xA0) | `lbl_80472D28` — likely |
| `gr/grzebes.c:526,539` | `(grZe_BubbleSpawnPos*)grZe_8049F140` | through `grZe_8049F158` into `grZe_8049F170` — likely |
| `gr/grvenom.c:1028,1038,1051,1100,1120,1145,1153,1420` | `s32* base = &grVe_803E5348` (+0x170 etc) | `grVe_803E5530` — likely |
| `mn/mndiagram3.c:67,98,309,318,342` | `&mnDiagram3_803EEC10` (0xC) | `803EEC1C/28/4C` — real |
| `mn/mnname.c:832..994,1399-1411,1735-1740` | `mnName_803ED538[4]` (+0xC8..+0x4F8) | `mnName_803ED568/574/580/598/600/618`, `mnName_AutoName*/RefuseName*` — real |
| `mn/mnevent.c:727,728,770-772` | `&mnEvent_803EF740` (+0x70..+0x118) | `mnEvent_803EF7A0` — real |

Uncertain: `gr/grmutecity.c` `(grMc_CarState*)grMc_8049F440` (its `cars` lands on
`grMc_8049F4B8`); the gr sweep judged it a same-object Ground-union view — verify before fixing.

### 16.4a Fix pass (2026-09-14/15)
Fixed (all `TARGET_PC`-guarded, original kept under `#else`; every touched TU compiles, relink OK,
100 s off-screen smoke: **0 FATAL**, retrace 5400):
- **`ty/toy.c`** — all 16 `_Toy_804A26B8` views (`Toy`/`Toy26B8`/`u16*`/`s32*`/`u8*`) now go through
  `Toy_804A284C` (u16[302], covering the console range 0x194..0x3EF) and `Toy_804A2AA8`; the five
  `_Toy_str_TyLight_dat` table views reference the real `_Toy_803FDD**` data. Named `TOY_*` accessors.
- **`mn/mndiagram3.c`, `mn/mnname.c`, `mn/mnevent.c`** — rewritten against `mnDiagram3_803EEC1C/28/4C`,
  `mnName_803ED568/574/580/598/600/618` (+ the AutoName/RefuseName string symbols), `mnEvent_803EF7A0`.
- **`gr/grvenom.c`** — the `(s32*)&grVe_803E5348` spawn-table views now index `grVe_803E5530` (offset +0x1E8).
- **`if/soundtest.c`** — `un_803F9F28`→`un_803F9FA4` and `un_803FA128`→`un_803FA258`, both confirmed by
  offset math (the second was only "likely" before).
- **`gm/gmtoulib.c:1721`** — `lbl_803D9DD0`; **`it/itspawn.c`**, **`it/kinds/itlinkarrow.c`**,
  **`ft/kinds/ftKirby/ftkirbyspeciallw.c`** — verified already fixed in-tree.
- **`gr/grmutecity.c`** — verified: `grMc_8049F440` (s32[30], 0x78) and `grMc_8049F4B8` are separate
  globals and `cars` at +0x78 is a genuine cross-symbol alias; the existing fix is correct.

**False positives — verified against `config/GALE01/symbols.txt`; do NOT "fix" these:**
- `gm/gm_19EF.c:137,141,563` — `(u8*)&lbl_80479A98 + 0x28` indexed by i lands at 0x2C..0x50, inside the
  0x78-byte `lbl_80479A98` (its own `x28` jobj array). The sweep's "+0x78 = `lbl_80479B10`" assumed
  8-byte pointers; guest pointers are 4-byte, so it never leaves the struct.
- `gm/gm_17EB.c:88,175` — `(UnkAllstarData*)lbl_80472CB0` reads only within the 0x78 buffer. The real
  0xA0 `UnkAllstarData` is `gm_80473A18` (+0x168), **not** the sweep's `lbl_80472D28` (0x120 bytes of
  regclear/results *rendering* data). The accessor backs Classic mode; the name is a misnomer, not a bug.

**Newly found, same class, still unfixed (not in the original sweep):**
- `gr/grzebes.c:612` `(grZe_BubbleState*)grZe_8049F140` (reads `grZe_8049F170` / `grZe_8049F158`) and
  `:2326` `Vec3* base = grZe_8049F140` indexed `[2]`/`[3]`. `grZe_8049F140` is only 0x18 bytes.
- `gr/grvenom.c` other-symbol views: `base[xC8+14]` → `grVe_803E5380` (+0x38) at
  1433/1465/1479/1487/1523/1536/1626, and `base[idx0+0xD6]` → `grVe_803E56A0` (+0x358) at 1488/1524/1537.

# 18. Card CSS-return hang — FIXED and verified in-game
`lb_8001CDB4`'s spin (`while (_p(xC) || _p(x10)) lb_8001CC84()`) polled the card state without
issuing any shim call, so the port's deferred-completion queue never pumped and the CARD write
behind `hsd_803AAA48`'s busy flag never completed - returning from the results screen to the CSS
pinned forever with `MELEE_CARD=1`. Fixed by adding `wait_idle()` to the spin (same pattern as the
waits in `lbcardnew.c`). Verified in-game: Mario ditto on Yoshi's Story -> results -> back to CSS,
with the card enabled, completes cleanly.

# 19. Audio pass (2026-09-14) — mixer, aux effects, output pacing

A broad pass over the audio path after the user reported it "still not perfect, lots of issues".
Everything is in `pc/platform/shim_ax.c` (rewritten) plus window-placement support in `main.c`; no
game-source changes.

## 19.1 The stream tick: a `>=` where the hardware uses an exact match (the audible one)

`HSD_Synth_8038ADD0` (synth.c:1289) plays the `.hps` stream out of a three-block ARAM ring. It only
moves `pb.addr.endAddress` onto a block **after** it has seen the voice's current address arrive
there, while `loopAddress` already points at the *next* block. So for up to one AX frame after every
block transition the end address sits a whole block *behind* the cursor.

The shim tested `cur_addr >= end_addr`, so during that window the test fired on **every sample**:
the voice re-looped once per sample for up to 5 ms. Blocks are ~3.6 s and two transitions in three
go forwards, so music produced a tick roughly every 3.6 s. Fixed by testing an exact match with a
one-ADPCM-frame (16-nibble) tolerance (`gw_ax_at_end`), which is what the hardware decoder does and
why the game's scheme works at all. The same test now also covers the PCM16/PCM8 formats.

## 19.2 Output pacing: no cushion at all

`gw_ax_frame_tick` generated sub-frames from the wall clock, so production averaged exactly real
time with **zero** latency cushion in front of the SDL callback. Any frame jitter emptied the ring
and the callback padded silence — a continuous crackle — and nothing primed the buffer at startup.

Generation is now driven by the ring's fill level, i.e. by the audio device clock, which is the
clock the DSP's 5 ms interrupt runs on; it self-corrects against every source of drift. Measured
over the same scripted 60 s menu run:

| target cushion | underruns |
|---|---|
| 35 ms | 321, still climbing in steady state |
| 60 ms (new default) | 14, all during boot; **flat zero** thereafter |

Tunable with `MELEE_AUDIO_LATENCY_MS`. The remaining boot/scene-load underruns are the game thread
blocking in synchronous DVD/ARQ reads for longer than any buffer covers, not a mixer problem.
Without a device the wall clock still drives the synth callback, so the game's audio state machine
keeps running either way. The ring also gained proper release/acquire barriers — `volatile` alone
does not order the `memcpy` against the cursor store.

## 19.3 The aux buses were being thrown away

`AXPBMIX.vAuxA*`/`vAuxB*` were never read, so every voice's reverb and echo send was dropped. Melee
sends heavily to both (`HSD_SynthSFXUpdateMix`, synth.c:1091-1113), which cost both the effects
themselves and a chunk of the level balance.

Both buses are now real, laid out exactly like the DSP's (`AXAux.c`: L/R/S contiguous, 160 samples
each), and the AXFX processors are implemented natively:

- **AUX A = AXFX reverb (std)** — a faithful C port of `reverb_std.c` `HandleReverb`: two feedback
  combs into two Schroeder all-passes with a one-pole damping filter between them, per channel,
  plus the pre-delay line (including its wrap-one-element-early quirk, which sets the real
  pre-delay length).
- **AUX B = AXFX delay** — `delay.c` `AXFXDelayCallback`.

The SDK's own sources are in `extern/dolphin/src/dolphin/axfx/` but **cannot** be built through the
gwtool pipeline: their inner loops are MWERKS `asm` blocks, which clang's PowerPC front end will
not accept. Hence the native reimplementation. Parameters are read out of the game-memory `AXFX_*`
struct, and the log confirms the game's own settings arrive intact:
`reverb-std (col=0.500 time=1.880 mix=1.000 damp=0.640 pre=0.0020)` and
`delay (260/310/6 ms, fb 24/24/0%, out 35/35/0%)` — matching `lbaudio_ax.c:2126,2134` and
`axdriver.c:1128-1149`. Reverb-hi and chorus stay unimplemented and now return **0** from Init so
axdriver leaves the bus unregistered, rather than returning 1 and leaving a live send feeding a
processor that is not there. An aux bus with no callback is dropped, as the DSP drops it.

## 19.4 The music slider was turning the sound effects down

`shim_misc.c` tracks `AISetStreamVolLeft/Right` and the mixer applied them as a master gain. On
hardware that call governs the AI's own DVD-streaming channel; Melee calls it from
`HSD_SynthStreamSetVolume` with the **music** volume (`HSD_Synth_804D6030`). This port plays the
stream through ordinary AX voices, and 804D6030 is already folded into every node's
`ve.currentVolume` (synth.c:986, :1345) — so the master gain both double-attenuated the music and
dragged every sound effect down with the music slider. The AI values are now tracked for logging
only. Harmless at the default (255), wrong as soon as the user touches the music volume.

## 19.5 Mixer quality

- **Linear interpolation** replaces the zero-order hold. The old resampler kept only the last
  decoded sample and *discarded* samples when pitching up, which aliases on every pitched voice —
  most of them. AX's own SRC interpolates (`AX_SRC_TYPE_LINEAR`).
- **ADPCM framing** now finds the frame header by nibble alignment (`cur_addr & 0xF`), as the
  hardware does, instead of a `samples_left` counter. Equivalent for a well-formed stream but
  self-resynchronising after an arbitrary seek — which `AXSetVoiceCurrentAddr` does on every
  stream block.
- **All nine AXPBMIX targets** are read (was: L and R only), with their `vDelta*` ramps.
- **De-pop**: a stopping voice's contribution used to step to zero in one sample. Its last value is
  now ramped out across the following sub-frame, as AX does through `AXPBDPOP`.
- **ITD** is implemented (was a no-op): up to a 31-sample independent delay on the main L/R sends,
  stepped one sample per sub-frame towards the target. `AXSetVoiceItdOn` now also sets
  `pb.itd.flag`, which is what `HSD_SynthSFXUpdateMix` tests to choose the interpolating path.
- `pb.ve.currentVolume` is written back alongside `pb.state` and `pb.addr.currentAddress`.
- The interpolation product needed 64 bits: `(next - prev) * frac` reaches 65535*65535, which
  overflows `int32`.

## 19.6 Tooling

- `MELEE_AUDIO_DUMP=<path>` writes the final mix to a 32 kHz stereo WAV (header refreshed about
  once a second, so it stays playable after a crash). `MELEE_AUDIO_NOFX=1` bypasses the aux
  processors.
- `main.c` gained `MELEE_WINDOW_X/Y/W/H`. Non-negative positions go through `AuroraConfig`, so the
  window never flashes on the wrong display; negative ones (a monitor left of or above the primary)
  are applied right after `aurora_initialize`, because Aurora reads a negative `windowPosX/Y` as
  "undefined" and centres the window (`window.cpp:342`). Parking it at 30000,30000 gives an
  effectively headless run, which is how this pass was verified.
- `MELEE_WINDOW_HIDE=1` exists but **does not work**: a hidden window makes the D3D11 swapchain
  present block forever and the frame loop never leaves `retrace=0`. Use off-screen placement.

## 19.7 Verification

Scripted 110 s menu run, window off-screen, `MELEE_AUDIO_DUMP` on: **0 FATAL**, 60 Hz pacing,
underruns flat at 526 for the final 36 s (all accrued during boot and scene loads), clipping
0.0011% of samples, peak 32768, no dropouts in the capture. Both AXFX processors initialise with
the game's own parameters.

Note for future runs: with no pad script the port sits on the opening cinematic, where the game
requests **no** voices at all — `AXAcquireVoice` is never called and the mixer is legitimately
silent. Always drive audio tests with `MELEE_PAD_SCRIPT` (e.g. `_build/audio_test_script.txt`).

Not done: reverb-hi and chorus (Melee uses neither); the surround bus is mixed but has no output
path; the aux return is summed in the same sub-frame rather than one behind as the DSP's triple
buffer does.

# 20. Performance pass (2026-09-14) — the frame pacer was spinning a full core

Requested: "work on performance." The existing `MELEE_PROFILE=1` frame profiler
(`pc/platform/shim_vi.c`, §12 note "no profiler exists yet" is stale — one was added in the §13.1
pacing fix session) already showed a hard 60 Hz frame with excellent percentiles, so this pass
measured rather than guessed, per the §12 method note.

## 20.1 What the profiler + per-thread CPU accounting showed

A 240 s idle run (`MELEE_PROFILE=1`, no input, off-screen): frame timing was already excellent —
`p50=16.67 p95=16.97-17.02 p99=17.04-17.15`, histogram entirely in the `<17.5` bucket. The split
told a different story: `game=0.1-0.2 present=16.5 events=0.01 begin=0.03`. "game" (the game's own
simulation + FIFO writes between ticks) and the GPU submit together cost a fraction of a
millisecond; "present" — which wraps `gw_pace_field()`'s wait for the 60 Hz boundary plus the
actual submit — accounted for essentially the whole frame.

Cross-checked against real OS accounting (`Get-Process` per-thread `TotalProcessorTime` over a 10 s
window, not just the internal profiler's math): the process burned **0.96 of a full CPU core**,
continuously, with one thread alone responsible for **8.91 of those 10 CPU-seconds (89%)** — the
game thread. That thread does almost no real work per frame; it was spending ~16 ms of every
16.67 ms frame in a tight `while` loop calling `YieldProcessor()`, added by the §13.1 pacing fix to
hold the game to 60 Hz against a free-running VRR present. `YieldProcessor()` (a `pause`
instruction) is a spin hint, not a yield — the thread never leaves the run queue, so the OS
scheduler cannot idle that core. Wasted heat, battery and fan noise for zero smoothness benefit,
and on a machine with fewer than 20 logical cores (this dev box) it can cost the render worker
thread, or any other app running alongside the game, real cycles.

## 20.2 Fix: sleep for the bulk of the wait, spin only the final ~3 ms

`gw_pace_field()` (`shim_vi.c`) now sleeps through most of the remaining time and only spins for
precision once the boundary is close:

```c
if (target - now > GW_PACE_SPIN_TICKS) {   /* > ~3 ms remaining */
  Sleep(1);
} else {
  YieldProcessor();                        /* final stretch: spin for exact timing */
}
```

`Sleep(1)` on stock Windows timer resolution (~15.6 ms default) would sleep far longer than 1 ms
and blow the frame budget, so the process now calls `timeBeginPeriod(1)` once (lazily, on the first
pace call) to get ~1-2 ms wakeups; Windows resets a process's timer-resolution request
automatically on exit, so there is no matching `timeEndPeriod`. `winmm.lib` was added to
`_build/melee_link_libs.rsp` for it (same hand-maintained-`.rsp` pattern as the GC-adapter's
`hid.lib`/`winusb.lib`/`setupapi.lib`, noted in §11). The periodic pump of alarms/deferred work
(`gw_os_run_alarms`/`gw_run_deferred`) keeps the exact same ~1 ms cadence it had before, just
checked after each wake instead of after each spin iteration — no behavior change there.

`GW_PACE_SPIN_TICKS` = 3 ms, sized comfortably above `Sleep(1)`'s typical overshoot under load so
the spin-tail absorbs the imprecision and the boundary is still hit exactly, same as before.

Audited the rest of `pc/platform` for the same bug class (a `while`/`for(;;)` loop with no blocking
wait): none found. The watchdog thread already sleeps 100 ms per poll; the two other unbounded
loops (`gw_runtime.c`'s watchdog body, `shim_dvd.c`'s FST path walk) are a periodic sleep and a
bounded tree walk respectively, not spins.

## 20.3 Verified

- **CPU, idle title screen, 10 s window:** 0.96 cores -> **0.23 cores** (process total); the
  spinning thread's share: 89% of a core -> **15.5%** of a core.
- **Frame timing, 240 s idle run, post-fix:** `p50=16.66-16.67 p95=16.93-16.96 p99=16.99-17.10`,
  histogram still entirely in `<17.5` at steady state — as good as before the change, marginally
  better in the tail. Zero FATAL, zero new empty ticks, wall-clock `present` unchanged (~16.5 ms,
  as it must be — only the CPU spent during that wall time dropped, not the wait itself).
- **Frame timing under real rendering load** (90 s run via the known-safe
  `audio_test_script.txt` pad script, into the menu with character models rendering — 151 frames
  with nonzero envelope-blend counts confirm skinned meshes were actually drawn):
  `p50=16.66 p95=17.1-17.4 p99=17.6-17.7 max<18.6`, zero FATAL, zero empty ticks, `game` cost still
  under 0.6 ms. The wider tail here is real GPU/game variance under load, comfortably inside one
  frame period either way.
- Audio unaffected: device opens at the same 60 ms target latency, no underruns, no ordering
  change (`gw_ax_frame_tick` is still called from the same point in `gw_frame_tick`).

One boot-time outlier remains and is unrelated to this change: the very first profiled frame after
disc load shows `game=3292 ms` (a one-time FST/boot stall, not `present`/pacing) — present before
this fix too, unaffected by it, and out of scope for a pacing change.

Not investigated this pass: GPU-bound cost in a real 4-player VS match (menu load is the heaviest
rendering scene actually profiled here); reaching one unattended needs either a much longer idle
wait for the attract-mode demo timer or CSS/SSS pad-script navigation, both deferred to keep this
pass fast and low-risk.

# 21. THP video decode ported — the cutscenes play for real (2026-09-14)

§17.6 left THP decode unimplemented and the movies showing a placeholder. The decoder is now
ported and every THP clip plays correctly, including the opening cinematic, which is enabled by
default again.

## 21.1 What was blocking it

`extern/dolphin/src/dolphin/thp/THPDec.c` is a complete, matching decompilation of the SDK's THP
decoder — but ~37 of its inner loops are MWERKS inline PowerPC `asm`, which clang's PPC front end
refuses outright, so the TU could not go through gwtool at all. Six functions were affected:

| Function | What the assembly was |
|---|---|
| `__THPInverseDCTNoYPos`, `__THPInverseDCTY8` | paired-single (Gekko SIMD) AAN float IDCT + tiled store |
| `__THPHuffDecodeTab` | one Huffman symbol, 5-bit quick table + maxCode fallback |
| `__THPHuffDecodeDCTCompY/U/V` | a full baseline-JPEG block: DC predictor, AC run/size loop |
| `THPInit` | locked-cache setup, plus GQR configuration |

## 21.2 The port

Each is now a `TARGET_PC` branch in `THPDec.c` carrying a plain-C implementation, with the
original assembly kept under `#else` so the decomp still builds for its real target. These are not
instruction-by-instruction transliterations — they are the standard algorithms the assembly
implements, which is both far less error-prone and much shorter (~300 lines total):

- **IDCT.** This is libjpeg's `jidctflt` AAN float IDCT. `__THPReadQuantizationTable` pre-scales
  the quantisation tables by `__THPAANScaleFactor[row] * __THPAANScaleFactor[col]` and deliberately
  omits the 1/8 — which is exactly the AAN setup — and the assembly's output stage supplies the
  rest: a bias of 1024.0 folded into the even half of the column butterfly, and a store through
  `GQR6 = 0x3D043D04`, i.e. u8 with store scale 2^-3. That is "divide by 8, clamp to 0..255", and
  the bias then lands as the +128 JPEG level shift. Both collapse into one `__THPStoreSample`.
  The assembly's extra zero-coefficient shortcut tiers (`_quarterIDCT`/`_halfIDCT`, picked by how
  many coefficients in a row are zero) are pure optimisations; they became a single all-AC-zero
  fast path.
- **Output layout is unchanged:** 8x4 `GX_TF_I8` tiles, 32 bytes each, `Gwid` pixels per row, so a
  tile row is `Gwid*4` bytes and `__THPInverseDCTY8` simply starts `Gwid*8` lower.
- **Huffman.** Baseline JPEG, over the same 5-bit `quick`/`increment` lookup and `maxCode`/`valPtr`
  fallback that `__THPPrepBitStream` builds. The bit reader keeps the original state exactly
  (`cnt` a 1-based cursor into the big-endian word `currByte`, so `33 - cnt` bits remain), with
  `__THPSlw`/`__THPSrw` reproducing PowerPC's "shift count with bit 5 set yields zero" where C
  would be UB. All stream loads stay ordinary C loads so gwtool byte-swaps them, which is what
  makes the big-endian bitstream read correctly without any manual swapping.
- **`THPInit`.** Two problems at once: it addresses the locked cache at `0xE0000000`, and its
  `__THPLC` setup is a **GC-layout alias view** of the §16.1 class — it writes `work672[]` past the
  end of `__THPLC` expecting `__THPLCWork672` to be the next symbol in memory. The PC branch skips
  both and points `__THPLCWork672[0..2]` at a static buffer, sized for 672-wide (Y is `width*16`
  bytes per MCU row, U and V `(width/2)*8` each).

Supporting shims in `shim_misc.c`: `gw_DCZeroRange` (the one cache op with a real side effect —
`dcbz` establishes zeroed lines, and `THPVideoDecode` relies on it to clear its 0x920-byte state),
plus `gw_LCStoreData` (a memcpy, since the "locked cache" is now ordinary memory) and
`gw_LCQueueWait` (a no-op). The THP stubs are gone from `shim_dev.c`; `THPDec.c` is in
`files.txt` and `melee_link_objects.rsp`.

## 21.3 The opening movie plays again by default

`gw_OSGetResetCode` had been hardcoded since the port's first commit to `0x80000000`, the
"rebooted from the IPL" code, which makes `gmmain_lib.c` set `skip_intro` and `bootOnLoad` jump
straight to `GM_TITLE`. That was the right call while THP drew garbage. It now reports a cold boot
— which is what launching the executable actually is — so `MvOpen.mth` plays, Start-skippable
exactly as on console. `MELEE_SKIP_INTRO=1` restores straight-to-title.

The `MELEE_FORCE_INTRO` knob added earlier in the session is gone, replaced by its inverse.

## 21.4 Verified

Full opening cinematic, off-screen capture, memory card enabled: plays start to finish, hands off
to the title screen, and attract mode follows with a live 4-player demo. **0 FATAL.** Frame pacing
holds at `p50=16.67 p95≈18.0 p99≈18.7` throughout playback.

Picture quality checked against content that would expose any decoder error: the sky/lens-flare
opening shot (smooth gradients — banding or DC drift would show), the "Nintendo's All-Stars in"
title card (crisp white-on-black text — any high-frequency coefficient error would ring or smear),
the Link sage-medallion card (fine engraving detail, correct skin/tunic/Triforce colours), and
Pikachu's Thunder (high-contrast lightning over cloud). All clean, correct colours, no tiling
seams, no chroma misregistration.

Cost: steady-state `game` time during playback is **under 1 ms per frame** (640x480), so the scalar
C decoder is comfortably fast enough; the profiler's remaining spikes attribute to disc I/O and
window-event pumping, not decode. The one-time ~700 ms spike at movie start is the file load.

Also fixed as a consequence: the same decoder backs the How-To-Play video, the Vault movies, and
the post-game "Congrats" still (`gm_1A9B.c` via `lb_01F8.c`), all of which previously drew
uninitialised heap. Those paths are not individually exercised here, but they share this code.

## 21.5 Why port the 2001 decoder rather than write a modern one

THP video is just baseline JPEG frames (intra-only, 4:2:0) in a simple container, so "porting the
decoder" meant porting a JPEG decoder — the same AAN IDCT maths any modern decoder uses. Only the
two asm-only inner loops were missing; the container parsing, frame scheduling, disc streaming and
GX upload were already real C in the decomp and already worked.

The alternative — transcoding the disc's `.thp` files to a modern codec and writing a new player —
was worse on every axis that matters here: it breaks the project's "bring your own ISO, read it
directly" model by requiring a conversion step and somewhere to put the output, it adds a large
third-party codec dependency to a 32-bit build, and it would still have to reproduce the game's
own movie state machine (`lbmthp.c`'s alarm-driven scheduling and `HSD_DevComRequest` streaming).

This does not cost anything for custom cutscenes later. It is strictly additive: the pipeline from
compressed frame → Y/U/V planes → GX tiles → screen → the game's scene state machine now works end
to end, which is the hard game-specific part. A modern codec can be dropped in later by filling the
same three planes and reusing all of it. And custom cutscenes are possible today by encoding to
THP, which is a documented format with existing encoders.

# 17. Documented crashes (not to fix)

## 17.3 GPU-backend crash in webgpu_dawn.dll (renderer, not game logic)
A no-card session crashed with `FATAL ... at 6F263548 webgpu_dawn.dll+0x363548`, `read of
0x000050E6` (near NULL), called from `gw_frame_tick+0x1143` (shim_vi present path). The fault is
inside Aurora's Dawn/WebGPU backend, not game code - a different class from the semantic/alias
work. Possible causes: a resource-lifetime/backend bug in Dawn or the Aurora WebGPU driver, or a
driver-specific issue. Evidence: `.omo/evidence/dawn-crash.log`. Not investigated.

## 17.2 Results-screen per-player stats are corrupted (deferred - user says don't fix yet)
After the results crash fixes (§16.4 camera/`pl` aliases, commits e6faf4f30 chain), the results
screen displays but the per-player stats (damage dealt and the "for fun" end-of-match values) show
garbage/maxed values. Likely another results-data source/alias issue in `gmresult.c` /
`gmresultplayer.c` (`MatchEnd`/`ResultsData` fields) - same family as the aliases above. Deliberately
deferred per the user's request; log only. Evidence: `.omo/evidence/results-hang-css.log` (same run).

## 17.6 Opening pre-rendered cinematic is corrupted - FIXED (2026-09-14, see section 21)
Root cause: THP video decode is not implemented on this port. `pc/platform/shim_dev.c`'s
`gw_THPVideoDecode`/`gw_THPDec_80331340`/`gw_THPDec_803313D0` are stubs that do nothing (the real
decoder, `extern/dolphin/src/dolphin/thp/THPDec.c`, is ~2800 lines with ~37 inline PPC `asm` blocks
in its DCT/Huffman/MCU decode path - the same class of blocker as the AXFX reverb/delay port in the
audio pass, clang's PPC front end will not accept `asm`). Both THP call sites
(`lbmthp.c`'s `fn_8001EF5C`, the multi-frame player used for the boot intro/How-To-Play/Vault
movies, and `lb_01F8.c`'s `lbMthp8001FAA0`, the single-frame decoder used for the post-game
"Congrats" still) call the stub unconditionally and use its result with **no success check**, so
the Y/U/V planes they hand to GX as three `GX_TF_I8` textures are never written by decode at all -
they display whatever `HSD_MemAlloc` handed back. Confirmed empirically (`MELEE_FORCE_INTRO=1`,
below): a flat **solid green** frame for the whole clip, which is exactly what the port's (correct)
YCbCr->RGB TEV conversion produces from all-zero planes (Y=Cb=Cr=0 -> R=0, G=~135, B=0 by the
standard BT.601 matrix) - i.e. the color-conversion path itself is fine; only the source content is
missing. That rules out the "colour-space/texture-upload gap" guess this note originally made.

**Partial fix** (`src/melee/lb/lbmthp.c` `fn_8001ECF4`, `src/melee/lb/lb_01F8.c`
`lbMthp8001FAA0`, both `TARGET_PC`-guarded): seed the Y/U/V planes with a flat black frame
(Y=0x10, Cb=Cr=0x80) once, right after allocation. Since nothing else ever writes them, every THP
clip now displays as a stable black frame instead of solid green/garbage. This does **not** make
movies play - it converts "visibly corrupted" into "plays as black" - real playback needs the
~2800-line decoder ported by hand (large, not attempted here).

**The boot-time opening (`MvOpen.mth`) is not reachable in normal play anyway**: `gw_OSGetResetCode`
(`shim_os.c`) has hardcoded `skip_intro = true` since the port's first commit, so `bootOnLoad`
(`gmboot.c`) always jumps straight to `GM_TITLE` and `GM_OPENING_MV` (`gmopening.c`, which is the
only caller of `lbMthp_8001F410("MvOpen.mth", ...)`) never runs. A normal user never sees this path
at all, corrupted or otherwise - confirmed with an off-screen boot capture (`PrintWindow`, no window
ever shown): title renders correctly, no THP attempt in the log. Added `MELEE_FORCE_INTRO=1` (same
shim) to force it on for testing without editing source; verified the fix through it (screenshots
in session, not committed - green before, black after, matching the hand-computed matrix exactly).
Still corrupted/black-instead-of-playing, reachable in normal play without the env var: the
How-To-Play video and Vault movies (`gmhowto.c`, `mngallery.c`) and the post-game "Congrats" still
(`gm_1A9B.c`), all through the same unchecked-decode path - not individually verified in-game this
session (menu navigation to reach them was judged not worth the risk for this pass; the fix is the
same code path already confirmed via the forced intro).

## 17.5 Zelda/Sheik respawn spawns BOTH as independent fighters (real gameplay bug, VS)
Observed in VS: player on Fox kills Zelda. Zelda respawns on the revival platform, and an
**independent Sheik respawns with her** - two separate controllable characters on the field. Both
count for kill credit, and the stock only fully respawns after both are killed. Root cause is
presumably the transform/respawn pairing: Zelda and Sheik share one player slot via the transform,
and the revival path appears to spawn the paired fighter as a second entity instead of swapping the
existing one. Related handling exists in `gm_1798.c` `fn_8017A67C` (`if ((u32)(kind - 0x12) <= 1U)`
special-cases ZKind 0x12/0x13 = Zelda/Sheik). **FIXED (2026-09-13, `b7612f1f7`)** — the real cause was
in `pl/player.c` `Player_80032070`, which reads `unkStruct->vec_arr[ckind].z` (an alias of
`ftMapping_list[ckind].has_transformation`) to decide whether to also revive the dormant partner. On
the port that alias reads unrelated memory, so the companion-revive branch fired for Zelda and
revived Sheik as a second fighter. It now reads `ftMapping_list[ckind].has_transformation` under
`TARGET_PC` (Ice Climbers still revive Nana via `has_transformation == 0`). Re-confirmed by
investigation on 2026-09-15; this note had gone stale during the public-release docs aggregation.

## 17.4 Single-player crashes: animation descriptor holds garbage (Classic + Adventure)
The same family, twice, both non-VS:
- Classic: `HSD_WObjAddAnim+0x24`, `read of 0x3A83126F` (= float 0.001 as a pointer), from
  `HSD_LObjAddAnimAll+0x55`. Evidence `.omo/evidence/classic-crash.log`.
- Adventure (after Bowser / at the ending): `HSD_AObjLoadDesc+0x48`, `read of 0x00B5CF3F`, with
  `edx=0x3A51B717` and `ebx=0x00B5CF3F` both float bit patterns, from `HSD_WObjAddAnim+0x2E`.
  Evidence `.omo/evidence/adventure-crash.log`.
A stage/light/animation descriptor is built from wrong memory (floats read as pointers), likely one
of the unfixed `gr/`/`mn/` alias views in §16.4. Non-VS, so logged and left per the user's VS
priority - not the `CLASSIC_MATCHUPS` fix.

## 17.1 Zelda/Sheik side-B — motion-state table walk off the rails (fun/harmless to leave)
Reported while testing characters: `ftSk_SpecialLw_80114758` (Sheik's side-B) →
`Fighter_ChangeMotionState+0x835`, `read of 0x0B528E88`, `ebp=0x2A0`, `eax=0x506C795A`
(= ASCII "ZylP" byte-swapped — a string fragment read as a pointer), `ebx=0x81272E08`. So the
motion-state change looks up a char-state entry that isn't valid for Sheik's copy/transform case
and the walk dereferences garbage. Same family as the `ftData_CharacterStateTables` concern
(§16.3). Deliberately **not fixed** — the user asked to keep/document it. Evidence:
`.omo/evidence/zelda-sheik-crash.log`.

## 16.3 Other real/likely findings not yet fixed
- `ft` Luigi `x222C_cycloneCharge` (`ftluigispeciallw.c:109/228`) read before write (source-annotated).
- `ft` mode-gated init: the cloak-refraction table (built only in VS scene `fn_8016E730`, `gmvs.c:2000`,
  read unguarded from `ftmaterial.c:71`), plus crowd-SFX (`gmvs.c:2025`) and bg-flash (`gmvs.c:2031`)
  with the same VS-only-init shape.
- `ft` `ftdemo.c:83` `ftData_UnkDemoCallbacks0[kind]` called with 29/33 slots NULL (all shipped callers
  use Mr/Kb/Lg/Gk).
- `gr` class C was empty (no mode-gated-init candidate).

## 18.1 Crash logs are archived (`crashlogs/`)

`melee-pc.log` is truncated on every launch, so a crash's only record was lost on the next run.
`gw_archive_crash_log()` (`pc/platform/gw_runtime.c`) now copies the session log to
`crashlogs/crash-<YYYYMMDD-HHMMSS>.log` (one-line `==== crash <time> <reason> ====` header then the
log) from every fatal path: `gw_panic` (all game `OSPanic`/asserts), the SEH handler
(`gw_unhandled_exception`), and the CRT invalid-parameter handler (`gw_invalid_parameter`). Files are
never overwritten and never rotated. The folder is created on demand next to the exe.

Gap: a hard `__fastfail` death (e.g. a raw stack-buffer overrun) bypasses SEH and archives nothing.
The CRT's own overrun path is caught by the invalid-parameter handler; not every fastfail is.

## 18.2 PAGE_GUARD watchdog is opt-in (`MELEE_WATCH=1`)

`gw_watch_page`/`gw_watch_tick` (`pc/platform/gw_runtime.c`) now no-op unless `MELEE_WATCH=1`. The
watchdog was always-on and flooded `melee-pc.log` with `gw: GUARD access ...` lines (one per re-arm
per frame) and perturbed frame timing. With it off, a normal boot logs ~128 KB instead of ~500 KB.
Set `MELEE_WATCH=1` only when chasing what writes a watched field.

## 18.3 Debug menu: Unlock All Characters / Unlock All Stages (commit `ab1e3c9f1`)

Two rows in the debug-menu root table `un_803FA4E0` (`if/soundtest.c`) call `gm_80164F18()` /
`gm_8016468C()` and persist via `lb_8001C87C()` after `lbCardNew_AllocWorkArea()`. The save needs the
card work area (the memcard scene normally allocates it) but not the card archive, which is why
`lb_8001C87C` works here and the asserting `lb_8001C8BC` does not. On a retail ISO `DbLevel` is forced
to `Master` (no `/develop.ini`), so the debug menu is unreachable; TARGET_PC branches in `gmtitle.c`
(the title scene exits on Y/B) and both title mode exits (`gmtitlemode.c onExit`,
`gmopeningmode.c onExitTitle`) route Y/B to `GM_DEBUG`. Keyboard Y/Z/L/R are not in the pad overlay,
so B (key `K`) is the keyboard entry point.

# 22. Stock icons showed Captain Falcon for every character — decomp UB, port-only (2026-09-15)

`gm_80168B34` (per-character frame index into the shared stock-icon / character-art texture atlas)
left its `base` local **uninitialised** for ordinary characters, and `gm_80168BF8` (player → icon
frame) had **no `return`**, relying on the tail call. Both are matching-decomp artifacts: mwcc kept
`ckind` in the register so `base` was accidentally right, and the missing return rode the tail call.
clang's `-ftrivial-auto-var-init=zero` (see `pipe_wsl.sh`) makes `base` 0, so
`return base + costume * 30` maps *every* character to frame 0 — which is **Captain Falcon**
(`CKind_Captain = 0`). Every HUD stock icon, status icon and results-screen art showed Falcon.
Fixed with `int base = ckind;` and an explicit `return`, both `TARGET_PC`-guarded (original kept for
the matching build); `if/ifstock.c`, `if/ifstatus.c` and `gm/gmresultplayer.c` all call through it.

New bug class to watch for: **decompiled C whose semantics depended on register reuse or a tail
call** — correct in the matching build, wrong here. Different from the GC-layout alias views (§16.1):
there the *address* is wrong, here the *value* is uninitialised. Worth a sweep for non-void functions
with no `return` and locals read before assignment. Not a regression from the audio/pacing/THP or
§16.4 passes — `gm_1601.c` was untouched by them.

# 23. Name-entry keyboard alias views + the Target Test C-stick toggle (2026-09-15)

## 23.1 The name-entry keyboard rendered no glyphs and crashed (same class as 16.4)
`mn/mnnamenew.c` casts `mnNameNew_803EDA58` (an `AnimLoopSettings[3]`, 0x803EDA58, 0x24 bytes) to a
reconstructed `MnNameNewDataLayout` whose `key_jobj_ids`/`x34`/`xFC`/`character_bytes`/`lower_glyphs`/
`upper_glyphs` fields actually live at 0x803EDA7C (`mnNameNew_KeyMap`) and 0x803EDCE4
(`mnNameNew_GlyphTable`). Those are separate symbols on the port, so the keyboard read unrelated
memory: no characters rendered, and `mnNameNew_MainInput` dereferenced a NULL glyph and crashed
(0x102A8459, `mnNameNew_MainInput+0xC9`). Fixed by reaching the real
`mnNameNew_KeyMap`/`mnNameNew_GlyphTable`/`unk_vec` symbols by name under TARGET_PC (`MNNAMENEW_*`
accessors). Same class as §16.1/§16.4 — `mnnamenew.c` was simply not in the 16.4 sweep table.

## 23.2 Target Test C-stick smash toggle
In 1P modes `Fighter_Spaghetti_8006AD10` (`ft/fighter.c`) zeroes `fp->input.cstick[0]`, and
`Camera_8002B0E0` (`cm/camera.c`) reads the raw pad for the zoom, so Target Test has no C-stick
smashes/aerials. New global `gm_CStickSmashTargetTest` (default off) plus a `C-STICK: SMASH` /
`C-STICK: CAMERA` label on the `STADIUM_TARGET` CSS (toggled with L/R) gates both: the fighter copies
the C-stick through, and the camera zoom is skipped. All `TARGET_PC`-guarded.

# 24. Audit wrap-up: 16.4 follow-ups, 15.2 and 16.3 (2026-09-15)

Closed the remaining audit items. All `TARGET_PC`-guarded; TUs compile, relink OK, 100 s off-screen
smoke 0 FATAL.

**Fixed**
- **§16.4 follow-ups** — `grzebes.c`: `(grZe_BubbleState*)grZe_8049F140` (`bubbles` → `grZe_8049F170`)
  and the `Vec3* base = grZe_8049F140` views (`base[2]/[3]` → `grZe_8049F158[0..1]`). `grvenom.c`:
  `base[xC8+14]` → `grVe_803E5380[xC8]`, `base[idx0+0xD6]`/`anim_ids` → `grVe_803E56A0`, and
  `grVe_GetAnimArg` → `grVe_803E5644[...]` (+0x2FC).
- **§15.2** — `particle.c` `hsd_804D08E8[...]` masked to `& 7` (8-entry table); `gmtoulib.c`
  `lbl_80473AB8[i + 1]` bounded (`i < 0x40` / `i < 0x3F`).
- **§16.3** — Luigi `x222C_cycloneCharge` zeroed in `ftLg_Init_OnLoad` (read-before-write; the block is
  never cleared); `ftdemo.c` `ftData_UnkDemoCallbacks0[kind]` NULL-guarded (latent).

**False positives — do NOT "fix" these**
- §15.2 `ftkinds/ftKirby/ftkirby.c` `ftKb_SpecialN_800F16D0` — already fully guarded
  (`de5fdc11a` / `bdcace0ab`); no raw `g->hats[...]` deref remains. The note was stale.
- §15.2 `texp.c` `a_in[cnst->reg-4]` — `cnst->reg` is only ever `0..7` or `0xFF`, so the index is
  provably 0..3. `tobj.c`/`psdisp.c` indices are data-driven and cannot be shown out of range.
- §16.3 "VS-only init" (cloak-refraction / crowd-SFX / bg-flash) — `fn_8016E730` runs for **every**
  fight (all 1P modes use `GS_VS`), so the reads are always preceded by the init.
- §16.3 `ftdemo.c` callbacks — 29/33 slots are NULL but no shipped caller passes those kinds, so it is
  latent only; guarded anyway.

The §17 list (documented crashes, deliberately unfixed) is unchanged.

# 25. Endianness boundary (last 15.2 item) + C-stick hotkey (2026-09-15)

## 25.1 Shim endianness
- `shim_os.c`: `gw_OSTicksToCalendarTime` now byte-swaps all ten `OSCalendarTime` fields after
  Aurora's native write, so the game reads the date big-endian (the save-description date was
  garbage — §13.6.5). Swapped by field name, not a raw byte loop.
- `shim_pad.c`: `gw_PADRead` byte-swaps the `u16 button` of **all four channels** immediately after
  `PADRead`, before the adapter/keyboard/script overlays (which already write big-endian with
  `gw_w16`). `extButton` is left native — the game (`HSD_PadRenewMasterStatus`) never reads it.

## 25.2 C-stick smash toggle: in-game hotkey
`ft/fighter.c` `Fighter_Spaghetti_8006AD10` (Target Test, player 0) flips `gm_CStickSmashTargetTest`
on the rising edge of either the controller combo `L + R + Start` or keyboard `F1`. F1 is not in the
GameCube pad bitfield, so `shim_pad.c`'s keyboard overlay maps it onto the reserved pad bit
`HSD_PAD_7` (0x0080), which flows through `HSD_PadRenewMasterStatus` into `HSD_PadGameStatus[0]`.
Each toggle logs `C-STICK: SMASH` / `C-STICK: CAMERA` via `OSReport` (an in-match SisLib text was
judged disproportionate). Gated on `GM_TARGET_TEST` so it never fires in VS.

# 26. Custom Break the Targets levels — mod loader, Phase 1 (2026-09-15)

A data-driven loader for custom Target Test target layouts. Phase 1 reuses each character's existing
Target Test stage geometry and only moves the targets.

- **Format** — `mods/targettest/<name>.tt` next to the executable, plain line-based text (`#`
  comments): `name <text>`, `character <ckind | name>` (e.g. `mario`), `target <x> <y> <z>` (up to
  21), and an optional `basestage <name>` accepted-and-ignored for forward compatibility with Phase 2
  geometry. No JSON dependency (this build is 32-bit). One mod per character; duplicates are logged
  and ignored.
- **Loader** — `pc/platform/gw_runtime.c`: `gw_TTMod_Count/ForCharacter/TargetCount/Target`, scanning
  `mods/targettest/` resolved next to the exe (same `GetModuleFileNameA` pattern as `shim_card.c`'s
  `card/`). Coordinates are stored native and marshalled to big-endian guest memory with `gw_wf32`.
  `main.c` triggers the scan at boot so the result is visible without entering Target Test.
- **Hook** — `gr/ground.c` `Ground_801C4210`: if a mod claims the loading Target Test character, spawn
  each target with `it_8027B5B0(It_Kind_Mato, &pos, NULL, NULL, 0)` at the mod's bare world
  coordinates and set `stage_info.x6D2/x6D4`. A NULL joint is deliberate: `itMato_UnkMotion0_Phys`
  only follows a joint when one is stored, so a joint-less target stays where it spawned. The vanilla
  `x280[199..219]` joint loop remains the PC fallback and the non-PC path.
- **Cross-boundary calls** — game code declares/calls the **unprefixed** `TTMod_*`; gwtool prefixes
  every game symbol, yielding `gw_TTMod_*`, matching the shim's definition.
- **Verified** — boot logs `gw: targettest: loaded 1 mods from C:\gdm\_build\mods\targettest`,
  0 FATAL. In-match target placement was not yet exercised (needs driving to Target Test).

**Known limits / Phase 2** — geometry is reused, so a mod can only move targets; max 21 targets
(`x280[199..219]`); one mod per character. Custom platforms require building a merged `MapCollData`
and re-running `mpLibLoad` at stage load (collision is a 2D XY line DB with no append API — see the
collision notes), plus the Blender round-trip exporter.

# 27. Custom Break the Targets geometry + Blender authoring — Phase C (2026-09-15)

A mod can now add floating, stand-on **platforms**.

- **Format** — `platform <cx> <cy> <cz> <w> <d>`: top surface at `cy`, X extent `w`, Z extent `d`
  (depth is display-only; collision is 2D XY). Loader API `gw_TTMod_PlatformCount` /
  `gw_TTMod_Platform` (limit 16).
- **Collision** — at stage load (`Ground_801C0800`, Target Test stages only, only when the active mod
  has platforms) a **merged `MapCollData`** is built in guest memory: the original `coll_data` copied
  verbatim plus one floor joint/line/vert-pair appended per platform, then `mpLibLoad` is re-run on
  it. Append-only, so no existing joint's per-kind ranges and no line-adjacency ids change. The
  appended lines' `groundCollLine` entries are initialised right after `mpLibLoad` via
  `mpGetGroundCollLine()`, reproducing what `mpLibLoad` does for the top-level ranges. Platforms get
  no `mpIsland` segment (fine for static single-player geometry; friction comes from `lo_flags`).
- **Visual** — a unit-cube HSD `Joint`/`DObj`/`MObj`/`PObj` (constant-diffuse material,
  `GX_CULL_NONE`) is built in game code and attached under map GObj 0's root JObj, scaled per
  platform.
- **Coordinates** — world→collision via `1/Ground_801C0498()`, the same factor `mpLibLoad` applies
  and the map JObj tree is under, so collision and visual coincide.
- **Verified** — compiles, links, boot **0 FATAL**, loader reports the mod. **In-game stand-on
  collision and the box visuals are NOT yet verified** (needs driving into Target Test); the
  "map GObj 0 is the visible root" assumption is the main thing to confirm on first play.

## 27.1 Blender authoring (`tools/blender/`)
- `melee_target_test_io.py` — Blender 4.x add-on: Export/Import `.tt` (File menu) plus a View3D
  sidebar panel. The parse/serialize layer has no `bpy` dependency, so it is testable outside Blender.
- Coordinate mapping, symmetric so a round trip is identity: `melee_x = bx`, `melee_y = bz`,
  `melee_z = -by`.
- `README.md` — install, usage, format reference. `test_roundtrip.py` — standalone, **all 42 checks
  pass**.
- Platform `cy` is the top surface; the vertical thickness is a documented default (2.0) and is not
  stored in `.tt`.
- Character names use the same table as the port loader, so `mario`→8, `fox`→2, `zelda`→18 resolve
  identically on both sides.

# 28. In-game verification pass (2026-09-15)

Driven headlessly with `MELEE_PAD_SCRIPT` + `PrintWindow` captures (window parked off every monitor).
Harness: `_build/tt_script.txt` (boot → title → 1-P Mode → Stadium → Target Test CSS).

**Verified in-game**
- The Target Test mod loader runs: `gw: targettest: loaded 1 mods from C:\gdm\_build\mods\targettest`.
- The Target Test CSS renders, and the **C-stick CSS toggle works end-to-end**: it shows
  `C-STICK: CAMERA`, and pressing **L** flips it to `C-STICK: SMASH` (captured).
- No crash across the whole navigation (boot → title → 1-P Mode → Stadium → Target Test CSS), 0 FATAL.

**Not verified — needs hands-on play**
- Entering the Target Test match itself, so **target placement, platform stand-on collision and the
  platform box visuals are still unconfirmed**. The script reaches the Target Test character-select
  screen reliably, but the roster cursor could not be moved onto a character via scripted input
  (DPad, analog stick and repeated A all failed to select), so the match never started.
- Priority for the first hands-on test: pick Mario, enter Target Test, and check (a) three targets at
  `0 30 0` / `45 60 0` / `-45 60 0`, (b) the two platform boxes at `0 40 0` and `-50 70 0` are visible
  and standable. If the boxes do not render, the map-GObj-0 attach assumption in §27 is wrong (no
  crash expected).

