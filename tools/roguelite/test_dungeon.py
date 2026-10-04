#!/usr/bin/env python3
"""Execute the real pure Lua module: properties and adversarial fixtures."""
from pathlib import Path
import shutil
import subprocess
import game_source

ROOT = Path(__file__).resolve().parents[2]
MODULE = game_source.ROGUELITE / 'dungeon.lua'
LUA = shutil.which('lua5.4') or shutil.which('lua')
assert LUA, 'Lua interpreter required'
TEST = r'''
local D=dofile(arg[1])
local function clone(t) if type(t)~='table' then return t end local o={} for k,v in pairs(t) do o[k]=clone(v) end return o end
local function serialize(t)
 if type(t)~='table' then return type(t)..':'..tostring(t) end
 local keys={} for k in pairs(t) do keys[#keys+1]=k end
 table.sort(keys,function(a,b) return tostring(a)<tostring(b) end)
 local out={} for _,k in ipairs(keys) do out[#out+1]=serialize(k)..'='..serialize(t[k]) end return '{'..table.concat(out,',')..'}'
end
local function reject(m,expected,profile)
 local ok,why=D.validate(m,profile); assert(not ok,'invalid fixture accepted')
 assert(why:find(expected,1,true),why)
end
local outputs={}
for seed=1,300 do
 local m=D.generate(seed)
 local valid,why,screen=D.validate(m);assert(valid,why)
 assert(m.schema_version==1 and m.version==1 and m.generator_version==2)
 assert(m.traversal_certified==false and screen and screen.traversal_certified==false)
 assert(screen.all_platforms_reachable==false and screen.mobility_scaled==false)
 assert(serialize(m)==serialize(D.generate(seed)))
 outputs[serialize(m.nodes.arena_a.room)]=true
 assert(#m.nodes.trail.exits==2)
 for _,node in pairs(m.nodes) do
  local r=node.room
  assert(r.floor.left==-130 and r.floor.right==130 and r.floor.y==0)
  assert(r.spawn.x==-84 and r.spawn.y==0)
  assert(r.kit.unit==13 and r.kit.grid==26 and r.kit.bay==52 and r.kit.height==52 and r.kit.depth==0)
  for _,enemy in ipairs(r.enemy_spawns) do assert(enemy.x==56 and enemy.y==0) end
  assert(r.exit_anchors.left.x==-104 and r.exit_anchors.right.x==104)
  assert(r.camera.left==-130 and r.camera.right==130 and r.camera.bottom==-36 and r.camera.top==108 and r.camera.top-r.camera.bottom==144)
  if #r.platforms>0 then
   local a,b,c=table.unpack(r.platforms)
   assert(a.width==44 and b.width==44 and c.width==48)
   assert(a.y==24 and b.y==24 and c.y==48)
   assert(r.kit.unit==13 and r.kit.grid==26 and r.kit.bay==52 and r.kit.height==52)
   assert(a.x-c.x==-44 and b.x-c.x==44 and c.x%2==0 and math.abs(c.x)<=8)
   for _,p in ipairs(r.platforms) do assert(p.passthrough and not p.ledges) end
  end
 end
 for _,choice in ipairs(m.nodes.trail.exits) do
  local id=choice.to; local steps=0
  while m.nodes[id].kind~='exit' do
   local n=m.nodes[id]; assert(#n.exits==1 and not n.exits[1].requires)
   id=n.exits[1].to; steps=steps+1; assert(steps<10)
  end
 end
end
local variants=0 for _ in pairs(outputs) do variants=variants+1 end assert(variants>3)
local base=D.generate(789)
-- Doubling cell geometry never doubles fighter jump capability or certification.
reject(base,'unreachable platform',{jump_height=18,horizontal_gap=30})
local reaches,why,screen=D.validate(base,{jump_height=24,horizontal_gap=30})
assert(reaches,why);assert(screen.all_platforms_reachable and not screen.traversal_certified)
local future=clone(base);future.generator_version=3;reject(future,'invalid manifest')
local wrongschema=clone(base);wrongschema.schema_version=2;reject(wrongschema,'invalid manifest')

local m=clone(base); m.nodes.entry.exits[1].to='absent'; reject(m,'invalid graph edge')
m=clone(base); m.nodes.boss.exits[1].requires='rime'; reject(m,'exit requires')
m=clone(base); m.nodes.arena_a.exits={}; reject(m,'branch has no unconditional exit')
m=clone(base); m.nodes.approach.exits={}; reject(m,'unreachable graph node')
m=clone(base); m.nodes.trail.room.platforms={{x=0,y=55,width=20,passthrough=true,ledges=true}}; reject(m,'unreachable platform',{jump_height=18,horizontal_gap=30})
m=clone(base); for i=1,17 do m.nodes.entry.room.platforms[i]={x=0,y=10,width=8,passthrough=true,ledges=false} end reject(m,'budget')
m=clone(base); m.nodes.entry.room.spawn.x=0/0; reject(m,'invalid spawn')
m=clone(base); m.nodes.trail.room.exit_anchors.right.y=50; reject(m,'invalid exit anchor')
m=clone(base); m.nodes.trail.room.exit_anchors.left.x=-55; reject(m,'invalid exit anchor')
m=clone(base); m.nodes.trail.room.kit.grid=12; reject(m,'incompatible kit structure')
m=clone(base); m.nodes.trail.room.platforms[1].width=400; reject(m,'platform bounds')
m=clone(base); m.nodes.trail.room.platforms[1].passthrough=false; reject(m,'clearance')
reject(base,'unreachable platform',{jump_height=5,horizontal_gap=30})
assert(not pcall(D.generate,0)); assert(not pcall(D.generate,math.huge))
print('dungeon: 300 seeded routes, reproducibility, both branches and adversarial validation passed')
'''
subprocess.run([LUA, '-', str(MODULE)], input=TEST, text=True, check=True)
