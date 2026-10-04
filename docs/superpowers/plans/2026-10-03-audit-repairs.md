# Project audit repairs — 2026-10-03

Scope: the user requested fixes for both project audit reports. This is the
repair ledger, not evidence that gameplay has been accepted. Existing dirty
workspace and game changes are preserved; the starting diffs and changed files
are in `_build/audit-20261003/repair-baseline/`.

**Handoff requested 2026-10-03:** implementation has stopped for handoff. Read
[`../../HANDOFF-AUDIT-REPAIRS-2026-10-03.md`](../../HANDOFF-AUDIT-REPAIRS-2026-10-03.md)
for the actual implemented/tested state and remaining work. Checkboxes below are
acceptance gates; they are not a claim that unchecked tasks lack code changes.

## Constraints and acceptance

- Repair the observed behavior, with regressions that fail before the fix and
  pass afterwards. Use existing production functions and suites.
- Preserve save compatibility, transactional economy, native ownership,
  deterministic replay, current generated-content restrictions, and user edits.
- One writer per file. Root owns `gw_script.c`, build/run and acceptance tooling;
  Envoy owns its Lua/editor/arena changes; ports owns converters/Geno runtime;
  release owns launcher/packaging/server. Coordinate interface changes.
- Builds use `tools/port/build.sh`; separate build/run roots when needed.
  No publishing, shared-branch merges, or disc-derived commits.
- Record component tests, full builds and gameplay/controller acceptance as
  separate evidence. Never convert a simulated test into a gameplay claim.

## Tasks

### 1. Envoy/editor state integrity (envoy agent)

- [ ] Recover from zero-control error screens after storage failures.
- [ ] Handle already-dead enemy cleanup idempotently.
- [ ] Reconcile native savestates with Lua state without duplicating durable rewards.
- [ ] Persist starter collection state; make pending export/decline flow visible and deliberate.
- [ ] Restore bounds/spawns correctly on editor undo/load and track restored placement ghosts.
- [ ] Convert spawn world/local coordinates correctly, including restoration.
- [ ] Run Lua regressions and actual-source arena checks; root integrates game build.

### 2. Fighter conversion and Geno (ports agent)

- [ ] Correct baked motion-rate clocks for neutral and Hi/HiAir specials.
- [ ] Preserve same-frame command order and reject/report unknown ACMD conditions.
- [ ] Bind installed moveset audit provenance to the actual generated words.
- [ ] Allocate article slots across simultaneous attacks; reject unsupported nonzero rehit honestly.
- [ ] Preserve reflector speed multipliers in article travel velocity.
- [ ] Reject unsafe article layout/overlay relocation during in-place hot reload.
- [ ] Coordinate negative reload-result handling with root's `gw_script.c` changes.
- [ ] Run converter/native regressions and the affected IR suites.

### 3. Release/launcher/netplay (release agent)

- [ ] Make random matchmaking retries idempotent and room membership cleanup consistent.
- [ ] Bound pending matchmaking state.
- [ ] Align enabled-file parsing and dependency cycle checks with the engine.
- [ ] Make actual Qt deployment pass a precise package guard without allowing personal paths.
- [ ] Reject incomplete packages and bind release binaries to build provenance.
- [ ] Correct advertised launcher capabilities to the actual available flow.
- [ ] Run server tests, fresh Qt tests and positive/negative packaging checks.

### 4. Shared runtime/build/test tooling (root)

- [ ] Rebuild stale ENet content in fresh lanes without damaging hardlinked baseline objects.
- [ ] Protect active run directories from pruning.
- [ ] Make sweep success require progress near the end of the observation window.
- [ ] Repair native acceptance NameError and hardcoded effects/parts checkout paths.
- [ ] Fix negative Geno reload handling without reporting success.
- [ ] Make Lua rollback write permissions truthful and deterministic.
- [ ] Investigate/fix the recorded native Slippi link/test and Python suite failures.
- [ ] Run affected suites, one integrated build/bridge audit, and relevant native tests.

### 5. Envoy gameplay completion (envoy agent, after state repairs)

- [ ] Replace the one-level repeat with physical progression: meaningful routes,
  encounters, earned rewards, and a clear finish. Reuse existing battle/economy
  machinery and authored scale; preserve legacy saves.
