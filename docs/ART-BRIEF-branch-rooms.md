# Art/asset brief: branch rooms and upper doorways (Gate 3)

Status: recipe-v2 configuration reviewed; native certification pending.
Companion to `ROGUELITE-COMPLETION-PLAN.md` Gate 3 and `SOL-ROOMS-CHECKPOINT.md`.
The recipe contract (`pc/scripts/examples/roguelite/room_recipes.lua`) already
authors the analytic collision; this brief covers the **visual** modules, their
exact kit transforms, and the native certification each template needs before
`certified=true` and runtime admission.

## Why

Topology templates now declare three and four sockets (`top`, `bottom`) for
split/merge/detour/shortcut rooms. The runtime can only admit a template after
an in-engine traversal/combat clip exists. The installer now includes all 21
BF models from `menu/out_roguelite/room-kit/`; live recipe binding and native
collision/traversal verification remain necessary.

## Kit constants (authoritative)

| Rule | Kit metres | Game units (UNIT = 6.5) |
| --- | --- | --- |
| Structural grid | 2 | 13 |
| Floor/wall bay | 4 | 26 |
| Wall storey | 4 | 26 |
| Doorway opening | 1.6 × 2.6 | 10.4 × 16.9 |

Source of truth: `melee/.../bf_interior_room/README.md` and the
`BF interior` layout in `bf_interior_room/scripts/main.lua`. Parts already
carry their rear depth; do not add another offset. Mirror right-hand parts with
`scale_x = -1`.

## Required models (install into the roguelite mod)

Installed by `tools/roguelite/prepare.py::install_room_kit` (plus `.coll.json`):

- `bf_wall_doorway_4m` (already) — reuse for the **upper storey** doorway.
- `bf_stairs_4m_rise2m` — ground-to-balcony ascent.
- `bf_balcony_4m` — upper landing (solid top, interior seams no ledge).
- `bf_ramp_4m_rise2m` — balcony-to-upper-floor ascent.
- `bf_floor_4m` / `bf_floor_opening_4m` — upper floor and drop-through opening.
- `bf_floor_end_trim`, `bf_beam_4m`, `bf_rear_post_4m` (already) for trim.

Glass variants are optional and out of scope for the first certification.

## Authored transforms (reconciled, game units)

`room_recipes.lua` (`ASCENT_MODULES`) is authoritative: the BF interior
example transforms converted once to game units (UNIT 6.5), in the lane's local
frame (`ox` = lane centre, `oy` = floor).

| Part | x | y | depth | mirror |
| --- | --- | --- | --- | --- |
| Stairs_4m_Rise2m | −39 | 0 | 0 | no |
| Balcony_4m | −13 | 13 | 0 | no |
| Ramp_4m_Rise2m | 13 | 13 | 0 | no |
| Floor_4m (solid upper landing) | 39 | 26 | 0 | no |
| Wall_Doorway_4m (upper) | 39 | 26 | 0 | yes (faces the lane) |

The analytic surfaces align to the two landings: balcony `x=-13,y=13` and upper
floor `x=39,y=26`. Sidecar-derived slope lines run from `(-52,0)` to `(-26,13)`
for the stairs and `(0,13)` to `(26,26)` for the ramp. Bind these through
`gd.stage_add_line`; horizontal proxy platforms do not reproduce the mesh.
Do not substitute `Floor_Opening_4m` at the upper arrival: its hole lies under
the player. The `top` anchor is `{x=39,y=26}` and must equal the upper doorway origin;
`RoomRecipes.validate` enforces that agreement. Any change to these transforms
must update both the recipe and this brief together, and invalidates prior
certification.

A `bottom` socket is a real floor opening, not a flag over solid floor:
`recipe.geometry.floor.openings` carries the gap and the graph edge for that
socket must be one-way. `RoomRecipes.validate` refuses an opening without a drop
anchor and a drop anchor without an opening. The runtime builds segmented floor
collision around the opening and enforces directionality (Gate 4).
The actual opening is 13 game units wide, centered at `x=0` (edges −6.5 and
+6.5), not a full 26-unit bay. The drop trigger is `(0,-6)`; the safe bottom
arrival is `(20,0)`. A socket trigger and a destination arrival have different
purposes and must not be substituted for each other.

## Templates needing certification

| Template | Sockets | Required clip |
| --- | --- | --- |
| `lane_balcony`, `lane_fork`, `arena_tiered`, `rest_balcony` | in/out/top | ground ↔ upper traversal both ways; combat on both levels |
| `branch_y` | in/branch_a(right)/branch_b(top) | both exits reachable without tech; return |
| `rejoin_merge` | in_a(left)/in_b(top)/out | both entries reachable; merge flow |
| `junction_cross` | 4-way incl. top + bottom drop | all four reachable; drop is one-way and safe |
| `shortcut_door` | in/out + bottom drop | drop lands safely; return exists |

## Acceptance per template (then set `certified = true`)

1. Natural-control clip: enter every socket, traverse to every other socket at
   normal speed, confirm no seam pop, no stuck state, no out-of-bounds KO.
2. Mobility coverage: short/heavy, floaty, fast-faller, multiple-jump must reach
   every mandatory socket without advanced tech; record margins.
3. Camera/blast-zone envelope verified; recovery space exists for a fighter
   knocked off the upper level.
4. Drop socket: confirm it is one-way (cannot be climbed back arbitrarily),
   lands on the intended surface, and cannot strand the player.
5. Collision/visual agreement: no visible step the fighter cannot stand on and
   no invisible wall.

Store clips under a build-identified acceptance directory and reference them
from `docs/ROGUELITE-ACCEPTANCE.md`; only then flip `certified`.

## Out of scope

- New ornamental geometry beyond the kit.
- Palette swaps presented as new layouts.
- Shipping any disc-derived asset.
