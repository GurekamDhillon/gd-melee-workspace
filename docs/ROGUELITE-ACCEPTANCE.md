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

## Current coordinator audit — 2026-09-30

This snapshot supersedes older status descriptions below; the baseline and
previous-pass sections remain historical evidence. Helper implementations and
catalogue counts do not establish complete player-facing gates.

- Landed game `e47bbe785`: atomic-only checkpoint mutation plus reviewed room,
  encounter and reward runtime helpers. Native scripting group passed 34/34;
  this is scripting coverage, not a full generated-run acceptance.
- Landed certification revisions: game `24b164c5f`, wrapper `66e7818`.
  `python3 -m unittest discover -s tools/roguelite -p test_certify_rooms.py`
  passed 62/62; log `_build/deepseek-coordination/certification-root-review.log`.
- Native normal-speed Falco `branch_y` run:
  `_build/deepseek-coordination/native-certification-v7-summary.json` names the
  executable hash and captures. Ascent, return and upper fork arrived; lower
  fork attempt fell below the room. Return has a seam-pop candidate requiring
  review. The attempted controller path may be wrong; this does not prove the
  lower socket impossible. No recipe certification was granted.
- Watched physical-controller evidence supersedes the failed scripted lower-door
  attempt: Bluetooth 8BitDo Ultimate2C on port1, 900-frame branch trace with
  301grounded samples near x52/y0. Lower-door reachability demonstrated for
  Falco (`_build/deepseek-coordination/watched-branch-trace.json`). User reports
  snag/pop at ALL stairs/balcony/ramp/upperlanding joins, so movement quality
  remains failed/pending a collision seam fix and watched retest. No full recipe
  certification. Review queue: `docs/ROGUELITE-WATCHED-RETESTS.md`.
- Compact command/HUD/onboarding helpers landed: game `7ebd732ee`, wrapper
  `41deb17`; combined root discovery 182named tests plus module suites passed
  (`_build/deepseek-coordination/combined-menu-review.log`). Main loadout/HUD/
  onboarding integration and in-game readability acceptance remain pending.
- Additional native Falco merge-room evidence:
  `_build/deepseek-coordination/native-merge-v2-summary.json`: left incoming
  controller attempt fell, top incoming placement was refused. Startup needed a
  longer bounded wait; neither failed observation certifies the recipe.
- Genuine game PNG evidence lives in
  `_build/deepseek-coordination/native-previews-clean/`. User requires in-game
  PNGs only; mockups/reference-sheet galleries are not acceptance evidence.
- Live v2 campaign output is **not accepted or installed**. Returned corrections
  address pause/stock/encounter/rollback issues in stub tests; review still finds
  premature new-run profile promotion on failed saves and an unjustified
  `reset(true)` on live script unload. The second corrective pass returned 19 passing stub cases; independent review
  continues. It explicitly reports the missing native owner-cleanup seam.
- Inventory second correction landed: game `1be259f18`, wrapper `05be7a1`.
  Root reran 16/16 focused cases and the original adversarial forged heal999 /
  zero-cost probe now refuses without spending. Validation reconstructs a plan
  from authoritative context; equipment apply/revert rollback is tested. This is
  a pure service milestone: bundling, persistence and in-game effects/menu
  integration remain pending.
- Enemy/boss prototype review found occlusion/reaction fail-open behavior,
  stale confirmations, changed attacks after tells, invalid boss resume and
  missing defeat-to-completion persistence. Corrective worker active.
- Expanded layout prototype review found disconnected-floor reachability,
  nonfinite coordinate acceptance, interior ledges and ignored template themes.
  Correction landed (game `da7af1524`, wrapper `ec1b9e1`): 16 translation-
  normalized geometry groups across 29 templates, actual-arrival screening,
  nonfinite refusals, seam ledges corrected and template themes honored.
  Theme labels still share BF visuals; every recipe remains uncertified.
  Combined root discovery passed 176 named tests plus import-time module suites
  (`_build/deepseek-coordination/combined-layout-inventory-review-2.log`).
  Migration refusal fixtures now explicitly contain finite pickup history,
  independent of which optional room a generator seed selects.
- Gene-action and menu followups await independent review. Inventory/equipment,
  new enemies, expanded layouts and gene actions are not offered as completed
  native gameplay merely because worker tests pass.

Gate position: Gates 1–2 have substantial automated contract evidence; Gates
3–4 are the current native/integration work. Gates 5–8 have prototype or helper
work pending corrections and live integration. Gates 9–12 still require full
presentation, audio, platform, complete-run and human playtesting evidence.
There is no agreed weighted percentage denominator, and no 100/100 claim.

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

## Delivered this pass (patches 1–4 of plan §18)

Revisions: `gdm` `1f01ae4` (+ inspector/diagnostics commits) and `melee`
`7a91c0a` (+ inspector/diagnostics commits). All changes are additive; the live
runtime still uses the v1 route, so Gate 0's working build is preserved.

