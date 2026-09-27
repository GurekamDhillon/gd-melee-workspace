# Handoff - m-ex content in the native PC port

**Reviewed 2026-09-27 against workspace `fc23753` and game `4c676892a`.** The dated state in
[NEXT-SESSION.md](NEXT-SESSION.md) wins over this architecture reference and the older handoffs.
The 2026-09-26/27 queues have been folded into it. Old run totals are historical evidence, not
results for HEAD. This review did not build or run the game.

## 0. First action on resume

Read `NEXT-SESSION.md`, then the current source and lane report for the task. Confirm which game
checkout and build root you are using. Never infer a running EXE's contents from source HEAD.

## 1. Architecture

m-ex content is loaded from `MxDt.dat` and mounted archives. `gw_mex_ftfunction_runtime.c`
installs per-kind hooks only where the blob supplies an override; absent hooks retain clone-base
behaviour. `gw_mex_grfunction` supplies the stage path. Interpreted guest code reaches native
functions through the generated `gw_mex_bridge` table and the PPC bridge ABI.

Geno extends that system with data-driven scripts, states, articles and effects. Its current JSON
version is 5, with additive v5.5 commands. It is public on `pc-port`; the LAB is a Lua script mod.
See `scripting.md` for every registered `gd` function and game `docs/geno.md` for encoding details.

## 2. Build and run

Use [tools/port/README.md](../tools/port/README.md). `build.sh` owns stale-object detection,
bridge regeneration/fixpoint and the final ABI audit. `run.sh` owns the EXE/map copy and sandbox.
Do not turn an isolated raw compile or link into a claimed completed build.

## 3. Index spaces

Keep m-ex internal/external ids, `FighterKind` and `CharacterKind` separate. PC m-ex kinds begin
at `Ft_Kind_Mex0 = 0x21` and `ChKind_Mex0 = 0x22`, with 94 slots. Retail kinds are a different
permutation, not this offset. Scene numbers require a prefix (`fk:`, `ck:`, `mex:`, `mexext:`;
stages `int:`/`ext:`); prefer the installed name when it is unambiguous.

## 4. Current work

The 2026-09-27 `NEXT-SESSION.md` owns the backlog. Runtime stage models, enemy/camera APIs,
logic-frame pad holds, boss hits and the Classic IntroEasy matrix fix are in game HEAD.
The platform exporter and build-speed round 2 are not in the audited workspace HEAD.

## 5. Evidence

Record the source revisions, actual EXE/map, shared renderer build, disc, mounted mods, switches
and run directory. Separate source inspection, engine test results, scripted gameplay results
and GD's visual/controller checks. An old 185/185 result cannot validate subsequent changes.

## 6. Traps

- **Hardlinked baseline objects.** `agent_new.sh` still links baseline `.obj` files into a new
  build root. A writer that truncates an existing output changes every link; a writer that
  creates a temporary file and replaces the output does not. The game-TU writer lives under
  local `_build/masstest/pipe_win.sh`, outside this repo. Inspect it before parallel builds;
  `GW_BUILD_ROOT` alone is not proof of isolation. Shared Aurora/Dawn libraries also need
  coordinated rebuilds.
- **Stale EXE/map.** A failed link or an already-running sandbox can leave you testing old code.
  `run.sh` copies both files per run so the baseline EXE is not held open. Check the copy's
  revision/new diagnostic text. Stop only your own PID after checking its executable path.
- **Bridge fixpoint and ABI.** `build.sh` links, regenerates from its own map and decomp metadata,
  recompiles/relinks if needed, then checks again (four checks maximum). An untrusted bridge
  object takes a conservative extra link. A stable source table alone is insufficient: the
  final EXE also gets the bridge ABI audit. Skipping this can call the wrong native function
  without a boot failure. Generated bridge changes are normal build output.
- **Timestamp scans.** `scan_stale_tus.py` checks game sources and headers, including Geno.
  This HEAD does not implement `GW_JOBS` or general content-hash incremental builds. Do not
  confuse the bridge's SHA-256 proof stamp with the proposed content-hash scanner.
