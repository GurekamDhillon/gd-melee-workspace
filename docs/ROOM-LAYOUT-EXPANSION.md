# Gate 3 room-layout expansion — 2026-09-30

Status: **authored and unit-tested; not installed, not native-certified.** This
document wins over any undated room-layout note. It covers the bulk catalogue
expansion owned in this lane: `room_catalogue.lua`, `room_recipes.lua`,
`rooms.lua`, `topology.lua` (theme-contract fix, root reviews separately), the
wrapper `tools/roguelite/test_room_layouts.py`, `tools/roguelite/test_topology.py`
(theme-contract assertions) and this file.

Every recipe here keeps `certified = false`. The certification gate in
`adapter.lua` still refuses the whole v2 manifest, so these layouts cannot spawn
actors. Normal-speed controller replays in the real engine remain the missing
evidence and are owned by root (native builds and game runs).

## 1. What changed

- `room_catalogue.lua`: nine additive templates; **20 → 29 templates**. Existing
  templates, roles, sockets, shapes, themes and the public API (`validate`,
  `templates_for_role`, `get`, `by_role`) are unchanged. Added
  `RoomCatalogue.audit(recipes)`.
- `room_recipes.lua`: nine new recipes with concrete module/collision geometry;
  a **geometry-only** `geometry_signature`; five named mobility profiles; a
  **directed, entry-based** `screen` with finite-coordinate refusal; and an
  `upper_doorway`-keyed ascent check. The four reviewed recipes (`branch_y`,
  `rejoin_merge`, `junction_cross`, `shortcut_door`) and `ASCENT_MODULES` are
  byte-for-byte untouched.
- `rooms.lua`: `recipe_plan` validates and reads back `node.recipe_version` and
  records it on the plan. Geometry is read from the resolved `node.room`
  snapshot only; the live recipe table is never consulted for an existing node.
- `topology.lua`: `add_room` honors a template's declared `theme` contract
  (`template.theme or assigned`), so generation no longer contradicts authored
  themes. Assigned primary/secondary routing is otherwise unchanged and routes
  still validate.
- New wrapper `tools/roguelite/test_room_layouts.py`; extended
  `test_topology.py`.

## 2. Honest geometry diversity vs. aliases

Diversity is **geometry diversity**, not a metadata signature. The canonical
signature includes only movement geometry (floor span, openings, platforms,
slopes, module placements) and ignores camera, spawn, arrivals, socket names,
shape labels and theme; it is normalised by translation, so a moved copy is the
same layout.

Current result: **29 templates, 16 geometry-distinct layouts.** The old
20-row catalogue hid aliases; `audit()` reports every group with more than one
member.

Declared geometry aliases (after the fix):

| geometry | templates |
| --- | --- |
| flat full-ground lane | `entry_gate`, `finish_gate`, `lane_open`, `lane_straight`, `teach_lane`, `arena_flat`, `rest_alcove`, `reward_vault`, `boss_arena` |
| side platforms over a gap | `lane_pit`, `arena_drop` |
| reviewed ascent (stairs/balcony/ramp/solid landing) | `lane_balcony`, `lane_fork`, `arena_tiered`, `rest_balcony`, `branch_y`, `rejoin_merge` |

`branch_y` and `rejoin_merge` are the same surface as the ascent and now alias
honestly; they differ only in socket topology, which is not geometry.

Geometry-distinct layouts per content role (targets from plan §3):

| group | distinct geometry | target |
| --- | --- | --- |
| traversal | 6 | ≥ 5 |
| combat | 7 | ≥ 4 |
| branch + connector | 4 | ≥ 3 |
| rest + reward | 4 | ≥ 2 |
| boss-capable | 2 | ≥ 2 |
| **total** | **16** | ≥ 16 |

## 3. New layouts (concrete geometry)

