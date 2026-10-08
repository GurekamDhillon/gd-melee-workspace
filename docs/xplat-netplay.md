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

## Different discs (0.2.2-test1: the DESYNC at frame 5212)

Written 2026-10-08 (lanes `desync-0221`: game `agent/desync-0221`, workspace `ws/desync-0221`). This section wins over the
statement in `gw_mexid.h` (before this lane) that two installs may differ in PlCo.dat and still play.

A Windows (VANILLA NTSC 1.02 disc) against Linux (SSBM ACE Build v2.0.0) match on build `e0a6f1a267791af8` desynced at frame 5212
(`netplay: DESYNC at frame 5212 - local checksum BED3F4B9, peer 0DCAAA05`). The handshake had accepted it: it compares the build id, the
protocol, the match rules and one "global game data" hash (`plco#`, `itco#`, `mexflags#`), and all three printed the same on both
sides (`plco#56f8,itco#ed4f,mexflags#b266`). The same two machines on the same (vanilla) disc played 4,950 frames, 7 rollbacks, 0 desyncs.

**Cause.** PlCo.dat of the ACE disc is not the vanilla file. `mx_plco()` hashed only the 21 shallow global tables at their retail sizes
and treated pointer words as markers, so ACE's file (155,693 bytes against 149,101: appended rows, and vanilla data moved or changed)
hashed like the vanilla one. Measured, one Windows exe, `tools/xplat/disc_pair.py`, `mode=vs;at=match;p1=falco/c0/hu/stocks99;
p2=sheik/c0/hu/stocks99;stage=fd;time=0`, seed 777, 6000 frames:

| run | rb (the netplay checksum) |
|---|---|
| vanilla disc against ACE disc | identical for frames 0-5243, differs from 5244 (`5D935CC9` v `7B26BF6F`) |
| vanilla disc against vanilla disc + ACE's PlCo.dat mounted as a loose mod | the same: first difference 5244, the same two values |
| vanilla disc against vanilla disc + vanilla PlCo.dat padded to ACE's size (header size patched) | identical for all 6001 frames |
| vanilla disc against the same disc with a 16:9 window, widescreen on, render scale 3 | identical for all 6001 frames |

So it is PlCo.dat's content, not the heap layout and not the window. The first visible difference is a fighter's joint pose on the first
frame of a new animation (Falco's `anim 0x107` at frame 3560, Sheik's `anim 0x109` at 5218); the hashed fields (position, motion, action
frame) agree until the changed pose reaches them (26 frames after 5218). Which PlCo field does it was not pinned down: the objects reachable
from `ftLoadCommonData` agree on their common prefix, and a word-level diff of the two files is 157 insert/delete hunks (144 inserts of
zero rows, 11 deletions of vanilla data that ACE moved or dropped, 2 replacements).

**Fix** (game commit `051018c8b`): the global `plco` component also hashes the whole PlCo.dat file. A vanilla and an ACE install now
refuse each other at the handshake with `different global game data; host has: plco#4748,...` and, on the guest, `game data differs from the
host's: PlCo.dat (common fighter data: a different disc or mod pack)`; two Windows clients on loopback: vanilla host + ACE guest refused,
vanilla + vanilla connects. The cost is that a mod pack that edits PlCo.dat can no longer play a vanilla install (the pack tool says ACE and
Akaneia both modify it); equal PlCo.dat files still play, whatever else differs. MxDt.dat (the m-ex tables) is not in the hash; no
experiment here shows it matters for the fighters and stages two installs have in common, but none shows it does not.

**Mods hash.** The log line `mods: envoy#xxxx,...` (`gw_Mods_Describe`) is a digest of every mod file's path and size. It is informational:
the handshake does not compare it (`cfg.mods_hash` is the global game data XOR the hashes of gameplay scripts that are `rollback_safe`,
none of the shipped ones is), because Lua mods cannot write the simulation online and everything that can (disc files, Geno overlays) goes through
the identities and the global hash. The Windows and Linux packages of one commit showed different digests (`envoy#2d54` v `envoy#ad28`)
only because the Windows package is checked out with CRLF line ends in its text files (119 of 303 files differ in size; the Linux one is
LF). `shim_dvd.c gw_mod_fingerprint_size` now leaves the CR of CR LF out of the size of a text file (`.lua .json .md .txt .wgsl .csv ...`),
so both print `envoy#ad28,envoy_drives#d154,geno-lab#bfa4`.

**Window and widescreen are not simulation inputs** (the 16:9 row above), so two players with different window shapes do not diverge for
that reason. The laptop ran the match at aspect 1.6 and Windows at 1.333.

## Tools

| | |
|---|---|
| `tools/xplat/pair.py NAME FRAMES SEED "SCENE"` | one scripted match on both builds in parallel, digests compared |
| `tools/xplat/matrix.py` | the scenario list (fighters, stages, items, 4 players, Turbo on/off, ACE, Akaneia m-ex) |
| `tools/xplat/net_pair.py NAME --mode direct|random --host win|linux` | a real netplay session between the two builds, local matchmaking server for `random` |
| `tools/xplat/envoy_set.py` | the Envoy set driver. Its input scripts `tools/xplat/envoy/en_host.lua` / `en_guest.lua` walk the Atlas menu (main menu > ONLINE, hover 68); the host logs `ROOMCODE <code>`, the guest is launched after that with `MELEE_LAB_ROOM=<code>` and joins that room by code (`gd.lab_env("ROOM")` + `gd.netplay_act("code", ...)`), never random matchmaking. Rules are the lobby's defaults (4 stocks, 8 min): the old Stocks 1 / Time 1 menu presses are gone (no Lua setter yet) |
| `tools/xplat/build_both.sh` | build the lane's Windows exe and Linux ELF |
| `tools/xplat/disc_pair.py NAME FRAMES SEED "SCENE" --package DIR [--a vanilla --b ace] [--mods-a DIR --mods-b DIR]` | two scripted matches on one Windows build that differ in disc and/or loose mods, `rb` compared: "can these two installs play each other?" |
| `tools/xplat/vm/` | a Linux 6.12 VM (QEMU/KVM in WSL) that runs the real Linux game with the userfaultfd write-watch, `MELEE_SNAP_VERIFY=1` and a fake-network rollback session |

Linux build used `~/lb2/{mD,wsD,outD,gwtoolD}` and `~/lb2/enterD.sh` (the rootfs with WSLg and the GPU nodes).
Headless turbo on Linux needs `SDL_VIDEODRIVER=x11`: under Wayland the hidden window never presents and the
GX fifo grows until a 32-bit allocation fails.
