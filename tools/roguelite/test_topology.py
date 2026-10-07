#!/usr/bin/env python3
"""Property suite for the variable topology generator and progression rules.

Runs the real pure Lua modules. It does not spawn a game; a live route check is
a separate gate. Adversarial fixtures assert that validation rejects malformed
graphs instead of silently accepting them.
"""
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

MODULES = [RT / name for name in ('rng.lua', 'room_catalogue.lua', 'encounter_catalogue.lua',
                                  'progression.lua', 'topology.lua', 'codec.lua')]

PRELUDE = r'''
local RNG=dofile(arg[1]); local Rooms=dofile(arg[2]); local Enc=dofile(arg[3])
local Prog=dofile(arg[4]); local Top=dofile(arg[5]); local Codec=dofile(arg[6])
assert(Rooms.validate() and Enc.validate())
local t=Top.new(Rooms,Enc,Prog,RNG)
local function clone(v) if type(v)~='table' then return v end local o={} for k,x in pairs(v) do o[k]=clone(x) end return o end
local function reject(m,needle) local ok,why=Top.validate(t,m); assert(not ok,'invalid fixture accepted: '..tostring(needle)); assert(why:find(needle,1,true),why) end
'''

TEST = r'''
-- 1000 ordinary seeds: valid, reproducible, bounded, structurally varied.
local signatures,counts,fallbacks={},{},0
for seed=1,1000 do
 local m=t:generate(seed)
 local ok,why=Top.validate(t,m); assert(ok,why)
 assert(Top.signature(m)==Top.signature(t:generate(seed)),'non-reproducible seed '..seed)
 assert(m.generation_report.fallback_used==false,'ordinary seed fell back')
 local n=#m.order; assert(n>=12 and n<=18,'room count '..n)
 assert(#m.spine>=8 and #m.spine<=12,'spine '..#m.spine)
 signatures[m.generation_report.topology_signature]=true
 counts[n]=(counts[n] or 0)+1
end
local ns,nc=0,0 for _ in pairs(signatures) do ns=ns+1 end for _ in pairs(counts) do nc=nc+1 end
assert(ns>=20,'only '..ns..' topology signatures')
assert(nc>=3,'only '..nc..' room counts')
-- A resolved manifest survives the bounded data codec byte-for-byte.
local sample=t:generate(424242)
local encoded=Codec.encode(sample); assert(encoded,'manifest did not encode')
assert(encoded==Codec.encode(t:generate(424242)))
local decoded=assert(Codec.decode(encoded))
assert(Top.signature(decoded)==Top.signature(sample))
assert(sample.stream_versions and sample.stream_versions.topology==1,'stream versions missing')
-- A saved manifest from another catalogue version is preserved as data; only
-- regeneration is refused, so an update cannot relocate a saved doorway.
local stale=Codec.decode(encoded); stale.catalogue_version=0
assert(Codec.decode(Codec.encode(stale)).catalogue_version==0)
local sv,swhy=Top.validate(t,stale); assert(not sv and tostring(swhy):find('version mismatch',1,true))
-- Locks/keys appear and are always satisfiable; the key is on a mandatory room.
local locked,keys=0,0
for seed=1,300 do
 local m=t:generate(seed)
 for id,room in pairs(m.rooms_by_id) do if room.grants_key then keys=keys+1 end end
 for id,edge in pairs(m.edges_by_id) do
  if edge.gate_rule then
   locked=locked+1
   local lock=m.locks[edge.gate_rule]; assert(lock)
   local granted=false
   for _,room in pairs(m.rooms_by_id) do if room.grants_key==lock.key and room.mandatory then granted=true end end
   assert(granted,'lock key never granted on a mandatory room')
  end
 end
end
assert(locked>0,'no locks generated across seeds')
assert(keys>0,'no keys generated across seeds')
-- Stream independence: content streams never perturb topology structure. Adding
-- a reward (and so changing the encounter/reward streams) leaves the graph shape
-- identical for the same seed.
local mutatedEnc=clone(Enc)
mutatedEnc.rewards.extra_reward={id='extra_reward',version=1,kind='upgrade',stat='potency',delta=1,family='any'}
local t2=Top.new(Rooms,mutatedEnc,Prog,RNG)
for seed=1,40 do
 assert(Top.signature(t2:generate(seed))==Top.signature(t:generate(seed)),'stream bleed at seed '..seed)
end
-- Adversarial fixtures are refused.
local function first_socket(room) for sid in pairs(room.sockets_by_id) do return sid end end
local base=t:generate(77)
local m=clone(base); m.edges_by_id[next(m.edges_by_id)].to_room='ghost'; reject(m,'endpoint missing')
m=clone(base); local eid=next(m.edges_by_id); m.edges_by_id[eid].from_socket='nope'; reject(m,'socket missing')
m=clone(base); local sr=m.rooms_by_id[m.start_room]; sr.sockets_by_id[first_socket(sr)].edge='ghost'; reject(m,'dangling')
m=clone(base); m.rooms_by_id[m.final_room].theme='void'; reject(m,'invalid theme')
m=clone(base); m.rooms_by_id[m.start_room].role='bogus'; reject(m,'invalid role')
m=clone(base); m.spine[1]='ghost'; reject(m,'spine references unknown room')
m=clone(base); m.edges_by_id[next(m.edges_by_id)].gate_rule='missing_lock'; reject(m,'unknown gate lock')
-- Removing the final room's edges must be rejected as unreachable.
m=clone(base)
local victim=m.rooms_by_id[m.final_room]
for sid,socket in pairs(victim.sockets_by_id) do
 if socket.edge then
  local edge=m.edges_by_id[socket.edge]
  local other=edge.from_room==m.final_room and edge.to_room or edge.from_room
  local other_socket=edge.from_room==other and edge.from_socket or edge.to_socket
  m.rooms_by_id[other].sockets_by_id[other_socket].edge=nil
  m.edges_by_id[socket.edge]=nil
  socket.edge=nil
 end
end
reject(m,'unreachable')
-- A gate with an unattainable key must fail progression, not just structure.
m=clone(base)
local gate_target
for id,edge in pairs(m.edges_by_id) do if edge.from_room==m.start_room or edge.to_room==m.start_room then gate_target=id end end
assert(gate_target,'entry edge missing')
m.edges_by_id[gate_target].gate_rule='frost_gate'
m.locks['frost_gate']={id='frost_gate',version=1,kind='persistent_key',key='never_granted',theme='frost'}
for _,room in pairs(m.rooms_by_id) do if room.grants_key=='never_granted' then room.grants_key=nil end end
reject(m,'unreachable')
-- Invalid seeds are refused, never clamped.
assert(not pcall(t.generate,t,0)); assert(not pcall(t.generate,t,-4)); assert(not pcall(t.generate,t,2147483647))
-- Theme contracts: a template that declares a theme must produce rooms with
-- that theme, and every generated route still validates. The assigned
-- primary/secondary stream is otherwise untouched.
local themed,mismatches=0,0
for seed=1,100 do
 local m=t:generate(seed)
 assert(Top.validate(t,m))
 for _,room in pairs(m.rooms_by_id) do
  local template=Rooms.rooms[room.template_id]
  if template.theme then
   themed=themed+1
   if room.theme~=template.theme then mismatches=mismatches+1 end
  end
 end
end
assert(themed>0,'no declared-theme templates were generated across 100 seeds')
assert(mismatches==0,'theme contract violated for '..mismatches..' of '..themed..' themed rooms')
-- A compatible-template constraint without a declared theme still lets the
-- generator assign any valid theme.
for _,id in ipairs(t:generate(4242).order) do
 local room=t:generate(4242).rooms_by_id[id]
 assert(Rooms.themes[room.theme],'unknown generated theme')
end
print('topology: 1000 seeds, reproducibility, '..ns..' signatures, locks/keys, theme contracts ('..themed..' themed rooms) and adversarial refusal passed')
'''

subprocess.run([LUA, '-', *[str(m) for m in MODULES]], input=PRELUDE + TEST, text=True, check=True)
