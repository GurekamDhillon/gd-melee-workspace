# DeepSeek execution instructions — next roguelite pass

**Continuation update, 2026-09-30:** read
[`DEEPSEEK-BULK-HANDOFF.md`](DEEPSEEK-BULK-HANDOFF.md) first. The finite-pickup
and codec defects below are now fixed; the installer includes the full kit,
and Sol has delivered tested room/runtime module changes. Live `main.lua`
integration and physical certification remain pending. The newer handoff
supersedes the old task order and status here; retain these acceptance
requirements as background rather than redoing completed work.

Updated 2026-09-30 after coordinator review of the completed foundation pass.
Read this first, then `ROGUELITE-COMPLETION-PLAN.md`,
`ROGUELITE-ACCEPTANCE.md`, `HANDOFF-ROGUELITE-2026-09-30.md` and
`ART-BRIEF-branch-rooms.md`. This supplements the full completion plan; it does
not reduce that plan to another prototype or documentation-only milestone.

New-art ownership belongs to the designated Astra session, not automatically
to whichever model currently occupies root. The Astra pass has now delivered
an initial export/review pack; see [art delivery](ASTRA-ART-DELIVERY.md). Use
existing approved assets and send concrete requests without waiting to
implement unrelated work.

## Assignment and current truth

Continue implementation of the full offline TBD gamemode. The immediate
integration milestone is a real generated run entered through the native TBD
button, with certified physical rooms, branching/return traversal, safe
save/resume and no fixed-room assumptions. Complete that milestone, then
continue the later gates in the full plan. A new catalogue or interface alone
does not complete a gameplay feature.

The prior pass delivered useful pure modules and planning contracts. The live
runtime still uses the fixed v1 route and its old save path. All v2 physical
recipes remain uncertified; the adapter refuses them. The gene/enemy/audio
catalogues describe intended content, rather than implemented mechanics,
AI or sound assets. The fresh-world-seed change is in source; verify it in the
installed bundle before claiming live behavior. Keep these distinctions in
every progress report.

Review baseline: wrapper commit `eb70cf7`, game commit `ecf824146`. Inspect the
actual current heads and dirty files first; later work may supersede this
snapshot. Preserve existing work and the user's saves. Do not reset, clean,
overwrite the local collection or blindly stage unrelated changes. Reuse
existing modules instead of introducing a second generator/save architecture.

## 1. Fix the two confirmed defects before integrating v2

### Finite consumable pickups must not regenerate on every room visit

`progression.lua` currently adds `room.grants_consumable` each time its search
enters the room. This permits inventing additional keys by walking back and
forth, and can approve a run that cannot actually be completed.

Reproduction using the real module: required rooms A → B → C → D; A ↔ B is
bidirectional; B → C and C → D each consume one key. Only A grants a single
finite key, and there are no other sources. The current validator returns true
because repeated A/B visits replenish the pickup. With one-shot pickups and
two distinct locked doors, this graph must be rejected. With two genuine keys
it must pass. Re-entering A must not grant a second key.

Implement explicit, stable pickup identity and claimed-pickup state in the
search. Include claimed state in its visited-state signature: identical room,
inventory and objective mask can have different future possibilities when
different pickups remain. Do not assume an optional pickup is represented by
the mandatory-objective mask. Branch inventories/claim sets must not mutate
siblings. Bound quantities, pickup count and total search states; invalid or
excessive data must produce a controlled refusal.

Define and test the runtime lock policy consistently with the validator. If a
key opens a door permanently, remember that opened lock and do not charge the
return trip again. If a particular gate consumes on every traversal, declare
that policy explicitly and test the return route. Do not silently choose one
policy in generation and another in gameplay. A repeatable key source, if ever
designed, needs an explicit rule and bounded analysis; it must not be the
default for an ordinary room pickup.

Add focused cases in `test_progression.py`: the reproduction, two-key success,
optional-source revisit, independent sibling paths, multiple pickups, opened
door return semantics, and a controlled state-budget refusal. Confirm the
previous objective-bit carry fix remains intact.

### The codec must not encode an object it cannot decode

`Codec.encode({[1]='numeric', ['1']='string'})` currently succeeds with
`{"1":"numeric","1":"string"}`. `Codec.decode` rejects that output as a
duplicate key. This can make a supposedly successful checkpoint write
unreadable.

Choose and document an unambiguous key contract. Prefer rejecting mixed or
colliding object keys before producing output; retain legitimate contiguous
arrays and the frozen migration requirements. If numeric object keys remain
supported, detect collisions after canonicalization and document their
round-trip semantics. Do not overwrite one value, remove duplicate detection
from the decoder or fix this only at a single call site.

Add regression cases in `test_codec.py` for numeric/string collisions, supported
numeric-only objects, ordinary string objects, contiguous arrays and stable
encoding order. Every accepted value must round-trip according to the declared
contract. Re-run checkpoint and legacy migration tests after changing it.

Record both defects and their actual fixes/evidence in the acceptance ledger.
Existing green tests did not cover these reproductions; they do not invalidate
the findings. The coordinator re-ran both against the final foundation pass.

## 2. Complete real physical room support

Use the existing BF kit and placement documentation. Installing existing
stairs, ramps, balconies and opening-floor models is authorized implementation
work. The designated Astra session retains authorship of new final art; that does not block
loading and arranging the approved kit, collision work or runtime integration.
If a new visual asset is genuinely necessary, give the coordinator a precise
brief and continue all independent work with an honest labelled placeholder.

Reconcile the art brief's transforms with `room_recipes.lua`; they presently
describe different upper-door positions. Convert kit dimensions once and make
visual geometry, collision, socket anchors, arrivals, floor openings and door
triggers agree. A `bottom` flag over the current continuous solid floor is not
a physical drop-through opening. Specify directionality on the graph edge and
verify that the intended return path exists.

