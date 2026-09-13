# HANDOFF — Melee PC port, 2026-09-12 ~18:10 PDT

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
