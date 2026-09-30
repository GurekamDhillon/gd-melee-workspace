#!/usr/bin/env python3
"""Exercise the TBD3 checkpoint envelope: integrity, framing and refusal."""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
RT = ROOT / 'melee/worktrees/linux/pc/scripts/examples/roguelite'
LUA = shutil.which('lua5.4') or shutil.which('lua')
assert LUA, 'Lua interpreter required'

MODULES = [RT / name for name in ('rng.lua', 'core.lua', 'codec.lua', 'checkpoint.lua')]

PRELUDE = r'''
local RNG=dofile(arg[1]); local Core=dofile(arg[2]); local Codec=dofile(arg[3]); local Checkpoint=dofile(arg[4])
local profile=Core.new_profile(17029)
local run=Core.new_run(profile)
local manifest=Codec.encode({schema_version=2,world_seed=run.world_seed,rooms={1,2,3}})
local function fields() return {generation=5,profile=assert(Core.snapshot(profile)),run=assert(Core.snapshot(run)),manifest=manifest,roster='ROSTER1 falco/c0\n'} end
'''

TEST = r'''
-- Round trip preserves every generation.
local text=Checkpoint.encode(fields())
local back=assert(Checkpoint.decode(text,Core,Codec))
assert(back.generation==5 and back.profile.type=='profile' and back.run.type=='run')
assert(back.manifest.world_seed==run.world_seed and back.manifest.rooms[3]==3)
assert(back.roster=='ROSTER1 falco/c0\n')
assert(Checkpoint.encode(fields())==text,'encoding not deterministic')
-- No run/roster is also valid.
local minimal=Checkpoint.encode({generation=0,profile=assert(Core.snapshot(profile))})
local m2=assert(Checkpoint.decode(minimal,Core,Codec))
assert(m2.run==nil and m2.manifest==nil and m2.roster==nil)
-- Integrity: a flipped body byte is detected.
local bad_body=text:sub(1,#text-1)..(text:sub(-1)=='X' and 'Y' or 'X')
assert(not Checkpoint.decode(bad_body,Core,Codec))
local head,body=text:match('^(.-)\n(.*)$')
local flipped=body:sub(1,1)==body:sub(2,2) and body:sub(3) or (body:sub(1,1)=='x' and 'y' or 'x')..body:sub(2)
assert(not Checkpoint.decode(head..'\n'..flipped,Core,Codec))
-- Truncation and over-long bodies are refused.
assert(not Checkpoint.decode(text:sub(1,#text-5),Core,Codec))
assert(not Checkpoint.decode(text..'extra',Core,Codec))
-- Unknown future versions are preserved with an explanation, not misparsed.
assert(not Checkpoint.decode('TBD4 1 2 0 0 0 00000000\nab',Core,Codec))
local _,why=Checkpoint.decode('TBD4 1 2 0 0 0 00000000\nab',Core,Codec)
assert(why:find('unsupported',1,true) and why:find('preserved',1,true))
-- Malformed header values are refused.
assert(not Checkpoint.decode('TBD3 xx 1 0 0 0 00000000\na',Core,Codec))
assert(not Checkpoint.decode('TBD3 1 999 0 0 0 00000000\na',Core,Codec))
assert(not Checkpoint.decode('not-checkpoint',Core,Codec))
assert(not Checkpoint.decode(42,Core,Codec))
-- A run owned by a different profile is rejected.
local other=Core.new_profile(99)
local forged=Checkpoint.encode({generation=1,profile=assert(Core.snapshot(other)),run=assert(Core.snapshot(run))})
assert(not Checkpoint.decode(forged,Core,Codec))
-- Encoding refuses invalid fields.
assert(not pcall(Checkpoint.encode,{generation=-1,profile='x'}))
assert(not pcall(Checkpoint.encode,{generation=1,profile=''}))
assert(not pcall(Checkpoint.encode,{generation=1,profile=42}))
-- Oversized body rejected before decode work.
local huge='{'..string.rep('x',1048576)..'}'
assert(not pcall(Checkpoint.encode,{generation=1,profile=huge}))
print('checkpoint: round trip, determinism, integrity, framing and version refusal passed')
'''

subprocess.run([LUA, '-', *[str(m) for m in MODULES]], input=PRELUDE + TEST, text=True, check=True)
