# Gene-world pass 2 independent review

Verdict: **corrective pass required**. The unchanged-action, binding-drift,
concurrency and optional-hook compatibility corrections pass against the accepted
modules. Provider refusal ownership remains broken, provider cleanup can follow
the replacement run, and smaller eligibility/capability claims exceed the actual
implementation.

Read-only review of the frozen lane at
`/home/gd/melee_linux_test/gdm/_build/deepseek-worktrees/gene-world`, 2026-09-30.
Read updated AGENTS.md, root gene-world-report-2.md, review-1, seed manifest,
adapter/actions/tests/contract. No candidate/root code edits, native build, game,
install or commit. This coordination artifact is the only authored file.

## Verification

- Lane: `python3 -m unittest tools.roguelite.test_gene_world -v` — **2 tests OK**,
  including all 15 internal finding groups.
- Root: `python3 tools/roguelite/test_gene_actions.py` — **2 tests OK**.
- Additionally executed root test_gene_actions.py's unmodified TEST string with
  the lane's candidate gene_actions.lua and accepted lane Core/Behaviors —
  exit0, `gene action contract: transaction findings passed`.
- Lane: `python3 -m unittest discover -s tools/roguelite` — **188 tests,
  errors=3, skipped=4, 8.334s**. All three errors are missing generated assets:
  room-kit manifest, room-kit collision sidecar, and effects-study manifest.
  test_runtime fails inside prepare.install because effects-study manifest is
  absent; the observed traceback is not an import-prepare failure.

Verified Core hash `30c025cf...`, Behaviors `daaa14d6...`, candidate Actions
`f33fcedf...`, matching the report. Diffed candidate Actions against current root:
only the optional begin capture, release validation, and request/record intent
transport are added. No accepted transaction logic was removed or weakened.

Existing real-module groups demonstrate unchanged Cinder native contact succeeds,
movement/source and Rime/Core-mark target rebindings cancel before spend, native
function/capability loss cancels, two concurrent player/enemy attacks remain
independent, and hookless injected worlds still succeed. Native hit opt-in and
default unknown-LOS refusal are present. These are contract/stub results, not
native collision certification.

## P1-A: refused provider token is refunded and forgotten without cleanup

`runtime_gene_world.lua`, apply_contribution: the `res ~= true` refusal branch
returns before retaining or releasing `detail.contrib`. A provider can create a
native token, return `false, {contrib=token}`, and leave an active effect. The real
GeneActions transaction refunds charge, while adapter ownership count becomes
zero. reset then reports success without calling provider.release.

Observed: provider release calls0, adapter contributions0, live native token
still true, charge restored3. This reproduces the cleanup half of review-1's
finding; pass2 fixed acceptance but not ownership.

Group13(a/b) asserts only refund and zero owned-count. That assertion permits the
ownership loss it should reject. Record every returned token as cleanup
responsibility even on false/nil acceptance; attempt release and retain/report
any refusal. Preserve exact-true acceptance and authored refund behavior.

Probe using the existing fixture helper prefix:

```lua
local live={};local releases=0
local guard={
  apply=function() live.token=true;return false,{contrib={id='token'}} end,
  release=function() releases=releases+1;live.token=nil;return true end,
}
local s=scene(19001,CONTRACT,{visibility=visible,guard=guard})
add_player(s.gd,1,{x=0});install(s.run,'bulwark','player','guard')
bind(s,'player',{kind='player',port=1,team='player',room='r1'})
charge(s.run,'player','defend',3,'d')
local ga=GA.new(Core,B,s.world,{admitted={cinder=true,rime=true,bulwark=true}})
assert(ga:begin('player','guard'));Core.tick(s.run,1);ga:advance()
assert(s.run.hosts.player.state.guard.charge==3)
assert(releases==0 and #s.world.contributions()==0 and live.token)
assert(s.world.reset(s.run))
assert(releases==0 and live.token)
```

Repeat with nil acceptance and a refused release; ownership must survive until
the provider confirms cleanup. A throwing provider that mutates without returning
a token cannot be repaired generically: document that provider contract limit,
and do not claim the adapter can undo arbitrary partial mutation.

## P1-B: old contribution release is dispatched against a replacement run

Adapter-owned records capture no owning run at apply. release_contribution calls
`provider.release(run, owned.native)` using its caller's run. reset defaults to
latest state.run. Even when GeneActions has attached c.run to the exact record,
the adapter ignores it. A persistent world following get_run from run1 to run2
therefore releases a run1 token with run2.

Observed provider release argument run2, token owner run1. This can make a
run-scoped provider remove/revert a coincidentally reused host in the replacement
run, or permanently refuse cleanup. Bind each contribution's release context to
the exact run at creation; do not redirect it during later get_run/reset calls.

