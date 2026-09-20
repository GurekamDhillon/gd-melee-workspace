# Handoff — m-ex content in the native PC port

**Written: 2026-09-19 (late evening).** Supersedes the earlier 2026-09-19 handoffs, in git
history.
Stage authoring / Blender-as-level-editor remains DROPPED.

Read `_research/port-dev-quickref.md` (commands, env vars, traps) first — it now documents the
build/run scripts and the parallel-agent setup, and those supersede the raw command lines. The
m-ex research: `mex-ppc-interpreter.md` (architecture), `mex-data-layer-design.md` +
`mex-dump-tools.md` (mexData/MxDt.dat), `mex-item-spawn.md` (itFunction, custom items),
`akaneia-dependency-scope.md`, `bridge-signatures.md`, `mex-css.md`, `mex-sound-banks.md`,
`rollback-netcode.md`.

---

## 0. FIRST ACTION ON RESUME

**Everything is committed and the tree is green: tests 39/39 on both vanilla and Akaneia.**
Nothing is blocking. The five-agent fan-out has been run, reported and MERGED.

The first action is a **windowed run**, because a pile of work is now code-complete and
screen-unverified. In this order, each on Akaneia:

1. **Meta Crystal** — external stage 293 / internal 76. The first m-ex custom stage; it has never
   executed. Expect `grfunction:` lines naming the install and each overridden `StageData` word.
2. **Charizard** (`MELEE_TRAINING=35`) — the cheapest Akaneia fighter, zero known gaps. Then Wolf
   (33) and **Dedede (38)**, the one whose `onLoad` crashed and is now fixed.
3. **CSS cursor scale** — a 5% shrink plus a sub-pixel nudge; only eyes can confirm it.
4. **An item throw/catch as Sonic** — slots 16/17/18 are newly wired. The log should show
   `interp: onItemRelease/onItemCatch/onItemDrop ... invocation 1 running`.

Sonic's spring (up-B, custom item 277) is **user-verified** as of this handoff.

## 1. State in one paragraph

**The m-ex fighter path is table-driven, the stage path now exists alongside it, and all five
agent branches are merged into `pc-port`.** Sonic is not special-cased anywhere: port kind 37 /
m-ex internal 31, loaded purely from `MxDt.dat` rows, spring verified in a real match. Merged this
session: m-ex custom **stages** (`gw_mex_grfunction.[ch]`, Meta Crystal wired end to end), item
slots 16/17/18, per-fighter BGM and the weighted menu playlist, CSS cursor scaling, **conditional
hook registration**, m-ex's `calloc` and five more resolver gaps, and the `anim_num` stride fix.
Rollback has a concrete port-specific design (`_research/rollback-port-design.md`, on
`agent/rollback`): 11.75 MB snapshot, ~535 us each way, 3.2% of a frame.

Three findings from this session are worth carrying forward as *lessons*, not just fixes:

- **Registering a hook unconditionally is not conservative.** A registered hook REPLACES the
  vanilla callback, so registering every slot for every fighter silently turned engine behaviour
  into a no-op wherever a blob leaves a slot empty. Sonic fills all of them, which is why it hid.
  Lucas was losing his per-frame callback outright.
- **A count that is not in the fighter's own data is probably the wrong count.** `anim_num` is
  stride 8, was read at stride 4, and every Akaneia fighter had a wrong animation bound - three of
  them read 0. Same shape as the demo-motion crash the morning before.
- **Platform statics outlive MEM1.** The test harness restores a MEM1 snapshot between tests but
  not platform statics, so any cached guest pointer names wiped memory. See §6.

### Known gaps, largest first

1. **Kirby hats** — `Mex_FtBaseKind` falls back to Mario for six of the seven Akaneia fighters, so
   Kirby swallowing Wolf gets Mario's cap and fireball. Akaneia ships all seven `PlKbCp*.dat` and
   every file is on the disc; the fix is to read `MexData.kirby_data.capfiles[k]`/`effectids[k]`
   per internal kind instead of copying the base. Not started.
2. **Category-2 hook slots** — 26 `onModelRender`, 33 `onZair`, 34 `onLanding`, 35 `onFSmash`, 41
   `onIntroL`, 43 `onTaunt`, 44 `onCatch` have no vanilla per-kind table, so each needs a new
   dispatch site in engine source (pattern: `ftCo_JumpAerial.c:147`, `ftCo_AttackHi4.c:94`).
   Tails needs 26/34; Lucas needs 33/35/41/43/44. Every install now LOGS the ones it is missing.
3. **SSS expansion** — until it lands, a custom stage is only reachable programmatically. Fully
   characterised: stride 0x20 vs the port's 0x1C, external id moves from a `u8` to an `s32` at
   `+0x1C`, `NUM_STAGES` 29 -> 66.
