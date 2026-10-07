# Next session - start here

**Current as of 2026-10-06 (this block wins).** Dated files supersede undated ones, and the newest
dated block below supersedes the older blocks under it, which stay as history. Checked against the
integration branches' logs since 2026-10-04: game `integration/2026-10-01/roguelite-100-game` at
`4c0cb4cc5`, workspace `integration/2026-10-01/roguelite-100` at `cd914b3`. This refresh ran no
builds or games; each "verified" below is what the cited ledger or progress file records.
Companions: `HANDOFF-2026-10-05.md` (Envoy, Turbo, CPU controller state and the owner's open decisions),
`_build/audit-20261003/windows-release/READINESS.md` (the release order; untracked, local).

**Now true.**
- **Atlas step 7 (2026-10-07; game `agent/atlas7`, workspace `ws/atlas7`; not merged): the MODS screen and the LAB.** The main menu's MODS row opens an Atlas screen
  (INSTALLED and CONFLICTS tabs, 256 mods windowed, toggles with cascade notes, X resolves, Y details, locked while online); the Settings MODS tab is unchanged until the owner
  has looked. The LAB's pause menu is an Atlas screen behind **`lab ui on`** (off by default; the legacy menu is the fallback), with its info panel, move timeline, mode strip
  and notices as HUD descriptions. Built on engine additions (stepper, tabs from Lua, the world backdrop, WITH tags, `gd.ui.token`, `gd.ui.entries` and `activate`, three HUD
  parts). **None of it has run in the game**: the proof list (Task 11 of `docs/superpowers/plans/2026-10-06-atlas-step7-mods-and-lab.md`) needs a window and the owner's look, and
  the retirement of the legacy pieces (Task 12) waits for it. Two spec corrections: the LAB has ten display modes, and step 7 needs step 3 (the HUD and the world backdrop).
- **Atlas step 1 is merged** (game `agent/atlas1`, workspace `ws/atlas1`; spec and plan in
  `docs/superpowers/`, ledger `.superpowers/sdd/2026-10-06-atlas-step1-components-and-envoy-bag/progress.md`).
  The `gd.ui` interface (screen stack, focus, pad/key/mouse input, parts, renderer budget, a Reduced Motion
  setting), its offline stand-in, nine `atlas-*` native test cases, the demo `demo_atlas_screen`, and three
  Atlas fonts (Barlow Condensed, Source Sans 3 Semibold, Hasklug Medium; 23 roles, pages tracked in `_build/ui`,
  licence and credit recorded). Reference: `docs/scripting.md` (`gd.ui`), `menu/CLAUDE.md`. Every task had review
  rounds; in-exe `script_` 78/0 and `kit_` 8/0 at the last build, no window.
- **The Envoy bag runs through `gd.ui` behind the `uxatlas` switch, off by default.** The legacy bag stays
  the default and the fallback. Local two-seat co-op shows only the top seat's bag under Atlas (legacy showed
  both): that is why Atlas cannot be the default yet (it needs per-port screen stacks, a spec-level change,
  raised to the owner). Ruling: A on toggle/choice rows goes to `on.change`; sliders fall through to `on.accept`.
- **Envoy fixes merged:** the pool split into bite-sized rules and a quieter match screen (`agent/envoy-split`
  work), drives picked up with A and a payout at the end of every stage (`agent/payout`), and the team and boss
  fixes (`agent/teamfix`: a teammate is not a foe, a payout runs once, a boss hand cannot be killed by a script
  write; `gd.match_end_pending`, `gd.player(port).team`). The softlock fixes (endless fall on the boss stage, a run
  started in the opening movie, an invalid bag slot) and the bundler's `safe_cb` wrapper are in. Their proofs in
  a game are owed (below).
