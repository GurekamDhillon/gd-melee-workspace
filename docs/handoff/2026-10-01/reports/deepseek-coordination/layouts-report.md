I'll start by inspecting the workspace state and the key documentation.

Now I understand the constraints. Let me set up a todo list and begin implementation.

Now I'll write the independent wrapper test. Let me create it carefully.

Done. Independent Gate 3 catalogue expansion implemented and frozen; no commits made.

## Frozen files (this lane's owned outputs)
Game worktree `melee/worktrees/linux`:
- `pc/scripts/examples/roguelite/room_catalogue.lua` (+62) — 20→28 templates (additive; existing rows untouched), optional `theme`, new `RoomCatalogue.audit(recipes)`.
- `pc/scripts/examples/roguelite/room_recipes.lua` (+236/-…) — 8 new recipes with concrete module/collision geometry, `mobility_profiles`, `can_traverse`/`screen` (directed), theme-free `signature`; ascent check keyed off `upper_doorway`.
- `pc/scripts/examples/roguelite/rooms.lua` (+6/-2) — `recipe_plan` validates/records `recipe_version`; still reads only the resolved `node.room` snapshot.

Wrapper:
- `tools/roguelite/test_room_layouts.py` (new, unittest wrapper)
- `docs/ROOM-LAYOUT-EXPANSION.md` (new)

`branch_y`/`rejoin_merge`/`junction_cross`/`shortcut_door` transforms, `ASCENT_MODULES`, `Rooms` public API, and `prior recipe version` readback are preserved.

## API
- `RoomCatalogue.audit(recipes) -> {templates, distinct, by_role={role={templates,distinct_count}}, aliases, recipe_aliases}`
- `RoomRecipes.signature(recipe[,template])`, `RoomRecipes.mobility_profiles{standard,short_heavy,floaty,fast_faller,multi_jump}`, `RoomRecipes.can_traverse(a,b,profile)`, `RoomRecipes.screen(recipe,profile)`
- `Rooms.plan` recipe path now returns `plan.recipe_version`, refuses a malformed version.

## Results
- 28 templates, **19 distinct signatures**; roles: traversal 6, combat 7, branch+connector 4, rest+reward 4, boss 2 (all ≥ targets). Alias groups explicitly reported.
- New layouts: `traverse_stagger`, `traverse_bridge`, `combat_flank`, `combat_dais`, `combat_ring`, `boss_dais`, `rest_platform`, `reward_ledge`.
- `test_room_layouts.py` 5/5 OK (independent mesh/sidecar dims+hashes, socket transforms, safe arrivals, BF grid/bay/storey/unit-scale/seam rules, floor-once, directed screen, budget derivation from engine source, alias audit, no-regeneration readback).
- Regressions green: `test_room_recipes` (28), `test_catalogue`, `test_rooms` 13/13, `test_topology` (1000 seeds/647 sigs), `test_route`, `test_adapter`, `test_progression`, `test_checkpoint`, `test_legacy`, `test_dungeon`, `test_route_map`, `test_integration_edges`, and untracked physical/encounter/reward suites. Discovery = 120 tests, 6 errors, all pre-existing (`test_certify_rooms` missing `roguelite_certification`, `test_persistence`/`test_runtime` missing `menu/out_effects_study`; same 6 without my files).
- Every new recipe is `certified=false`; no native cap raised, no existing budget lowered; union of models stays the reviewed 10.

## Integration requirements
- Root owns native build/install/replays and merging. New templates flow through `adapter` → `Route:create` → `Rooms.plan` unchanged; v2 admission still refuses until root certifies recipes with normal-speed controller clips.
- Do not modify `main.lua`/`prepare.py` here (integration lane owns them); the live v2 path must be wired by that worker.
- Preserve the seeded dirty baselines (`main.lua`, `runtime_*.lua`, other docs) — untouched.

## Unavailable evidence
No native build, install, game run, screenshot, replay, camera/blast-zone, seam, body-clearance, recovery-margin, or human-feel evidence exists in this Linux headless lane. The catalogue is honestly left uncertified.
