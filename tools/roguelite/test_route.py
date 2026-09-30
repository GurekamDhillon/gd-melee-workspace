#!/usr/bin/env python3
"""Full-stack route service test: create, certify gate, save validation, resume."""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
RT = ROOT / 'melee/worktrees/linux/pc/scripts/examples/roguelite'
LUA = shutil.which('lua5.4') or shutil.which('lua')
assert LUA, 'Lua interpreter required'

MODULES = [RT / name for name in ('rng.lua', 'room_catalogue.lua', 'room_recipes.lua',
                                  'encounter_catalogue.lua', 'progression.lua', 'topology.lua',
                                  'progress.lua', 'codec.lua', 'adapter.lua', 'route.lua')]

TEST = r'''
local RNG=dofile(arg[1]); local Rooms=dofile(arg[2]); local Recipes=dofile(arg[3])
local Enc=dofile(arg[4]); local Prog=dofile(arg[5]); local Top=dofile(arg[6])
local Progress=dofile(arg[7]); local Codec=dofile(arg[8]); local Adapter=dofile(arg[9]); local Route=dofile(arg[10])
local topology=Top.new(Rooms,Enc,Prog,RNG); local adapter=Adapter.new(Rooms,Recipes)
local route=Route.new({topology=topology,adapter=adapter,progress=Progress,progression=Prog,encounters=Enc})
local run={id='run1',world_seed=4242,stocks=3,progress={supplies=2,room='r001',cleared={},claimed={}}}
local function clone(v) if type(v)~='table' then return v end local o={} for k,x in pairs(v) do o[k]=clone(x) end return o end
-- Uncertified recipes are refused before any run is created.
local r,why=route:create(run); assert(not r and tostring(why):find('not certified',1,true),tostring(why))
-- Certify in place for the integration test, then restore afterwards.
local saved={} for id,recipe in pairs(Recipes.recipes) do saved[id]=recipe.certified; recipe.certified=true end
r=assert(route:create(run))
assert(r.manifest.schema_version==2 and r.progress.run_id=='run1' and r.progress.current_room==r.manifest.start_room)
assert(assert(route:validate_save(run,r.manifest,r.progress)))
assert(assert(route:resume(run,r.manifest,r.progress)))
-- Tampering is caught by semantic save validation.
local m=clone(r.manifest); local p=clone(r.progress)
p.current_room='ghost'; assert(not route:validate_save(run,m,p),'unknown current room accepted')
p=clone(r.progress); m2=clone(r.manifest); m2.world_seed=run.world_seed+1
assert(not route:validate_save(run,m2,p),'seed mismatch accepted')
p=clone(r.progress); p.run_id='other'; assert(not route:validate_save(run,r.manifest,p),'foreign run accepted')
p=clone(r.progress); p.visited['ghost']=true; assert(not route:validate_save(run,r.manifest,p),'unknown visited room accepted')
-- Resolved geometry and mechanics are saved, never regenerated on resume.
for _,id in ipairs(r.manifest.order) do
 local room=r.manifest.rooms_by_id[id]
 assert(room.geometry and room.recipe_version and room.recipe_modules)
 if room.encounter then assert(room.encounter_spec.id==room.encounter) end
 if room.reward then assert(room.reward_spec.id==room.reward) end
end
m=clone(r.manifest);m.generator_version=99
assert(not route:validate_save(run,m,r.progress),'future generator version accepted')
m=clone(r.manifest);m.rooms_by_id[m.start_room].geometry=nil
assert(not route:validate_save(run,m,r.progress),'missing resolved geometry regenerated')
m=clone(r.manifest);m.rooms_by_id[m.start_room].geometry.spawn.x=999
assert(not route:validate_save(run,m,r.progress),'changed saved geometry accepted')
m=clone(r.manifest);m.edges_by_id[next(m.edges_by_id)].direction='sideways'
assert(not route:validate_save(run,m,r.progress),'invalid edge direction accepted')
m=clone(r.manifest);m.edges_by_room[m.start_room]={}
assert(not route:validate_save(run,m,r.progress),'missing adjacency accepted')
p=clone(r.progress);p.discovered.ghost=true
assert(not route:validate_save(run,r.manifest,p),'unknown discovered room accepted')
p=clone(r.progress);p.current_socket='ghost'
assert(not route:validate_save(run,r.manifest,p),'unknown arrival accepted')
p=clone(r.progress);p.claimed['reward:ghost']=true
assert(not route:validate_save(run,r.manifest,p),'invented reward claim accepted')
p=clone(r.progress);p.opened.ghost=true
assert(not route:validate_save(run,r.manifest,p),'invented opened lock accepted')
p=clone(r.progress);p.pickups.ghost=true
assert(not route:validate_save(run,r.manifest,p),'invented pickup claim accepted')
p=clone(r.progress);p.keys.ghost=true
assert(not route:validate_save(run,r.manifest,p),'invented key accepted')
-- Each exit records the opposite socket and physical arrival explicitly.
for id,node in pairs(r.view.nodes) do
 for _,exit in ipairs(node.exits) do
  assert(exit.edge_id and exit.anchor and exit.arrival and exit.arrival_socket)
  assert(r.manifest.rooms_by_id[exit.to].sockets_by_id[exit.arrival_socket])
 end
end
-- Both split branches and both merge arrivals retain their own socket identity.
local split,merge
for id,room in pairs(r.manifest.rooms_by_id) do
 if room.shape=='split' then split=id elseif room.shape=='merge' then merge=id end
end
assert(split and merge)
for _,exit in ipairs(r.view.nodes[split].exits) do
 if exit.kind=='branch' then
  local fork={manifest=r.manifest,view=r.view,progress=Progress.new(run.id,split)}
  local prior=Codec.encode(fork.progress)
  local next_progress=assert(route:travel(fork,exit))
  assert(Codec.encode(fork.progress)==prior,'travel mutated checkpoint before commit')
  fork.progress=next_progress
  local back,into_merge
  for _,e in ipairs(r.view.nodes[exit.to].exits) do
   if e.to==split then back=e elseif e.to==merge then into_merge=e end
  end
  assert(back and into_merge)
  local returned=assert(route:travel(fork,back));assert(returned.current_room==split)
  local merged=assert(route:travel(fork,into_merge));assert(merged.current_room==merge)
  assert(merged.current_socket==into_merge.arrival_socket)
 end
end
-- Consumable door policy matches progression.lua: lock identity opens once;
-- explicitly repeated tolls charge every crossing. Failed traversal is atomic.
local locked=clone(r)
local exit=locked.view.nodes[locked.progress.current_room].exits[1]
locked.manifest.edges_by_id[exit.edge_id].gate_rule='test_lock'
locked.manifest.locks.test_lock={kind='consumable_key',key='test_key'}
assert(not route:travel(locked,exit),'lock allowed without key')
assert(Progress.grant_consumable(locked.progress,'test_key',1))
local before=Codec.encode(locked.progress)
local crossed=assert(route:travel(locked,exit))
assert(Codec.encode(locked.progress)==before and crossed.opened.test_lock and not crossed.consumables.test_key)
locked.progress=crossed
local back
for _,e in ipairs(locked.view.nodes[crossed.current_room].exits) do if e.edge_id==exit.edge_id then back=e end end
assert(back and route:travel(locked,back),'opened door charged return trip')
locked.manifest.locks.test_lock['repeat']=true
assert(not route:travel(locked,back),'repeat toll did not charge return')
-- Stable finite pickups grant once even after leaving and returning.
local pickup_route=clone(r)
local room=pickup_route.manifest.rooms_by_id[pickup_route.progress.current_room]
room.pickups={{id='finite-key',key='test_key',amount=1}}
assert(route:collect(pickup_route));assert(route:collect(pickup_route))
assert(pickup_route.progress.consumables.test_key==1 and pickup_route.progress.pickups['finite-key'])
room.pickups={{id='second-key',key='test_key',amount=9}}
local before_pickup=Codec.encode(pickup_route.progress)
assert(not route:collect(pickup_route),'inventory overflow accepted')
assert(Codec.encode(pickup_route.progress)==before_pickup,'failed pickup partially claimed')
-- Persistence: manifest and progress round-trip through the bounded codec.
local mtext=assert(Codec.encode(r.manifest)); local ptext=assert(Codec.encode(r.progress))
local dm=assert(Codec.decode(mtext)); local dp=assert(Codec.decode(ptext))
assert(route:validate_save(run,dm,dp),'round-tripped save must validate')
assert(Progress.validate(dp))
-- Diagnostics expose versioned fields.
local d=route:diagnostics(r); assert(d.diag_version==1 and d.manifest_admissible==true and d.current_room==r.progress.current_room and d.visited==1)
for id,value in pairs(saved) do Recipes.recipes[id].certified=value end
assert(not route:create(run),'gate must close again')
print('route: create/resume, certification gate, semantic save validation, persistence and diagnostics passed')
'''

subprocess.run([LUA, '-', *[str(m) for m in MODULES]], input=TEST, text=True, check=True)
