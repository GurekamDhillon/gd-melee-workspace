#!/usr/bin/env python3
"""Regression suite for the progression validator.

Covers: the revisit-carry defect (idempotent objective bitmask); the finite
pickup defect (one-shot claim identity, so a room cannot be farmed for keys);
persistent and consumable gates; opened-door return semantics; independent
sibling inventories; and bounded/controlled refusal.
"""
from pathlib import Path
import shutil
import subprocess
import game_source

ROOT = Path(__file__).resolve().parents[2]
MODULE = game_source.ROGUELITE / 'progression.lua'
LUA = shutil.which('lua5.4') or shutil.which('lua')
assert LUA, 'Lua interpreter required'

TEST = r'''
local P=dofile(arg[1])
local function room(id, fields) fields=fields or {}; fields.id=id; return fields end
local function edge(id,a,b,gate,dir) return {id=id,from_room=a,to_room=b,gate_rule=gate,direction=dir or 'both'} end

-- (1) Revisit-carry: A<->B and A<->F traversable, D mandatory but wired to
-- nothing. Revisiting A/B must not manufacture D's objective bit.
local carry={start_room='A',final_room='F',spine={'A','D','F'},
 rooms_by_id={A=room('A'),B=room('B'),D=room('D'),F=room('F')},
 edges_by_id={e1=edge('e1','A','B'),e2=edge('e2','A','F')},locks={}}
assert(not P.validate(carry),'revisit carry falsely completed the run')
carry.edges_by_id.e3=edge('e3','A','D'); assert(P.validate(carry))

-- (2) Finite consumable pickups. A -> B -> C -> D; A<->B and both locked doors
-- are bidirectional. Only A grants a finite key. Repeated A/B visits must not
-- replenish it. One key cannot open two distinct doors; two keys must.
local function chain(keys_granted, repeat_policy)
 local locks={g1={id='g1',version=1,kind='consumable_key',key='k'},g2={id='g2',version=1,kind='consumable_key',key='k'}}
 if repeat_policy then locks.g1['repeat']=true; locks.g2['repeat']=true end
 return {start_room='A',final_room='D',spine={'A','B','C','D'},
  rooms_by_id={A=room('A',{grants_consumable={k=keys_granted}}),B=room('B'),C=room('C'),D=room('D')},
  edges_by_id={e1=edge('e1','A','B'),e2=edge('e2','B','C','g1'),e3=edge('e3','C','D','g2')},locks=locks}
end
assert(not P.validate(chain(1)),'one finite key opened two doors (replenishment)')
assert(P.validate(chain(2)),'two genuine keys should open two doors')
-- Re-entering A must not grant a second key: with repeatable pickups it would.
local cycling=chain(1); cycling.rooms_by_id.A.grants_consumable.k=1
assert(not P.validate(cycling),'revisiting A replenished the pickup')

-- (3) Optional source revisit: an optional room grants the only key; visiting it
-- twice must not fund two doors.
local optional={start_room='A',final_room='D',spine={'A','B','C','D'},
 rooms_by_id={A=room('A'),O=room('O',{grants_consumable={k=1}}),B=room('B'),C=room('C'),D=room('D')},
 edges_by_id={e1=edge('e1','A','O'),e2=edge('e2','A','B'),e3=edge('e3','B','C','g1'),e4=edge('e4','C','D','g2')},
 locks={g1={id='g1',version=1,kind='consumable_key',key='k'},g2={id='g2',version=1,kind='consumable_key',key='k'}}}
assert(not P.validate(optional),'optional pickup was replenished on revisit')

-- (4) Independent sibling pickups. Both branches are collectable; a gate after
-- the merge needs each branch's distinct key. Missing either branch's pickup
-- must fail, so sibling states cannot leak.
local function siblings(both)
 local rooms={A=room('A'),B=room('B'),C=room('C'),M=room('M'),N=room('N'),F=room('F')}
 rooms.B.grants_consumable={kb=1}
 if both then rooms.C.grants_consumable={kc=1} end
 return {start_room='A',final_room='F',spine={'A','B','C','M','N','F'},rooms_by_id=rooms,
  edges_by_id={e1=edge('e1','A','B'),e2=edge('e2','A','C'),e3=edge('e3','B','M'),e4=edge('e4','C','M'),
   e5=edge('e5','M','N','gb'),e6=edge('e6','N','F','gc')},
  locks={gb={id='gb',version=1,kind='consumable_key',key='kb'},gc={id='gc',version=1,kind='consumable_key',key='kc'}}}
end
assert(P.validate(siblings(true)),'both sibling keys should complete the chain')
assert(not P.validate(siblings(false)),'a missing sibling key must fail')

-- (5) Multiple pickups in one room are all claimed once.
local multi={start_room='A',final_room='C',spine={'A','B','C'},
 rooms_by_id={A=room('A',{grants_consumable={ka=1,kc=1}}),B=room('B'),C=room('C')},
 edges_by_id={e1=edge('e1','A','B','ga'),e2=edge('e2','B','C','gc')},
 locks={ga={id='ga',version=1,kind='consumable_key',key='ka'},gc={id='gc',version=1,kind='consumable_key',key='kc'}}}
assert(P.validate(multi),'multiple pickups in one room should both be available')

-- (6) Opened-door semantics: a consumable gate that opens permanently is not
-- charged on the return/second use; a repeat gate is.
local function opened(repeat_policy)
 local lock={id='g',version=1,kind='consumable_key',key='k'}
 if repeat_policy then lock['repeat']=true end
 return {start_room='A',final_room='F',spine={'A','B','F'},
  rooms_by_id={A=room('A',{grants_consumable={k=1}}),B=room('B'),F=room('F')},
  edges_by_id={e1=edge('e1','A','B','g'),e2=edge('e2','B','F','g')},locks={g=lock}}
end
assert(P.validate(opened(false)),'opening a door permanently must not charge the second use')
assert(not P.validate(opened(true)),'a repeat gate must charge on every traversal')

-- (7) Persistent keys behave as before.
local function persistent(grant)
 local m={start_room='A',final_room='F',spine={'A','B','F'},
  rooms_by_id={A=room('A'),B=room('B'),F=room('F')},
  edges_by_id={e1=edge('e1','A','B','g'),e2=edge('e2','B','F')},
  locks={g={id='g',version=1,kind='persistent_key',key='k'}}}
 if grant then m.rooms_by_id[grant].grants_key='k' end
 return m
end
assert(not P.validate(persistent(nil))); assert(P.validate(persistent('A'))); assert(not P.validate(persistent('F')))

-- (8) Controlled state-budget refusal and malformed data.
assert(not P.validate(chain(2),{max_states=1}),'state budget must be enforced')
local bad=chain(2); bad.rooms_by_id.A.grants_consumable.k=0; assert(not P.validate(bad))
bad=chain(2); bad.rooms_by_id.A.pickups={{id='p',key='k',amount=1},{id='p',key='k',amount=1}}; assert(not P.validate(bad))
bad=persistent('A'); bad.edges_by_id.e1.gate_rule='missing'
local ok,why=P.validate(bad); assert(not ok and tostring(why):find('unknown lock',1,true))
bad=persistent('A'); bad.locks.g.kind='bogus'; assert(not P.validate(bad))
assert(not P.validate({}))
print('progression: revisit-carry, finite pickups, siblings, opened doors, budget and refusal passed')
'''

subprocess.run([LUA, '-', str(MODULE)], input=TEST, text=True, check=True)
