"""Actual Lua lifecycle adapter tests; native policy tests are script_cpu_technical."""
from pathlib import Path
import shutil
import subprocess
import unittest
from tools.test_support import require_game
require_game('pc/scripts/examples/roguelite')
import game_source

SOURCE = game_source.ROGUELITE / 'technical_ai.lua'


class TechnicalAiTests(unittest.TestCase):
    def test_native_control_adapter(self):
        lua = shutil.which('lua') or shutil.which('lua5.4')
        self.assertIsNotNone(lua, 'Actual Lua interpreter required')
        program = r'''
gd={}
local A=assert(loadfile(arg[1]))()
local ok,why=A.configure(2,3,123)
assert(not ok and why:find('unavailable') and not A.status(2).enabled)
local calls={};local skill=0;local refusal=false
function gd.cpu_technical(port,level,seed)
 if not level then return {enabled=skill>0,skill=skill,tech_inputs=2} end
 calls[#calls+1]={port=port,level=level,seed=seed}
 if refusal then return false end
 skill=level;return true
end
for _,bad in ipairs({-1,4,1.5}) do assert(not A.configure(2,bad,1)) end
assert(not A.configure(2,3,0));assert(not A.configure(2,3,2147483648));assert(#calls==0)
assert(A.configure(2,3,421));assert(calls[1].port==2 and calls[1].level==3 and calls[1].seed==421)
assert(A.status(2).enabled and A.status(2).skill==3)
refusal=true;ok,why=A.configure(1,3,421);assert(not ok and why:find('baseline'))
refusal=false;assert(A.clear(2));assert(calls[#calls].level==0 and not A.status(2).enabled)
function gd.cpu_technical() error('offline refusal') end
assert(not A.configure(2,2,1));assert(not A.clear(2));assert(not A.status(2).enabled)
print('native technical AI lifecycle adapter invariants passed')
'''
        result = subprocess.run([lua, '-', str(SOURCE)], input=program, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('invariants passed', result.stdout)


if __name__ == '__main__':unittest.main()
