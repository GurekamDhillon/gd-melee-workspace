local J=dofile('melee/pc/scripts/lib/pickup_juice.lua')
local sounds,live,rows={}, {}, {}
local serial=0
local moves,controls={},{}
local g={play_sound=function(id,o) sounds[#sounds+1]={id=id,pitch=o.pitch} end,
 fx_world=function(...) serial=serial+1;live[serial]=true;return serial end,
 fx_move=function(h,x,y,z) assert(live[h]);moves[h]={x=x,y=y,z=z};return true end,
 fx_control=function(h,_,opts) controls[h]=opts;return true end,
 fx_end=function(h,fade) assert(fade==0);live[h]=nil;return true end,
 items=function() return rows end}
local j=J.new(g)
assert(j:collect(99,'red')==nil,'unowned collections ignored')
local function drop(h,c) rows[#rows+1]={handle=h,x=h,y=0,z=0,visual_y=6,rotation=0,visible=true};j:drop(h,c,h,0,900) end
drop(1,'red');local a=j:collect(1,'red',{x=10,y=0});assert(a==-100);assert(next(j.drops)==nil)
drop(2,'red');assert(j:collect(2,'red')==-30)
drop(3,'blue');assert(j:collect(3,'blue')==140,'streak spans colours')
for i=1,91 do j:tick() end
drop(4,'green');assert(j:collect(4,'green')==200,'streak expires after 90 frames')
drop(5,'white');assert(j:collect(5,'white')==370);assert(sounds[#sounds].id==250,'white sound differs')
for i=1,40 do j:tick() end
assert(next(live)==nil,'collect transients finish')
drop(6,'yellow');j:tick();j:expire(6);assert(next(live)==nil,'expiry kills all item effects')
drop(7,'red');drop(8,'green');j:clear();assert(next(live)==nil);assert(next(j.drops)==nil);assert(next(j.flash)==nil)
local off=J.new(g,{glow=false,pool=false,sparkles=false,pop_trail=false,collect_burst=false,sound=false,highlight=false})
off:drop(9,'red',0,0,900);off:tick();off:collect(9,'red');assert(next(live)==nil,'effects independently disabled')
drop(10,'blue');local d=j.drops[10];rows[#rows].x=20;rows[#rows].y=4;rows[#rows].visual_y=10;rows[#rows].rotation=90;rows[#rows].age=42;rows[#rows].visible=false;j:tick()
assert(math.abs(moves[d.fx.highlight].x-20)<.0001,'degrees convert to radians');assert(math.abs(moves[d.fx.highlight].z-3)<.0001)
assert(moves[d.fx.pool].y==4.15 and moves[d.fx.glow].y==15.6875,'moving floor and hover follow native row')
assert(controls[d.fx.glow].opacity==0,'blink follows native visibility');assert(d.age==42,'native age owns lifecycle')
rows[#rows]=nil;j:tick();assert(j.drops[10]==nil and next(live)==nil,'missing native row ends all effects')
j:clear();rows={}
for h=100,134 do drop(h,'red') end
local count=0;for _ in pairs(live) do count=count+1 end;assert(count==150,'30-drive effect cap')
for h=100,114 do j:collect(h,'red') end
assert(#j.transients==12,'collect burst cap');j:clear();assert(next(live)==nil)
drop(200,'blue');rows[#rows].age=900;j:tick();assert(j.drops[200]==nil and next(live)==nil,'native lifetime expires immediately')
print('pickup juice: streak, identity, collect, expiry, clear, toggles PASS')