- [ ] Make exploration and upper routes purposeful, preserve solo exploration,
  no elevated platform ledges, and consistent camera framing.
- [ ] Align menus/objectives/instructions with implemented behavior.
- [ ] Verify deterministic generation, connectivity, checkpoints and campaign transitions.
- [ ] Prepare a fresh native acceptance bundle. Controller/visual acceptance is
  recorded separately and remains open until observed.

### 6. Integration review (root with cross-review)

- [ ] Review diffs against the saved dirty baseline, resolve integration defects.
- [ ] Record exact tests and unresolved native/visual limitations per task.
- [ ] Update the handoff with repaired findings and remaining acceptance work.

## Progress

### 2026-10-03 resume (second session): measured outcomes

Nothing committed or published. Evidence is under `_build/audit-20261003/`; run logs under
`_build/runs/<name>/melee-pc.log`. Exe under test: game `378d79b20` plus the dirty tree, stamped
`_build/build-provenance.json`, `melee-pc.exe` sha256 `cad49c48d0e7a1d5…`, ACE disc.

| Gate | Result |
|---|---|
| Integrated build (`build.sh`, `GW_JOBS=4`) | Passed. First build: 3 game TUs and 6 shims rebuilt, bridge fixpoint at check 2/4. Final build after the last Lua edits: nothing stale, fixpoint at check 1/4. |
| Bridge ABI audit | 18,827 of 18,827 entries resolved against the live map; 0 read ECX/EDX in the prologue. |
| Build provenance | Recorded and `--verify` passed on the final build. `source_dirty: true` (both trees are uncommitted). |
| Native game suite (`run.sh --test`) | 218 passed, 0 failed, 0 `not ok`, no crash logs, on the final exe (`audit-native-final-20261003`). Includes `geno_registry_reload_layout` and `geno_v5_article_reflection`. |
| Native spawn regression | New `build.sh --native-test arena-spawn` (`pc/tests/arena_spawn_test.c`, `tools/port/arena_spawn_fixture.py`): actual `script_arena.inc`, `PSMTXInverse`/`PSMTXConcat`/`PSMTXMultVec` and `lb_8000B1CC`. Fails against the pre-repair source at the world readback; passes now (rotated, scaled parent; exact local restore under a moved parent; missing point, out-of-range slot and singular parent refuse without ownership). |
| Envoy snapshot error state | `on_loadstate` keeps `load_data`'s error menu when no durable slot is usable. `test_snapshot_load_keeps_the_loader_error_when_no_slot_is_usable` failed first, passes now. |
| Launcher packaging | `build_launcher.ps1` passed twice end to end: configure, build, CTest, deploy, sanitize, `deployed launcher runtime OK (SDK-free PATH)`. `check_release.ps1` accepts the actual deployed Qt bytes as folder and zip (233 files) and refuses the unsanitized SDK `Qt6Core.dll` (`further-release/actual-deploy-guard.txt`). Qt copies `NotSigned`, CRT and SDK originals `Valid`. A failing native tool stops the script (`native-exit-probe.txt`). Fixed: blank `Architecture:` in `qt-build.txt` (now `x64`). The game-side release bundle itself was not assembled. |
| Suites | roguelite 304 OK, 1 skip, 2 expected failures; `tools/port` 45 OK, 5 skips; IR 148 OK, 5 skips; server 14; release 14; effects 4; model-parts 11; sweep 4; native `script-policy` passed. |

**Sora regenerated into an isolated mod root** (`_build/audit-20261003/sora-regen/`, commands in
`regen.sh`, log `regen.log`; the working baseline mod under `_build/agents/alpha/sora/` was only
read). Moveset, magic, specials and install all exited 0 with no `--skip-acmd-audit`; installer
audit `passed`, 189 clips / 276 rows, 1,239 hitbox frames checked, moveset carries
`payload_sha256`. Two caveats: the default `_build/tmp/ir/trail.acmd.json` has no audit sidecar
and was refused, and the Ghidra dump is not on disk to re-parse, so the input was
`_build/tmp/codex-nodrop-run/trail.acmd.json`, the only parse whose sidecar matches the current
`acmd_parse.py`; and `fx/` (114 effect packages) was copied unchanged from the baseline because
these tools do not regenerate it. Native launch `sora-regen-20261003` (LAB, FD, vs Marth cpu0,
real pad input): fighter loads as kind 57 with 23 Geno states and 28 overlays; neutral special
enters Geno state 0 and spawns the Fire article with its model, which despawns on hit; up and
side specials enter their states; Marth took 19.2%. Timing against the source game, visuals and
feel were not assessed; that is the owner's test.

