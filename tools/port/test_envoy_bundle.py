"""Offline packaging contracts for the one-folder Envoy entry."""
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


class BundleTests(unittest.TestCase):
    def module(self):
        spec = importlib.util.spec_from_file_location('envoy_bundle', HERE / 'envoy_bundle.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_generated_entry_is_current_and_deterministic(self):
        module = self.module()
        text = module.bundle()
        self.assertEqual(text, module.bundle())
        self.assertEqual(text, module.TARGET.read_text(encoding='utf-8'))
        self.assertLess(len(text.splitlines()), 400)
        self.assertNotIn('require(', text)
        import json
        self.assertIn(json.dumps((ROOT / 'melee/pc/scripts/lib/pickup_juice.lua').read_text(encoding='utf-8'), ensure_ascii=False), text)
        self.assertIn('app.retire = function() missions.install.retire(mission) end', text)
        self.assertNotIn('function on_frame_pre()', text)
        self.assertNotIn('mission:pre_frame()', text)
        self.assertIn('missions.mission_launch = nil', text)

    def test_all_runtime_sources_are_embedded_verbatim(self):
        import json
        module = self.module()
        text = module.bundle()
        for name in module.MISSION_MODULES:
            source = (module.MISSIONS / (name + '.lua')).read_text(encoding='utf-8')
            self.assertIn(json.dumps(source, ensure_ascii=False), text)
        for name in module.ENVOY_MODULES:
            source = (module.SCRIPTS / (name + '.lua')).read_text(encoding='utf-8')
            self.assertIn(json.dumps(source, ensure_ascii=False), text)

    def test_fixed_native_radius_tracks_the_single_tuning_table(self):
        import json
        module=self.module()
        definition=module.drive_definition()
        current=json.loads(module.DRIVE.read_text())
        self.assertEqual(definition,current)
        self.assertEqual(definition['radius']*definition['visual']['scale'],17.5)
        changed=module.drive_definition('pickup_base=20,')
        self.assertEqual(changed['radius']*changed['visual']['scale'],20)
        for key in current:
            if key!='radius': self.assertEqual(changed[key],current[key])
        with self.assertRaises(ValueError): module.drive_definition('pickup_base=-1,')


if __name__ == '__main__':
    unittest.main()
