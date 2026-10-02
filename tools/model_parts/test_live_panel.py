"""Drive the shipped Lua panel through mouse events; no renderer is mocked as proof of appearance."""
from pathlib import Path
import subprocess
import unittest


SCRIPT = Path(__file__).resolve().parents[2] / 'melee/worktrees/linux/pc/scripts/examples/character_parts_lab/main.lua'

DRIVER = r'''
local mx,my,mb,frame=0,0,0,0
local colors,store,draws,fx,unavailable={},{},{},{},{}
local part_calls,fx_stops,pad_frames=0,0,0
local config='return {fighters={"falco"},assets={falco="asset"},costume=0,autoscan=false}'
local function controls(asset,name)
  return 'signature\tgeometry\nasset_sha256\t'..asset..'\ncostume\t0\n'..name..'\t1\t0.5\t0,1\n'
end
store['falco-controls.tsv']=controls('stale','STALE LABEL')
gd={
  data_read=function(k) if k=='config.lua' then return config end;return store[k] end,
  data_write=function(k,v) store[k]=v end,
  input=function(p) if p==4 then pad_frames=pad_frames+1 end end,
  scene_launch=function()end,match=function()return{active=true,frame=frame}end,
  resume=function()end,pause=function()end,teleport=function()end,
  player=function()return{x=0,y=0,costume=0}end,
  camera_detach=function()end,camera_set=function()end,camera_attach=function()end,
  parts=function()
    local p={geometry_signature='geometry'}
    for i=0,5 do p[#p+1]={index=i,source=i==5 and 1 or 0,item_kind=7,
      joint=1,body_joint=1,area=10-i,regions={torso=1},bounds={0,0,0,1,1,1}} end
    return p
  end,
  parts_clear=function() colors={} end,
  dobj_solid=function(p,d,c)
    part_calls=part_calls+1
    if unavailable[d] then return false end
    colors[d]=c;return true
  end,
  rgb=function(r,g,b)return r*65536+g*256+b end,
  fx_stop=function()fx_stops=fx_stops+1 end,
  fx_attach=function(name)fx[#fx+1]=name;return true end,
  mouse=function()return mx,my,mb end,
  log=function()end,fill=function()end,
  kit={text=function(x,y,t)draws[y]=t end},
}
local function advance(n)for i=1,n do on_tick() end end
local function click(x,y)mx,my,mb=x,y,1;on_tick();mb=0;on_tick()end
local function text(y)draws={};on_draw();return draws[y]end
dofile(arg[1])
on_frame();on_frame();frame=100;on_frame()
assert(pad_frames==3)
assert(text(111)~='STALE LABEL','stale costume asset accepted')
store['falco-controls.tsv']=controls('asset','Reviewed torso')
advance(180);assert(text(111)=='Reviewed torso')
click(135,190);assert(colors[0] and colors[1] and not colors[2],'group slider did not colour only its members')
local original=colors[0]
click(160,330);assert(colors[0]==gd.rgb(255,230,60))
click(160,330);assert(colors[0]==original,'highlight did not restore colour')
click(30,330);click(240,145);assert(text(129)=='Raw DObj 5')
store['falco-controls.tsv']=controls('asset','Renamed torso')
advance(180);assert(text(129)=='Raw DObj 5','report refresh moved raw selection')
unavailable[5]=true
click(90,190);assert(text(129)=='Raw DObj 5 (expired)','expired item was not marked')
click(30,360);advance(12);assert(colors[0] and colors[4] and not colors[5])
click(160,360);assert(next(colors)==nil,'restore left draw overrides active')
click(400,405);assert(fx[#fx]=='GoldEmbers' and next(colors)==nil)
click(400,405);assert(fx[#fx]=='FrostDrift')
click(300,405);assert(fx[#fx]=='GoldEmbers')
click(500,405);local count=#fx;advance(301);assert(#fx==count+1,'rotation did not advance')
click(160,360);count=#fx;advance(305);assert(#fx==count and next(colors)==nil,'restore did not stop rotation')
on_unload();assert(next(colors)==nil and fx_stops>0)
print('part panel workflow ok')
'''


class LivePanelTests(unittest.TestCase):
    def test_mouse_workflow_asset_binding_and_retired_items(self):
        result = subprocess.run(['lua', '-', str(SCRIPT)], input=DRIVER, text=True,
                                capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('part panel workflow ok', result.stdout)


if __name__ == '__main__':
    unittest.main()
