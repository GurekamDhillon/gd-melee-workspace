# Gene-actions followup 5 report: mark-revision capacity

Lane: isolated `gene-actions` worktree, branch `agent/deepseek-gene-actions-20260930`.
Bounded correction only. No main/native/save-schema change, no commit/build/install/art.

## Files owned/changed
- `melee/worktrees/linux/pc/scripts/examples/roguelite/core.lua` (modified, +80/-4)
- `melee/worktrees/linux/pc/scripts/examples/roguelite/gene_actions.lua` (new)
- `melee/worktrees/linux/pc/scripts/examples/roguelite/gene_behaviors.lua` (new)
- `tools/roguelite/test_gene_actions.py` (new)
- `docs/GENE-ACTION-CONTRACT.md` (new)
- this report (coordination artifact, outside the lane)

## Defect fixed
Cap 64 was a silent boundary: on the 65th distinct target `Core.activate` still
spent charge and mutated `r.marks`, `bump_mark_revision` silently returned,
`mark_revision` returned nil, and the engine could not conditionally undo the
owned mark. Raising the number alone does not make the next boundary correct.

## Bound and rationale
`MARK_TARGET_CAP = 256`, derived from inspected limits, not chosen arbitrarily:
- `topology.lua` rejects a route outside `12..18` rooms (`room count out of band`).
- `runtime_encounters.lua` default actor budget is `max_actors = 12` live actors
  per encounter; entity ids are `enemy_<room>_<serial>`, so a whole route can
  retire up to `18 * 12 = 216` distinct actor targets, plus two fighter ports.
- 256 covers that with headroom. The engine additionally resets the ephemeral
  registry on room leave (after pending transactions are cancelled), which keeps
  the resident set near one room's needs at any route length.

## Correctness at saturation
- `Core.activate` preflights any mark mutation (`action == 'mark'` set, or a
  `family == 'fire'` consume of a live mark) **before** `st.charge = 0` /
  `ready_at`. If the target is untracked and the registry is saturated it returns
  `nil, 'mark revision capacity'` with no mutation and no spend.
- `Core.mark_revision` returns `nil` for an untracked target at saturation, so
  `Core.restore_mark` can never perform an untracked mutation without a slot.
- Tracked targets keep working at saturation; tombstones are never evicted while
  transactions can be pending. The engine mirrors the capacity check in
  `preflight` for an early refusal.
- No save/checkpoint schema change: the registry is ephemeral, weak-keyed, and
  never serialized; pending actions do not survive a resume.

## Tests (real Core + real action engine)
`python3 -m unittest tools.roguelite.test_gene_actions -v` -> 2 tests OK,
`29 finding groups passed`. New groups:
- Group 28 (Core): 256 distinct marks succeed; 257th `activate` refused with
  `mark revision capacity`, snapshot byte-identical (no spend/cooldown/mark),
  no residual mark; a tracked target still activates; an untracked
  `restore_mark` at saturation is refused.
- Group 29 (engine): the real action engine marks 256 distinct targets through
  `begin/advance`, refuses the over-bound target in `preflight` with charge still
  3 and no residual mark, keeps a tracked target working, and after
  `on_room_leave` (registry reset with nothing pending) a new target succeeds.
- Fourth-pass ABA/expiry groups (24-26) remain green: `nil -> mark -> nil`
  interleaving, callback tick past expiry, and exactly-one live restore.

Reasoning for regressions: with the previous cap the Core loop would fail at
i=65 and the engine loop would never reach its boundary; the tests exercise the
actual bound and the clean refusal.

## Adjacent suites
- `test_core.py`: pass (snapshot/round-trip unchanged; registry not serialized).
- `test_gene_catalogue.py`: pass.
- `test_checkpoint.py`, `test_legacy.py`: pass (Core/checkpoint/migration).
- Full discovery: 116 tests, same 4 pre-existing environment errors (missing
  generated art/room-kit sidecars, absent `roguelite_certification/main.lua`,
  and `import prepare` in `test_persistence`/`test_runtime`), unrelated.

`luac5.4 -p` clean; no global leakage; content-deterministic reruns; no trailing
whitespace.

## Limitations
- Native collision, startup windows, occlusion and conversion remain unbound;
  the fake world proves the transaction/ownership contract, not native hits.
- The 256 bound assumes the current topology (12..18 rooms) and the 12-actor
  encounter budget; a future generator or raised actor budget must revisit it.
- The registry reset relies on integration calling `on_room_leave`; without it
  the 256 cap still bounds memory and refuses cleanly.
- Root still owns the full Core persistence/migration regression on the final
  artifact; Windows/hardware/human acceptance is untouched.

## Independent review (root reviewer)

Verdict: BLOCKED. Saturation handling itself passes: mutation capacity is checked before charge/cooldown, tracked targets remain usable, no tombstone eviction, and restore at saturation refuses. Focused command `python3 -m unittest tools.roguelite.test_gene_actions tools.roguelite.test_core tools.roguelite.test_checkpoint tools.roguelite.test_legacy tools.roguelite.test_gene_catalogue -v` passes (3 unittest methods; checkpoint, legacy and catalogue execute their assertions during import). No lane files edited.

### Blocker: supported reentrant room cleanup resets revisions while refund is still in flight

Use helper prefix from test_gene_actions.py TEST string (before group 1):

```lua
local r,obs,st,w=scene(8101)
local ga=GA.new(Core,B,w)
charge(r,'player','defend',3,'oldguard')
assert(Core.activate(r,'player','guard',{target='enemy'}))
install(r,'rime','ally','guard'); install(r,'cinder','ally','traversal')
charge(r,'ally','defend',3,'allyguard'); charge(r,'ally','move',3,'allytraverse')
charge(r,'player','direct_hit',3,'playerfire')
st.on_apply_effect=function(rr)
 print('before clear',Core.mark_revision(rr,'enemy'))
 ga:on_room_leave()
 print('after clear',Core.mark_revision(rr,'enemy'))
 assert(Core.activate(rr,'ally','guard',{target='enemy'}))
 assert(Core.activate(rr,'ally','traversal',{target='enemy'}))
 print('after interleaving',Core.mark_revision(rr,'enemy'),rr.marks.enemy~=nil)
end
st.refuse_effect=true
assert(ga:begin('player','assault'))
ga:advance()
print('resurrected',r.marks.enemy~=nil,r.marks.enemy and r.marks.enemy.source)
```

Actual: before clear 2; after clear 0; after interleaving 2,false; resurrected true,player. Expected: enemy mark remains absent after ally consumes it. Single action-engine instance; no unsupported ownership assumption. Reentrant room cleanup is explicitly supported by release logic and contract section 5.7. clear() removes the record but release() retains rec on its stack and refunds after callback return; Core.forget_run resets revisions prematurely, producing an ABA match. Defer registry forgetting until every in-flight release/refund unwinds or use a generation token invalidated by reset. Add regression preserving existing 29 groups.

### Additional Core boundary defect: missing source host accepted

```lua
local r=scene(8102)
assert(Core.restore_mark(r,'enemy',{source='missing_host',expires=180},0))
local snapshot,why=Core.snapshot(r)
print(snapshot~=nil,why)
```

Actual: restore succeeds, then snapshot refuses `invalid mark` at core.lua:353. Expected: restore validates `r.hosts[before.source]` and refuses without mutation. restore_mark currently validates only source name and expiry, although the persisted schema requires a source host.
