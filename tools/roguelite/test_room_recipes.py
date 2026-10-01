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
-- Upper/drop sockets carry the expected anchor shapes and agree with the
-- authored visual transforms.
local branch=Rooms.rooms.branch_y
local g=assert(Recipes.resolve(branch))
assert(g.exit_anchors.top and g.exit_anchors.top.y==26 and g.exit_anchors.top.x==39 and not g.exit_anchors.top.drop)
local recipe=Recipes.get(branch.recipe)
assert(recipe.upper_doorway and recipe.upper_doorway.x==g.exit_anchors.top.x and recipe.upper_doorway.y==g.exit_anchors.top.y,
 'upper doorway must match the top anchor')
local modules=0 for _,m in ipairs(recipe.modules or {}) do modules=modules+1 end
assert(modules>=4,'ascent needs stairs/balcony/ramp/upper floor')
-- All shared ascent layouts must arrive on their flat lead-in, not underneath
-- the one-way stair slope (short fighters cannot climb it from below).
for _,r in pairs(Recipes.recipes) do if r.upper_doorway then
 local stair=r.geometry.lines[1]
 assert(r.geometry.spawn.y==stair.y0 and r.geometry.spawn.x<=stair.x0-Recipes.unit,
  'ascent spawn overlaps the stair slope')
 local a=r.geometry.arrivals.left
 assert(a.y==stair.y0 and a.x<=stair.x0-Recipes.unit and a.x>r.geometry.floor.left,
  'ascent arrival must have a flat lead-in inside the floor')
end end
local c=assert(Recipes.resolve(Rooms.rooms.junction_cross))
assert(c.exit_anchors.bottom and c.exit_anchors.bottom.drop,'drop socket must be marked')
assert(#c.floor.openings==1 and c.floor.openings[1].x==c.exit_anchors.bottom.x,'drop needs a real floor opening')
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
-- Orphan opening (no drop anchor) and drop anchor without an opening are refused.
local orphan=clone(Rooms); Recipes.recipes.lane_open.geometry.floor.openings={{x=0,width=26}}
assert(not Recipes.validate(orphan))
Recipes.recipes.lane_open.geometry.floor.openings={}
local noopen=clone(Rooms); Recipes.recipes.junction_cross.geometry.floor.openings={}
assert(not Recipes.validate(noopen))
Recipes.recipes.junction_cross.geometry.floor.openings={{x=0,width=13}}
assert(Recipes.validate(Rooms))
-- Authored hole width and safe arrivals are checked against geometry.
Recipes.recipes.junction_cross.geometry.floor.openings={{x=0,width=26}}
assert(not Recipes.validate(Rooms))
Recipes.recipes.junction_cross.geometry.floor.openings={{x=0,width=13}}
local arrival=Recipes.recipes.junction_cross.geometry.arrivals.bottom
Recipes.recipes.junction_cross.geometry.arrivals.bottom={x=0,y=0,facing=1}
assert(not Recipes.validate(Rooms),'arrival over a real hole accepted')
Recipes.recipes.junction_cross.geometry.arrivals.bottom=arrival
assert(Recipes.validate(Rooms))
print('room recipes: '..count..' templates resolve, reachable, uncertified; bounds and refusal passed')
'''

subprocess.run([LUA, '-', *[str(m) for m in MODULES]], input=TEST, text=True, check=True)
