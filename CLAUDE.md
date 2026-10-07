# GD's Melee workspace: notes for agents

This repo is the build system, tooling, research and release pipeline around the game repo. The game
itself is a **separate checkout, normally `<root>/melee`** (branch `pc-port`, `GurekamDhillon/melee`). The two
are versioned apart; a change to gameplay lives there, a change to how it is built, tested, packaged or
described lives here. `SETUP.md` gets a machine ready; `tools/port/bootstrap.sh` checks it. In the
`codex/docs-refresh` worktree the game checkout is `${GW_MELEE}` (read-only for this
docs task); no builds or commits. `GW_MELEE` selects a non-default game checkout.

## Orientation

| you want to | go to |
|---|---|
| build or run the game | `tools/port/build.sh`, `run.sh` (never raw clang; see `melee/pc/docs/PORT_DEV_QUICKREF.md`) |
| the state of things and the traps | `docs/NEXT-SESSION.md` (read first), `docs/HANDOFF.md` §6 Traps, §7 Conventions |
| project words and naming rules | `docs/TERMINOLOGY.md` |
| the scripting API (`gd.*`, `gd.kit`) | `docs/scripting.md`; the LAB API is `melee/docs/geno.md` §14 |
| m-ex research | `_research/mex-*.md`, `docs/MEX_PORT_STATUS.md`, `tools/mex_port/README.md` |
| the menus' art | `menu/` (`menu/README.md`); `docs/ART-BRIEF-menus.md` |
| a release, the launcher, the friends zip | `tools/release/` (`README.md` there), `tools/netplay/` |
| Meta Knight, Ultimate Kirby and Sora (`ultimate-trail`) | `ports/halberd/`, `ports/ir/` (`ports/README.md`) |
| the crash sweep | `tools/sweep/` |
| session history | `docs/DEVLOG.md` (long; the numbered sections are dated) |

There are per-directory `CLAUDE.md` files under `tools/`, `menu/`, `ports/` and `docs/` with the local
detail. This file stays short.

## Facts that cost sessions (from `docs/NEXT-SESSION.md`; still true)

1. **A stale artifact is not the one being used.** Verify a fix in the EXE, not the source:
   `grep -a "your new log text" _build/melee-pc.exe`. `build.sh` rebuilds stale game TUs and shims
   now, but a copied exe in `_build/runs/<name>/` is a copy.
2. **The bridge fixpoint.** `gw_mex_bridge.c` maps guest addresses to native functions and is
   generated from the link map. `build.sh` links, regenerates, and recompiles/relinks as needed
   until the table matches the final map, then audits the EXE ABI. A stale bridge can build
   and boot while silently calling the wrong function.
   `build.sh` regenerating it and leaving it uncommitted is normal build output.
3. **The harness under-reports.** Read a failing run's log (`_build/runs/<name>/melee-pc.log`)
   before calling a failure class an artifact.
4. **Concurrency.** Several games at once need separate run dirs (`run.sh` does this) and
   separate build roots (`tools/port/agent_new.sh <name>`, `GW_BUILD_ROOT`). Baseline
   objects are hardlinked; check that the local game-TU writer replaces them, not truncates them.
5. **Timing.** Lua pad holds count logic frames. `MELEE_FPS=u` uncaps rendering;
   `MELEE_TURBO=1` accelerates scripted/batch logic. `run.sh --test --realtime <name>` clears
   the test wrapper's default turbo request. Commands: `tools/port/README.md`.
6. **`.github/README.md` outranks the root README** on GitHub.

## Conventions

- **No disc-derived data is ever committed**, here or in `melee`. Disc images come from `.env`
  (`GW_ISO_VANILLA`, `GW_ISO_AKANEIA`, `GW_ISO_ACE`), git-ignored. Audit before pushing.
- Research notes go in `_research/<topic>.md`; a session's handoff goes in `docs/`. Dated files
  supersede undated ones; say which one wins at the top.
- Release notes: `tools/release/notes/<version>.md`; `tools/release/VERSION` is the version.
- The launcher's strings are looked up by their exact English text (`Lang.cs`); change both copies
  and run `tools/release/launcher/check_strings.py`. That is the C# reference launcher's table: the Qt
  window (`tools/release/launcher/qt/`) carries its strings inline as `t("English", "Spanish")` pairs,
  checked by `tools/release/launcher/check_qt_strings.py` (also a CTest test, `launcher_qt_strings`).
- The README's art is rebuilt from `menu/pipeline/readme_text.json` by `menu/pipeline/readme.py`
  (headless Chromium); the committed PNGs in `docs/readme/` are what GitHub shows.

## What a cloud or headless agent cannot do here

The game builds and runs only on Windows, with the disc images. Without them: Lua can be
syntax-checked and the LAB's logic run against its stub (`melee/pc/geno/tools/lab_stage_d_check.lua`),
game-side C can be syntax-checked as PowerPC (`clang --target=powerpc-unknown-eabi -fsyntax-only`),
Python tools run, and the README art renders. Anything that must be seen on screen or timed in the
game is for a Windows agent; say so rather than reporting it done.