```lua
local got_run
local guard={apply=function()return true,{contrib={id='owned'}}end,
  release=function(run)got_run=run;return true end}
local s=scene(19002,CONTRACT,{visibility=visible,guard=guard})
add_player(s.gd,1,{x=0});install(s.run,'bulwark','player','guard')
bind(s,'player',{kind='player',port=1,team='player',room='r1'})
charge(s.run,'player','defend',3,'d')
local ga=GA.new(Core,B,s.world,{admitted={cinder=true,rime=true,bulwark=true}})
assert(ga:begin('player','guard'));Core.tick(s.run,1);ga:advance()
Core.tick(s.run,1);ga:advance();assert(#s.world.contributions()==1)
local old=s.run;local fresh=Core.new_run(s.profile);s.holder.run=fresh
assert(s.world.get_run()==fresh);assert(s.world.reset())
assert(got_run==fresh and got_run~=old)
```

## Other concrete correction/coverage requirements

1. **Unknown eligibility is not consistently fail-closed.** player_eligibility
   uses OR to decide known state: body_state='?' with timed_state='normal' is
   accepted. A missing shield_on is treated as unshielded. An optional
   invulnerable provider returning nil sets known=true and accepts a player with
   no body/timed fields. Both real Cinder probes call gd.hit once and spend all
   charge. Validate the actual recognized state vocabulary, require the necessary
   state/shield evidence, and treat nil/unknown provider answers as unknown.
   A trustworthy explicit false immunity answer can grant normal eligibility;
   absent evidence must not silently grant it.
2. **Advertised exact-true contribution acceptance still accepts a table.**
   apply_contribution accepts `{ok=true,contrib=token}` as its first provider
   result. Real bulwark probe spends charge0 and owns1 token. The report and
   adapter comments say exact true is required. Remove the alternate acceptance
   or explicitly revise the contract and tests; when rejecting a returned token,
   preserve cleanup responsibility as in P1-A. apply_status also has a table-ok
   alternative, so align its documented contract intentionally.
3. **Custom-actor movement capability is incorrectly granted before spend.**
   native_capability for apply_movement checks only gd.impulse presence, not that
   the source is a player. A real cinder traversal action from a bound owned
   enemy passes begin, then spends/refunds when apply_movement discovers that
   impulse needs a fighter port. Observed started1/refunded1/native calls0.
   Refuse that unsupported direction in the capability/intent preflight.
4. Add conversion-provider versions of ownership/reset/refusal tests, not only
   guard. Test real native token state and provider.release count, not just the
   adapter dictionary size. Include replacement-run cleanup and refused-token
   recovery.
5. Keep the native acceptance opt-in closed until root confirms corrected
   gd.hit/gd.enemy_strike semantics. The flag is a caller assertion, not detection
   that native code was fixed. True means accepted native action, including armor
   absorption; it does not prove percent loss or ordinary hit callbacks.

Eligibility probe patterns after constructing/binding two players and charging
Cinder exactly as the first probe:

```lua
-- Partial unknown native fields still grant a hit.
s.gd.players[2].body_state='?'
s.gd.players[2].shield_on=nil
-- Or create the scene with invulnerable=function()return nil end,
-- and add_player(..., {x=5,omit_body=true}).
local ga=GA.new(Core,B,s.world)
assert(ga:begin('player','assault'));Core.tick(s.run,1);ga:advance()
assert(calls(s.gd,'hit')==1)
```

Custom movement probe:

```lua
local s=scene(19006,nil,{})
local h=add_enemy(s.gd,{x=0})
install(s.run,'cinder','mob','traversal')
bind(s,'mob',{kind='enemy',handle=h,team='e',room='r1'})
charge(s.run,'mob','move',3,'m')
local ga=GA.new(Core,B,s.world)
assert(ga:begin('mob','traversal'));Core.tick(s.run,1);ga:advance()
assert(ga.stats.refunded==1 and #s.gd.calls==0)
```

## Probe execution

Load lane tools/roguelite/test_gene_world.py with importlib. Extract its helpers
with `prefix = fixture.TEST.split('-- =====================================================================')[0]`.
Append each probe, then execute actual lane modules:

```python
subprocess.run(['lua5.4', '-', str(rt/'gene_behaviors.lua'), str(rt/'core.lua'),
                str(rt/'gene_actions.lua'), str(rt/'runtime_gene_world.lua')],
               input=prefix + body, text=True, capture_output=True)
```

All independent probes exited0 while asserting the defect states described above.
Corrective tests must assert cleanup/ownership and pre-spend refusal instead.
This review is frozen for the bounded corrective pass; native/gameplay integration
remains root-owned.
