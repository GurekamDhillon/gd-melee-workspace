#!/usr/bin/env python3
"""Deferred export: the earned gene is never silently dropped at a full collection.

Covers the whole contract the handoff requires:
  * a full collection defers instead of dropping, and the gene stays durable
  * the deferred gene survives a save/relaunch round trip unchanged
  * claiming is exactly once: a repeated claim neither duplicates nor deletes
  * claiming is refused while the collection is still full
  * a refused save leaves the pending gene intact and still claimable
  * declining is a separate, explicit, recorded user action
  * a non-deferring caller still has to choose, and gets a refusal not a drop
"""
from pathlib import Path
import shutil
import subprocess
import unittest
import game_source

CORE = game_source.ROGUELITE / 'core.lua'

PRELUDE = r'''
local Core = assert(loadfile(arg[1]))()
local function check(v, m) if not v then error(m or 'assertion failed', 2) end return v end
local function count(t) local n = 0 for _ in pairs(t) do n = n + 1 end return n end
local function fill(p, to)
  local serial = tonumber(p.next_id) - 1
  while count(p.genes) < to do
    serial = serial + 1
    p.genes['g' .. serial] = {id = 'g' .. serial, kind = 'cinder', version = 1, seed = 1,
      base = {potency = 8, capacity = 3, gain = 1, reach = 9, cooldown = 90},
      upgrades = {}, parents = {}, locks = {}}
    p.next_id = serial + 1
  end
end
local function relaunch(p) return check(Core.restore(check(Core.snapshot(p), 'snapshot')), 'restore') end
'''

