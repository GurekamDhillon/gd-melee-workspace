#!/usr/bin/env python3
"""World-seed allocation: successive runs must differ, explicit seeds reproduce.

Regression for plan trap #2: Core.new_run previously derived every run seed from
the unchanged profile seed, so successive runs repeated the dungeon.
"""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / 'melee/worktrees/linux/pc/scripts/examples/roguelite/core.lua'
LUA = shutil.which('lua5.4') or shutil.which('lua')
assert LUA, 'Lua interpreter required'

TEST = r'''
local C=assert(loadfile(arg[1]))()
local function seed_ok(x) return type(x)=='number' and x%1==0 and x>=1 and x<=2147483646 end
local p=C.new_profile(31337)
assert(p.world_seed,'profile must carry a world seed')
-- Successive runs advance the world stream.
local seen={}
for i=1,25 do
 local r=C.new_run(p)
 assert(seed_ok(r.world_seed))
 seen[r.world_seed]=(seen[r.world_seed] or 0)+1
 assert(seen[r.world_seed]==1,'repeated world seed on run '..i)
end
-- Explicit seeds are reproducible and independent of the counter, but still
-- advance the profile so later default runs differ.
local a=C.new_run(p,{seed=999}); local b=C.new_run(p,{seed=999})
assert(a.world_seed==999 and b.world_seed==999)
local c=C.new_run(p)
assert(c.world_seed~=999,'default run must diverge from an explicit seed')
-- The world seed survives a snapshot round trip and acquisition does not move it.
local r=C.new_run(p); local ws=r.world_seed
local restored=assert(C.restore(assert(C.snapshot(r))))
assert(restored.world_seed==ws)
C.acquire(r,'cinder')
assert(r.world_seed==ws and r.seed~=ws,'acquisition must not move the world seed')
-- A legacy profile without world_seed still starts runs deterministically.
local legacy=C.new_profile(5150); legacy.world_seed=nil
assert(C.restore(assert(C.snapshot(legacy))).world_seed==nil)
local l1=C.new_run(legacy); local l2=C.new_run(legacy)
assert(seed_ok(l1.world_seed) and l1.world_seed~=l2.world_seed)
print('world seed: per-run advancement, explicit reproducibility, persistence and legacy fallback passed')
'''

subprocess.run([LUA, '-', str(CORE)], input=TEST, text=True, check=True)
