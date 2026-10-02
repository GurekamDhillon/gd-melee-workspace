"""Release-timed variants of the original, reviewed fire/ice asset study.

The lab founders include 36 frames of anticipation. A committed command already
deals its hit, so these variants begin at the release and omit that charge layer.
Original masks, materials and particle budgets are preserved.
"""
import copy
import importlib.util
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]


def build(mod):
    spec = importlib.util.spec_from_file_location('rogue_original_fx', ROOT/'tools/effects_lab/recipes.py')
    recipes = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(recipes)
    for original in recipes.recipes()[:2]:
        data = copy.deepcopy(original)
        data['name'] = 'RogueCinderRelease' if original['name'] == 'SolarEruption' else 'RogueRimeRelease'
        data['source']['release_variant_of'] = original['name']
        data['source']['release_frame'] = 0
        data['source']['phases'] = [0, 1, 18, 42, 96]
        data['emitters'] = [e for e in data['emitters'] if not e['name'].endswith('_charge')]
        for emitter in data['emitters']:
            emitter['emission']['start'] = max(0, emitter['emission']['start'] - 36)
        path = Path(mod)/'fx'/data['name']
        (path/'tex').mkdir(parents=True, exist_ok=True)
        for texture in data['textures']:
            shutil.copyfile(recipes.ASSET_ROOT/'rgba'/(texture['name']+'.png'), path/texture['file'])
        (path/(data['name']+'.gfx.json')).write_text(json.dumps(data,indent=2)+'\n')
