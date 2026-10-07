#!/usr/bin/env python3
"""Long-run collection/economy simulation against the real Core rules.

Runs many deterministic run cycles for a fresh profile and an established
(capacity) profile, asserting bounded collection/ledger growth, failure
retention, export rules and safe behaviour at capacity. This is a pure model
simulation, not an in-game economy playtest.
"""
from pathlib import Path
import shutil
import subprocess
from tools.test_support import require_game
require_game('pc/scripts/examples/roguelite')
import game_source

ROOT = Path(__file__).resolve().parents[2]
CORE = game_source.ROGUELITE / 'core.lua'
LUA = shutil.which('lua5.4') or shutil.which('lua')
assert LUA, 'Lua interpreter required'

TEST = r'''
local C=assert(loadfile(arg[1]))()
local function count(t) local n=0 for _ in pairs(t) do n=n+1 end return n end
local function bounded(p)
 -- snapshot runs the strict validator; success means every gene/base is in range.
 assert(C.snapshot(p))
 assert(count(p.genes)<=128 and count(p.finished)<=512)
 return count(p.genes),count(p.finished)
end
-- Fresh profile: 40 mixed runs. A failed export at capacity must not lose the
-- run; finish without export must still succeed and be idempotent.
local p=C.new_profile(20260930)
local successes,failures,exports,refusals=0,0,0,0
for i=1,40 do
 local r=C.new_run(p)
 local id=C.acquire(r,i%2==0 and 'cinder' or 'rime')
 assert(C.reward(r,id,'potency',(i%5)))
 assert(C.equip(r,'player','assault',id))
 local outcome=(i%3==0) and 'failure' or 'success'
 if outcome=='failure' then
  local before=count(p.genes)
  assert(C.finish(p,r,'failure').outcome=='failure')
  failures=failures+1
  assert(count(p.genes)==before,'failure must not add collection genes')
 else
  local res,why=C.finish(p,r,'success',id)
  if res then successes=successes+1; exports=exports+1
  else
   refusals=refusals+1
   local again=assert(C.finish(p,r,'success'))
   assert(again.outcome=='success' and again.export==nil)
   assert(C.finish(p,r,'success',id).outcome=='success','finish must be idempotent')
  end
 end
 if i%4==0 then assert(C.breed(p,'g1','g3')) end
 bounded(p)
end
assert(successes+failures==40 and exports+refusals==successes)
-- Established profile at capacity: cannot export, but can still complete a run
-- and the collection does not overflow.
local full=C.new_profile(456)
while count(full.genes)<128 do assert(C.breed(full,'g1','g3')) end
assert(count(full.genes)==128)
local frun=C.new_run(full)
local before=assert(C.snapshot(full))
assert(not C.finish(full,frun,'success',next(frun.genes)))
assert(before==assert(C.snapshot(full)),'refused export must not mutate the profile')
local result=assert(C.finish(full,frun,'success'))
assert(result.outcome=='success' and result.export==nil)
assert(count(full.genes)==128 and count(full.finished)>=1)
bounded(full)
print('economy: 40-run fresh simulation and capacity profile bounded, exports and failure retention passed')
'''

subprocess.run([LUA, '-', str(CORE)], input=TEST, text=True, check=True)
