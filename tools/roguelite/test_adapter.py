#!/usr/bin/env python3
"""Exercise the runtime adapter: certification gate, node mapping, exits."""
from pathlib import Path
import shutil
import subprocess
import game_source

ROOT = Path(__file__).resolve().parents[2]
RT = game_source.ROGUELITE
LUA = shutil.which('lua5.4') or shutil.which('lua')
assert LUA, 'Lua interpreter required'

MODULES = [RT / name for name in ('rng.lua', 'room_catalogue.lua', 'room_recipes.lua',
                                  'encounter_catalogue.lua', 'progression.lua', 'topology.lua', 'adapter.lua')]

TEST = r'''
local RNG=dofile(arg[1]); local Rooms=dofile(arg[2]); local Recipes=dofile(arg[3])
local Enc=dofile(arg[4]); local Prog=dofile(arg[5]); local Top=dofile(arg[6]); local Adapter=dofile(arg[7])
local t=Top.new(Rooms,Enc,Prog,RNG)
local m=t:generate(42)
local function clone(v) if type(v)~='table' then return v end local o={} for k,x in pairs(v) do o[k]=clone(x) end return o end
-- Uncertified recipes are refused with a clear reason.
local unc=Adapter.new(Rooms,Recipes)
local view,why=unc:manifest(m); assert(not view and tostring(why):find('not certified',1,true),tostring(why))
local diag=unc:diagnostics(m); assert(diag.diag_version==1 and diag.manifest_admissible==false and diag.refusal)
-- Certify in place for the mapping test, then restore.
local saved={} for id,recipe in pairs(Recipes.recipes) do saved[id]=recipe.certified; recipe.certified=true end
local a=Adapter.new(Rooms,Recipes)
local ok=assert(a:check(m))
local v=assert(a:manifest(m))
assert(v.start==m.start_room and v.final==m.final_room and #v.order==#m.order)
-- Every room maps to a legacy kind and geometry, with exits matching edges.
local expected={}
for _,id in ipairs(m.order) do
 local node=v.nodes[id]; assert(node,'missing node '..id)
 assert(node.room and node.room.floor.left==-65 and node.room.floor.right==65)
 assert(node.kind=='entry' or node.kind=='exit' or node.kind=='arena' or node.kind=='boss' or node.kind=='rest' or node.kind=='traversal' or node.kind=='reward' or node.kind=='branch' or node.kind=='connector')
 expected[id]=0
end
for _,edge in pairs(m.edges_by_id) do
 if edge.direction=='both' then expected[edge.from_room]=expected[edge.from_room]+1; expected[edge.to_room]=expected[edge.to_room]+1 end
end
for id,node in pairs(v.nodes) do assert(#node.exits==expected[id],'exit count mismatch for '..id) end
-- A top socket's exit resolves to a top anchor.
local sawTop=false
for id,node in pairs(v.nodes) do
 for _,exit in ipairs(node.exits) do
  assert(v.nodes[exit.to],'exit target missing')
  assert(node.room.exit_anchors[exit.side],'exit side has no anchor: '..exit.side)
  if exit.side=='top' then sawTop=true; assert(node.room.exit_anchors.top.y==26) end
 end
end
assert(sawTop,'no upper-socket exit sampled across the generated route')
-- One-way edges only list the traversable direction.
local one=clone(m)
local target=nil
for id,edge in pairs(one.edges_by_id) do if edge.direction=='both' then target=id break end end
assert(target,'no bidirectional edge to flip')
one.edges_by_id[target].direction='forward'
local ov=assert(a:manifest(one))
local edge=one.edges_by_id[target]
local from_exits=0 for _,exit in ipairs(ov.nodes[edge.from_room].exits) do if exit.to==edge.to_room then from_exits=from_exits+1 end end
local back_exits=0 for _,exit in ipairs(ov.nodes[edge.to_room].exits) do if exit.to==edge.from_room then back_exits=back_exits+1 end end
assert(from_exits==1 and back_exits==0,'one-way edge not enforced')
-- Restore and confirm the gate closes again.
for id,value in pairs(saved) do Recipes.recipes[id].certified=value end
assert(not a:manifest(m))
assert(a:diagnostics(m).manifest_admissible==false)
print('adapter: certification gate, node/exit mapping, one-way handling and diagnostics passed')
'''

subprocess.run([LUA, '-', *[str(m) for m in MODULES]], input=TEST, text=True, check=True)
