local base='melee/pc/scripts/examples/missions/scripts/'
local D={mission={RESPAWN_SLOT=4}}
local loads,unloads=0,0
D.world={load=function()loads=loads+1;return{}end,unload=function()unloads=unloads+1 end}
D.zones={reject=function()end}
D.chunks=assert(loadfile(base..'chunks.lua'))()(D)
local chunks={}
for i=1,9 do chunks[i]={id='c'..i,serial=i,rect={left=(i-1)*10,right=i*10,bottom=0,top=10},spawn={x=i*10-5,y=5},level={}}end
local g={stage_set_spawn=function()return true end,time=function()return 0 end,log=function()end}
local s=D.chunks.new(g,{chunks=chunks},'test');s.current=chunks[5]
s.loaded={c5={},c1={},c2={},c3={}}
local m={committed=chunks[5],frame=1}
assert(D.chunks.update(s,{x=49,y=5},m));assert(s.loaded.c6,'nearest missing chunk first')
assert(loads+unloads==1,'one mutation per frame')
D.chunks.update(s,{x=49,y=5},m);assert(loads+unloads==1,'duplicate calls share frame budget')
s.wave_frame=2;m.frame=2;D.chunks.update(s,{x=49,y=5},m);assert(loads+unloads==1,'wave spawn excludes streaming')
for i=3,8 do m.frame=i;local before=loads+unloads;D.chunks.update(s,{x=49,y=5},m);assert(loads+unloads-before<=1)end
assert(D.chunks.prefetch,'directional prefetch contract')
local ahead=D.chunks.new(g,{chunks=chunks},'ahead');ahead.current=chunks[5];ahead.loaded={c4={},c5={},c6={}};ahead.last_point={x=45,y=5}
D.chunks.update(ahead,{x=49,y=5},{committed=chunks[5],frame=10})
assert(ahead.loaded.c7 and ahead.current==chunks[5],'next window loads before room commitment')
local warm=assert(loadfile(base..'mission_warm.lua'))()(D)
local seen,removed={},{};local now=0
local wg={fill=function()end,time=function()return now end,log=function()end,spawn_enemy=function(k)seen[#seen+1]=k;return #seen end,enemy_remove=function(h)removed[h]=true end}
local t={doc={mission={enemies={{kind='goomba'},{kind='koopa'},{kind='goomba'}}},level={}},assets={},target={x=0,y=0},covered=true}
for i=1,80 do now=i;warm.draw(wg,t);if warm.tick(wg,t)then break end end
assert(#seen==2 and removed[1]and removed[2],'fallback cleans every kind')
local calls=0;wg.warm=function(d)assert(#d.enemies==2);calls=calls+1;return 9 end
wg.warm_done=function()return now>90 end;wg.warm_release=function(h)assert(h==9)end
local q={doc=t.doc,assets={},target=t.target,covered=true}
assert(not warm.tick(wg,q));now=91;assert(not warm.tick(wg,q));assert(warm.tick(wg,q));assert(calls==1)
-- Fallback must count rendered cover frames, not fast logic callbacks.
local stuck={doc=t.doc,assets={},target=t.target,covered=true}
for _=1,40 do warm.tick(wg,stuck)end -- native job remains pending at reset time
warm.cleanup(wg,stuck)
local a={doc=t.doc,assets={},target=t.target,covered=true}
wg.warm=nil
warm.tick(wg,a);for _=1,100 do assert(not warm.tick(wg,a))end
assert(a.warming.index==1,'no draw means no fallback completion')
warm.cleanup(wg,a);assert(not a.warming.enemy)
local live_items,live_models=0,0
wg.item_spawn=function()live_items=live_items+1;return 50 end
wg.item_remove=function()live_items=live_items-1 end
wg.model_spawn=function()live_models=live_models+1;return 60 end
wg.model_despawn=function()live_models=live_models-1 end
local all={doc={mission=t.doc.mission,maze={cells={{enemy_kinds={'topi'}}}},level={},chunks={{level={warm_items={'drive'}}}}},assets={mesh=31},asset_paths={'mesh'},target=t.target,covered=true}
for i=1,160 do warm.draw(wg,all);if warm.tick(wg,all)then break end end
assert(all.warming.done and live_items==0 and live_models==0,'items and all models warmed and removed')
-- Guarded prepare/activate and failed activation retire partial construction.
local world=assert(loadfile(base..'world.lua'))()(D);local n=0
local pg={model_load=function()return 1 end,model_spawn=function()return 2 end,
 area_prepare=function(name,builder)builder();n=n+1;return 11 end,
 area_activate=function(h)assert(h==11);return true end,
 area_unload=function()n=n-1 end,model_release=function()end}
local ar=world.load(pg,'prepared',{parts={},lines={}});assert(ar.prepared==11 and n==1)
pg.area_activate=function()return false end
assert(not pcall(world.load,pg,'failed',{parts={},lines={}}));assert(n==1)
-- Every fallback type and native job is reclaimed by abandonment.
local ins=assert(loadfile(base..'install.lua'))()(D)
for _,kind in ipairs({'enemy','item','model','handle'})do
 local cleaned=false;local cg={}
 cg.enemy_remove=function()cleaned=true end;cg.item_remove=cg.enemy_remove
 cg.model_despawn=cg.enemy_remove;cg.warm_release=cg.enemy_remove
 local warming={[kind]=123};D.mission_warm=warm
 local r={g=cg,staging={warming=warming,c={},built={},assets={}}}
 ins.abandon(r);assert(cleaned and not r.staging,'abandon '..kind)
end
print('fix3 streaming/warm/area/abandon contracts PASS')