**Envoy: not accepted, and the owner now expects to rebuild it from scratch.** Task 5 stays open
and should not be finished by patching. What this session established:

- Independent geometry review (tests in `tools/roguelite/test_physical_campaign.py`, own
  reachability code, seeds 1–40): no ground bypass in any room, but sentinel, detour and champion
  share 79–82% of their geometry, five of seven rooms use the same staircase climb, and the seed
  only shifts floor holes. Those two findings are left as `expectedFailure`. Three rooms had pits
  with no way back to the door; those were fixed in `physical_campaign.lua`.
- Native run, real pad input (`gd.input`), fresh bundle, Falco (`envoy-audit-20261003e`): the
  entry room is crossed in 624 frames with three jumps, so the 18-unit staircase is no obstacle
  to a real fighter. The switchback's raised door refuses while its monsters live, and the Down
  press falls into the command tree with no "clear the room" message.
- Found natively and fixed: the pit fix pushed the entry room to 50–51 art instances against
  `Rooms.max_instances=48`, so it played with no art (`room visuals unavailable: physical
  instance budget`). New regression `test_every_room_fits_the_native_art_instance_budget`; the
  entry obstruction is now two bays wide (44–45 instances).
- Not exercised natively: any encounter, reward, rest, detour, champion, saved-v5 resume,
  failure/retry, camera or menu usability. Those remain double-based only.