- Pure modules in `melee/.../roguelite/`: `rng.lua`, `codec.lua`,
  `checkpoint.lua`, `legacy.lua`, `progress.lua`, `room_catalogue.lua`,
  `room_recipes.lua`, `encounter_catalogue.lua`, `gene_catalogue.lua`,
  `enemy_catalogue.lua`, `audio_catalogue.lua`, `progression.lua`,
  `topology.lua`, `adapter.lua`, `inspector.lua`, frozen `dungeon_v1.lua`.
- Tests (run at discovery import): `test_rng.py`, `test_codec.py`,
  `test_checkpoint.py`, `test_catalogue.py`, `test_topology.py`,
  `test_legacy.py`, `test_inspector.py`, `test_progression.py`,
  `test_room_recipes.py`, `test_adapter.py`, `test_economy.py`,
  `test_world_seed.py`, `test_gene_catalogue.py`, `test_enemy_catalogue.py`,
  `test_progress.py`, `test_audio_catalogue.py`, `test_route.py`.
- Next pass (coordinator review): finite-pickup and codec key-collision fixes;
  full BF kit installation and reconciled upper-door/opening recipes; `route.lua`
  semantic save validation; TBD3 progress section. Native harness verified
  (211 tests, 3 pre-existing unrelated failures). Live v2 wiring and Gate 3
  in-engine certification remain, per `HANDOFF-ROGUELITE-2026-09-30.md`.
- `prepare.py` bundles the new modules; existing 35-test suite remains green.
- `main.lua` diagnostics gained `diag_version`, `runtime_ready`,
  `ability_ready`; `live_acceptance.py` consumes them.

Verified evidence (this revision): topology 1000 seeds valid + reproducible,
775 distinct structural signatures, 0 fallback, locks always keyed on a
mandatory room; TBD1/TBD2 dev fixtures migrate to TBD3 with a byte-identical
reconstruction of the frozen v1 route; codec/checkpoint reject corruption.

Boundary reached: Gate 3 (certified physical templates/mobility) needs authored
3-socket geometry and in-engine traversal clips; Gate 4+ need the native
runtime/Windows/hardware. These remain `planned`/`blocked`, not claimed.

## Requirement rows