- **Platform statics outlive MEM1.** Native cached guest pointers must be invalidated after a
  test snapshot restore (`gw_Mex_InvalidateAfterMem1Restore`). Restoring game memory does not
  restore host caches or allocation cursors.
- **Counts belong to the data.** Clone-base counts can overrun a ported fighter's own tables.
  Bound archive walks and account for empty motion rows. A new fighter kind also reaches
  per-kind tables loaded from disc; widening a C array alone is insufficient.
- **Conditional hooks.** A registered override replaces the original callback. Register only
  supplied hooks; an absent m-ex override falls back to the clone handler.
- **Content selection.** A vanilla disc has no added fighter unless mounted mod files supply
  it. `MELEE_MODS_DIR` is the parent of packs, not one pack. Use native Windows paths (`pwd -W`
  in Git Bash); `/c/...` in an environment variable is not a Windows filename. Read the mount log.
- **Harness summaries are incomplete.** Read `melee-pc.log` and crash logs before classifying a
  failure. The local pipe's `CC_FAIL`/`GW_FAIL` text matters as well as its exit code. Never pipe
  a compiler through `head`: SIGPIPE can interrupt output. Preserve a source file's line endings.
- **Three clocks.** `MELEE_FPS=u` uncaps presentation; realtime game logic stays at 60 Hz.
  `MELEE_TURBO=1` accelerates scripted/batch simulation. `gd.input` holds count completed logic
  frames, but legacy text scripts consume PADReads. A paused render read cannot consume a Lua hold.
- **Pad ownership.** A script claim stays connected and neutral between holds. Release it with
  `gd.release_pad`, task completion or script unload; console socket claims end on disconnect.
- **Turbo is not a visual/performance check.** Unpresented match frames skip display lists and
  skinning unless `MELEE_TURBO_DRAWS=1`. The `run.sh --test` wrapper requests turbo, but the
  headless suite has no paced frame loop. Use `--realtime` before the sandbox name to clear it.
- **Stage APIs are stricter than general gameplay APIs.** Stage/enemy creation requires an active
  offline match and a gameplay script; the console cannot do it. `stage_add_model` attaches an
  existing floor via `platform=handle`; there is no `model=` platform option in this HEAD.
- **Runtime libraries matter.** A rebuilt EXE does not prove a shared Aurora change is running.
  Source at `4c676892a` uses 24 MiB for storage (its comment cites a 10,573 KB four-Sora peak)
  and 12 MiB for vertices. It drops remaining draws after overflow; this source review does
  not verify visual stability or which shared library a running game loaded.

## 7. Conventions

- Guard game-source changes with `#if defined(TARGET_PC)` and retain the original path.
- Game TUs use the PPC frontend/gwtool pipeline. Native `pc/platform` shims do not belong in
  `files.txt`; list their objects in the link response file. Lane sync rewrites the curated
  workspace link list for its build root; do not glob stale object directories into it.
- Native shims use `gw_r*`/`gw_w*` for game-visible memory. Game code calls unprefixed shim
  names because gwtool adds `gw_`; do not add a second endianness or symbol-prefix layer.
- m-ex is specification/reference material, not vendored implementation. Keep attribution on
  reimplemented features. No disc-derived data or Nintendo assets in either repo or a release.
- Keep research under `_research/`, current handoffs under `docs/`, release notes under
  `tools/release/notes/<version>.md`. Dated files win and explicitly name what they supersede.
- Change launcher English strings and `Lang.cs` together; run `check_strings.py`. README words
  come from `menu/pipeline/readme_text.json`; GitHub displays committed `docs/readme` PNGs and
  prefers `.github/README.md` when present.
- Stage only named paths when authorised to commit. Do not push, publish or merge shared
  branches without GD's go. Commit trailers must identify the actual contributor; do not copy
  another agent's identity from an old handoff. This docs-refresh task permits no commits.
