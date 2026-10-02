#!/usr/bin/env python3
"""Exercise the bounded data codec: round trips, limits and injection refusal."""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / 'melee/worktrees/linux/pc/scripts/examples/roguelite/codec.lua'
LUA = shutil.which('lua5.4') or shutil.which('lua')
assert LUA, 'Lua interpreter required'

TEST = r'''
local C=dofile(arg[1])
local function round(v) local t=assert(C.encode(v)); local d=assert(C.decode(t)); assert(C.encode(d)==t,'round trip drift'); return d end
-- Arrays keep order and length; objects keep keys.
local arr=round({10,20,30}); assert(#arr==3 and arr[1]==10 and arr[3]==30)
local obj=round({name='x',nested={a=1,b={true,false}},flag=true}); assert(obj.name=='x' and obj.nested.a==1 and obj.nested.b[2]==false and obj.flag==true)
assert(C.encode({})=='{}')
assert(C.encode({1,2})=='[1,2]')
-- Floating point and integer strings survive.
local nums=round({1.5,-0.25,1e10,0,-3}); assert(nums[1]==1.5 and nums[3]==1e10 and nums[5]==-3)
-- Escape handling for controls and quotes.
local s=round('a"b\\c\nd\te'); assert(s=='a"b\\c\nd\te')
local u=round(string.char(1)..string.char(127)); assert(u==string.char(1)..string.char(127))
-- Deterministic: key order does not change the encoding.
assert(C.encode({b=1,a=2})==C.encode({a=2,b=1}))
-- Object numeric keys 1..64 canonicalize to strings.
local mixed=round({['1']='a',['64']='b'}); assert(mixed['1']=='a' and mixed['64']=='b')
-- Numeric-only contiguous tables are arrays and preserve numeric keys.
local arr2=round({[1]='a',[2]='b'}); assert(arr2[1]=='a' and arr2[2]=='b')
-- A non-contiguous integer object is an object; numeric keys become strings.
local gap=round({[2]='a'}); assert(gap['2']=='a' and gap[2]==nil)
-- A number key and its string twin collide and must be refused, never emitted
-- as an undecodable duplicate.
assert(not C.encode({[1]='numeric',['1']='string'}))
-- Key-collision detection does not change ordinary objects or arrays.
assert(C.encode({a=1,b=2})==C.encode({b=2,a=1}))
assert(C.encode({10,20,30})=='[10,20,30]')
-- Every accepted value round-trips under the declared contract.
for _,v in ipairs({{}, {1,2,3}, {['1']='a'}, {[2]='a'}, {a={b={c=true}}}}) do
 local encoded=assert(C.encode(v)); assert(C.encode(assert(C.decode(encoded)))==encoded)
end
-- Refusals: executable/metatable/nonfinite/oversized. Encode returns nil,err.
assert(not C.encode(setmetatable({},{__index={}})))
assert(not C.encode(print))
assert(not C.encode(0/0))
assert(not C.encode(math.huge))
assert(not C.encode(string.rep('a',513)))
assert(not C.encode({[65]='x'}))
local deep={} local cur=deep for i=1,40 do cur[1]={} cur=cur[1] end assert(not C.encode(deep))
-- Decoder refusals return nil,err.
assert(not C.decode('{'))
assert(not C.decode('{"x":1,"x":2}'))
assert(not C.decode('01'))
assert(not C.decode('1.'))
assert(not C.decode('1e'))
assert(not C.decode('[1,2,]'))
assert(not C.decode('{"k":}'))
assert(not C.decode('{"k":1}junk'))
assert(not C.decode('{"k":"\\ud800"}'))
assert(not C.decode('{"k":"\\q"}'))
assert(not C.decode(string.rep('[',30)..string.rep(']',30)))
assert(not C.decode(42))
assert(C.decode('{"a":[1,{"b":true}]}').a[2].b==true)
print('codec: round trips, key order, escape handling, limits and injection refusal passed')
'''
subprocess.run([LUA, '-', str(MODULE)], input=TEST, text=True, check=True)
