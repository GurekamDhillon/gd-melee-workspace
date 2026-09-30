# Roguelite implementation handoff (2026-09-30)

Companion to `ROGUELITE-COMPLETION-PLAN.md` and `ROGUELITE-ACCEPTANCE.md`.
This records what the current pass delivered, the interfaces a next agent
consumes, and the exact next steps. No live runtime behavior changed: the game
still runs the v1 fixed route.

## State

Patches 1–4 of the plan's suggested sequence are done and committed (pure,
offline-verified). Gate 3 certification and Gate 4 runtime wiring are **not**
done and must not be claimed.

Pure modules (`melee/worktrees/linux/pc/scripts/examples/roguelite/`):
`rng.lua`, `codec.lua`, `checkpoint.lua`, `legacy.lua`, `room_catalogue.lua`,
`room_recipes.lua`, `encounter_catalogue.lua`, `progression.lua`,
`topology.lua`, `adapter.lua`, `inspector.lua`, frozen `dungeon_v1.lua`.
`prepare.py` bundles them; `main.lua` gained versioned diagnostics.

## Interfaces (injected dependencies, no globals)

```lua
local Top    = Topology.new(RoomCatalogue, EncounterCatalogue, Progression, Rng)
local v2     = Top:generate(seed, {attempts=32})      -- schema v2 manifest
local Adapter= require adapter  -- Adapter.new(RoomCatalogue, RoomRecipes)
local view,why = Adapter:manifest(v2)                 -- refuses uncertified recipes
local text   = Inspector.render(v2)
local cp     = Checkpoint.encode({generation=n, profile=…, run=…, manifest=Codec.encode(v2), roster=…})
local mig    = Legacy.migrate(tbd2_text, {core=Core, codec=Codec, checkpoint=Checkpoint, v1=DungeonV1})
```

## How to run

```sh
cd /home/gd/melee_linux_test/gdm
python3 -m unittest discover -s tools/roguelite -p 'test_*.py' -v
```

## Next steps (gate order)

1. **Gate 3** — follow `docs/ART-BRIEF-branch-rooms.md`: install the extra BF
   models in `prepare.py::install_room_kit`, reconcile the upper-door visual
   transforms with `room_recipes.lua` anchors, capture the per-template native
   traversal/combat clips, then set `certified = true` only for certified
   templates. Do not flip `certified` without clips.
2. **Gate 4** — consume `adapter.lua` in `main.lua`/`rooms.lua` behind an
   explicit version switch. Legacy saves keep v1 (`run.progress.room` is a v1
   id); new v2 runs store instance ids. Replace `main.lua`'s `node.id=='approach'`
   and `arena_a/arena_b` literals and `Rooms.plan()`'s eight-id whitelist with
   manifest/template/encounter fields. Update `test_runtime.py`,
   `test_rooms.py`, `live_acceptance.py` to data-driven invariants; never delete
   a contract just to go green.
3. **Gates 5–12** — genes/actions, enemies/AI/bosses, inventory, commands,
   regions/FX (incl. the new Gate 9 vocabulary subsection), audio, platform
   parity, playtest. See the plan.

## Defects found and fixed this pass

- `progression.lua`: the objective bitmask added `2^(bit-1)` unconditionally, so
  revisiting a required room carried into another objective and falsely
  completed an unvisited room. Fixed with an idempotent, LuaJIT-safe bit set;
  `test_progression.py` reproduces the old failure.
- `progression.lua`: added `grants_consumable` for real resource-aware search.

## Known limitations

- All `room_recipes.lua` entries are `certified=false`; the adapter refuses
  every manifest until Gate 3 clips exist. This is intentional.
- Consumable-key search is bounded but the manifest content (key sources) is
  minimal; expand with the lock catalogue.
- The content counts in plan §3 are targets, not met; no category is padded.
