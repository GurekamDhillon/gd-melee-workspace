"""Execute combat feedback in real Lua, including Core-driven readiness/deltas.

Renderer checks use recorded engine calls; native appearance remains a root-led check.
"""
from pathlib import Path
import shutil
import subprocess
import unittest
import game_source

RUNTIME = game_source.ROGUELITE


class FeedbackTests(unittest.TestCase):
    def run_lua(self, body):
        lua = shutil.which('lua') or shutil.which('lua5.4')
        self.assertIsNotNone(lua, 'Lua interpreter required; do not translate the policy to Python')
        prelude = r'''
local F=assert(loadfile(arg[1]))()
local C=assert(loadfile(arg[2]))()
local p=C.new_profile(123);local r=C.new_run(p);local s=F.new()
local function observed()
 local a={};for _,slot in ipairs({'assault','traversal','guard'}) do
  a[slot]=C.ability(r,'player',slot)
 end;return a
end
local function sync(n,paused) F.update(s,observed(),n or 0,paused,r.hosts.player.slots) end
local function charge()
 for i=1,3 do C.on_event(r,{host='player',kind='direct_hit',move_id='hit:'..r.frame..':'..i}) end
end
local function advance(n,paused)
 if not paused then assert(C.tick(r,n)) end;sync(n,paused)
end
'''
        result = subprocess.run(
            [lua, '-', str(RUNTIME / 'feedback.lua'), str(RUNTIME / 'core.lua')],
            input=prelude + body, text=True, capture_output=True, timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_core_readiness_charge_cooldown_and_identity(self):
        self.run_lua(r'''
sync();assert(F.view(s).slots.assault.status=='CHARGING')
assert(F.view(s).slots.assault.charge==0 and not F.view(s).slots.traversal)
C.on_event(r,{host='player',kind='direct_hit',move_id='one'});sync()
assert(F.view(s).slots.assault.charge==1 and F.view(s).queued==0)
charge();sync();local a=F.view(s).slots.assault
assert(a.ready and a.pulse==1 and a.ratio==1 and F.view(s).queued==0)
advance(18);assert(F.view(s).slots.assault.pulse==.5)
advance(18);a=F.view(s).slots.assault;assert(a.ready and a.pulse==0)
for i=1,90 do advance(1);assert(F.view(s).slots.assault.pulse==0) end
local action=assert(C.activate(r,'player','assault'));sync();a=F.view(s).slots.assault
assert(a.status=='COOLDOWN' and a.remaining==action.cooldown and a.charge==0)
advance(action.cooldown);assert(F.view(s).slots.assault.status=='CHARGING')
charge();sync();assert(F.view(s).slots.assault.pulse==1)
-- Rest changes/ready saved-state load do not pretend a new charge threshold was earned.
assert(C.equip(r,'player','assault',nil));assert(C.equip(r,'player','traversal','r1'))
sync();assert(F.view(s).slots.traversal.ready and F.view(s).slots.traversal.pulse==0)
F.reset(s);sync();assert(F.view(s).slots.traversal.pulse==0)
local view=F.view(s);view.slots.traversal.charge=-100
assert(F.view(s).slots.traversal.charge==3)
''')

    def test_queue_priorities_preemption_bounds_and_fifo(self):
        self.run_lua(r'''
for i=1,6 do assert(F.notify(s,{kind='info',key='info'..i,title='Info '..i})) end
assert(F.view(s).queued==6 and F.view(s).notification.key=='info1')
local ok,why=F.notify(s,{kind='info',key='overflow',title='Dropped'})
assert(ok==false and why=='queue full')
assert(F.notify(s,{kind='clear',key='room',title='Cleared'}))
assert(F.view(s).queued==6 and F.view(s).notification.key=='room')
assert(F.notify(s,{kind='error',key='save',title='Write failed'}))
assert(F.view(s).notification.key=='save')
assert(F.notify(s,{kind='failure',key='death',title='Ended'}))
assert(F.view(s).queued==6 and F.view(s).notification.key=='death')
F.dismiss(s,'death');assert(F.view(s).notification.key=='save')
F.dismiss(s,'save');F.dismiss(s,'room')
assert(F.view(s).notification.key=='info1')
assert(s.queue[2].key=='info2' and s.queue[3].key=='info3')
-- All higher priority kinds preempt; same-priority events retain arrival order.
F.dismiss(s);F.notify(s,{kind='blocked',key='first',title='First'})
F.notify(s,{kind='blocked',key='second',title='Second'})
assert(F.view(s).notification.key=='first')
F.dismiss(s,'first');assert(F.view(s).notification.key=='second')
''')

    def test_coalescing_expiry_including_waiting_and_reset(self):
        self.run_lua(r'''
F.notify(s,{kind='blocked',key='target',title='Face target',ttl=10})
advance(5)
local ok,why=F.notify(s,{kind='blocked',key='target',title='Face nearby target',ttl=3600})
assert(ok and why=='coalesced');local v=F.view(s)
assert(v.queued==1 and v.notification.count==2 and v.notification.expires==10)
assert(v.notification.title=='Face nearby target')
for i=1,200 do F.notify(s,{kind='blocked',key='target',title='Face nearby target'}) end
assert(F.view(s).notification.count==99)
advance(5);assert(F.view(s).queued==0)
F.notify(s,{kind='error',key='save',title='Save failed',ttl=20})
F.notify(s,{kind='release',key='ability',title='Cinder Eruption',ttl=5})
advance(5);assert(F.view(s).queued==1 and F.view(s).notification.key=='save')
advance(15);assert(F.view(s).queued==0)
-- Same key used by a different kind cannot turn a refusal into a celebration.
F.notify(s,{kind='clear',key='room',title='Cleared'})
F.notify(s,{kind='error',key='room',title='Checkpoint failed'})
assert(F.view(s).queued==2 and not F.view(s).notification.celebrate)
F.reset(s);assert(F.view(s).clock==0 and F.view(s).queued==0 and not next(F.view(s).slots))
assert(not F.notify(s,{kind='imaginary',title='No'}))
assert(not F.notify(s,{kind='info',title='No',ttl=0}))
assert(not F.notify(s,{kind='info',title='No',ttl=math.huge}))
assert(not pcall(F.update,s,{},0/0))
''')

    def test_menu_pause_freezes_lifetime_and_motion(self):
        self.run_lua(r'''
sync();charge();sync();F.notify(s,{kind='clear',key='arena',title='Cleared',ttl=120})
advance(10);local v=F.view(s);local pulse=v.slots.assault.pulse
for i=1,100 do advance(60,true) end
v=F.view(s);assert(v.clock==10 and v.paused and v.slots.assault.pulse==pulse)
assert(v.queued==1 and v.notification.expires==120)
advance(26);assert(F.view(s).slots.assault.ready and F.view(s).slots.assault.pulse==0)
advance(84);assert(F.view(s).queued==0)
-- Menu-driven observed changes do not pulse on resume.
assert(C.activate(r,'player','assault'));advance(90);charge();sync(0,true)
assert(F.view(s).slots.assault.ready and F.view(s).slots.assault.pulse==0)
sync(0,false);assert(F.view(s).slots.assault.pulse==0)
F.reset(s);s.reduced=true;sync();assert(F.view(s).slots.assault.pulse==0)
assert(s.reduced);F.reset(s);assert(s.reduced)
''')

    def test_committed_clamped_deltas_and_truthful_finish_notices(self):
        self.run_lua(r'''
local before=C.resolve(r,'player','assault')
assert(F.clear(s,{key='arena',title='Arena A',reward=true}));sync(0,true)
assert(C.reward(r,'r1','potency',100));assert(C.reward(r,'r1','gain',-.25))
local after=C.resolve(r,'player','assault')
assert(F.reward(s,{key='reward1',name='Power specialization',before=before,after=after}))
local e=F.view(s).notification
assert(e.kind=='upgrade' and e.celebrate and #e.deltas==2)
assert(F.view(s).queued==2) -- committed upgrade immediately preempts paused clear notice
assert(e.deltas[1].before==10 and e.deltas[1].after==30 and e.deltas[1].delta==20)
assert(e.deltas[2].before==1 and e.deltas[2].after==.75)
assert(e.detail:find('Power 10 > 30',1,true) and e.detail:find('Gain 1 > 0.75',1,true))
assert(not e.detail:find('Cooldown',1,true)) -- no invented cooldown tradeoff
after.potency=1;assert(F.view(s).notification.deltas[1].after==30)
F.dismiss(s);after=C.resolve(r,'player','assault')
assert(F.reward(s,{before=after,after=after}));assert(not F.view(s).notification.celebrate)
F.dismiss(s);assert(not F.reward(s,{before=after}));assert(F.view(s).queued==0)
local result=assert(C.finish(p,r,'success','r1'));F.finish(s,result)
e=F.view(s).notification
assert(e.kind=='inheritance' and e.detail:find(result.export,1,true))
assert(e.detail:find('Temporary upgrades excluded',1,true))
assert(next(p.genes[result.export].upgrades)==nil)
F.dismiss(s);local failed=C.new_run(p);F.finish(s,assert(C.finish(p,failed,'failure')))
e=F.view(s).notification;assert(e.kind=='failure' and not e.celebrate)
assert(e.detail:find('Collection retained',1,true))
F.dismiss(s);F.finish(s,{outcome='success'})
assert(F.view(s).notification.detail=='Collection retained / No gene exported')
F.dismiss(s);assert(not F.finish(s,nil));assert(not F.finish(s,{outcome='refused'}))
assert(F.view(s).queued==0)
''')

    def test_draw_bounds_pause_determinism_and_reduced_effects(self):
        self.run_lua(r'''
local fills,texts,icons={},{},{}
gd={fill=function(x,y,w,h,color)
 assert(x>=0 and y>=0 and w>=0 and h>=0 and x+w<=640 and y+h<=480)
 fills[#fills+1]={x=x,y=y,w=w,h=h,color=color}
end,kit={text=function(x,y,t,role,color,align,opts)
 assert(opts.max_w and x+opts.max_w<=640 and y<=480)
 texts[#texts+1]=t
end,icon=function(name,x,y,scale,color)
 assert(name:match('^rogue_'));icons[#icons+1]=name
end}}
sync();charge();sync();assert(F.clear(s,{key='arena',title='Arena A',reward=true}))
F.draw(s);local normal=#fills;assert(#icons==4)
assert(table.concat(texts,'|'):find('READY',1,true))
assert(table.concat(texts,'|'):find('Choose a reward',1,true))
-- Combat rectangles stay in the compact bottom rail or brief top notification, including shadows.
for _,f in ipairs(fills) do assert(f.y+f.h<=52 or f.y>=407) end
local before=F.view(s);F.draw(s);assert(F.view(s).clock==before.clock)
fills={};texts={};F.draw(s,{player={percent=123,lives=2,supplies=1},opponent={percent=87,lives=2,label='CHAMPION'}})
assert(table.concat(texts,'|'):find('123%%'))
assert(table.concat(texts,'|'):find('LIVES 2',1,true))
assert(table.concat(texts,'|'):find('87%% / 2 LEFT'))
fills={};F.draw(s,{hud=false,compact_menu=true})
for _,f in ipairs(fills) do assert(f.y>=63 and f.y+f.h<=89) end
fills={};icons={};F.draw(s,{reduced=true});assert(#fills<normal)
assert(F.view(s).slots.assault.ready)
-- Warning/refusal events have no success line or sparks.
F.dismiss(s);F.notify(s,{kind='blocked',title='Face nearby fighter'})
fills={};F.draw(s,{hud=false});assert(#fills==3)
fills={};icons={};F.draw(s,{hud=false,notifications=false});assert(#fills==0 and #icons==0)
''')


if __name__ == '__main__':
    unittest.main()
