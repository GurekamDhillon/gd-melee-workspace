# TBD roguelite acceptance ledger

Companion to `docs/ROGUELITE-COMPLETION-PLAN.md`. One row per acceptance
requirement. A requirement is only `automated-pass` when a command in this file
was run against the revision named in the row; it is only `live-pass` /
`human-reviewed` when the evidence artifact names the build and operator.

State vocabulary: `planned`, `implemented`, `automated-pass`, `live-pass`,
`human-reviewed`, `blocked`. A requirement may carry several evidence types at
once; the weakest missing one keeps it out of "complete".

Severity: P0 crash/data loss · P1 softlock / broken controls / unreachable
required objective / broken supported platform · P2 major readability, fairness
or performance · P3 cosmetic.

## Baseline (Gate 0)

Recorded 2026-09-30.

- Workspace `gdm` revision `8c8f682da006b4e883ff7905a20b758d984a9a08`
  (branch `agent/linux-qt-launcher`), dirty files preserved, not reset.
- Game checkout `melee/worktrees/linux` revision
  `d67201cad8b5af87656c23e25716556ad8afa26a` (branch `agent/linux`), dirty.
- Native Linux build: `_build/agents/linux/melee`, sha256 prefix `910b1cefb5b7b9c1`.
- Disc: `/home/gd/melee_linux_test/Super Smash Bros. Melee (USA) (En,Ja) (v1.02).iso`.
- Save data: `_build/agents/linux/scripts-data/roguelite_main/` (`checkpoint-{a,b}.txt`).
- Baseline suite: `python3 -m unittest discover -s tools/roguelite -p 'test_*.py'`
  → 35 tests OK (see revision above).
- Frozen legacy generator + fixtures:
  `melee/worktrees/linux/pc/scripts/examples/roguelite/dungeon_v1.lua` and
  `_build/roguelite-validation-saves/legacy-v1/` (core.lua, dungeon.lua,
  checkpoint-a/b, config). Do not overwrite with destructive save tests.

Plan revision note (2026-09-30, by another agent): `ROGUELITE-COMPLETION-PLAN.md`
gained Gate 9 subsection `Expanded visual vocabulary — beyond bursts`
(afterimages, tracers/ribbons, halos, orbitals/fields, persistent surface
treatments, silhouette attachments, contact/world traces, combat/UI
connections) with a motion-clip acceptance bar; later sections renumbered.
This does not change Gates 1–8 or the command list. Tracked as G9-VOCAB below.

Known traps inherited from the plan §2 (still open): fixed eight-node route;
`main.lua` uses `node.id=='approach'` and `arena_a/arena_b` literals;
`Rooms.plan()` whitelists eight IDs; door geometry only supports two sockets;
Core codec numeric-key limit 16; transient native handles persist nowhere;
Adventure vanish unlocks traversal; `rogue_state` emits `ready` twice.

## Requirement rows

| ID | Requirement | Owner | Depends on | State | Evidence / command | Limitation |
| --- | --- | --- | --- | --- | --- | --- |
| G0-1 | Baseline reproducible; tests isolated | coord | — | automated-pass | baseline suite above; fixtures copied | no live clip captured yet |
| G0-2 | Frozen v1 generator + save fixtures | coord | — | automated-pass | `dungeon_v1.lua`, `_build/roguelite-validation-saves/legacy-v1/` | — |
| G1-1 | Named deterministic RNG streams | worker | — | implemented | `rng.lua`; `test_rng.py` | not yet consumed by runtime |
| G1-2 | Bounded data codec beyond numeric-key 16 | worker | — | implemented | `codec.lua`; `test_codec.py` | independent of Core's frozen codec |
| G1-3 | Versioned checkpoint envelope (TBD3) | worker | G1-2, G1-4 | implemented | `checkpoint.lua`; `test_checkpoint.py` | A/B + atomic rename wiring is Gate 4 |
| G1-4 | Room/encounter/reward catalogue contracts | worker | — | implemented | `room_catalogue.lua`, `encounter_catalogue.lua`; `test_catalogue.py` | initial finite catalogue is a subset of the §3 target |
| G2-1 | Variable connected topology, branches, returns, loops | worker | G1-1, G1-4 | implemented | `topology.lua`; `test_topology.py` (1000 seeds + adversarial) | not yet spawned in-engine |
| G2-2 | Progression validator (locks/keys/reachability) | worker | G2-1 | implemented | `progression.lua`; `test_progression.py` | persistent keys first; consumable search bounded |
| G2-3 | Save/load preserves resolved manifest | worker | G1-3, G2-1 | implemented | `checkpoint` round-trip test | runtime adapter pending |
| G3-* | Certified physical room templates + mobility | worker | G2-1 | planned | — | needs authored geometry / in-engine clips |
| G4-* | Runtime world lifecycle + exploration | worker | G2-*, G3-* | planned | — | `main.lua`/`rooms.lua` adapter |
| G5-* | Action provenance + gene families | worker | — | planned | — | — |
| G6-* | Enemies, bosses, fighter AI | worker | G5-* | planned | — | — |
| G7-* | Inventory / collection / economy | worker | G1-* | planned | — | — |
| G8-* | Commands, menus, onboarding | worker | G1-* | planned | — | — |
| G9-* | Regions / equipment / FX catalogue | worker | G5-* | planned | — | — |
| G9-VOCAB | Afterimages/tracers/halos/orbitals/surface/silhouette/contact/UI vocabulary with motion-clip acceptance | worker | G9-* | planned | — | new plan subsection; needs native render support inspection + clips |
| G10-* | Audio + world presentation | worker | G4-*, G9-* | planned | — | — |
| G11-* | Platform parity, performance, delivery | worker | G4-*, G9-* | planned | — | needs Windows + hardware for full pass |
| G12-* | Full playtesting + polish pass | human | all | planned | — | human/hardware gate |

## Commands

```sh
cd /home/gd/melee_linux_test/gdm
python3 -m unittest discover -s tools/roguelite -p 'test_*.py' -v
```
