#!/usr/bin/env python3
"""Validate the enemy behaviour contract and cross-check encounter kinds."""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
RT = ROOT / 'melee/worktrees/linux/pc/scripts/examples/roguelite'
LUA = shutil.which('lua5.4') or shutil.which('lua')
assert LUA, 'Lua interpreter required'

MODULES = [RT / 'encounter_catalogue.lua', RT / 'gene_catalogue.lua', RT / 'enemy_catalogue.lua']

TEST = r'''
local Enc=dofile(arg[1]); local Genes=dofile(arg[2]); local E=dofile(arg[3])
local ok,why=E.validate(E,Enc); assert(ok,why)
local behaviors,enemies=0,0
for _ in pairs(E.behaviors) do behaviors=behaviors+1 end
for _ in pairs(E.enemies) do enemies=enemies+1 end
assert(behaviors>=6 and enemies>=4)
-- Every behavior's gene eligibility references a real gene family.
for _,b in pairs(E.behaviors) do for _,f in ipairs(b.genes) do assert(Genes.families[f],'behavior gene family missing: '..f) end end
-- Every enemy's gene eligibility references a real gene family.
for _,e in pairs(E.enemies) do for _,f in ipairs(e.genes) do assert(Genes.families[f],'enemy gene family missing: '..f) end end
-- Every encounter's archetype and kinds are covered.
for id,enc in pairs(Enc.encounters) do
 assert(E.behaviors[enc.archetype],'archetype missing: '..id)
 for _,enemy in ipairs(enc.enemies) do assert(E.enemies[enemy.kind],'enemy kind missing: '..enemy.kind) end
end
-- Adversarial fixtures are refused.
local function clone(v) if type(v)~='table' then return v end local o={} for k,x in pairs(v) do o[k]=clone(x) end return o end
local bad=clone(E); bad.behaviors.zone.window=200; assert(not pcall(E.validate,bad,Enc))
bad=clone(E); bad.enemies.champion.phases=1; assert(not pcall(E.validate,bad,Enc))
local enc=clone(Enc); enc.encounters.scout_pair.enemies={{kind='ghost',count=1,level=3}}
assert(not pcall(E.validate,E,enc))
print('enemy catalogue: behaviors, kinds, gene eligibility and encounter cross-check passed')
'''

subprocess.run([LUA, '-', *[str(m) for m in MODULES]], input=TEST, text=True, check=True)
