#!/usr/bin/env python3
"""Exercise the bounded run-progress record: transitions, bounds, codec round-trip."""
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

MODULES = [RT / 'codec.lua', RT / 'progress.lua']

TEST = r'''
local Codec=dofile(arg[1]); local P=dofile(arg[2])
local r=P.new('run1','r001',{supplies=2,lives=3})
assert(P.validate(r))
assert(r.visited.r001 and r.discovered.r001 and r.current_room=='r001')
-- Transitions.
assert(P.enter(r,'r002','out')); assert(r.current_room=='r002' and r.current_socket=='out' and r.visited.r002)
assert(P.reveal(r,'r002','e003')); assert(r.discovered.r002 and r.revealed.e003)
assert(P.claim(r,'reward_x')); assert(P.claim(r,'reward_x')) -- idempotent
assert(P.unlock(r,'frost_key')); assert(r.keys.frost_key)
assert(P.grant_consumable(r,'charge',2)); assert(r.consumables.charge==2)
assert(P.spend_consumable(r,'charge')); assert(r.consumables.charge==1)
assert(P.defeat(r,'enemy_r002_1')); assert(r.defeated.enemy_r002_1)
assert(P.complete_objective(r,'boss','done')); assert(r.objectives.boss=='done')
assert(P.spend_supply(r) and r.supplies==1)
assert(P.lose_life(r) and r.lives==2)
assert(P.validate(r))
-- Serialization round trip.
local text=assert(Codec.encode(r)); local back=assert(Codec.decode(text)); assert(P.validate(back))
assert(P.enter(back,'r003') and back.current_room=='r003')
-- Bounds and refusals.
local capped=P.new('run2','r000')
for i=1,63 do assert(P.enter(capped,'room'..i)) end
local ok,why=P.enter(capped,'overflow'); assert(not ok and tostring(why):find('capacity',1,true))
assert(not P.grant_consumable(r,'charge',99))
local c2=P.new('run3','r000'); assert(P.grant_consumable(c2,'k',9)); assert(not P.grant_consumable(c2,'k',1))
assert(not P.spend_consumable(c2,'missing'))
assert(not P.enter({version=99},'x'))
assert(not P.enter(r,''))
assert(not P.complete_objective(r,'x','bogus'))
local bad=P.new('run4','r000'); bad.mystery=true; assert(not P.validate(bad))
bad=P.new('run4','r000'); bad.visited.r000=nil; assert(not P.validate(bad)) -- current room not visited
bad=P.new('run4','r000'); bad.supplies=99; assert(not P.validate(bad))
bad=P.new('run4','r000'); bad.consumables.k=0; assert(not P.validate(bad))
assert(P.finish(r,'success') and r.outcome=='success' and P.validate(r))
assert(not P.enter(r,'r999'),'finished run must not advance')
print('progress: transitions, bounds, refusal, codec round-trip and finish passed')
'''

subprocess.run([LUA, '-', *[str(m) for m in MODULES]], input=TEST, text=True, check=True)
