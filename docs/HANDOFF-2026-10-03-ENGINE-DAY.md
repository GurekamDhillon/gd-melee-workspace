# Handoff: 2026-10-03, the engine day (missions, shaders, menus, Envoy groundwork)

Written 2026-10-03 13:55. This supersedes the "What is left" part of `HANDOFF-AUDIT-REPAIRS-2026-10-03.md` for everything
after the audit repairs; that file remains the record of the repairs themselves. Nothing is committed or published in
either repository: both trees are dirty by design, and GD has not asked for a commit.

## State of the build

`_build/melee-pc.exe`, built 13:5x: bridge fixpoint, ABI audit 18,827/18,827 with 0 wrong-convention, provenance recorded,
native suite 236/236. Aurora was rebuilt with a carried patch (`_build/patches/aurora-gd-surface-v1.patch`); rebuilding it on
this machine needs the Build Tools toolchain selected explicitly (recipe in memory `aurora-rebuild-needs-buildtools`).
Jobs still writing source when this was written: Codex Envoy slice 1 (Lua), maze generator (Lua/Python), six-slot matches
(engine C: the next build must wait for it or it will not stamp).

## What exists now, and how far each was checked

"In game" means run in the real game on the vanilla disc in the LAB by a verification lane, with measurements.

| Area | What | Checked |
|---|---|---|
| Mission folders | `gd.mod_read/list/stamp`, content-stamped model reload (128 assets), 64 collision lines per mesh, `gd.stage_hide`, fly range 49,000, `gd.player` contact fields | In game, two rounds |
| Missions mod | `melee/pc/scripts/examples/missions/`: load a folder, chunks, reload, play-from-marker, fly commands, CPU parking, retries, camera modes (follow / chunk / shaft) | In game two rounds; camera modes being measured now (round 3) |
| Blender exporter | `tools/blender/gd_mission/` + kit collision: walls (winding fixed), pass-through floors, `gd_solid` ceilings, walk-through doorways, one shared atlas, object names, camera fields | In game: walls, platforms, ceilings, doorway with Mario/Ganondorf/Bowser, 11 reloads |
| Effects behind map pieces | Kit pieces draw once in the first stage pass; translucent pieces split far/near | In game, before/after screenshots |
| Widescreen menus | Kit canvas widened and centred, full-bleed strips, scroll cue, Widescreen row, default on for wide windows, AUDIO page restored, descriptions fit | In game at 4:3, 16:9, ~2.25:1; fix2 (description width, breadcrumb, select band) NOT yet checked |
| Shaders | Mod WGSL with hot reload, `gd.post_*` chains, custom materials and glass, `gd.light_set`, fighter/stage surface shaders | In game; no GPU-time number; object-id post-processing unsupported |
| Camera | `gd.camera_params` (zero gains remove the origin skew), no log flood | In game |
| Fighter modifiers | `gd.fighter_mod` damage dealt/taken, run/air speed, shield | In game, exact ratios; damage also scales knockback |
| Reserve fighters | `gd.fighter_bench/call/benched`, per-entity state, refusals | In game, incl. Ice Climbers and Zelda |
| Contacts | `gd.contacts`, events, JSON trace, `gd.wait_until`, console commands, debug overlay | Traces and wait in game; overlay visuals need GD's eyes; console `wait` log line unverified |
| Clank | Engine `on_clank` event, `gd.hitstop`-style timed freeze, pass lifetime helpers; throwaway demo `experiment/clank_impact/` | Shown to GD: sword/sword, fist/fist, sword/fist, sword/projectile |
| Controller remapping | SETTINGS > CONTROLS remap page, profiles, presets, safety restore | NOT run in game; tap-jump-off unresolved (needs a netplay-safe design) |
| Envoy | Spec approved (`docs/superpowers/specs/2026-10-03-supertime-envoy-design.md`); slice 1 code being finished by Codex | Never run in game |
| Maze generator, six-slot matches | With Codex | Not built |

