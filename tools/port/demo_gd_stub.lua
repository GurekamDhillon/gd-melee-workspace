-- Explicit contract subset for demo authoring. This is not a physics/GPU emulator.
-- Missing methods error: no universal gd.__index no-op can hide a misspelling.
local S={frame=0,keys={},logs={},commands={},files={},resources={},next=10,waits={},mods={},tints=0,paused=false}
local g={}
local function noop() end
local function yes() return true end
local function handle(kind,value)
  S.next=S.next+1; S.resources[S.next]={kind=kind,value=value}; return S.next
end
local function remove(h) local old=S.resources[h]; S.resources[h]=nil; return old~=nil end
local function resource(h,kind)
  assert(S.resources[h] and S.resources[h].kind==kind,'stale '..kind..' handle'); return S.resources[h]
end
S.players={}
for port=1,6 do S.players[port]={port=port,char=port,char_name='Fox',kind=port,cpu=port>1,
  x=0,y=0,vx=0,vy=0,percent=0,stocks=4,falls=0,facing=1,action=14,action_frame=0,anim_frame=0,airborne=false} end
function g.frame() return S.frame end
function g.scene() return {epoch=S.epoch or 1} end
function g.time() return S.frame/60 end
function g.match() return {active=S.active~=false,stage=32,frame=S.frame,netplay=false} end
function g.player(p) return S.players[p] end
function g.players() return S.players end
function g.safe_area() return {x=0,y=0,w=853,h=480,right=853,bottom=480} end
function g.key_pressed(k) local pressed=S.keys[k]; S.keys[k]=nil; return pressed end
g.key=g.key_pressed
function g.pad() return {x=0,y=0,A=false,buttons=0} end
function g.mouse() return 100,100,0,0 end
function g.input(port,spec,frames) assert(S.players[port] and frames>=1); S.pad_claim=port end
function g.release_pad() S.pad_claim=nil end
g.release=g.release_pad
function g.command(name,fn) S.commands[name]=fn end
function g.log(...) S.logs[#S.logs+1]=table.concat({...},' ') end
function g.teleport(p,x,y) assert(type(x)=='number' and type(y)=='number'); S.players[p].x=x; S.players[p].y=y end
function g.set_percent(p,n) S.players[p].percent=n end
function g.cpu_mode(p,mode) assert(mode=='stand' or mode=='fight'); S.players[p].cpu_mode=mode; return true end
function g.fighter_mod(p,...)
  if select('#',...)>0 then S.mods[p]=(...); return true end
  return S.mods[p]
end
function g.fighter_bench(p)
  S.bench_calls=(S.bench_calls or 0)+1
  if S.refuse_bench then return false,'unsafe action' end
  S.players[p].benched=true; return true
end
function g.fighter_benched(p)
  local player=S.players[p]
  return player and player.benched or false,{{entity_index=0,present=player~=nil,
    invisible=player and player.hidden or false,benched=player and player.benched or false,dormant=false}}
end
function g.fighter_call(p,x,y)
  assert(S.players[p].benched,'calling an unbenched fighter'); S.players[p].benched=false; g.teleport(p,x,y); return true
end
function g.fighter_recycle(p,opts)
  if S.players[p].action~=13 then return false,'KO not complete' end
  g.teleport(p,opts.x,opts.y); S.players[p].percent=0; S.players[p].hidden=S.recycle_hidden or false; return true
end
function g.floor_below() return 0 end
function g.stage_add_platform(x,y,w) assert(w>0); return handle('line',{x=x,y=y}) end
function g.stage_add_line(x0,y0,x1,y1,kind)
  assert((kind=='floor' and x1>x0) or (kind=='ceiling' and x1<x0) or
    (kind=='left_wall' and y1>y0) or (kind=='right_wall' and y1<y0),'wrong line winding')
  return handle('line')
end
g.stage_remove=remove
function g.stage_move(h,x,y) resource(h,'line'); assert(type(x)=='number' and type(y)=='number'); return true end
function g.stage_hide(on)
  assert(type(on)=='boolean')
  if not on then for _,r in pairs(S.resources) do if r.kind=='slot' then return false,'stage slots live' end end end
  S.hidden=on; return true
end
for _,name in ipairs{'stage_set_camera_bounds','stage_set_blast_bounds','stage_set_spawn'} do
  g[name]=function() S.arena=true; return true end
end
function g.stage_restore_bounds() S.arena=false; return true end
function g.stage_spawn() return 0,0,0 end
function g.area_load(name,builder)
  if S.area_budget then assert(S.area_frame~=S.frame,'more than one area loaded in a logic frame'); S.area_frame=S.frame end
  if S.area_failure then return false,'injected build failure' end
  if S.areas and S.areas[name] then return false end
  S.areas=S.areas or {}; local before=S.next; builder(); S.areas[name]={}
  for h=before+1,S.next do S.areas[name][h]=true end
  return true
end
function g.area_unload(name)
  if not S.areas or not S.areas[name] then return false end
  for h in pairs(S.areas[name]) do remove(h) end; S.areas[name]=nil; return true
end
function g.mod_read(path)
  assert(path:match('^missions/') and not path:find('..',1,true),'invalid mission path')
  local f=io.open(S.folder..'/'..path,'rb'); if not f then return nil,'missing' end
  local text=f:read('*a'); f:close(); return text
end
function g.mod_stamp(path) return #assert(g.mod_read(path)) end
function g.mod_list() return {{name='tiny',dir=true}} end
function g.model_load(name)
  if not S.models then error('optional export not installed') end
  return handle('asset',name)
end
function g.model_spawn(asset,options) resource(asset,'asset'); return handle('model',options) end
g.model_despawn=remove; g.model_release=remove
function g.model_label(h,text) resource(h,'model'); assert(#text<=80); return true end
function g.model_set(h,opts) resource(h,'model'); assert(type(opts)=='table'); return true end
function g.light_set(values) assert(type(values)=='table'); S.light=values end
function g.camera_get() return {eye={x=0,y=30,z=200},interest={x=0,y=0,z=0},fov=30} end
function g.camera_params(values)
  local old=S.camera_params or {yaw_gain=0.05,pitch_gain=0.05}
  S.camera_params=values; return old
end
for _,name in ipairs{'camera_set','camera_shake','camera_bounds','camera_attach','camera_detach'} do g[name]=noop end
function g.camera_follow()
  assert(not S.in_task,'camera follow claimed inside a temporary task')
  S.camera_claim=true
end
function g.camera_move(o) assert(type(o.frames)=='number' and o.frames>=1 and o.frames<=6000) end
function g.project(x,y) return x+320,240-y,true,1 end
function g.spawn_enemy(kind,x,y) return handle('enemy',{kind=kind,x=x,y=y,alive=true}) end
function g.enemy_alive(h) return S.resources[h]~=nil end
function g.enemy_state(h) local r=S.resources[h]; return r and r.value end
g.enemy_remove=remove
function g.item_define(path) assert(type(path)=='string'); return true end
function g.item_spawn(name,x,y,opts) return handle('item',{name=name,x=x,y=y,payload=opts.payload}) end
g.item_despawn=remove
function g.items()
  local out={}; for h,r in pairs(S.resources) do if r.kind=='item' then
    out[#out+1]={id=h,handle=h,kind=0,name=r.value.name,owner_port=0,layer='geno',x=r.value.x,y=r.value.y,z=0,visual_y=r.value.y+6,rotation=S.frame*6,visible=true}
  end end; return out
end
function g.hitboxes() return {{id=0,damage=5,angle=45,radius=3}} end
function g.motion_list() return {{id=0,name='DeadRight'},{id=12,name='Rebirth'},{id=14,name='Wait'},{id=44,name='Attack11'}} end
function g.motion_name() return 'Wait' end
function g.timeline(_,motion) assert(motion==nil or type(motion)=='number'); return {length=30,events={{frame=3,name='hitbox'}}} end
function g.set_motion(port,motion) assert(type(motion)=='number','motion requires numeric id'); S.players[port].action=motion; S.paused=true; return true end
function g.debug_draw(_,flags) if flags~=nil then S.debug=flags end; return S.debug or 0 end
function g.contacts(p) local q=S.players[p]; return {x=q.x,y=q.y,floor={label='stub',owner=S.floor}} end
function g.contact_events(cursor) return {},cursor or 0,0 end
function g.contact_trace(on) S.trace=on~=false; return true end
function g.contact_overlay(on) S.overlay=on end
function g.wait_until(spec)
  assert(type(spec)=='table' and spec.timeout>0); local h=handle('wait',spec)
  S.waits[h]={done=false,ok=false,frames=0,reason='pending'}; return h
end
local native_wait=g.wait_until
function g.wait_until(spec,timeout)
  if type(spec)=='table' then return native_wait(spec) end
  local age=0
  while not spec() do
    if timeout and age>=timeout then return false end
    coroutine.yield(1); age=age+1
  end
  return true
end
function g.run(fn) S.tasks=S.tasks or {}; S.tasks[#S.tasks+1]={co=coroutine.create(fn),left=1} end
function g.wait(n) return coroutine.yield(n) end
function g.press(port,buttons,n) g.input(port,{buttons=buttons},n); g.wait(n) end
function g.tilt(port,x,y,n) g.input(port,{x=x,y=y},n); g.wait(n) end
function g.wait_status(h) return S.waits[h] end
function g.advance()
  S.frame=S.frame+1
  for _,task in ipairs(S.tasks or {}) do
    if coroutine.status(task.co)~='dead' then
      task.left=task.left-1
      if task.left<=0 then S.in_task=true; local ok,n=coroutine.resume(task.co); S.in_task=false; assert(ok,n); task.left=n or 1 end
    end
  end
  for h,w in pairs(S.waits) do if not w.done then
    w.frames=w.frames+1; local spec=resource(h,'wait').value; local p=S.players[spec.port or 1]
    local ok=(not spec.on or S.floor==spec.on) and (not spec.x or math.abs(p.x-spec.x)<=spec.radius)
      and (spec.airborne==nil or p.airborne==spec.airborne)
    if ok then w.done=true; w.ok=true; w.reason='condition met'
    elseif w.frames>=spec.timeout then w.done=true; w.reason='timeout' end
  end end
end
function g.data_read(path) if S.read_error then return nil,'unreadable' end; return S.files[path],S.files[path] and nil or 'missing' end
function g.data_exists(path) return S.files[path]~=nil end
function g.data_write_atomic(path,text) if S.write_error then return false,'write refused' end; S.files[path]=text; return true end
function g.parts() return {{index=0},{index=1}} end
function g.dobj_tint(_,index,color) assert(type(index)=='number' and type(color)=='number'); S.tints=S.tints+1; return true end
function g.dobj_tints() return {count=S.tints} end
function g.parts_clear() S.tints=0 end
function g.stage_slot_load(name) if S.refuse_slot then return nil,'out of capacity' end; return handle('slot',name) end
function g.stage_switch(slot,opts)
  resource(slot,'slot')
  if S.arena then return false,'arena tracking owns the stage' end
  S.switch=slot; return true
end
function g.stage_queue(entries) assert(#entries>0); S.queue=entries; return true end
function g.stage_queue_clear() S.queue=nil; return true end
g.stage_queue_next=yes
function g.stage_slots() return {} end
function g.shader_load(path,opts) assert(type(path)=='string' and type(opts)=='table'); return handle('shader') end
function g.shader_status(h) resource(h,'shader'); return {valid=true} end
function g.post_add(path,opts) assert(type(opts)=='table'); return handle('post') end
function g.post_set(h,opts) resource(h,'post'); assert(type(opts)=='table'); return true end
function g.post_clear()
  assert(not S.live_cover,'demo cleared the live transition cover')
  for h,r in pairs(S.resources) do if r.kind=='post' then remove(h) end end
end
function g.fighter_shader(_,path,opts) assert(path==nil or type(opts.params)=='table'); return true end
function g.stage_shader(path,opts) assert(path==nil or type(opts.params)=='table'); return true end
function g.fx() return {{live_particles=5}} end
function g.fx_world(package,x,y,z,scale,seed)
 assert(type(package)=='string' and scale>0);return handle('fx',{package=package,x=x,y=y,z=z})
end
function g.fx_move(h,x,y,z) local r=resource(h,'fx');r.value={x=x,y=y,z=z};return true end
function g.play_sound(id,opts) S.sounds=S.sounds or {};S.sounds[#S.sounds+1]={id=id,pitch=opts and opts.pitch or 0};return #S.sounds end
function g.fx_play() return handle('fx') end
function g.fx_attach() return true end
function g.fx_instance(h) return S.resources[h] and {live_particles=5} end
function g.fx_end(h) return remove(h) end
function g.fx_control(h) resource(h,'fx'); return true end
function g.fx_shader() return true end
function g.fx_stop() for h,r in pairs(S.resources) do if r.kind=='fx' then remove(h) end end end
function g.fly_speed(v) local old=S.speed or 2; if v then S.speed=v end; return old end
function g.fly_solid(v) local old=S.solid or false; if v~=nil then S.solid=v end; return old end
function g.fly(_,v) if v~=nil then S.flying=v==true or v=='toggle' end; return S.flying end
function g.fly_target() if S.fly_unsafe then error('fighter state cannot fly') end; S.flying=true end
function g.fly_attack() S.flying=true; S.attacking=true end
function g.fly_clear() S.attacking=false end
function g.fly_state() return {flying=S.flying,attacking=S.attacking,pulses=3} end
function g.hitstop() S.hitstop=true; return true end
function g.hitstop_cancel() S.hitstop=false end
function g.pause() S.paused=true end
function g.resume() S.paused=false end
function g.paused() return S.paused end
function g.history(depth,interval)
  if depth then S.depth=depth; S.interval=interval end
  return {now=S.frame,depth=S.depth or 0,interval=S.interval or 1}
end
function g.savestate(slot) S.snapshot={slot=slot,percent=S.players[1].percent}; S.saved_event=slot end
function g.loadstate(slot) assert(S.snapshot and S.snapshot.slot==slot); S.players[1].percent=S.snapshot.percent; S.loaded_event=slot end
function g.scene_launch() S.launched=true end
for _,name in ipairs{'scene_clear','step','label','text','fill','box','line'} do g[name]=noop end
function g.prof() return true,'profiler toggled' end
function g.perf() return {fps=120,profiler={zones={}}} end
function g.comm() S.comm=true end
function g.comm_state() return {shown=S.comm or false,queued=0} end
function g.comm_clear() S.comm=false end
g.kit={available=function() return true end}
for _,name in ipairs{'panel','icon','text','button','paragraph'} do g.kit[name]=noop end
-- Warm declarations are diagnostic jobs, never immediate readiness.
function g.warm(spec)
  local n=0;for _,values in pairs(spec) do n=n+#values end
  return handle('warm',{count=n,started=S.frame})
end
function g.warm_status(h)
  local r=resource(h,'warm').value
  local prepared=math.min(r.count,S.frame-r.started)
  return {objects=r.count,prepared=prepared,pending=r.count-prepared,done=prepared==r.count,failed=false}
end
function g.warm_done(h)
  if S.warm_failure then return false,'fixture discovery failure' end
  return g.warm_status(h).done,nil
end
function g.warm_release(h) resource(h,'warm');return remove(h) end
return g,S
