#!/usr/bin/env python3
"""Render the topology inspector and assert it shows distinct, coherent routes."""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
RT = ROOT / 'melee/worktrees/linux/pc/scripts/examples/roguelite'
LUA = shutil.which('lua5.4') or shutil.which('lua')
assert LUA, 'Lua interpreter required'

MODULES = [RT / name for name in ('rng.lua', 'room_catalogue.lua', 'encounter_catalogue.lua',
                                  'progression.lua', 'topology.lua', 'inspector.lua')]

TEST = r'''
local RNG=dofile(arg[1]); local Rooms=dofile(arg[2]); local Enc=dofile(arg[3])
local Prog=dofile(arg[4]); local Top=dofile(arg[5]); local Inspector=dofile(arg[6])
local t=Top.new(Rooms,Enc,Prog,RNG)
local renders={}
for _,seed in ipairs({1,2,3,5,8,13,21,34}) do
 local m=t:generate(seed)
 local before=Top.signature(m)
 local text=Inspector.render(m)
 assert(before==Top.signature(m),'inspector mutated the manifest')
 assert(text:find('MANDATORY SPINE',1,true) and text:find('EDGES',1,true) and text:find('OPTIONAL ROOMS',1,true) and text:find('LOCKS',1,true))
 assert(text:find('seed='..seed,1,true))
 assert(text:find('signature='..m.generation_report.topology_signature,1,true))
 renders[#renders+1]=text
end
-- At least three of the eight fixtures must be visibly different routes.
local distinct=0 for i=1,#renders do local unique=true for j=1,i-1 do if renders[i]==renders[j] then unique=false end end if unique then distinct=distinct+1 end end
assert(distinct>=3,'inspector did not show distinct routes: '..distinct)
print('inspector: renders distinct routes, sections and is read-only passed')
'''
subprocess.run([LUA, '-', *[str(m) for m in MODULES]], input=TEST, text=True, check=True)
