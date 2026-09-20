# Next session — start here

**Written 2026-09-19, late. The tree is committed, the build is green, and there is a harvest of
crash logs waiting in `_build/crashlogs/`.** `docs/HANDOFF.md` is still the architecture document
and its §6 traps and §7 conventions are unchanged; this file is only what happened at the end of
this session and what to do first.

## The build is current and gated

- gwtool was rebuilt **with the ABI pin** (`pinInternalAbi`), then **all 988 TUs** were rebuilt
  through it, then relinked. This ordering is mandatory; `_build/build_gwtool.bat` says why.
- `tools/port/build.sh` ends `abi ... reads ECX/EDX in prologue : 0 ... OK`. First time.
  Bridge: 18,510 entries, fixpoint reached.
- **Tests 63/63 on vanilla, Akaneia AND ACE.**

The harness was lying before today: `gw_apply_fixups()` is a toggle and was being re-applied after
every test, so game globals were correct or byte-swapped **by the parity of the test index**. Any
green result older than this session that touched a game global was a coin flip. It is fixed.

## Run it

```
_build\play.bat akaneia
_build\play.bat ace
_build\play.bat akaneia "mode=vs;p1=ck:34/c0/hu;p2=ck:2/c0/cpu1"
```

`play.bat` now sets `MELEE_CARD_PATH` (`_build/card`, or `_build/card-ace` for ACE). **It did not
before**, and `shim_card.c` falls back to `card/` next to the exe — which lives in a per-run
sandbox. So every launch had an empty card: the memcard prompt on boot and a **fully locked
roster**, which re-flows the CSS grid. That, not a table bug, is where "Fox is missing" and
"Sonic is unselectable" came from. If a roster ever looks wrong again, **check the card first.**

To re-harvest: `& "_build\harvest.ps1"` (all 17 scenes) or `-Only wolf`. It runs **off-screen**
on purpose because it is unattended; a single scene you want to watch goes through `play.bat`.

## What the harvest found — 13 of 17 green

**Green, and these are real results, not absence of evidence:** Diddy, Charizard, Lucas, Dedede
and Tails all reach a match on Akaneia; **Fox c4/c5 and Jigglypuff c5/c6 load**, which is the
per-costume table fix working, including the hat path that had never been run; Game & Watch c4/c5
and the Falcon c6 / Yoshi c7 spread load; both deliberate bad costumes are refused as designed;
vanilla is unaffected; ACE boots to the CSS.

**Four reds, in the order I would take them:**

1. **Wolf (`ck:34`, Akaneia) — `_gw_ftParts_80074A4C+0xD`, a NULL `gobj`.** Unchanged by the
   tail-call fix. The `gw_ppc.c` tail-call bug was real and is fixed and tested on its own terms
   (`ppc_tail_branch_returns`), but **it was not Wolf's cause**, or not all of it. The tell: both
   `MEX_IndexFighterItem` calls still log before the fault, which does not fit a story where the
   terminal `b` is the branch being taken. Trace the interpreter; do not re-assume the theory.
2. **Kirby c6 inhaling DK — `_gw_lbFileGetFullName+0x10`.** Suspect a **regression from this
   session's merge**: `ftKb_Init_803C9FC8[kind][costume]` now goes through `FT_COSTUME_VIS_IDX`.
   The copy table may belong with the archive-loading tables that must keep the *real* costume id.
3. **Metal Sonic (ACE) — the symptom MOVED.** No longer `GObjProc_QueueProc`; now
   `unimplemented opcode at ip=0x81269014 word=0x00000127`, from `entry[0] = 0x81269008`. `0x127`
   is not a PowerPC instruction, so this is data being executed — a wrong entry point, not a
   missing opcode. **Do not go add an opcode.**
4. **Sonic (Akaneia) faulted inside `webgpu_dawn.dll+0x363548`**, not in game code, on the one
   scene that was already user-verified working. Treat as GPU/driver flake until it repeats;
   re-run it before spending time on it.

Every one of those has its full log at `_build/crashlogs/<tag>.log`, plus a frame capture.

## Still open, unchanged by today

CSS portraits for added characters render as rainbow corruption (#13). Trophies, rollback, the
remaining bridge gaps and perf (#10). The root repo still has **no remote and exists only as this
copy** (#7) — that is the largest unmanaged risk in the project and it is a decision, not a task.
Akaneia's spare costumes still need writing up in `_research` (#3).
