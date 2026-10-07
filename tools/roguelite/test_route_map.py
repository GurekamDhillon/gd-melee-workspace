#!/usr/bin/env python3
"""Exercise the discovered-map view: visibility, gates, spoilers, ordering, refusal."""
from pathlib import Path
import shutil
import subprocess
from tools.test_support import require_game
require_game('pc/scripts/examples/roguelite')
import game_source

ROOT = Path(__file__).resolve().parents[2]
RT = game_source.ROGUELITE
LUA = shutil.which('lua5.4') or shutil.which('lua')
assert LUA, 'Lua interpreter required'

MODULES = [RT / name for name in ('progress.lua', 'route_map.lua')]

TEST = r'''
local Progress=dofile(arg[1]); local RouteMap=dofile(arg[2])
local function clone(v) if type(v)~='table' then return v end local o={} for k,x in pairs(v) do o[k]=clone(x) end return o end
-- Keys are emitted in sorted order so two builds compare byte-for-byte.
local function serialize(v)
 local t=type(v)
 if t=='nil' then return 'nil' end
 if t=='string' then return string.format('%q',v) end
 if t=='number' or t=='boolean' then return tostring(v) end
 if t~='table' then return '<'..t..'>' end
 local parts={}
 for k,x in pairs(v) do parts[#parts+1]=serialize(k)..'='..serialize(x) end
 table.sort(parts)
 return '{'..table.concat(parts,',')..'}'
end
local function exit_of(map,room_id,edge_id)
 for _,e in ipairs(map.exits[room_id] or {}) do if e.edge==edge_id then return e end end
end
local function s(id,side,edge) return {id=id,side=side,edge=edge} end
-- Hand-built schema-v2 manifest matching topology.build(): rooms_by_id,
-- edges_by_id and a locks map; r004/r005 stay undiscovered.
local manifest={
 schema_version=2, world_seed=9911,
 generation_report={topology_signature='spine|opt=reward|shortcut=1'},
 rooms_by_id={
  r001={id='r001',title='Threshold',role='entry',theme='cobalt',depth=0,mandatory=true,
        sockets_by_id={out=s('out','right','e001')}},
  r002={id='r002',title='Court',role='combat',theme='fire',depth=1,mandatory=true,
        reward='reward_secret',encounter='enc_secret',
        sockets_by_id={enter=s('enter','left','e001'),out=s('out','right','e002'),down=s('down','bottom','e003')}},
  r003={id='r003',title='Vault',role='reward',theme='fire',depth=2,mandatory=false,
        reward='reward_taken',
        sockets_by_id={enter=s('enter','left','e002'),out=s('out','right','e004'),down=s('down','bottom','e005')}},
  r004={id='r004',title='Deep Vault',role='reward',theme='frost',depth=3,mandatory=false,
        reward='reward_locked',
        sockets_by_id={top=s('top','top','e003'),left=s('left','left','e004')}},
  r005={id='r005',title='Hidden Vault',role='reward',theme='cobalt',depth=3,mandatory=false,
        reward='reward_hidden',
        sockets_by_id={enter=s('enter','left','e005')}},
 },
 edges_by_id={
  e001={id='e001',from_room='r001',from_socket='out',to_room='r002',to_socket='enter',direction='both',kind='main',discovery_rule='always'},
  e002={id='e002',from_room='r002',from_socket='out',to_room='r003',to_socket='enter',direction='both',kind='branch',discovery_rule='always'},
  e003={id='e003',from_room='r002',from_socket='down',to_room='r004',to_socket='top',direction='forward',kind='branch',gate_rule='frost_gate',discovery_rule='hidden'},
  e004={id='e004',from_room='r003',from_socket='out',to_room='r004',to_socket='left',direction='backward',kind='shortcut',discovery_rule='always'},
  e005={id='e005',from_room='r003',from_socket='down',to_room='r005',to_socket='enter',direction='both',kind='branch',gate_rule='timed_vault',discovery_rule='always'},
 },
 locks={
  frost_gate={id='frost_gate',version=1,kind='persistent_key',key='frost_key',theme='frost'},
  timed_vault={id='timed_vault',version=1,kind='consumable_key',key='vault_charge',theme='any'},
 },
}
-- A real Progress.new record, then flags set directly so r004/r005 stay unknown
-- even though their edges are revealed.
local p=Progress.new('run1','r001')
p.current_room='r002'; p.visited.r002=true; p.discovered.r002=true; p.discovered.r003=true
p.revealed.e001=true; p.revealed.e002=true; p.revealed.e003=true; p.revealed.e004=true; p.revealed.e005=true
p.claimed.reward_taken=true
assert(Progress.validate(p))
local map=assert(RouteMap.build(manifest,p))
assert(RouteMap.version==1)
assert(map.current=='r002' and map.world_seed==9911 and map.topology_signature=='spine|opt=reward|shortcut=1')
assert(map.counts.discovered_rooms==3 and map.counts.known_exits==6 and map.counts.undiscovered_reward_count==2,serialize(map.counts))
assert(map.rooms.r004==nil and map.rooms.r005==nil,'undiscovered rooms leaked')
assert(map.rooms.r001 and map.rooms.r002 and map.rooms.r003)
assert(map.rooms.r002.current and not map.rooms.r001.current)
assert(map.rooms.r001.visited and not map.rooms.r003.visited)
-- Revealed-vs-unrevealed and hidden exits, plus the one-way edge's origin.
local e=exit_of(map,'r001','e001')
assert(e and e.to=='r002' and e.side=='right' and e.hidden==false and e.destination_discovered==true and e.gate==nil and e.gate_open==true)
e=exit_of(map,'r002','e003')
assert(e and e.to=='r004' and e.side=='bottom' and e.hidden==true and e.destination_discovered==false)
assert(e.gate=='frost_gate' and e.gate_open==false,'closed persistent gate must read closed')
assert(exit_of(map,'r002','e002') and exit_of(map,'r003','e002') and exit_of(map,'r003','e005'))
assert(not exit_of(map,'r003','e004'),'backward edge leaked as an exit from its origin')
assert(#map.exits.r001==1 and #map.exits.r002==3 and #map.exits.r003==2)
-- Gate table: persistent closed without the key, consumable closed with no stock.
assert(map.locks.frost_gate.kind=='persistent_key' and map.locks.frost_gate.key=='frost_key')
assert(map.locks.frost_gate.has_key==false and map.locks.frost_gate.opened==false)
assert(map.locks.timed_vault.kind=='consumable_key' and map.locks.timed_vault.has_key==false and map.locks.timed_vault.opened==false)
-- Persistent open once the key is held; consumable open via stock or an opener.
local pb=clone(p); pb.keys.frost_key=true; pb.consumables.vault_charge=2
local mb=assert(RouteMap.build(manifest,pb))
assert(exit_of(mb,'r002','e003').gate_open==true and exit_of(mb,'r003','e005').gate_open==true)
assert(mb.locks.frost_gate.has_key==true and mb.locks.timed_vault.has_key==true)
local pc=clone(p); pc.opened.timed_vault=true
local mc=assert(RouteMap.build(manifest,pc))
assert(exit_of(mc,'r003','e005').gate_open==true)
assert(mc.locks.timed_vault.opened==true and mc.locks.timed_vault.has_key==false)
assert(exit_of(mc,'r002','e003').gate_open==false)
-- An unknown lock kind is closed, never optimistically open.
local mx=clone(manifest); mx.locks.frost_gate.kind='mystery'
assert(exit_of(assert(RouteMap.build(mx,p)),'r002','e003').gate_open==false)
-- Spoiler boundary: no reward or encounter id appears anywhere in the map.
local text=serialize(map)
for _,needle in ipairs({'reward_secret','reward_taken','reward_locked','reward_hidden','enc_secret'}) do
 assert(not text:find(needle,1,true),'spoiler leaked: '..needle)
end
for id,room in pairs(map.rooms) do assert(room.reward==nil and room.encounter==nil) end
assert(map.rooms.r002.reward_claimed==false and map.rooms.r003.reward_claimed==true)
-- Deterministic ordering: two builds serialize identically.
assert(serialize(map)==serialize(assert(RouteMap.build(manifest,p))),'map build not deterministic')
-- Controlled refusal, never a throw.
for _,case in ipairs({{nil,p},{manifest,nil},{42,p},{manifest,'x'},{manifest,42}}) do
 local r,why=RouteMap.build(case[1],case[2])
 assert(r==nil and type(why)=='string' and #why>0,'malformed input not refused')
end
local bad=clone(manifest); bad.schema_version=1
local r,why=RouteMap.build(bad,p); assert(r==nil and type(why)=='string')
local pv=clone(p); pv.version=1
r,why=RouteMap.build(manifest,pv); assert(r==nil and type(why)=='string')
local norooms=clone(manifest); norooms.rooms_by_id=nil
r,why=RouteMap.build(norooms,p); assert(r==nil and type(why)=='string')
local noflags=clone(p); noflags.revealed=nil
r,why=RouteMap.build(manifest,noflags); assert(r==nil and type(why)=='string')
print('route map: discovery, exit visibility, gates, spoiler boundary, determinism and refusal passed')
'''

subprocess.run([LUA, '-', *[str(m) for m in MODULES]], input=TEST, text=True, check=True)
