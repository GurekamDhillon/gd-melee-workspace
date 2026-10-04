#!/usr/bin/env python3
"""Check real Lua room ownership/plans and source-authored native binary assets."""
import importlib.util
import json
import math
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
import game_source

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = game_source.ROGUELITE
spec = importlib.util.spec_from_file_location('rogue_room_assets', Path(__file__).with_name('room_assets.py'))
assets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assets)


class RoomsTests(unittest.TestCase):
    def test_physical_traversal_slab_projection_and_collision_limits(self):
        self.run_lua(r'''
local n=Traversal.generate(42).nodes.entry
local before=serialize(n);local p=assert(R.plan(n));local c=assert(R.collision(n))
assert(#p.parts==48 and #c.platforms==20 and #c.lines==3 and #c.floor_segments==1)
assert(before==serialize(n),'planner mutated saved physical geometry')
local walls=0
for _,part in ipairs(p.parts) do
 assert(part.background and part.collision==false and part.scale_z==2)
 if part.model=='bf_wall_solid_4m' then
  walls=walls+1;assert(math.abs(part.z-17.68)<.000001)
  assert(math.abs(part.z+2*(-8.84))<.000001,'slab mesh midpoint not on gameplay plane')
 else assert(part.z==0,'floor/portal projection moved') end
end
assert(walls==4);assert(R.enter(s,n));assert(R.clear(s))
local bad=copy(n);bad.room.platforms[1].y=157;assert(not R.collision(bad))
bad=copy(n);bad.physical=nil;assert(not R.collision(bad),'legacy admitted high physical geometry')
bad=copy(n);bad.room.lines[3].x0,bad.room.lines[3].x1=bad.room.lines[3].x1,bad.room.lines[3].x0
assert(not R.collision(bad),'wrong ceiling orientation admitted')
''')
    def test_generated_maze_render_collision_copy_and_directed_walls(self):
        self.run_lua(r'''
local Maze=dofile((arg[1]:gsub('rooms.lua$','maze.lua')))
for seed=1,30 do
 local m=Maze.generate(seed)
 for _,id in ipairs(m.order) do
  local n=m.nodes[id];local before=serialize(n);local c=assert(R.collision(n));local p=assert(R.plan(n))
  assert(before==serialize(n) and serialize(c.lines)==serialize(n.room.lines))
  assert(#c.platforms==7 and #c.lines==6 and #p.parts<=32)
  local platforms,blockers,upper=0,0,0
  for _,part in ipairs(p.parts) do
   assert(part.z==(part.kind=='blocker' and 17.68 or 0) and part.scale_z==2 and part.collision==false and part.background==true)
   if part.kind=='platform' then platforms=platforms+1 end
   if part.kind=='blocker' then blockers=blockers+1;assert(part.scale_x*26==8 and part.scale_y*26==48) end
   if part.kind=='portal' and part.y==54 then upper=upper+1 end
  end
  local expected=0;for _,e in ipairs(n.exits) do if e.side=='top' or e.side=='bottom' then expected=expected+1 end end
  assert(platforms==7 and blockers==2 and upper==expected)
  assert(R.enter(s,n));for _,v in pairs(live) do assert(v.opts.scale_z==2) end
  assert(R.clear(s))
 end
end
local bad=copy(Maze.generate(1).nodes.entry)
bad.room.lines[1].y0,bad.room.lines[1].y1=bad.room.lines[1].y1,bad.room.lines[1].y0
assert(not R.collision(bad),'backwards wall accepted')
''')
    def test_all_plans_preserve_world_projection_with_background_depth(self):
        kit = ROOT / 'menu/out_roguelite/room-kit'
        bounds = {}
        for mesh in kit.glob('*.gxmesh'):
            data = mesh.read_bytes()
            _, _, nv, _, _, _, _, offset, _ = assets.HEADER.unpack_from(data)
            bounds[mesh.stem] = max(struct.unpack_from('>8f', data, offset+i*32)[2] for i in range(nv))
        maxima = '{' + ','.join('["%s"]=%r' % row for row in sorted(bounds.items())) + '}'
        self.run_lua('local forward=' + maxima + r'''
local function check(n)
 local before=serialize(R.collision(n));local p=assert(R.plan(n))
 for _,part in ipairs(p.parts) do
  assert(forward[part.model], 'missing independently decoded mesh bounds')
  assert(part.z==0 and part.background==true and part.collision==false, 'assembly projection/depth policy drift')
 end
 assert(before==serialize(R.collision(n)), 'visual depth changed physics')
 assert(R.enter(s,n))
 for _,instance in pairs(live) do assert(instance.opts.z==0 and instance.opts.background==true and instance.opts.collision==false) end
 assert(R.clear(s))
end
for _,id in ipairs(manifest.order) do check(manifest.nodes[id]) end
for id,t in pairs(C.rooms) do
 local g,r=Recipes.resolve(t)
 check({id=id,template_id=id,recipe=t.recipe,recipe_version=r.version,
  recipe_modules=r.modules or {},room=g,exits={}})
end
''')

    def test_double_scale_preserves_assembly_and_background_depth(self):
        self.run_lua(r'''
local n=copy(manifest.nodes.trail)
n.room.kit={unit=13,grid=26,bay=52,height=52,depth=0}
n.room.exit_anchors={left={x=-104,y=0},right={x=104,y=0}}
n.room.platforms={{x=-44,y=24,width=44,passthrough=true,ledges=false},
 {x=44,y=24,width=44,passthrough=true,ledges=false},
 {x=0,y=48,width=48,passthrough=true,ledges=false}}
local p=assert(R.plan(n));local floors=0
for _,part in ipairs(p.parts) do
 assert(part.z==0 and part.scale_z==2 and part.scale_y==2 and not part.collision and part.background==true)
 if part.kind=='mainfloor' then floors=floors+1;assert(part.scale_x==2) end
 if part.kind=='platform' then assert(part.scale_x*26==44 or part.scale_x*26==48) end
end
assert(floors==5)
local old=copy(n);old.room.floor={left=-65,right=65,y=0}
old.room.kit={unit=6.5,grid=13,bay=26,height=26,depth=0}
old.room.platforms={};old.room.exit_anchors={left={x=-52,y=0},right={x=52,y=0}}
assert(R.plan(old),'older narrow saved snapshot rejected')
local g,r=Recipes.resolve(C.rooms.branch_y)
local recipe={id='double_ascent',template_id='branch_y',recipe=C.rooms.branch_y.recipe,
 recipe_version=r.version,recipe_modules=copy(r.modules),room=copy(g),exits={}}
local dimensions={x=true,y=true,x0=true,y0=true,x1=true,y1=true,left=true,right=true,
 width=true,unit=true,grid=true,bay=true,height=true,depth=true}
local function double(t)
 for k,v in pairs(t) do
  if type(v)=='table' then double(v) elseif dimensions[k] and type(v)=='number' then t[k]=v*2 end
 end
end
double(recipe.room);double(recipe.recipe_modules)
local original=serialize(recipe);local rp=assert(R.plan(recipe));local stairs=0
assert(serialize(recipe)==original and #rp.lines==2)
for _,part in ipairs(rp.parts) do
 assert(part.z==0 and part.scale_z==2 and part.scale_y==2 and part.collision==false and part.background==true)
 if part.model=='bf_stairs_4m_rise2m' then stairs=stairs+1;assert(part.x==-78 and part.y==0) end
end
assert(stairs==1)
''')
    def test_incremental_preload_yields_caches_and_stops_permanent_failure(self):
        self.run_lua(r'''
for i=1,6 do
 local prior=load_serial;assert(R.preload_step(s)==false)
 assert(load_serial==prior+1 and count(live)==0,'preload must load exactly one and never spawn')
end
assert(R.preload_step(s)==true and load_serial==6)
assert(R.enter(s,manifest.nodes.trail));assert(load_serial==6,'room reloaded cached kit')
assert(R.release(s));R.reset(s)
fail_load=load_serial+1
assert(R.preload_step(s)==nil)
local prior=load_serial
assert(R.preload_step(s)==nil and load_serial==prior,'permanent failure was retried')
R.reset(s);fail_load=nil;assert(R.preload_step(s)==false)
''')
    def test_recipe_rooms_place_all_sockets_segment_drops_and_cleanup(self):
        self.run_lua(r'''
local function node_for(id,t)
 local g,r=Recipes.resolve(t)
 local node={id='generated_'..id,template_id=id,recipe=t.recipe,recipe_modules=r.modules or {},
  recipe_version=r.version,theme='frost',kind=t.role,room=copy(g),exits={}}
 for _,socket in ipairs(t.sockets) do
  node.room.arrivals[socket.id]=copy(g.arrivals[socket.side])
  node.exits[#node.exits+1]={socket=socket.id,side=socket.side,anchor=copy(g.exit_anchors[socket.side]),to='other'}
 end
 return node
end
for id,t in pairs(C.rooms) do
 local n=node_for(id,t);local original=serialize(n);local p=assert(R.plan(n))
 assert(serialize(n)==original and #p.parts<=28)
 local c=assert(R.collision(n));assert(#c.floor_segments+#c.platforms+#c.lines<=16)
 for _,e in ipairs(n.exits) do
  local a=assert(R.anchor(n,e));local arrival=assert(R.arrival(n,e.socket))
  assert(a.x==n.room.exit_anchors[e.side].x and arrival.facing)
  if e.side=='bottom' then
   assert(a.drop and a.y<0 and #c.floor_segments==2)
   assert(c.floor_segments[1].right==-6.5 and c.floor_segments[2].left==6.5)
   for _,f in ipairs(c.floor_segments) do assert(arrival.x<f.left or arrival.x>f.right or arrival.y==f.y) end
  end
 end
 if n.room.exit_anchors.top then
  local stairs,ramp,upper,door=0,0,0,0
  for _,part in ipairs(p.parts) do
   if part.model=='bf_stairs_4m_rise2m' then stairs=stairs+1;assert(part.x==-39 and part.y==0) end
   if part.model=='bf_ramp_4m_rise2m' then ramp=ramp+1;assert(part.x==13 and part.y==13) end
   if part.model=='bf_floor_4m' and part.y==26 then upper=upper+1;assert(part.x==39) end
   if part.model=='bf_wall_doorway_4m' and part.y==26 then door=door+1;assert(part.x==39 and part.scale_x==-1) end
  end
  assert(stairs==1 and ramp==1 and upper==1 and door==1 and #c.lines==2)
 end
 local prior=load_serial
 while R.preload_step(s,n)==false do assert(load_serial==prior+1);prior=load_serial end
 local loaded=load_serial;assert(R.enter(s,n));assert(loaded==load_serial,'preload missed recipe asset')
 assert(R.clear(s) and count(live)==0)
end
assert(count(refs)==10 and R.release(s) and count(refs)==0)
local bad=node_for('bad',C.rooms.junction_cross)
bad.room.floor.openings[1].width=26;assert(not R.plan(bad),'off-grid visual opening accepted')
bad=node_for('bad',C.rooms.branch_y);bad.room.lines[1].x1=0/0;assert(not R.plan(bad))
bad=node_for('bad',C.rooms.branch_y);bad.room.platforms[1].x=100;assert(not R.plan(bad))
bad=node_for('bad',C.rooms.branch_y);bad.recipe_modules={};assert(not R.plan(bad))
''')

    def test_recipe_slopes_and_opening_match_independent_exporter_sidecars(self):
        lua = shutil.which('lua') or shutil.which('lua5.4')
        program = r'''
local C=dofile(arg[1]);local Recipes=dofile(arg[2])
local g,r=Recipes.resolve(C.rooms.branch_y)
for _,line in ipairs(g.lines) do print('slope',line.part,line.x0,line.y0,line.x1,line.y1) end
for _,module in ipairs(r.modules) do
 if module.part~='bf_wall_doorway_4m' then print('module',module.part,module.x,module.y) end
end
local d=Recipes.resolve(C.rooms.junction_cross)
for _,o in ipairs(d.floor.openings) do print('opening',o.x,o.width) end
'''
        result = subprocess.run([lua, '-', str(RUNTIME / 'room_catalogue.lua'), str(RUNTIME / 'room_recipes.lua')],
                                input=program, text=True, capture_output=True, check=True)
        source = RUNTIME.parent / 'bf_interior_room/models'
        rows = [row.split() for row in result.stdout.splitlines()]
        modules = {row[1]: tuple(map(float, row[2:])) for row in rows if row[0] == 'module'}
        for row in rows:
            if row[0] == 'slope':
                name = row[1]
                sidecar = json.loads((source / (name+'.coll.json')).read_text())
                line = sidecar['lines'][0]
                x,y = modules[name]
                self.assertEqual(tuple(map(float,row[2:])), (x+line[1],y+line[2],x+line[3],y+line[4]))
            elif row[0] == 'opening':
                center,width = map(float,row[1:])
                lines = json.loads((source / 'bf_floor_opening_4m.coll.json').read_text())['lines']
                self.assertEqual((center-width/2,center+width/2),(lines[0][3],lines[1][1]))
        self.assertIn('bf_floor_4m', modules, 'upper doorway needs solid authored floor')
        self.assertNotIn('bf_floor_opening_4m', modules)
        exported = ROOT / 'menu/out_roguelite/room-kit'
        for name in modules:
            sidecar = json.loads((source / (name+'.coll.json')).read_text())
            self.assertEqual(sidecar, json.loads((exported / (name+'.coll.json')).read_text()),
                             'installer input drifted from reviewed BF sidecar')
            data = (exported / (name+'.gxmesh')).read_bytes()
            _,_,nv,_,_,_,_,offset,_ = assets.HEADER.unpack_from(data)
            points = [struct.unpack_from('>8f',data,offset+i*32)[:3] for i in range(nv)]
            lo = [min(v[i] for v in points) for i in range(3)]
            hi = [max(v[i] for v in points) for i in range(3)]
            for line in sidecar['lines']:
                for x,y in ((line[1],line[2]),(line[3],line[4])):
                    self.assertTrue(lo[0]-.001<=x<=hi[0]+.001 and lo[1]-.001<=y<=hi[1]+.001,
                                    f'{name} collider endpoint lies outside actual visual bounds')

    def test_exported_bf_wall_and_door_native_dimensions_and_depth(self):
        kit = ROOT / 'menu/out_roguelite/room-kit'
        if not (kit / 'bf_wall_doorway_4m.gxmesh').exists():
            self.skipTest('Blender BF exports not present; source and collision tests still run')
        for name in ('bf_wall_solid_4m', 'bf_wall_doorway_4m'):
            data = (kit / (name+'.gxmesh')).read_bytes()
            magic, version, vertices, indices, width, depth, height, offset, ioffset = assets.HEADER.unpack_from(data)
            self.assertEqual((magic,version), (b'GXMS',2))
            self.assertLessEqual(ioffset+indices*2, len(data))
            points = [struct.unpack_from('>8f',data,offset+i*32)[:3] for i in range(vertices)]
            lo = [min(p[a] for p in points) for a in range(3)]
            hi = [max(p[a] for p in points) for a in range(3)]
            self.assertAlmostEqual(lo[0], -13)
            self.assertAlmostEqual(hi[0], 13)
            self.assertAlmostEqual(hi[1], 26)
            self.assertLess(hi[2], -7, 'kit already includes depth behind fighters')
            self.assertGreaterEqual(lo[1], -.27, 'door sill is the only below-floor trim')

    def run_lua(self, body):
        lua = shutil.which('lua') or shutil.which('lua5.4')
        self.assertIsNotNone(lua, 'Real Lua required')
        prelude = r'''
local Traversal=dofile(arg[1]:gsub('rooms.lua$','traversal.lua'))
local env=setmetatable({Traversal=Traversal},{__index=_G})
local R=assert(loadfile(arg[1],'t',env))();local D=assert(loadfile(arg[2]))()
local C=dofile(arg[3]);local Recipes=dofile(arg[4])
local s=R.new();local manifest=D.generate(123)
local live,refs,loads,names={},{},{},{}
local serial,load_serial,spawn_calls=0,0,0
local fail_load,fail_spawn,throw_load,throw_spawn,refuse_clear,throw_release
local function count(t) local n=0 for _ in pairs(t) do n=n+1 end return n end
local function copy(t) local o={} for k,v in pairs(t) do o[k]=type(v)=='table' and copy(v) or v end return o end
local function serialize(t)
 if type(t)~='table' then return type(t)..':'..tostring(t) end
 local k={} for key in pairs(t) do k[#k+1]=key end
 table.sort(k,function(a,b) return tostring(a)<tostring(b) end)
 local o={} for _,key in ipairs(k) do o[#o+1]=serialize(key)..'='..serialize(t[key]) end
 return '{'..table.concat(o,',')..'}'
end
gd={model_load=function(name)
 load_serial=load_serial+1
 if throw_load or load_serial==fail_load then error('load API restricted') end
 serial=serial+1;refs[serial]=1;names[serial]=name;loads[name]=(loads[name] or 0)+1;return serial
end,model_spawn=function(asset,opts)
 spawn_calls=spawn_calls+1
 if throw_spawn then error('spawn API restricted') end
 if spawn_calls==fail_spawn then return nil,'instance allocation refused' end
 assert(refs[asset]==1 and opts.collision==false)
 for _,axis in ipairs({'scale_x','scale_y','scale_z'}) do
  assert(math.abs(opts[axis])>=.001 and math.abs(opts[axis])<=100,'native model scale range')
 end
 serial=serial+1;live[serial]={asset=asset,opts=copy(opts)};return serial
end,model_despawn=function(h)
 if refuse_clear then return false end
 if not live[h] then return false end
 live[h]=nil;return true
end,model_get=function(h) return live[h] end,model_release=function(asset)
 if throw_release then error('release API restricted') end
 assert(refs[asset]==1)
 for _,inst in pairs(live) do assert(inst.asset~=asset,'released with live instance') end
 refs[asset]=nil -- Actual native API returns no values, not true.
end}
'''
        result = subprocess.run([lua, '-', str(RUNTIME / 'rooms.lua'), str(RUNTIME / 'dungeon.lua'), str(RUNTIME / 'room_catalogue.lua'), str(RUNTIME / 'room_recipes.lua')],
                                input=prelude + body, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_seeded_plans_both_branches_physics_alignment_and_bounds(self):
        self.run_lua(r'''
local fingerprints={}
for seed=1,300 do
 local m=D.generate(seed)
 for _,id in ipairs(m.order) do
  local node=m.nodes[id];local factor=node.room.kit.unit/6.5;local rear=0
  local before=serialize(node);local p=assert(R.plan(node))
  assert(serialize(p)==serialize(assert(R.plan(D.generate(seed).nodes[id]))))
  assert(before==serialize(node),'plan mutated physical route')
  assert(#p.parts<=48 and #p.platforms==#node.room.platforms)
  local visual_platforms,portals=0,0
  for _,part in ipairs(p.parts) do
   assert(part.collision==false and part.scale_y>0 and part.scale_z==factor)
   assert(part.x>=-130 and part.x<=130 and part.y>=0 and part.y<=60)
   assert(part.model:match('^bf_'))
   if part.kind=='platform' then
    visual_platforms=visual_platforms+1;local physical=node.room.platforms[visual_platforms]
    assert(part.x==physical.x and part.y==physical.y and part.scale_x*26==physical.width)
    assert(p.platforms[visual_platforms].visual_top==physical.y)
   elseif part.kind~='mainfloor' and part.kind~='trim' then assert(part.z==rear) end
   if part.kind=='portal' then
    portals=portals+1;local e=node.exits[portals];local a=node.room.exit_anchors[e.side]
    assert(part.x==a.x and part.y==a.y)
    assert(part.scale_x==factor and part.scale_y==factor and part.z==rear)
   end
  end
  assert(visual_platforms==#node.room.platforms and portals==#node.exits)
  local bays,wall_at,door_at={},{},{}
  for _,part in ipairs(p.parts) do
   if part.kind=='mainfloor' then
    assert(part.scale_x==factor and part.scale_y==factor and part.x%(13*factor)==0)
    bays[#bays+1]=part.x
   elseif part.kind=='wall' then wall_at[part.x]=true
   elseif part.kind=='portal' then door_at[part.x]=true
   elseif part.kind=='post' then assert(part.x%(13*factor)==0 and part.scale_x==factor and part.scale_y==factor) end
  end
  assert(#bays==10/factor)
  table.sort(bays);local edge=130-13*factor;assert(bays[1]==-edge and bays[#bays]==edge)
  for j=2,#bays do assert(bays[j]-bays[j-1]==26*factor) end
  for x in pairs(door_at) do assert(not wall_at[x],'solid wall behind opening') end
  assert(portals==0 or (door_at[-edge] or door_at[edge]))
  if node.kind=='arena' then assert(p.theme==(node.encounter=='pressure' and 'fire' or 'frost')) end
  if seed==1 then fingerprints[id]=serialize(p) end
 end
 assert(assert(R.plan(m.nodes.arena_a)).theme~=assert(R.plan(m.nodes.arena_b)).theme)
end
assert(fingerprints.trail~=fingerprints.approach and fingerprints.arena_a~=fingerprints.arena_b)
local bad=copy(manifest.nodes.trail);bad.room.platforms[1].x=150;assert(not R.plan(bad))
bad=copy(manifest.nodes.trail);bad.room.platforms[1].width=0/0;assert(not R.plan(bad))
bad=copy(manifest.nodes.trail);bad.room.exit_anchors.left.x=-65;assert(not R.plan(bad))
bad=copy(manifest.nodes.trail);bad.exits[2].side='left';assert(not R.plan(bad))
bad=copy(manifest.nodes.trail);bad.room.kit.unit=5;assert(not R.plan(bad))
bad=copy(manifest.nodes.trail);bad.room.exit_anchors.left.x=-55;assert(not R.plan(bad))
assert(not R.plan({id='new',kind='arena'}))
''')

    def test_room_changes_cache_cleanup_and_no_leaks(self):
        self.run_lua(r'''
for seed=1,20 do
 local m=D.generate(seed)
 for _,id in ipairs(m.order) do
  local ok,n=R.enter(s,m.nodes[id]);assert(ok,n)
  local v=R.view(s);assert(v.instances==n and count(live)==n and v.assets<=R.max_assets)
  assert(v.room_id==id and v.theme==assert(R.plan(m.nodes[id])).theme)
 end
end
for name,n in pairs(loads) do assert(n==1,'model loaded more than once: '..name) end
assert(R.clear(s));assert(count(live)==0 and R.view(s).instances==0)
assert(count(refs)>0) -- retained immutable references are intentionally reused per scene
assert(R.release(s));assert(count(live)==0 and count(refs)==0 and R.view(s).assets==0)
assert(R.release(s));assert(R.clear(s))
''')

    def test_partial_allocation_failures_cleanup_real_handles(self):
        self.run_lua(r'''
local total=#assert(R.plan(manifest.nodes.arena_b)).parts
for failure=1,total do
 fail_spawn=spawn_calls+failure
 local ok,why=R.enter(s,manifest.nodes.arena_b)
 assert(not ok and why:find('allocation refused',1,true))
 assert(count(live)==0 and R.view(s).instances==0 and not R.view(s).room_id)
 fail_spawn=nil;assert(R.enter(s,manifest.nodes.trail));assert(R.clear(s))
end
assert(R.release(s));assert(count(refs)==0)
-- Every load failure point in a new scene is recoverable, with no leaked ownership.
local unique={};for _,p in ipairs(assert(R.plan(manifest.nodes.arena_a)).parts) do unique[p.model]=true end
for failure=1,count(unique) do
 fail_load=load_serial+failure
 local ok,why=R.enter(s,manifest.nodes.arena_a)
 assert(not ok and why:find('load API restricted',1,true))
 assert(count(live)==0)
 fail_load=nil;assert(R.release(s));assert(count(refs)==0)
end
throw_load=true;assert(not R.enter(s,manifest.nodes.rest));assert(count(live)==0)
throw_load=nil;throw_spawn=true;assert(not R.enter(s,manifest.nodes.rest));assert(count(live)==0)
throw_spawn=nil;assert(R.release(s));assert(count(refs)==0)
''')

    def test_restricted_cleanup_retains_ownership_and_teardown_reset(self):
        self.run_lua(r'''
assert(R.enter(s,manifest.nodes.trail));local n=count(live)
refuse_clear=true;local ok,why=R.clear(s);assert(not ok and R.view(s).instances==n)
assert(not R.enter(s,manifest.nodes.rest));assert(count(live)==n)
assert(not R.release(s));assert(count(refs)>0)
refuse_clear=nil;assert(R.clear(s));assert(count(live)==0)
throw_release=true;assert(not R.release(s));assert(count(refs)==R.view(s).assets)
throw_release=nil;assert(R.release(s));assert(count(refs)==0)
assert(R.enter(s,manifest.nodes.rest))
local v=R.view(s);v.handles[1]=-99;assert(R.view(s).handles[1]>0)
-- Native scene teardown removes instances/assets first; reset then makes no API calls.
live={};refs={};gd=nil;R.reset(s)
assert(R.view(s).instances==0 and R.view(s).assets==0 and not R.view(s).room_id)
assert(R.clear(s));assert(R.release(s));assert(not R.enter(s,manifest.nodes.entry))
''')

    def test_mesh_native_format_normals_bounds_and_empty_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = assets.build(tmp)
            root = Path(tmp) / 'models'
            self.assertEqual(len(manifest['models']), 21)
            triangles = {}
            for name, meta in manifest['models'].items():
                data = (root / f'{name}.gxmesh').read_bytes()
                magic, version, nv, ni, width, depth, height, voff, ioff = assets.HEADER.unpack_from(data)
                self.assertEqual((magic, version, voff, ioff), (b'GXMS', 2, 36, 36+nv*32))
                self.assertEqual(len(data), ioff+ni*2)
                self.assertEqual(ni % 3, 0)
                self.assertTrue(3 <= nv <= 65535 and 3 <= ni <= 65535)
                vertices = [struct.unpack_from('>8f', data, voff+i*32) for i in range(nv)]
                indices = struct.unpack_from(f'>{ni}H', data, ioff)
                self.assertTrue(all(i < nv for i in indices))
                self.assertTrue(all(math.isfinite(v) for row in vertices for v in row))
                for row in vertices:
                    self.assertAlmostEqual(sum(v*v for v in row[5:]), 1, places=5)
                    self.assertTrue(0 < row[3] < 1 and row[4] == .5)
                lo = [min(v[i] for v in vertices) for i in range(3)]
                hi = [max(v[i] for v in vertices) for i in range(3)]
                for actual, expected in zip((width, depth, height), (hi[i]-lo[i] for i in (0,2,1))):
                    self.assertAlmostEqual(actual, expected, places=5)
                for actual, expected in zip(lo+hi, meta['bounds']['min']+meta['bounds']['max']):
                    self.assertAlmostEqual(actual, expected, places=5)
                if meta['type'] == 'platform':
                    self.assertEqual((lo[0],hi[0],hi[1],lo[1]), (-.5,.5,0,-1))
                sidecar = json.loads((root / f'{name}.coll.json').read_text())
                self.assertEqual(sidecar, {'version': 1, 'atlas': f'rogue_room_palette_{meta["theme"]}', 'lines': []})
                self.assertNotIn('alpha', sidecar)
                triangles[meta['type']] = ni//3
            self.assertLessEqual(max(triangles.values())*20, 2000)

    def test_atlas_rgba8_layout_and_opaque_source_pixels(self):
        for theme in assets.THEMES:
            data = assets.atlas_bytes(theme)
            header = struct.unpack_from('>11I', data)
            self.assertEqual(header, (0x47585458,1,6,32,4,0xFFFFFFFF,0,512,0,64,0))
            self.assertEqual(len(data), 576)
            for i, base in enumerate(assets.BASE_PALETTE):
                color = assets.ACCENTS[theme] if i == 4 else base
                tile = data[64+i*64:128+i*64]
                self.assertEqual(tile[:32], bytes((255,color[0]))*16)
                self.assertEqual(tile[32:], bytes((color[1],color[2]))*16)

    def test_actual_native_gxtx_parser_and_model_mip_validation(self):
        # Compile the unchanged parser/level validator from renderer source, not
        # a Python translation of the authoring header. This runs no game/build.
        platform = game_source.PLATFORM
        runtime = (platform / 'gw_runtime.c').read_text()
        script = (platform / 'gw_script.c').read_text()
        def function(source, signature):
            start = source.index(signature)
            brace = source.index('{', start)
            depth = 1
            end = brace + 1
            while depth:
                depth += (source[end] == '{') - (source[end] == '}')
                end += 1
            return source[start:end]
        typedef_start = runtime.index('typedef struct {', runtime.index('#define GW_GXTEX_MAGIC'))
        typedef_end = runtime.index('static GwGxTex *gw_gxtex_get', typedef_start)
        program = ('#include <stdint.h>\n#include <stdio.h>\n#include <stdlib.h>\n'
                   '#include <string.h>\n#define GW_GXTEX_MAX 8\n'
                   '#define GW_GXTEX_MAGIC 0x47585458u\n#define GW_GXTEX_VERSION 1\n'
                   '#define gw_log(...) ((void)0)\n' + runtime[typedef_start:typedef_end]
                   + function(runtime, 'static uint32_t gw_gxtex_be32(')
                   + function(runtime, 'static int gw_gxtex_open_dir(const char *dir, const char *name, int quiet) {')
                   + function(script, 'static int gs_stage_tex_levels(')
                   + '\nint main(int argc,char **argv){int h=gw_gxtex_open_dir(argv[1],argv[2],0);'
                     'if(h<0)return 2;GwGxTex*t=&gw_gxtex[h];'
                     'if(t->format!=6||t->width<4||t->height<4||t->width>4096||t->height>4096)return 3;'
                     'return gs_stage_tex_levels(t->width,t->height,t->image_size)<1?4:0;}\n')
        cc = shutil.which('cc') or shutil.which('clang')
        if not cc and (ROOT/'_toolchains/llvm/bin/clang.exe').exists():
            cc = str(ROOT/'_toolchains/llvm/bin/clang.exe')
        self.assertIsNotNone(cc, 'C compiler required for native format regression')
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path / 'check.c').write_text(program)
            executable = path / ('check.exe' if __import__('os').name=='nt' else 'check')
            subprocess.run([cc, '-std=c99', str(path/'check.c'), '-o', str(executable)], check=True, capture_output=True)
            for theme in assets.THEMES:
                (path / (theme+'.gxtex')).write_bytes(assets.atlas_bytes(theme))
                self.assertEqual(subprocess.run([str(executable),tmp,theme]).returncode, 0)
            # Original swapped size/offset fits within the file, but violates the
            # model loader's complete 4x4-tiled level requirement (64 != 512).
            broken = bytearray(assets.atlas_bytes('cobalt'))
            struct.pack_into('>I', broken, 28, 64)
            struct.pack_into('>I', broken, 36, 512)
            (path/'broken.gxtex').write_bytes(broken)
            self.assertEqual(subprocess.run([str(executable),tmp,'broken']).returncode, 4)

    def test_actual_mesh_bounds_match_lua_plans_and_native_budgets(self):
        lua = shutil.which('lua') or shutil.which('lua5.4')
        self.assertIsNotNone(lua)
        program = r'''
local R=dofile(arg[1]);local D=dofile(arg[2])
for seed=1,20 do for _,node in pairs(D.generate(seed).nodes) do
 local p=assert(R.plan(node))
 for _,v in ipairs(p.parts) do
  print(seed,node.id,v.model,v.x,v.y,v.z,v.scale_x,v.scale_y,v.scale_z)
 end
end end
'''
        result = subprocess.run([lua, '-', str(RUNTIME / 'rooms.lua'), str(RUNTIME / 'dungeon.lua')],
                                input=program, text=True, capture_output=True, check=True, timeout=30)
        # The committed BF sidecar is authored by the Blender exporter and
        # establishes floor endpoints independently of the room-plan code.
        sidecar = json.loads((RUNTIME.parent / 'bf_interior_room/models/bf_floor_4m.coll.json').read_text())
        floor = sidecar['lines'][0]
        # Sidecars use object fields; native parser also supports this schema.
        if isinstance(floor, dict):
            lo, hi = floor['x0'], floor['x1']
        else:
            lo, hi = floor[1], floor[3]
        self.assertAlmostEqual(hi-lo, 26)
        coverage = {}
        models = set()
        for row in result.stdout.splitlines():
            seed, node, model, *transform = row.split()
            x,y,z,sx,sy,sz = map(float, transform)
            models.add(model)
            self.assertTrue(model.startswith('bf_'))
            self.assertNotIn('ramp', model)
            self.assertNotIn('stairs', model)
            if model == 'bf_floor_4m' and y == 0:
                coverage.setdefault((seed,node), []).append((x+lo*sx,x+hi*sx))
        self.assertEqual(len(models), 6)
        for spans in coverage.values():
            spans.sort()
            self.assertAlmostEqual(spans[0][0], -130)
            self.assertAlmostEqual(spans[-1][1], 130)
            for first, second in zip(spans,spans[1:]):
                self.assertAlmostEqual(first[1], second[0], msg='main floor visual gap')

    def test_source_only_reproducibility_and_non_owned_files_preserved(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            self.assertEqual(assets.build(a), assets.build(b))
            ar, br = Path(a) / 'models', Path(b) / 'models'
            original = {p.name: p.read_bytes() for p in ar.iterdir()}
            self.assertEqual(original, {p.name: p.read_bytes() for p in br.iterdir()})
            sentinel = ar / 'other_kit.gxmesh'
            sentinel.write_bytes(b'preserve another owner')
            assets.build(a)
            self.assertEqual(sentinel.read_bytes(), b'preserve another owner')
            self.assertEqual(original, {p.name:p.read_bytes() for p in ar.iterdir() if p.name in original})


if __name__ == '__main__':
    unittest.main()
