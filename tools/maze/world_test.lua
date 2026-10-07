local base=(os.getenv('GW_MELEE') or 'melee')..'/pc/scripts/examples/missions/scripts/'
local D={}
for _,n in ipairs({'mission','validator','maze_set','maze_clearance','maze_metrics','maze_topology','maze_check','maze_world_check','maze_route','maze_encounters','maze','maze_world','loader','world','zones','chunks','glue','fighters','camera','maze_commands','maze_rewards','world_commands','commands','mission_finish','hud','install','runtime'})do
 local f=loadfile(base..n..'.lua');if f then D[n]=n=='mission'and f()or f()(D)end
end
assert(D.maze_world,'world generator missing')
local w=D.maze_world.generate(7,{regions=4,size=8})
assert(D.maze_world_check.check(w).ok)
assert(D.maze.encode(w)==D.maze.encode(D.maze_world.generate(7,{regions=4,size=8})))
assert(#w.world.links>=4 and w.world.goal=='r4')
local changed=D.maze_world.generate(7,{regions=4,size=8,seeds={r2=99}})
for i,r in ipairs(w.world.regions)do if i~=2 then
 assert(r.seed==changed.world.regions[i].seed and r.map==changed.world.regions[i].map,'unrelated region rerolled')
 for j,id in ipairs(r.chunks)do local c=w.cells[tonumber(id:sub(2))];local z=changed.cells[tonumber(changed.world.regions[i].chunks[j]:sub(2))]
 assert(c.x==z.x and c.y==z.y and c.template==z.template,'unrelated region moved')end
end end
local files=D.maze.files(w,'world_test');local root=assert(load(files['missions/world_test/level.lua'],'root','t',{}))()
local regions=0;for _,z in ipairs(root.zones)do if z.kind=='region'then regions=regions+1 end end;assert(regions==4)
local g={mod_read=function(p)return files[p]end,mod_stamp=function(p)return files[p]and 1 end,
 mod_list=function()local out={};for _,p in ipairs({'bf_floor_4m','bf_wall_solid_4m','bf_wall_doorway_4m','bf_beam_4m','bf_door_leaf'})do out[#out+1]={name=p..'.gxmesh'}end;return out end}
local doc=D.loader.folder(g,'world_test');assert(#doc.chunks==#w.cells)
local c={doc=doc,stream=D.chunks.new(g,doc,'test_')};g.log=function()end
local region=D.zones.sample(g,c,doc.mission.start,0);assert(region.region=='r1')
assert(D.maze_world.ascii(w):find('r4',1,true)and D.maze_world.ascii(w):find('connectors',1,true))
for _,options in ipairs({{regions=1},{regions=7},{size=21}})do assert(not pcall(D.maze_world.generate,7,options),'world limit ignored')end
local bad=assert(load('return '..D.maze.encode(w),'bad','t',{}))();local link=bad.world.links[1]
for _,cell in ipairs(bad.cells)do for _,e in ipairs(cell.exits)do if e.to==link.from then e.to=nil;e.sealed=true end end end
assert(not D.maze_world_check.check(bad).ok,'broken connector accepted')
local trapped=D.maze_world.generate(1,{regions=3,size=12})
trapped.cells[12].exits[3].traversal='drop'
assert(not D.maze_world_check.check(trapped).ok,'one-way interior trap accepted')
D.zones.describe({log=function()end},{doc=doc,stream=c.stream,membership=region})
local library=assert(load(D.maze.starters()['missions/maze-chunks/library.lua'],'library','t',{}))()
for _,t in ipairs(library)do
  t.level.parts[#t.level.parts+1]={name='authored_marker',part='bf_floor_4m',x=40,y=0,z=3,rot=0,collision=false,floor_flags=0}
  t.level.lines[#t.level.lines+1]={kind='floor',x1=10,x2=42,y1=18,y2=18,passthrough=true,label='authored_platform'}
  t.level.camera={mode='chunk',margin=8}
end
local authored=D.maze_world.generate(7,{regions=3,size=8,templates=library});local count=0
for _,cell in ipairs(authored.cells)do if cell.region then
  local marker,platform=false,false
  for _,part in ipairs(cell.level.parts)do if part.name:find('authored_marker',1,true)then marker=true end end
  for _,line in ipairs(cell.level.lines)do if line.label=='authored_platform'then platform=true end end
  assert(marker and platform and cell.level.camera.margin==8,'authored regional geometry discarded');count=count+1
end end;assert(count==24)
for seed=1,25 do local q=D.maze_world.generate(seed,{regions=3+seed%3,size=8+seed%5});assert(D.maze_world_check.check(q).ok)end
local installs,ticks,peak=0,0,0
local runtime_g={match=function()return{active=true,netplay=false}end,player=function()return{action=14}end,
  log=function()end,mod_read=function()return nil end,mod_stamp=function()return nil end,mod_list=g.mod_list}
local r={g=runtime_g,install=function(self,name)
  installs=installs+1;self.current={doc=D.loader.folder(runtime_g,name),stream={}}
end}
D.world_commands.dispatch(r,{'world','7','3','8'})
assert(r.world_generation and installs==0,'world command blocked or installed before preparation')
while r.world_generation do
  local instructions=0;local co=r.world_generation.co;debug.sethook(co,function()instructions=instructions+1000 end,'',1000)
  D.world_commands.tick(r);debug.sethook(co);peak=math.max(peak,instructions);ticks=ticks+1
  assert(ticks<3000,'world preparation never ends')
end
assert(installs==1 and r.world and #r.world.output.cells>24,'continuous world was not installed exactly once')
assert(peak<500000,'unbounded world callback instructions '..peak)
D.world_commands.dispatch(r,{'world','7','5','20'})
local maxpeak,maxsteps=0,0
while r.world_generation do
 local co=r.world_generation.co;local instructions=0;debug.sethook(co,function()instructions=instructions+1000 end,'',1000)
 D.world_commands.tick(r);debug.sethook(co);if instructions>500000 then print('budget phase '..tostring(r.world_generation and r.world_generation.phase)..' instructions='..instructions)end;maxpeak=math.max(maxpeak,instructions);maxsteps=maxsteps+1;assert(maxsteps<5000)
end
assert(r.world and r.world.seed==7 and #r.world.output.cells>256,'large world failed')
assert(maxpeak<500000,'maximum world callback unbounded '..maxpeak)
print('large world: '..#r.world.output.cells..' chunks, '..maxsteps..' callbacks, peak '..maxpeak..' instructions')
D.world_commands.dispatch(r,{'world','8','3','8'});local folder=r.world_generation.folder
D.world_commands.cancel(r);assert(not r.world_generation and not D.loader.generated[folder])
print('world callback budget: '..ticks..' callbacks; peak '..peak..' Lua instructions (native IO/parser time needs game verification)')
print('world contracts PASS: determinism, independent reroll, regions/loops/connectors, zones, limits, no soft locks,25 seeds')
