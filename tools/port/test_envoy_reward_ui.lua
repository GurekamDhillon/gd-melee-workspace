-- Capture real UI drawing calls: animation must reach native kit and fill geometry.
local base='melee/pc/scripts/examples/envoy/scripts/'
local stats={'power','speed','guard','jump'}
local C=dofile(base..'companion.lua')({genetics={stats=stats}})
local H=dofile(base..'hud.lua')({companion=C})
local M=dofile(base..'menu.lua')({})
local V=dofile(base..'menu_draw.lua')({companion=C,hud=H})
local c={stats={}};local before,after={},{}
for _,name in ipairs(stats) do
 before[name]={points=10,level=0,grade='C'}
 after[name]={points=30,level=1,grade='C'};c.stats[name]=after[name]
end
local r={preview=true,before=before,after=after,levelups={power=1},animation_frames=48}
local texts,fills,lists={},{},{}
local g={safe_area=function()return{x=0,y=0,w=800,h=600,right=800}end,
 fill=function(x,y,w,h,col)fills[#fills+1]={x=x,y=y,w=w,h=h,col=col}end}
g.kit={available=function()return true end,panel=function()end,
 text=function(x,y,t)texts[#texts+1]=t end,list=function(x,y,w,rows)lists=rows end}
local function has(s)for _,t in ipairs(texts)do if t:find(s,1,true)then return true end end;return false end
local function render(t,menu)
 texts,fills,lists={},{},{};r.animation=t
 if menu then local s=M.new();s:show('reward');V.draw(g,s,{reward=r})
 else H.draw(g,c,'reward',nil,nil,r) end
 local widths={};for _,f in ipairs(fills)do if f.col==H.colours.red then widths[#widths+1]=f.w end end
 assert(#widths==1,'one real Power bar fill must be drawn')
 return widths[1]
end
for _,menu in ipairs({false,true})do
 local initial=render(0,menu);assert(initial>0 and has('L0'),'before level appears at tick 0')
 local mid=render(12,menu);assert(math.abs(mid/initial-1.5)<.001,'bar grows before crossing')
 assert(not has('LEVEL UP'),'level-up waits for crossing')
 local crossing=render(24,menu);assert(crossing==0 and has('L1'),'bar resets at actual level threshold')
 assert(has('LEVEL UP'),'level-up moment appears at crossing')
 local final=render(48,menu);assert(math.abs(final/initial-2/3)<.001,'bar reaches after progress at tick 48')
end
local s=M.new();s:show('reward');r.preview=false;r.options={{colour='green',points=30,effect='+12% run speed'}}
V.draw(g,s,{reward=r});assert(lists[1].label=='green drive / +12% run speed','effect replaces raw points')
s:results({});assert(s:entries({})[1].label=='Return to menu','safe results wording')
assert(s:input('accept',{}).type=='hub','results returns to menu route')
local rows=s:entries({retail_menu=true});assert(rows[1].label=='Begin run')
for _,row in ipairs(rows)do assert(row.label~='Walk in garden','no unresolved garden entry')end
rows=s:entries({retail_menu=true,garden_available=true});assert(rows[2].label=='Walk in garden')
rows=s:entries({});assert(rows[1].label=='Walk in garden','legacy campaign menu retained')
-- Growth carry is inherited experience, excluded from the current life's levels.
r.preview=true;r.before.power={points=110,carry=100,level=0,grade='C'}
r.after.power={points=150,carry=100,level=2,grade='B'}
r.animation=48
local v,fraction,current,needed,moment=H.stat_view(c,'power',r)
assert(v.level==2 and fraction==0 and current==0 and needed>0 and moment and v.grade=='B')
r.animation=-10;v=H.stat_view(c,'power',r);assert(v.level==0 and v.points==110)
r.animation=100;v=H.stat_view(c,'power',r);assert(v.level==2 and v.points==150)
v=H.stat_view(c,'power');assert(v==c.stats.power,'normal HUD keeps actual stats')
print('Envoy reward UI: captured HUD/menu bars, level crossing, effects and results passed')