LUA = r'''
-- ---- A. a full collection defers rather than drops ----
local p = Core.new_profile(4242)
local run = Core.new_run(p, {stocks = 2})
check(Core.equip(run, 'player', 'assault', 'r1'), 'equip refused')
run.progress.supplies = 1
fill(p, 128)
check(count(p.genes) == 128, 'fixture is not full')

-- A non-deferring caller must choose explicitly; it is refused, not silently emptied.
local refused, why = Core.finish(p, run, 'success', 'r1')
check(refused == nil and why:find('choose no export', 1, true),
  'a non-deferring finish was not refused: ' .. tostring(why))
check(p.finished[run.id] == nil, 'the refused finish wrote a finish record')

-- A deferring caller keeps the gene on the finish record.
local res = check(Core.finish(p, run, 'success', 'r1', {defer_export = true}), 'deferring finish refused')
check(res.deferred ~= nil and res.pending == true, 'the export was not deferred')
check(res.export == nil, 'a deferred export also recorded an export')
check(res.deferred.id == 'r1', 'the deferred gene is not the run gene')
check(count(p.genes) == 128, 'deferring added a gene to a full collection')

-- ---- B. it is durable across a relaunch ----
local p2 = relaunch(p)
check(p2.finished[run.id] ~= nil, 'the finish record was lost on relaunch')
check(p2.finished[run.id].deferred ~= nil, 'the deferred gene was lost on relaunch')
check(p2.finished[run.id].deferred.id == 'r1', 'the deferred gene changed identity on relaunch')
check(#Core.pending_exports(p2) == 1, 'pending_exports did not list the deferred export')
check(Core.pending_exports(p2)[1].run == run.id, 'pending_exports named the wrong run')

-- ---- C. claiming is refused while full, and exactly once once there is room ----
check(Core.claim_deferred(p2, run.id) == nil, 'a full collection accepted a claim')
check(p2.finished[run.id].deferred ~= nil, 'the refused claim destroyed the pending gene')

check(Core.discard(p2, 'g4'), 'could not make room')
local before = count(p2.genes)
local claimed = check(Core.claim_deferred(p2, run.id), 'claim refused with room')
check(claimed == p2.genes[p2.finished[run.id].export].id, 'the claim did not return the new gene id')
check(p2.finished[run.id].export == claimed, 'the finish record does not name the claimed gene')
check(p2.finished[run.id].deferred == nil, 'the claim left the deferred gene in place')
check(p2.finished[run.id].pending == nil, 'the claim left the record pending')
check(count(p2.genes) == before + 1, 'the claim did not add exactly one gene')

-- Repeated claim: refused, and nothing is duplicated or deleted.
local again, why2 = Core.claim_deferred(p2, run.id)
check(again == nil and why2 == 'nothing to claim', 'a repeated claim succeeded: ' .. tostring(why2))
check(count(p2.genes) == before + 1, 'a repeated claim duplicated or deleted genes')
check(Core.claim_deferred(p2, 'run99') == nil, 'an unknown run produced a claim')

-- A relaunch after the claim keeps exactly one copy.
local p3 = relaunch(p2)
check(count(p3.genes) == before + 1, 'the relaunch duplicated or lost the claimed gene')
check(p3.finished[run.id].deferred == nil, 'the relaunch resurrected the deferred gene')
check(#Core.pending_exports(p3) == 0, 'pending_exports still lists a claimed export')

-- ---- D. a refused save leaves the pending gene intact and claimable ----
local q = Core.new_profile(77)
local r2 = Core.new_run(q, {stocks = 2})
check(Core.equip(r2, 'player', 'assault', 'r1'), 'equip refused')
fill(q, 128)
check(Core.finish(q, r2, 'success', 'r1', {defer_export = true}), 'defer refused')
-- Simulate a refused durable write: the caller rolls back to its snapshot.
local snap = check(Core.snapshot(q), 'snapshot')
local bad = check(Core.restore(snap), 'restore')
check(bad.finished[r2.id].deferred ~= nil, 'the refused save lost the pending gene')
check(Core.discard(bad, 'g4'), 'could not make room after the refused save')
check(Core.claim_deferred(bad, r2.id) ~= nil, 'the gene was not claimable after a refused save')

-- ---- E. declining is explicit and recorded ----
local s = Core.new_profile(99)
local r3 = Core.new_run(s, {stocks = 2})
check(Core.equip(r3, 'player', 'assault', 'r1'), 'equip refused')
fill(s, 128)
check(Core.finish(s, r3, 'success', 'r1', {defer_export = true}), 'defer refused')
check(count(s.genes) == 128, 'defer added a gene')
check(Core.decline_deferred(s, r3.id), 'decline refused')
check(s.finished[r3.id].deferred == nil, 'the declined gene was not dropped')
check(s.finished[r3.id].declined == true, 'the decline was not recorded')
check(#Core.pending_exports(s) == 0, 'a declined export is still pending')
check(Core.decline_deferred(s, r3.id) == nil, 'a repeated decline succeeded')
check(count(s.genes) == 128, 'declining changed the collection')

-- ---- F. enemy-owned and absent genes are never deferred ----
local u = Core.new_profile(1234)
local r4 = Core.new_run(u, {stocks = 2})
-- Use the id acquire returns. next() over a string-keyed table is not stable
-- across processes, which made this group flaky rather than wrong.
local enemy = check(Core.acquire(r4, 'cinder'), 'acquire refused')
check(Core.equip(r4, 'enemy_x', 'assault', enemy), 'enemy equip refused')
fill(u, 128)
local r5 = Core.finish(u, r4, 'success', enemy, {defer_export = true})
check(r5 == nil, 'an enemy-owned gene was deferred')
local r6 = Core.finish(u, r4, 'success', 'nope', {defer_export = true})
check(r6 == nil, 'an absent gene was deferred')

print('deferred export: defer, relaunch, exactly-once claim, refused save, decline passed')
'''


class DeferredExportTests(unittest.TestCase):
    def test_deferred_export_contract(self):
        lua = shutil.which('lua5.4') or shutil.which('lua')
        self.assertIsNotNone(lua, 'Lua interpreter required')
        result = subprocess.run([lua, '-', str(CORE)], input=PRELUDE + LUA,
                                text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('deferred export: defer, relaunch, exactly-once claim, refused save, decline passed',
                      result.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
