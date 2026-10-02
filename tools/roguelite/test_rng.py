#!/usr/bin/env python3
"""Exercise rng.lua determinism, stream independence and bounded selection."""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / 'melee/worktrees/linux/pc/scripts/examples/roguelite/rng.lua'
LUA = shutil.which('lua5.4') or shutil.which('lua')
assert LUA, 'Lua interpreter required'

TEST = r'''
local R=dofile(arg[1])
local MOD=R.modulus
-- Named streams are reproducible and mutually independent.
local a1=R.new(12345,'topology'); local a2=R.new(12345,'topology')
local b=R.new(12345,'encounters')
local seen={}
for i=1,50 do local x=a1:int(); assert(x>=1 and x<MOD); assert(x==a2:int(),'stream drift'); seen[i]=x end
local overlap=0
for i=1,50 do if b:int()==seen[i] then overlap=overlap+1 end end
assert(overlap==0,'independent streams coincide')
assert(R.new(12345,'topology').count==0)
-- A different base or name changes the stream.
assert(R.derive(1,'a')~=R.derive(2,'a'))
assert(R.derive(1,'a')~=R.derive(1,'b'))
-- Bounds and ranges stay in range across many draws.
local r=R.new(7,'bounds')
for i=1,2000 do local v=r:range(-3,9); assert(v>=-3 and v<=9 and v%1==0) end
for i=1,2000 do local v=r:below(14); assert(v>=1 and v<=14) end
-- Weighted selection only returns declared values and respects zero weight.
local w=R.new(9,'weights')
local counts={}
for i=1,3000 do local v=w:weighted({{value='x',weight=3},{value='y',weight=1},{value='z',weight=0}}); assert(v=='x' or v=='y'); counts[v]=(counts[v] or 0)+1 end
assert(counts.x>counts.y and counts.y>0,'weighting not reflected')
-- Shuffle is a permutation and deterministic.
local src={} for i=1,20 do src[i]=i end
local s1=R.new(4,'shuffle'):shuffle(src)
local s2=R.new(4,'shuffle'):shuffle(src)
assert(#s1==20)
for i=1,20 do assert(s1[i]==s2[i],'shuffle not reproducible') end
local sum=0 for _,v in ipairs(s1) do sum=sum+v end
assert(sum==210)
-- sorted_keys is order-independent.
local t={z=1,a=2,m=3}
local ks=R.sorted_keys(t)
assert(ks[1]=='a' and ks[2]=='m' and ks[3]=='z')
-- Invalid input is refused.
assert(not pcall(R.new,0,'x'))
assert(not pcall(R.new,1,''))
assert(not pcall(R.new,1,string.rep('a',65)))
assert(not pcall(function() R.new(1,'x'):range(5,4) end))
assert(not pcall(function() R.new(1,'x'):below(0) end))
assert(not pcall(function() R.new(1,'x'):weighted({{value=1,weight=0}}) end))
print('rng: derivation, independence, bounds, weighting, shuffle and refusal passed')
'''
subprocess.run([LUA, '-', str(MODULE)], input=TEST, text=True, check=True)
