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
local progress=Codec.encode({version=2,run_id=run.id,current_room='r001',start_room='r001',visited={r001=true},discovered={r001=true},revealed={},claimed={},keys={},consumables={},defeated={},objectives={},opened={},pickups={},encounter_kos={},supplies=2,lives=3})
local function fields() return {generation=5,profile=assert(Core.snapshot(profile)),run=assert(Core.snapshot(run)),manifest=manifest,roster='ROSTER1 falco/c0\n',progress=progress} end
'''

TEST = r'''
-- Round trip preserves every generation.
local text=Checkpoint.encode(fields())
local back=assert(Checkpoint.decode(text,Core,Codec))
assert(back.generation==5 and back.profile.type=='profile' and back.run.type=='run')
assert(back.manifest.world_seed==run.world_seed and back.manifest.rooms[3]==3)
assert(back.roster=='ROSTER1 falco/c0\n')
assert(back.progress and back.progress.run_id==run.id and back.progress.current_room=='r001','progress section missing')
assert(Checkpoint.encode(fields())==text,'encoding not deterministic')
-- The earlier roster-only 5-length header still decodes (progress absent).
local ptext=assert(Core.snapshot(profile)); local roster='ROSTER1 falco/c0\n'
local oldbody=ptext..roster
local oldform=string.format('TBD3 5 %d 0 0 %d %s\n%s',#ptext,#roster,Checkpoint.checksum(oldbody),oldbody)
local oldback=assert(Checkpoint.decode(oldform,Core,Codec))
assert(oldback.progress==nil and oldback.roster==roster,'old form must not invent progress')
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
-- A section of the wrong schema version is refused and preserved, never
-- returned as if interchangeable.
local wrong=Checkpoint.encode({generation=1,profile=assert(Core.snapshot(profile)),progress=Codec.encode({version=1,run_id=run.id,current_room='r001',start_room='r001'})})
assert(not Checkpoint.decode(wrong,Core,Codec,{progress_version=2}))
local _,pwhy=Checkpoint.decode(wrong,Core,Codec,{progress_version=2})
assert(pwhy and pwhy:find('progress version',1,true) and pwhy:find('preserved',1,true))
assert(Checkpoint.decode(wrong,Core,Codec,{progress_version=1}))
local badman=Checkpoint.encode({generation=1,profile=assert(Core.snapshot(profile)),manifest=Codec.encode({schema_version=1})})
assert(not Checkpoint.decode(badman,Core,Codec,{manifest_schema=2}))
-- Plural gates accept a supported set and preserve a future inner schema. A v1
-- manifest with no schema_version is treated as its `version` (1).
local supported={manifest_schemas={[1]=true,[2]=true},progress_versions={[1]=true,[2]=true}}
assert(Checkpoint.decode(text,Core,Codec,supported))
local v1man=Checkpoint.encode({generation=3,profile=assert(Core.snapshot(profile)),manifest=Codec.encode({version=1,world_seed=run.world_seed})})
local v1back=assert(Checkpoint.decode(v1man,Core,Codec,supported))
assert(v1back.manifest.version==1)
assert(not Checkpoint.decode(Checkpoint.encode({generation=1,profile=assert(Core.snapshot(profile)),manifest=Codec.encode({schema_version=3})}),Core,Codec,supported))
local _,mswhy=Checkpoint.decode(Checkpoint.encode({generation=1,profile=assert(Core.snapshot(profile)),manifest=Codec.encode({schema_version=3})}),Core,Codec,supported)
assert(mswhy and mswhy:find('manifest schema',1,true) and mswhy:find('preserved',1,true))
local future=Checkpoint.encode({generation=1,profile=assert(Core.snapshot(profile)),progress=Codec.encode({version=3,run_id=run.id,current_room='r001',start_room='r001'})})
assert(not Checkpoint.decode(future,Core,Codec,supported))
local _,fwhy=Checkpoint.decode(future,Core,Codec,supported)
assert(fwhy and fwhy:find('progress version',1,true) and fwhy:find('preserved',1,true))
-- Unknown future versions are preserved with an explanation, not misparsed.
assert(not Checkpoint.decode('TBD4 1 2 0 0 0 00000000\nab',Core,Codec))
local _,why=Checkpoint.decode('TBD4 1 2 0 0 0 00000000\nab',Core,Codec)
assert(why:find('unsupported',1,true) and why:find('preserved',1,true))
-- Malformed header values are refused.
assert(not Checkpoint.decode('TBD3 xx 1 0 0 0 00000000\na',Core,Codec))
assert(not Checkpoint.decode('TBD3 1 999 0 0 0 00000000\na',Core,Codec))
assert(not Checkpoint.decode('not-checkpoint',Core,Codec))
assert(not Checkpoint.decode(42,Core,Codec))
-- Malformed nested sections with a valid envelope/checksum are controlled
-- refusals, and a throwing restore dependency never escapes to the caller.
local function frame(gen,prof,run,man,ros,prog)
 prof,run,man,ros,prog=prof or '',run or '',man or '',ros or '',prog or ''
 local body=prof..run..man..ros..prog
 return string.format('TBD3 %d %d %d %d %d %d %s\n%s',gen,#prof,#run,#man,#ros,#prog,Checkpoint.checksum(body),body)
end
local ptext=assert(Core.snapshot(profile))
local ok_bad,val_bad,why_bad=pcall(Checkpoint.decode,frame(5,ptext,'','{not json','',''),Core,Codec)
assert(ok_bad and val_bad==nil and why_bad:find('manifest section',1,true))
local ok_p,val_p,why_p=pcall(Checkpoint.decode,frame(5,ptext,'','','', '{not json'),Core,Codec)
assert(ok_p and val_p==nil and why_p:find('progress section',1,true))
local ok_pr,val_pr,why_pr=pcall(Checkpoint.decode,frame(5,'not a profile','','','',''),Core,Codec)
assert(ok_pr and val_pr==nil and why_pr:find('profile section',1,true))
local bomb={restore=function() error('restore exploded') end}
local ok_thrown,val_thrown=pcall(Checkpoint.decode,frame(5,ptext,'','','',''),bomb,Codec)
assert(ok_thrown and val_thrown==nil,'decode must contain restore exceptions')
-- The explicit preserve flag distinguishes future versions from corruption.
local _,_,in_schema_preserve=Checkpoint.decode(badman,Core,Codec,{manifest_schemas={[2]=true}})
assert(in_schema_preserve==true)
local _,_,future_outer=Checkpoint.decode('TBD4 1 2 0 0 0 00000000\nab',Core,Codec)
assert(future_outer==true)
local _,_,legacy_outer=Checkpoint.decode('TBD2 1 2 0 0 0 00000000\nab',Core,Codec)
assert(legacy_outer==false)
local _,_,bad_preserve=Checkpoint.decode('TBD3 1 999 0 0 0 00000000\na',Core,Codec)
assert(bad_preserve~=true)
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
