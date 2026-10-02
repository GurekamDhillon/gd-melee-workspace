"""Actual Lua custom-enemy adapter invariants; native combat has separate tests."""
from pathlib import Path
import shutil
import subprocess
import unittest
import game_source

BASE = game_source.ROGUELITE

class EnemyGenesTests(unittest.TestCase):
    def test_shared_rules_and_lifecycle(self):
        lua = shutil.which('lua') or shutil.which('lua5.4')
        self.assertIsNotNone(lua)
        program = r'''
local C=assert(loadfile(arg[1]))();local E=assert(loadfile(arg[2]))()
local profile=C.new_profile(891);local run=C.new_run(profile)
local actors={ [11]={x=0,y=0,facing=1,hits=0,attack_id=1,received=0},[12]={x=0,y=0,facing=1,hits=0,attack_id=1,received=0} }
local calls,events,incoming=0,{},0;local accepted=false
local gd={enemy_state=function(h)return actors[h]end,player=function()return {x=2,y=0}end,
 enemy_strike=function(h,p,a) assert(h==11 or h==12);assert(p==1);assert(a.damage>=9 and a.reach==9);calls=calls+1;return accepted end}
local e=E.new(C,gd,{get_run=function()return run end,on_tell=function(s,event)events[#events+1]=event;assert(s.host)end,
 on_player_hit=function(h,from,damage)error('authoritative event mode must not poll incoming hits') end})
assert(not e:attach(11,{host='player',family='cinder'}))
assert(not e:attach(11,{host='enemy_a',family='cinder',slot='guard'}))
assert(e:attach(11,{host='enemy_a',family='cinder'}))
local id=run.hosts.enemy_a.slots.assault;assert(run.genes[id].base.potency==8)
assert(C.ability(run,'enemy_a','assault').damage==9 and C.ability(run,'enemy_a','assault').cost==1)
assert(not e:attach(12,{host='enemy_a',family='cinder'}))
assert(e:attach(12,{host='enemy_b',family='rime'}))
local seed,nextid=run.seed,run.next_id;e:detach(12);assert(e:attach(12,{host='enemy_b',family='rime'}));assert(run.seed==seed and run.next_id==nextid)
actors[11].hits=1;actors[11].received=1;actors[11].last_attacker=2;actors[11].last_damage=7
C.tick(run,1);e:tick();assert(incoming==0 and e:states()[1].phase=='telegraph')
local frame=run.frame;e:tick();assert(run.frame==frame and incoming==0)
actors[11].hits=2 -- same activation, another victim must not charge twice
C.tick(run,24);e:tick();assert(calls==1 and C.ability(run,'enemy_a','assault').ready)
assert(run.hosts.enemy_a.state.assault.ready_at==0)
-- Fresh restored run must be used, no old captured references.
run=assert(C.restore(C.snapshot(run)));accepted=true
C.tick(run,20);e:tick();C.tick(run,24);e:tick();assert(calls==2 and not C.ability(run,'enemy_a','assault').ready)
assert(C.ability(run,'enemy_a','assault').remaining==90)
actors[12].hits=1;C.tick(run,1);e:tick();C.tick(run,24);e:tick()
assert(run.marks.player and run.marks.player.source=='enemy_b')
-- Borrowed instances cannot leave via player fusion/export.
assert(not C.fuse(run,id,'r1'));assert(not C.finish(profile,run,'success',id))
actors[11]=nil;C.tick(run,1);e:tick();assert(#e:states()==1)
local before=calls;C.tick(run,30);e:tick();assert(calls==before)
e:clear();assert(#e:states()==0 and run.hosts.enemy_a.slots.assault==id)
print('enemy adapter invariants passed')
'''
        result = subprocess.run([lua, '-', str(BASE/'core.lua'), str(BASE/'enemy_genes.lua')], input=program, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout+result.stderr)


if __name__ == '__main__':
    unittest.main()
