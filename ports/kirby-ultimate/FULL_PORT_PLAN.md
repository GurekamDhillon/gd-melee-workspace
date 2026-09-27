# Ultimate Kirby native port plan

This plan supersedes the movement proof described in `README.md`. It targets a
playable character in GD's Melee/LAB, with Ultimate-derived movement, attacks,
specials, article behavior, costume and motion. Audio, effects and particles are
outside the requested completion gate.

## Current evidence and limits

- The current mod overlays vanilla Kirby (`PlKb.dat`) with 25 Ultimate movement
  values, five air jumps, uncharged side-B hitboxes, a local c00 costume, and 20
  converted clips. The LAB probe checks 19 movement/side-B facts. Melee Kirby's
  status handlers, hammer item, hurtboxes and most scripts still run.
- The Ultimate IR has 369 shared fighter parameters, 16 motion parameters and
  115 typed fields across four special and two projectile parameter lists.
  It inventories 1,602 c00 motions and
  parses public ACMD game scripts. Eight article names and their script owners
  are identified, but their numeric indices and runtime descriptors are unknown.
  It has **no decoded status/action table**. The public script version has not been binary matched
  to the local Ultimate 13.0.2 NRO. Status rules derived from filenames must be
  marked as inferred until the NRO or measured runtime confirms them.
- Meta Knight demonstrates the host shape: a Kirby-clone m-ex row, own `Pl*.dat`
  / `Pl*AJ.dat` / costumes, Geno `states` and `specials` for native callbacks,
  converted ftcmd and figatrees, article/model parts, then automated LAB checks.
  Its stages are `ports/halberd/tools/build_mk_slot.py`, `mk_slot_files.py`,
  `build_mk.py`, and `melee/pc/geno/geno_game_specials.inc`.
- An isolated `kirby_native` game worktree now has a parameterized m-ex slot,
  eight costume-file entries, an empty-motion-row loader fix, and Geno Hammer
  hold/weak/full release states. The slot spawns in LAB 5/5 with stock and
  experimental visual archives. The Hammer live-input probe passes 14/14,
  including hold walking and 19%/35% releases. A composed native-slot probe
  passes 16/16 across representative normals, throws, grabs, Final Cutter and
  Stone actions, and live ground/air Final Cutter input passes 12/12. These remain staged in an
  isolated slot pack; the default runner below still overlays Melee Kirby.
- The ACE m-ex fighter table has one empty row used by Brawl Kirby. With that
  pack and Meta Knight present, every loadable m-ex slot is occupied. A separate
  Ultimate Kirby slot therefore needs an **explicit** existing row to replace.
  The slot builder must require the chosen internal/external IDs and expected
  current fighter name; no installed pack chooses a victim implicitly.

## Build architecture

1. Keep the existing vanilla-Kirby overlay as the LAB development target until
   the native actions are verified. Build its `PlKb.dat` from the movement pass,
   then static ACMD-to-ftcmd normals, then special scripts, then install selected
   `PlKbAJ.dat` clips and `PlKbNr.dat` costume. Every pass accepts the previous
   output and records source IDs; later passes must preserve earlier script
   pointers and untouched motion rows.
2. Add a parameterized m-ex packaging pass. Clone Kirby's MxDt/PlCo/CSS/stock
   entries into the explicitly chosen row; write `PlUk.dat`, `PlUkAJ.dat`,
   `PlUkNr.dat` and `geno.json` attached to `PlUk.dat`. The generated shared
   MxDt starts from the Meta Knight/Brawl Kirby superset so those rows survive.
   Until a destination is chosen, this pass remains staged and is not mounted.
3. Use Geno state rows (`0x400+n`) for actions needing new transition/physics
   logic. New behavior IDs, callback IDs and parameter IDs append to the stable
   contracts in `geno.h`/`geno_game_v2.inc`; no existing ID changes. Per-move
   state stays in the snapshotted `GenoState.move_i/move_f` block. Plain
   animation/hitbox actions continue to use the host rows and ftcmd.
4. Use the existing Kirby hammer/Final Cutter/Stone visuals only as temporary
   LAB placeholders while article descriptors and attachment rules are decoded.
   Article ownership, despawn and rollback must be checked before calling a
   special native. The Ultimate hammer, cutter wave and Stone forms need their
   own locally built geometry and/or host object behavior.

## Execution order and gates

| Stage | Implement | Required evidence |
|---|---|---|
| 1. Static attacks | Ground/aerial normals, rapid jab, grab/throws, ledge and get-up attacks from mapped ACMD; matching clips | Structural row/script checks and LAB hitbox timelines against IR. Twenty-four static attack rows pass LAB. Rapid jab's eight-pulse loop passes archive/timing tests and live input 4/4 with a documented integer-damage approximation. Four throw absolute payloads and release frames pass a 5/5 LAB timeline; victim animations, other status behavior, and live grab/throw regression remain. |
| 2. Hammer charge | Start, hold, walk/turn/jump, weak/max release and air variants as Geno states; `hold_max_f=120`, `hold_walk_speed_x=0.4`, `charge_speed=1` from local PRC | LAB input/transition/charge/hitbox checks; mark inferred status edges until NRO confirmed |
| 3. Other specials | Inhale/copy, Final Cutter rise/descent/wave, Stone transform/fall/landing, each with ground/air edges | Final Cutter's ten rising sword hitboxes pass a 3/3 ground/aerial LAB timeline and live input route passes 12/12; native traces prove stock wave item spawn on ground and air. Stone host state and aerial hit pass a 16/16 composed-slot probe. Inhale/copy against Fox passes 9/9. Ultimate wave geometry/behavior, ground Stone source timing, and broader copy roster remain. |
| 4. Visual/body | Complete c00-c07 faces, puffed models, visibility/LOD, collision/hurtbox map; convert clips for every reachable action | Runtime pose/visibility inspection in LAB; no missing clips, invalid joints, or visible idle/walk/run/jump loop snaps; verify all eight selectable costumes |
| 5. Own slot | Package the verified files into explicit m-ex destination and bind Geno profile | Slot spawns, CSS selects, 19/19 prior probe and new attack/special probes on `PlUk.dat`; other installed fighters still resolve |
| 6. Regression | Damage, death, ledge, grab, shield, item, rollback/netplay paths | LAB scenario suite and full game test; no stale host-only special left reachable |

The completion gate is a playable LAB/versus fighter whose reachable movement
(including five air jumps), normals, grabs/throws, four specials, Kirby's copy
interaction against the Melee roster, and articles use the intended
Ultimate-derived data and native rules, with runtime model/animation inspection.
Melee has no Final Smash input, so Final Smash scripts remain IR inventory rather
than a reachable move. A green movement probe alone does not satisfy the gate.
