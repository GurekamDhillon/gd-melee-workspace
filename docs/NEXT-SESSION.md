# Next session - start here

**Current as of 2026-09-27**, checked against workspace `fc23753` and game `4c676892a`.
This dated state supersedes `QUEUED-2026-09-26.md`, `QUEUED-2026-09-27.md` and the general
state in `HANDOFF-2026-09-24.md`. The dated Slippi handoff remains the record of those replay
runs, not a test result for today's HEAD. `HANDOFF.md` supplies the architecture and sections 6-7 rules.

**gd.comm landed (2026-09-28):** the paused `e06941cb` session's task was finished at game
`d6b067d25` (escapes fix, build + bridge OK, headless suite 203/203 on ACE, in-game smoke PASS;
docs in `scripting.md`). `RESUME-2026-09-28-e06941cb.md` keeps that session's context (its Claude
weekly limit resets Oct 3, 2am PT).

**Map editor overhaul (2026-09-28; workspace `3412a63`, game `dc138d56d`):** the in-game map editor
got the pass specified by `_research/map-editor-bible.md`. The overlay now **fills the widescreen
window** (`gd.safe_area`; see `docs/scripting.md`), and the editor gained: gizmo handles (red/green
move, cyan scale, gold rotate), typed + drag-scrub inspector fields, a filtered/categorised palette with
a translucent placement ghost, `Space` action search, a named Action Log with undo/redo rows,
multi-select (Shift/Ctrl add–remove, marquee box-select) with group transforms and delete as one undo
step, layout **v2** (camera/blast bounds **and spawns** persist; every edit is undoable through a
document-level history), draggable camera-bounds edges, an out-of-bounds placement warning, and
**native spawn editing** — `gd.stage_set_spawn(slot,x,y)` / `gd.stage_spawn(slot)` for starts/respawns
0–7 and item spawns 127–146, with `map spawn` in the editor. Evidence: contract tests (130 assertions,
PASS), headless suite 203/203 (10 runs), on-screen captures for each UI change, and live checks (a
moved respawn made P1 respawn there; an item-spawn move + undo restored `0,30`).
**Open on the editor** (bible §8 backlog, each needs native/feature work): native `gd.kit.field`, ghost
hover highlight, camera collision, orthographic views.
**Awaiting a decision:** which showcase to build — (1) Sora Magic FX showcase (zero engine work: the
`gw_fx.c` runtime, the `ultimate_vfx_geno.py` importer and the fx_bindings already exist), (2) a
scripted room/boss on the Gamemode library, or (3) a Geno specials reel.
**Option 1 is the shortest path and its content already exists on disk** (verified 2026-09-28):
`_build/agents/alpha/sora/bak-v6/ultimate-trail-slot/` holds a built Sora slot — fighter config, ACMD
conversion and **dozens of `fx/P_Trail*/**.gfx.json` effect packages** (AerialSweep\*, Air\*, and the
magic/Keyblade sets). The remaining work is to install that slot under `MELEE_MODS_DIR`, verify the
effects attach in a match (`gd.fx()` census + a capture), and tune; start from
`docs/prompts/codex-sora-effects.md` and `_research/geno-effects-runtime.md`.

## Current code

- Release version is **0.1.6** (`tools/release/VERSION`). HEAD has substantial work after that
  release; the old 185/185 result does not validate it. This refresh ran no builds or games.
- **Ultimate fighters:** the shared IR pipeline installs a fighter on its own skeleton. Sora's
  source id is `trail` (default name `Ultimate Trail`, token `ultimatetrail`); Ultimate Kirby uses
  `kirby` (name `Ultimate Kirby`, token `ultimatekirby`). Sora has ACMD conversion, Geno magic and physical-special generators,
  effect packages and bindings, UI art, alternate costumes and conversion-loss/position audits.
  The Aerial Sweep carry-profile change was reverted in workspace `e7d5246`; do not report it
  as part of HEAD. See `ports/README.md` for the actual entry points and slot conflicts.
- **Geno:** JSON version 5, with additive v5.5 features: 16 articles per profile, on-hit dispatch,
  counter windows, lock-on/stick aim, animation-rate writes, HBDMG, HBSTUN and HBFLAGS. Native
  `.gfx.json` effect simulation and rendering and fighter `fx_bindings` exist. Generated output
  and visual fidelity still need their own verification; a renderer is not proof of parity.
- **Fighters/rendering:** 94 m-ex slots, 255 PC fighter parts, 0x20000-byte animation buffers;
  optional 64-envelope PC palette POBJs with a `pobj_palette: 1` engine requirement. MEM1 is
  40 MiB; snapshots share pages and the netplay protocol is 3. Aurora has CPU-side indexed-array
  comparison, interpolation for palette draws and the host UI on interpolated presents.
- **Scripting:** offline stage lines, attached models, real Target Test targets, camera control,
  six Adventure enemy kinds, fly/teleport, boss-defeat holds, `gd.set_damage` and `gd.hit` are
  registered. `gd.input` holds count completed logic frames, including single stepping; extra
  PADReads while paused do not consume them. LAB input-driven export steps one frame per tick.