| ID | Requirement | Owner | Depends on | State | Evidence / command | Limitation |
| --- | --- | --- | --- | --- | --- | --- |
| G0-1 | Baseline reproducible; tests isolated | coord | — | automated-pass | baseline suite above; fixtures copied | no live clip captured yet |
| G0-2 | Frozen v1 generator + save fixtures | coord | — | automated-pass | `dungeon_v1.lua`, `_build/roguelite-validation-saves/legacy-v1/` | — |
| G1-1 | Named deterministic RNG streams | worker | — | automated-pass | `rng.lua`; `test_rng.py` | not yet consumed by runtime |
| G1-2 | Bounded data codec beyond numeric-key 16 | worker | — | automated-pass | `codec.lua`; `test_codec.py` | independent of Core's frozen codec |
| G1-3 | Versioned checkpoint envelope (TBD3) | worker | G1-2, G1-4 | automated-pass | `checkpoint.lua`; `test_checkpoint.py` | A/B + atomic rename wiring is Gate 4 |
| G1-4 | Room/encounter/reward catalogue contracts | worker | — | automated-pass | `room_catalogue.lua`, `encounter_catalogue.lua`; `test_catalogue.py` | 20 rooms, 17 encounters incl. 3 bosses, 28 rewards, 8 unclaimed reactions; gene families/mechanics are Gate 5 |
| G1-5 | TBD1/TBD2 migration via frozen v1 generator | worker | G1-2, G1-3 | automated-pass | `legacy.lua`; `test_legacy.py` (incl. dev fixtures) | runtime still uses its own loader |
| G1-6 | Deliberate world-seed allocation (no repeated runs) | worker | — | automated-pass | `core.lua`; `test_world_seed.py` | advances `profile.world_seed`; legacy profiles fall back to `seed` |
| G1-7 | Bounded run-progress record, separate from manifest | worker | G1-2 | automated-pass | `progress.lua`; `test_progress.py` | runtime persistence wiring is Gate 4 |
| G2-1 | Variable connected topology, branches, returns, loops | worker | G1-1, G1-4 | automated-pass | `topology.lua`; `test_topology.py` (1000 seeds + adversarial) | not yet spawned in-engine |
| G2-2 | Progression validator (locks/keys/reachability) | worker | G2-1 | automated-pass | `progression.lua`; `test_topology.py`, `test_progression.py` | objective bitmask fixed to be idempotent; consumable keys need `grants_consumable` |
| G2-3 | Save/load preserves resolved manifest | worker | G1-3, G2-1 | automated-pass | `checkpoint` + topology round-trip tests | runtime adapter pending |
| G2-4 | Graph inspector shows distinct routes | worker | G2-1 | automated-pass | `inspector.lua`; `test_inspector.py` | text evidence, not in-engine |
| G2-5 | Revisit-carry false completion fixed | worker | G2-2 | automated-pass | `progression.lua`; `test_progression.py` | confirmed against old arithmetic |
| G2-6 | Finite pickups claimed once; no key farming | worker | G2-2 | automated-pass | `progression.lua` v2; `test_progression.py` | stable pickup ids, claimed state in signature, one-shot/opened-door policy |
| G1-8 | Codec refuses colliding object keys | worker | G1-2 | automated-pass | `codec.lua`; `test_codec.py` | numeric object keys canonicalize to strings; collisions rejected before output |
| G3-RECIPE | Recipe contract/resolver (all socket sides) | worker | G2-1 | automated-pass | `room_recipes.lua`; `test_room_recipes.py` | all recipes `certified=false`; native clips pending |
| G3-KIT | Full BF kit installed; ascent reconciled to visual transforms | worker | — | automated-pass | `prepare.py`; `room_recipes.lua`; `ART-BRIEF-branch-rooms.md` | installation tested in temp profile; native load not yet run |
| G3-OPEN | Real floor openings for drop sockets (no flag over solid floor) | worker | G3-RECIPE | automated-pass | `room_recipes.lua`; `test_room_recipes.py` | runtime segmented floor + directionality is Gate 4 |
| G3-CERT | In-engine traversal/combat certification per template | worker | G3-KIT | blocked | native harness available; clips pending | needs live normal-speed runs; not self-certified |
| G4-ADAPTER | v2 manifest -> runtime node adapter, certification-gated | worker | G2-1, G3-RECIPE | automated-pass | `adapter.lua`; `test_adapter.py` | live runtime still v1; needs certified recipes |
| G4-ROUTE | Route service: create/resume + semantic save validation | worker | G2-1, G4-ADAPTER, G1-7 | automated-pass | `route.lua`; `test_route.py`; `checkpoint.lua` progress section | stub-verified; native TBD entry not yet wired |
| G3-* | Certified physical room templates + mobility | worker | G2-1, G3-RECIPE | planned | `docs/ART-BRIEF-branch-rooms.md` | needs installed visual modules + in-engine clips |
| G4-* | Runtime world lifecycle + exploration | worker | G2-*, G3-* | planned | — | `main.lua`/`rooms.lua` adapter |
| G5-* | Action provenance + gene families | worker | — | planned | — | — |
| G5-GENE | Gene-family contract (6 families, 12 genes, authored reactions) | worker | G1-4 | automated-pass | `gene_catalogue.lua`; `test_gene_catalogue.py` | only cinder/rime implemented; mechanics are Gate 5 |
| G6-* | Enemies, bosses, fighter AI | worker | G5-* | planned | — | — |
| G6-ENEMY | Enemy behavior contract cross-checked with encounters | worker | G1-4, G5-GENE | automated-pass | `enemy_catalogue.lua`; `test_enemy_catalogue.py` | data only; AI/native wrappers are Gate 6 |
| G7-* | Inventory / collection / economy | worker | G1-* | planned | — | — |
| G7-ECON | Long-run economy simulation stays bounded | worker | G1-* | automated-pass | `test_economy.py` | pure model simulation, not an in-game playtest |
| G8-* | Commands, menus, onboarding | worker | G1-* | planned | — | — |
| G9-* | Regions / equipment / FX catalogue | worker | G5-* | planned | — | — |
| G9-VOCAB | Afterimages/tracers/halos/orbitals/surface/silhouette/contact/UI vocabulary with motion-clip acceptance | worker | G9-* | planned | — | new plan subsection; needs native render support inspection + clips |
| G10-* | Audio + world presentation | worker | G4-*, G9-* | planned | — | — |
| G10-AUDIO | Audio event map with buses, provenance, critical tells | worker | G1-* | automated-pass | `audio_catalogue.lua`; `test_audio_catalogue.py` | assets unassigned; mixing/playback is Gate 10 |
| G11-* | Platform parity, performance, delivery | worker | G4-*, G9-* | planned | — | needs Windows + hardware for full pass |
| G12-* | Full playtesting + polish pass | human | all | planned | — | human/hardware gate |

## Commands

```sh
cd /home/gd/melee_linux_test/gdm
python3 -m unittest discover -s tools/roguelite -p 'test_*.py' -v
```


### Native seam fix and enemy helper review

Explicit room-local floor seam calls are committed, with ambiguity/refusal and
rollback tests. The native patch is applied in root working files; Linux build,
bridge/ABI and actual-source ASan/UBSan tests passed. Full native suite: 214/214.
Full roguelite suite after room callers and enemy helper landing: 202 tests OK.
Evidence: `_build/deepseek-coordination/stage-seam-landed-evidence.json`.

The isolated watched-review profile is prepared with this build. User-reported
snagging at all ascent joins remains **pending a watched retest**; automated tests
are not human movement acceptance. All recipes remain uncertified. Enemy helpers
have 32 tests and exact observable-state/run ownership checks; they still need
native runtime wiring and normal-speed combat/tell/AI acceptance.
