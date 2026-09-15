# Port dev quick-reference (agents: READ THIS FIRST)

Workspace root: `C:\gdm` = `/mnt/c/gdm` (a junction to the same checkout).
Game repo: `C:\gdm\melee` (branch `pc-port`). Build dir: `C:\gdm\_build`. Docs: `_research/`, `docs/DEVLOG.md`.
Commands digest: `docs/DEVLOG.md` §4. Boot gates / SDK notes: `_research/melee-boot.md`. Invariants: `_research/console-invariants.md`.

## Toolchain
- Clang: `/mnt/c/gdm/_toolchains/llvm/bin/clang.exe` (a Windows binary; run it directly from WSL, `--target=i686-pc-windows-msvc`).
- Windows-side steps run via `cmd.exe` from WSL. Visual Studio Build Tools supply `vcvarsall` for the link step.

## Rebuild a platform shim (`melee/pc/platform/<shim>.c`)
```
C:/gdm/_toolchains/llvm/bin/clang.exe --target=i686-pc-windows-msvc -c -O2 -DTARGET_PC \
  -I C:/gdm/melee/extern/aurora/include -I C:/gdm/melee/pc/platform \
  -I C:/gdm/_build/ax86/_deps/sdl3_prebuilt-src/include \
  C:/gdm/melee/pc/platform/<shim>.c -o C:/gdm/_build/masstest/shimobj/<shim>.obj
```
- The **SDL3 include path is required**, not optional: `main.c`, `shim_ax.c` and `shim_vi.c` all
  reach SDL3 headers (directly or through `aurora/event.h`). Omitting it fails with
  `'SDL3/SDL_events.h' file not found`.
- New shim file? Add its `.obj` to `_build/melee_link_objects.rsp` and any new import library to
  `_build/melee_link_libs.rsp` - **both response files are hand-maintained, not generated.**

## Rebuild one game TU (`melee/src/**.c`) - use the pipe script, NOT raw clang
```
cd /mnt/c/gdm/melee && bash /mnt/c/gdm/_build/masstest/pipe_wsl.sh <src path>   # e.g. src/melee/lb/lbarq.c
# Git Bash alternative: pipe_win.sh <path>
```
Game TUs go clang (PPC frontend) -> gwtool -> `.obj`. Compiling a game TU directly with the Windows clang produces a wrong object; always use the pipe.
- This includes SDK TUs under `extern/dolphin/src/` that the port builds for real rather than
  shimming - currently `mtx/mtx44.c` and `thp/THPDec.c` (see DEVLOG section 21). Adding one means a
  line in `_build/masstest/files.txt` **and** a line in `_build/melee_link_objects.rsp`.
- **Blocker to expect:** much of the SDK source is MWERKS inline PowerPC `asm`, which clang's PPC
  front end rejects outright, so those TUs cannot be piped as-is. Precedents both ways:
  `axfx/reverb_std.c` + `delay.c` were reimplemented natively in `shim_ax.c` (section 19.3);
  `thp/THPDec.c` was ported in place behind `TARGET_PC` with the assembly kept under `#else`
  (section 21.2).

## Relink (after any `.obj` change)
```
cmd.exe /c "cd /d C:\gdm\_build\ax86m && ..\build_melee_pc.bat"   # expect MELEE_PC_LINK_OK
```

## Run (interactive, e.g. for the user to play) - env vars must be EXPORTED
```
cd /mnt/c/gdm/_build
export MELEE_CARD=1            # memory card (GCI folder at _build/card)
export MELEE_PAD_IGNORE_ADAPTER=1   # only when using scripted/keyboard, not a real controller
export WSLENV="MELEE_CARD:MELEE_PAD_IGNORE_ADAPTER"
nohup ./melee-pc.exe --iso 'C:\iso\Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso' > /tmp/opencode/live.log 2>&1 &
disown
```
- **Gotcha:** `env MELEE_CARD=1 ./melee-pc.exe` does NOT propagate - `WSLENV` shares vars from the
  WSL *shell* environment, so the var must be `export`ed first (or already exported in the shell).
  Symptom of getting it wrong: the log says `card: disabled ... reporting no card`.
- Success looks like `gw: card: initialised (GCI folder) at ...\_build\card`; the
  `aurora::card: Failed to get status of file at idx: 1/2` errors are just empty slots.
- Kill before relaunch: `cmd.exe /c "taskkill /IM melee-pc.exe /F"`.