**Mission layer for the kit map editor (new, at the owner's direction).** Lua only:
`map mission ...` commands, an optional `mission` table in v2 layouts, a pure state machine
(`scripts/mission.lua`, embedded in `main.lua` by `tools/port/map_mission_sync.py`), a sample and
35 stub tests (`pc/tests/map_mission_test.lua`, `tools/port/test_map_mission.py`). Native run
`mission-probe-20261003b` (LAB, Final Destination, Falco, real pad input): start, wave 1, wave 2,
checkpoint and goal, ending `mission: complete time=30.4s deaths=0 defeated=3`. Not exercised
natively: death/respawn and lives, time-out, restart, the HUD and marker overlay, editing commands.

### 2026-10-03 later: Sora redone against the game's own logic, mission layer verified, release bundle

Prompted by the owner: "Sora's side b works nothing like ultimate ... needs to be redone". Nothing
committed or published. Final exe `melee-pc.exe` sha256 `abbf83d0a820b744…`, provenance verified,
bridge ABI 18,827/18,827 with 0 wrong-convention calls, native suite **219/219** (ACE disc, run
`final-native-suite-20261003`). Suites: IR 204 OK (5 skips), kirby-ultimate 46, `tools/port` 45
(5 skips), roguelite 304 (1 skip, 2 expected failures), release 14, mission Lua 30 + 35.

**Sonic Blade (side special) rewritten.** Spec, cited to the decompiled status code:
`_research/ultimate-sonic-blade-spec-2026-10-03.md`. Baseline of the old move:
`_build/audit-20261003/sora-regen/sb-baseline.txt`. What was wrong: dash 1 was steered and locked
on (the real one is straight), the aim was clamped to 40/60 degrees and never downward on the
ground (real: full circle), one 8-frame freeze stood in for SEARCH (9) + TURN (8), the follow-up
needed B (real: stick alone or the special latched), speed never decayed, and the stronger
follow-up was keyed to "previous dash hit" (real: special latched and not stick-aimed).
- Engine (`melee/pc/geno`, documented in `melee/docs/geno.md`): hooks 8 `geno.dash.search`,
  9 `geno.dash.aim`, 10 `geno.brake`; value 0x3D STICK_LEN; phys `brake`; a `both`-coll landing
  keeps the script's horizontal speed; test `geno_v54_dash`.
- Generator: `ports/ir/tools/trail_specials_geno.py` (states SSearch, STurnUp, STurnDown added
  last so earlier state numbers hold), tests `test_sonic_blade.py` (7).
- Measured in the LAB (`sb-new-solo-1/2`, `sb-new-1`, `sora-final-2`): dash 12 frames at 3.2 then
  END 35; stick alone continues; 45 degrees gives (1.769, 1.769), 315 degrees (2.082, -2.082),
  straight up 2.502 then 2.302, back -2.944 then -2.708; powered 3.386 / 3.115; a target in range
  overrides the stick and is homed on at its live position; END 35/40/45 frames, air END with vy
  inside +-1.5.
- Not ported (listed in the generator header): the aim cursor and lock marker (Geno cannot attach
  an effect to another fighter), ledge grabs during a dash and the last-dash ledge assist, the
  35-frame head-on contact counter, the 0.98 factor, the exe-side start status timing. BEST-FIT:
  frame-11 `add_speed` taken along the heading; SEARCH/TURN hover; the target point is the
  opponent's position.

**The rest of the kit**, from `_research/ultimate-trail-specials-fidelity-2026-10-03.md`:
- Motion rate was inverted in the converter and (since the morning's repair) in both special
  generators: `FT_MOTION_RATE r` is game frames per clip frame. Jab first hit went from action
  frame 12 to 4; the morning's "divide by rate" repair was the wrong direction and is reverted
  (`test_motion_rate.py`, `test_audit_repairs.py`).
- Sora ran on Marth's attributes; `attr_apply.py` + `install_ultimate.py --attrs` now patch the
  calibrated set into the fighter file (table and readback: `sora-normals/attribute-table.md`).
- Dair rise-then-dive: converter kinetics + new value 0x3E FALL_LIMIT; measured +1.24 then -3.31.
- Magic: twelve cast states on the real `d00special*` clips (they played item-scope clips),
  Firaga chaining, air hop, shard lifetimes 13/15, cycle at cast entry (`test_magic_fidelity.py`).
- Aerial Sweep cancels into the side special in its 0xe600 window (measured: `sora-final-2`);
  the stick guard is BEST-FIT.
- Effects: `trail_fx_bindings.py --attach-to <mod>` replaces a manual step that the regenerated
  mods had been missing (no fighter-bound effects); bindings follow the new states (60 states).
- Registry JSON pool doubled (the merged profile was at 1,920 of 2,048 values).
- Combined mod: `_build/audit-20261003/sora-final/mods` (`regen.sh` there). The working baseline
  mod under `_build/agents/alpha/sora/` is untouched.
- Open: nair/fair hits 2-3 (design ready: `sora-normals/aerial-chain-design.md`), jab
  hit-confirm rule, Thundaga cloud placement, counter lunge scaling/rebound, four-slot hitbox
  drops, `geno.md` 19.8 (magic table) is stale, pending-review loss entries with
  `approved_by: null`. None of this was judged by eye; feel and looks are the owner's test.

**Mission layer** (`melee/pc/scripts/examples/map_editor`, evidence
`_build/audit-20261003/mission-native2/RESULTS.md`): death/checkpoint respawn (fixed: respawn slot
4 instead of a refused teleport), lives, time-out, restart/stop, editing in the running game, all
three objectives and the lost-enemy rule verified natively; added a mission tool with
click/drag authoring, trigger zones, timed and position-started waves, `map mission test`, a
multi-level sample. A real editor bug fixed on the way: the mouse mapping's matrix inverse
returned the cofactor matrix, so click-to-place could not have worked on the real camera. Engine:
the fly/teleport guard no longer refuses rolls, ledge states, taunts or a teetering fighter.

**Release bundle**: `build_release.ps1` to `_build/audit-20261003/release-bundle` passes the guard
on folder and zip (453 files). Three script defects fixed on the way: a tool missing from PATH
read as success, the launcher smoke hanging on a Qt message box without a console, and a relative
`-OutDir` corrupting the manifest paths. Non-strict run: both trees are dirty, so this is not a
publishable build.

2026-10-03: baseline captured; implementation starting in the current checkout so
the fixes include the audited uncommitted work. All source writers have disjoint
ownership; no commits are required for this repair pass.
