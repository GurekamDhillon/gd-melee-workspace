#!/usr/bin/env python3
"""Validate the audio event map coverage, provenance and refusal."""
from pathlib import Path
import shutil
import subprocess
from tools.test_support import require_game
require_game('pc/scripts/examples/roguelite')
import game_source

ROOT = Path(__file__).resolve().parents[2]
MODULE = game_source.ROGUELITE / 'audio_catalogue.lua'
LUA = shutil.which('lua5.4') or shutil.which('lua')
assert LUA, 'Lua interpreter required'

TEST = r'''
local A=dofile(arg[1])
local ok,why=A.validate(A); assert(ok,why)
local count,unassigned=0,0
for _,e in pairs(A.events) do count=count+1; if e.provenance=='unassigned' then unassigned=unassigned+1 end end
assert(count>=15,'only '..count..' events')
assert(unassigned==count,'no asset may be claimed before sourcing')
-- Every critical tell exists and is flagged.
for _,id in ipairs(A.critical) do assert(A.events[id] and A.events[id].critical) end
-- Adversarial fixtures are refused.
local function clone(v) if type(v)~='table' then return v end local o={} for k,x in pairs(v) do o[k]=clone(x) end return o end
local bad=clone(A); bad.events.menu_focus.bus='void'; assert(not pcall(A.validate,bad))
bad=clone(A); bad.events.enemy_tell.critical=false; assert(not pcall(A.validate,bad))
bad=clone(A); bad.events.reward.asset='x.wav'; assert(not pcall(A.validate,bad))
bad=clone(A); bad.events.menu_focus.concurrency=99; assert(not pcall(A.validate,bad))
print('audio catalogue: coverage, provenance, critical tells and refusal passed')
'''

subprocess.run([LUA, '-', str(MODULE)], input=TEST, text=True, check=True)
