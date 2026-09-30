#!/usr/bin/env python3
"""Exercise the transactional physical-room runtime against a fake engine.

Real Rooms/RoomRecipes/RoomCatalogue/Topology/Adapter modules run unchanged.
Recipes stay uncertified; the fixtures admit them through a separate test-only
Adapter wrapper, exactly as the runtime would see an admitted node. Nothing here
is an in-engine playtest or a certification claim.
"""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / 'melee/worktrees/linux/pc/scripts/examples/roguelite'
LUA = shutil.which('lua5.4') or shutil.which('lua')
MODULES = [RUNTIME / name for name in ('rng.lua', 'room_catalogue.lua', 'room_recipes.lua',
                                       'encounter_catalogue.lua', 'progression.lua', 'topology.lua',
                                       'adapter.lua', 'rooms.lua', 'runtime_rooms.lua')]

PRELUDE = r'''
local RNG=assert(loadfile(arg[1]))() local Cat=assert(loadfile(arg[2]))()
local Recipes=assert(loadfile(arg[3]))() local Enc=assert(loadfile(arg[4]))()
local Prog=assert(loadfile(arg[5]))() local Top=assert(loadfile(arg[6]))()
local Adapter=assert(loadfile(arg[7]))() local Rooms=assert(loadfile(arg[8]))()
local RR=assert(loadfile(arg[9]))()
local function copy(t) if type(t)~='table' then return t end local o={} for k,v in pairs(t) do o[k]=copy(v) end return o end
local function count(t) local n=0 for _ in pairs(t) do n=n+1 end return n end
-- Fake stage/model engine. Rooms reads the global gd, so expose it globally;
-- the runtime takes the same table explicitly, as production main will.
local serial=0
local records,spawns,loads,assets={},{},{},{}
local isolation=true
local fail_platform,fail_line,fail_spawn,fail_load=nil,nil,nil,nil
local refuse_remove,refuse_despawn={},{}
local platform_calls,line_calls,spawn_calls,load_calls=0,0,0,0
local platform_log,line_log,teleports={},{},{}
local link_log={}
local fail_link,throw_link=nil,nil
-- Fighters are real live tables so placement can capture verified originals.
local players={[1]={x=-42,y=0,vy=0},[2]={x=28,y=0,vy=0}}
local refuse_teleport_port,false_teleport_port,fail_player_port=nil,nil,nil
gd={buttons={},
 log=function() end,
 stage_isolate=function(v) if v~=nil then isolation=v end return isolation end,
 stage_add_platform=function(x,y,w,opts)
  platform_calls=platform_calls+1;platform_log[#platform_log+1]={x=x,y=y,w=w,opts=opts}
  if fail_platform and platform_calls==fail_platform then return nil,'platform allocation refused' end
  serial=serial+1;records[serial]={kind='platform',x=x,y=y,w=w,opts=opts};return serial
 end,
 stage_add_line=function(x0,y0,x1,y1,kind,opts)
  line_calls=line_calls+1;line_log[#line_log+1]={x0=x0,y0=y0,x1=x1,y1=y1,kind=kind,opts=opts}
  if fail_line and line_calls==fail_line then return nil,'line allocation refused' end
  serial=serial+1;records[serial]={kind='line',x0=x0,y0=y0,x1=x1,y1=y1,opts=opts};return serial
 end,
 stage_link=function(a,b)
  assert(records[a] and records[b],'link used foreign or removed handles')
  link_log[#link_log+1]={a,b}
  if throw_link and #link_log==throw_link then error('link API restricted') end
  if fail_link and #link_log==fail_link then return false,'occupied endpoint' end
  local ra,rb=records[a],records[b]
  local ax,ay=ra.x1 or (ra.x+ra.w/2),ra.y1 or ra.y
  local bx,by=rb.x0 or (rb.x-rb.w/2),rb.y0 or rb.y
  assert((ax-bx)^2+(ay-by)^2<=0.05^2,'link bridged a gap or interior')
  assert(not ra.right and not rb.left,'endpoint linked twice')
  ra.right=b;rb.left=a;return true
 end,
 stage_remove=function(h) if not records[h] or refuse_remove[h] then return false end records[h]=nil;return true end,
 player=function(port) if fail_player_port==port then return nil end return players[port] end,
 teleport=function(port,x,y)
  if refuse_teleport_port==port then error('fighter respawning') end
  if false_teleport_port==port then return false end
  local p=players[port];p.x=x;p.y=y;teleports[#teleports+1]={port=port,x=x,y=y};return true
 end,
 model_load=function(name)
  load_calls=load_calls+1;loads[#loads+1]=name
  if fail_load and load_calls==fail_load then error('load API restricted') end
  serial=serial+1;assets[serial]=name;return serial
 end,
 model_spawn=function(asset,opts)
  spawn_calls=spawn_calls+1
  if fail_spawn and spawn_calls==fail_spawn then return nil,'instance allocation refused' end
  assert(assets[asset] and opts.collision==false,'visual instance must be collision free')
  serial=serial+1;spawns[serial]=true;return serial
 end,
 model_despawn=function(h) if not spawns[h] or refuse_despawn[h] then return false end spawns[h]=nil;return true end,
 model_release=function(asset) assets[asset]=false end,
 model_get=function(h) return spawns[h] end}
local function reset_logs() platform_calls,line_calls=0,0;platform_log,line_log={},{} end
local function records_live() return count(records) end
local function admission() return {resolve=Recipes.resolve,is_certified=function() return true end} end
local function manifest(seed)
 local top=Top.new(Cat,Enc,Prog,RNG)
 return assert(Adapter.new(Cat,admission()):manifest(top:generate(seed)))
end
local function drive(rr,tx)
 while true do
  local st,why=rr:step(tx)
  if st=='loading' then
  elseif st=='ready' then return true
  else return false,why end
 end
end
local function commit_room(rr,node,from,exit)
 local tx,why=rr:begin(node,from and {from=from,exit=exit} or nil)
 assert(tx,'begin: '..tostring(why))
 local ok,bad=drive(rr,tx)
 assert(ok,'step: '..tostring(bad))
 local out,reason=rr:commit(tx)
 assert(out,'commit: '..tostring(reason))
 return out
end
local function find_exit(view,pred)
 for _,id in ipairs(view.order) do
  for _,e in ipairs(view.nodes[id].exits) do if pred(view.nodes[id],e) then return view.nodes[id],e end end
 end
end
local function recipe_node(template_id,kind)
 local t=assert(Cat.rooms[template_id])
 local g,r=Recipes.resolve(t)
 return {id=template_id,template_id=template_id,recipe=t.recipe,recipe_modules=r.modules or {},
  recipe_version=r.version,theme='cobalt',kind=kind,room=copy(g),exits={}},g,r
end
'''