## Run (ONE instance only)
```
cd /mnt/c/gdm/_build && timeout 45s ./melee-pc.exe --iso '/mnt/c/iso/Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso'
```
- Before every run: `cmd.exe /c "tasklist | findstr /i melee-pc"` and wait until none. Two concurrent instances kill each other's runs.
- Screenshots and scripted input **are** available now and are the normal way to verify a visual change: `MELEE_PAD_SCRIPT` for input, `PrintWindow` for capture, window parked off-screen so nothing appears on the user's monitors (see "Run without the window appearing on a monitor"). Still ask the user for anything needing real judgement or a path the scripts cannot reach.
- `_build/melee-pc.log` is truncated on every run: copy it into `.omo/evidence/` immediately after a run.
- Never redirect stdout into `melee-pc.log` (two writers).

## Resolve an rva/crash address to a symbol (needs Git Bash gawk; WSL mawk fails)
```
"/mnt/c/Program Files/Git/bin/bash.exe" -lc 'bash /c/gdm/_build/masstest/mapsym.sh 0x10355E93'
```

## Environment variables

| Variable | Effect |
|---|---|
| `MELEE_ISO=<path>` | disc image, if not passed as `--iso` |
| `MELEE_CARD=1` | enable the memory card (GCI folder at `_build/card`) |
| `MELEE_SKIP_INTRO=1` | skip the opening movie and boot straight to the title |
| `MELEE_PAD_SCRIPT=<file>` | drive channel 0 from a text script; see `_build/audio_test_script.txt` |
| `MELEE_PAD_IGNORE_ADAPTER=1` | ignore a physical adapter (use with scripted/keyboard input) |
| `MELEE_PAD_DIAG=1` | adapter enumeration + raw report dumps |
| `MELEE_PROFILE=1` | per-frame timing split, percentiles, histogram (see section 20) |
| `MELEE_WINDOW_X/Y` | window position; may be negative. Applied at creation, so no flash |
| `MELEE_WINDOW_W/H` | window size (Aurora clamps to at least 640x480) |
| `MELEE_AUDIO_LATENCY_MS` | output ring cushion, default 60 (section 19.2) |
| `MELEE_AUDIO_DUMP=<path>` | write the final mix to a 32 kHz stereo WAV |
| `MELEE_AUDIO_NOFX=1` | bypass the aux effect processors |
| `MELEE_BACKEND=d3d12\|auto\|vulkan` | override the default D3D11 backend |
| `MELEE_AURORA_VERBOSE=1` | log Aurora INFO (present mode, adapter) |

`MELEE_WINDOW_HIDE=1` exists but **does not work**: a hidden window makes the D3D11 present block
forever and the frame loop never leaves `retrace=0`. Park the window off-screen instead.

## Run without the window appearing on a monitor

Some work needs the game running while the user is doing something else on screen. Place the window
off every monitor at creation time and hide the console:

```powershell
$env:MELEE_WINDOW_X = "30000"; $env:MELEE_WINDOW_Y = "30000"
Start-Process -FilePath C:\gdm\_build\melee-pc.exe `
  -ArgumentList '--iso','"C:\iso\Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso"' `
  -WorkingDirectory C:\gdm\_build -WindowStyle Hidden -PassThru
```

Frames can then be captured with `PrintWindow(hwnd, hdc, PW_RENDERFULLCONTENT)`, which works on an
off-screen window. A separate Windows desktop (`CreateDesktop` + `STARTUPINFO.lpDesktop`) does
**not** work - the process dies with `STATUS_DLL_INIT_FAILED` (0xC0000142).

**Audio tests must drive input.** With no pad script the port sits on the opening movie and then
the title screen; the game requests no AX voices there, so the mixer is legitimately silent and it
looks exactly like broken audio. Use `MELEE_PAD_SCRIPT` and confirm `gw: AX: first audible frame`
in the log before concluding anything.

