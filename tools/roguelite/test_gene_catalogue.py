#!/usr/bin/env python3
"""Validate the gene-family contract and cross-check cinder/rime with Core."""
from pathlib import Path
import shutil
import subprocess
import game_source

ROOT = Path(__file__).resolve().parents[2]
RT = game_source.ROGUELITE
LUA = shutil.which('lua5.4') or shutil.which('lua')
assert LUA, 'Lua interpreter required'

MODULES = [RT / 'core.lua', RT / 'gene_catalogue.lua']

TEST = r'''
local Core=dofile(arg[1]); local G=dofile(arg[2])
local ok,why=G.validate(G); assert(ok,why)
local families,genes,reactions,implemented=0,0,0,0
for _ in pairs(G.families) do families=families+1 end
for _,g in pairs(G.genes) do genes=genes+1; if g.implemented then implemented=implemented+1 end end
for _ in pairs(G.reactions) do reactions=reactions+1 end
assert(families>=6 and genes>=12 and reactions>=6)
-- Only cinder and rime are implemented, and they match Core's definitions.
assert(implemented==2,'only cinder/rime may claim implementation')
for id,kind in pairs({cinder='cinder',rime='rime'}) do
 local g=G.genes[id]; local d=Core.definitions[kind]
 assert(g and d,'missing gene/core definition for '..id)
 assert(#g.placements==3,'core gene has three placements')
 for placement in pairs(d.variants) do
  local supported=false for _,p in ipairs(g.placements) do if p==placement then supported=true end end
  assert(supported,'core placement not declared in catalogue: '..placement)
 end
end
-- Unimplemented genes never pretend to have a mechanic.
for _,g in pairs(G.genes) do if not g.implemented then assert(g.recipe and #g.recipe>0) end end
-- Adversarial fixtures are refused.
local function clone(v) if type(v)~='table' then return v end local o={} for k,x in pairs(v) do o[k]=clone(x) end return o end
local bad=clone(G); bad.genes.cinder.base.potency=999; assert(not pcall(G.validate,bad))
bad=clone(G); bad.genes.cinder.placements={'assault'}; assert(not pcall(G.validate,bad))
bad=clone(G); bad.genes.cinder.family='void'; assert(not pcall(G.validate,bad))
bad=clone(G); bad.reactions.thermal_shock.families={'fire','void'}; assert(not pcall(G.validate,bad))
bad=clone(G); bad.genes.cinder.base={potency=8}; assert(not pcall(G.validate,bad))
print('gene catalogue: 6 families, 12 genes, authored reactions and refusal passed')
'''

subprocess.run([LUA, '-', *[str(m) for m in MODULES]], input=TEST, text=True, check=True)
