Understood. Let me re-read the current module and tests, then implement the five lifecycle/transaction fixes.

I'll rewrite the module with the lifecycle, placement-restore, token/exit validation, motion-aware drop, and corrected transaction guidance.

Now update the test prelude to model fighters, placement knobs, and explicit-false teleport.

Now add the new lifecycle, placement, and begin-validation tests.

All 10 pass. Run the full suite and check the diff.

All five findings addressed. Only the same two owned files changed; no tracked baseline edited, no commits.

## Files
- `melee/worktrees/linux/pc/scripts/examples/roguelite/runtime_rooms.lua` (rewritten; game repo)
- `tools/roguelite/test_physical_runtime.py` (extended; workspace repo)

## Fixes by finding
1. **Lifecycle APIs** — added `:cleanup()` / `:release()` (alias) covering the active room, an in-flight `busy` destination (via rollback, restoring placements) and `pending_source`; refused collision handles stay in the room record and refused model handles stay in the `Rooms` state until retried. Added `:reset(confirmed)`: makes no native calls, and while it still believes it owns live handles it returns `false,'reset requires confirmed native scene teardown'` unless the caller explicitly confirms the native teardown. Repeated `cleanup`/`rollback`/`flush` are idempotent (no double free).
2. **Transactional placement** — `:place` now verifies and captures every fighter's current position through `engine.player` *before* moving anyone, then moves in order. A throw or an explicit `false` from `teleport` is a failure (`real gd.teleport` returns nothing → success; throws on error). On partial failure it restores all already-moved fighters; a refused restore is kept in `tx.placement.pending`. `rollback` restores placements first (source still live), then destroys the destination. Commit refuses while restores are pending.
3. **Token/exit validation** — `begin` requires `args.from` to be the module's own `active` room identity (or nil only before the first room); a foreign token, an arbitrary/inactive token, or omitting the source while active is refused. The exit is validated by `_canonical_exit` against `source.node.exits` (identity or full canonical `edge_id/socket/to/arrival_socket`) and `canonical.to` must equal `dest_node.id`; a forged target or mismatched destination is refused, and the trigger is resolved from the canonical exit, not the caller's copy. Route APIs untouched.
4. **Bottom trigger motion** — `:triggered(info, player, floor, previous)` now requires actual descent while strictly below the floor and inside the opening. Descent comes from native `player.vy` when finite, else from a `previous` position sample; `vy`~0, rising from below, no motion data, or falling outside the opening do not trigger. Standing at the anchor still does not.
5. **Corrected guidance** — module header now states: gameplay paused throughout; begin→step→place→stage/validate Route/Core/progress→persist→**then** `commit` destructively retires the source. Save refusal → `rollback` destroys destination and restores placements, source untouched. It explicitly states commit cannot restore the source, and that a post-save source-retirement refusal sets `released=false` + `:pending_source`, keeping gameplay paused until `:flush()`/`cleanup` retire the colliders.

## Commands / results
- `luac5.4 -p .../runtime_rooms.lua` → OK; `python3 -m py_compile tools/roguelite/test_physical_runtime.py` → OK.
- `python3 tools/roguelite/test_physical_runtime.py -v` → 10 passed (added: placement capture/partial-failure/save-refusal rollback; begin foreign-source/forged-exit; cleanup/release/reset lifecycle with refusal retry, no double free).
- `python3 -m unittest discover -s tools/roguelite -p 'test_*.py'` → Ran 47, OK (skipped=1).
- `git diff --check` clean in both repos; only the two new untracked files; pre-existing dirty baselines preserved.

## Integration notes
Wiring order for root: `gd.pause()` → `begin`/`step` to `'ready'` → `:place` from `:arrival` → copy-apply `Route:travel`/`collect` and stage Core/progress → save → `commit`. If anything before commit fails, `rollback` (destination + fighters). If `commit` returns `released=false`, keep paused and call `:flush()` until clean. On scene end, `cleanup`/`release`; then `reset(true)` only after real native teardown. `engine.player`/`engine.teleport` must be present for transactional placement.

Limitation (unchanged, documented): no engine per-room grouping, so both rooms' colliders are transiently live in the isolated stage during a build; source is never destroyed before commit. This is fake-engine evidence only — not native traversal certification, no build/run.
