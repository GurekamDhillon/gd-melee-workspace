# Art/asset brief: branch rooms and upper doorways (Gate 3)

Status: planning brief. Companion to `ROGUELITE-COMPLETION-PLAN.md` Gate 3.
The recipe contract (`pc/scripts/examples/roguelite/room_recipes.lua`) already
authors the analytic collision; this brief covers the **visual** modules, their
exact kit transforms, and the native certification each template needs before
`certified=true` and runtime admission.

## Why

Topology templates now declare three and four sockets (`top`, `bottom`) for
split/merge/detour/shortcut rooms. The runtime can only admit a template after
an in-engine traversal/combat clip exists, and the roguelite packet currently
installs only six BF models. The full kit (`menu/out_roguelite/room-kit/`)
already contains the needed pieces; they must be installed and bound.

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

Add to `tools/roguelite/prepare.py::install_room_kit` (plus `.coll.json`):

- `bf_wall_doorway_4m` (already) — reuse for the **upper storey** doorway.
- `bf_stairs_4m_rise2m` — ground-to-balcony ascent.
- `bf_balcony_4m` — upper landing (solid top, interior seams no ledge).
- `bf_ramp_4m_rise2m` — balcony-to-upper-floor ascent.
- `bf_floor_4m` / `bf_floor_opening_4m` — upper floor and drop-through opening.
- `bf_floor_end_trim`, `bf_beam_4m`, `bf_rear_post_4m` (already) for trim.

Glass variants are optional and out of scope for the first certification.

## Authored transforms (kit metres, from the BF interior example)

For the upper-door (top socket) geometry, in the lane's local frame
(`ox` = lane centre, `oy` = floor):

| Part | x | y (storey) | depth | mirror |
| --- | --- | --- | --- | --- |
| Stairs_4m_Rise2m | −6 | 0 | 0 | no |
| Balcony_4m | −2 | 2 | 0 | no |
| Ramp_4m_Rise2m | 2 | 2 | 0 | no |
| Floor_Opening_4m | 6 | 4 | 0 | no |
| Wall_Doorway_4m (upper) | 6 | 4 | 0 | yes (faces the lane) |

The analytic recipe ascent currently uses passthrough steps at
`(-22,9) (-6,18) (10,26)` with the `top` anchor at `{x=10,y=26}`. The visual
layout above must be reconciled to those anchors before certification (either
move the module transforms to the recipe anchors or adjust the recipe), and the
reconciled coordinates recorded in `room_recipes.lua` comments. The `top`
anchor must coincide with the upper doorway origin.

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
