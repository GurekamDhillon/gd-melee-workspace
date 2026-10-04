-- Plain Lua contract fixture; no game launch. Both normal and six-slot claims.
local entry='melee/pc/scripts/examples/bench/scripts/main.lua'
local config={frames=10,seed=3,roster={'fox','fox','fox','fox','fox','fox'},
  features={'missing_asset'},setup={{feature='unsupported_api',api='imaginary',args={}}},
  events={{frame=3,feature='save',api='savestate',args={1}}}}
local claims,modes,writes,quit,resets,reports,saves={},{},{},0,0,0,0
local source=assert(io.open(entry)):read('*a')
local encode='return {frames=10,seed=3,roster={"fox","fox","fox","fox","fox","fox"},features={"missing_asset"},setup={{feature="unsupported_api",api="imaginary",args={}}},events={{frame=3,feature="save",api="savestate",args={1}}}}'
gd={mod_read=function(path)if path=="scripts/config.lua" then return encode end;return nil,"fixture absent" end,player=function(i)return {char=i,char_name='fighter'..i}end,
  match=function()return {active=true}end,log=function()end,
  cpu_mode=function(i,mode)modes[i]=mode end,
  input=function(i,sample,n)claims[i]=(claims[i] or 0)+1;assert(n==1 and sample.buttons)end,
  prof=function(command)if command=='reset' then resets=resets+1 elseif command=='report' then reports=reports+1 end;return true end,
  savestate=function(slot)assert(slot==1);saves=saves+1 end,
  data_write_atomic=function(name,data)writes[#writes+1]=data;return true end,
  release=function(i)assert(i>=1 and i<=6)end,quit=function()quit=quit+1 end,
  perf=function()return {frames={}}end,rollbacks=function()return {total=0}end}
assert(load(source,'@bench/main.lua'))()
on_frame_pre();on_frame() -- admission/setup frame, reset only
for i=1,10 do on_frame_pre();on_frame() end
assert(quit==1 and resets==1 and reports==1 and saves==1)
for i=1,6 do assert(claims[i]==10,'fixed logic input count') end
assert(modes[5]=='stand' and modes[6]=='stand' and modes[4]==nil)
local final=writes[#writes]
assert(final:find('"complete":true',1,true));assert(final:find('"frames":10',1,true))
assert(final:find('unsupported',1,true));assert(final:find('cpu_virtual_script',1,true))
on_frame_pre();on_frame();assert(quit==1)
print('bench Lua contract PASS: six-slot claims, explicit CPU mode, 10 frames, warmup/reset, event, unsupported status, single completion')
