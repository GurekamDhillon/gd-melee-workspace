#!/usr/bin/env python3
"""Collection discard: the only way a full collection can shrink.

Covers the guards that make discard safe (locked gene, an ancestor of a retained
gene, emptying the collection), that it touches nothing else, and that a
discarded gene survives a save/load round trip as gone rather than resurrected.
"""
from pathlib import Path
import subprocess
import unittest
from tools.test_support import require_game
require_game('pc/scripts/examples/roguelite')
import game_source

CORE = game_source.ROGUELITE / 'core.lua'

PRELUDE = r'''
local Core = assert(loadfile(arg[1]))()
local function check(v, m) if not v then error(m or 'assertion failed', 2) end return v end
local function count(t) local n = 0 for _ in pairs(t) do n = n + 1 end return n end
'''

LUA = r'''
local p = Core.new_profile(4242)
check(p.genes.g1 and p.genes.g2 and p.genes.g3, 'fixture genes missing')

-- A plain, unlocked, non-ancestor gene discards.
check(Core.discard(p, 'g2'), 'a plain discard was refused')
check(not p.genes.g2, 'the gene is still in the collection after discard')
check(count(p.genes) == 2, 'discard changed the collection size incorrectly')
-- Nothing else moved: no other gene, no ledger, no id counter.
check(p.genes.g1 and p.genes.g3, 'discard removed another gene')
check(p.next_id == 4 and p.next_run == 1, 'discard disturbed profile counters')
check(not p.finished['run1'], 'discard wrote a finish record')
check(#p.genes.g1.locks == 0 and #p.genes.g3.locks == 0, 'discard disturbed another gene')

-- Unknown gene is refused.
check(select(2, Core.discard(p, 'nope')) == 'unknown gene', 'an unknown gene was discarded')

-- A locked gene cannot be discarded, and the lock survives the refusal.
check(Core.lock(p, 'g1', 'potency', true), 'lock refused')
check(select(2, Core.discard(p, 'g1')):find('locked potency', 1, true),
  'a locked gene was discarded')
check(p.genes.g1 and p.genes.g1.locks.potency, 'the refused discard took the locked gene')

-- The collection may not be emptied: the last gene is refused.
local s = Core.new_profile(31)
check(Core.discard(s, 'g2'), 'could not discard the second gene')
check(Core.discard(s, 'g3'), 'could not discard the third gene')
check(count(s.genes) == 1, 'the fixture is not down to one gene')
check(select(2, Core.discard(s, 'g1')) == 'collection must keep at least one gene',
  'the collection was allowed to empty itself')
check(s.genes.g1, 'the final discard emptied the collection')

-- A gene that is an ancestor of a retained gene cannot be discarded: that would
-- orphan recorded parentage.
local q = Core.new_profile(77)
check(Core.breed(q, 'g1', 'g3'), 'breed refused')
local child = nil
for id, g in pairs(q.genes) do if g.parents and #g.parents == 2 then child = id end end
check(child, 'no bred child to parentage-test')
check(select(2, Core.discard(q, 'g1')):find('parent of', 1, true),
  'an ancestor was discarded: ' .. tostring(select(2, Core.discard(q, 'g1'))))
check(q.genes.g1, 'the refused ancestor discard removed the parent')
check(q.genes[child], 'the refused ancestor discard removed the child')

-- Discard survives a durable round trip as a deletion, not a resurrection.
local r = Core.new_profile(9)
check(Core.discard(r, 'g2'), 'round-trip discard refused')
local text = check(Core.snapshot(r), 'snapshot after discard failed')
local back = check(Core.restore(text), 'restore after discard failed')
check(not back.genes.g2, 'the discarded gene came back after a save/load round trip')
check(back.genes.g1 and back.genes.g3, 'the round trip lost other genes')
check(back.next_id == r.next_id, 'the round trip disturbed next_id')

-- A discard of a never-existed collection entry on a wrong container is refused.
local run = Core.new_run(r, {stocks = 1})
check(select(2, Core.discard(run, 'r1')) == 'unknown gene', 'a run accepted a collection discard')

print('discard: guards, isolation and durable round trip passed')
'''


class DiscardTests(unittest.TestCase):
    def test_discard_contract(self):
        import shutil
        lua = shutil.which('lua5.4') or shutil.which('lua')
        self.assertIsNotNone(lua, 'Lua interpreter required')
        result = subprocess.run([lua, '-', str(CORE)], input=PRELUDE + LUA,
                                text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('discard: guards, isolation and durable round trip passed', result.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