## Conventions that have bitten workers
- **Big-endian game memory.** Native shims must read/write game-visible scalars with `gw_r32`/`gw_w32` (and `gw_r16`/`gw_w16`, `gw_rf32`/`gw_wf32`). A native little-endian store the game then byte-swaps reads back wrong (e.g. `AXVPB.index`).
- **Shim boundary.** A shim defines `gw_X`; the pipe/gwtool prefixes *every* symbol in a game TU with `gw_`, so game code must call the **unprefixed** `X`. Declare `extern void wait_idle(void);` and call `wait_idle()` under `TARGET_PC` - NOT `gw_wait_idle`, which double-prefixes to `gw_gw_wait_idle` and fails to link (this exact mistake cost a link cycle).
- **Deferred completions.** ARQ and DVD completions are queued via `gw_defer` and pumped only in `gw_wait_idle`/`gw_frame_tick`. Any game-side blocking spin that calls no shim deadlocks; fix it by pumping `gw_wait_idle()` inside the spin (TARGET_PC-guarded). Precedents: the pad gate (`shim_dvd.c` `gw_DVDGetDriveStatus` -> `gw_wait_idle`), `lbarq.c` ARQ wait, and `synth.c` deflag sync (see `shim_ar.c:12-14`).
- **Game-source changes** must be `#if defined(TARGET_PC)`-guarded with the original code kept.
- **Audio backend exists** (2026-09-12/13, reworked 2026-09-14 - see DEVLOG section 19). Aurora has no `ax`/`ai`/`dsp`, so `shim_ax.c` implements AX: DSP-ADPCM decode, a 64-voice mixer over `gw_aram` with linear resampling, both aux buses with native AXFX reverb-std and delay, ITD and de-pop, over an SDL3 32 kHz stereo output paced by the ring fill level. `HSD_SynthCallback` is pumped per sub-frame from `gw_frame_tick`.
- **Cutscenes work** (2026-09-14 - DEVLOG section 21). `extern/dolphin/src/dolphin/thp/THPDec.c` is built as a game TU with its Gekko paired-single IDCT and assembly Huffman decoders reimplemented in C behind `TARGET_PC`; the opening movie plays by default.
- **Commits:** commit on `pc-port` with a short `pc: ...` subject. Never `git add -A`; stage paths explicitly.
- **Evidence:** each task writes `.omo/evidence/task-<name>.log` with the exact commands and their outputs.
- **Aurora bootstrap cache.** `build_aurora_x86.bat` builds the vendored `melee/extern/aurora`. If `_build/ax86` was previously configured from another Aurora checkout (`dusklight/extern/aurora`), CMake refuses the stale cache ("does not match the source ... used to generate cache") - delete `_build/ax86/CMakeCache.txt` and `_build/ax86/CMakeFiles/` and re-run. Keep `_build/ax86/_deps`: `ax86m` reuses its `dawn-src` and SDL3 package.

## Endianness: one system exists (`gwtool` + `gw.h`) - do not build a second

**Mechanism.** Game TUs go clang `--target=ppc32-none-eabi ... -DLINT -DTARGET_PC` -> LLVM IR ->
`_build/gwtool/gwtool.exe` -> x86 COFF. gwtool byte-swaps *every* memory access, so game memory is
big-endian exactly as on GameCube and values are native only in registers; it also prefixes every
symbol with `gw_`. The full contract is the header comment of `pc/platform/gw.h` - read it before
touching a shim.

**Who swaps.** Game `src/` contains no swap code by construction (gwtool does it). Shims are native
x86 and swap by hand: every multi-byte field behind a game pointer must use `gw_r16/w16`,
`gw_r32/w32`, `gw_r64/w64`, `gw_rf32/wf32`, `gw_rptr/wptr`. A native LE store the game then
byte-swaps reads back wrong.

**ABI at the boundary** (`gw.h`): scalars (int/float/pointer) arrive native - declare normally; a
by-value struct arrives as a byte copy, so its fields are big-endian; a <=8-byte struct return comes
packed big-endian; a larger struct return uses a BE sret pointer.

**Swap-site inventory (2026-09-13; `shim_ax` has grown a lot since - recount before relying on it).** Shims: `shim_card` 40, `shim_ax` 23, `shim_gx` 23,
`shim_dvd` 7, `gw_runtime` 6, `shim_pad` 5, `shim_ar` 4, `shim_libc` 2, `shim_os` 2, `gc_adapter` 1.
Game `src/`: 0 (by construction).

**Formerly-known boundary violation (FIXED, 2586eccbc).** `shim_ax.c` stored the `AXVPB`
`priority`, `callback` and `userContext` fields with *native* stores while the game read
them byte-swapped, which made `HSD_SynthSFXUnloadBank_inline` unlink the wrong sfx ids and
crash in `HSD_SynthSFXPlayWithGroup`. Kept here as the canonical worked example of the
class: a wrong native store surfaces later as a garbage pointer, not as an obvious
endianness bug.

**Rule for new shims:** any field a shim writes that the game can read must go through a `gw_*`
accessor. When in doubt, use the accessor - a wrong native store surfaces later as a garbage
pointer, not as an obvious endianness bug.
