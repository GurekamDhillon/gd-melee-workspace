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
 assert(D.validate(m)); assert(serialize(m)==serialize(D.generate(seed)))
 outputs[serialize(m.nodes.arena_a.room)]=true
 assert(#m.nodes.trail.exits==2)
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
local m=clone(base); m.nodes.entry.exits[1].to='absent'; reject(m,'invalid graph edge')
m=clone(base); m.nodes.boss.exits[1].requires='rime'; reject(m,'exit requires')
m=clone(base); m.nodes.arena_a.exits={}; reject(m,'branch has no unconditional exit')
m=clone(base); m.nodes.approach.exits={}; reject(m,'unreachable graph node')
m=clone(base); m.nodes.trail.room.platforms={{x=0,y=55,width=20,passthrough=true,ledges=true}}; reject(m,'unreachable platform')
m=clone(base); for i=1,17 do m.nodes.entry.room.platforms[i]={x=0,y=10,width=8,passthrough=true,ledges=false} end reject(m,'budget')
m=clone(base); m.nodes.entry.room.spawn.x=0/0; reject(m,'invalid spawn')
m=clone(base); m.nodes.trail.room.exit_anchors.right.y=50; reject(m,'invalid exit anchor')
m=clone(base); m.nodes.trail.room.exit_anchors.left.x=-55; reject(m,'invalid exit anchor')
m=clone(base); m.nodes.trail.room.kit.grid=12; reject(m,'incompatible kit structure')
m=clone(base); m.nodes.trail.room.platforms[1].width=200; reject(m,'platform bounds')
m=clone(base); m.nodes.trail.room.platforms[1].passthrough=false; reject(m,'clearance')
reject(base,'unreachable platform',{jump_height=5,horizontal_gap=30})
assert(not pcall(D.generate,0)); assert(not pcall(D.generate,math.huge))
print('dungeon: 300 seeded routes, reproducibility, both branches and adversarial validation passed')
'''
subprocess.run([LUA, '-', str(MODULE)], input=TEST, text=True, check=True)
