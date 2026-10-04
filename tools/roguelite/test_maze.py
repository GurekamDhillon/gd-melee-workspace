"""Seeded DFS prototype maze: pure topology, real blockers and conservative paths."""
import shutil
import subprocess
import unittest
import game_source

class MazeTests(unittest.TestCase):
    def test_seeded_topology_geometry_and_refusal(self):
        program = r"""
local M=dofile(arg[1])
local function signature(m)
 local rows={}
 for _,id in ipairs(m.order) do
  local n=m.nodes[id];local out={id,n.kind}
  for _,e in ipairs(n.exits) do out[#out+1]=e.side..':'..e.to end
  rows[#rows+1]=table.concat(out,',')
 end
 return table.concat(rows,';')
end
local variants={}
for seed=1,300 do
 local m=M.generate(seed)
 assert(M.validate(m))
 assert(m.schema_version==1 and m.generator_version==3 and m.certified==false)
 assert(signature(m)==signature(M.generate(seed)))
 variants[signature(m)]=true
 local edges,entry,rest,boss,finish=0,0,0,0,0
 for _,id in ipairs(m.order) do
  local n=m.nodes[id]
  edges=edges+#n.exits
  entry=entry+(n.kind=='entry' and 1 or 0);rest=rest+(n.kind=='rest' and 1 or 0)
  boss=boss+(n.kind=='boss' and 1 or 0);finish=finish+(n.kind=='exit' and 1 or 0)
  assert(#n.room.platforms==7 and #n.room.lines==6)
  assert(n.room.collision_count==14 and n.room.model_count==32)
  assert(n.room.camera.bottom==-36 and n.room.camera.top==80)
  for _,p in ipairs(n.room.platforms) do assert(not p.ledges and p.passthrough and (p.width==44 or p.width==48)) end
 end
 assert(edges/2==13 and entry==1 and rest==1 and boss==1 and finish==1)
end
local count=0 for _ in pairs(variants)do count=count+1 end assert(count>250)
local m=M.generate(42);m.nodes[m.start].room.lines[1].y1=100
assert(not M.validate(m),'forged wall accepted')
m=M.generate(42);m.nodes[m.start].room.platforms[1].y=55
assert(not M.validate(m),'unreachable geometry accepted')
m=M.generate(42);table.remove(m.nodes[m.start].exits)
assert(not M.validate(m),'nonreciprocal maze accepted')
m=M.generate(42);m.nodes[m.start].grid=nil;assert(not M.validate(m),'malformed grid accepted')
assert(not pcall(M.generate,0));assert(not pcall(M.generate,math.huge))
print('maze: 300 reproducible DFS+loop layouts, topology, blockers, clearance and refusal passed')
"""
        lua=shutil.which('lua') or shutil.which('lua5.4')
        self.assertIsNotNone(lua)
        result=subprocess.run([lua,'-',str(game_source.ROGUELITE/'maze.lua')],input=program,text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_checkpoint_validation_instruction_budget_and_mutation_safety(self):
        program=r"""
local M=dofile(arg[1]);local m=M.generate(42)
local function measured(fn)
 local count=0
 debug.sethook(function()count=count+100 end,'',100)
 local ok,why=fn()
 debug.sethook()
 assert(ok,why)
 return count
end
local first=measured(function()return M.validate(m)end)
local second=measured(function()return M.validate(m)end)
print('maze validate instructions first='..first..' repeat='..second)
assert(first<60000 and second<60000,'maze checkpoint validation exceeds bounded budget')
-- A cached template must never allow modified decoded or live geometry.
m.nodes[m.start].room.lines[1].y1=100
assert(not M.validate(m),'modified live geometry accepted after cached validation')
local g=M.geometry(0);g.platforms[1].y=85
assert(not M.screen(g),'analytical screen cache hid a mutated platform')
"""
        lua=shutil.which('lua') or shutil.which('lua5.4')
        result=subprocess.run([lua,'-',str(game_source.ROGUELITE/'maze.lua')],input=program,text=True,capture_output=True)
        print(result.stdout, end='')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
