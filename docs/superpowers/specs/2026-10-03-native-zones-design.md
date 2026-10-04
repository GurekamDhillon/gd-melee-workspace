# Native zones design

Status: approved by the integrator; source implementation completed on 2026-10-03.
Implementation choices and unexecuted native acceptance are recorded in
`_build/tmp/codex-native-zones-report.md`.
Requirements: `docs/prompts/codex-native-zones.md`.

## Purpose and constraints

Compute room, doorway and trigger membership once per logic frame so camera and
other scripts can share deterministic membership, including being outside all zones.
Preserve both dirty trees. No builds, game launches, commits, resets, stashes or
formatting. Implement in new include files; reread shared registration and frame
hooks immediately before small integration edits.

## Storage and execution

Keep definitions, identity counters, previous/current entity membership, residence
frames and pending transition records in a zero-initialized game-side static in
`script_game.c`, implemented by new `script_zones.h` and `script_zones.inc`.
`gw_snap.c:sn_game_object` already includes this TU's mutable statics. Do not put
simulation state in the native contact observer, which explicitly excludes snapshots.
Expose scalar accessors only; native Lua code never dereferences fighter pointers.

Call the game-side pass after `ScriptGame_StageFrame`, before FramePost's rollback
early return. It runs during resimulation; Lua event delivery does not. No zones
means an immediate count check and return, with no fighter traversal or allocation.
Definitions are not inferred from native Lua tables during rewind.

## Definition contract

Capacity: 64 live zones, 16 vertices per optional convex polygon. Strings have
explicit limits: name/label 80 bytes, kind 31 bytes, eight tags of 31 bytes each.
Reject overflow, duplicate live names, non-finite coordinates, inverted/zero-area
rectangles, non-convex polygons and malformed tags atomically. Never truncate silently.
Handles are positive generation identities, never reused in a scene; refuse exhaustion.

`gd.zone_add{name=, kind="trigger", label=name, x0=, y0=, x1=, y1=,
points={{x,y},...}, tags={...}, model=handle}` returns a handle.
Rectangle bounds or polygon points are required, mutually exclusive. An optional
model binding translates local geometry by its gameplay-plane position; rotation
and scale are deliberately not inherited. This keeps rectangles axis aligned.
Binding disappears with its model, with normal terminal exits.

`gd.zone_set(handle, patch)` validates a complete merged definition before replacing
it; `gd.zone_remove(handle)` removes only a resource owned by the calling script.
All writes use the existing offline gameplay gate and rewind branch mechanism:
membership may drive gameplay hooks, so these are gameplay writes.
Script unload/reload, stage switch and scene change retire resources with exits
while the receiving scripts are still available. Retired definitions remain long
enough to supply terminal event payloads. Cleanup must run before hook teardown.

## Reference point and boundaries

Use `Fighter.cur_pos.x/y`, the fighter origin used by blast-zone checks in
`src/melee/ft/ft_0D31.c:53-83`. ECB centre changes with animation and would make
room membership change without movement. Report all six owner slots and their
sub-fighters separately, with `port` one-based and a scalar entity identity.
Dead/benched entities are absent; respawn becomes a new membership lifetime even
when an object address is reused. Entity identity must include lifetime information.

Rectangles use `[x0,x1) × [y0,y1)`. Polygon containment uses consistently oriented
edge equations with a canonical half-open edge rule: include edges directed downward,
or rightward when horizontal; exclude the opposite direction. Normalize winding
before testing. Identical points give identical results without movement heuristics.
No hysteresis is introduced. Sample membership at completed logic frames; crossing
an entire zone between samples does not invent an enter/exit pair.

## Queries and events

`gd.zones()` returns live definitions; `gd.point_zones(x,y)` returns containing
definitions sorted by kind, ascending area, then handle. `gd.zones_at(port)`
returns the primary fighter's ordered memberships with `frames` and
`seconds=frames/60`; optional entity selection exposes the sub-fighter result.
`gd.zone_members(handle)` returns records with port, entity, sub, x, y and frames.
Queries are always allowed and never advance residence time.

Compute a complete before/after membership difference, then queue exits before
enters in stable entity/handle order. Payloads include zone handle, name, label,
kind, port, entity, sub, x, y, and `from` (the ordered prior handles).
`on_zone_none` means nonempty to empty; `on_zone_some` means empty to nonempty,
including initial entry. An entity disappearing emits exits and none if needed.
Zone deletion and unload capture terminal payloads before erasing definitions.

Arm each hook only when a script actually defines it. Keep this separate from
unconditional membership computation; preserve the existing events opt-in test.
Snapshot the transition batch and its frame identity. Native delivery happens
once on live frames, never on silent resimulation, and mutation from an event
hook appends work for the next batch. Bounded storage must cover the maximum
64-zone × entity transition batch; overflow cannot silently lose required exits.

## Integration

New `gw_script_zones.inc` owns Lua validation, scalar marshalling, queries and
event payloads. Add small registration/hook edits only after rereading shared files.
Extend contacts and trace pictures with the cached primary membership; add
`zone=name` to the existing contact watcher. Resolve names at evaluation so a
removed target fails descriptively. Timeout diagnostics list current zone names
or "outside every zone". The contact overlay shows the same cached names.
Append a profiler ID for the membership pass and update its name mapping without
renumbering existing IDs.

Reserve a Geno zones schema version macro and document the proposed zone data
shape using this contract. Do not add a Geno stage loader or claim data loading exists.
Optional item tracking is deferred; the required fighter contract ships first.
Online use requires deterministic zone creation/mutations replayed by both peers,
handshake schema/content agreement, and a rollback-safe gameplay consumer; the
current Lua write gate remains offline.

## Validation and delivery

New focused C fixtures exercise adjacent rectangle edges/corners, convex polygon
edges/winding, capacity and atomic invalid updates, stationary boundaries, repeated
crossings, disappearance/respawn/teleport, six owners and Nana, translating bindings,
binding deletion, owner unload, stage/scene cleanup, ordering and none/some counts.
Exercise the real membership implementation, not a second overlap algorithm.
Add suite fixtures for hook arming, Lua registration, watcher diagnostics and
snapshot restoration. A rewind fixture with populated definitions and residence
state must assert zero differing bytes using the existing rewind mechanism.
Under the no-build/no-launch constraint, record native execution as pending even
if portable fixtures and syntax checks pass; no claim of live rewind exactness.

Add the catalogue's single-feature `zones` demo with two rooms and a doorway,
world-space outlines, fighter membership text and transition logs. Check every
`gd` call against registrations and existing demo conventions. Add public Zones
documentation only when implementation exists, with source-validation limits.

Final `_build/tmp/codex-native-zones-report.md` records signatures and file:line,
cost bounds, reference point, boundary rule, snapshot coverage, executed checks
and unexecuted acceptance: stop in doorway, turn back, dash across ten times,
knock out of every zone and return, rewind with zero differing bytes.