Keep authored door width/height, storeys, bay seams and module orientation.
Do not turn an arbitrary off-grid stack of platforms into a certified kit
layout by changing assertions. Reuse model metadata and validate actual mesh
bounds/sidecars, rather than testing constants copied from the implementation.

Certification requires live normal-speed movement through the real geometry:
each admitted template/socket, representative mobility types, fighting and
recovery on elevated surfaces, camera/blast bounds, collision seams, both
entries at merges and all supported return connections. Scripted ordinary pad
input is acceptable for repeatable checks; label it. Teleportation and debug
flight can inspect placement but cannot prove natural reachability. Capture
motion evidence with the tested build, template/recipe version and limitations.

Tie certification to the reviewed geometry/assets and mobility contract. A
later geometry change invalidates the old certification. Do not flip every
`certified` flag merely to make the adapter pass. Do not constrain generation
to the old two-door linear rooms and call that completion.

## 3. Connect the generator, adapter and saves to the live game

Read the current `main.lua`, `rooms.lua`, `core.lua`, `prepare.py`, adapter,
checkpoint and progress modules before editing. The adapter is an interface,
not proof that the runtime already handles every exit, actor or reward.

Implement these in reviewable patches:

1. Install/bundle the required assets and modules into an isolated test profile.
2. Admit certified template sets and create new v2 runs from the real generator.
   Remove fixed room-ID checks and the eight-room whitelist from the v2 path.
   Resolve encounters/rewards from manifest data; definitions lacking mechanics
   must not appear as functioning gameplay options.
3. Support per-socket doors, explicit destination arrival anchors, branching,
   merges, return traversal, discovered-map state, locks and one-time rewards.
4. Persist the resolved manifest and a separately validated progress record in
   TBD3. Validate graph shape, versions, seed/ownership, current room, visited
   IDs, pickup/lock claims and progression consistency before accepting a save.
   A checksum and syntactically valid table do not prove a valid run.
5. Keep legacy v1 runs resumable with their frozen generator. New saves must
   identify their route/schema version; never regenerate a saved v2 manifest
   using the current catalogue. Verify selected-fighter and running-fighter
   metadata independently, including costume and partners/transforms.
6. Wire A/B recovery and atomic temporary-write/rename if supported, adding a
   tested native helper if needed. Failures must retain the prior checkpoint
   and restore in-memory claims consistently. Unknown future versions are
   preserved and explained, not overwritten by a fresh run.
7. Finish explicit load/build/place/encounter/clear/reward/transition states,
   isolated-stage ownership, cleanup and error recovery. Preserve the existing
   incremental asset-load yields and Lua hook budgets. An enemy escaping or
   disappearing is not a confirmed defeat.

Use the actual native TBD menu entry for acceptance. Keep the compact HUD and
recursive D-pad controls: Left/Right/Down choose forks; Up goes to the parent
while traversing; Up taunts only at the root. Preserve vanilla behavior on exit.

## 4. Verify integration before expanding the catalogue further

Run focused pure tests for changed contracts, then the full roguelite suite.
Note that some new suites execute at discovery import: report those outputs
alongside the 35 named unittest cases, rather than inventing a combined count.
Use the native build/test entry points in the completion plan for native edits.

Perform real generated-run checks at normal speed on distinct seeds: topology
variation, both forks, backtracking, locks, encounter completion, rewards,
failure, victory and reload of the exact saved route. Include a legacy-save
resume, interrupted transition, rejected actor/model allocation, corrupt newest
A/B file, and save failure during reward claim. Never use the user's only
collection as a destructive test fixture. Record logs/clips durably under a
build-identified acceptance directory.

Run one shared game/build owner at a time. If you are the sole active agent,
act as that coordinator: build, install and run the checks yourself. If another
agent is driving the game, arrange an exclusive handoff. A need for native
testing is a work item, not by itself an external blocker or reason to stop at
pure modules. Missing Windows/hardware/human checks remain pending; continue
the Linux implementation and other available work.

After the generated-run integration gate passes, continue Gates 5–12 in the
full plan: action provenance, actual genes/reactions, enemies/AI/bosses,
inventory/economy, menus, roster/equipment effects, audio, platform delivery and
polish. The new afterimage/tracer/halo vocabulary remains planned until real
render support and motion evidence exist. Prioritize the working gameplay loop
before adding more contract-only content.

## Reporting and stopping rules

- Report what changed, what is installed/live, exact tests/builds, evidence and
  unresolved limitations. Commit only reviewed owned files; leave unrelated
  pre-existing work intact. Do not publish a release or tag.
- Update the ledger as work lands. A schema test proves a schema, not a boss,
  audio mix or playable room. Match completion claims to actual evidence.
- Do not call the overall assignment finished because a foundation pass was
  committed. Continue available implementation through the full plan.
- If genuinely blocked, identify the exact failed command/API, observed error,
  alternatives attempted and the smallest external dependency. Continue other
  independent work; do not invent native APIs or certify unsupported content.
- Human feel/polish and unavailable hardware cannot be self-certified. Prepare
  a reviewable build and a precise outstanding acceptance route when those are
  the only remaining checks.

## Copyable task message

> Continue from `docs/DEEPSEEK-BULK-HANDOFF.md` and its linked Sol checkpoints.
> The earlier finite-key and codec fixes are done. Implement the remaining safe
> save layer, live v2 wiring and native certification in bounded tested patches,
> preserving completed work and saves. Follow the full completion plan after
> the generated-run gate; distinguish live behavior from pending acceptance.
> Respect Astra art ownership, compact HUD, D-pad tree, offline scope and the
> no-release rule. The uncapped FPS experiment remains cancelled.
