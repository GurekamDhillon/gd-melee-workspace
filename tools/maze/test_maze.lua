local base='melee/pc/scripts/examples/missions/scripts/'
local D={}
for _,n in ipairs({'mission','validator','maze_set','maze_clearance','maze_metrics','maze_topology','maze_check','maze_encounters','maze','loader','glue','fighters','maze_commands','maze_rewards','commands','runtime'}) do
  local f=assert(loadfile(base..n..'.lua'))
  D[n]=n=='mission' and f() or f()(D)
end
local function clone(t) return assert(load('return '..D.maze.encode(t),'copy','t',{}))() end
local function rejected(m,word)
  local report=D.maze_check.check(m)
  assert(not report.ok and table.concat(report.errors,' '):find(word,1,true),word)
end
local a=D.maze.generate(7,{size=12})
local loop_seen,vertical_seen,reward_seen=false,false,false
assert(D.maze.encode(a)==D.maze.encode(D.maze.generate(7,{size=12})))
assert(D.maze.encode(a)~=D.maze.encode(D.maze.generate(8,{size=12})))
local calls=0
D.maze.generate(7,{size=8},function(n) calls=calls+1;return 1 end)
assert(calls>0,'injected RNG unused')
assert(not pcall(D.maze.generate,1,{size=8},function() return 0 end))
for _,size in ipairs({7,21,8.5}) do assert(not pcall(D.maze.generate,1,{size=size})) end
assert(not pcall(D.maze.generate,0/0,{size=8}))
for seed=1,1000 do
  local size=8+seed%13
  local m=D.maze.generate(seed,{size=size})
  local report=D.maze_check.check(m)
  assert(report.ok,table.concat(report.errors,';'))
  assert(#m.cells==size and #m.main_path==math.max(4,math.ceil(size*.55)))
  assert(report.distance[m.goal]>=1,'goal route missing')
  assert(D.maze.ascii(m):find('S',1,true) and D.maze.ascii(m):find('G',1,true))
  local files=D.maze.files(m,'maze_test')
  local g={mod_read=function(p)return files[p],'missing' end,
    mod_stamp=function(p)return files[p] and 1 end,
    mod_list=function(p) if p:match('/models/$') then
      local out={};for _,n in ipairs({'bf_floor_4m','bf_wall_solid_4m','bf_wall_doorway_4m','bf_beam_4m','bf_door_leaf'})do out[#out+1]={name=n..'.gxmesh',dir=false}end;return out end return {} end}
  local doc=D.loader.folder(g,'maze_test')
  assert(#doc.chunks==size and not D.mission.check_playable(doc.mission))
  assert(D.maze_check.folder(g,'maze_test').ok,'emitted folder proof')
  local count=0
  for _,c in ipairs(m.cells) do
    if c.reward then reward_seen=true end
    for _,e in ipairs(c.exits) do if e.to and (e.side=='up' or e.side=='down') then vertical_seen=true end end
    assert(c.enemy_budget==math.min(3,math.floor(report.distance[c.id]/3)))
    assert(c.difficulty==1+report.distance[c.id]/math.max(1,report.distance[m.goal]))
    count=count+c.enemy_budget
  end
  assert(#doc.mission.enemies==count and count<=64)
  local edges=0;for _,c in ipairs(m.cells) do for _,e in ipairs(c.exits) do if e.to then edges=edges+1 end end end
  if edges/2>#m.cells-1 then loop_seen=true end
end
assert(loop_seen and vertical_seen and reward_seen,'varied topology coverage')
local tree=D.maze.generate(7,{size=20,length=10,loops=false})
local edges=0;for _,c in ipairs(tree.cells) do for _,e in ipairs(c.exits) do if e.to then edges=edges+1 end end end
assert(#tree.main_path==10 and edges/2==19,'length and loop targets')
local up=D.maze.generate(1,{size=8,length=8,loops=false},function(n)return math.min(3,n)end)
up.cells[1].exits[3].traversal='drop';rejected(up,'unreachable')
local bad=clone(a);bad.cells[2].x=bad.cells[1].x;bad.cells[2].y=bad.cells[1].y
rejected(bad,'overlap')
bad=clone(a);bad.goal='absent';rejected(bad,'goal')
bad=clone(a)
local changed=false
for _,c in ipairs(bad.cells) do for _,e in ipairs(c.exits) do
  if e.sealed then e.sealed=false;changed=true;break end
end if changed then break end end
rejected(bad,'unsealed')
bad=clone(a)
for _,c in ipairs(bad.cells) do for _,e in ipairs(c.exits) do
  if e.to and e.side=='up' then c.platforms={};changed=true end
end end
rejected(bad,'climb')
bad=clone(a);bad.cells[2].exits[1].slot=99;rejected(bad,'slot')
bad=clone(a);bad.cells[1].level.lines={};rejected(bad,'seal')
bad=clone(a)
for _,e in ipairs(bad.cells[1].exits) do e.to=nil;e.sealed=true end
rejected(bad,'unreachable')
local prototypes=D.maze.starters()
local templates=assert(load(prototypes['missions/maze-chunks/library.lua'],'library','t',{}))()
local one_way=clone(templates)
for _,t in ipairs(one_way) do for _,e in ipairs(t.level.exits) do if e.side=='up' then e.traversal='drop' end end end
local descending=D.maze.generate(1,{size=8,length=8,templates=one_way},function(n)return math.min(3,n) end)
for i=2,#descending.cells do if descending.cells[i].exits[3].to then assert(descending.cells[i].exits[3].traversal=='drop','authored receiving exit strengthened')end end
assert(D.maze_check.check(descending).ok,'one-way descent remains reachable')
local custom=D.maze.generate(7,{size=12,templates=templates})
assert(D.maze_check.check(custom).ok,'authored starter library')
local source=clone(templates)
local varied=D.maze.generate(7,{size=12,templates=templates})
assert(D.maze.encode(source)==D.maze.encode(templates),'author data mutated')
local files=D.maze.files(a,'maze_test')
local child='missions/maze_test/chunks/c1/level.lua'
local value=assert(load(files[child],'child','t',{}))();value.lines={}
files[child]='return '..D.maze.encode(value)
assert(not D.maze_check.folder({mod_read=function(p)return files[p] end},'maze_test').ok,
  'checker must inspect actual child file, not root certificate')
assert(not pcall(D.loader.folder,{mod_read=function(p)return files[p] end,
  mod_stamp=function(p)return files[p] and 1 end},'maze_test'),'loader refuses broken maze before model/world calls')
local logs={};local ready=true
local g={command=function()end,player=function()return {action=ready and 14 or 0} end,
  log=function(s)logs[#logs+1]=s end,mod_read=function()return nil,'missing' end,
  mod_stamp=function()return nil end,mod_list=function()local out={};for _,n in ipairs({'bf_floor_4m','bf_wall_solid_4m','bf_wall_doorway_4m','bf_beam_4m','bf_door_leaf'})do out[#out+1]={name=n..'.gxmesh',dir=false}end;return out end,
  time=function()return 0 end}
local r=D.runtime.new(g)
local installs=0
function r:install(name)
  if self.reject then error('install capacity refused') end
  local doc=D.loader.folder(g,name)
  installs=installs+1;self.current={doc=doc,run=D.glue.new(doc)}
end
assert(r:command('maze 7 12'));assert(r.maze.seed==7 and #r.current.doc.chunks==12)
assert(r:command('maze map'));D.commands.tour(r)
assert(#r.current.tour.queue>=12,'tour includes every generated chunk')
assert(r:command('maze reroll'));assert(r.maze.seed==8)
r.reject=true;local old=r.maze
assert(not r:command('maze reroll'));assert(r.maze==old,'failed install advanced reroll')
r.reject=false;ready=false
assert(r:command('maze reroll'));assert(r.pending and r.maze.seed==8)
ready=true;for _=1,6 do r:retry() end
assert(not r.pending and r.maze.seed==9 and installs==3,'readiness reroll exactly once')
local reward
for _,c in ipairs(a.cells) do if c.reward then reward=c;break end end
assert(reward)
local claims,percent=0,80
local reward_g={player=function()return {x=reward.x*130+20,y=reward.y*104+8,percent=percent,action=14} end,
  set_damage=function(port,value)assert(port==1);claims=claims+1;percent=value;return true end,
  log=function(s)logs[#logs+1]=s end}
local current={doc={maze=a},maze_rewards={}}
D.maze_rewards.tick(reward_g,current);D.maze_rewards.tick(reward_g,current)
assert(claims==1 and percent==55,'reward heals 25 once per run')
print('maze contracts PASS: 1000 seeds, validator, determinism, RNG, negative checks')
