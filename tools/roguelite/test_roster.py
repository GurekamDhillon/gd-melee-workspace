"""Real Lua stock picker/binding checks and deterministic metadata generation."""
from pathlib import Path
import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from tools.test_support import require_game
require_game('pc/scripts/examples/roguelite')
import game_source

ROOT = Path(__file__).resolve().parents[2]
SOURCE = game_source.ROGUELITE
SPEC = importlib.util.spec_from_file_location('rogue_bindings', Path(__file__).with_name('build_bindings.py'))
BUILD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILD)


class RosterTests(unittest.TestCase):
    def test_lua_picker_binding_and_provenance(self):
        lua = shutil.which('lua') or shutil.which('lua5.4')
        self.assertIsNotNone(lua, 'Actual Lua interpreter required')
        with tempfile.TemporaryDirectory() as td:
            counts = Path(td) / 'counts.lua'
            counts.write_text('return ' + BUILD.lua(BUILD.stock_counts()))
            program = r'''
local R=assert(loadfile(arg[1]..'/roster.lua'))()
local B=assert(loadfile(arg[1]..'/bindings.lua'))()
local counts=assert(loadfile(arg[2]))()
assert(#R.list==26)
local seen,all= {},0
for _,e in ipairs(R.list) do
 assert(not seen[e.id]);seen[e.id]=true
 assert(e.costumes==counts[e.id])
 for costume=0,e.costumes-1 do
  local c={id=e.id,costume=costume};local scene=assert(R.scene(c))
  assert(scene==e.id..'/c'..costume)
  local loaded=assert(R.decode(assert(R.encode(c))));assert(loaded.id==e.id and loaded.costume==costume)
  all=all+1
 end
 assert(not R.scene({id=e.id,costume=e.costumes}))
 assert(not R.scene({id=e.id,costume=-1}))
 assert(not R.scene({id=e.id,costume=0/0}))
end
assert(all==123)
assert(seen.zelda and seen.sheik and seen.popo)
assert(not R.scene({id='nana',costume=0}))
assert(not R.decode('ROSTER1 fox/c0\nreturn os.execute("bad")'))
assert(not R.decode('ROSTER1 fox/c16\n'))
local s=R.new({id='falco',costume=0})
local ctx={coverage=B.coverage}
local function control(id)
 local v=R.view(s,ctx);for _,b in ipairs(v.controls) do if b.id==id then return b end end error(id)
end
local function click(id)
 local c=control(id);return R.update(s,ctx,{mx=c.x+3,my=c.y+3,click=true})
end
click('fighter:pikachu');click('costume:next');assert(s.choice.id=='pikachu' and s.choice.costume==1)
local a=click('accept');assert(a.kind=='fighter_selected' and R.scene(a.fighter)=='pikachu/c1')
click('costume:previous');click('costume:previous');assert(s.choice.costume==3)
s.focus='costume:next';R.update(s,ctx,{confirm=true});assert(s.choice.costume==0)
click('fighter:popo');assert(R.view(s,ctx).note:find('partner'))
assert(R.update(s,ctx,{back=true}).kind=='fighter_back')
click('fighter:zelda');assert(R.view(s,ctx).note:find('Transform'))
s.focus='fighter:captain';R.update(s,ctx,{right=true});assert(s.focus=='fighter:donkey')
local report=assert(B.coverage({id='falco',costume=0}));assert(report.samples==36)
report.slots.assault[1]=-99;local pristine=B.coverage({id='falco',costume=0});assert(pristine.slots.assault[1]~=-99)
local _,unknown=B.coverage({id='falco',costume=1});assert(unknown:find('No measured'))
local function fixture(choice)
 local e=assert(B.coverage(choice));local parts={geometry_signature=e.signature};local draws={}
 for id,p in pairs(e.evidence) do parts[#parts+1]={index=tonumber(id),source=0,status=0,path=p.path,joint=p.joint,item_kind=-1,item_ordinal=-1};draws[#draws+1]={index=tonumber(id),render=0} end
 table.sort(parts,function(x,y)return x.index<y.index end)
 return parts,{kind=e.kind,costume=e.costume},draws,e
end
local parts,player,draws,entry=fixture({id='falco',costume=0})
local resolved=assert(B.resolve(parts,player,draws));assert(#resolved.assault==#entry.slots.assault)
assert(not B.resolve(parts,player))
local topology=B.topology(parts,player)
parts.geometry_signature='bad';assert(not B.resolve(parts,player,draws));parts.geometry_signature=entry.signature
player.costume=1;assert(not B.resolve(parts,player,draws));player.costume=0
player.kind=1;assert(not B.resolve(parts,player,draws));player.kind=entry.kind
-- Live transparent overlays, changed identities and expired records never tint.
local id=entry.slots.assault[1]
for _,d in ipairs(draws) do if d.index==id then d.render=0x40000000 end end
resolved=assert(B.resolve(parts,player,draws));assert(#resolved.assault==#entry.slots.assault-1)
for _,d in ipairs(draws) do if d.index==id then d.render=0 end end
for _,p in ipairs(parts) do if p.index==id then p.status=1 end end
resolved=assert(B.resolve(parts,player,draws));assert(#resolved.assault==#entry.slots.assault-1)
assert(topology~=B.topology(parts,player))
for _,p in ipairs(parts) do if p.index==id then p.status=0;p.joint=p.joint+1 end end
resolved=assert(B.resolve(parts,player,draws));assert(#resolved.assault==#entry.slots.assault-1)
-- Owned item identities affect refresh fingerprint but have no persistent color selector.
parts[#parts+1]={index=400,source=1,status=0,path=0,joint=0,item_kind=12,item_ordinal=5}
assert(topology~=B.topology(parts,player));resolved=assert(B.resolve(parts,player,draws));assert(not resolved.equipment_bound)
for _,slot in ipairs({'assault','guard','traversal'}) do for _,used in ipairs(resolved[slot]) do assert(used~=400) end end
local ic,climber,icdraws=fixture({id='popo',costume=0});assert(B.resolve(ic,climber,icdraws));climber.kind=11
assert(not B.resolve(ic,climber,icdraws),'Nana accepted unmeasured Popo selector')
local hat,pk,pkdraws,pke=fixture({id='pikachu',costume=1});local hatmap=assert(B.resolve(hat,pk,pkdraws))
assert(#hatmap.assault==3 and hatmap.assault[1]==22)
local total=0
local function bounds(x,y,w,h) assert(x>=0 and y>=0 and x+w<=640 and y+h<=480);total=total+1 end
gd={fill=bounds,kit={panel=bounds,button=function(x,y,w,label,selected,opts) bounds(x,y,w,opts.h) end,
 icon=function(name,x,y,scale) bounds(x,y,16*scale,16*scale) end,
 text=function(x,y,txt,role,color,align,opts) assert(x>=0 and y>=0 and y<=480 and x+opts.max_w<=640);total=total+1 end}}
R.draw(s,ctx);assert(total>35)
for _,width in ipairs({640,480*16/9,1120}) do
 local area={x=7,y=3,w=width,h=480};local drawn={}
 local function box(x,y,w,h)assert(x>=area.x and y>=area.y and x+w<=area.x+width+.0001 and y+h<=area.y+480)end
 gd.safe_area=function()return area end
 gd.fill=box;gd.kit.panel=box
 gd.kit.button=function(x,y,w,label,selected,opts)box(x,y,w,opts.h);drawn[#drawn+1]={x=x,y=y,w=w,h=opts.h}end
 gd.kit.icon=function(name,x,y,scale)assert(scale==.65);box(x,y,16*scale,16*scale)end
 gd.kit.text=function(x,y,txt,role,color,align,opts)assert(x>=area.x and y>=area.y and y<=area.y+480 and x+opts.max_w<=area.x+width+.0001)end
 local v=R.view(s,ctx);R.draw(s,ctx);assert(v.canvas.w==width and #drawn==#v.controls)
 for i,c in ipairs(v.controls)do assert(c.x==drawn[i].x and c.y==drawn[i].y and c.w==drawn[i].w and c.h==drawn[i].h)end
 local back=v.controls[#v.controls]
 assert(back.x+back.w>area.x+.95*width,'unused right side of roster')
 assert(R.update(s,ctx,{mx=back.x+back.w-1,my=back.y+1,click=true}).kind=='fighter_back','rightmost pointer hit missed')
end

print('stock roster/picker/binding invariants passed')
'''
            result = subprocess.run([lua, '-', str(SOURCE), str(counts)], input=program, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('invariants passed', result.stdout)

    def test_generation_is_deterministic_and_conservative(self):
        fixture={'schema':1,'character':'falco','costume':0,'geometry_signature':'1234567890abcdef',
          'asset_sha256':'a'*64,'sample_count':4,'requested_sample_count':4,'cancelled':False,'failures':[],
          'parts':[]}
        def part(index,roles,**extra):
            p={'index':index,'source':0,'status':0,'joint':1,'path':index,'regions':roles,
              'mean_coverage':.1,'max_coverage':.1,'equipment_candidate':False};p.update(extra);return p
        fixture['parts']=[part(0,{'left_hand':.99}),part(1,{'head':1}),
          part(2,{'torso':.95}),part(3,{'left_foot':.95}),part(4,{'left_hand':1},source=1),
          part(5,{'torso':1},status=1),part(6,{'torso':.5,'head':.5}),
          part(7,{'left_hand':1},mean_coverage=0,max_coverage=0),
          part(8,{'torso':1},equipment_candidate=True),part(9,{'right_hand':1},equipment_candidate=True)]
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'falco-analysis.json';path.write_text(json.dumps(fixture))
            first=BUILD.catalogue(td);second=BUILD.catalogue(td)
            self.assertEqual(BUILD.render(first),BUILD.render(second))
            self.assertEqual(first['falco/c0']['slots'],{'assault':[0,9],'guard':[2],'traversal':[3]})
            fixture['cancelled']=True;path.write_text(json.dumps(fixture))
            with self.assertRaises(ValueError):BUILD.catalogue(td)
            fixture['cancelled']=False;fixture['failures']=['failed capture'];path.write_text(json.dumps(fixture))
            with self.assertRaises(ValueError):BUILD.catalogue(td)

    def test_current_measured_production_metadata(self):
        if not list(BUILD.REPORTS.glob('*-analysis.json')):
            self.skipTest('Local ignored measurement reports unavailable')
        generated=BUILD.render(BUILD.catalogue(BUILD.REPORTS))
        self.assertEqual((SOURCE/'bindings.lua').read_text(),generated)
        self.assertEqual(len(BUILD.catalogue(BUILD.REPORTS)),28)


if __name__=='__main__':unittest.main()
