"""Physical long-room prototype contracts; no native playability certification."""
import shutil
import subprocess
import unittest
from tools.test_support import require_game
require_game('pc/scripts/examples/roguelite')
import game_source


class TraversalTests(unittest.TestCase):
    def run_lua(self, program):
        lua = shutil.which('lua') or shutil.which('lua5.4')
        self.assertIsNotNone(lua)
        result = subprocess.run([lua, '-', str(game_source.ROGUELITE / 'traversal.lua'),
                                 str(game_source.ROGUELITE / 'maze.lua')], input=program,
                                text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_long_physical_routes_budgets_and_legacy_separation(self):
        self.run_lua(r'''
local T=dofile(arg[1]);local Old=dofile(arg[2]);local variants={}
for seed=1,200 do
 local m=T.generate(seed);assert(T.validate(m))
 assert(m.generator_version==4 and m.schema_version==1 and m.certified==false)
 assert(#m.order==2 and m.nodes.exit.terminal and not m.nodes.exit.room)
 local n=m.nodes.entry;local g=n.room;local parts=T.parts(n)
 assert(n.physical and #n.exits==1 and n.exits[1].to=='exit')
 assert(g.floor.right-g.floor.left==832 and g.kit.bay==52 and g.kit.grid==26 and g.kit.unit==13)
 assert(g.spawn.x==-390 and g.exit_anchors.right.x==390)
 assert(g.exit_anchors.right.x-g.spawn.x>=780,'short room disguised by doors')
 assert(#g.platforms==20 and #g.lines==3 and g.collision_count==24)
 assert(#parts==48 and g.model_count==#parts)
 local names={};for _,p in ipairs(parts)do
  assert(p.z==0 and p.background and p.collision==false and p.scale_y==2 and p.scale_z==2)
  names[p.model]=true
 end
 local count=0;for _ in pairs(names)do count=count+1 end;assert(count==4)
 local body=g.blockers[1];assert(body.bottom==78 and body.top==130)
 assert(g.lines[3].kind=='ceiling' and g.lines[3].x0==body.right and g.lines[3].x1==body.left and g.lines[3].y0==78)
 assert(g.camera.top>=g.physical_bounds.top+40)
 assert(T.screen(g))
 local again=T.generate(seed).nodes.entry.room
 assert(again.shift==g.shift and again.spur_side==g.spur_side)
 variants[g.shift..':'..g.spur_side]=true
end
local count=0;for _ in pairs(variants)do count=count+1 end;assert(count==6)
local old=Old.generate(42);assert(Old.validate(old));assert(not T.validate(old))
assert(Old.validate(old),'new prototype changed frozen old manifests')
''')

    def test_reachability_mutation_and_partial_geometry_refusal(self):
        self.run_lua(r'''
local T=dofile(arg[1]);local m=T.generate(42)
local ok,proof=T.screen(m.nodes.entry.room);assert(ok,proof)
assert(proof.max_jump_rise<=18 and proof.reachable_surfaces==21)
assert(proof.lower_distance>=780 and proof.upper_reachable and proof.spur_reachable)
m.nodes.entry.room.platforms[1].y=100
assert(not T.screen(m.nodes.entry.room),'unreachable first step accepted')
assert(not T.validate(m),'mutated checkpoint accepted after cache warm')
m=T.generate(42);m.nodes.entry.room.lines[3].x0=m.nodes.entry.room.lines[3].x1
assert(not T.validate(m),'missing solid-body ceiling accepted')
m=T.generate(42);m.nodes.entry.exits[1].to='entry';assert(not T.validate(m),'internal warp accepted')
m=T.generate(42);m.nodes.entry.room.blockers[1].bottom=40
assert(not T.screen(m.nodes.entry.room),'unsafe underpass headroom accepted')
local n=T.generate(42).nodes.entry;local parts=T.parts(n)
parts[1].y=999;assert(T.parts(n)[1].y==0,'mutable part cache leaked')
assert(not pcall(T.generate,0));assert(not pcall(T.generate,math.huge))
''')

    def test_checkpoint_validation_stays_bounded(self):
        self.run_lua(r'''
local T=dofile(arg[1]);local m=T.generate(42);local count=0
debug.sethook(function()count=count+100 end,'',100)
local ok,why=T.validate(m);debug.sethook();assert(ok,why)
assert(count<60000,'physical checkpoint validation exceeds bounded budget')
''')


if __name__ == '__main__':
    unittest.main()
