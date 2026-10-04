#!/usr/bin/env python3
"""Exercise legacy TBD1/TBD2 migration to TBD3 with the frozen v1 generator."""
from pathlib import Path
import shutil
import subprocess
import sys
import hashlib
import game_source

ROOT = Path(__file__).resolve().parents[2]
RT = game_source.ROGUELITE
FIXTURES = ROOT / '_build/roguelite-validation-saves/legacy-v1'
LUA = shutil.which('lua5.4') or shutil.which('lua')
assert LUA, 'Lua interpreter required'
# Pin the frozen generator to historical 7a91c0a29, not the generator under test.
assert hashlib.sha256((RT / 'dungeon_v1.lua').read_bytes().replace(b'\r\n', b'\n')).hexdigest() == '80fac102a349c8308196a179fe768a0a377cdf020d35d3d427179254651569f5', 'frozen historical V1 generator changed'

MODULES = [RT / name for name in ('rng.lua', 'core.lua', 'codec.lua', 'checkpoint.lua', 'progress.lua', 'dungeon_v1.lua', 'legacy.lua')]

PRELUDE = r'''
local RNG=dofile(arg[1]); local Core=dofile(arg[2]); local Codec=dofile(arg[3])
local Checkpoint=dofile(arg[4]); local Progress=dofile(arg[5]); local V1=dofile(arg[6]); local Legacy=dofile(arg[7])
local deps={core=Core,codec=Codec,checkpoint=Checkpoint,v1=V1}
'''

TEST = r'''
local profile=Core.new_profile(2024)
local run=Core.new_run(profile)
local ptext,rtext=assert(Core.snapshot(profile)),assert(Core.snapshot(run))
local roster='ROSTER1 falco/c0\nROSTER1 link/c1\n'
local function tbd2() return string.format('TBD2 %d %d %d %d\n%s%s%s',12,#ptext,#rtext,#roster,ptext,rtext,roster) end
local parsed=assert(Legacy.parse(tbd2()))
assert(parsed.version==2 and parsed.generation==12 and parsed.roster_text==roster)
-- Migration reproduces the frozen v1 route exactly and preserves progress room.
local migrated=assert(Legacy.migrate(tbd2(),deps))
local back=assert(Checkpoint.decode(migrated,Core,Codec))
assert(back.generation==12 and back.profile.id==profile.id and back.run.id==run.id)
assert(back.roster==roster)
local expected=assert(V1.generate(run.world_seed))
local old=expected.nodes.trail.room
assert(old.floor.left==-65 and old.floor.right==65 and old.spawn.x==-42)
assert(old.kit.unit==6.5 and old.kit.grid==13 and old.kit.bay==26 and old.kit.height==26)
assert(old.exit_anchors.left.x==-52 and old.exit_anchors.right.x==52)
assert(old.platforms[1].y==12 and old.platforms[3].y==24 and old.platforms[1].ledges)
assert(old.platforms[1].width==22 and old.platforms[3].width==24)
assert(Codec.encode(back.manifest)==Codec.encode(expected),'manifest not byte-identical to v1 route')
assert(back.manifest.nodes[run.progress.room],'progress room missing after migration')
-- TBD1 has no roster and no manifest section, and still migrates.
local tbd1=string.format('TBD1 %d %d %d\n%s%s',7,#ptext,#rtext,ptext,rtext)
local p1=assert(Legacy.parse(tbd1)); assert(p1.version==1 and p1.roster_text==nil)
local m1=assert(Legacy.migrate(tbd1,deps))
local b1=assert(Checkpoint.decode(m1,Core,Codec))
assert(b1.generation==7 and b1.roster==nil and b1.manifest.nodes[run.progress.room])
-- Refusals: unknown version, truncation, foreign owner, malformed.
assert(not Legacy.parse('TBD4 1 2 0 0 0 00000000\nab'))
local _,why=Legacy.parse('TBD4 1 2 0 0 0 00000000\nab')
assert(why:find('unsupported',1,true))
assert(not Legacy.parse(tbd2():sub(1,#tbd2()-3)))
assert(not Legacy.parse('garbage'))
assert(not pcall(Legacy.migrate,tbd2(),{}))
local other=Core.new_profile(777)
local forged=string.format('TBD2 1 %d %d 0\n%s%s',#(assert(Core.snapshot(other))),#rtext,assert(Core.snapshot(other)),rtext)
assert(not Legacy.migrate(forged,deps))
-- Progress schema migration: 1 -> 2 adds the missing maps, is not mutated and
-- re-validates; an unknown version is preserved and explained.
local v1={version=1,run_id=run.id,current_room='r001',start_room='r001',
 visited={r001=true},discovered={r001=true},revealed={},claimed={},keys={},
 consumables={},defeated={},objectives={},supplies=2,lives=3}
assert(Progress.version==2)
local up=assert(Legacy.migrate_progress(v1,Progress))
assert(up.version==2 and up.opened and up.pickups and up.encounter_kos)
assert(Progress.validate(up))
assert(v1.version==1 and v1.opened==nil,'migration must not mutate the input')
local v2={version=2,run_id=run.id,current_room='r001',start_room='r001',
 visited={r001=true},discovered={r001=true},revealed={},claimed={},keys={},
 consumables={},defeated={},objectives={},opened={},pickups={},encounter_kos={},supplies=2,lives=3}
assert(Legacy.migrate_progress(v2,Progress)==v2)
local _,mwhy=Legacy.migrate_progress({version=3},Progress)
assert(mwhy and mwhy:find('unsupported progress version',1,true) and mwhy:find('preserved',1,true))
assert(not Legacy.migrate_progress({version=1,run_id='r',current_room='x',start_room='x',supplies=99,lives=3},Progress))
assert(not Legacy.migrate_progress('nope',Progress))
print('legacy: TBD1/TBD2 parse, v1 route reconstruction, TBD3 wrap and refusal passed')
'''

def run(extra):
    subprocess.run([LUA, '-', *[str(m) for m in MODULES], *extra], input=PRELUDE + TEST, text=True, check=True)

def fixture_check():
    a = FIXTURES / 'checkpoint-a.txt'
    b = FIXTURES / 'checkpoint-b.txt'
    if not a.exists() or not b.exists():
        return
    program = r'''
local RNG=dofile(arg[1]); local Core=dofile(arg[2]); local Codec=dofile(arg[3])
local Checkpoint=dofile(arg[4]); local Progress=dofile(arg[5]); local V1=dofile(arg[6]); local Legacy=dofile(arg[7])
local deps={core=Core,codec=Codec,checkpoint=Checkpoint,v1=V1}
for _,path in ipairs({arg[8],arg[9]}) do
 local f=assert(io.open(path,'r')); local text=f:read('a'); f:close()
 local migrated,why=Legacy.migrate(text,deps)
 assert(migrated,'frozen fixture failed migration: '..tostring(why))
 local back=assert(Checkpoint.decode(migrated,Core,Codec))
 if back.run then
  local expected=assert(V1.generate(back.run.world_seed))
  assert(Codec.encode(back.manifest)==Codec.encode(expected),'fixture route mismatch')
  assert(back.manifest.nodes[back.run.progress.room],'fixture progress room missing')
 end
end
print('legacy: frozen development checkpoint fixtures migrate to TBD3')
'''
    subprocess.run([LUA, '-', *[str(m) for m in MODULES], str(a), str(b)], input=program, text=True, check=True)

run([])
fixture_check()
