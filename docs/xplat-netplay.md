# Windows and Linux builds playing each other (0.2.0)

Written 2026-10-07 (lane `xplat-netplay`: game branch `agent/xplat-netplay`, workspace branch `ws/xplat-netplay`).
Netplay protocol is still **5**; no packet changed.

## What was wrong

The handshake compared `np_exe_hash()`, a hash of the executable FILE. A PE and an ELF always differ, so
a Windows and a Linux build of one commit refused each other ("different melee-pc.exe build").
Behind that sat the real question: do the two builds compute the same game? They did not, in four
small ways (all found by comparing per-frame state digests of the same scripted match, below).

## The build identity (what the handshake compares now)

`np_build_id()` in `pc/platform/gw_netplay.c`, carried in the same field the exe hash used:

    build id = FNV( sources , numerics )

* **sources**: `tools/port/build_id.py` hashes every simulation-relevant text file of the game checkout
  (`src/ include/ libs/ pc/`, minus docs, tests, old pipeline scripts, the generated m-ex bridge and the
  header itself; gwtool's source is kept) with CRLF normalised, reading the WORKING TREE
  (`git ls-files --cached --others --exclude-standard`). It writes `pc/platform/gw_build_id.h`
  (git-ignored) when the digest changes; `build.sh` and `build_linux.sh` run it first. Same bytes give the
  same digest on any platform and any checkout; a modified or added source changes it.
* **numerics**: measured at run time. The game's own math (sinf cosf tanf atan2f atanf acosf asinf expf powf,
  the Gekko `frsqrte`/`fres`), the shims' `sqrtf` and `GXProject`, and the libm calls game code reaches
  (`fma`, `fmodf`) run on 1,536 fixed inputs and their results are hashed. A build whose floating
  point rounds differently (x87 instead of SSE, another libm) gets another id and is refused at the
  handshake instead of desyncing mid-match. The log line shows both halves:
  `netplay: build id ... = sources ... (<commit>, N files, GWBUILDID:...) + numerics ...`.
* `check_build_id.py` (run at the end of both build scripts) greps the linked exe for `GWBUILDID:<hash>`
  and stops the build if the object was compiled without the current header (it found one such stale
  object during this work). A build with no header falls back to the whole-file hash.

Refusal text is now "different game build (host X, you Y): the sources or the floating-point results differ".

## Determinism: what was different, and the fixes

Method (`tools/xplat/`): the same seeded pseudo-random input (`det_input.lua`, 1-4 pads) drives a match on
the Windows build and the Linux build (WSL, Ubuntu 22.04 rootfs, WSLg), `MELEE_XHASH_LOG` writes per frame
`rb` (RB_GameHash, the netcode's checksum), `wide` (every fighter's and item's whole struct, GObj and joint
tree, heap addresses and audio ids masked), and `mem`/`glob` (all of MEM1 and the game globals with
image pointers masked); `cmp_xhash.py` finds the first divergent column/frame, `MELEE_XHASH_DUMP_FRAMES` +
`xhash_diff.py` name the words. `matrix.py` runs the scenario list.

Four real differences, found in this order, all fixed:

1. **Linux native shims were compiled for x87.** `clang -m32` is the i386 triple with the i686 CPU: float
   arithmetic on the x87 stack at extended precision. Windows shims (`--target=i686-pc-windows-msvc`) and
   all game TUs (gwtool) use SSE2. Fix: `-msse2 -mfpmath=sse` in `tools/port/shim_linux.sh`.
2. **x87 control word**: Windows threads start at 0x027F (53-bit), Linux at 0x037F. Fix: a constructor in
   `gw_compat_linux.c` sets 0x027F.
3. **`GXProject` ran inside Aurora**, which the Linux build compiles for x87 too. Its result feeds
   `Camera_LogicToScreen` (the fighters' off-screen flag). Fix: `gw_GXProject` computes it in the shim with
   Aurora's expressions, contraction off. The Windows `mem` digest is bit-identical before and after, so
   Windows behaviour (replays, savestates) is unchanged.
4. Diagnostics only: fighter/item sound-voice ids, a joint's id key (a native stack address) and
   item kind-specific unions that hold sound handles differ by platform and are not simulation state; the
   `wide` digest leaves them out.

Windows is unchanged: a Windows build from before these changes and the new one print identical
`DET:` state lines (positions, percent, stocks, action) for 6000-frame matches.

Residual MEM1 differences between the platforms (about 400 words of ~10.5 M, checked by dumps): the audio
engine's voice blocks, OS thread control blocks (native stack pointers, queue links) and sound handles.
Globals: only pad, render-owned and menu symbols (the classes SyncTest already excludes).

## Tools

| | |
|---|---|
| `tools/xplat/pair.py NAME FRAMES SEED "SCENE"` | one scripted match on both builds in parallel, digests compared |
| `tools/xplat/matrix.py` | the scenario list (fighters, stages, items, 4 players, Turbo on/off, ACE, Akaneia m-ex) |
| `tools/xplat/net_pair.py NAME --mode direct|random --host win|linux` | a real netplay session between the two builds, local matchmaking server for `random` |
| `tools/xplat/envoy_set.py` | the Envoy set driver. Its input scripts `tools/xplat/envoy/en_host.lua` / `en_guest.lua` walk the Atlas menu (main menu > ONLINE, hover 68); the host logs `ROOMCODE <code>`, the guest is launched after that with `MELEE_LAB_ROOM=<code>` and joins that room by code (`gd.lab_env("ROOM")` + `gd.netplay_act("code", ...)`), never random matchmaking. Rules are the lobby's defaults (4 stocks, 8 min): the old Stocks 1 / Time 1 menu presses are gone (no Lua setter yet) |
| `tools/xplat/build_both.sh` | build the lane's Windows exe and Linux ELF |

Linux build used `~/lb2/{mD,wsD,outD,gwtoolD}` and `~/lb2/enterD.sh` (the rootfs with WSLg and the GPU nodes).
Headless turbo on Linux needs `SDL_VIDEODRIVER=x11`: under Wayland the hidden window never presents and the
GX fifo grows until a 32-bit allocation fails.
