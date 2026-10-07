"""The delivered pickup assets and native definition remain the production ones."""
import json
from pathlib import Path
import unittest
from tools.test_support import GAME, require_game
ROOT=Path(__file__).resolve().parents[2]
MOD=GAME/'pc/scripts/examples/envoy'
class PolishTests(unittest.TestCase):
 def setUp(self):
  require_game('pc/scripts/examples/envoy/items/drive/item.json')
 def test_all_original_colour_packages_and_shader_dependencies_shipped(self):
  for colour in ('red','green','blue','yellow','white'):
   for kind in ('glow','pool','sparkles','highlight','pop_trail','collect_burst'):
    name='PickupJuice_'+kind+'_'+colour;folder=MOD/'fx'/name
    package=folder/(name+'.gfx.json');data=json.loads(package.read_text())
    self.assertEqual(data['name'],name);self.assertEqual(data['textures'],[])
    demo=GAME/'pc/scripts/examples/demos/pickup-juice/fx'/name
    self.assertEqual(package.read_bytes(),(demo/package.name).read_bytes())
    for emitter in data['emitters']:
     shader=emitter['material']['shader']['fragment']
     self.assertEqual((folder/shader).read_bytes(),(demo/shader).read_bytes())
     self.assertTrue(emitter['material']['additive_batch'])
 def test_native_polish_numbers_and_scaled_touch_capsule(self):
  data=json.loads((MOD/'items/drive/item.json').read_text());v=data['visual']
  self.assertEqual((v['hover'],v['scale'],v['tilt'],v['spin']), (6,2.5,12,6))
  # Original envoy_drives model height (game commit eeab98999), not the old SA2 model.
  self.assertAlmostEqual(v['height']*v['scale'],11.0)
  self.assertEqual(data['radius']*v['scale'],17.5)
  self.assertEqual((data['lifetime'],data['blink']), (900,120))
if __name__=='__main__':unittest.main()
