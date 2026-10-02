# Review of the new integration work — 2026-10-01

Reviewed read-only in `_build/integration/roguelite-100`: wrapper HEAD
`4540040`, native HEAD `3062566f5`. Native changes since `d5ba31d98`;
wrapper changes since `eeabb27`. No candidate changes landed into root.

New work: deferred full-collection exports and collection claim/decline/discard;
inventory service integration and persisted run inventory; equipment service
construction/apply/revert; run history construction/append; art dependency
documentation and bootstrap; new regression suites. These are useful changes,
but R2 and R3a should not be accepted as fully closed yet.

## Findings

### P1 — Earned/exported genes cannot be discarded durably

Native `pc/scripts/examples/roguelite/core.lua:320–331` removes the collection
gene without changing the finish ledger. Validation at line 471 requires every
historical `result.export` to still exist in `profile.genes`. Consequently main's
discard save fails and rolls the removal back for every gene exported by a
completed run. This obstructs the new capacity recovery flow for ordinary earned
collections; tests currently discard starter or manually fabricated genes.

Independent real-Core reproduction:

```lua
local p=C.new_profile(1)
local r=C.new_run(p,{stocks=3})
local result=assert(C.finish(p,r,'success',r.hosts.player.slots.assault))
assert(C.discard(p,result.export))
print(C.snapshot(p)) -- nil, core.lua:471: bad export
```

Required fix: define an explicit historical-export/discard policy. Preserve the
history of the earned export while allowing its later absence, or record a
validated discarded state. Regression must finish/export, discard that actual
export through main, save/relaunch, then claim a deferred gene into the freed
slot. Do not merely remove the historical finish record.

### P1 — Shipped legacy Restore spends an item when the heal is refused

Native `main.lua:1199–1204` calls `gd.set_percent` without checking its return or
reading back the result, then unconditionally reports success to the inventory
service. This differs from the defensive v2 branch at lines 1148 onward. The
legacy branch is the currently shipped path while recipes remain uncertified.

Independent bundled-main reproduction: start a normal production legacy run,
set player percent to 90, replace `gd.set_percent` with a false-returning stub,
then press D-pad right and left to use Restore. Observed: percent remains 90,
inventory goes from 2 to 1, supply counter becomes 1; the failed heal is charged.

Required fix: share a verified native-heal implementation between both paths.
Test false, throw, unchanged readback, failed save, and refused undo separately.
The current generic undo is swallowed with `pcall`; it cannot truthfully promise
"nothing changed" if native rollback itself refuses. Retain recovery ownership
for such a refusal rather than dropping the obligation.

### P2 — v2 Restore creates two contradictory authoritative supply counts

Native `main.lua:391–392` installs the consumed inventory and decrements only
`run.progress.supplies`. `save()` stages and commits `route_mirror`, which copies
the unchanged `route.progress.supplies` over that counter. The campaign progress
record is never charged through the former campaign supply transaction.

Independent certified-test-source bundled-main probe: starting with two supplies,
call the actual `use_inventory_item` upvalue with a successful heal. It returns
true; inventory has 1, run mirror has 2. The newest decoded checkpoint likewise
contains inventory=1 and run supplies=2. This is a save-seam reproduction, not
native recipe certification. Availability/UI still consult the supply mirror.
`run_inventory` also seeds only once, so subsequent campaign supply changes do
not update the inventory automatically.

Required fix: stage inventory and route progress together and persist/commit
them through one transaction; define how campaign rewards replenish the same
inventory. Test the v2 command path, save/relaunch, travel, reward, and refusal,
asserting all three counts agree throughout.

### P2 — Run history is not included in the successful finish checkpoint

Native `main.lua:484` saves the finish, then lines 494–500 append its history
entry without another write. Existing history is not reconstructed on load.
Independent bundled-main probe after finishing: live history entries=1; newest
decoded checkpoint history entries=0. A process exit before another save loses
the visible history entry despite a durable finish record. The current new test
checks only live memory.

Required fix: stage the history entry before the same durable finish write and
restore it along with profile/run on refusal. Test the decoded checkpoint and a
fresh reload immediately after finish, including retry/exactly-once. Define the
history overflow policy; the default refuses at 64 entries while Core admits 512
finishes.

## Additional UI/test concerns

- `menus.lua:248–254` renders all pending exports at `y=113+(i-1)*30`, with no
  bound, pagination, or scrolling. At eight pending records these controls
  overlap existing buttons; later rows run beyond the screen. Claim/decline also
  overlay the existing build/stat panel. Pending exports need their own bounded
  page. Decline permanently deletes the pending gene on a single activation,
  unlike the explicitly confirmed discard action.
- The uncommitted `test_v2_runtime.py` deferred-export test calls the private
  dispatcher directly for discard/claim, bypassing menu confirmation/navigation.
  Its `assert(... or true,'kind check skipped')` can never fail. Replace it with
  real earned-gene comparison and drive the actual menu controls. Its claimed
  failed-claim-save coverage currently exercises failed discard save instead.
- Art bootstrap improves setup, but `pkgs=(pillow numpy fonttools playwright)`
  has no pinned ranges despite the comment claiming ranges. A clean run today
  does not prove reproducibility across future dependency versions. Blender/3D
  generation is not exercised by this six-generator script. I did not install
  packages or regenerate assets during this read-only review.

## Verification and limits

Independently ran the complete current pure/stub suite:
`python3 -m unittest discover -s tools/roguelite -p 'test_*.py'`.
**251 tests ran, OK, skipped=1** (250 executed passes).
Log: `root-review-new-work.log` in this directory.

The reviewed bytes include the uncommitted `tools/roguelite/test_v2_runtime.py`
change. It is not present in wrapper HEAD. Native working changes are confined
to generated `pc/platform/gw_mex_bridge.c`. No native source edits in this new
commit range; earlier independently verified native 214/214 result remains
historical evidence, not a fresh playtest of these Lua features. No native build,
controller playtest, recipe certification, screenshots, push, or release was
performed in this review.
