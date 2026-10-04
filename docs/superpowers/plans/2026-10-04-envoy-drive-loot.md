# EM3 drives and expanded pool execution plan

Authority: docs/prompts/codex-envoy-modifiers-step2.md and approved design
sections 5, 6, 8, 8b and build order 2/3. Preserve dirty trees; no game build,
launch, commits, reset, stash or revert. No opponent rolls or Classic integration.

- [x] Extend shared-data pool/engine, stock-loss regression and synergy artefact.
- [x] Deterministic weighted drive generator, bag/four slots and full-bag tests.
- [x] Offline LAB controller bag, physical pickups, commands and checkpoints.
- [x] Independent review, regressions, bundle last, report and play script.

Interfaces: new drive_loot factory(D), drive_bag factory(D); pool affix/group/
weight metadata is validated by loot layer rather than combat schema. Normal
records declare prefix/suffix, group=id and weight. Uniques are fixed drives;
keystones remain a separate companion choice and never roll as affixes.
Bag contains compact immutable rolled records (colour, rarity, seed, depth,
affixes{id,tier}, unique id optional). Slot edits preflight the complete native
rule budget before publishing. New adapter modules stay <=400 editable lines.

Ruling: use current approved modifier effects and supported native API only;
unsupported named examples are reported and replaced by five honest fixed
uniques/three honest keystones, never approximated silently. Cost if wrong:
owner may prefer waiting for those engine primitives over alternative records.
Ruling: duplicate affix IDs across equipped drives contribute highest tier once,
consistent with existing max=1 modifier stacking; base implicits multiply with
caps. Cost if wrong: duplicate loot has less build value than additive stacking.
Ruling: inventory persists behind one tuning switch, default fresh on scene/run;
no profile migration or Classic attachment in this packet. Cost if wrong:
cross-session persistence requires a later save-format change.
Ruling: live LAB exactness remains unrun; full bag is serialized with sim_commit
and isolated roundtrip/replay tested. Cost if wrong: native integration still
needs actual LAB rewind_test differing_bytes=0 after an authorized build.

Ledger: implementation dispatched in parallel on disjoint owned files by the
subagent-driven-development skill. No commit-based review packages because the
packet explicitly prohibits commits and source trees include prior work.

Ruling: drive drop is an explicit console timeline edit using existing item_spawn
branching outside on_frame. Automatic opponent drops are out of scope. Persist
compact drop map at the next checkpoint; replay never respawns from Lua. Cost if
wrong: acceptance must test rewinding across manual-drop snapshot boundaries.

| Interface | Producer/consumer | Check |
|---|---|---|
| Pool -> loot | affix/group/weight/tiers | normal rolls only; five fixed uniques |
| Bag -> engine | highest-tier mods + multiplying implicits | native rule budget preflight |
| Bag -> adapter | snapshot/derive/equip/swap/discard | atomic edits and reserved drop capacity |
| Engine -> adapter | stock transient reset + set_build | persistent build restored on respawn |
| Adapter -> bundle | factories/hooks/expire/tick | root integrates once after contracts |
| Task1 | schema/records/tests | preserve approval; unsupported primitives excluded |
| Task2 | generator/bag/tests |10k deterministic rolls; strict records |
| Task3 | UI/drops/checkpoint/tests | no Lua collision or unjournaled frame spawning |
| Task4 | review/regressions/docs | no game-build or live rewind claim |

Baseline: two Lua suites fail their obsolete stock-loss expectations after the
integrator fix; task1/3 update these into persistence regressions. Existing
integration branches are explicitly retained by packet, not isolated/reset.

Ruling: collect ground drops before inventory edits, except keystone choice; refuse paused drops and drops with pending edits. This conservatively prevents pickup/index races without new native journaling. Cost: the owner must collect drops and resume before editing/dropping again.
Review: task1/2 accepted; task3 residual pickup race and missing native item handles corrected and read-only re-reviewed. Mirror Shard reconsidered because native clank payload supports the written percent-damage rule; adding Lua event context and generic clank damage effect rather than inventing a missing native API.

Final ledger: independent final source review ACCEPT, including Mirror Shard and both clank owners; source artifacts finalized, bundle regenerated last, 289 Lua/12 Python checks passed. Catalogue retains known demo_zones baseline failure. Live acceptance explicitly unrun per packet.