4. **Stage audio** — `s32_arr_803BB6B0[71..95]` needs filling, AND `lbAudioAx_80026EBC` does
   `1ULL << ssm_id` where the added stages' ids are 56..77. Undefined; the bank never loads. The
   fighter side already hit this and uses a by-index request path.
5. **ACE** — 31 fighters fit `GW_MEX_SLOTS` exactly, zero spare, and **31 is a hard ceiling**:
   a FighterKind must fit `Fighter.x597_bits : 6`. A 32nd needs that field widened first, not just
   the four constants. 16 of ACE's 31 blobs have `codeSize == 0` (built by an older MexTK) and the
   loader rejects them outright - recoverable from the instruction-reloc table's max offset.
   ACE's ISO is at `C:/iso/SSBM ACE Build v2.0.0.iso`.
6. **Trophies** — NOT data plumbing. 34 m-ex patches, a save-data-format change plus a menu-scene
   rewrite. Wants its own task.
7. Bridge gaps recorded, not fixed: float varargs (`HSD_ForeachAnim`), double args, struct returns.
8. `gw_ppc_static_native` gates its bridge lookup at `0x80300000` but the main heap starts near
   `0x806A0000`, so every interpreted access to a fighter struct pays a ~15-probe binary search
   (8.6 ns). Raising the gate would speed up all m-ex content.

## 2. How to run it

Use the scripts; they encode the traps.

```
bash C:/gdm/tools/port/build.sh --tu src/melee/ft/ftdata.c --shim shim_dvd.c
bash C:/gdm/tools/port/run.sh sonic --iso C:/iso/Akaneia.iso
bash C:/gdm/tools/port/run.sh --test t --iso "C:/iso/Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso"
```

`build.sh` does compile → link → **regenerate `gw_mex_bridge.c`** → compile it → link again, and
then proves the bridge is a fixpoint. `run.sh` runs a *copy* of the exe in `_build/runs/<name>/`,
so logs/crashlogs/card/mods never collide and a running game can never block the next link.

Launch visibly on the main desktop — the user wants to watch. Pad scripts live in `_build/pad_*.txt`
and `run.sh` resolves a bare name against that directory. They start consuming frames at the first
`PADRead`, during boot, so a short burst never reaches the match; use a repeating one.

Useful env: `MELEE_TRAINING=37` (Sonic), `MELEE_TARGET_TEST=32`, `MELEE_MODS=0/1`,
`MELEE_DVD_TRACE`, `MELEE_HEAP_TRACE`, `MELEE_MEX_TRACE_CALLS`, `MELEE_MEX_DUMP_CODE=<path>`,
`MELEE_MEX_TRACE_PARTS`, `MELEE_MEX_TRACE_SCALE`, `MELEE_PPC_TRACE_FP`.

**The fighter kind numbers**, confirmed in-engine: Wolf 33, Diddy 34, Charizard 35, Lucas 36,
**Sonic 37**, Dedede 38, Tails 39, from m-ex internal **27–33**. `MELEE_TRAINING=38` was Sonic
only while he was the sole registered slot; with all 7 registered it is Dedede, and the stale
number cost one play-test that loaded Dedede and crashed.

## 3. What changed since the last handoff