- **Also in:** Geno slice 4 (the Courier, an original fighter on its own model; shield, retarget by limb), Geno
  format 9 in the checker, Envoy online first slices (protocol 5 in server, guard and docs), a performance record
  per run, the Linux build compiling again, and **Linux 0.1.8.2** (the package bundles nothing the graphics
  driver links against; fixes "No supported adapters" on current Mesa; notes in `tools/release/notes/`).
  `tools/release/VERSION` is still **0.1.7**; no 0.2.0 is cut.

**Open.**
- **Proofs that need a game window; run them only when the owner is away** (see traps): the Atlas bag and
  `demo_atlas_screen` in a window (look, focus cues at 640x480, real font widths, the Z+START chord), `uxatlas`
  on in a real Envoy run, the boss stage with burn present (does P1 ever fall for minutes; does the out-of-bounds
  watchdog cost a stock), a run begun from the title movie, the bag after a depth change, the payout and
  team-stage fixes in a full run, the Courier's Classic/Versus/stage checks (slice 4d items 3-4 are not done).
- **Unmerged branches** (game): `agent/motionfix` `9522c0d40` (shader-cache guard: a bad shader configuration
  no longer crashes the game or bricks its cache; built and unit-tested, never run in a game; a release blocker)
  and `agent/envoynet` `bba679110` (WIP: a native evaluator for triggered records, Envoy online stage 4).
  The main game checkout also has uncommitted `gw_script_motion.inc` and `pc/tests/motion_api_test.c` changes.
- **Release 0.2.0 blockers** (READINESS.md, in its order; recommended as a public test build): decide the
  release shape; merge and prove `agent/motionfix`; make `build_release.ps1` package Envoy's shaders and drive
  models and the Geno fighters; the owner's decisions in `HANDOFF-2026-10-05.md`; one real internet match on
  protocol 5 after the server is redeployed; the 114-run crash sweep on the final exe; commit the regenerated
  `gw_mex_bridge.c` before a strict build; `publish.ps1`'s stale "protocol 4" body; a Linux 0.2.0 at the same protocol.
- **Deferred minors** from the Atlas ledger (not defects of record): UTF-8 truncation in text fit, kerning pairs
  with non-ASCII characters dropped, the `png2gx --manifest` and `kit_ui.py` recipes failing from a clean tree,
  silent drops in `atlas_tokens.py`, grid scroll not written back.
- `DEVLOG.md` has no numbered section for this week; the ledgers and `_build/audit-20261003/*/PROGRESS.md` are
  the record (local, untracked).

**Geno full fighter (2026-10-05):** slices 2 and 3 are in `docs/superpowers/plans/2026-10-05-geno-full-fighter-slice2.md` (the plan and the road to slice 8). Slice 2 is built: a define with its own move set (`melee/pc/geno/mods/vanilla-striker/`, format 7); the lesson is `docs/learn/geno-fighters/11-defined-fighter.md`, the sweep and ranked gaps are in `10-known-gaps.md` section Z, the engine reference is `melee/docs/geno.md` 22.1.

**Controller remapping source pass (2026-10-03):** CONTROLS now has a controller-only
remap editor, device profiles, presets and shim input transforms. Report and
integrator/owner acceptance steps: `_build/tmp/codex-controls-remap-report.md`.
Libclang syntax checks passed; no game build, game launch or executable test run
was performed. Tap-jump-off is still outstanding; do not describe the whole
controls packet or the under-one-minute/controller usability goal as accepted.

**Audit repair handoff (2026-10-03):** read
[HANDOFF-AUDIT-REPAIRS-2026-10-03.md](HANDOFF-AUDIT-REPAIRS-2026-10-03.md) first for
the current uncommitted repairs, focused test evidence and remaining integration
work. The user requested handoff before the full game build and gameplay
acceptance. That dated handoff supersedes earlier repair progress claims; the
Envoy requirements below remain in force.