All coordinates are game units (UNIT 6.5, 13-unit grid, 26-unit bay/storey,
floor `[-65, 65]`). **Every new layout keeps the full ground floor as its
mandatory route; the raised surfaces are optional ledges.** None of these
layouts forces elevation or a jump on the mandatory path — the ground route
from the entry to the exit always exists. Platforms are one-way
(`passthrough = true`) ledges except where a surface runs into a ramp/seam, and
modules reuse only the ten BF models already cached by the reviewed ascent.

| template | role | surfaces (x, y, width) | modules |
| --- | --- | --- | --- |
| `traverse_stagger` | traversal | (-26,13,20), (0,26,20), (26,13,20) | floor ×3 |
| `traverse_bridge` | traversal | (-39,13,26), (39,13,26), (0,26,26) | floor ×3 |
| `combat_flank` | combat | (-13,13,26), (13,13,26) | ramp(-39,0), floor ×2, ramp(39,0,mirror) |
| `combat_dais` | combat | (0,13,26) | floor ×1 |
| `combat_ring` | combat | (0,13,26), (-26,26,20), (26,26,20) | floor ×3 |
| `boss_dais` | boss | (0,13,26), (-39,26,20), (39,26,20) | floor ×3 |
| `rest_platform` | rest | (-26,13,20), (26,13,20) | floor ×2 |
| `reward_ledge` | reward | (-39,13,26), (0,26,26) | floor ×2 |
| `crossing_door` | connector | (0,13,20) over the real drop | floor ×1 |

`combat_flank` is a continuous ramp → walkway → ramp chain: every edge of its
two 26-wide bays is an interior seam (ramps at ±26, the bays meeting at 0), so
both surfaces carry `ledges = false` per the BF placement rule. `crossing_door`
is the only new geometry with a real floor opening: a one-way bridge at
`(0,13)` sits above the reviewed 13-unit gap, so a run can cross above or drop
through.

## 4. Themes are contracts, not three distinct art sets

The nine new templates declare `cobalt`, `fire` or `frost`. `topology.lua` now
honors those declarations: across 100 seeds the test found **327 themed rooms
and 0 theme-contract mismatches** (previously two-thirds contradicted their
template). Encounter/reward filtering uses the resulting room theme and every
route still validates.

**This is not three visually distinct themes.** All BF kit modules sample the
same kit atlas; the three themes are composition/encounter/presentation
contracts, not separate art. Do not claim visual distinctness until Astra
supplies and native runs verify distinct art.

## 5. BF kit rules enforced and tested

`tools/roguelite/test_room_layouts.py` inspects the real installed kit and the
engine, not copied builder constants:

- **Unit 6.5 / grid 13 / bay & storey 26.** Structural plan parts and recipe
  modules are on the 13-unit grid and a storey; structural parts are unit scale.
- **Doorway replaces a wall bay.** No solid wall shares a bay with a portal.
- **Posts meet seams; beams meet storey tops.**
- **Floor collision once.** Floor segments split exactly on each authored
  13-unit opening; no platform fills an opening; platform collision and its
  scaled visual module agree.
- **Ledges exterior only.** Any solid (`passthrough = false`) landing carries
  `ledges = false`, and a surface that runs into a ramp/seam is authored
  `seam_platform` (no ledges).
- **Sidecars/dimensions actually inspected.** Installed sidecars are compared to
  the independent exporter sidecars; mesh dims/hash/bytes against the manifest;
  collider endpoints against real mesh bounds; every slope is reconstructed from
  its part sidecar under the placed transform.
- **Safe arrivals.** Every socket arrival sits on a real floor/landing.

## 6. Budgets derived from engine source

