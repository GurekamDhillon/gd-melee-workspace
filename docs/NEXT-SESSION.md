# Next session — start here

**Written 2026-09-20, after an 86-commit day.** `docs/HANDOFF.md` remains the architecture
document; its §6 Traps and §7 Conventions still hold and this file does not repeat them. This is
the state of things and what to do first.

## The build is green and both repos are backed up

- **70/70 headless on vanilla, Akaneia and ACE.** `tools/port/build.sh` ends `abi … OK`.
- Port: `pub` = `GurekamDhillon/melee`, branch **`pc-port`** (public).
- Workspace: `origin-ws` = `GurekamDhillon/gd-melee-workspace` (**private**, created today).
  122 commits of build system, tooling, research and docs. Audited before pushing: zero
  disc-derived files locally or on the remote.

## READ THIS FIRST: three ways this tree lies to you

Every one of these cost hours today, and two of them produced confident, wrong reports that
became the premise for further work.

**1. A stale artifact is not the one being used.** `build.sh` rebuilt stale *shims* but not stale
*game TUs*, so four fixes — the CSS portraits, `tlut_no`, Kirby, and the ACE stage work — were
"verified" against binaries that had never contained them. One of those false verifications was
written up as established evidence and handed to an agent as a thing not to re-derive.
*Now fixed*: `build.sh` rebuilds a stale game TU as well as a stale shim.
**The habit that catches it: grep the EXE for a string the fix adds, not the source.**

```
grep -a "your new log text" _build/melee-pc.exe
```

Same class, different costume: the GitHub front page showed upstream's README for weeks because
`.github/README.md` outranks the root one. The file was committed and correct; it just was not
the one being served.

**2. The harness under-reports.** A sweep called 150 runs "failed, no fault logged"; 52 of them
had a plain `gw: FATAL ACCESS_VIOLATION` in their logs. The fault text was being scraped from
selftest's *console output*, which prints only the first three matches and is wrapped.
*Now fixed*: faults are parsed from the log. Before dismissing a class of failure as an artifact,
read one of the logs.

**3. Concurrency breaks things that were implicitly single-instance.** Running four games at once
surfaced: a shared Dawn pipeline cache that corrupted and made every later run die at its first
draw (looked exactly like a dead GPU — a reboot was recommended and would not have helped); a
spin watchdog whose 4-second wall-clock threshold fired falsely under load; volume set by process
*name*, so each run turned a sibling down and left itself at full; and two sweeps running at once
because one was believed stopped. All fixed, mostly by making the tooling assert the invariant
instead of relying on memory.

## What works now that did not this morning

| | before | after |
|---|---|---|
| added stages loading | 19/109 | **~81/109** |
| headless tests | 63 | **70** |
| trophies | never executed | gallery, collection, lottery, unlock popup |
| m-ex off a vanilla ISO | not possible | **works, both discs** |
| PNG → GX texture → drawn | did not exist | **works, verified on screen** |

Highlights, with the cause rather than the symptom:

- **The float signature table was scoped to Sonic's two blobs.** Every other fighter read `f32`
  arguments out of integer registers. That was the NaN collision box. Regenerated with
  `--all-symbols`: 19,355 rows.
- **Articles with `codeSize == 0` were refused, not recovered** — which is what "the port does not
  load itFunction yet" actually was. Three ACE fighter groups went 0/7 → clean.
- **The execute trap was armed only by the fighter install**, so every added stage with guest code
  died in MEM1. Two lines.
- **The CSP formula was inverted**: `animateJoint` takes a *frame*, the code computed an *image
  index*, and an `HSD_A_T_TIMG` track maps between them. The original formula was right.
- **Trophies needed no new code** — 12k lines of `ty/` had simply never been reached. Two decomp
  artifacts that depended on retail's `.data` layout were in the way.

## Do these first

1. **#20 — two stages left.** `ext:302` exhausts the HSD heap at ~frame 273 *after rendering*,
   which implies the port over-allocates somewhere an ordinary match does not. That is the most
   interesting bug on the board. `ext:306` faults in `ucrtbase` — a pointer crossing the
   host/guest boundary that the `gw_ppc_call` mirror does not cover.
2. **#23 — the loading screen**, now that the texture path exists. Hold the scene until aurora's
   pipelines are warm rather than letting the match fill in piece by piece.
3. **#22 — m-ex trophies 293..341.** Invisible, not broken: `TY_TROPHY_COUNT` bounds every loop.
   Raising it is a **save-format** change, so decide the format deliberately.
4. **#10 — rollback, bridge gaps, perf.** Nobody has profiled the port yet. A design doc exists at
   `_research/rollback-port-design.md` and a branch at `agent/rollback`.

## Facts that are easy to get wrong

- **`ck:41` is Wario. Metal Sonic is `ck:55`.** A task was mislabelled for a day over this.
- **ACE fits exactly**: 31 added fighters into 31 slots, zero spare. The ceiling is 43, set by a
  6-bit `x597_bits` field; going past that means widening it.
- **ACE is a superset of Akaneia** for fighters — same seven files, more costumes. Combining the
  discs would add nothing.
- **`TyExt.dat` is not a table**, it is a display asset. The extended trophy table is
  `TyDataf.dat`'s `tyModelFileTbl`: 293 vanilla, 342 on both mod discs, and **ACE adds none of its
  own**.
- **`MELEE_MODS_DIR` points at the pack's *parent*.** Pointing at the pack itself gives
  `MxDt.dat not on this disc` and a green-looking 70/70 that proves nothing.
- **`skipmemcard=0` is required for trophy scenes**, or saving *and* loading are both disabled.
- `_build/card` is the fully-unlocked card. Use `_build/card-trophy` or a copy for anything that
  writes.
