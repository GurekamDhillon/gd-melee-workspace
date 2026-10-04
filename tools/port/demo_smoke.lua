-- lua tools/port/demo_smoke.lua <mod-folder> [scenario]
local folder,scenario=assert(arg[1]),arg[2] or 'basic'
local g,S=dofile('tools/port/demo_gd_stub.lua'); S.folder=folder
if scenario=='staged' or scenario=='staging-failure' or scenario=='staging-cancel' then S.area_budget=true end
if scenario=='fly-refusal' then S.fly_unsafe=true end
if scenario=='staging-failure' then S.area_failure=true end
S.models=scenario=='models'
local env={gd=g,assert=assert,error=error,ipairs=ipairs,pairs=pairs,next=next,pcall=pcall,
  select=select,tonumber=tonumber,tostring=tostring,type=type,load=load,
  math=math,string=string,table=table,utf8=utf8,coroutine=coroutine}
-- No io/os/require/_G in the mod environment, matching the engine sandbox.
local function hook(name,...)
  if env[name] then return env[name](...) end
end
local function frame()
  g.advance()
  if S.saved_event then local slot=S.saved_event; S.saved_event=nil; hook('on_savestate',slot) end
  if S.loaded_event then local slot=S.loaded_event; S.loaded_event=nil; hook('on_loadstate',slot) end
  hook('on_frame_pre'); hook('on_frame'); hook('on_draw')
end
assert(loadfile(folder..'/scripts/main.lua','t',env))()
if scenario=='bench-refusal' or scenario=='old-match-refusal' then S.refuse_bench=true end
if scenario=='old-match-refusal' then S.frame=1000 end
if scenario=='best-read-refusal' then S.read_error=true; S.files['best.txt']='1' end
hook('on_scene',1,'GS_TRAINING',0)
-- Catch-up load: deliberately omit on_match_start to validate initialization.
frame()
if folder:find('gauntlet',1,true) and scenario~='staged' and scenario~='staging-cancel' and not S.refuse_bench then for _=1,20 do frame() end end
if scenario=='staged' then
  assert(next(S.resources)==nil,'setup should stage in a task')
  for _=1,20 do frame() end
  assert(S.hidden and S.players[2].benched,'staged setup did not complete')
  assert(S.bench_calls==1 and S.camera_claim,'setup reentered or camera vanished with task')
  for _,r in pairs(S.resources) do assert(r.kind~='slot','boss slot preloaded during setup') end
elseif scenario=='fly-refusal' then
  S.keys.T=true; hook('on_tick')
  assert(not S.flying,'unsafe fly unexpectedly started')
elseif scenario=='staging-failure' then
  assert(not S.players[2].benched and next(S.resources)==nil,'failed setup left a bench/partial area')
elseif scenario=='staging-cancel' then
  frame(); assert(next(S.resources),'cancel test did not reach a partial build')
  hook('on_unload')
  for _=1,20 do g.advance() end
  assert(not S.players[2].benched and next(S.resources)==nil,'cancelled task resumed construction')
elseif scenario=='tour-cover' then
  S.live_cover=true; hook('on_stage_switch',{phase='before',slot=S.switch})
  hook('on_stage_switch',{phase='after',slot=S.switch})
  S.live_cover=false; frame()
end
if scenario=='bench-refusal' or scenario=='old-match-refusal' then
  assert(next(S.resources)==nil,'refused bench built geometry')
  S.refuse_bench=false; for _=1,6 do frame() end
  for _=1,20 do frame() end
  assert(S.players[2].benched,'bench retry did not acquire boss')
