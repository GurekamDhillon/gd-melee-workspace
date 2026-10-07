"""Execute actual menu view models, exact previews and input using real Lua Core."""
from pathlib import Path
import shutil
import subprocess
import unittest
from tools.test_support import require_game
require_game('pc/scripts/examples/roguelite')
import game_source

SOURCE = game_source.ROGUELITE


class MenuTests(unittest.TestCase):
    def test_views_actions_and_rendering(self):
        lua = shutil.which('lua') or shutil.which('lua5.4')
        self.assertIsNotNone(lua, 'Lua interpreter required')
        program = r'''
Core=assert(loadfile(arg[1]..'/core.lua'))()
local M=assert(loadfile(arg[1]..'/menus.lua'))()
local C=Core
local p=C.new_profile(321);local r=C.new_run(p)
local s=M.new();local ctx={menu='collection',profile=p,run=r,starter='g1',node={id='arena_a'}}
local function snapshot() return C.snapshot(p)..C.snapshot(ctx.run) end
local function button(v,id) for _,b in ipairs(v.controls) do if b.id==id then return b end end error('missing control '..id) end
local function click(id)
 local b=button(M.view(s,ctx),id)
 return M.update(s,ctx,{mx=b.x+5,my=b.y+5,click=true})
end
local unchanged=snapshot()
local v=M.view(s,ctx);assert(v.selected.id=='g1' and v.selected.stats.potency==10)
assert(click('gene:g3')==nil and s.selected=='g3')
local a=click('starter');assert(a.kind=='starter' and a.id=='g3')
local result=M.apply(ctx,a);assert(result.ok and result.starter=='g3');ctx.starter=result.starter
local before=snapshot()
for _,control in ipairs(M.view(s,ctx).controls) do
 assert(control.id~='lock' and control.id~='parents' and control.action.kind~='breed')
end
assert(not M.apply(ctx,{kind='breed',a='g1',b='g3'}).ok,'stale breeding action accepted')
assert(not M.apply(ctx,{kind='lock',id='g3',stat='potency'}).ok,'stale trait lock action accepted')
assert(snapshot()==before,'collection action changed existing genes or locks')
s.section='parents';v=M.view(s,ctx);assert(v.section=='main' and not v.child,'stale parent screen remained live')
click('gene:g2');assert(click('starter').kind=='blocked')
-- Every stat in reward previews includes active slot modifiers and caps.
ctx.menu='reward';s=M.new();assert(C.apply_modifier(r,'player','assault',{id='cap',stat='potency',add=18}))
assert(C.reward(r,'r1','potency',1));assert(C.apply_modifier(r,'player','assault',{id='gain',stat='gain',add=-.6}))
before=snapshot();v=M.view(s,ctx)
local heavy=button(v,'reward2');assert(heavy.before.stats.potency==29 and heavy.after.stats.potency==30)
assert(math.abs(heavy.after.stats.gain-.15)<.00001)
assert(snapshot()==before)
result=M.apply(ctx,click('reward2'));assert(result.ok and result.reward_claimed)
ctx.run=result.run;r=ctx.run
local effective=C.resolve(r,'player','assault');for _,stat in ipairs(M.traits) do assert(effective[stat]==heavy.after.stats[stat]) end
assert(p.genes.g1.base.potency==10 and not p.genes.g1.upgrades.potency)
assert(not M.apply(ctx,{kind='reward',index=1,id='r1'}).ok,'duplicate reward accepted')
-- Unplaced acquisition is visible; occupied destinations reject without mutation.
ctx.node.id='arena_b';result=M.apply(ctx,{kind='reward',index=4});assert(result.ok and not r.genes[result.id]);ctx.run=result.run;r=ctx.run
ctx.menu='rest';s=M.new();click('gene:r2')
before=snapshot();assert(click('place:assault').kind=='blocked');assert(snapshot()==before)
click('gene:r1');v=M.view(s,ctx);local placement=button(v,'place:traversal')
assert(placement.preview.ability.action=='step' and placement.preview.ability.trigger=='move')
assert(placement.preview.stats.potency==15,'new placement retained old slot modifier')
result=M.apply(ctx,click('place:traversal'));assert(result.ok);ctx.run=result.run;r=ctx.run
assert(not r.hosts.player.slots.assault and r.hosts.player.slots.traversal=='r1')
assert(C.ability(r,'player','traversal').action=='step')
click('gene:r2');v=M.view(s,ctx);assert(v.selected.placed=='guard')
result=M.apply(ctx,click('unequip'));assert(result.ok and not r.hosts.player.slots.guard)
-- Enemy ownership is never available in selectable player genes or actionable mutations.
local enemy=assert(C.acquire(r,'cinder'));assert(C.equip(r,'enemy_arena','assault',enemy))
v=M.view(s,ctx);for _,id in ipairs(v.ids) do assert(id~=enemy) end
assert(not M.apply(ctx,{kind='place',id=enemy,slot='guard'}).ok)
assert(not M.apply(ctx,{kind='fuse',a='r1',b=enemy}).ok)
-- Fusion exact preview preserves source, consumes selected parents and reuses placement.
click('gene:r1');click('parents');click('gene:r3');before=snapshot();v=M.view(s,ctx)
assert(v.child and v.child.gene.parents[1]=='r1' and v.child.gene.parents[2]=='r3')
local expected=v.child;assert(snapshot()==before)
result=M.apply(ctx,click('confirm'));assert(result.ok);ctx.run=result.run;r=ctx.run
assert(not r.genes.r1 and not r.genes.r3 and r.genes[result.id])
for _,stat in ipairs(M.traits) do assert(C.resolve(r,'player','traversal')[stat]==expected.stats[stat]) end
assert(r.genes[result.id].base.potency==expected.gene.base.potency)
assert(r.genes[enemy] and r.hosts.enemy_arena.slots.assault==enemy)
-- Core remains available to tools; existing full collections still paginate.
ctx.menu='collection';s=M.new()
while p.next_id<=128 do assert(C.breed(p,'g1','g3')) end
-- Pagination exposes every individual through mouse and controller focus.
v=M.view(s,ctx);assert(v.pages==22)
click('next');assert(s.page==2);v=M.view(s,ctx);assert(button(v,'gene:g7'))
s.focus='previous';M.update(s,ctx,{right=true});assert(s.focus=='next');M.update(s,ctx,{confirm=true});assert(s.page==3)
-- Controller A returns the same action as mouse click, with no source mutation.
ctx.menu='rest';s=M.new();v=M.view(s,ctx);s.focus='continue'
a=M.update(s,ctx,{confirm=true});assert(a.kind=='continue')
assert(click('leave').kind=='leave')
-- Render each screen with bounds-checking engine stubs; all drawings fit 640x480.
local draws=0
local function bounds(x,y,w,h) assert(x>=0 and y>=0 and x+w<=640.01 and y+h<=480.01,'draw outside screen');draws=draws+1 end
local function kittext(x,y,txt,role,color,align,opts) assert(type(txt)=='string' and x>=0 and x<=640 and y>=0 and y<=480);assert(opts and opts.max_w and x+opts.max_w<=640);draws=draws+1 end
gd={fill=bounds,kit={panel=function(x,y,w,h) bounds(x,y,w,h) end,button=function(x,y,w,txt,selected,opts) bounds(x,y,w,opts.h) end,text=kittext,icon=function(name,x,y,scale) assert(name:match('^rogue_'));bounds(x,y,16*scale,16*scale) end}}
for _,menu in ipairs({'collection','rest','reward','error'}) do ctx.menu=menu;s=M.new();M.draw(s,ctx) end
ctx.menu='rest';s=M.new();click('gene:'..result.id);click('parents');click('gene:r2');M.draw(s,ctx)
local missing={menu='rest',profile=p};assert(M.view(M.new(),missing).error);M.draw(M.new(),missing)
assert(draws>150)
print('menu view/action/input/render invariants passed')
'''
        result = subprocess.run([lua, '-', str(SOURCE)], input=program, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('invariants passed', result.stdout)


if __name__ == '__main__':
    unittest.main()
