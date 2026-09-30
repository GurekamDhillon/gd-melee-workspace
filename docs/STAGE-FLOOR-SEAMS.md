# Scripted room floor seams

Adjacent floor surfaces need explicit links for ordinary grounded movement to
follow the chain. Touching coordinates alone do not join separately allocated
native collision lines. The roguelite room runtime and certification probe now
use the same room-local linking helper.

## Native API

`gd.stage_link(handle_a, handle_b)` returns `true` on success or `false, reason`
on a controlled refusal. It is a gameplay-script operation in an active match;
invalid handle arguments or a disallowed calling context raise a Lua error.
Use `pcall` when constructing a room transaction.

Both handles must be active floor lines owned by the calling script generation.
A platform's floor handle is eligible. Lines must run left to right, and one
line's right endpoint must meet the other's left endpoint within **0.05 game
units of Euclidean distance**. Argument order does not matter. Interior
intersections, same-side endpoints, gaps and ceiling/wall lines are not seams.

The API refuses occupied endpoints, inconsistent or disabled topology, cycles,
foreign/stale handles and an unavailable current collision map. Calling it again
on an already linked pair is a refusal, not an idempotent success. Links update
both native floor traversal directions and refresh the affected floor islands.

Removing a floor clears its links and incoming references. Moving a floor clears
links that no longer meet the endpoint contract and preserves compatible links.
An unsafe map/removal refusal must keep the handle owned for a later retry; do
not drop it from a cleanup list just because removal was attempted.

## Room construction

`RuntimeRooms.link_floor_seams(engine, entries)` accepts the newly allocated
floor entries for **one room only**. Each entry contains `handle`, `x0`, `y0`,
`x1`, `y1`. It returns `true, count` or `false, reason`.

1. Allocate every floor segment, slope and platform, retaining handles even if
   construction fails partway through.
2. Preflight all opposite endpoint matches. Refuse an endpoint with multiple
   candidate neighbours rather than choosing one by allocation order.
3. Link the pairs before entering visuals or admitting gameplay.
4. On any refused/throwing native call, roll back the destination. Some links
   may already exist; removing their owned handles also removes those links.
   Retain any refused removals for retry.

A resident source room and an incoming destination can have identical geometry
and the same script owner. Never pass handles from both rooms to one linking
call. Native ownership distinguishes scripts, not rooms. Linking a global list
would incorrectly weld two overlapping transactional worlds together.

Rooms without touching opposite endpoints need no `stage_link` API. Rooms with
required seams fail closed if the API is missing. The helper does not bridge
floor openings, snap geometry to a grid or certify a recipe.

## Evidence and remaining acceptance

The branch ascent has three links: stairs to balcony, balcony to ramp, and ramp
to upper landing. Native actual-source tests cover bidirectional floor-follow,
island refresh, removal/movement, slot reuse and duplicate-coordinate chains.
Lua tests cover room locality, drop gaps, ambiguity and retryable rollback.
The updated branch room also reached `phase=ready` in a normal-speed native
match. These checks establish construction and graph behavior; the previously
reported snagging still needs a watched controller retest.

See [watched retests](ROGUELITE-WATCHED-RETESTS.md) and the
[acceptance ledger](ROGUELITE-ACCEPTANCE.md). All recipes remain uncertified.
