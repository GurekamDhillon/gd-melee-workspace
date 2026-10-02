# Gene-world pass 3 independent review

Verdict: **previous findings corrected; one bounded-ownership correction remains**.
Provider tokens are now cleaned up or retained on refusal, and cleanup keeps its
original run context. Eligibility and custom-movement preflight corrections pass.
However, the capacity check occurs after provider.apply, so refused cleanup can
accumulate live native tokens beyond the configured limit on every refunded retry.

Reviewed the frozen pass3 report, updated adapter/tests/contract, lane AGENTS.md,
and previous review evidence on 2026-09-30. No candidate/root code edits, native
build, install, game launch or commit. This coordination report is the only new
artifact. Native/gameplay evidence remains separate and root-owned.

## Verification

Accepted lane dependency hashes remain:

- Core `30c025cfb87a56191a5440d51e80dca68c1e812add9e6dfeeffa5f96aa06dd8c`.
- Behaviors `daaa14d6388eec3d415eab4d84df8b28d0fe196097e16b6eb964f5afe34ced48`.
- Actions `f33fcedf3f2e25c5b3a71c44a2bd767def7ae4c3a2aad90c8ce9c8e2346f8d2c`
  (accepted root engine plus the same bounded optional hooks).
- World `0195e4c0135419ae89079e3df6f09e539af288bde1aa042152891a5ae16c6dc5`.

Commands/results:

- Lane `python3 -m unittest tools.roguelite.test_gene_world -v`: **2 tests OK**,
  including all 16 internal groups.
- Root `python3 tools/roguelite/test_gene_actions.py`: **2 tests OK**.
- Root test_gene_actions.py's unmodified TEST string, run with candidate Actions
  and accepted lane Core/Behaviors: exit0, transaction findings pass.
- Lane `python3 -m unittest discover -s tools/roguelite`: **188 tests,
  errors=3, skipped=4, 9.347s**. Same missing room-kit manifest/sidecar and
  effects-study manifest errors as review2. The test_runtime traceback ends in
  missing effects-study manifest inside prepare.install, not an import-prepare
  quirk. Discovery is not green.

## Independently confirmed corrections

Additional real-Core/GeneActions probes used stateful providers with live-token
dictionaries and original-run assertions, for **both guard and conversion**:

- false, nil, and table-ok results with a token refund charge and call release
  once; the live token disappears and adapter ownership returns to zero.
- false plus token with refused release refunds charge while keeping the live
  token and owned record. reset reports failure without losing ownership.
- after get_run follows a fresh run, retry reset still passes the token's exact
  original run to the provider; once release accepts, the token disappears.
- body_state='?', missing shield_on, and omitted immunity fields with a nil
  invulnerable provider refuse before native contact and spending.
- custom-enemy Cinder traversal refuses before spending/refunding; ordinary
  fighter traversal remains green in the lane suite.

Existing unchanged-action, actor drift, Core-only Rime mark, concurrent action,
capability-loss, LOS refusal, and hookless-world groups also pass. No regression
against accepted pure action transactions was observed.

## P1: provider mutation occurs before the contribution capacity gate

Location: `runtime_gene_world.lua:704-734`, especially provider.apply at714 and
the `over` computation at721.

After a false-plus-token apply whose release refuses, the adapter correctly
retains the record, but GeneActions has already refunded/interrupted the action
and owns no contribution. A fresh action can therefore begin. apply_contribution
calls the provider again even when the adapter is already full. It then owns the
new token before discovering the exceeded capacity, attempts release, and keeps
that token too if cleanup refuses. Every later retry repeats this.

With max_contributions1, three real bulwark attempts produced:

```
adapter contributions=3
live provider tokens=3
provider release calls=3 (all refused)
logical charge=3 (refunded)
```

This permits unbounded native effect/token growth while nominally capped. The
same path serves conversions. Preserving every issued token is correct; avoid
issuing another token once capacity is exhausted.

Required bounded correction:

1. Gate/reserve ownership capacity **before** provider.apply, including records
   retained from refused cleanup. A full adapter must not invoke the provider.
2. Surface the exhausted contribution capacity through intent validation before
   Core.activate, so another action does not unnecessarily spend/refund.
3. Preserve cleanup responsibility for any token actually issued, including a
   provider callback that changes ownership reentrantly. Do not restore a cap by
   discarding records or native handles.
4. Test max1 with both false-token/refused-release and accepted-token cases;
   subsequent begins/releases must make no further provider.apply call. After
   successful cleanup, a new action should work again. Include conversion.

## Exact capacity repro

Extract the helper prefix of lane test_gene_world.py:
`prefix = fixture.TEST.split('-- =====================================================================')[0]`.
Append this body and execute the four actual Lua modules with the fixture's
normal argument order:

```lua
local live={};local apply_calls=0;local release_calls=0
local guard={
  apply=function(run)
    apply_calls=apply_calls+1
    local token={id=apply_calls}
    live[token]=true
    return false,{contrib=token}
  end,
  release=function(run,token)
    release_calls=release_calls+1
    return false
  end,
}
local s=scene(20300,
  {native_hit_contract='accepted_damage',max_contributions=1},
  {visibility=visible,guard=guard})
add_player(s.gd,1,{x=0})
install(s.run,'bulwark','player','guard')
bind(s,'player',{kind='player',port=1,team='p',room='r1'})
charge(s.run,'player','defend',3,'d')
local ga=GA.new(Core,B,s.world,
  {admitted={cinder=true,rime=true,bulwark=true}})
for i=1,3 do
  assert(ga:begin('player','guard'))
  Core.tick(s.run,6);ga:advance()
  Core.tick(s.run,1);ga:advance()
end
local n=0;for _ in pairs(live)do n=n+1 end
assert(apply_calls==3 and release_calls==3 and n==3)
assert(#s.world.contributions()==3)
assert(s.run.hosts.player.state.guard.charge==3)
```

The independent probe exited0 while asserting this defect. Its safe regression
should assert exactly one provider application/live token at capacity and no new
spend, with ownership retained until confirmed release.

## Integration limits

The previous blockers need no redesign. Keep the identity hooks and truthful
native acceptance opt-in. gd.hit/enemy_strike armor semantics, ordinary
collision/hitlag/shield/immunity, controller behavior and normal-speed play remain
separate native gates. A provider that mutates then throws without returning a
token cannot be generically rolled back; require its explicit contract rather
than inventing cleanup. The report is frozen for root's next bounded correction.
