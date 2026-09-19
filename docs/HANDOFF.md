# Handoff — m-ex content in the native PC port (Sonic)

**Written: 2026-09-19.** Supersedes the 2026-09-16 handoff (in git history). Stage authoring /
Blender-as-level-editor remains DROPPED.

Read `_research/port-dev-quickref.md` (commands, env vars, traps) first. The m-ex research, all
current and each with explicit open questions: `mex-ppc-interpreter.md` (architecture),
`mex-data-layer-design.md` + `mex-dump-tools.md` (mexData/MxDt.dat), `mex-item-spawn.md`
(itFunction, custom items), `akaneia-dependency-scope.md` (what Sonic needs from the disc),
`bridge-signatures.md` (float signatures), `mex-css.md` (character select).

---

## 1. State in one paragraph

**Sonic is playable end to end, user-verified.** Pick him from the character select screen
(dev toggle, below), play a VS match, reach the results screen, return to the CSS. The user played
hands-on: "everything I tested in gameplay looked, and felt right". All eight specials run and
complete, including the spring (his item) and the homing attack's on-hit. His mouth and idle face
render, the jab fist animates correctly, model scale and movement physics look right. In-engine
tests: **33/33** on both discs. What is NOT done is presentation and packaging: his CSS icon and
portraits, his voice/stock icon/emblem/victory animation, and running him from a vanilla disc.

Baseline: melee fork `pc-port` @ `504be24aa`, root @ `f8ea7a0` (plus this handoff). 16 melee
commits today, each with a detailed message — `git log 64cf61c92..504be24aa` is the change log.

## 2. How to run it

```
MELEE_CSS_SONIC=pichu   # that character's CSS icon selects Sonic (any name/ckind; art stays Pichu's)
MELEE_TARGET_TEST=32    # or: boot straight into Target Test as Sonic
--iso C:\iso\Akaneia.iso   # REQUIRED - Sonic's files exist only on the Akaneia disc
```
Launch visibly on the main desktop (the user wants to watch; the old off-screen rule is retired).
Pad scripts for unattended runs live in `_build/pad_*.txt`; they are consumed from the first
PADRead, during BOOT, so a short burst never reaches the match — repeat the cycle and put A presses
first to clear the no-memory-card prompt. Good ones: `pad_specials_repeat.txt`, `pad_upb.txt`,
`pad_idle_jab_turn.txt`, `pad_dj_repeat.txt`. Use `WaitForExit()` rather than fixed sleeps.

Diagnostics (all env-gated, off by default):
| var | shows |
|---|---|
| `MELEE_PPC_TRACE_FP=1` | every bridged float call with its marshalled args and result |
| `MELEE_MEX_DUMP_CODE=<path>` | writes the RELOCATED ftFunction blob, for `ppc_disasm.py --raw` |
| `MELEE_MEX_TRACE_PARTS=1` | model-part visibility table (mouth/eyes) on change |
| `MELEE_MEX_TRACE_SCALE=1` | any joint with abnormal scale, with its animation tracks |

