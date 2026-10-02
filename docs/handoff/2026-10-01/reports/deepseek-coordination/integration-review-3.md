# Integration followup 2 review for corrective pass 3

Reviewed frozen integration lane on 2026-09-30, before followup 3 edits. No game,
build, install or lane edits. `python3 tools/roguelite/test_v2_runtime.py` passed
19/19. Additional probes used its actual modules and native-correct copy
`gd.player` snapshots; bundled-main probes certified only a temporary source copy.

Verdict: not ready for active integration merely after native unload cleanup.
New-run staging and ordinary active pending-save retry are corrected, but owner
retirement and effect rollback still have concrete P1 failures.

## Confirmed improvements

The staged initial-save branch restores exact previous profile, run, route,
campaign and fighter references on refusal. An added bundled-main probe tested an
existing campaign with refused collider cleanup, rather than only a first run.
All five reference comparisons passed. One transition phase per tick works, and
storage recovery before the pending-save retry limit succeeds through main.
`on_unload` now truthfully identifies missing native owner cleanup; it does not
fabricate confirmed scene teardown.

## P1: retired campaign callbacks follow the replacement run

`main.lua:391` captures globals in get_run/get_route/set_run/set_progress/save_route.
`begin` promotes the new globals before `retire_campaign(old_campaign)` at 586.
`runtime_encounters.lua:641` obtains the current global run during teardown, then
648 deletes an acquired gene by reused id and 651 deletes its host. The old
ownership record therefore operates on the new run.

Actual-Core probe: old encounter owns acquired enemy `r4`; new profile breeds
`g4`, and new run2 inherits it as `r4`. Assigning the replacement RUN then calling
old campaign teardown deletes new run2's inherited g4/r4. Ownership callbacks
must stay bound to the original run/route during retirement and subsequent
orphan retries. Do not serialize an old pending progress record against a new
manifest/run. Explicit rebinds should apply only to the current campaign.

Run with `test_v2_runtime.PRELUDE`:

```lua
local camp=reset(7)
assert(enter(camp)=='active')
assert(camp:request_travel(exit_to('r1','r2'))); assert(drive(camp)=='active')
assert(camp:request_travel(exit_to('r2','r4'))); assert(drive(camp)=='active')
local found=false
for _,info in pairs(camp.encounters.owned) do if info.gene=='r4' then found=true end end
assert(found)
local p=Core.new_profile(7); Core.new_run(p)
assert(Core.breed(p,'g1','g3')=='g4')
local fresh=Core.new_run(p); assert(fresh.genes.r4.origin=='g4')
RUN=fresh
assert(camp:teardown())
assert(not RUN.genes.r4) -- reproduced defect; regression must assert preserved
```

## P1: refused retirement permits overlapping old/new worlds

`main.lua:586` ignores retire_campaign's false result. Its orphan list is retried
only in cleanup or match teardown, not active ticks. A bundled-main probe left
one previous collider owned, started a new run, and reached:
`old.rooms:total()==1`, `fresh:running()==true`, engine pause=false. Another 100
active ticks made zero old-owner cleanup attempts, even if removal later recovers.
Keep gameplay paused until every retained old owner is released; retry boundedly
and expose an explicit error on exhaustion. Deduplicate orphan ownership when a
refused replacement is attempted repeatedly.

Bundled-main probe, after the fixture bundle loads:

```lua
local function uv(fn,name)
  for i=1,99 do local n,v=debug.getupvalue(fn,i)
    if not n then break end; if n==name then return v end
  end
  error('missing upvalue '..name)
end
files={}; request=true; tick=0
ready(); click('start'); step(); step(); tick=91; step(); assert(settle(400))
local old=assert(roguelite_v2())
refuse_stage_remove=true
local choose=uv(on_tick,'choose_menu')
choose({kind='leave'}) -- real leave action, retained old native ownership
assert(state().menu=='collection' and roguelite_v2()==old)
click('start'); step(); assert(settle(400))
local fresh=assert(roguelite_v2())
assert(fresh~=old and old.rooms:total()>0 and fresh:running() and pause==false)
local calls=0; local original=old.teardown
old.teardown=function(self) calls=calls+1; return original(self) end
for i=1,100 do step() end
assert(calls==0) -- reproduced defect; corrective regression must retry/block
```

## P1: teardown discards refused native effect rollback

`runtime_campaign.lua:761` checks encounter/room cleanup but ignores effect_pending.
`reset(false):781` then clears that ownership. A failed supply save followed by a
refused percent restoration leaves percent50 instead of80. Teardown returns true
and reset clears the retry. Native owner cleanup cannot restore this logical heal
transaction. Attempt effect rollback during teardown and report failure/retain
ownership until readback confirms restoration.

Run with the campaign PRELUDE:

```lua
local camp=reset(9); assert(enter(camp)=='active')
ps[1].percent=80; save_fail=true; percent_refuse_call=2
local ok=camp:use_supply()
assert(not ok and camp.effect_pending and ps[1].percent==50)
assert(camp:teardown()); assert(camp:reset(false))
assert(not camp.effect_pending and ps[1].percent==50) -- reproduced ownership loss
```

## P1: mismatched heal readback also loses rollback ownership

At runtime_campaign.lua:627-630, a write whose readback differs from target calls
set_percent(before) once with pcall and ignores both refusal and readback. The
current effect has not entered `applied`, so `_abort_effects` cannot retain it.
Probe gives percent51 (before80), supplies unspent, no effect_pending, unblocked.
Record the attempted write's restoration responsibility before checking readback;
keep it whenever restoration is refused or unverified. The explicit-false and
throw branches also need to account for a callback that mutated before refusing.

```lua
local camp=reset(8); assert(enter(camp)=='active'); ps[1].percent=80
local calls=0
gd.set_percent=function(port,n)
  calls=calls+1
  if calls==1 then ps[port].percent=n+1; return true end
  return false
end
local ok=camp:use_supply()
assert(not ok and ps[1].percent==51 and camp.effect_pending==nil and not camp:blocked())
```

## Limits and review notes

Pending-save retries reaching the configured eight-attempt limit remain owned and
surface error, as intended by the bounded-failure test. Once main reaches that
error, later storage recovery does not retry automatically; main calls tick only
while blocked(), which returns false in error. The menu only implements
retry_finish, so recovery then requires reload/restart. This is a product recovery
limit, not a claim that ordinary active retries remain broken.

Campaign.teardown also ignores the result of its one pending-save flush before
reporting clean. Avoid claiming all state is durably settled merely because native
handles were released; preserve/report the unsaved generation on refusal.

The native unload owner-cleanup seam remains a necessary external prerequisite.
The Lua log is truthful but cannot retain colliders after its environment vanishes.
No native certification, broad completion or art evidence was established here.

## Probe execution

From the integration worktree, import `tools/roguelite/test_v2_runtime.py` with
`tools/roguelite` on Python sys.path (for prepare). Campaign snippets execute via:

```python
subprocess.run([fixture.LUA, '-', str(fixture.RT)],
               input=fixture.PRELUDE + body, text=True, capture_output=True)
```

Bundled-main snippets use fixture._certified_source(), fixture.prepare.bundle(),
the IIFE wrapping used by MainIntegrationTests, and fixture.PRELUDE_MAIN. Always
delete that temporary source copy afterward. No repository recipe certification
flags or generated output need modification.