| budget | value | source |
| --- | --- | --- |
| room instances | 28 (`Rooms.max_instances`) | `rooms.lua` |
| cached assets | 10 (`Rooms.max_assets`) | `rooms.lua` |
| explicit collision | 16 | `rooms.lua` `recipe_plan` |
| native model assets | 32 (`SCRIPT_MESH_ASSETS`) | `pc/gameworld/script_model.h` |
| native model instances | 128 (`SCRIPT_MESH_INSTANCES`) | `pc/gameworld/script_model.h` |
| native stage lines | 200 (`SCRIPT_STAGE_LINES`) | `pc/gameworld/script_game.c` |

The test reads these and asserts plans stay under both the Lua budget and the
native ceiling. **Native caps were not raised and the existing recipe runtime
budget was not lowered.** The union of models across all plans is still the
reviewed ten.

## 7. Directed mobility screening

`RoomRecipes.mobility_profiles` holds conservative screening envelopes, not
engine-measured fighter values:

| profile | jump_height | horizontal_gap | fall_gap |
| --- | --- | --- | --- |
| standard | 18 | 30 | 45 |
| short_heavy | 13 | 20 | 30 |
| floaty | 26 | 30 | 45 |
| fast_faller | 13 | 26 | 60 |
| multi_jump | 26 | 36 | 60 |

`screen()` now:

- refuses any non-finite movement coordinate (NaN or infinity) up front;
- seeds **only the surface at the actual arrival** (`spawn` by default, or
  `opts.entry`), never every floor, so disconnected floors must really be
  crossed (a zero-jump/zero-gap profile fails `shortcut_door`/`crossing_door`);
- requires **every required surface** (floor span or platform) plus every
  non-drop socket anchor and every drop edge to be reachable, so a raised
  unreachable platform fails;
- searches directionally (up needs a jump, down only the fall allowance), so an
  overhang is never reversed.

All 29 templates pass all five profiles in the test, and explicit negative
regressions confirm `shortcut_zero`, `crossing_zero`, `raised_unreachable`,
`nan_platform_y`, `inf_line` and an off-surface `entry` are refused. This is a
fast rejection screen; ledge grabs, body clearance, knockback and recovery
margins still need the native replay.

## 8. Versioning and saved routes

- Catalogue `version` stays `1` (schema unchanged; only additive templates), so
  existing v2 saves still validate.
- Every recipe stays `version = 2`.
- A resolved room stores `geometry`, `recipe_version` and `recipe_modules`; the
  planner reads those back and never regenerates from the current catalogue, so
  adding a layout or changing a theme cannot relocate a saved doorway.
  `adapter:check` still refuses a saved room whose geometry no longer matches its
  certification.
- The theme fix changes which theme a generated room gets, but not the resolved
  geometry; already-saved manifests carry their own geometry and theme and are
  not regenerated.

## 9. Tests and evidence

```sh
python3 tools/roguelite/test_room_layouts.py
python3 tools/roguelite/test_room_recipes.py
python3 tools/roguelite/test_catalogue.py
python3 -m unittest tools.roguelite.test_rooms -q
python3 tools/roguelite/test_topology.py
python3 tools/roguelite/test_route.py
python3 tools/roguelite/test_adapter.py
```

Passing: `test_room_layouts` 5/5, `test_room_recipes` (29 templates, uncertified),
`test_catalogue`, `test_rooms` 13/13, `test_topology` (1000 seeds, 647
signatures, 327 themed rooms / 0 theme mismatches), `test_route`, `test_adapter`,
`test_dungeon`, `test_legacy`, `test_route_map`, `test_progression`,
`test_checkpoint`, `test_integration_edges`, and the untracked physical/
encounter/reward runtime suites. `test_persistence` and `test_runtime` fail in
this worktree for pre-existing reasons unrelated to these files.

## 10. Not done here

- No native build, install, game run, screenshot or replay.
- No recipe is certified, and no generated run is claimed playable.
- The three themes are not visually distinct art; the BF kit is one atlas.
- Human feel, camera/blast-zone behaviour, seam contact, recovery space and
  actual fighter mobility remain unverified until root captures normal-speed
  controller clips per admitted template and mobility profile.