Always on: the execute trap logs the first call per target and the first 48 return values; the
instruction-budget panic dumps the guest registers; every guest address prints with its function
name (the blob's own debug symbols).

## 3. What was built (the architecture you now have)

Interpreter correctness — each of these silently produced wrong numbers, not crashes:
- `fcmpu` set the LT bit for GREATER-than (every guest float compare was backwards for >).
- opcode 59/63 decoded with a 10-bit XO; A-form is 5-bit, so `fmul` with frC != 0 was
  "unimplemented"; `fmul` also used frB instead of frC. `xoris` was missing (the ONLY missing class
  reachable in Sonic's code, per a reachability audit).
- bridged calls defaulted to "8 integer args": float args came from r3.. and float returns were
  discarded. Now prototype-derived (`tools/mex_port/gen_sigs.py` -> `gw_mex_sigs_gen.inc`, 115
  targets across ftFunction + the spring blob, 0 disagreements with the hand table). **Regenerate
  it whenever a new blob is added** — the spring died on frame 1 until its own blob was scanned.

Native code <-> guest code:
- guest -> native: the bridge (`gw_mex_bridge.c`, generated; regenerate after every relink).
- native -> guest via an API (GObj_SetupGXLink, HSD_GObj_SetupProc): a pool of 64 native thunks.
- native -> guest via a raw store (e.g. `fp->deal_dmg_cb = SpecialNHit_Enter`): a vectored
  exception handler. MEM1 is non-executable, so such a call faults cleanly with EIP = the target;
  the trap redirects EIP to an interpreting trampoline (target in blob code) or to the function's
  native build (target is a VANILLA GameCube address — m-ex does this constantly: Sonic has 64
  stores like `pre_hitlag_cb = efLib_PauseAll`). Anything else still reaches the crash logger.
- guest code is a SET of ranges (`gw_ppc_add_code_range`): ftFunction + one per item article.
- re-entry: a hook already on the stack runs vanilla instead (`gw_Mex_GObjDispatch`), plus a
  depth cap and a 50M-instruction budget, both of which dump the guest chain/registers.

m-ex content:
- `MxDt.dat` loaded as mexData (it IS the m-ex data; field paths verified from the file).
- `MEX_GetFtItemID` / `MEX_IndexFighterItem` real; `itFunction` loaded (fills `item.Custom`).
- item.c: the custom-item kind range (>= 237), its renderer, and `Item` grown to 0xFD0 with
  m-ex's original-owner word at +0xFCC.
- jobj.c: m-ex joint scale compensation (flag bit 26), re-expressed from the hook Akaneia ships.
  This was the first ENGINE patch from `codes.gct` the port needed — Akaneia's 1,163 codes are
  not all irrelevant after all; check that inventory when content misrenders.
- 21 of Sonic's 25 override slots wired. Wire by the vanilla TABLE a slot overrides (Header.s
  names: onDeath, onKnockbackEnter...), not by his function's name (OnRespawn, EyeTextureDamaged).
  An unregistered slot silently runs the Fox clone's handler — that is how his idle mouth broke.

## 4. Open work, in recommended order

1. **Proper m-ex CSS (task #17 phase 2).** `_research/mex-css.md` has the plan. Retires the dev
   toggle; gives Sonic his icon, portraits (the retail ones show "corrupted Captain Falcon" on
   Akaneia), emblem, voice and stock icon.
2. **Mods folder (#10) then vanilla-disc acceptance (#12).** Two mechanisms: additive files and a
   per-record override for `PlCo.dat` (Sonic's ftPartsTable[31]). Now also: engine patches like
   the scale compensation are native code, so they come with the port, not the mod.
3. **Unwired slots 16/17/18** (item release/catch/unknown): no dispatch site yet; only matter while
   Sonic holds an item. Untested: items, teams, 1P/Classic, Training.
4. **Hit-reaction eyes** (slots 21/22) are wired; the user has played VS but nobody has
   specifically checked his eye texture when hit.
5. Bridge gaps recorded, not fixed: float VARARGS (`HSD_ForeachAnim`), double args, struct returns.

## 5. The lesson of the day

Most of the day's bugs were silent: wrong numbers, wrong index spaces, a fallback running the
wrong character's handler. None of them crashed where the bug was. What found them was
instrumentation (the instruction budget, the register dump, the symbol table, the parts and scale
traces), not reading code harder. Two causes were misattributed first (the item system for the
neutral-B hang; MoveLogic "never firing" - it fires only in character-specific states). Measure,
then conclude.

## 6. Traps (still true; each cost time)

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

Added 2026-09-19:
- **This machine's shell is Git Bash, not WSL.** No `/mnt/c`. Link with
  `cd C:/gdm/_build/ax86m && cmd.exe //c "..\build_melee_pc.bat"` (the `vswhere` line in its output
  is noise; `MELEE_PC_LINK_OK` is the signal). Game TUs: `bash C:/gdm/_build/masstest/pipe_win.sh <src>`.
- **LNK1104 "cannot open melee-pc.exe"** = a hung game still holds it. `taskkill /IM melee-pc.exe /F`
  first. A failed link leaves the OLD exe, and tests then run the old code silently.
- **Build order after any pc/platform change:** compile -> link -> `gen_bridge.py` -> compile
  `gw_mex_bridge.c` -> link again (the bridge is keyed to native VAs). Check the fixpoint by
  regenerating and diffing.
- **Never pipe clang through `head`** — SIGPIPE kills it mid-write and leaves no .obj.
- **Mixed line endings:** `src/` files are often CRLF, `pc/platform/` LF. Patch scripts must match
  the file's endings or their `old in s` asserts fail (safely, before writing).
- **Write patch scripts with the Write tool**, not bash heredocs: `\n` / `\0` inside nested
  quoting landed as real newlines and a literal NUL byte (twice) — the NUL still compiled.
- **An unregistered m-ex slot does not fail** — it runs the Fox clone's handler. Audit all of a
  fighter's override slots when adding one.

## 7. Conventions

- Game-source changes `#if defined(TARGET_PC)`-guarded, original under `#else`.
- Native platform shims (`pc/platform/*.c`) are compiled directly and listed in
  `_build/melee_link_objects.rsp` (outside version control) — **not** in `files.txt` (which is only
  for PPC→x86 pipe TUs).
- **m-ex has NO LICENCE** — specification only; reimplement in original C; never vendor/copy its
  `.asm`/`.h`/`.dat`.
- `GIT_MASTER=1`; per-command `-c user.name="GD" -c user.email="gd@gsd.sh"`; melee subjects `pc:`,
  root `docs:`/`build:`/`tools:`. **Never `git add -A`.**

