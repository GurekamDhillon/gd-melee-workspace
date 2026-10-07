"""Validate original assets, finite lifecycle/budget and semantic blend invariants."""
import itertools
import hashlib
import json
import math
from pathlib import Path
import subprocess
import tempfile
import unittest
from expression import express, TRAITS
from recipes import build, recipes, asset_catalog, VERSION
from tools.effects_lab.prepare import CHECKOUT

class EffectsLabTests(unittest.TestCase):
    def test_assets_and_supported_packages(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);build(root)
            assets=asset_catalog()
            used=set()
            for pkg in recipes():
                path=root/'fx'/pkg['name'];actual=json.loads((path/(pkg['name']+'.gfx.json')).read_text())
                self.assertEqual(pkg,actual)
                self.assertLessEqual(len(pkg['emitters']),32)
                textures={t['name'] for t in pkg['textures']}
                used.update(textures)
                self.assertEqual(pkg['source']['recipe_version'],VERSION)
                for t in pkg['textures']:
                    data=(path/t['file']).read_bytes();self.assertTrue(data.startswith(b'\x89PNG\r\n\x1a\n'))
                    self.assertEqual(hashlib.sha256(data).hexdigest(),assets[t['name']]['sha256'])
                    self.assertEqual((t['w'],t['h']),(256,256))
                    self.assertEqual(t['swizzle'],assets[t['name']].get('gfx_texture_swizzle','rgba'))
                for e in pkg['emitters']:
                    self.assertIn(e['material']['shader']['type'],('sprite','warp','distortion'))
                    self.assertGreater(e['emission']['duration'],0)
                    self.assertIsInstance(e['emission']['one_time'],bool)
                    self.assertNotIn('infinite',e['particle'])
                    self.assertLess(e['emission']['start']+e['emission']['duration']+e['particle']['life']*1.4,160)
                    for sampler in e['samplers']:self.assertIn(sampler['texture'],textures)
                    shader=e['material']['shader']
                    if shader['type']!='sprite':
                        self.assertEqual(shader['alpha_textures'],[0])
                        self.assertEqual(shader['offset'],1)
                        self.assertEqual(assets[e['samplers'][1]['texture']]['kind'],'data')
                        self.assertEqual(e['samplers'][1]['wrap'],['Repeat','Repeat'])
                # All authored key times are ordered and finite.
                for e in pkg['emitters']:
                    curves=[e['particle']['scale']['keys']]+[v['keys'] for v in e['color'].values() if isinstance(v,dict) and 'keys' in v]
                    for keys in curves:
                        self.assertEqual(sorted(k[3] for k in keys),[k[3] for k in keys])
                        self.assertTrue(all(math.isfinite(x) for k in keys for x in k))
            self.assertEqual(used,set(assets))

    def test_continuous_budget_and_extreme_traits(self):
        for extreme in itertools.product((0,1),repeat=len(TRAITS)):
            traits=dict(zip(TRAITS,extreme))
            for t in (0,.1,.25,.5,.75,.9,1):
                controls=express(t,traits)
                for k in range(7):
                    self.assertAlmostEqual(controls[k][0]+controls[k+7][0],1)
                    self.assertLessEqual(controls[k][1]+controls[k+7][1],1.65)
                for c in controls:self.assertTrue(all(math.isfinite(v) and 0<=v<=(3 if i==5 else 2) for i,v in enumerate(c)))
        for t in (.1,.25,.5,.75,.9):
            left,right=express(t-1e-5),express(t+1e-5)
            self.assertLess(max(abs(a-b) for x,y in zip(left,right) for a,b in zip(x,y)),.0001)
        self.assertEqual(express(0)[7][0],0)
        self.assertEqual(express(1)[0][0],0)
        isolated=express(.5,isolate=4)
        self.assertEqual(sum(c[0]>0 for c in isolated),2)
        for invalid in (float('nan'),float('inf'),-1,2):
            with self.assertRaises(ValueError):express(invalid)

    def test_expression_matches_lua(self):
        # Exercise the actual mouse lab expression through its emitted live controls.
        script=CHECKOUT/'pc/scripts/examples/effects_lab/main.lua'
        driver='''gd={data_read=function()end,input=function()end,scene_launch=function()end,match=function()return{active=true,frame=100}end,teleport=function()end,player=function()return{x=0,y=0}end,camera_detach=function()end,camera_set=function()end,resume=function()end,fx_play=function()return 1 end,fx_instance=function()return{alive=true}end,fx_end=function()end,mouse=function()return 0,0,0 end,fx_control=function(h,i,c,f)print(i,c.opacity,c.rate,c.speed,c.life,c.size,c.brightness,c.turbulence)end};dofile(arg[0]);on_frame();on_frame()'''
        driver=driver.replace('on_frame();on_frame()', 'on_frame();gd.match=function()return{active=true,frame=0}end;on_frame();gd.match=function()return{active=true,frame=100}end;on_frame()')
        result=subprocess.run(['lua','-e',driver,str(script)],capture_output=True,text=True,check=True)
        # With -e, script is also executed after driver. Only driver calls on_frame.
        rows=[line.split() for line in result.stdout.splitlines()]
        self.assertEqual(len(rows),14)
        for row,expected in zip(rows,express(0)):
            for value,target in zip(row[1:],expected):self.assertAlmostEqual(float(value),target)

    def test_mouse_workflow(self):
        script=CHECKOUT/'pc/scripts/examples/effects_lab/main.lua'
        driver=r'''local mx,my,mb,paused,stepped,plays,edits=0,0,0,false,0,0,0
local store={};local fades={};local alive=true
function click(x,y)mx,my,mb=x,y,1;on_tick();mb=0;on_tick()end
gd={data_read=function(k)return store[k]end,data_write=function(k,v)store[k]=v end,input=function()end,
scene_launch=function()end,match=function()return{active=true,frame=100}end,teleport=function()end,
player=function()return{x=0,y=0}end,camera_detach=function()end,camera_set=function()end,camera_attach=function()end,
resume=function()paused=false end,pause=function()paused=true end,paused=function()return paused end,
step=function(n)stepped=stepped+n;paused=true end,perf=function()return{frames={{total_ms=1}}}end,
fx_play=function()plays=plays+1;alive=true;return plays end,fx_instance=function()return{alive=alive}end,
fx_end=function(h,f)fades[#fades+1]=f end,fx_stop=function()end,mouse=function()return mx,my,mb end,
fx_control=function(h,i,c,f)edits=edits+1;assert(c.opacity>=0 and c.opacity<=1 and c.rate<=2)end}
dofile(arg[0]);on_frame();on_frame();assert(plays==0) -- outgoing scene cannot be treated as ready
gd.match=function()return{active=true,frame=0}end;on_frame()
gd.match=function()return{active=true,frame=100}end;on_frame();assert(plays==1 and edits==14)
click(130,155);assert(edits==28) -- blend changes a running handle
click(300,390);assert(paused)
click(400,390);assert(stepped==1 and paused)
click(30,386);assert(edits==42) -- semantic layer isolation
click(300,424);assert(store['favourite.lua'])
click(390,424);assert(plays==2) -- seeded replay from versioned save
local current=store['favourite.lua'];store['favourite.lua']=current:gsub('recipe=2','recipe=1')
click(390,424);assert(plays==2) -- older artwork cannot silently replace the saved recipe
store['favourite.lua']=current
click(550,390);assert(plays==3 and fades[#fades]==10) -- consume/fade preview into reaction
click(550,390);assert(plays==3) -- reaction cooldown
click(550,357);assert(fades[#fades]==12)
click(400,357);alive=false;on_frame();assert(plays==4) -- loop after complete cleanup
click(400,357);alive=false;click(130,155);assert(plays==5) -- editing a finished preview replays it
gd.match=function()return{active=true,frame=200}end
click(550,390);assert(plays==6)
click(130,155);assert(plays==7) -- editing during a reaction uses the correct 14-emitter package
on_unload();print('mouse workflow ok')'''
        result=subprocess.run(['lua','-e',driver,str(script)],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('mouse workflow ok',result.stdout)

if __name__=='__main__':unittest.main()
