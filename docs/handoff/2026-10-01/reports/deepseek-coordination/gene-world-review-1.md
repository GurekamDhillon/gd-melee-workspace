# Gene-world adapter review 1

Verdict: **BLOCKED**. Read-only lane review; only this coordination report was
written. No native/build/game/main/prepare changes. The lane's seeded tests pass,
but the actual frozen root Core/action engine does not pass the adapter contract.

## Review inputs and evidence

Lane: `/home/gd/melee_linux_test/gdm/_build/deepseek-worktrees/gene-world`.
Reviewed `runtime_gene_world.lua`, `test_gene_world.py`, `GENE-WORLD-CONTRACT.md`
and the root `gene-world-report.md`. Root accepted dependency hashes:

- core.lua: `30c025cfb87a56191a5440d51e80dca68c1e812add9e6dfeeffa5f96aa06dd8c`
- gene_actions.lua: `994bfe3d6cbf80ab0862e90a812e64a18cfb95aa35e2762985a12f7971326983`
- gene_behaviors.lua: `daaa14d6388eec3d415eab4d84df8b28d0fe196097e16b6eb964f5afe34ced48`

`python3 -m unittest tools.roguelite.test_gene_world -v` in the lane: **2 tests
pass**, against historical dependencies. Separately, copied the three accepted
root dependencies and the lane adapter to a TemporaryDirectory, then ran the
unaltered `test_gene_world.py` TEST string with those four paths:

```python
with tempfile.TemporaryDirectory(prefix='gene-world-review-') as tmp:
    tmp = Path(tmp)
    for name in ('core.lua', 'gene_actions.lua', 'gene_behaviors.lua'):
        shutil.copy2(root_runtime / name, tmp / name)
    shutil.copy2(lane_runtime / 'runtime_gene_world.lua', tmp / 'runtime_gene_world.lua')
    result = subprocess.run(
        ['lua5.4', '-', str(tmp/'gene_behaviors.lua'), str(tmp/'core.lua'),
         str(tmp/'gene_actions.lua'), str(tmp/'runtime_gene_world.lua')],
        input=world_test.TEST, text=True, capture_output=True, timeout=90)
```

Actual: exit **1**, `stdin:162: gd.hit not called`, in finding group 2. Thus the
reported sixteen groups do not pass with the final integration dependencies.

The additional repros below run the helper prefix of that same TEST string
(everything before the first `-- =====================================================================`)
with the accepted root dependencies. They require no lane edits.

## 1. Release free-state recheck destroys the selected target token

At adapter line 286, `can_start` replaces `state.expect[host@slot]` with only
`{run, source_gen}`. `query` previously recorded `target_gen` and `target_ref`.
The final action engine rechecks `can_start` at release; `revalidate` then
compares the existing target's generation/reference to nil and refuses it.

Exact default Cinder repro:

```lua
local s=scene(18001,nil,{visibility=visible})
add_player(s.gd,1,{x=0,facing=1})
add_player(s.gd,2,{x=5,facing=-1})
bind(s,'player',{kind='player',port=1,team='player',room='r1'})
bind(s,'enemy',{kind='player',port=2,team='enemy',room='r1'})
charge(s.run,'player','direct_hit',3,'first')
local ga=GA.new(Core,B,s.world)
assert(ga:begin('player','assault'))
local events=ga:advance()
print(calls(s.gd,'hit'),s.run.hosts.player.state.assault.charge,ga.stats.refunded)
for _,e in ipairs(events) do print(e.kind,e.reason) end
```

Actual: `0, 3, 1`, `interrupted, target binding drift`. Expected: one gd.hit
acceptance and charge spent when no state or actor identity changed. Fix without
removing the final engine's required free-state recheck or weakening drift checks.

## 2. Pending actions silently follow rebound native actors

The same overwrite also adopts a new source generation at release. Movement
has no target-token check, so this is observable despite blocker 1:

```lua
local s=scene(18002)
add_player(s.gd,1,{x=0}); add_player(s.gd,2,{x=0})
install(s.run,'cinder','player','traversal')
bind(s,'player',{kind='player',port=1,team='player',room='r1',token='old'})
charge(s.run,'player','move',3,'first')
local ga=GA.new(Core,B,s.world)
assert(ga:begin('player','traversal'))
bind(s,'player',{kind='player',port=2,team='player',room='r1',token='new'})
ga:advance()
print(last_call(s.gd,'impulse').port,s.run.hosts.player.state.traversal.charge)
```

Actual: impulse applied to **port 2**, charge **0**. Expected: cancel the old
port-1 action and preserve its charge; never transfer it to a new native actor.

Core-owned Rime marks bypass `apply_status` and therefore bypass adapter
mutation validation entirely. The final engine refreshes the selected target's
observation and replaces the old view; it does not interpret adapter-specific
generation fields. Repro:

```lua
local s=scene(18003,nil,{visibility=visible})
add_player(s.gd,1,{x=0}); add_player(s.gd,2,{x=5}); add_player(s.gd,3,{x=5})
install(s.run,'rime','player','assault')
bind(s,'player',{kind='player',port=1,team='player',room='r1'})
bind(s,'enemy',{kind='player',port=2,team='enemy',room='r1',token='old'})
charge(s.run,'player','direct_hit',3,'first')
local ga=GA.new(Core,B,s.world)
assert(ga:begin('player','assault'))
bind(s,'enemy',{kind='player',port=3,team='enemy',room='r1',token='new'})
ga:advance()
print(s.run.marks.enemy~=nil,s.run.hosts.player.state.assault.charge)
```

Actual: `true, 0`: the replacement actor's logical host is marked. Expected:
cancel without marking/spending. Enforce stable source **and** target identity
for default Cinder/Rime, including Core-only marks, not only inside apply_effect.
End-to-end tests must prove unchanged bindings still succeed and changed
bindings cancel, rather than counting blocker 1's blanket refusal as drift safety.

## 3. Optional contribution providers violate refusal/cleanup ownership

These providers are explicitly exposed and exercised by the lane contract.

- At lines 522-532, `apply_contribution` checks that a token was returned but
  never checks that the provider returned exactly true. A provider returning
  `false, {contrib=token}` is reported as success. In a real GA bulwark action,
  actual `applied=true`, charge 0, adapter-owned count 1. Expected: refusal,
  authored refund, and release/retain the returned token according to confirmed
  cleanup results. Nil plus a token has the same defect.
- At lines 252-254, `world.reset()` simply replaces the contributions table.
  With a successful provider and one owned live token, actual reset leaves
  adapter-owned count 0 and calls provider.release **zero times**. A native token
  therefore survives while ownership is forgotten. Reset must release confirmed
  handles and retain/report refusals, or explicitly refuse reset while handles
  remain. It must not discard them.

Minimal provider for the first repro:

```lua
local guard={
  apply=function() return false,{contrib={id='native-token'}} end,
  release=function() return true end,
}
```

Use the fixture's bulwark guard action, admitted explicitly exactly as group 16.
For the reset repro change apply's return to true, keep a provider release counter,
and call world.reset after ga:advance creates the contribution.

## Capability and missing fighter eligibility corrections

The report says missing fighter invulnerability/reflection are refused. Actual
observe initializes `vulnerable=true` and `reflecting=false` and keeps them when
the optional providers are absent (lines 159-177). With no invulnerable provider,
`world.observe('enemy').vulnerable` is true. The API audit confirms gd.player
does not expose those states. Unknown eligibility is therefore assumed safe,
not refused. Resolve this gap with a trustworthy provider or a fail-closed gate;
at minimum do not claim that unavailable checks have been enforced. This matters
for Core-only marks as well as native strikes.

Capability reporting is likewise unconditional: removing `s.gd.impulse` still
produces `world.supports('cinder','traversal') == true` and
`capabilities().seams.apply_movement == true`. The final action engine does not
call world.supports; adapter stubs satisfy its function-existence checks even
when the underlying native implementation is missing. The lane's missing-native
tests consequently spend and refund rather than providing the claimed capability
preflight. Report actual native/provider availability and ensure the promised
early refusal is exercised with the final engine. Default absent LOS itself is
correctly denied through world.occluded and the engine's preflight.

## Native API audit: correct shapes, with a material refusal limit

Read root `pc/platform/gw_script.c`, `pc/gameworld/script_game.c`,
`src/melee/it/item.c` and `src/melee/ft/ftcoll.c`.

- gd.hit(target_port, {from=source_port,damage,angle,kbg,bkb}) is correct.
- gd.enemy_hurt(handle, {from=source_port,damage,angle,kbg,bkb,reach}) is correct.
- gd.enemy_strike(source_handle, target_port, {damage,angle,kbg,bkb,reach}) is
  correct; the target is a separate argument, not a from field.
- Enemy damage/reach 1..30, fighter damage 0..500, angle 0..361, knockback
  0..1000, impulse |x|<=4 / |y|<=3 match the native validators. The native bridge
  checks owned handles. gd.player exposes the fields the adapter reads.
- Exact-true native acceptance and nil/false/throw refusals are handled on the
  direct hit/movement routes; the wrapper does not itself retry these calls.

**A false native return is not proof of zero native mutation.** In
`script_game.c:2415`, ScriptGame_Hit calls ftColl_80076640 before returning false.
`ftcoll.c:216` may subtract damage from fp->dmg.x1834 while x221C_b4 remains set,
then return false. EnemyStrike uses the same helper. Thus native acceptance-only
contracts and charge refunds cannot imply a complete rollback of native effects.
Record this audited limit and cover adapter behavior with a stateful refusal
double; no native source fix is authorized in this lane. Item_ScriptCommitDamage
likewise has an actual commit result, so the adapter correctly uses its boolean
rather than inferring success from metadata.

## Required bounded followup

Re-seed/read the final accepted root dependencies, preserve their transaction
semantics, fix the adapter identity/refusal/ownership paths, and add real-module
end-to-end regressions for the exact cases above. Rerun all existing sixteen
groups against those final dependencies. Do not modify native/build/main/prepare
or other lanes. Native collision/hardware/controller acceptance remains unproved.
