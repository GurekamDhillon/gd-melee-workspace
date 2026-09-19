# Handoff — Sonic port (m-ex content into the native PC port)

**Written: 2026-09-16.** Supersedes the 2026-09-15 handoff (in git). Stage authoring / Blender-as-
level-editor remains DROPPED.

Read `_research/port-dev-quickref.md` (commands, env vars, traps), `_research/mex-ppc-interpreter.md`
(option B architecture) and `_research/sonic-clone-boot.md` (the fighter plumbing findings) before
touching anything.

---

## 1. Committed baseline (melee fork `pc-port`)

```
b05c5af08 pc: fix the double-jump crash - bound m-ex hook re-entry
64cf61c92 pc: regenerate the m-ex bridge table
108fa831e pc: bridge static-global reads in the interpreter (option B)
b88705b38 pc: wire MoveLogic so Sonic's locomotion is his own (option B)
fc3f5663b pc: close the last bridge gaps; directional specials complete (option B)
0e0171e5b pc: wire onDoubleJump/onUSmash/OnItemPickup; full override set registered (phase 3e)
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
(now **29/29**).

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
- **Sonic's real PPC `ftFunction` RUNS in-game** via the interpreter, through real engine dispatch:
  `onLoad`, `onFrame` (per-frame), `onActionStateChange`, `onReapplyAttr`, `special_hi` (completes),
  and **`MoveLogic`** — his own `MotionState[31]` move table is installed, with **his** anim ids
  (`0x127`). **But see gap 5: that table's callbacks are never actually invoked**, so "his
  locomotion is his own" is NOT supported by any run. The bridge marshals calls, float args (`f1-f8`), and **static globals**
  (game statics live in native memory but their guest addresses fall inside the MEM1 window).
  In-engine tests are at **29/29**.

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

**Known crashes / gaps (verified by playing, not guessed):**
1. ~~Double jump → STACK_OVERFLOW~~ **FIXED (2026-09-19, `b05c5af08`).** The cause was hook
   re-entry, not the interpreter alone: Sonic's `onDoubleJump` override calls `ftCo_800CBAC4`, the
   very engine function whose dispatch site invoked it, so the hook re-triggered itself until the
   native stack was gone. `gw_Mex_GObjDispatch` now skips a hook already on the stack for that
   (event, kind) and runs vanilla instead — the standard detour rule, which covers every registered
   slot. `GW_PPC_MAX_DEPTH` (16) in `gw_ppc_call` is the backstop: at the cap the call is refused
   and the guest chain is logged once, so a new cycle is diagnosable instead of fatal. The same
   change fixed a latent corruption — every `gw_ppc_call` restarted on one fixed guest stack top,
   so a nested run clobbered the interrupted frame; a nested run now continues below the
   interrupted frame's own r1. Regression test: `ppc_reentry_cap`.
2. **Neutral-B (`special_n`) → guest access violation** walking an m-ex item list: an item gobj's
   `user_data` is NULL (`ea=0x00000010`). The m-ex item system / `mexData` item tables are not built
   (the item shims no-op, e.g. `MEX_GetFtItemID → 0`). Root-cause it in the item system, do NOT
   null-guard the guest code.
3. **Guest render/proc callbacks** re-enter fine but hang the render loop without m-ex's
   render-context tables; currently deferred via logged shims.
5. **MoveLogic's callbacks never fire — NEW, and the top open item (2026-09-19).** The table is
   rewritten at install (`interp: MoveLogic table @ guest 0x807F4F34 (31 MotionState entries)`),
   but across 1700+ fighter frames including jumps, double jumps and landings **not one** of the
   four trampolines (`anim`/`input`/`phys`/`coll`) logs an invocation — `gw_mex_move_call`'s
   first-invocation log never appears at all. So Sonic's moveset is still running Fox's state
   callbacks. Start at `gw_mex_movelogic_setup` (`gw_mex_ftfunction_runtime.c`): establish whether
   the engine reads `ftData_CharacterStateTables[33]` for this kind at all, i.e. whether the table
   swap is wired into the lookup the engine actually performs or only written where nothing reads.

4. `special_lw`/`special_s` don't fire in the headless pad-script setup (a pre-existing vanilla
   input-routing asymmetry in `ftCo_Attack100`/`ftCo_SpecialS`), not a bridge gap.

**Honest scope:** this is **not a finished Sonic port**. Assets + code load and many real behaviours
run, and he is controllable with his own locomotion — but gameplay fidelity is **unverified** (no
full-match play test), and the three gaps above are open.

**Bridge maintenance:** `gw_mex_bridge.c` is generated by `tools/mex_port/gen_bridge.py`
(committed as of `32d59c6`; it used to be untracked) and keyed to native VAs;
its `.obj` is compiled by `verify_changed.sh`, **not** by the link step. Correct order after any
pc/platform change: `gen_bridge.py` → `verify_changed.sh pc/` → `build_melee_pc.bat`. A stale bridge
causes non-deterministic garbage-pointer crashes.

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
- **Sonic only exists on the Akaneia disc.** A `MELEE_TARGET_TEST=32` run against the vanilla
  v1.02 ISO boots fine and logs no `interp:` lines at all — it looks like the ftFunction failed to
  install when in fact the character is not on the disc. Use `C:\iso\Akaneia.iso`.
- **A pad script starts consuming frames at the first `PADRead`, during boot.** The match only
  begins ~2400 log lines in, so a short burst (the old `_build/pad_dj.txt`, 562 frames) is fully
  spent on the boot sequence and the fighter never sees an input — which reads as "the bug is
  gone". Repeat the cycle well past match start; `_build/pad_dj_repeat.txt` (8160 frames) does.
- **Never pipe a `clang.exe` invocation through `head`.** The early pipe close kills clang
  mid-write and you get a *missing* `.obj` plus a confusing `LNK1181` on the next link.
- **`vswhere.exe is not recognized`** from `build_melee_pc.bat` is benign noise from `vcvarsall`;
  the signal is still `MELEE_PC_LINK_OK` on the last line.

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