- **1P:** scene launch supports Classic, Adventure and All-Star with step/difficulty fields.
  Retail table lookups for m-ex fighters, AllA animation-heap capacity and step bounds have fixes.
  Classic step 7's IntroEasy projection uses `Mtx44` (`d07539c59`). The boss-hit work landed
  (`8fccfdc27`); those old queue entries are no longer unmerged tasks.
- **Build/run:** a single Python scan finds stale game TUs; bridge regeneration writes only
  changed bytes and relinks until the generated table agrees with the link map. `run.sh --test`
  exports turbo by default; `--realtime` clears it. Headless `--test` itself has no paced frame
  driver. `MELEE_FPS=u` uncaps presentation, not game logic. `GW_JOBS` sets compile jobs (content-hash rebuilds, tools/port/README.md).

## Pending work and decisions

The queue records intent, not proof that a lane is still running. Recheck its tree and report
before resuming it; do not reuse the old alpha/echo/beta assignments as current ownership.

1. **Four-Sora frame arena:** `4c676892a` sets Aurora's storage buffer to 24 MiB. Its source
   comment cites a 10,573 KB four-Sora peak; this replaces the temporary 64 MiB measurement
   setting. The vertex buffer is 12 MiB; overflow drops remaining draws. Recheck the queued
   `codex-frame-arena-report.md` and matching run/library before claiming flicker is resolved.
2. **Platform exporter:** the queued `codex-platform-model` work exports GD's Blender BF_Platform
   and adds a `model=` platform option. HEAD has `gd.stage_add_model{platform=handle}`;
   `gd.stage_add_platform` still reads only `passthrough` and `ledges`. The exporter/shortcut
   is not part of this audited HEAD.
3. **Build speed (done 2026-09-27):** content-hash rebuilds and `GW_JOBS` are merged (round 3). Measured on
   a lane: warm no-op 4.0 s, one TU 5.5 s, reverts rebuild nothing, a narrow header rebuilds its one consumer.
4. **Menu art:** replace `menu/out/2x/frame_edge_v.png`, `frame_edge_h.png` and the four
   `frame_corner_{bl,br,tl,tr}.png` pieces. Decide how the 1x copies and generator change too.
   Make the engine menu kit and art generators parametric. Existing frame pieces are still
   generated and consumed; neither task is done.
5. **Move grafting: estimate only, do not build.** GD asked about replacing one Melee fighter's
   move with another's. The earlier estimate was 1-2 days for a normal/throw graft tool plus
   LAB checks, and roughly half a day to two days per special. These are planning estimates,
   not measured delivery times. `build_melee_fighter.py` now handles any retail fighter; the
   move-graft tool itself is not established by that generalisation.
6. **Sora effects:** GD requires Ultimate particles in place of the procedural spell models.
   The importer, native effects runtime and bindings now exist; compare the installed spell
   effects against the source before closing the request. `trail_magic_models.py` still exists.
7. **Workspace move:** later, with agents and games stopped, move to `E:\Projects\Melee Workspace`
   or a nearby location. Repair both repos' worktrees, update `.env`, lane/build paths, mod/run
   references and path-keyed agent memory. Ghidra can move separately. Nothing was moved here.
8. The queue reports stage-pool reservation on the results screen. Treat it as an observation
   needing a current log, not a confirmed defect. Leave the three VPS crash reports untouched
   under GD's existing instruction.

## Operating rules and traps

- **Agents build; GD tests** visual/controller behaviour. Use numeric/log evidence, a visible
  main-desktop window, ACE by default, level-0 CPUs and `MELEE_VOLUME=3`. Check free RAM (8 GiB
  baseline); normally one game per agent. Stop only a PID you started, after checking its path.
- Build with `tools/port/build.sh`. Inspect errors and the final bridge ABI audit. A sandbox
  contains a copied EXE/map: changing source or the baseline EXE does not refresh a live run.
- Use separate build and run roots. `agent_new.sh` hardlinks baseline objects; inspect the local
  game-TU writer before assuming writes are isolated. Shared Aurora rebuilds affect every lane.
- `MELEE_MODS_DIR` names the parent of mod folders. Native Windows code needs Windows paths:
  use Git Bash `pwd -W`, not `/c/...`. Confirm mounted mods in the log.
- Inspect each failed run's `melee-pc.log` and crash logs; a harness summary is not diagnosis.
- Script pad claims survive gaps as connected neutral input. Release them explicitly or let the
  owning task/script end. Legacy text pad scripts still count PADReads, not Lua logic frames.
- Turbo requires scripted input or LAB batch export and refuses netplay. Hidden turbo frames
  skip display lists/skinning by default; `MELEE_TURBO_DRAWS=1` retains that work. Use realtime
  for presentation timing and controller checks.
- No disc-derived assets in either repo. No push, publish or merge to shared branches without
  GD's go. `.github/README.md` takes precedence over the root README on GitHub.
