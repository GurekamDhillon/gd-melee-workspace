"""Opt-in render diagnostics preserve collision and own their FX handles."""
import shutil
import subprocess
import unittest
from pathlib import Path

class RenderProbeTests(unittest.TestCase):
    def test_commands_validate_and_retain_effect_ownership(self):
        lua = shutil.which("lua") or shutil.which("lua5.4")
        self.assertIsNotNone(lua, "Real Lua interpreter required")
        code = r"""
local commands, views, casts = {}, {}, {}
local present=true
local fx_handles={}
gd={log=function()end,command=function(n,f)commands[n]=f end,
 stage_view=function(a,b)views[#views+1]={a,b}end,
 player=function()return present and {} or nil end,
 fx_play=function(...)casts[#casts+1]={...};return 42 end}
""" + Path(__file__).with_name("render_probe.lua").read_text() + r"""
commands.envoy_map('off');commands.envoy_map('on');commands.envoy_map('invalid')
assert(#views==2 and views[1][1]==false and views[2][1]==true)
assert(views[1][2]==false and views[2][2]==false)
present=false;commands.envoy_fx_probe('cinder');assert(#casts==0)
present=true;commands.envoy_fx_probe('invalid');assert(#casts==0)
commands.envoy_fx_probe('cinder');commands.envoy_fx_probe('rime')
assert(#casts==2 and casts[1][1]=='RogueCinderRelease' and casts[2][1]=='RogueRimeRelease')
assert(casts[1][2]==1 and casts[1][5]==16 and #fx_handles==2 and fx_handles[1]==42)
print('PASS probe validation and ownership')
"""
        result = subprocess.run([lua, "-"], input=code, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
