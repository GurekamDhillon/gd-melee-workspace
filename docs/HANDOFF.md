# Handoff — m-ex content in the native PC port

**Written: 2026-09-19 (evening).** Supersedes the 2026-09-19 (morning) handoff, in git history.
Stage authoring / Blender-as-level-editor remains DROPPED.

Read `_research/port-dev-quickref.md` (commands, env vars, traps) first — it now documents the
build/run scripts and the parallel-agent setup, and those supersede the raw command lines. The
m-ex research: `mex-ppc-interpreter.md` (architecture), `mex-data-layer-design.md` +
`mex-dump-tools.md` (mexData/MxDt.dat), `mex-item-spawn.md` (itFunction, custom items),
`akaneia-dependency-scope.md`, `bridge-signatures.md`, `mex-css.md`, `mex-sound-banks.md`,
`rollback-netcode.md`.

---

## 0. FIRST ACTION ON RESUME

The #21 work is **uncommitted** (29 files in `melee/`, plus `tools/port/` and three build files in
the root repo). `agent_new.sh` branches worktrees off `HEAD`, so **every fan-out agent would start
from a tree that still has the old Sonic-specific code**. Commit before creating any worktree.

Ask the user first, then:

```
git -C C:/gdm/melee add -u && git -C C:/gdm/melee add pc/platform/gw_mex_bridge.c
git -C C:/gdm/melee commit        # subject: "pc: generalize m-ex fighter support (table-driven)"
git -C C:/gdm      add tools/port .gitignore _build/build_melee_pc.bat _build/masstest/pipe_win.sh \
                       _research/port-dev-quickref.md docs/HANDOFF.md
git -C C:/gdm      commit         # subject: "tools: per-agent build roots and run sandboxes"
```

Never `git add -A` (see §7).

## 1. State in one paragraph

**The m-ex fighter path is now table-driven, and Sonic runs entirely through it.** He is no longer
special-cased anywhere: he loads as port kind 37 / m-ex internal 31 purely from `MxDt.dat` rows,
and 7 m-ex kinds (33..39) are registered from Akaneia's data. `src/melee/ft/kinds/ftSonic/` is
deleted. His spring (up-B, custom item kind 277) spawns and runs. In-engine tests **33/33**.
Also landed today: announcer + victory theme + results screen, the Aurora update, the upstream
doldecomp merge, the mods folder (#10), vanilla-disc + mods Sonic (#12), and — new this evening —
**parallel build/run infrastructure so several agents can work at once** (§5).

Not verified by the user since the spring fix: he play-tested before it, not after. The change is
narrow (see §3) and `--test` is green, but a hands-on VS match is the right first move.

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

Useful env: `MELEE_TRAINING=38` (Sonic), `MELEE_TARGET_TEST=32`, `MELEE_MODS=0/1`,
`MELEE_DVD_TRACE`, `MELEE_HEAP_TRACE`, `MELEE_MEX_TRACE_CALLS`, `MELEE_MEX_DUMP_CODE=<path>`,
`MELEE_MEX_TRACE_PARTS`, `MELEE_MEX_TRACE_SCALE`, `MELEE_PPC_TRACE_FP`.

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

Tasks #23–#26 plus rollback are the fan-out in §5. Smaller items, none blocking:

1. **Stale Sonic-specific comments** in `gw_mex_ftfunction_runtime.c` (~lines 4, 231, 1985) and
   `ftdata.h:77` — the code is generic now, the prose still says "Sonic".
2. **#17 leftovers**: CSS cursor scaling, icon blink, unwired slots 16/17/18 (item release/catch).
3. **Bridge gaps** recorded, not fixed: float varargs (`HSD_ForeachAnim`), double args, struct
   returns.
4. **Temporary debug traces** in the runtime can go once the other fighters are in.

## 5. Parallel agents (new) and the fan-out plan

### The mechanism

```
bash C:/gdm/tools/port/agent_new.sh <name>        # worktree + build root, objects hardlinked
export GW_MELEE=C:/gdm/worktrees/<name>
export GW_BUILD_ROOT=C:/gdm/_build/agents/<name>
```

`GW_BUILD_ROOT` holds that agent's objects, link response file and `melee-pc.exe`, so two agents
share nothing they write. Shared and read-only: the Aurora/Dawn/SDL3 libraries in `_build/ax86m`
(the link always runs there because `melee_link_libs.rsp` names them relative to it — only the
outputs move) and the ISOs. `agent_rm.sh <name>` cleans up, refuses on uncommitted work, and never
deletes the branch.

Verified end to end: a second agent built into its own root and ran its own `--test` (33/33) while
the main tree linked concurrently. `--test` is headless (no window, no GPU) so test runs
parallelise freely; **gameplay runs each open a window and share one audio device, so keep audio
checks serial.**

### The fan-out (launch these on resume, after §0's commit)

Five agents, each in its own worktree. #23 and #25 are the two that actually need the engine; #24
depends on #23's findings, so stage it second. Every prompt must carry the same preamble:

> Work only in your own worktree. `export GW_MELEE=C:/gdm/worktrees/<name>` and
> `export GW_BUILD_ROOT=C:/gdm/_build/agents/<name>` before anything else, and build only with
> `tools/port/build.sh` and run only with `tools/port/run.sh`. Read
> `_research/port-dev-quickref.md` and `docs/HANDOFF.md` first. m-ex is a SPECIFICATION ONLY — no
> copied `.asm`/`.h`/`.dat`. Write each file to disk as you go and build incrementally; do not
> report success you have not seen a green build and a green `--test` for.

| agent | task | scope |
|---|---|---|
| `fighters-akaneia` | #23 | Wolf, Diddy, Charizard, Lucas, Dedede, Tails (m-ex internal 27–32). The table path already registers them; find what each one needs beyond Sonic's path — per-kind items, Kirby hats, demo tables. One fighter fully working before starting the next. |
| `fighters-ace` | #24 | ACE's additional fighters. ACE's `MxDt.dat` defines 31 new fighters in total, Akaneia's 7 included — start by dumping it and reconciling the two index spaces, then report the real list before importing. |
| `stages` | #25 | m-ex custom stages (Akaneia + ACE): `grFunction`, stage tables, SSS expansion, stage audio. Research first, land the smallest stage end to end second. |
| `content` | #26 | Remaining m-ex content: items, music, trophies, menus. Mostly data-table plumbing; likely the easiest to finish. |
| `rollback` | — | Rollback netcode. `_research/rollback-netcode.md` already exists (delivered, never summarised to the user). Next step is a concrete port-specific design: what state must be snapshotted (MEM1 regions, the PPC interpreter's state, allocator state), and what it costs per frame. **Design only, no implementation.** |

`GW_MEX_SLOTS` is 31 and `GW_MEX_KIND_MAX` is `0x21 + 31`, which exactly fits ACE's 31 added
fighters with nothing spare. #24 should check that first; if ACE needs more, the constant and
`Ft_Kind_None`/`ChKind_Cap` move together.

Two agents must not edit the same file. `ftdata.c`, `forward.h` and
`gw_mex_ftfunction_runtime.c` are the likely collisions between #23, #24 and #25 — have them
report needed shared-file changes back rather than landing them independently, and integrate here.

## 6. Traps (each cost time; still true unless struck)

- ~~**Build races**: never run two agents that build+link concurrently.~~ **Fixed** by
  `GW_BUILD_ROOT` (§5). Two agents may now build and test at the same time.
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
