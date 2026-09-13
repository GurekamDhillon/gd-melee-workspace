# Port dev quick-reference (agents: READ THIS FIRST)

Workspace root: `C:\gdm` = `/mnt/c/gdm` = `/mnt/c/Users/Gurek/Desktop/GD's Melee` (a junction; same tree).
Game repo: `C:\gdm\melee` (branch `pc-port`). Build dir: `C:\gdm\_build`. Docs: `_research/`, `HANDOFF.md`.
Commands digest: `HANDOFF.md` §4. Boot gates / SDK notes: `_research/melee-boot.md`. Invariants: `_research/console-invariants.md`.

## Toolchain
- Clang: `/mnt/c/gdm/_toolchains/llvm/bin/clang.exe` (a Windows binary; run it directly from WSL, `--target=i686-pc-windows-msvc`).
- Windows-side steps run via `cmd.exe` from WSL. Visual Studio Build Tools supply `vcvarsall` for the link step.

## Rebuild a platform shim (`melee/pc/platform/<shim>.c`)
```
C:/gdm/_toolchains/llvm/bin/clang.exe --target=i686-pc-windows-msvc -c -O2 -DTARGET_PC \
  -I C:/gdm/melee/extern/aurora/include -I C:/gdm/melee/pc/platform \
  C:/gdm/melee/pc/platform/<shim>.c -o C:/gdm/_build/masstest/shimobj/<shim>.obj
```

## Rebuild one game TU (`melee/src/**.c`) - use the pipe script, NOT raw clang
```
cd /mnt/c/gdm/melee && bash /mnt/c/gdm/_build/masstest/pipe_wsl.sh <src path>   # e.g. src/melee/lb/lbarq.c
# Git Bash alternative: pipe_win.sh <path>
```
Game TUs go clang (PPC frontend) -> gwtool -> `.obj`. Compiling a game TU directly with the Windows clang produces a wrong object; always use the pipe.

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
cd /mnt/c/gdm/_build && timeout 45s ./melee-pc.exe --iso 'C:\Users\Gurek\Downloads\Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso'
```
- Before every run: `cmd.exe /c "tasklist | findstr /i melee-pc"` and wait until none. Two concurrent instances kill each other's runs.
- DO NOT take or capture screenshots. DO NOT build any input-injection (keybd_event/SendKeys) or capture harness. Interactive steps (navigating menus, pressing buttons) and all visual checks are performed by the human user - ASK them via the orchestrator instead of building tooling to do it. The human supplies the reproduction (they can drive the game and hand you the log).
- `_build/melee-pc.log` is truncated on every run: copy it into `.omo/evidence/` immediately after a run.
- Never redirect stdout into `melee-pc.log` (two writers).

## Resolve an rva/crash address to a symbol (needs Git Bash gawk; WSL mawk fails)
```
"/mnt/c/Program Files/Git/bin/bash.exe" -lc 'bash /c/gdm/_build/masstest/mapsym.sh 0x10355E93'
```

## Conventions that have bitten workers
- **Big-endian game memory.** Native shims must read/write game-visible scalars with `gw_r32`/`gw_w32` (and `gw_r16`/`gw_w16`, `gw_rf32`/`gw_wf32`). A native little-endian store the game then byte-swaps reads back wrong (e.g. `AXVPB.index`).
- **Shim boundary.** A shim defines `gw_X`; the pipe/gwtool prefixes *every* symbol in a game TU with `gw_`, so game code must call the **unprefixed** `X`. Declare `extern void wait_idle(void);` and call `wait_idle()` under `TARGET_PC` - NOT `gw_wait_idle`, which double-prefixes to `gw_gw_wait_idle` and fails to link (this exact mistake cost a link cycle).
- **Deferred completions.** ARQ and DVD completions are queued via `gw_defer` and pumped only in `gw_wait_idle`/`gw_frame_tick`. Any game-side blocking spin that calls no shim deadlocks; fix it by pumping `gw_wait_idle()` inside the spin (TARGET_PC-guarded). Precedents: the pad gate (`shim_dvd.c` `gw_DVDGetDriveStatus` -> `gw_wait_idle`), `lbarq.c` ARQ wait, and `synth.c` deflag sync (see `shim_ar.c:12-14`).
- **Game-source changes** must be `#if defined(TARGET_PC)`-guarded with the original code kept.
- **Audio backend exists** (added 2026-09-12/13). Aurora has no `ax`/`ai`/`dsp`, so `shim_ax.c` implements AX (DSP-ADPCM decode + 64-voice mixer over `gw_aram`) and the AI entries in `shim_misc.c` drive a SDL3 32 kHz stereo output; `HSD_SynthCallback` is pumped per frame from `gw_frame_tick`. Verified audible - audio is not inert.
- **Commits:** `git -c user.name='GD' -c user.email='gd@gsd.sh' commit -m "pc: ..."` on `pc-port`. Never `git add -A`. The root repo has 3 pre-existing modified files that must stay uncommitted.
- **Evidence:** each task writes `.omo/evidence/task-<name>.log` with the exact commands and their outputs.

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

**Swap-site inventory (2026-09-13).** Shims: `shim_card` 40, `shim_ax` 23, `shim_gx` 23,
`shim_dvd` 7, `gw_runtime` 6, `shim_pad` 5, `shim_ar` 4, `shim_libc` 2, `shim_os` 2, `gc_adapter` 1.
Game `src/`: 0 (by construction).

**Known boundary violation (candidate root cause of the attract SFX crash).**
`shim_ax.c:503-505,530` store `priority`, `callback`, `userContext` into the game's `AXVPB` with
*native* stores. The game never writes `vpb->priority` itself - it only reads it (`synth.c:298,400`)
and passes it back through `AXAcquireVoice`/`AXSetVoicePriority` - so through gwtool it reads a
byte-swapped count, and `HSD_SynthSFXUnloadBank_inline` (`synth.c:295`) unlinks the wrong sfx ids,
leaving dangling `HSD_Synth_804C29E0` bucket nodes that `HSD_SynthSFXPlayWithGroup` then walks
(crash at `1035469D`/`103546CD`). Fix = store those three `AXVPB` fields with `gw_w32` after
confirming who reads `callback`/`userContext`.

**Rule for new shims:** any field a shim writes that the game can read must go through a `gw_*`
accessor. When in doubt, use the accessor - a wrong native store surfaces later as a garbage
pointer, not as an obvious endianness bug.
