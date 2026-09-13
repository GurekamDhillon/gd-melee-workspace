# HANDOFF — Melee PC port

> **Update, 2026-09-12 ~18:50 PDT (Claude Code session).** Boot now reaches the game's own
> startup banner. Read section 5 at the bottom first — it supersedes section 3, corrects two
> claims in sections 1 and 2, and records the fix for the current blocker. Everything above it is
> the original 18:10 handoff, left as written.

## Original handoff, 2026-09-12 ~18:10 PDT

**Milestone this session: the port now links and runs.** `_build/melee-pc.exe` launches, brings up
Aurora (D3D12 backend, 1280x960), maps MEM1 at 0x80000000, loads the disc FST, and boots far enough
to start audio/effect initialisation. The remaining work is boot debugging, not scaffolding — see §3
for the exact stopping point and the two candidate causes.

Written by opencode (WSL side) for the next agent, most likely Claude Code CLI on the Windows
side. Read this top to bottom before touching anything; the middle section lists facts that cost
real time to discover.

## 0. Environment / where things live

- Workspace root: `C:\Users\Gurek\Desktop\GD's Melee` (WSL: `/mnt/c/Users/Gurek/Desktop/GD's Melee`)
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
- Previous Claude Code session: `baee277b-47a0-4abc-8652-1166575f103e` ("gd-s-melee-05"), state on
  the Windows side under `C:\Users\Gurek\.claude\projects\C--Users-Gurek-Desktop-GD-s-Melee\`.

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
cd C:/gdm/_build && timeout 45s ./melee-pc.exe --iso "C:\Users\Gurek\Downloads\Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso"
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
