#!/usr/bin/env python3
"""Validate the room/encounter catalogue contracts and their refusals."""
from pathlib import Path
import shutil
import subprocess
from tools.test_support import require_game
require_game('pc/scripts/examples/roguelite')
import game_source

ROOT = Path(__file__).resolve().parents[2]
RT = game_source.ROGUELITE
LUA = shutil.which('lua5.4') or shutil.which('lua')
assert LUA, 'Lua interpreter required'

MODULES = [RT / name for name in ('rng.lua', 'room_catalogue.lua', 'encounter_catalogue.lua',
                                  'progression.lua', 'topology.lua')]

TEST = r'''
local RNG=dofile(arg[1]); local Rooms=dofile(arg[2]); local Enc=dofile(arg[3])
local Prog=dofile(arg[4]); local Top=dofile(arg[5])
assert(Rooms.validate() and Enc.validate())
-- Every required role has at least one template, and shapes are present.
for role in pairs(Rooms.roles) do
 if role~='finish' and role~='branch' then assert(#Rooms.templates_for_role(role)>0,'role without template: '..role) end
end
local split,merge,cross=false,false,false
for _,t in pairs(Rooms.rooms) do if t.shape=='split' then split=true elseif t.shape=='merge' then merge=true elseif t.shape=='cross' then cross=true end end
assert(split and merge and cross,'missing branch shapes')
-- Socket ids and sides are unique per template; every socket has a side.
for _,t in pairs(Rooms.rooms) do
 local ids,sides={},{}
 for _,s in ipairs(t.sockets) do assert(not ids[s.id],'dup socket'); assert(not sides[s.side],'dup side'); ids[s.id],sides[s.side]=true,true end
end
-- Finite content targets (plan section 3): compositions, bosses, rewards and
-- the authored reaction vocabulary, with implementations honestly unclaimed.
local encounters,bosses,rewards,locks,reactions=0,0,0,0,0
for _,e in pairs(Enc.encounters) do if e.archetype=='boss' then bosses=bosses+1 else encounters=encounters+1 end end
for _ in pairs(Enc.rewards) do rewards=rewards+1 end
for _ in pairs(Enc.locks) do locks=locks+1 end
local boss_themes={}
for _,e in pairs(Enc.encounters) do if e.archetype=='boss' then for _,t in ipairs(e.themes) do boss_themes[t]=true end end end
for _,r in pairs(Enc.reactions) do reactions=reactions+1; assert(r.implemented==false,'reaction must not claim implementation') end
assert(encounters>=12,'only '..encounters..' encounter compositions')
assert(bosses>=3,'only '..bosses..' bosses')
assert(rewards>=24,'only '..rewards..' rewards')
assert(locks>=3,'only '..locks..' locks')
assert(reactions>=6,'only '..reactions..' reactions')
assert(boss_themes.cobalt and boss_themes.frost and boss_themes.fire,'boss themes must cover all three themes')
-- Encounter theme filtering returns only allowed rows and covers each theme.
for _,theme in pairs({'cobalt','frost','fire'}) do
 local rows=Enc.encounters_for_theme(theme)
 assert(#rows>0,'no encounters for '..theme)
 for _,e in ipairs(rows) do
  local ok=false for _,a in ipairs(e.themes) do if a==theme then ok=true end end assert(ok)
 end
end
-- Invalid catalogue fixtures are refused.
local function clone(v) if type(v)~='table' then return v end local o={} for k,x in pairs(v) do o[k]=clone(x) end return o end
local function reject_rooms(mutate) local c=clone(Rooms); mutate(c); assert(not pcall(c.validate,c),'invalid room catalogue accepted') end
reject_rooms(function(c) c.rooms.branch_y.sockets={{id='in',side='left'},{id='in',side='top'}} end)
reject_rooms(function(c) c.rooms.branch_y.sockets={{id='a',side='left'},{id='b',side='left'}} end)
reject_rooms(function(c) c.rooms.branch_y.shape='blob' end)
reject_rooms(function(c) c.rooms.branch_y.role='nope' end)
reject_rooms(function(c) c.rooms.branch_y.sockets={} end)
local function reject_enc(mutate) local c=clone(Enc); mutate(c); assert(not pcall(c.validate,c),'invalid encounter catalogue accepted') end
reject_enc(function(c) c.encounters.scout_pair.difficulty=9 end)
reject_enc(function(c) c.encounters.scout_pair.enemies={} end)
reject_enc(function(c) c.rewards.potency_small.kind='bogus' end)
reject_enc(function(c) c.rewards.potency_small.family='void' end)
reject_enc(function(c) c.locks.frost_gate.kind='bogus' end)
reject_enc(function(c) c.reactions.thermal_shock.components={} end)
reject_enc(function(c) c.reactions.thermal_shock.implemented='yes' end)
print('catalogue: roles, shapes, sockets, theme filtering and refusal passed')
'''

subprocess.run([LUA, '-', *[str(m) for m in MODULES]], input=TEST, text=True, check=True)
