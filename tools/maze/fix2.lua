local base='melee/pc/scripts/examples/missions/scripts/'
local D={}
for _,n in ipairs({'mission','validator','maze_set','maze_clearance','maze_metrics','maze_topology','maze_check','maze_encounters','maze','maze_world','loader','world','zones','chunks','glue','fighters','camera','maze_commands','maze_rewards','commands','mission_finish','hud','install','runtime'})do
  local f=loadfile(base..n..'.lua');if f then D[n]=n=='mission'and f()or f()(D)end
end
local failures=0
local function test(name,fn)local ok,why=pcall(fn);print((ok and 'PASS 'or 'FAIL ')..name..(ok and ''or ': '..tostring(why)));if not ok then failures=failures+1 end end
local function clone(t)return assert(load('return '..D.maze.encode(t),'fixture','t',{}))()end
test('clearance across actual ceiling seam names both objects',function()
  assert(D.maze_clearance,'missing clearance checker')
  local m=D.maze.generate(7,{size=12});assert(D.maze_clearance.check(m).ok)
  local c=m.cells[1];c.level.lines[#c.level.lines+1]={kind='floor',x1=c.x*130+10,x2=c.x*130+42,y1=c.y*104+80,y2=c.y*104+80,passthrough=true,label='bad_platform'}
  c.level.lines[#c.level.lines+1]={kind='ceiling',x1=c.x*130+42,x2=c.x*130+10,y1=c.y*104+100,y2=c.y*104+100,label='bad_roof'}
  local result=D.maze_check.check(m);assert(not result.ok and table.concat(result.errors,' '):find('bad_platform',1,true)and table.concat(result.errors,' '):find('bad_roof',1,true))
end)
test('clearance refuses upper floor seams wall gaps and narrow drop landings',function()
  local lower={id='lower',x=0,y=0,level={lines={{kind='floor',x1=10,x2=42,y1=100,y2=100,passthrough=true,label='seam_platform'}}}}
  local upper={id='upper',x=0,y=1,level={lines={{kind='ceiling',x1=42,x2=10,y1=104,y2=104,label='upper_floor'}}}}
  local q=D.maze_clearance.check({cells={lower,upper}});assert(not q.ok and table.concat(q.errors,' '):find('upper/upper_floor',1,true))
  lower.level.lines={{kind='floor',x1=2,x2=34,y1=20,y2=20,passthrough=true,label='near_wall'},
    {kind='left_wall',x1=0,x2=0,y1=0,y2=104,label='wall'}}
  assert(not D.maze_clearance.check({cells={lower}}).ok)
  lower.exits={{side='down',to='below'}};lower.level.lines={}
  local below={id='below',x=0,y=-1,level={lines={{kind='floor',x1=59,x2=71,y1=-4,y2=-4,passthrough=true,label='narrow'}}}}
  assert(not D.maze_clearance.check({cells={lower,below}}).ok)
end)
test('uncomfortable climb and unproved slopes refuse with object names',function()
  local m=D.maze.generate(7,{size=20});local c
  for _,cell in ipairs(m.cells)do if cell.exits[3].to then c=cell;break end end;assert(c)
  c.platforms[1].y=25
  local q=D.maze_clearance.check(m);assert(not q.ok and table.concat(q.errors,' '):find('/climb1',1,true))
  c.level.lines[#c.level.lines+1]={kind='floor',x1=10,x2=42,y1=c.y*104+20,y2=c.y*104+22,label='slope'}
  q=D.maze_clearance.check(m);assert(not q.ok and table.concat(q.errors,' '):find('slope',1,true))
end)
test('invalid authored recipes refuse with chunk and ceiling object names',function()
  local templates=assert(load(D.maze.starters()['missions/maze-chunks/library.lua'],'library','t',{}))()
  for _,t in ipairs(templates)do t.level.lines[#t.level.lines+1]={kind='ceiling',x1=130,x2=0,y1=30,y2=30,label='tight_roof'}end
  local ok,why=pcall(D.maze.generate,7,{templates=templates});assert(not ok and tostring(why):find('c1/',1,true)and tostring(why):find('tight_roof',1,true))
end)
test('holes stay open and horizontal traversal costs a hop',function()
  local m=D.maze.generate(99,{size=20});local found=false;local report=D.maze_check.check(m)
  for _,c in ipairs(m.cells)do if c.exits[4].to then
    for _,l in ipairs(c.level.lines)do assert(l.label~='walk_bridge','bridge remains')end
    for _,e in ipairs(c.exits)do if e.to and (e.side=='left'or e.side=='right')then
      found=true;assert(report.costs[c.id][e.to]>=2 and report.actions[c.id][e.to]=='hop','walk cost hides hole')
    end end
  end end;assert(found)
end)
test('comfortable ascent step and broad drop landing certificates',function()
  local m=D.maze.generate(1,{size=20},function(n)return math.min(2,n)end)
  for _,c in ipairs(m.cells)do if c.exits[3].to and c.exits[3].traversal=='climb'then
    local y=0;for _,p in ipairs(c.platforms)do assert(p.y-y<=20);y=p.y end
  end end
  assert(D.maze_clearance.check(m).ok)
end)
test('crawl exception still requires standing headroom',function()
  local c={id='crawl',x=0,y=0,exits={},level={lines={{kind='floor',x1=10,x2=42,y1=0,y2=0,label='crawl:floor'},
    {kind='ceiling',x1=42,x2=10,y1=21,y2=21,label='crawl:roof'}}}}
  assert(D.maze_clearance.check({cells={c}}).ok)
  c.level.lines[2].y1=19;c.level.lines[2].y2=19;assert(not D.maze_clearance.check({cells={c}}).ok)
end)
test('metrics describe loops wrong turns and main directions',function()
  local m=D.maze.generate(7,{size=20});local q=D.maze_metrics.measure(m)
  assert(q.branches>=1 and q.longest_dead_end>=2 and q.turns>=1 and q.cycles>=1)
  assert(q.directions.left+q.directions.right+q.directions.up+q.directions.down==#m.main_path-1)
end)
test('completion pauses once renders finish and releases only owned pause',function()
  local pauses,resumes=0,0;local logs={}
  local g={pause=function()pauses=pauses+1 end,resume=function()resumes=resumes+1 end,paused=function()return false end,
    log=function(s)logs[#logs+1]=s end,fly_clear=function()end,text=function(_,_,s)logs[#logs+1]=s end}
  local c={doc={name='maze'},run={state={result={status='complete',frames=60}}}}
  local r={g=g,current=c};D.mission_finish.tick(r);D.mission_finish.tick(r);assert(pauses==1)
  D.mission_finish.draw(g,c);assert(table.concat(logs,' '):find('MISSION COMPLETE',1,true))
  D.mission_finish.release(r);D.mission_finish.release(r);assert(resumes==1)
  c.run.finish=nil;g.paused=function()return true end;D.mission_finish.tick(r);D.mission_finish.release(r);assert(resumes==1)
end)
test('refused replacement preserves finish pause and rollback reacquires it',function()
  local paused,pauses,resumes=true,0,0
  local g={command=function()end,log=function()end,paused=function()return paused end,
    pause=function()paused=true;pauses=pauses+1 end,resume=function()paused=false;resumes=resumes+1 end}
  local r=D.runtime.new(g);r.current={run={finish=true,finish_pause=true,state={result={status='complete',frames=60}}}}
  r.attempt=function()return nil,'invalid replacement'end
  assert(not r:command('maze invalid')and paused and resumes==0,'invalid command released finish pause')
  r.attempt=function()r.staging={};return true end
  assert(r:command('maze 7')and not paused)
  r.staging=nil;D.mission_finish.tick(r);assert(paused and pauses==1,'rollback failed to restore pause')
end)
assert(failures==0,failures..' fix2 contract failures')
