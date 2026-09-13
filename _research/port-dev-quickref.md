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
- **No audio backend.** Aurora has no `ax`/`ai`/`dsp`; `shim_ax.c` and the AI entries in `shim_misc.c` are inert (a voice pool exists only so the synth does not crash). Audio is not a flag.
- **Commits:** `git -c user.name='GD' -c user.email='gd@gsd.sh' commit -m "pc: ..."` on `pc-port`. Never `git add -A`. The root repo has 3 pre-existing modified files that must stay uncommitted.
- **Evidence:** each task writes `.omo/evidence/task-<name>.log` with the exact commands and their outputs.
