# Roguelite implementation handoff (2026-09-30)

Companion to `ROGUELITE-COMPLETION-PLAN.md` and `ROGUELITE-ACCEPTANCE.md`.
Next-pass assignment and coordinator review corrections:
[DeepSeek execution instructions](DEEPSEEK-NEXT-PASS.md).
This records what the current pass delivered, the interfaces a next agent
consumes, and the exact next steps. No live runtime behavior changed: the game
still runs the v1 fixed route.

## State

Patches 1–4 of the plan's suggested sequence are done and committed (pure,
offline-verified). Gate 3 certification and Gate 4 runtime wiring are **not**
done and must not be claimed.

Pure modules (`melee/worktrees/linux/pc/scripts/examples/roguelite/`):
`rng.lua`, `codec.lua`, `checkpoint.lua`, `legacy.lua`, `progress.lua`,
`room_catalogue.lua`, `room_recipes.lua`, `encounter_catalogue.lua`,
`gene_catalogue.lua`, `enemy_catalogue.lua`, `audio_catalogue.lua`,
`progression.lua`, `topology.lua`, `adapter.lua`, `inspector.lua`, frozen
`dungeon_v1.lua`. `prepare.py` bundles them; `main.lua` gained versioned
diagnostics and `core.lua` allocates a fresh world seed per run.

Planning contracts (data, `implemented`/`certified` flags honest): the gene,
enemy and audio catalogues define Gate 5/6/10 targets without claiming
mechanics. `adapter.lua` refuses any manifest with an uncertified recipe.

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

## Next pass (2026-09-30, after coordinator review)

Per `docs/DEEPSEEK-NEXT-PASS.md`:

- Fixed `progression.lua` finite-pickup replenishment: v2 with stable one-shot
  pickup ids, claimed state in the search signature, bounded inventory and an
  explicit opened-door policy. `test_progression.py` reproduces the defect.
- Fixed `codec.lua` object key collision (number 1 vs string "1") by rejecting
  colliding canonical keys; documented numeric-key round-trip semantics.
- Section 2: `prepare.py` installs the full 21-model BF kit; `room_recipes.lua`
  reconciles the ascent to the reviewed visual transforms (top anchor and upper
  doorway both `x=39,y=26`) and models drop sockets as real `floor.openings`.
- Section 3 seam: `route.lua` composes generator/adapter/progress and validates
  a saved route semantically; `checkpoint.lua` TBD3 carries a progress section.
- Native harness confirmed working: `_build/agents/linux/melee --test --iso
  <iso>` runs 211 tests (3 pre-existing script failures: `script_pad_claim_gaps`,
  `script_pad_mask`, `script_lab_events`; unrelated to roguelite).

## Next steps (gate order)

1. **Gate 3** — follow `docs/ART-BRIEF-branch-rooms.md`: install the extra BF
   models in `prepare.py::install_room_kit`, reconcile the upper-door visual
   transforms with `room_recipes.lua` anchors, capture the per-template native
   traversal/combat clips, then set `certified = true` only for certified
   templates. Do not flip `certified` without clips.
2. **Gate 4 (in progress)** — the coordinator's immediate milestone is a real
   generated run entered through native TBD. Do these reviewable patches:
   a. Save layer: `main.lua` writes TBD3 via `Checkpoint.encode` with the
      resolved manifest + `Progress` record; load detects TBD3, else legacy
      TBD2/TBD1. Keep v1 generation while the save format changes, then switch.
      Update `test_runtime.py`/`test_integration_edges.py` to the new envelope.
   b. Generation: when certified recipes exist, `begin()` calls `route:create`;
      fall back to `Dungeon` v1 with a logged reason otherwise. Remove
      `main.lua`'s `node.id=='approach'`/`arena_a`/`arena_b` literals and
      `Rooms.plan()`'s eight-id whitelist on the v2 path.
   c. Runtime: per-socket doors (left/right at ±52, top at the upper doorway,
      bottom via segmented floor + one-way edge), merges, returns, discovered
      map, locks and one-time rewards; `rooms.lua` plans from
      `recipe`/`recipe.modules`.
   d. Native certification: install the bundle into an isolated profile, run
      normal-speed traversal/combat clips per template, then set
      `recipe.certified=true` only for certified templates. Do not flip every
      flag to make the adapter pass. If another agent is driving the game,
      arrange an exclusive handoff.
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

- Coordinator review reproduced two outstanding defects after the final pass:
  finite `grants_consumable` pickups replenish on room revisits, and the codec
  accepts numeric/string key collisions that its decoder then rejects. Fix both
  before v2 integration; see the next-pass instructions for reproductions.
- All `room_recipes.lua` entries are `certified=false`; the adapter refuses
  every manifest until Gate 3 clips exist. This is intentional.
- Consumable-key search is bounded but the manifest content (key sources) is
  minimal; expand with the lock catalogue.
- The content counts in plan §3 are targets, not met; no category is padded.