**Envoy gameplay correction (2026-10-02):** read
[ENVOY-PROBLEMS-2026-10-02.md](ENVOY-PROBLEMS-2026-10-02.md) before treating the
current prototype as accepted gameplay. It supersedes earlier optimistic Envoy
readiness summaries: the default is one physical traversal level that ends and
repeats, not the requested spatial maze/campaign. The dated acceptance document
retains individual test evidence; it does not establish gameplay completion.

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
`_build/agents/alpha/sora/bak-v6/ultimate-trail-slot/` is a complete **fighter** mod — id
`ultimate-trail-slot`, name "ULTIMATE SORA (Ultimate, own skeleton)", `kind: "fighter"`, and it
**must not be enabled beside `metaknight-slot`** (both claim ACE row 51/52). It ships `files/`
(GnTrailFire/Ice/Bolt/Cloud, `MxDt.dat`, `PlCo.dat`, the CSS/ifall USDs), a **Geno v4** `geno.json`
(Firaga/Blizzaga/… states, `attach: PlUs.dat`, host behaviour = Marth) and **114
`fx/P_Trail*/*.gfx.json` effect packages** (the magic, Keyblade and Counter sets). To verify: put the
slot under a mods parent, point `MELEE_MODS_DIR` at that parent, run on the **ACE** disc, pick Sora in
the scene grammar (try the m-ex name first, then `mex:<row>`), drive a cast from the console
(`gd.press(1,"B",-1)` in a ground state) and read `gd.fx()` for the attached `P_TrailFire*` package,
plus a capture for the visual. Guides: `docs/prompts/codex-sora-effects.md`,
`_research/geno-effects-runtime.md`.
**First probe (2026-09-28) — installs, loads its effects, wrong fighter selected:** with the slot copied
under `_build/agents/batcha/sora-mods/` and `MELEE_MODS_DIR` pointed at it, the port mounts it
(`gw: mods: ultimate-trail-slot fighter 0.1.0 on`, 11 new paths), reserves the Geno article region and
**the effect runtime loads Sora's packages** — e.g. `P_TrailKeybladeFlare` (2 emitters),
`P_TrailSmashHiFlash` (12 emitters, 8 textures, 6 meshes), `P_TrailSmashLwImpact` (16 emitters). So the
effects half is proven with real content. What is **not** proven is the fighter: `p1=mex:51` selects the
disc's own `zero` (a Link clone: `char=57`, `anim_symbol=PlyLink5K_Share_ACTION_Wait_figatree`), so
`gd.fx()` is `{}` after `gd.input(1,"B",2)`; `p1=mex:52` did not boot (runner `exit 127`, card error
`Failed to open file: SuperSmashBros0110290334`). Cause: `INSTALL.json` says the slot replaces **row
internal 52 / external 51** and takes `MxDt.dat` under a different table than this disc's row (ACE Build
v2.0.0's row 51 is `zero`). Next: identify the ACE build the slot's row targets, or re-run
`ports/ir/tools/install_ultimate.py` against this disc's tables, then select that fighter and re-check
`gd.fx()` for `P_TrailFire*`/`P_TrailKeyblade*` after a B press. A third probe with the fighter id as a
name (`p1=trail`) started **no match at all** (`gd.match().active == false`, `gd.player(1)` nil), so the
name form is not accepted for this slot; read the mod's own `MxDt.dat` / `INSTALL.json`
`moveset_rows` to learn the m-ex slot id the port expects, then select by `mex:<n>`.
**RESOLVED (2026-09-28) — demo option 1 is verified in-game.** The working recipe is the **alpha
lane's** setup, not a fresh slot copy: `MELEE_MODS_DIR="C:/gdm/_build/agents/alpha/sora/mods-gd-latest"`
(2 mods, enabled via its `enabled.txt`: `geno-lab` + `ultimate-trail-slot`) and the fighter **by name**:
`MELEE_SCENE="mode=training;p1=ultimatesora"` (`mex:` row selectors do not address this slot; the name
does). Verified on ACE Build v2.0.0: `gd.player(1).char_name == "ultimate sora"`,
`anim_symbol = PlyUltimateSora5K_Share_ACTION_a00wait1_figatree`, and after `gd.input(1,"B",90)` the
log shows `fx: P_TrailFireEnd attached … 2/2 emitter(s), refused 0`, `fx: bind Firaga call 3 … joint 78`,
a census of **44 live particles** (`fire3=7 fire1=5 spark2=10 circle2=1 …`), a magic hit on P2
(`geno: … on_hit: damage x100 500`) and the live query `gd.fx() = {P_TrailFireBullet, emitter_count=10,
live_particles=41, owner_kind=article}`. Captures: `_build/agents/batcha/sora-fx-cap2/now00.png` (the
fireball mid-flight) and `sora-fx-cap/now00.png`. The earlier `mex:51`/"zero" and `mex:52`/127 probes were
the wrong selector and a fresh-copy mismatch; the alpha lane's `mods-gd-latest` carries the matching
`MxDt` clone. **Next for a showcase:** a capture set per spell (Firaga/Blizzaga/Thundaga + Keyblade
smash), longer holds for mid-cast frames, and a side-by-side against Ultimate for the fidelity pass.
**Showcase captures (2026-09-28)** in `_build/agents/batcha/sora-showcase/`: `firaga.png` (Firaga
fireball mid-flight) and `sonic-blade.png` (side-B star flash) are **visually confirmed**.
`blizzaga.png` (down-B, `P_TrailIceShot`) and `thundaga.png` (up-B, `P_TrailThunderCloud` 5 emitters +
`P_TrailThunderBullet`) had the effects **live at capture/query time**. Re-examined at full size:
`blizzaga.png` **is a keeper** — a white/blue burst (the IceShot's impact cloud) is visible on the
platform edge beside the CPU. `thundaga.png` shows a sparkle over Sora, but the storm sky in it is the
**stage's own** background, so the cloud itself is still unconfirmed.
A 3-frame blind burst also missed (six frames across two casts): the visible window is **shorter than
one capture round-trip** (~0.4 s of PrintWindow latency). The reliable route for thundaga (and any
further spell) is to **gate the capture on a `gd.fx()` poll** — cast, then poll `gd.fx()` and capture
the instant it is non-empty — or to record a short video and pick the frame. Do not present
`thundaga.png` as an effect shot yet. **Recipe for a directional special:**
`gd.input(1,{y=-110},6)` (or `y=110`) **then** `gd.input(1,{buttons="B"},30)`, ~3 s between casts; a
simultaneous stick+B spec attaches nothing. Still to capture: Aerial Sweep and a Keyblade smash, plus a
side-by-side against Ultimate for the fidelity pass.

## Current code

- Release version is **0.1.7** (`tools/release/VERSION`; this line said 0.1.6 when written). HEAD has substantial work after that
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
- **No game windows while the owner is at the machine.** A lane launches none (focus theft); game-driving
  proofs wait until he is away, then run on the second monitor at `MELEE_VOLUME=0`, at most 8 instances.
- **Never kill games by image name.** A `taskkill /IM` ended the owner's play session. Stop only a PID you
  started, after checking its path. A frozen build folder also needs its `ui/`.
- **Run the Envoy Lua tests from the workspace root.** A lane's "23 of 65 fail, same at baseline" was a path
  artefact (unverified until rerun); all 65 passed from the root.
- **A build is refused when sources change under it** (the provenance check). Nothing else may edit the game
  worktree while an exe build runs; reviews are read-only and may overlap, fixes and builds are serial.
- **The Atlas link list is the workspace `_build/melee_link_objects.rsp`.** A lane building another game
  branch must carry the `gw_ui_*` units, or the link drops them.
- **A test run as the developer console can hide ownership bugs**: `gd.ui` judges a handler by its slot owner,
  not `gs.cur`, and `gs.cur` is -1 in the tick. Tick tests with a non-console owner.
- **The subagent usage limit can stop a lane mid-commit.** Check the tree for a finished but uncommitted
  edit, verify it, then commit; do not redo it.
