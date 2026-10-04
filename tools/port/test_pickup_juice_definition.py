"""Pickup presentation definitions must agree with the production strict decoder."""
from pathlib import Path
import json,re,unittest
ROOT=Path(__file__).resolve().parents[2]
class DefinitionTests(unittest.TestCase):
 def test_visual_contract_and_final_numbers(self):
  decoder=(ROOT/'melee/pc/platform/geno_items_registry.inc').read_text()
  match=re.search(r'const char\* const visual\[\]=\{([^}]+)\}',decoder)
  self.assertIsNotNone(match)
  allowed=set(re.findall(r'"([^"]+)"',match.group(1)))
  for path in ('envoy/items/drive/item.json','demos/pickup-juice/items/demo_juice/item.json'):
   with self.subTest(path=path):
    item=json.loads((ROOT/'melee/pc/scripts/examples'/path).read_text());v=item['visual']
    self.assertFalse(set(v)-allowed)
    self.assertEqual(v['hover'],6);self.assertEqual(v['scale'],2.5)
    self.assertEqual(v['spin']*60,360);self.assertEqual(v['tilt'],12)
    self.assertAlmostEqual(v['height']*v['scale'],11.375)
    self.assertEqual(v['bob_speed'],3);self.assertEqual(v['bob'],.6)
 def test_demo_embeds_current_shared_factory(self):
  import importlib.util
  path=ROOT/'tools/port/pickup_juice_demo.py'
  spec=importlib.util.spec_from_file_location('pickup_bundle',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  self.assertEqual(m.bundle(),m.TARGET.read_text())
if __name__=='__main__':unittest.main()
