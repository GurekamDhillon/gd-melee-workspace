local base=(os.getenv('GW_MELEE') or 'melee')..'/pc/scripts/examples/missions/scripts/'
local D={}
for _,n in ipairs({'mission','validator','maze_set','maze_clearance','maze_metrics','maze_topology','maze_check','maze_encounters','maze','loader','world','zones','chunks','glue','fighters','camera','maze_commands','maze_rewards','commands','install','runtime'})do
  local f=assert(loadfile(base..n..'.lua'));D[n]=n=='mission' and f() or f()(D)
end
local failures=0
local function test(name,fn)local ok,why=pcall(fn);print((ok and 'PASS 'or 'FAIL ')..name..(ok and ''or ': '..tostring(why)));if not ok then failures=failures+1 end end
local function data(text)return assert(load(text,'fixture','t',{}))()end
local function model(m)
  local files=D.maze.files(m,'test');local g={mod_read=function(p)return files[p]end,mod_stamp=function(p)return files[p]and 1 end,
    mod_list=function(p) assert(p:sub(1,9)=='missions/' and not p:find('..',1,true)and not p:find('\\',1,true)and not p:find(':',1,true),'engine path '..p)
      local out={};for _,name in ipairs({'bf_floor_4m','bf_wall_solid_4m','bf_wall_doorway_4m','bf_beam_4m','bf_door_leaf'})do out[#out+1]={name=name..'.gxmesh'}end;return out end}
  return D.loader.folder(g,'test'),files,g
end
test('runtime catalogue uses engine missions prefix',function()
  local m=D.maze.generate(7);local doc,files,g=model(m)
  g.log=function()end;g.mod_read=function(p)assert(p:sub(1,9)=='missions/');return nil end;g.mod_stamp=function(p)assert(p:sub(1,9)=='missions/');return nil end
  local r={g=g,install=function()end};D.maze_commands.dispatch(r,{'maze','7'})
end)
test('runtime reads authored recipe library through engine-safe paths',function()
  local library=D.maze.starters()['missions/maze-chunks/library.lua'];local templates=data(library)
  for _,t in ipairs(templates)do t.spawn={x=33,y=8}end
  local function path(p)assert(p:sub(1,9)=='missions/' and not p:find('..',1,true)and not p:find('\\',1,true)and not p:find(':',1,true))end
  local g={mod_read=function(p)path(p);if p=='missions/maze-chunks/library.lua'then return 'return '..D.maze.encode(templates)end end,
    mod_stamp=function(p)path(p);if p=='missions/maze-chunks/library.lua'then return 1 end end,
    mod_list=function(p)path(p);local out={};for _,n in ipairs({'bf_floor_4m','bf_wall_solid_4m','bf_wall_doorway_4m','bf_beam_4m','bf_door_leaf'})do out[#out+1]={name=n..'.gxmesh'}end;return out end,log=function()end}
  local r={g=g,install=function()end};D.maze_commands.dispatch(r,{'maze','7'})
  assert(r.maze.output.cells[1].spawn.x==33,'authored recipes silently ignored')
end)
test('same-folder asynchronous refusal restores previous generated overlay',function()
  local name='missions/maze_7_12/';local previous={files={},stamp=5};D.loader.generated[name]=previous
  local old={seed=7,size=12,folder=name};local r={maze=old,current={doc={folder=name}},last_install_error='refused',
    maze_pending={next={folder=name},previous=previous},g={log=function()error('false success')end}}
  D.loader.generated[name]={files={},stamp=6};D.maze_commands.settle(r)
  assert(D.loader.generated[name]==previous and r.maze==old and not r.maze_pending)
end)
test('room zones and unique physical transitions are emitted',function()
  local m=D.maze.generate(99,{size=20});local root=data(D.maze.files(m,'test')['missions/test/level.lua'])
  local rooms,doors=0,0
  for _,z in ipairs(root.zones or {})do if z.kind=='room'then rooms=rooms+1 else doors=doors+1;assert(#z.rooms==2)end end
  local edges=0;for _,c in ipairs(m.cells)do for _,e in ipairs(c.exits)do if e.to then edges=edges+1 end end end
  assert(rooms==20 and doors==edges/2)
end)
test('horizontal walk across open down hole explicitly requires a hop',function()
  local m=D.maze.generate(99,{size=20});local report=D.maze_check.check(m);assert(report.ok and report.costs)
  local seen=false
  for _,c in ipairs(m.cells)do if c.exits[4].to then
    for _,l in ipairs(c.level.lines)do assert(l.label~='walk_bridge')end
    for _,e in ipairs(c.exits)do if e.to and(e.side=='left'or e.side=='right')then seen=true;assert(report.costs[c.id][e.to]==2 and report.actions[c.id][e.to]=='hop')end end
  end end;assert(seen)
end)
test('reward no-return setter is consumed once and never manufactures damage',function()
  local m=D.maze.generate(1,{size=8});local reward;for _,c in ipairs(m.cells)do if c.reward then reward=c;break end end;assert(reward)
  local percent,calls=80,0
  local g={player=function()return{x=reward.x*130+20,y=reward.y*104+8,percent=percent,action=14}end,
    set_damage=function(_,n) calls=calls+1;percent=n end,log=function()end}
  local c={doc={maze=m}};D.maze_rewards.tick(g,c);D.maze_rewards.tick(g,c)
  assert(calls==1 and percent==55)
  percent=0;local fresh={doc={maze=m}};D.maze_rewards.tick(g,fresh);assert(percent==0)
end)
test('spatial encounters never spawn at start or through a transition',function()
  local m=D.maze.generate(7,{size=20});local doc=model(m)
  local c={doc=doc,run=D.glue.new(doc),stream={loaded={},current=doc.chunks[1]}}
  c.membership={point=doc.mission.start,committed=doc.chunks[1],room=doc.chunks[1]}
  local spawns=0;local g={player=function()return c.membership.point end,log=function()end,
    stage_set_spawn=function()return true end,spawn_enemy=function()spawns=spawns+1;return spawns end}
  c.stream.g=g;D.glue.step(g,c);assert(spawns==0 and c.run.state.nbegun==0,'enemy wave started before its room')
  local target;for _,cell in ipairs(m.cells)do if cell.enemy_budget>0 then target=doc.zone_data.chunks[cell.id];break end end
  c.membership={point=target.spawn,committed=target,room=target,transition={name='door'}}
  c.stream.loaded[target.id]={};D.glue.step(g,c);assert(spawns==0)
  c.membership.transition=nil;c.stream.current=target;D.glue.step(g,c);assert(spawns>0)
end)
test('shared waves defer room spawns at global live enemy cap',function()
  local tracked={};for i=1,32 do tracked[i]=true end
  local run={state={tracked=tracked,m={enemies={{},{},{}}}},encounter_room={rect={left=0,right=130,bottom=0,top=104}}}
  local c={doc={maze={}},run=run};local actions={}
  for i=1,3 do actions[i]={type='spawn',index=i,x=20,y=8}end
  assert(#D.maze_encounters.actions(c,actions)==0)
  tracked[1]=nil;tracked[2]=nil
  assert(#D.maze_encounters.actions(c,{})==2 and run.encounter_pending[3])
end)
test('queued flight retries transient refusal without losing target',function()
  local calls=0;local target={name='far',x=280,y=8}
  local c={doc={chunks={}},stream={pending=false},pending_visit=target}
  local g={player=function()return{x=20,y=8}end,log=function()end,
    fly_target=function()calls=calls+1;if calls==1 then error('dead fighter')end;return true end}
  local preload=D.chunks.preload;D.chunks.preload=function()return true end
  local r={current=c,g=g};local ok,why=pcall(function()
    D.commands.tick(r);assert(c.pending_visit==target)
    D.commands.tick(r);assert(not c.pending_visit and calls==2)
  end)
  D.chunks.preload=preload;assert(ok,why)
end)
test('one queued chunk build per tick and committed spawn remains stable',function()
  local chunks={};for i=1,4 do chunks[i]={id='c'..i,serial=i,rect={left=(i-1)*130,right=i*130,bottom=0,top=104},spawn={x=(i-1)*130+20,y=8},level={parts={},lines={}}}end
  local builds=0;local g={time=function()return 0 end,log=function()end,stage_set_spawn=function()return true end,
    area_load=function(_,fn) builds=builds+1;fn();return true end,area_unload=function()return true end}
  local s=D.chunks.new(g,{chunks=chunks},'queue_');s.current=chunks[1];s.loaded.c1={name='old',replacements={},assets={}}
  local membership={committed=chunks[3],changed=true,prior={committed=chunks[1]}}
  s.zone_state={committed=chunks[3]}
  D.chunks.update(s,{x=280,y=8},membership)
  assert(builds<=1 and s.loaded[s.current.id],'multi-build or respawn without collision')
  for frame=1,10 do local before=builds;membership={frame=frame,committed=chunks[3],changed=true,prior={committed=s.current}};s.zone_state.committed=chunks[3];D.chunks.update(s,{x=280,y=8},membership);D.chunks.update(s,{x=280,y=8},membership);assert(builds-before<=1)end
  assert(s.current==chunks[3])
end)
test('terminal state logs completion even after interrupted action dispatch',function()
  local mission=D.mission.validate({start={x=0,y=8},goal={x=10,y=8,w=24,h=32},objective={type='reach_goal'}})
  local c={doc={mission=mission,level={}},run=nil,stream={}};c.run=D.glue.new(c.doc)
  c.run.state.result={status='complete'}
  local logs={};local g={player=function()return{x=10,y=8,falls=0}end,log=function(s)logs[#logs+1]=s end}
  D.glue.step(g,c);D.glue.step(g,c);local n=0;for _,s in ipairs(logs)do if s=='mission: complete'then n=n+1 end end
  assert(n==1)
end)
test('neighbouring rewards cannot damage or claim at start',function()
  for _,seed in ipairs({1,7,99,123})do local m=D.maze.generate(seed,{size=12});local writes=0
    local g={player=function()return{x=20,y=8,percent=0,action=14}end,set_damage=function()writes=writes+1 end,log=function()end}
    local c={doc={maze=m}};for _=1,300 do D.maze_rewards.tick(g,c)end
    assert(writes==0 and not next(c.maze_rewards or {}),'reward touched start')
  end
end)
test('spatial wave regions are connected and capped',function()
  for seed=1,100 do local m=D.maze.generate(seed,{size=20});local owner,n=D.maze_encounters.plan(m);assert(n<=8)
    local groups={};for _,c in ipairs(m.cells)do local w=owner[c.id];if w then groups[w]=groups[w]or {};groups[w][c.id]=c end end
    for _,cells in pairs(groups)do local id=next(cells);local q={id};local seen={[id]=true};local count=0
      for _,c in pairs(cells)do count=count+c.enemy_budget end;assert(count<=32)
      local i=1;while q[i]do for _,e in ipairs(cells[q[i]].exits)do if cells[e.to]and not seen[e.to]then seen[e.to]=true;q[#q+1]=e.to end end;i=i+1 end
      for key in pairs(cells)do assert(seen[key],'disconnected wave region')end
    end
  end
end)
test('main paths include west and kit goal is visible geometry',function()
  local west=false
  for seed=1,40 do local m=D.maze.generate(seed,{size=12});for i=2,#m.main_path do local a=m.cells[i-1];local b=m.cells[i];if b.x<a.x then west=true end end
    local goal=m.cells[tonumber(m.goal:sub(2))];local marker=false;for _,p in ipairs(goal.level.parts)do if p.name:find('goal',1,true)then marker=true end end;assert(marker,'no visible goal')
  end;assert(west,'east-only path')
end)
assert(failures==0,failures..' fix1 contract failures')
