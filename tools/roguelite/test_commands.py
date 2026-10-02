"""Execute command policy in Lua, including held-button and taunt boundaries."""
from pathlib import Path
import shutil
import subprocess
import unittest
import game_source

MODULE = game_source.ROGUELITE / 'commands.lua'


class CommandsTests(unittest.TestCase):
    def test_tree_and_interception(self):
        lua = shutil.which('lua') or shutil.which('lua5.4')
        self.assertIsNotNone(lua)
        code = r'''
local C=assert(loadfile(arg[1]))(); local s=C.new()
local allow=function() return true end
local function press(b,fn) C.update(s,0,fn or allow);return C.update(s,b,fn or allow) end
local e,m=press(8);assert(e.kind=='taunt' and m==7)
e,m=press(1);assert(e.node=='magic' and m==15)
for i=1,120 do assert(not C.update(s,1,allow));assert(s.node=='magic') end
e,m=press(1);assert(e.node=='fire' and C.view(s).depth==2)
e,m=press(8);assert(e.kind=='back' and s.node=='magic' and m==15)
e,m=press(8);assert(e.kind=='back' and s.node=='root' and m==15)
for i=1,120 do e,m=C.update(s,8,allow);assert(not e and m==15) end
e,m=C.update(s,0,allow);assert(not e and m==7)
e,m=press(8);assert(e.kind=='taunt' and m==7)
press(1);press(1);e,m=press(2,function()return false,'Unequipped'end)
assert(e.kind=='blocked' and e.reason=='Unequipped' and s.node=='fire' and m==15)
e,m=press(2);assert(e.kind=='execute' and e.family=='cinder' and e.slot=='traversal' and s.node=='root' and m==7)
assert(not C.update(s,2,allow)) -- held activation cannot open Item on return
press(1);e,m=press(9);assert(not e and m==15 and s.node=='magic')
assert(not C.update(s,1,allow));assert(s.node=='magic') -- chord must release
e,m=press(8);assert(e.kind=='back' and m==15)
C.reset(s,8);e,m=C.update(s,8,allow);assert(not e and m==15)
press(1);press(2);e,m=press(4);assert(e.family=='rime' and e.slot=='guard')
e,m=press(0x100);assert(not e and m==7) -- A untouched
e,m=press(0x301);assert(e.node=='magic' and m==15) -- face buttons don't block Dpad
local view=C.view(s);assert(view.path[1]=='COMMAND' and view.branches[1].direction=='left')
press(2);local before=s.node;e,m=press(4);assert(e.action=='gene')
C.reset(s);press(2);assert(not press(4));assert(s.node=='item') -- absent leaf
e=press(1,function() return false,'No supplies' end);assert(e.kind=='blocked')
assert(not pcall(C.update,s,0/0));assert(not pcall(C.update,s,-1))
print('commands passed')
'''
        result = subprocess.run([lua, '-', str(MODULE)], input=code, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
