# Handoff — Sonic port (m-ex content into the native PC port)

**Written: 2026-09-16.** Supersedes the 2026-09-15 handoff (in git). Stage authoring / Blender-as-
level-editor remains DROPPED.

Read `_research/port-dev-quickref.md` (commands, env vars, traps), `_research/mex-ppc-interpreter.md`
(option B architecture) and `_research/sonic-clone-boot.md` (the fighter plumbing findings) before
touching anything.

---

## 1. Committed baseline (melee fork `pc-port`)

```
8ca550072 pc: load Sonic's real data (model, costumes, anims); behaviour still Fox
9de877025 pc: render Sonic's model - fix Aurora's indexed-draw buffer growth
9a3922df1 pc: grow heap 3 for the Akaneia item archive (fixes the match-setup OOM)
4a417fe9f pc: add an m-ex ftFunction blob loader (option B, phase 2)
6ca8fa92b pc: boot the new Ft_Kind_Sonic slot in Target Test (fox-clone renders)
dee0280e5 pc: add a PowerPC interpreter core and its end-to-end test (option B, phase 1)
0c41100eb pc: add an internal Ft_Kind_Sonic slot as a pure Fox clone
```

Root repo: `1097b20` (B design doc), `24dc590`/`d374ee3`/`ba29781` (handoff, extractor, ignores).
Verified at each commit: `verify_changed.sh` 0 failures both modes; `MELEE_PC_LINK_OK`; tests green
(now **21/21**).

## 2. What WORKS now

- **The Akaneia ISO boots a match** (`MELEE_TARGET_TEST=32`). The match-setup OOM was `IfAll.usd`
  growing ~55 KB on Akaneia (custom items) overflowing heap 3; heap 3 grown 128 KB (donated from
  the main heap).
- **Sonic's real model renders in-game**: `PlSn.dat`/`ftDataSonic`, `PlSnNr.dat` /
  `PlySonic5K_Share_joint`, 7 costumes. Screenshot: `.omo/evidence/sonic-renders.png`.
- **PPC interpreter core** (`pc/platform/gw_ppc.{h,c}`) — big-endian guest fetch/execute, bridge
  seam, reentrant; test green.
- **ftFunction blob loader** (`pc/platform/gw_mex_ftfunction.{h,c}`) — loads `PlSn.dat`'s
  `ftFunction`, relocates it, resolves **25 overrides**, surfaces the func-address case; tests green
  on both discs.
- **Aurora patch** (`extern/aurora/lib/gx/command_processor.cpp`): geometric growth of the indexed
  draw buffer (m-ex models push per-triangle indexed draws; the old exact-size re-upload was O(n²)
  and overflowed the 8 MiB staging buffer → `abort()`).

## 3. What is NOT done — the remaining work

**Sonic's BEHAVIOUR is still Fox's.** Running his real moveset is option B phase 3: install the
interpreted `ftFunction` overrides into the engine dispatch so the game calls the PPC. Checklist
(from the phase-2 report):
1. heap-allocate the interpreted code (not the test's fixed pin);
2. build the guest→native bridge table (`melee/config/GALE01/symbols.txt` × `melee-pc.map`) —
   **a partial, 658 KB `pc/platform/gw_mex_bridge.c` + `gw_mex_ftfunction_runtime.c` exist but were
   NEVER wired into the build or verified** (a prior agent stalled); judge whether to reuse them;
3. install overrides into dispatch (11 existing `gw_Mex_GObjDispatch` events + MoveLogic, the 8
   specials, onActionStateChange, onReapplyAttr, onDoubleJump, onUSmash) — only the slots this
   fighter's functionRelocTable overrides;
4. re-express the func-address reloc case as a native hook;
5. marshal float args/returns + struct/sret across the bridge;
6. set r2 to the guest mexData base and populate the `OFST_*` slots the blob reads.

Phase 3 is being attempted in a narrow form first (prove ONE override — `onLoad` — runs in-game,
with log proof) before doing all 25. If that has not landed, resume there; the narrow proof is the
gate.

## 4. Traps (still true, each cost time)

- **`pipe_wsl.sh` `$?` is meaningless** — the signal is `CC_FAIL`/`GW_FAIL` in the *text*. Treat
  green as untrusted until falsified.
- **Agents stall and write nothing.** Two subagents did; the fix is a hard "write each file to disk
  before moving on, build/verify incrementally" instruction. Check the working tree, not the story.
- **A new kind index is outside EVERY vanilla-sized per-kind structure.** Two classes: C tables
  (`[Ft_Kind_Max]`) and **disc-loaded** tables inside `PlCo.dat` (`ftPartsTable`, `Fighter_804D6540`,
  widened by `ftCommonData_ExtendKindTable`), plus the **figatree-kind bits** packed MSB-first in
  `x10_animCurrFlags` (low 6 bits) — Fox's data says kind 1, the port's kind is 33, so they must be
  rewritten (`ftData_8008572C`). Expect more of these when behaviour is wired.
- **A `/GS`-looking crash may be `abort()`.** `0xC0000409` here was `ByteBuffer::resize`'s
  `if (!m_owned) abort()`, not a stack cookie — override `__security_check_cookie` to tell them apart.
- **Memory budget**: the card and the match setup both allocate from `memp`; heap sizes live in
  `lbHeap_803BA380[]` (`src/melee/lb/lbheap.c`, TARGET_PC block). Changing a size value is
  layout-safe; the total must fit MEM1.
- **Build races**: never run two agents that build+link concurrently (they clobber `melee-pc.exe`).
- **`C:\gdm` is a junction to the repo root**; launch env vars must be `export`ed and in `WSLENV`.
  `MELEE_WINDOW_HIDE` does not work — park off-screen with `MELEE_WINDOW_X/Y=30000`.
- Resolve crash RVAs with the quickref's `mapsym.sh` via Git Bash.

## 5. Conventions

- Game-source changes `#if defined(TARGET_PC)`-guarded, original under `#else`.
- Native platform shims (`pc/platform/*.c`) are compiled directly and listed in
  `_build/melee_link_objects.rsp` (outside version control) — **not** in `files.txt` (which is only
  for PPC→x86 pipe TUs).
- **m-ex has NO LICENCE** — specification only; reimplement in original C; never vendor/copy its
  `.asm`/`.h`/`.dat`.
- `GIT_MASTER=1`; per-command `-c user.name="GD" -c user.email="gd@gsd.sh"`; melee subjects `pc:`,
  root `docs:`/`build:`/`tools:`. **Never `git add -A`.**

## 6. Not proven

- Sonic's real moveset (phase 3). Sonic currently renders with Fox's behaviour.
- The other ~45 of the 49 m-ex flags (unchanged).
- The partial `gw_mex_bridge.c` is unverified and not linked.