## Rules learned today (also in memory)

- `cpu0` does not make an opponent idle in the LAB. Test probes call `gd.cpu_mode(port,"stand")` and log it. Zelda/Sheik
  needed both halves set (fixed today, unverified in game).
- Scripted input does not drive a CPU slot: use a human slot (`p2=marth/hu`) for a fighter a script must pilot.
- Agent test windows go on the second monitor (`MELEE_WINDOW_X=-1080 MELEE_WINDOW_Y=-360`, width <= 1080), never hidden.
- A Codex job can die at start with "Selected model is at capacity": check for `turn.failed`, not just output.
  `codex exec resume` takes `-c 'sandbox_mode="workspace-write"'`, not `-s`.
- Building while a Codex job writes C refuses the provenance stamp; the exe is still usable for testing.
- Give credit always: `CREDITS.md`.
- The slippi-ai / Phillip idea was dropped by GD: do not pursue.

## Open defects and unverified items

1. Mission completion was 9/10 before the retry fix; re-measuring in round 3.
2. Controller remapping: nothing verified in game; tap jump off needs a design (offline-only, or a setting both peers exchange).
3. Shaders: GPU cost unmeasured against the 120 fps target; `gd.fx_shader`, MSAA modes and palette fighters untested; one
   capture showed no fighters with all three surface shader types active (unexplained).
4. Glass: the new material is visible; the old kit glass without a material sidecar is still faint.
5. Shield bubbles and dust draw over a wall that is in front of the fighters (believed to match vanilla; not confirmed).
6. `background=true` kit pieces are invisible unless the host stage is hidden.
7. Menus: three small polish items in fix2 unverified; mouse mapping, resize while open, results screen, true 21:9 unchecked.
8. One-folder vanilla fighter mods: design note with eight owner decisions, not started
   (`_research/vanilla-single-folder-mods-2026-10-03.md`).
9. Sora: parked items listed in `docs/superpowers/plans/2026-10-03-audit-repairs.md`; GD moved on from Sora.
10. Savestate/rewind with benched fighters, modifiers and reloaded assets: untested.

## Decisions GD made today

Envoy rebuilt from scratch; mazes and hand-built levels, authored in Blender; one Chao-like companion, hub-only first, a hub
garden, enemy-dropped drives; the companion's colours paint the fighter; a working menu system before any art; shipping Chao
assets is probably fine (packaging still open); proper widescreen fix; widescreen default on for wide windows; six-slot
matches wanted; shader items 1-4 all wanted; contact events with a debug overlay; the clank demo is a throwaway but its
engine capabilities stay.

## Where things are

Codex packets: `docs/prompts/codex-*.md`; their reports: `_build/tmp/codex-*-report.md`. Verification evidence:
`_build/audit-20261003/` (`mission-verify/`, `batch2-verify/`, `shader-verify/`, `render-effects/`, `menus-art/`,
`clank-demo/`, `mission-integ/` build and suite logs). Research notes written today: `_research/*-2026-10-03.md`.

## Evening update (written 21:57; supersedes the sections above where they differ)

**Build.** `_build/melee-pc.exe` built 20:28, STAMPED (bridge fixpoint, ABI audit, provenance). Native suite 255/256: the
one failure is `script_sound_options` (the test needed `luaopen_math`; fixed in `gw_script_sound_tests.inc`, not yet
rebuilt). Carries: the staging crash fix (`fighter ground no under Id` is no longer fatal on PC and the loader verifies
floor before release), the stage-switch music/cover hang fix, standalone drive items with hover/size/spin, native zones
(`gd.zone_add`, `on_zone_enter/exit/none/some`, `gd.zones_at`), the zone-based room camera, `gd.sfx` options.
An engine job is editing source now (`docs/prompts/codex-no-hitch-engine.md`); it could not run a compiler, so expect
compile errors, and it touches `melee/extern/aurora` (rebuild Aurora: memory `aurora-rebuild-needs-buildtools`).