**Generalization (#21).** `gw_mex_ftfunction_runtime.c` went from one global Sonic state to
`gw_mex_kinds[31]`, selected per fighter by `gw_Mex_SelectKind`/`RestoreKind` around every hook.
A dense slot table skips MxDt rows whose `Pl` file is not on the disc. `ftdata.c`'s
`ftData_MexInitKinds()` fills 26 callback slots per kind with a clone-base fallback, plus file,
anim, costume and demo data. `Ft_Kind_Mex0` = 0x21, `ChKind_Mex0` = 0x22, 31 slots each.

**The spring crash, fixed this evening.** Sonic's up-B faulted in `HSD_JObjAddAnim` reading
`0x0000002D`. Cause: the demo-motion flag rewrite in `ftdata.c` looped over the *clone base's*
count (16) while Sonic's `fd->x14` really has 14 entries, writing the fighter kind (37 = `0x25`)
past the end at a 0x18 stride — straight into the spring article's `ItemStateArray`, whose zeroed
`anim_joint` became `0x25` (`0x25 + 8` = the faulting address). Proven by diffing runtime memory
against `PlSn.dat`'s relocation table: those words are `0` on disc.

Nothing gives that table's length — `ftData_UnkIntPairs[kind].count` is the base's and `MxDt.dat`
has no equivalent — so the loop now trusts the data: every real motion has a subaction script, so
it stops at the first entry with `xC == NULL` (and never leaves the archive), then corrects the
stored count. It reports 14, matching the disc.

Worth knowing: the first version of that guard keyed on the authored kind bits, assuming they hold
m-ex's internal id. They are **0** in this data, so it found 0 entries and would have silently
re-broken the results screen. Dump the disc before trusting a discriminator.

## 4. Open work

The big items are §1's "Known gaps". Smaller ones, none blocking:

1. **Stale Sonic-specific comments** in `gw_mex_ftfunction_runtime.c` and `ftdata.h:77` — the
   code is generic now, the prose still says "Sonic".
2. **Temporary debug traces** in the runtime can go once the other fighters are in.
3. **CSS icon blink is DONE** — it needed nothing. Every icon-joint site already goes through
   `MNCS_ICON_ROOT()` and `MNCS_NUM_SK` is already dynamic. The old open-work entry was wrong.
4. **`item.RuntimeIndex`'s zero run** is 49 entries for Akaneia but would need 120 for ACE
   (custom article ItemKinds run 253..356 there vs 253..285). Nothing hardcodes 49 today; check
   when ACE articles get wired.
5. **`css_icon_count` is 56 against 65 external ids** on ACE, so the CSS does not show
   everything. Do not assume a 1:1 mapping.

## 5. Parallel agents — the mechanism, and what the fan-out produced

### The mechanism

```
bash C:/gdm/tools/port/agent_new.sh <name>        # worktree + build root, objects hardlinked
export GW_MELEE=C:/gdm/worktrees/<name>
export GW_BUILD_ROOT=C:/gdm/_build/agents/<name>
```

`GW_BUILD_ROOT` holds that agent's objects, link response file and `melee-pc.exe`. Shared and
read-only: the Aurora/Dawn/SDL3 libraries in `_build/ax86m` (the link always runs there because
`melee_link_libs.rsp` names them relative to it — only the outputs move) and the ISOs.
`agent_rm.sh <name>` cleans up, refuses on uncommitted work, and never deletes the branch.

`--test` is headless and parallelises freely. **Gameplay runs open a window and share one audio
device, so keep them serial** — give agents an explicit instruction not to launch one, or several
will fight over the screen.

**The isolation had a hole and it is now fixed** — see §6's hardlink entry. Any new tool that
writes into `$GW_OUT` must write-then-rename, not write in place.

### What the five agents produced (all merged into `pc-port`)

| agent | outcome |
|---|---|
| `fighters-akaneia` | Dedede's `onLoad` crash fixed (m-ex `calloc` at `0x803D706C`), 5 more resolver gaps, **conditional hook registration**, slots 12/19/20, a headless test that walks every blob's absolute branches. Kirby hats identified, not started. |
| `fighters-ace` | Research only. The reconciled 31-fighter list, the `x597_bits` ceiling, the `codeSize == 0` blocker, and the `anim_num` stride bug — which turned out to be live and wrong for every fighter. |
| `stages` | `gw_mex_grfunction.[ch]`, the stage tables, Meta Crystal wired end to end. The key finding: `mexData.stage_desc` is byte-for-byte the port's own `StageData`, and stages have only TWO index spaces. |
| `content` | Item slots 16/17/18, per-fighter BGM, menu playlist, CSS cursor scale. Two negatives worth as much: icon blink needed nothing, trophies are not cheap. |
| `rollback` | `_research/rollback-port-design.md` on `agent/rollback`. Design only. |

**The merge order that worked:** `stages` (clean), `content` (clean), `fighters-akaneia` (one real
conflict), then regenerate the bridge once from the merged link. Each agent's regenerated
`gw_mex_bridge.c` is merge noise — keep one side, regenerate at the end.

**The conflict worth remembering:** `content` added three unconditional item-slot registrations to
the same block `fighters-akaneia` was rewriting to be conditional. Both sides merged cleanly if
taken verbatim, and doing so would have silently reintroduced the exact bug on three fresh slots.
The resolution was to fold content's three into akaneia's conditional form. **A clean auto-merge
between two agents is not evidence that the result is correct.**

## 6. Traps (each cost time; still true unless struck)

- **Build races: NOT fixed — `agent_new.sh`'s hardlinks leak between agents.** The claim that
  `GW_BUILD_ROOT` isolates agents was wrong, and it cost most of an evening. `agent_new.sh`
  HARDLINKS the object baseline into each agent's root; `pipe_win.sh:16` then runs
  `gwtool.exe ... -o "$d/$n.obj"`, and gwtool TRUNCATES that path in place instead of unlinking
  it, so a write through any one link mutates the shared inode — baseline and every agent at
  once. clang (used for `--shim`) unlinks and replaces, so shims are safe and only game TUs leak,
  which is why `--test` "verified" it. Symptom: a link failing on unresolved externals that
  belong to a DIFFERENT agent's work, and a bridge that silently comes out too small (17,675
  entries instead of 22,273) and links green. **Until `pipe_win.sh` writes to a temp and renames
  (cheap, correct) or `agent_new.sh` copies instead of hardlinking (~1 GB per agent), treat every
  parallel green build and green `--test` as unverified.** Two agents hit this independently; one
  de-linked its own root by hand with `cp --no-preserve=links` and carried on.
