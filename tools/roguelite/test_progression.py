#!/usr/bin/env python3
"""Regression suite for the progression validator.

Covers the revisit-carry defect (an idempotent objective bitmask) plus
persistent/consumable key accounting and malformed locks.
"""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
MODULE = ROOT / 'melee/worktrees/linux/pc/scripts/examples/roguelite/progression.lua'
LUA = shutil.which('lua5.4') or shutil.which('lua')
assert LUA, 'Lua interpreter required'

TEST = r'''
local P=dofile(arg[1])
local function room(id, fields) fields=fields or {}; fields.id=id; return fields end
local function edge(id,a,b,gate) return {id=id,from_room=a,to_room=b,gate_rule=gate,direction='both'} end

-- Revisit-carry reproduction: A<->B and A<->F are traversable, D is a mandatory
-- room wired to nothing. A correct validator must fail: no path visits D. The
-- old arithmetic marked D complete when A/B were revisited (1+2 carry).
local carry={start_room='A',final_room='F',spine={'A','D','F'},
 rooms_by_id={A=room('A'),B=room('B'),D=room('D'),F=room('F')},
 edges_by_id={e1=edge('e1','A','B'),e2=edge('e2','A','F')},locks={}}
local ok,why=P.validate(carry); assert(not ok,'revisit carry falsely completed the run: '..tostring(why))
-- Positive control: wire D in and the same graph must complete.
carry.edges_by_id.e3=edge('e3','A','D')
assert(P.validate(carry))
-- An isolated mandatory room must fail even though start/finish are connected.
local unreachable={start_room='A',final_room='F',spine={'A','B','F'},
 rooms_by_id={A=room('A'),B=room('B'),F=room('F')},
 edges_by_id={e1=edge('e1','A','F')},locks={}}
assert(not P.validate(unreachable),'unreachable required room accepted')

-- Persistent key gates.
local function persistent(grant_room)
 local m={start_room='A',final_room='F',spine={'A','B','F'},
  rooms_by_id={A=room('A'),B=room('B'),F=room('F')},
  edges_by_id={e1=edge('e1','A','B','g'),e2=edge('e2','B','F')},
  locks={g={id='g',version=1,kind='persistent_key',key='k'}}}
 if grant_room then m.rooms_by_id[grant_room].grants_key='k' end
 return m
end
assert(not P.validate(persistent(nil)),'gate opened without a key')
assert(P.validate(persistent('A')),'key before the gate should open it')
assert(not P.validate(persistent('F')),'key granted after the gate must not open it')

-- Consumable keys: resource-aware search, not a boolean has_key.
local function consumable(second_grant)
 local m={start_room='A',final_room='F',spine={'A','B','F'},
  rooms_by_id={A=room('A',{grants_consumable={k=1}}),B=room('B'),F=room('F')},
  edges_by_id={e1=edge('e1','A','B','g'),e2=edge('e2','B','F','g')},
  locks={g={id='g',version=1,kind='consumable_key',key='k'}}}
 if second_grant then m.rooms_by_id.B.grants_consumable={k=1} end
 return m
end
assert(P.validate(consumable(true)),'two consumable keys should open both gates')
assert(not P.validate(consumable(false)),'one consumable key cannot open two gates')

-- Malformed locks and manifests are refused.
local m=persistent('A'); m.edges_by_id.e1.gate_rule='missing'
local ok2,why2=P.validate(m); assert(not ok2 and tostring(why2):find('unknown lock',1,true))
m=persistent('A'); m.locks.g.kind='bogus'; assert(not P.validate(m))
assert(not P.validate({}))
print('progression: revisit-carry regression, persistent/consumable keys and refusal passed')
'''

subprocess.run([LUA, '-', str(MODULE)], input=TEST, text=True, check=True)
