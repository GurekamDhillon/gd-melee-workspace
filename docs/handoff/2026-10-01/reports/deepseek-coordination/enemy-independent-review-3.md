# Enemy follow-up 3 independent review

Verdict: landing blocked. Existing focused suite passes all 30 tests. Run/gene/state table identity corrections pass. No lane files edited.

## Visibility nil fails open

Using PRELUDE/helpers from tools/roguelite/test_enemy_behaviors.py:

```lua
local r,host=charged_run('cinder','assault','direct_hit',3)
local m=make_manager(r,{visible=function() return nil end})
assert(add_agent(m))
local found=drive_to_ability(m,'enemy_test_1',function(f) return obs({frame=f}) end,60)
print(found ~= nil,found and found.frame)
```

Observed: true, 17. Expected: nil visibility predicate result refuses target observability; no tell or ability request. encounter_behaviors.lua:272 only rejects explicit false.

## Malformed observation exceptions

```lua
local ok,err=pcall(B.sanitize_obs,{targets={}})
print(ok,err)
local ok2,err2=pcall(B.sanitize_obs,obs({targets={false}}))
print(ok2,err2)
```

Observed: both false. Missing self crashes at line 232 adding nil self_dropped; non-table target crashes at line 239 adding nil more. Expected: boundary refuses invalid self with nil/reason and handles/refuses invalid target without throwing through manager tick.
