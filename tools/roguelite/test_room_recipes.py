#!/usr/bin/env python3
"""Validate the physical recipe contract: coverage, bounds and explicit refusal."""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
RT = ROOT / 'melee/worktrees/linux/pc/scripts/examples/roguelite'
LUA = shutil.which('lua5.4') or shutil.which('lua')
assert LUA, 'Lua interpreter required'

MODULES = [RT / 'room_catalogue.lua', RT / 'room_recipes.lua']

TEST = r'''
local Rooms=dofile(arg[1]); local Recipes=dofile(arg[2])
local ok,why=Recipes.validate(Rooms); assert(ok,why)
-- Every supported recipe resolves geometry whose anchors cover its sockets.
local supported,unsupported=0,0
for id,template in pairs(Rooms.rooms) do
 local geometry,recipe=Recipes.resolve(template)
 if Recipes.is_supported(template.recipe) then
  supported=supported+1
  assert(geometry,id..' should resolve: '..tostring(recipe))
  for _,socket in ipairs(template.sockets) do assert(geometry.exit_anchors[socket.side],id..' missing anchor') end
  assert(geometry.floor.left==-65 and geometry.floor.right==65)
 else
  unsupported=unsupported+1
  assert(geometry==nil,'unsupported resolved')
  assert(tostring(recipe):find('unsupported',1,true),'missing unsupported reason for '..id)
 end
end
assert(supported>=8 and unsupported>=6,'supported='..supported..' unsupported='..unsupported)
-- The 3-socket branch shapes are explicitly unsupported (no authored up/down doors).
assert(not Recipes.is_supported('branch_y') and not Recipes.is_supported('rejoin_merge'))
assert(not Recipes.is_supported('junction_cross') and not Recipes.is_supported('shortcut_door'))
-- A missing anchor for a declared socket side is refused, not guessed.
local fake={recipe='lane_open',sockets={{id='in',side='left'},{id='out',side='middle'}}}
local g,r=Recipes.resolve(fake); assert(not g and tostring(r):find('no anchor',1,true))
-- Unknown recipes and malformed geometry are refused.
assert(not Recipes.resolve({recipe='nope',sockets={}}))
local function clone(v) if type(v)~='table' then return v end local o={} for k,x in pairs(v) do o[k]=clone(x) end return o end
local bad=clone(Rooms); bad.rooms.lane_straight.recipe='ghost_recipe'
assert(not Recipes.validate(bad))
-- A declared socket side without an anchor is refused.
bad=clone(Rooms); bad.rooms.lane_straight.sockets={{id='in',side='left'},{id='out',side='middle'}}
assert(not Recipes.validate(bad))
-- Out-of-bounds authored geometry is refused, and the module is restored after.
local original=Recipes.recipes.lane_open.geometry.platforms
Recipes.recipes.lane_open.geometry.platforms={{x=100,y=0,width=10,passthrough=true,ledges=true}}
assert(not Recipes.validate(Rooms))
Recipes.recipes.lane_open.geometry.platforms=original
assert(Recipes.validate(Rooms))
print('room recipes: '..supported..' supported, '..unsupported..' explicitly unsupported, bounds and refusal passed')
'''

subprocess.run([LUA, '-', *[str(m) for m in MODULES]], input=TEST, text=True, check=True)