- **LNK1104 "cannot open melee-pc.exe"** = a run still holds it. `run.sh` makes this impossible;
  outside it, `taskkill /IM melee-pc.exe /F`. A failed link leaves the OLD exe and tests then
  silently run old code — `build.sh` now detects this and refuses to continue.
- **Build order after any `pc/platform` change:** compile → link → `gen_bridge.py` → compile
  `gw_mex_bridge.c` → link again. A stale bridge does not fail the build or the boot; it silently
  calls the wrong native function. `build.sh` does this and verifies the fixpoint.
- **A new kind index is outside EVERY vanilla-sized per-kind structure** — C tables
  (`[Ft_Kind_Max]`), disc-loaded tables in `PlCo.dat` (`ftPartsTable`, `Fighter_804D6540`, widened
  by `ftCommonData_ExtendKindTable`), and the figatree-kind bits packed MSB-first in
  `x10_animCurrFlags` (low 6 bits). Expect more of these.
- **Platform statics outlive MEM1, and the test harness exploits that.** `gw_test.c` snapshots
  MEM1 and restores it around every test, but deliberately does NOT restore platform statics —
  its own comment says "a test must set up any platform state it depends on". So any guest
  pointer cached in a `pc/platform` static keeps naming an address whose contents are gone. The
  m-ex runtime and the stage tables both did this; `gw_Mex_InvalidateAfterMem1Restore()` now
  drops them and `gw_test.c` calls it after the restore. **Any new module that caches a guest
  pointer must hook into that function.** The symptom is nasty: the cache says the table is live
  while every word in it reads zero, and an accessor that merely degrades (as the fighter ones
  did) hides it until something stricter reads the same data.
- **`gw_mex_persist_alloc` is a bump allocator that never frees.** Re-initialising the m-ex
  runtime therefore leaks the whole 384 KB region in about three cycles. The invalidation above
  rewinds it; anything else that re-inits must too. Rollback cares about this as well.
- **A per-kind count from the clone base can overrun the real table** — that was tonight's crash
  (§3). When a count is not in the fighter's own data, derive the end from the data, and bound it
  by the archive.
- **An unregistered m-ex slot does not fail** — it runs the clone base's handler. Audit all of a
  fighter's override slots when adding one.
- **Four index spaces**: m-ex INTERNAL, m-ex EXTERNAL, port `FighterKind`, port `CharacterKind`.
  Guest code that indexes an m-ex table by `fp->kind` is reading the wrong row unless it goes
  through a shim.
- **Sonic (and every m-ex fighter) only exists on the Akaneia/ACE discs.** A run against vanilla
  boots fine and logs no `interp:` lines at all — that reads as "the blob failed to install" when
  the character simply is not on the disc.
- **`vswhere.exe is not recognized`** from the link is benign noise; the signal is
  `MELEE_PC_LINK_OK` on the last line.
- **Never pipe `clang.exe` through `head`** — SIGPIPE kills it mid-write, leaving no `.obj` and a
  confusing `LNK1181` next link.
- **Write patch scripts with the Write tool, not bash heredocs.** This bit again today: `\n` and
  backslashes inside a nested heredoc arrived mangled and the `assert old in s` failed (safely).
- **Mixed line endings:** `src/` is often CRLF, `pc/platform/` LF. Patch scripts must preserve the
  file's own endings.
- **`pipe_win.sh`'s exit code is meaningless** — the signal is `CC_FAIL`/`GW_FAIL` in the text.
- **Agents stall and write nothing.** Check the working tree, not the story.
- Resolve crash RVAs with the quickref's `mapsym.sh`; `/DYNAMICBASE:NO` makes map RVAs exact.

## 7. Conventions

- Game-source changes `#if defined(TARGET_PC)`-guarded, original under `#else`.
- Native shims (`pc/platform/*.c`) are listed in `_build/melee_link_objects.rsp` — **not** in
  `files.txt` (that is only for PPC→x86 pipe TUs). Both response files are hand-maintained.
- **m-ex has NO LICENCE** — specification only; reimplement in original C; never vendor its
  `.asm`/`.h`/`.dat`.
- `GIT_MASTER=1`; per-command `-c user.name="GD" -c user.email="gd@gsd.sh"`; melee subjects `pc:`,
  root `docs:`/`build:`/`tools:`. **Never `git add -A`.**
- Commit messages end with `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>`.