class PhysicalRuntimeTests(unittest.TestCase):
    def run_lua(self, body):
        self.assertIsNotNone(LUA, 'Lua interpreter required')
        result = subprocess.run([LUA, '-', *[str(m) for m in MODULES]],
                                input=PRELUDE + body, text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_resolved_ascent_room_local_graph_during_overlap(self):
        self.run_lua(r'''
local src=recipe_node('branch_y','traversal')
local dest=recipe_node('branch_y','traversal');dest.id='branch_y_copy'
local exit={edge_id='duplicate',socket='out',side='right',to=dest.id,arrival_socket='left'}
src.exits={exit}
local rr=RR.new(gd,Rooms)
commit_room(rr,src)
local source=rr:active_room()
assert(#link_log==3,'real ascent must join slope/landing/slope/landing')
local source_set={} for _,e in ipairs(source.handles) do source_set[e.handle]=true end
local tx=assert(rr:begin(dest,{from=source,exit=exit}))
assert(drive(rr,tx))
assert(#link_log==6 and rr:total()==10,'duplicate destination failed to build')
local dest_set={} for _,e in ipairs(tx.dest.handles) do dest_set[e.handle]=true end
for i,pair in ipairs(link_log) do
 local own=i<=3 and source_set or dest_set
 assert(own[pair[1]] and own[pair[2]],'source/destination were cross linked')
end
local slope1,slope2,lower,upper,ground
for _,e in ipairs(tx.dest.handles) do
 if e.x0==-52 and e.x1==-26 then slope1=e.handle
 elseif e.x0==0 and e.x1==26 then slope2=e.handle
 elseif e.x0==-26 and e.x1==0 then lower=e.handle
 elseif e.x0==26 and e.x1==52 then upper=e.handle
 elseif e.x0==-65 and e.x1==65 then ground=e.handle end
end
assert(records[slope1].right==lower and records[lower].right==slope2 and records[slope2].right==upper)
assert(not records[ground].left and not records[ground].right,'ground interior was linked')
assert(rr:rollback(tx));assert(rr:total()==5 and records_live()==5)
for _,pair in ipairs(link_log) do if source_set[pair[1]] then assert(records[pair[1]].right==pair[2]) end end
assert(rr:cleanup())
''')

    def test_endpoint_matching_refuses_ambiguity_and_preserves_gaps(self):
        self.run_lua(r'''
local calls={}
local engine={stage_link=function(a,b)calls[#calls+1]={a,b};return true end}
local function e(h,x0,y0,x1,y1)return {handle=h,x0=x0,y0=y0,x1=x1,y1=y1}end
-- Euclidean distance, not a per-axis box; separated drop lips never link.
assert(RR.link_floor_seams(engine,{e(1,-65,0,-6.5,0),e(2,6.5,0,65,0)}))
assert(RR.link_floor_seams(engine,{e(3,0,0,1,1),e(4,1.04,1.04,2,2)}))
assert(#calls==0)
-- Interior crossing/touch, and same-side endpoints cannot create seams.
assert(RR.link_floor_seams(engine,{e(5,0,0,2,2),e(6,0,2,2,0),e(7,1,1,3,1)}))
assert(#calls==0)
assert(RR.link_floor_seams(engine,{e(8,0,0,1,0),e(9,0,0,2,1)}));assert(#calls==0)
-- The allowed tolerance survives reversed allocation order.
local ok,n=RR.link_floor_seams(engine,{e(11,1.03,.03,2,0),e(10,0,0,1,0)})
assert(ok and n==1 and calls[1][1]==10 and calls[1][2]==11)
calls={}
ok=RR.link_floor_seams(engine,{e(1,0,0,1,0),e(2,1,0,2,0),e(3,1.02,0,3,0)})
assert(not ok and #calls==0,'ambiguous graph linked before complete preflight')
ok=RR.link_floor_seams(engine,{e(1,0,0,1,0),e(2,-1,0,1,0),e(3,1,0,2,0)})
assert(not ok and #calls==0,'multiple left neighbours silently selected')
''')

    def test_required_links_fail_closed_with_retryable_rollback(self):
        self.run_lua(r'''
for _,mode in ipairs({'false','throw','missing','ambiguous'}) do
 local node=recipe_node('branch_y','traversal')
 local rr=RR.new(gd,Rooms)
 local tx=assert(rr:begin(node))
 local original=gd.stage_link
 local calls_before=#link_log
 if mode=='false' then fail_link=calls_before+2
 elseif mode=='throw' then throw_link=calls_before+2
 elseif mode=='missing' then gd.stage_link=nil
 else
  node.room.platforms[#node.room.platforms+1]={x=-12,y=13,width=28,passthrough=false,ledges=false}
  -- begin captures collision; update it through a fresh transaction.
  assert(rr:rollback(tx));tx=assert(rr:begin(node))
 end
 -- Refuse the first cleanup handle, retaining ownership and the line count.
 local remove=gd.stage_remove
 local pending
 gd.stage_remove=function(h)if not pending then pending=h;return false end return remove(h) end
 local spawned_before=spawn_calls
 local ok,why=drive(rr,tx)
 assert(not ok,tostring(why))
 local expected=mode=='ambiguous' and 'ambiguous' or (mode=='missing' and 'stage_link' or 'seam link refused')
 assert(why:find(expected,1,true),tostring(why))
 assert(spawn_calls==spawned_before,'visuals spawned before seam validation')
 assert(rr:total()==1 and #tx.dest.handles==1 and tx.dest.handles[1].handle==pending,'rollback lost refused handle')
 gd.stage_remove=remove;gd.stage_link=original;fail_link=nil;throw_link=nil
 assert(rr:rollback(tx));assert(rr:total()==0 and records_live()==0)
end
-- Missing link API is compatible with an authored room requiring no seams.
gd.stage_link=nil
local node=recipe_node('shortcut_door','traversal')
local rr=RR.new(gd,Rooms);commit_room(rr,node)
assert(rr:cleanup() and records_live()==0)
''')

    def test_translated_collision_slopes_and_incremental_preload(self):
        self.run_lua(r'''
reset_logs()
local view=manifest(42)
local ascent
for _,id in ipairs(view.order) do if #((view.nodes[id].room.lines) or {})>0 then ascent=view.nodes[id];break end end
assert(ascent,'no ascent room in the generated route')
local rr=RR.new(gd,Rooms,{max_total_lines=32})
local tx=assert(rr:begin(ascent))
local steps=0
while true do
 local st,why=rr:step(tx)
 if st=='loading' then steps=steps+1;assert(load_calls==steps,'one model load per loading step')
 elseif st=='ready' then break
 else error(tostring(why)) end
end
local plan=assert(Rooms.plan(ascent))
local unique={} for _,p in ipairs(plan.parts) do unique[p.model]=true end
assert(steps==count(unique),'preload did not load one asset per missing model')
local col=assert(Rooms.collision(ascent))
local pi=0
for _,seg in ipairs(col.floor_segments) do
 pi=pi+1 local c=platform_log[pi]
 assert(c.x==(seg.left+seg.right)/2 and c.y==seg.y and c.w==seg.right-seg.left)
 assert(c.opts.passthrough==false and c.opts.ledges==true and c.opts.draw==false)
end
for _,p in ipairs(col.platforms) do
 pi=pi+1 local c=platform_log[pi]
 assert(c.x==p.x and c.y==p.y and c.w==p.width)
 assert(c.opts.passthrough==p.passthrough and c.opts.ledges==p.ledges)
end
assert(pi==#col.floor_segments+#col.platforms)
assert(#line_log==#col.lines and #col.lines>0,'ascent slopes were not built through stage_add_line')
for i,l in ipairs(col.lines) do
 local c=line_log[i]
 assert(c.x0==l.x0 and c.y0==l.y0 and c.x1==l.x1 and c.y1==l.y1 and c.kind=='floor')
 assert(c.opts.passthrough==l.passthrough and c.opts.ledges==l.ledges)
end
assert(rr:place(tx,{{port=1,x=0,y=0}}))
local out=assert(rr:commit(tx))
assert(out.room_id==ascent.id and out.room.instances==#plan.parts and out.room.instances<=28)
assert(rr:total()==#col.floor_segments+#col.platforms+#col.lines)
print('physical: translated floor/slope collision, incremental preload, bounded visuals passed')
''')

    def test_per_socket_trigger_arrival_upper_and_return(self):
        self.run_lua(r'''
reset_logs()
local view=manifest(42)
local rr=RR.new(gd,Rooms,{max_total_lines=32})
local src,exit=find_exit(view,function(n,e) return e.side=='top' end)
assert(src and exit,'no upper-socket exit in the generated route')
local src_out=commit_room(rr,src)
local src_room=rr:active_room()
local dest=view.nodes[exit.to]
local info=assert(rr:resolve_exit(src,dest,exit))
assert(info.side=='top' and info.socket==exit.socket and info.arrival_socket==exit.arrival_socket)
assert(info.socket~=info.arrival_socket,'distinct sockets were collapsed')
assert(info.trigger.x==src.room.exit_anchors[exit.side].x and info.trigger.y==src.room.exit_anchors[exit.side].y)
assert(info.arrival.x==exit.arrival.x and info.arrival.y==exit.arrival.y)
local side
for _,s in ipairs(Cat.rooms[dest.template_id].sockets) do if s.id==exit.arrival_socket then side=s.side end end
local authored=dest.room.arrivals[exit.arrival_socket] or dest.room.arrivals[side]
assert(authored and info.arrival.x==authored.x and info.arrival.y==authored.y,
 'destination arrival did not follow destination socket then authored side')
local out=commit_room(rr,dest,src_room,exit)
assert(out.room_id==dest.id and out.arrival.x==info.arrival.x and out.arrival.y==info.arrival.y)
local back
for _,e in ipairs(dest.exits) do if e.to==src.id then back=e break end end
assert(back,'bidirectional edge has no return exit')
local back_info=assert(rr:resolve_exit(dest,src,back))
local back_out=commit_room(rr,src,rr:active_room(),back)
assert(back_out.room_id==src.id and back_out.arrival.x==back_info.arrival.x and back_out.arrival.y==back_info.arrival.y)
-- merge entries: two destination sockets keep two distinct authored arrivals
local mergenode,mg=recipe_node('rejoin_merge','branch')
local function merge_exit(side)
 return {side=side,socket='s_'..side,anchor=copy(mg.exit_anchors[side]),to=mergenode.id,
  arrival_socket=(side=='left' and 'in_a' or 'in_b'),arrival=copy(mg.arrivals[side]),edge_id='m_'..side}
end
local left_info=assert(rr:resolve_exit(mergenode,mergenode,merge_exit('left')))
local top_info=assert(rr:resolve_exit(mergenode,mergenode,merge_exit('top')))
assert(left_info.arrival.x~=top_info.arrival.x or left_info.arrival.y~=top_info.arrival.y,
 'merge entries collapsed to one arrival')
assert(left_info.arrival.x==mg.arrivals.left.x and top_info.arrival.y==mg.arrivals.top.y)
-- one-way direction: the adapter lists only the traversable side; the runtime
-- resolves that single exit and the destination exposes no invented return
local one=copy(Top.new(Cat,Enc,Prog,RNG):generate(42))
local eid
for id,e in pairs(one.edges_by_id) do if e.direction=='both' then eid=id break end end
one.edges_by_id[eid].direction='forward'
local oneview=assert(Adapter.new(Cat,admission()):manifest(one))
local edge=one.edges_by_id[eid]
local from_node=oneview.nodes[edge.from_room]
local one_exit
for _,e in ipairs(from_node.exits) do if e.edge_id==eid then one_exit=e end end
assert(one_exit,'one-way edge was not listed for its traversable side')
local one_info=assert(rr:resolve_exit(from_node,oneview.nodes[edge.to_room],one_exit))
assert(one_info.to==edge.to_room)
for _,e in ipairs(oneview.nodes[edge.to_room].exits) do assert(e.edge_id~=eid,'one-way edge exposed a return') end
print('physical: per-socket trigger/arrival, upper, merge, return and one-way passed')
''')

    def test_bottom_drop_requires_downward_passage(self):
        self.run_lua(r'''
local node,g=recipe_node('junction_cross','branch')
local dest,dg=recipe_node('entry_gate','entry')
local bottom,top
for _,s in ipairs(Cat.rooms.junction_cross.sockets) do
 if s.side=='bottom' then bottom=s.id elseif s.side=='top' then top=s.id end
end
assert(bottom and top)
dest.room.arrivals['out']=copy(dg.arrivals.right)
local function canonical(side,socket,anchor)
 return {side=side,socket=socket,anchor=copy(anchor),to=dest.id,arrival_socket='out',
  arrival=copy(dg.arrivals.right),edge_id='e1',kind='shortcut'}
end
local rr=RR.new(gd,Rooms,{max_total_lines=32})
local info=assert(rr:resolve_exit(node,dest,canonical('bottom',bottom,g.exit_anchors.bottom)))
assert(info.drop==true and info.opening and info.opening.width>0)
local floor=node.room.floor
local below=floor.y-4.01
assert(not rr:triggered(info,{x=info.trigger.x,y=floor.y,vy=0}),'standing at the drop anchor must not trigger')
assert(not rr:triggered(info,{x=info.trigger.x,y=floor.y-1,vy=-6}),'not yet below the floor')
assert(not rr:triggered(info,{x=info.opening.x,y=below,vy=6}),'rising from below must not trigger')
assert(not rr:triggered(info,{x=info.opening.x,y=below,vy=0}),'no downward motion must not trigger')
assert(rr:triggered(info,{x=info.opening.x,y=below,vy=-6}),'falling through the opening must trigger')
assert(not rr:triggered(info,{x=info.opening.x+info.opening.width,y=floor.y-10,vy=-6}),'outside the authored opening')
assert(not rr:triggered(info,{x=info.opening.x,y=floor.y+8,vy=-6}),'one-way drop never triggers rising above')
-- vy absent: a previous sample supplies the descent, including the rising case
assert(rr:triggered(info,{x=info.opening.x,y=floor.y-10},floor,{x=info.opening.x,y=floor.y}),
 'previous-sample descent was not detected')
assert(not rr:triggered(info,{x=info.opening.x,y=floor.y-6},floor,{x=info.opening.x,y=floor.y-12}),
 'previous-sample rise must not trigger')
assert(not rr:triggered(info,{x=info.opening.x,y=below}),'no motion data must not trigger')
local top_info=assert(rr:resolve_exit(node,dest,canonical('top',top,g.exit_anchors.top)))
assert(rr:triggered(top_info,{x=g.exit_anchors.top.x,y=g.exit_anchors.top.y}))
assert(not rr:triggered(top_info,{x=g.exit_anchors.top.x+40,y=g.exit_anchors.top.y}))
-- the drop floor is built as two real segments; the opening is never filled
reset_logs()
local rr2=RR.new(gd,Rooms,{max_total_lines=32})
local out=commit_room(rr2,node)
local jcol=assert(Rooms.collision(node))
assert(#jcol.floor_segments==2,'drop floor did not resolve to two segments')
assert(#link_log==3,'junction should link its ascent but never bridge the drop')
for _,e in ipairs(rr2:active_room().handles) do
 if e.y0==0 and e.y1==0 then
  assert(not records[e.handle].left and not records[e.handle].right,'authored drop lip was welded')
 end
end
local opening=g.floor.openings[1]
for i,seg in ipairs(jcol.floor_segments) do
 local c=platform_log[i]
 assert(c.x==(seg.left+seg.right)/2 and c.w==seg.right-seg.left and c.y==seg.y)
 assert(seg.right<=opening.x-opening.width/2+0.001 or seg.left>=opening.x+opening.width/2-0.001,
  'a floor segment covered the authored drop opening')
end
assert(out.room.line_count==#jcol.floor_segments+#jcol.platforms+#jcol.lines)
print('physical: downward-only bottom drop, open gap and distinct upper socket passed')
''')

    def test_allocation_and_placement_refusal_roll_back_destination(self):
        self.run_lua(r'''
reset_logs()
local view=manifest(42)
local rr=RR.new(gd,Rooms,{max_total_lines=32})
local src_out=commit_room(rr,view.nodes[view.start])
local src=rr:active_room()
local src_lines=records_live()
local exit=view.nodes[view.start].exits[1]
local dest=view.nodes[exit.to]
reset_logs();fail_platform=1
local tx=assert(rr:begin(dest,{from=src,exit=exit}))
local ok,why=drive(rr,tx)
assert(not ok and tostring(why):find('refused',1,true),'allocation refusal not reported: '..tostring(why))
assert(records_live()==src_lines,'refused destination left collision behind')
assert(rr:view_active().room_id==view.start and rr:pending()==nil)
fail_platform=nil
local out=commit_room(rr,dest,src,exit)
assert(out.room_id==dest.id)
-- a refused visual instance also rolls back the collision already built for it
local rr3=RR.new(gd,Rooms,{max_total_lines=32})
local s3_out=commit_room(rr3,view.nodes[view.start])
local s3=rr3:active_room()
local s3_lines=records_live()
local e3=view.nodes[view.start].exits[1]
local tx3=assert(rr3:begin(view.nodes[e3.to],{from=s3,exit=e3}))
fail_spawn=spawn_calls+1
local ok3,why3=drive(rr3,tx3)
assert(not ok3 and tostring(why3):find('refused',1,true),'visual refusal not reported: '..tostring(why3))
assert(records_live()==s3_lines,'visual refusal left destination collision behind')
assert(rr3:view_active().room_id==view.start)
fail_spawn=nil
assert(commit_room(rr3,view.nodes[e3.to],s3,e3).room_id==view.nodes[e3.to].id)
-- a refused placement fails the transaction and keeps the source
local rr2=RR.new(gd,Rooms,{max_total_lines=32})
local s2_out=commit_room(rr2,view.nodes[view.start])
local s2=rr2:active_room()
local e2=view.nodes[view.start].exits[1]
local src2_lines=records_live()
local tx2=assert(rr2:begin(view.nodes[e2.to],{from=s2,exit=e2}))
assert(drive(rr2,tx2))
refuse_teleport_port=1
local placed,pwhy=rr2:place(tx2,{{port=1,x=0,y=0}})
assert(not placed and tostring(pwhy):find('respawning',1,true))
refuse_teleport_port=nil
assert(rr2:rollback(tx2))
assert(rr2:view_active().room_id==view.start and records_live()==src2_lines)
print('physical: allocation and placement refusal roll back destination, source intact passed')
''')

    def test_partial_cleanup_retry_preserves_ownership(self):
        self.run_lua(r'''
reset_logs()
local view=manifest(42)
local rr=RR.new(gd,Rooms,{max_total_lines=32})
local src_out=commit_room(rr,view.nodes[view.start])
local src=rr:active_room()
local src_lines=records_live()
local exit=view.nodes[view.start].exits[1]
local dest=view.nodes[exit.to]
local tx=assert(rr:begin(dest,{from=src,exit=exit}))
assert(drive(rr,tx))
local handles={}
for _,entry in ipairs(tx.dest.handles) do handles[#handles+1]=entry.handle;refuse_remove[entry.handle]=true end
assert(#handles>0)
local live=records_live()
local ok,why=rr:rollback(tx)
assert(not ok and tostring(why):find('refused',1,true))
assert(records_live()==live,'refused destination handles must stay owned')
assert(rr:view_active().room_id==view.start)
for _,h in ipairs(handles) do refuse_remove[h]=nil end
assert(rr:rollback(tx))
assert(records_live()==src_lines,'retry did not free the destination')
-- a refused source teardown is reported, kept owned and retried
refuse_remove[src.handles[1].handle]=true
local out=commit_room(rr,dest,src,exit)
assert(out.released==false and rr:pending() and #rr:pending().handles>0)
assert(rr:begin(dest,{from=rr:active_room(),exit=exit})==nil,'transition started with outstanding cleanup')
refuse_remove[src.handles[1].handle]=nil
assert(rr:flush())
assert(rr:pending()==nil)
print('physical: partial cleanup retry preserves and then frees ownership passed')
''')

    def test_isolation_interruption_bounded_dual_residency_and_budget(self):
        self.run_lua(r'''
reset_logs()
local view=manifest(42)
local rr=RR.new(gd,Rooms,{max_total_lines=32})
local src_out=commit_room(rr,view.nodes[view.start])
local src=rr:active_room()
local start_lines=records_live()
local exit=view.nodes[view.start].exits[1]
local dest=view.nodes[exit.to]
local tx=assert(rr:begin(dest,{from=src,exit=exit}))
local st=rr:step(tx)
assert(st=='loading' or st=='ready')
isolation=false
local bad,why=rr:step(tx)
assert(bad==nil and tostring(why):find('isolation',1,true),'lost isolation was not detected')
assert(rr:view_active().room_id==view.start and records_live()==start_lines)
isolation=true
local tx2=assert(rr:begin(dest,{from=src,exit=exit}))
assert(drive(rr,tx2))
local dcol=assert(Rooms.collision(dest))
local dobj=#dcol.floor_segments+#dcol.platforms+#dcol.lines
assert(records_live()==start_lines+dobj,'dual residency did not hold both rooms')
assert(records_live()<=32,'dual residency exceeded the bound')
assert(assert(rr:commit(tx2)))
assert(rr:total()==dobj and records_live()==dobj,'commit did not release the source')
local rr2=RR.new(gd,Rooms,{max_total_lines=start_lines})
local s2_out=commit_room(rr2,view.nodes[view.start])
local s2=rr2:active_room()
assert(rr2:begin(dest,{from=s2,exit=exit})==nil,'total line budget was bypassed')
assert(rr2:total()==start_lines)
print('physical: isolation interruption, bounded dual residency and total budget passed')
''')

    def test_placement_capture_partial_failure_and_save_refusal_rollback(self):
        self.run_lua(r'''
reset_logs()
local view=manifest(42)
local rr=RR.new(gd,Rooms,{max_total_lines=32})
local src_out=commit_room(rr,view.nodes[view.start])
local src=rr:active_room()
local exit=view.nodes[view.start].exits[1]
local dest=view.nodes[exit.to]
local o1x,o1y,o2x,o2y=players[1].x,players[1].y,players[2].x,players[2].y
-- explicit false from the injected teleport is a failure; first fighter restored
local tx=assert(rr:begin(dest,{from=src,exit=exit}))
assert(drive(rr,tx))
false_teleport_port=2
local placed,pwhy=rr:place(tx,{{port=1,x=1,y=1},{port=2,x=2,y=2}})
assert(not placed and tostring(pwhy):find('refused',1,true),'explicit false not treated as failure: '..tostring(pwhy))
assert(players[1].x==o1x and players[1].y==o1y,'first fighter not restored')
assert(players[2].x==o2x and players[2].y==o2y)
false_teleport_port=nil
assert(rr:rollback(tx))
-- a throwing teleport also fails and restores
local tx2=assert(rr:begin(dest,{from=rr:active_room(),exit=exit}))
assert(drive(rr,tx2))
refuse_teleport_port=1
local p2,w2=rr:place(tx2,{{port=1,x=9,y=9},{port=2,x=8,y=8}})
assert(not p2 and tostring(w2):find('respawning',1,true))
assert(players[1].x==o1x and players[2].x==o2x)
refuse_teleport_port=nil
assert(rr:rollback(tx2))
-- save refused after all moved: rollback restores every fighter, retrying a refusal
local tx3=assert(rr:begin(dest,{from=rr:active_room(),exit=exit}))
assert(drive(rr,tx3))
assert(rr:place(tx3,{{port=1,x=5,y=5},{port=2,x=6,y=6}}))
assert(players[1].x==5 and players[2].x==6)
refuse_teleport_port=1
local ok,why=rr:rollback(tx3)
assert(not ok and tostring(why):find('restore refused',1,true),'refused restore was not retained: '..tostring(why))
assert(players[1].x==5,'a refused restore must not drop the fighter')
assert(players[2].x==o2x and players[2].y==o2y,'the later fighter was not restored first')
refuse_teleport_port=nil
assert(rr:rollback(tx3))
assert(players[1].x==o1x and players[1].y==o1y and players[2].x==o2x and players[2].y==o2y)
assert(rr:view_active().room_id==view.start)
print('physical: placement capture, partial-failure restore and save-refusal rollback passed')
''')

    def test_begin_rejects_foreign_source_and_forged_exit(self):
        self.run_lua(r'''
reset_logs()
local view=manifest(42)
local rr=RR.new(gd,Rooms,{max_total_lines=32})
local out=commit_room(rr,view.nodes[view.start])
local src=rr:active_room()
local exit=view.nodes[view.start].exits[1]
local dest=view.nodes[exit.to]
-- a token owned by another module instance is foreign
local rr2=RR.new(gd,Rooms,{max_total_lines=32})
commit_room(rr2,view.nodes[view.start])
assert(rr:begin(dest,{from=rr2:active_room(),exit=exit})==nil,'foreign source accepted')
-- an arbitrary/inactive token is refused
assert(rr:begin(dest,{from={node=view.nodes[view.start],handles={}},exit=exit})==nil,'inactive source accepted')
-- omitting the source while a room is active is refused
assert(rr:begin(dest)==nil,'missing source accepted with an active room')
-- a forged exit with a different target cannot bypass direction/target checks
local forged=copy(exit);forged.to='not_a_room'
assert(rr:begin(dest,{from=src,exit=forged})==nil,'forged exit target accepted')
-- a canonical exit must aim at the destination node passed in
assert(rr:begin(view.nodes[view.start],{from=src,exit=exit})==nil,'mismatched destination accepted')
-- the genuine canonical exit still opens
local tx=assert(rr:begin(dest,{from=src,exit=exit}))
assert(rr:rollback(tx))
print('physical: begin rejects foreign source and forged/mismatched exits passed')
''')

    def test_cleanup_release_reset_lifecycle(self):
        self.run_lua(r'''
reset_logs()
local view=manifest(42)
-- active room exit, idempotent and free of double frees
local rr=RR.new(gd,Rooms,{max_total_lines=32})
assert(commit_room(rr,view.nodes[view.start]))
assert(rr:total()>0 and records_live()>0)
assert(rr:cleanup())
assert(rr:active_room()==nil and rr:total()==0 and records_live()==0)
assert(rr:release())
assert(rr:total()==0 and records_live()==0)
-- interruption while loading
local rr2=RR.new(gd,Rooms,{max_total_lines=32})
commit_room(rr2,view.nodes[view.start])
local e2=view.nodes[view.start].exits[1]
local tx2=assert(rr2:begin(view.nodes[e2.to],{from=rr2:active_room(),exit=e2}))
local st2=rr2:step(tx2)
assert(st2=='loading' or st2=='ready')
assert(rr2:cleanup())
assert(rr2:active_room()==nil and records_live()==0 and rr2:total()==0)
-- interruption while placed: cleanup restores the moved fighter
local rr3=RR.new(gd,Rooms,{max_total_lines=32})
commit_room(rr3,view.nodes[view.start])
local e3=view.nodes[view.start].exits[1]
local o1x,o1y=players[1].x,players[1].y
local tx3=assert(rr3:begin(view.nodes[e3.to],{from=rr3:active_room(),exit=e3}))
assert(drive(rr3,tx3))
assert(rr3:place(tx3,{{port=1,x=7,y=7}}))
assert(players[1].x==7)
assert(rr3:cleanup())
assert(players[1].x==o1x and players[1].y==o1y,'cleanup did not restore placements')
assert(records_live()==0 and rr3:total()==0)
-- refused removal retains the active room, then retries to completion
local rr4=RR.new(gd,Rooms,{max_total_lines=32})
commit_room(rr4,view.nodes[view.start])
local h=rr4:active_room().handles[1].handle
refuse_remove[h]=true
local ok,why=rr4:cleanup()
assert(not ok and tostring(why):find('refused',1,true))
assert(records_live()>0 and rr4:total()>0 and rr4:active_room()~=nil,'refused active room was lost')
refuse_remove[h]=nil
assert(rr4:cleanup())
assert(records_live()==0 and rr4:total()==0)
assert(rr4:cleanup())
-- reset may not silently lose live handles
local rr5=RR.new(gd,Rooms,{max_total_lines=32})
commit_room(rr5,view.nodes[view.start])
assert(rr5:reset()==false,'reset dropped live handles without confirmation')
assert(rr5:total()>0 and rr5:active_room()~=nil)
-- simulated real native scene teardown: engine records are gone; reset drops bookkeeping
records,spawns,assets={},{},{}
assert(rr5:reset(true))
assert(rr5:total()==0 and rr5:active_room()==nil and rr5:pending()==nil)
isolation=true
print('physical: cleanup/release/reset lifecycle, refusal retry and no double free passed')
''')

    def test_runtime_consumes_only_admitted_nodes(self):
        self.run_lua(r'''
local top=Top.new(Cat,Enc,Prog,RNG)
local strict=Adapter.new(Cat,Recipes)
local view,why=strict:manifest(top:generate(42))
assert(not view and tostring(why):find('not certified',1,true),
 'uncertified recipes were admitted without the test-only wrapper')
print('physical: runtime consumes only adapter-admitted nodes passed')
''')


if __name__ == '__main__':
    unittest.main()