**Checked in the game this evening**
- Generated maze, seed 7 size 12: walked by a lane with real inputs and then played to the goal by GD
  (`_build/audit-20261003/maze-gen/`, launch line in its report; `owner-mods` is the copy GD played).
- Envoy: two runs started back to back in one session, no crash (`_build/runs/envoy-smoke3`). Nothing past the first room
  of slices 2-4 has been played. Runs fall back to authored rooms because the maze kit is not in the Envoy mod.
- Hitch measurement (`_build/audit-20261003/maze-hitch/`): first draw of an enemy kind builds render pipelines inline
  (Goomba 6 pipelines ~1.2 s, Koopa 4 ~0.75 s; `pipeline_cache.cpp` ~1395); 2-3 chunk installs on one frame cost 20-44 ms;
  the loading hold always runs to its 10 s ceiling (`gmscene.c` ~538-551). Lua fixes verified in a copy: warm at load,
  one install per frame (38.8 -> 11.2 ms). Still 11-14.5 ms per room crossing until the engine work lands.
  The profiler works; `gd.perf(1)` costs ~4.5 ms per call.

**GD's verdicts and decisions this evening**
- Drives as pickups "felt nice"; wanted hover, 2.5x size, visible spin, eye and ear candy (done in source, unseen).
- Stats were not felt: more slices for progression (slices 2-4 written). "Reach is a stupid stat": replaced by Jump,
  approved. Stats are Power, Speed, Guard, Jump.
- Room camera "too eager" at doorways; GD proposed non-physical zones per room and per transition, with a defined
  behaviour outside every zone. Built both in Lua and natively.
- Maze: "Read lightly as a maze"; platforms too close to ceilings (clearance rules); floor holes are fine (keep them);
  camera ok; wants mazes interconnected across seeds (maze world of regions); approved pluggable layout algorithms
  (recursive backtracker, braid knob, lock and key). Hitching on room entry and the start-up wait: "CANNOT have that".
- Blender look work: first Sonnet palettes "look terrible"; a hand-built doorway and a guided Sonnet stone kit were
  acceptable studies; a parametric round based on `melee/pc/assets_src/bf_platform/` crashed Blender (null material in the
  depsgraph). GD: "forget it for now". Everything is in
  `_build/audit-20261003/maze-themes/recovered/session_autosave_2145.blend`; renders beside it. Rules for a next round:
  work in a scratch .blend saved per piece; never delete a material or node group in use; do not introspect
  `modifier.properties`.

**Codex queue at 21:57** (packets in `docs/prompts/`, reports in `_build/tmp/codex-<name>-report.md`)
- running: `maze-fix2` (clearance, variety, maze world), `no-hitch-engine`, `envoy-replace-reach`
- queued on the maze thread, in order: `maze-fix3` (Lua no-hitch), `maze-fix4` (pluggable algorithms)
- done, unverified in game: `mission-runtime-fix9` (zone camera), `native-zones`, `drive-polish` (+ merge into Envoy),
  `envoy-slices-2-4` (+ fix1), `maze-fix1`, `stage-switch-fix5` (hang only: full vanilla stage teardown and
  re-initialisation is NOT done and needs its own packet), `roster-stress` (63-Sonic mod fills 94 slots; 100 refused).

**Next, in order**
1. When `no-hitch-engine` finishes: rebuild Aurora and the game, fix compile errors, suite; cold-sandbox walk of maze seed
   7 expecting no `pipeline wait` lines; measure worst frame per room entry and the loading hold.
2. Play-check for GD: Envoy with Jump, the hub, evolution and the polished drives; the zone camera at doorways; a maze
   from the retuned generator and a maze world.
3. Still never run: controller remapping, the profiler benchmark scenarios, the 94-slot roster in game, stage switching
   against vanilla side by side (Randall lap, Fountain platforms, ledges).
4. Owed packets: full vanilla stage teardown for mid-match switches; exporter zone markers; maze kit into the Envoy mod.

