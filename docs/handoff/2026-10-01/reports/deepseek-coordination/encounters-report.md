I'll start by exploring the codebase to understand the existing structures and APIs.

Now I have a thorough understanding. Let me check a couple more test files and the enemy spawn demo for style, then design.

Now I'll write the orchestrator module.

I need to fix a few issues: host cleanup and spawn-point indexing. Let me update the module.

Now the host cleanup:

Now the test wrapper:

Now update the test to set the global `gd` and use the public view:

All 7 pass. Let me run the full roguelite suite to confirm no regressions from the new files.

Let me refine the attach error reporting and do a final review of the module.

Let me harden cleanup for a partial gene-host attach failure (record the host before attaching):

Implementation complete. Stopping editing.

## Owned files (new, untracked; nothing staged/committed)
- `melee/worktrees/linux/pc/scripts/examples/roguelite/runtime_encounters.lua` (620 lines)
- `tools/roguelite/test_encounter_runtime.py` (7 tests)

The five pre-existing dirty game files (`adapter/progress/room_recipes/rooms/route`) and dirty coordination files were not touched. No `prepare.py`/`main.lua` wiring, no native/install.

## API (`RuntimeEncounters.new(Core, gd, {EnemyGenes,EnemyCatalogue,TechAI,Progress}, opts)`)
`opts`: `get_run`, `on_event`, `bounds`, `spawn_point`, `fighter_port`, `target_port`, `max_actors`(12), `max_custom`(8), `max_fighter_waves`(4), `max_respawns`(2), `cleanup_attempts`(4).
- `:begin(node, progress)` → `true,events` | `nil,reason` (transactional first live wave)
- `:update(progress)` → `true,events`; `:hit{handle,id,from,damage}` → `{handled,entity,host,...}`
- `:defeat(handle, progress)` → events; `:stock(port,before,after,progress)` → events
- `:clear()`; `:reset()`; `:plan(node)` (pure); `:states()`; `:composition()`; `:active_entity()`; `:status()`
- Events: `tell, defeat, stock, wave, clear, respawn, ignored, error`

## Supported specs / policy
- Custom actors: catalogue `host='adventure'` ∩ native spawn list (`goomba`, `redead;` koopa/like_like/octorok/polar_bear if catalogued) → `gd.spawn_enemy` + EnemyGenes host.
- `fighter` → TechAI CPU (skill from level 1-3/4-6/7-9), no gene host.
- `champion` → TechAI CPU + Core gene host, `+4` encounter potency, explicit `stocks=2` and `phase=kos+1` fed only by observed stock drops.
- Scheduling: consecutive custom actors share a wave; each fighter is a singleton sequential wave (one p2 port). Stable ids match route.lua `enemy_<room>_<serial>`; `progress.defeated`/`encounter_kos`.
- Refusals: no/empty/bad spec, unknown or described-but-unimplemented kind, champion bad family/multiple champions, too many fighter waves, actor budget, unvisited room, invalid progress. Fighter never silently dropped.

## Behavior verified (real modules + injected gd stubs, not native)
Rollback on spawn/attach refusal (actors, hosts, modifiers, no leak; `Core.snapshot` valid); duplicate/stale defeat + duplicate contact harmless; vanish/escape → bounded respawn then hard `error`, never defeat/clear; wave continuation + partial resume (defeated ids, boss `encounter_kos`); gene immutability + champion buff; cleanup retry/failure/budgets.

## Results
`python3 -m unittest tools.roguelite.test_encounter_runtime -v` → 7/7 OK. Full suite `discover` → 44 tests OK (1 skip). Lua syntax `luac5.4 -p` OK.

## Remaining main wiring (root-owned)
Instantiate the module and route `node.encounter_spec`/schema-2 progress; replace `on_enemy_defeated`/`previous_stocks` logic with `:defeat`/`:stock`; call `:update` in `on_frame`; expose its host for `apply_gene`/Visuals; `:clear()` in `cleanup`/room transitions; add the module to `prepare.bundle`. No claim of native combat or playtesting.
