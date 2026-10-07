return function(test,fixture,chunks)
  test('fix3 unsafe prepare retries every frame and expires with named timeout',function()
    local s,r=fixture();s.manual_stage=true
    local prepare=r.g.fighter_bench;local player=r.g.player
    r.g.player=function(port)if port==2 then return{cpu=true,action=14,x=0,y=0}end;return player(port)end
    r.g.fighter_benched=function(port)return false end
    r.g.fighter_bench=function(port)if port==2 then return false,'unsafe'end;return prepare(port)end
    assert(r:command('play test'))
    for _=1,599 do r:frame()end
    assert(r.staging.phase=='prepare'and s.loads==0)
    r:frame();assert(r.staging.phase=='rollback'and r.staging.failure.frames==600)
    assert(r.staging.failure.condition:find('unsafe CPU',1,true))
  end)
  test('fix3 partial CPU preparation retains ownership across retries',function()
    local s,r=fixture();s.manual_stage=true;local safe=false;local held={};local player=r.g.player
    local bench,benched,call=r.g.fighter_bench,r.g.fighter_benched,r.g.fighter_call
    r.g.player=function(port)if port==2 or port==3 then return{cpu=true,action=14,x=port*10,y=10}end;return player(port)end
    r.g.fighter_benched=function(port)if port==1 then return benched(port)end;return held[port]end
    r.g.fighter_bench=function(port)if port==1 then return bench(port)end;if port==3 and not safe then return false,'unsafe'end;held[port]=true;return true end
    r.g.fighter_call=function(port,...)if port==1 then return call(port,...)end;held[port]=nil;return true end
    assert(r:command('play test'));for _=1,5 do r:frame()end
    assert(r.staging.c.fighters[2].owned)
    safe=true;for _=1,50 do r:frame()end
    assert(r.current.fighters[2].owned and r.current.fighters[3].owned)
    r:stop('test');assert(not held[2]and not held[3])
  end)
  test('fix3 warm readiness holds handover and all chunk models are declared',function()
    local s,r=fixture();s.manual_stage=true;local ready=false;local jobs={}
    r.g.warm=function(q)jobs[#jobs+1]=q;return #jobs end
    r.g.warm_done=function()return ready end
    assert(r:command('play test'))
    for _=1,40 do r:frame()end
    assert(r.staging.phase=='warm'and not r.current)
    assert(#jobs[1].enemies==2)
    ready=true;for _=1,30 do r:frame()end
    assert(r.current and jobs[2].models[1]and not r.staging)
  end)
  test('fix3 warms a model used only beyond the initial streaming window',function()
    local s,r=fixture();chunks(s)
    local key='missions/test/chunks/c4_2/level.lua';s.files[key]=s.files[key]:gsub('part="custom"','part="late"')
    local list=r.g.mod_list;r.g.mod_list=function(path)local out=list(path);if path:match('/models/$')then out[#out+1]={name='late.gxmesh',dir=false}end;return out end
    assert(r:command('play test'))
    local found=false;for _,h in ipairs(s.warm_declaration.models or{})do if tostring(h):find('late.gxmesh',1,true)then found=true end end
    assert(found and not r.current.stream.loaded.c4_2)
  end)
  test('fix3 held engine launch advances on tick without logic frames',function()
    local s,r=fixture();s.manual_stage=true;local released=0
    r.g.launch_ready=function()released=released+1;return true end
    r:launch_start({mission='test',pending=true})
    for _=1,60 do r:tick()end
    assert(r.current and not r.launch and released==1)
    assert(r.current.run.frames==0,'launch does not advance mission clock')
  end)
  test('fix3 pending engine launch cancels at its readiness deadline',function()
    local s,r=fixture();s.manual_stage=true;s.p.action=0;local cancel,release=0,0
    r.g.launch_cancel=function()cancel=cancel+1 end;r.g.launch_ready=function()release=release+1;return true end
    r.current={doc={folder='missions/unrelated/'},run={}} -- cannot release for an older mission
    r:launch_start({mission='test',pending=true});assert(r.pending)
    for _=1,600 do r:tick()end
    assert(not r.launch and not r.pending and cancel==1 and release==0)
  end)
  test('fix3 invalid engine launch cancels once without throwing',function()
    local s,r=fixture();local cancelled=0;r.g.launch_cancel=function()cancelled=cancelled+1 end
    assert(pcall(r.launch_start,r,{mission='../bad',pending=true}))
    assert(not r.launch and cancelled==1)
  end)
  test('fix3 declared mod autostart and native area guards',function()
    local s,r=fixture();s.files['missions/autostart.lua']='return {mission="test"}'
    r:match_start();r:frame();assert(r.current)
    local count=0;local load=r.g.area_load
    r.g.area_prepare=function(name,build)assert(load(name,build));count=count+1;return count end
    r.g.area_activate=function()return true end
    assert(r:command('restart'));assert(count>0)
    r:stop('command');r:frame();assert(not r.current,'stop must not retrigger autostart in the same match')
  end)
  test('fix3 collision trigger replaces one matching instance per frame',function()
    local s,r=fixture();local parts={}
    for i=1,30 do parts[i]='{part="custom",x=0,y=0,z=0,rot=0,collision=true,floor_flags=0}'end
    s.files['missions/test/level.lua']='return {version=2,units=6.5,parts={'..table.concat(parts,',')..'}}'
    s.files['missions/test/mission.lua']='return {start={x=0,y=10},enemies={{kind="goomba",x=20,y=10}},triggers={{x=0,y=10,w=4,h=4,action="collision",at={x=0,y=0},r=20,open=true}},objective={type="defeat_all"}}'
    assert(r:command('play test'));s.manual_stage=true;s.manual_stream=true
    local calls=0;local spawn=r.g.model_spawn;r.g.model_spawn=function(...)calls=calls+1;return spawn(...)end
    for _=1,35 do local before=calls;r:frame();assert(calls-before<=1)end
    assert(calls==30)
  end)
  test('fix3 queued maze enemies recheck room and live capacity',function()
    local s,r,d=fixture();assert(r:command('play test'));s.manual_stage=true;s.manual_stream=true
    local c=r.current;local a,b={id='a',rect={left=0,right=40,bottom=0,top=40}},nil
    b={id='b',rect={left=40,right=80,bottom=0,top=40}}
    c.doc.maze={cells={{id='a',enemy_budget=1,enemy_wave=1},{id='b',enemy_budget=1,enemy_wave=1}}}
    d.maze_encounters=assert(loadfile('pc/scripts/examples/missions/scripts/maze_encounters.lua')or loadfile((os.getenv('GW_MELEE') or 'melee')..'/pc/scripts/examples/missions/scripts/maze_encounters.lua'))()(d)
    c.stream.loaded={a={},b={}};c.membership={committed=b,room=b,point={x=60,y=10},frame=10}
    c.run.spawn_queue={{type='spawn',index=2,kind='koopa',x=20,y=10,facing=1}}
    c.run.state.pending=1;local before=s.serial;d.glue.step(r.g,c,c.membership.point)
    assert(c.run.encounter_pending[2]and s.serial==before,'queued enemy waits for its own room')
    c.doc.maze=nil;c.run.spawn_queue={{type='spawn',index=2,kind='koopa',x=20,y=10,facing=1}}
    c.run.state.tracked={};for i=1,32 do c.run.state.tracked[i]={index=1,frame=-1}end
    r.g.enemy_status=function()return 'alive'end;r.g.enemy_state=function()return{x=0,y=10}end
    d.glue.step(r.g,c,c.membership.point);assert(#c.run.spawn_queue==1 and s.serial==before,'full pool defers queued spawns')
  end)
  test('fix3 spawn queue is bounded and streaming shares its budget',function()
    local s,r=fixture();s.files['missions/test/mission.lua']='return {start={x=0,y=10},enemies={{kind="goomba",x=20,y=10},{kind="koopa",x=25,y=10},{kind="goomba",x=30,y=10}},objective={type="defeat_all"}}'
    r:command('play test');s.manual_stage=true;s.manual_stream=true
    local function live()local n=0;for _ in pairs(s.enemies)do n=n+1 end;return n end
    local before=live();r:frame();assert(live()-before<=1)
    r.current.stream.load_frame=r.current.run.frames+1;before=live();r:frame();assert(live()==before)
    r:frame();assert(live()<=3)
  end)
end
