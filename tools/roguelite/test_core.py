"""Exercise the real pure Lua rules, without an engine or a translated Python model."""
from pathlib import Path
import shutil
import subprocess
import unittest
from tools.test_support import require_game
require_game('pc/scripts/examples/roguelite')
import game_source

CORE = game_source.ROGUELITE / 'core.lua'


class CoreTests(unittest.TestCase):
    def test_full_collection_decode_stays_below_callback_work_budget(self):
        lua = shutil.which('lua') or shutil.which('lua5.4')
        self.assertIsNotNone(lua, 'Real Lua required')
        program = r'''
local C=dofile(arg[1]);local p=C.new_profile(77)
for i=1,125 do assert(C.breed(p,'g1','g3')) end
local raw=assert(C.snapshot(p));local instructions=0
debug.sethook(function() instructions=instructions+100 end,'',100)
local restored,why=C.restore(raw)
debug.sethook();assert(restored,why)
assert(instructions<500000,'full collection decode consumes '..instructions..' instructions')
assert(C.snapshot(restored)==raw,'optimized decode changed saved bytes')
local escaped=C.new_profile(78)
escaped.history={note='quote" slash\\ newline\n'..string.char(0,1,31,127)}
local encoded=assert(C.snapshot(escaped))
assert(C.snapshot(assert(C.restore(encoded)))==encoded,'escaped Core strings changed')
for _,bad in ipairs({'"\\q"','"\\ud800"','"unterminated', 'truex','falsex','1e','1.e2','1e2e3'}) do
 assert(not C.restore(bad),'malformed token accepted: '..bad)
end
'''
        result = subprocess.run([lua, '-', str(CORE)], input=program,
                                text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_gameplay_and_persistence(self):
        lua = shutil.which('lua') or shutil.which('lua5.4')
        self.assertIsNotNone(lua, 'Lua interpreter required; do not substitute a mock')
        program = r'''
local C=assert(loadfile(arg[1]))()
local function equal(a,b) assert(C.snapshot(a)==C.snapshot(b),'snapshot mismatch') end
local p=C.new_profile(123); local original=assert(C.snapshot(p));local r=C.new_run(p)
local source=r.genes.r1.base.potency
assert(C.reward(r,'r1','potency',4)); assert(C.resolve(r,'player','assault').potency==source+4)
assert(r.genes.r1.base.potency==source and p.genes.g1.base.potency==source)
assert(C.apply_modifier(r,'player','assault',{id='penalty',stat='potency',add=-3,expires=5}))
assert(C.resolve(r,'player','assault').potency==source+1)
assert(C.tick(r,5)); assert(C.resolve(r,'player','assault').potency==source+4)
assert(C.apply_modifier(r,'player','assault',{id='item',stat='potency',add=7}))
assert(C.resolve(r,'player','assault').potency==source+11)
assert(C.remove_modifier(r,'player','assault','item'));assert(C.resolve(r,'player','assault').potency==source+4)
local before=C.snapshot(r); assert(not C.activate(r,'player','assault',{target='enemy'}));assert(before==C.snapshot(r))
for i=1,3 do assert(C.on_event(r,{host='player',kind='direct_hit',move_id='m'..i})==1) end
assert(C.on_event(r,{host='player',kind='direct_hit',move_id='m3'})==0)
assert(C.on_event(r,{host='player',kind='direct_hit',move_id='reaction',reaction=true})==0)
local a=assert(C.activate(r,'player','assault',{target='enemy'}));assert(a.action=='eruption' and a.damage==source+4 and a.lineage=='reaction')
assert(C.equip(r,'player','assault',nil));assert(C.equip(r,'player','guard','r1'))
assert(C.on_event(r,{host='player',kind='defend',move_id='swapexploit'})==0)
assert(C.ability(r,'player','guard').remaining==90)
assert(C.equip(r,'player','guard','r2'));assert(C.equip(r,'player','assault','r1'))
assert(C.on_event(r,{host='player',kind='direct_hit',move_id='cooldown'})==0)
assert(C.tick(r,90));assert(C.equip(r,'player','assault',nil));assert(C.equip(r,'player','traversal','r1'))
assert(C.on_event(r,{host='player',kind='direct_hit',move_id='no'})==0)
for i=1,3 do C.on_event(r,{host='player',kind='move',move_id='walk'..i}) end
assert(C.activate(r,'player','traversal',{}).action=='step')
local enemy=assert(C.acquire(r,'rime'));assert(C.equip(r,'enemy','guard',enemy))
local beforeexport=C.snapshot(p);local beforeenemy=C.snapshot(r)
assert(not C.finish(p,r,'success',enemy));assert(beforeexport==C.snapshot(p) and beforeenemy==C.snapshot(r))
assert(not C.fuse(r,enemy,'r2'))
for i=1,3 do C.on_event(r,{host='enemy',kind='defend',move_id='block'..i}) end
local unready=C.snapshot(r);assert(not C.activate(r,'enemy','guard',{}));assert(unready==C.snapshot(r))
assert(C.activate(r,'enemy','guard',{target='player'}).action=='mark')
assert(r.marks.player.source=='enemy')
assert(C.tick(r,90));for i=1,3 do C.on_event(r,{host='player',kind='move',move_id='walkagain'..i}) end
assert(C.activate(r,'player','traversal',{target='player'}).reaction=='thermal_shock');assert(not r.marks.player)
local saved=assert(C.snapshot(r));local restored=assert(C.restore(saved));equal(r,restored)
assert(C.tick(restored,180));assert(not restored.marks.player)
local child=assert(C.acquire(r,'cinder'));assert(C.reward(r,child,'potency',-100));assert(r.genes[child].base.potency==8)
assert(r.world_seed~=r.seed and r.world_seed==assert(C.restore(saved)).world_seed)
assert(C.equip(r,'player','traversal',nil));local fused=assert(C.fuse(r,'r1',child));assert(not r.genes.r1 and not r.genes[child]);assert(r.genes[fused].parents[1]=='r1')
local failed=C.new_run(p)
local retained=p.genes.g1.base.potency;assert(C.reward(failed,'r1','potency',20));assert(C.finish(p,failed,'failure').outcome=='failure');assert(p.genes.g1.base.potency==retained)
local exported=assert(C.finish(p,r,'success',fused)).export;assert(p.genes[exported]);assert(next(p.genes[exported].upgrades)==nil)
local count=p.next_id;assert(C.finish(p,r,'success',fused).export==exported and p.next_id==count)
local bred=assert(C.breed(p,'g1',exported));assert(p.genes[bred].parents[1]=='g1' and p.genes.g1)
local snapshot=assert(C.snapshot(p));assert(not C.breed(p,'g1','g2'));assert(snapshot==C.snapshot(p))
assert(C.lock(p,'g1','potency',true));assert(C.lock(p,'g3','potency',true));local conflict=assert(C.snapshot(p));assert(not C.breed(p,'g1','g3'));assert(conflict==C.snapshot(p))
assert(C.lock(p,'g3','potency',false));local locked=assert(C.breed(p,'g1','g3'));assert(p.genes[locked].base.potency==p.genes.g1.base.potency and p.genes[locked].locks.potency)
snapshot=assert(C.snapshot(p))
equal(p,assert(C.restore(snapshot)))
local x=C.new_profile(123);local y=C.new_profile(123);equal(x,y);equal(C.new_run(x),C.new_run(y))
for _,bad in ipairs({'return os.execute("touch /tmp/rogue")','{"type":"profile","version":2}','{"x":1,"x":2}','{"x":1e999}','{"x":01}','{"x":1.}','{"x":1+2}',snapshot..'junk'}) do assert(not C.restore(bad),'accepted unsafe save') end
local foreign=C.new_run(C.new_profile(999));local checkpoint=assert(C.snapshot(p));assert(not C.finish(p,foreign,'success','r1'));assert(checkpoint==C.snapshot(p))
local invalid=assert(C.restore(snapshot));invalid.genes.g1.base.potency=0/0;assert(not C.snapshot(invalid))
invalid=assert(C.restore(snapshot));invalid.next_id=1;assert(not C.snapshot(invalid))
invalid=assert(C.restore(saved));invalid.hosts.player.state.traversal.charge=-1;assert(not C.snapshot(invalid))
invalid=assert(C.restore(saved));invalid.progress.supplies=10;assert(not C.snapshot(invalid))
invalid=assert(C.restore(saved));invalid.progress.cleared.entry='yes';assert(not C.snapshot(invalid))
local crash=assert(C.restore(saved));assert(C.finish(p,crash,'success',fused).export==exported)
local full=C.new_profile(456);for i=1,125 do assert(C.breed(full,'g1','g3')) end
local fullrun=C.new_run(full);local fullbefore=assert(C.snapshot(full));local runbefore=assert(C.snapshot(fullrun))
assert(not C.finish(full,fullrun,'success','r1'));assert(fullbefore==C.snapshot(full) and runbefore==C.snapshot(fullrun))
assert(C.finish(full,fullrun,'success').outcome=='success');assert(C.restore(assert(C.snapshot(full))))
local ledger=C.new_profile(789);for i=1,512 do assert(C.finish(ledger,C.new_run(ledger),'failure')) end
local ledgerbefore=assert(C.snapshot(ledger));assert(not pcall(C.new_run,ledger));assert(ledgerbefore==C.snapshot(ledger))
-- The durable history exceeds sixteen entries without becoming unsavable.
local H=dofile(arg[1]:gsub('core.lua$','run_history.lua'))
local hp=C.new_profile(790);hp.history=assert(H.new(hp.id))
for i=1,17 do local hr=C.new_run(hp);assert(C.finish(hp,hr,'failure'));local e=assert(H.make_entry(hr,{outcome='failure'}));hp.history=assert(H.append(hp.history,e)) end
local historybytes=assert(C.snapshot(hp));local hrestored=assert(C.restore(historybytes));assert(H.validate(hrestored.history));assert(#hrestored.history.entries==17,'Core restore lost history array indexes')
local nextfinished=C.new_run(hrestored);assert(C.finish(hrestored,nextfinished,'failure'));hrestored.history=assert(H.append(hrestored.history,assert(H.make_entry(nextfinished,{outcome='failure'}))));assert(#assert(C.restore(assert(C.snapshot(hrestored)))).history.entries==18,'append after reload lost history')
local snap=assert(C.snapshot(restored));assert(not C.apply_modifier(restored,'player','traversal',{id='bad',stat='potency',add=0/0}));assert(snap==C.snapshot(restored))
-- Exported genes remain explicitly discardable and the durable finish ledger
-- records that the old collection item was removed instead of dangling.
local d=C.new_profile(909);local dr=C.new_run(d);local dexport=assert(C.finish(d,dr,'success','r1')).export
assert(C.discard(d,dexport));assert(not d.genes[dexport])
assert(d.finished[dr.id].export==nil and d.finished[dr.id].discarded_export==dexport)
assert(C.restore(assert(C.snapshot(d))))
print('core gameplay/persistence invariants passed')
'''
        result = subprocess.run([lua, '-', str(CORE)], input=program, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('invariants passed', result.stdout)


if __name__ == '__main__':
    unittest.main()
