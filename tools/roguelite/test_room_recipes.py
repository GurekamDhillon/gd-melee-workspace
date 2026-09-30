#!/usr/bin/env python3
"""Validate the physical recipe contract: coverage, bounds, reachability, refusal."""
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
-- Every template resolves geometry whose anchors cover its declared sockets,
-- and every recipe passes the analytic ascent screen. None are certified yet.
local count,certified=0,0
for id,template in pairs(Rooms.rooms) do
 count=count+1
 local geometry,recipe=Recipes.resolve(template)
 assert(geometry,id..' should resolve: '..tostring(recipe))
 for _,socket in ipairs(template.sockets) do assert(geometry.exit_anchors[socket.side],id..' missing anchor for '..socket.side) end
 assert(geometry.floor.left==-65 and geometry.floor.right==65)
 assert(geometry.spawn and geometry.camera)
 local reachable,reason=Recipes.reachable(recipe); assert(reachable,id..': '..tostring(reason))
 if Recipes.is_certified(template.recipe) then certified=certified+1 end
end
assert(count>=18,'only '..count..' templates')
assert(certified==0,'nothing may be certified before native clips; got '..certified)
-- Upper/drop sockets carry the expected anchor shapes.
local g=assert(Recipes.resolve(Rooms.rooms.branch_y))
assert(g.exit_anchors.top and g.exit_anchors.top.y==26 and not g.exit_anchors.top.drop)
local c=assert(Recipes.resolve(Rooms.rooms.junction_cross))
assert(c.exit_anchors.bottom and c.exit_anchors.bottom.drop,'drop socket must be marked')
-- A missing anchor for a declared socket side is refused, not guessed.
local fake={recipe='lane_open',sockets={{id='in',side='left'},{id='out',side='middle'}}}
local fg,fr=Recipes.resolve(fake); assert(not fg and tostring(fr):find('no anchor',1,true))
-- Unknown recipes and malformed geometry are refused.
assert(not Recipes.resolve({recipe='nope',sockets={}}))
local function clone(v) if type(v)~='table' then return v end local o={} for k,x in pairs(v) do o[k]=clone(x) end return o end
local bad=clone(Rooms); bad.rooms.lane_straight.recipe='ghost_recipe'
assert(not Recipes.validate(bad))
bad=clone(Rooms); bad.rooms.lane_straight.sockets={{id='in',side='left'},{id='out',side='middle'}}
assert(not Recipes.validate(bad))
-- Out-of-bounds authored geometry is refused, and the module is restored after.
local original=Recipes.recipes.lane_open.geometry.platforms
Recipes.recipes.lane_open.geometry.platforms={{x=100,y=0,width=10,passthrough=true,ledges=true}}
assert(not Recipes.validate(Rooms))
Recipes.recipes.lane_open.geometry.platforms=original
assert(Recipes.validate(Rooms))
-- An ascent that exceeds the jump profile fails the reachability screen.
local steep=clone(Recipes.recipes.lane_balcony)
steep.geometry.platforms={{x=0,y=55,width=8,passthrough=true,ledges=true}}
assert(not Recipes.reachable(steep))
print('room recipes: '..count..' templates resolve, reachable, uncertified; bounds and refusal passed')
'''

subprocess.run([LUA, '-', *[str(m) for m in MODULES]], input=TEST, text=True, check=True)
