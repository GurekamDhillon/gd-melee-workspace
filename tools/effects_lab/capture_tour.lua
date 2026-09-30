-- Native cosmetic catalogue capture. Run only in the isolated tour profile.
local cases={
 {"GoldEmbers","Gold Embers",55},{"FrostDrift","Frost Drift",55},
 {"ElectricSparks","Electric Sparks",32},{"CrimsonSpiral","Crimson Spiral",17},
 {"EmeraldRings","Emerald Rings",17},{"HeatShimmer","Heat Shimmer",17},
 {"ShadowPulse","Shadow Pulse",17},{"SolarEruption","Solar Eruption",44},
 {"GlacialShatter","Glacial Shatter",44},{"ThermalBlend","Thermal Blend (50/50)",44},
 {"ThermalShock","Thermal Shock",18},{"RogueCinderRelease","Cinder / immediate release",12},
 {"RogueRimeRelease","Rime / immediate release",12}}
local requested,ready=false,false
local index,age,handle=1,0,0
local function frame_fixture()
 gd.cpu_mode(1,"stand");gd.cpu_mode(2,"stand");gd.fly_solid(false)
 gd.fly_attack(1,false);gd.fly_attack(2,false)
 gd.fly_target(1,0,0);gd.fly_target(2,110,0)
 gd.teleport(1,0,0);gd.teleport(2,110,0)
 gd.camera_detach();gd.camera_set{eye={x=5,y=17,z=98},interest={x=0,y=10,z=0},fov=30}
end
local peak,refused=0,0
local results={}
function on_frame()
 gd.input(4,{},1);gd.input(2,{},1)
 if not requested then requested=true;gd.scene_launch{mode="vs",p1="falco",p2="fox",stage="fd",stocks=99,items="off",time=0};return end
 local m=gd.match();if not m.active or m.frame<100 then return end
 if not ready then
  assert(gd.stage_add_platform(0,0,300,{draw=true}));assert(gd.stage_isolate(true))
  ready=true;gd.teleport(1,0,2);gd.teleport(2,100,2);gd.hud_visible(false)
  gd.camera_detach();gd.camera_set{eye={x=5,y=17,z=98},interest={x=0,y=10,z=0},fov=30}
 end
 local c=cases[index]
 if age==0 then
  frame_fixture()
  handle=gd.fx_play(c[1],1,0,0,10,0,1,17029);peak=0;refused=0
  assert(handle>0,"missing package "..c[1])
  if c[1]=="ThermalBlend" then for i=0,13 do gd.fx_control(handle,i,{opacity=.5,rate=.5,brightness=1.6},0) end end
 end
 age=age+1
 local q=gd.fx_instance(handle);peak=math.max(peak,q.particles);refused=math.max(refused,q.refused)
 if age==c[3] then gd.screenshot(c[1]..".png") end
 if age==90 then gd.fx_end(handle,0) end
 if age==105 then
  q=gd.fx_instance(handle)
  results[#results+1]=string.format('%s\t%d\t%d\t%d\t%d\n',c[1],peak,q.particles,q.emitters,refused)
  index=index+1;age=0
  if index>#cases then
   gd.data_write('evidence.tsv','package\tpeak_particles\tfinal_particles\tfinal_emitters\trefused\n'..table.concat(results))
   gd.data_write('complete.txt','complete 13 native packages; fixed seed 17029; fixed attack-disabled intangible fly targets; cosmetic attachment fixture\n')
   gd.quit()
  end
 end
end
function on_draw()
 if not ready or index>#cases then return end
 local c=cases[index];local q=gd.fx_instance(handle)
 gd.fill(12,12,616,58,0x080D19DC)
 gd.kit.text(23,35,c[2],"label","gold")
 gd.kit.text(23,56,string.format("NATIVE COSMETIC PREVIEW %02d/13 | frame %d | particles %d",index,age,q.particles),"caption","bone")
 gd.fill(12,444,616,25,0x080D19DC)
 gd.kit.text(23,462,"Original textures / existing sprite, warp and distortion shaders","caption","bone")
end
function on_unload()gd.fx_stop();gd.hud_visible(true);gd.camera_attach(0)end
