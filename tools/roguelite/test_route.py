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
local route=Route.new({topology=topology,adapter=adapter,progress=Progress,progression=Prog})
local run={id='run1',world_seed=4242,stocks=3,progress={supplies=2}}
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