end
if scenario=='gauntlet' or scenario=='retry-refusal' or scenario=='best-read-refusal' then
  assert(S.players[2].benched and S.hidden,'mission did not reserve/hide')
  for wave=1,2 do
    local victims={}
    for h,r in pairs(S.resources) do if r.kind=='enemy' then victims[#victims+1]=h end end
    assert(#victims==(wave==1 and 2 or 1),'wrong wave count')
    for _,h in ipairs(victims) do local kind=S.resources[h].value.kind; S.resources[h]=nil; hook('on_enemy_defeated',{handle=h,kind=kind}) end
    frame()
  end
  local item
  for h,r in pairs(S.resources) do if r.kind=='item' then item=h; break end end
  assert(item,'no defeat drop')
  local event={item=item,name='gauntlet_drive',port=1,payload={amount=1}}
  hook('on_item_collect',event); local damage=S.mods[1].damage_dealt
  hook('on_item_collect',event); assert(S.mods[1].damage_dealt==damage,'duplicate reward')
  -- Rebuild exactly the same seed to find the destination, using the supplied pure module.
  local set=dofile(folder..'/missions/gauntlet/maze_set.lua')()
  local m=dofile(folder..'/missions/gauntlet/maze.lua')({maze_set=set}).generate(42,{size=8,length=4})
  for _,c in ipairs(m.cells) do if c.id==m.goal then g.teleport(1,c.x*130+320,c.y*104+8) end end
  frame(); assert(S.switch,'maze goal did not request boss transition')
  hook('on_stage_switch',{phase='after',slot=S.switch})
  assert(not S.players[2].benched and S.players[2].percent==0,'fresh boss not called')
  S.players[2].falls=1; frame(); assert(tonumber(S.files['best.txt']),'victory did not save best')
  if scenario=='best-read-refusal' then assert(S.files['best.txt']=='1','unreadable prior best was overwritten') end
  if scenario=='retry-refusal' then
    hook('on_match_end'); S.frame=0; S.refuse_bench=true
    frame(); S.refuse_bench=false; for _=1,26 do frame() end
    assert(S.players[2].benched and next(S.resources),'retry stuck after transient reserve refusal')
  end
elseif scenario=='pickup-juice' then
  S.keys.I=true;hook('on_tick');frame()
  local plain
  for h,r in pairs(S.resources) do if r.kind=='item' then plain=h end;assert(r.kind~='fx','plain pickup created effects') end
  assert(plain,'plain spawn absent')
  S.keys.R=true;hook('on_tick');frame();assert(next(S.resources)==nil,'plain clear leaked')
  S.keys.J=true;hook('on_tick');frame()
  local item,fx=nil,0
  for h,r in pairs(S.resources) do if r.kind=='item' then item=h elseif r.kind=='fx' then fx=fx+1 end end
  assert(item and fx==5,'juiced spawn missing bounded effects')
  S.resources[item]=nil
  hook('on_item_collect',{item=item,name='demo_juice',port=1,payload={colour='blue',amount=1}})
  for _=1,25 do frame() end
  assert(next(S.resources)==nil,'collect left effects')
  S.keys.J=true;hook('on_tick');frame()
  for h,r in pairs(S.resources) do if r.kind=='item' then item=h end end
  S.resources[item]=nil;hook('on_item_expire',{item=item,name='demo_juice'})
  assert(next(S.resources)==nil,'expiry left effects')
  assert(S.sounds and #S.sounds==3,'drop/collect sound lifecycle incorrect')
elseif scenario=='drill' or scenario=='drill-timeout' then
  S.keys.D=true; hook('on_tick')
  if scenario=='drill' then
    for h,r in pairs(S.resources) do if r.kind=='line' then S.floor=h; break end end
    frame()
  else for _=1,181 do frame() end end
  local w=select(2,next(S.waits)); assert(w and w.done,'watcher did not resolve')
  assert(w.ok==(scenario=='drill'),'wrong drill result')
elseif scenario=='safe-moves' then
  S.keys.M=true; hook('on_tick'); assert(S.players[1].action==44,'selected a death/entry state')
elseif scenario=='snapshot-proof' then
  S.keys.S=true; hook('on_tick'); frame()
  assert(S.players[1].percent==25,'snapshot did not perturb damage for proof')
  S.keys.L=true; hook('on_tick'); frame()
  assert(S.players[1].percent==0 and S.logs[#S.logs]:find('PROVED',1,true),'snapshot restore not proved')
elseif scenario=='recycle-visible' or scenario=='recycle-hidden' then
  S.players[6].action=13; S.players[6].hidden=true; S.recycle_hidden=scenario=='recycle-hidden'
  S.keys.R=true; hook('on_tick'); for _=1,3 do frame() end
  assert(S.logs[#S.logs]:find(S.recycle_hidden and 'FAIL' or 'PROVED',1,true),'recycle visibility not checked')
elseif scenario=='tour' then
  assert(S.switch,'initial switch absent'); hook('on_stage_switch',{phase='after',slot=S.switch}); frame()
  assert(S.queue and #S.queue==3,'tour queue not armed after event')
elseif scenario=='save-refusal' then
  S.files['counter.txt']='4'; S.keys.R=true; hook('on_tick')
  S.write_error=true; S.keys.S=true; hook('on_tick'); assert(S.files['counter.txt']=='4','failed write changed saved counter')
end
-- Exercise focused demo hotkeys after load. Gauntlet/tour use dedicated scenario tests.
if scenario=='basic' or scenario=='models' then
  for _,key in ipairs{'Q','I','R','T','P','C','M','B','F','G','W','O','S','E','H','U','J','SPACE','K','N','A','V','RIGHT','LEFT'} do
    S.keys[key]=true; hook('on_tick'); frame()
  end
end
hook('on_unload')
assert(not S.pad_claim,'pad claim survived explicit unload')
assert(S.trace~=true,'trace survived explicit unload')
assert(S.tints==0,'part tint survived explicit unload')
print('PASS '..folder..' '..scenario)
