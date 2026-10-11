"""The hand-animation file is a Stage A input, and the converter never writes it (offline)."""
import importlib.util
import os
from pathlib import Path
import sys
import unittest

PORT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PORT / 'tools'))


class HandInput(unittest.TestCase):
    def test_hand_file_triggers_stage_a(self):
        tmp = PORT.parents[1] / '_build/_test_hand_input'
        tmp.mkdir(parents=True, exist_ok=True)
        hand = tmp / 'hand.json'
        hand.write_text('{}')
        fighter = tmp / 'fighter.json'
        fighter.write_text('{}')
        os.environ['GOKU_HAND'] = str(hand)
        try:
            spec = importlib.util.spec_from_file_location('goku_build_hand', PORT / 'tools/build.py')
            b = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(b)
            self.assertIn(hand.resolve(), b.stage_a_inputs(fighter))
            before = b.stage_a_signature(fighter)
            hand.write_text('{"x": 1}')
            self.assertNotEqual(before, b.stage_a_signature(fighter))
        finally:
            os.environ.pop('GOKU_HAND', None)

    def test_converter_only_reads_it(self):
        text = (PORT / 'tools/xv2_to_artist.py').read_text(encoding='utf-8')
        self.assertIn('HAND_FILE', text)
        self.assertNotIn('HAND_FILE.write', text)
        self.assertNotIn("open(HAND_FILE, 'w", text)


if __name__ == '__main__':
    unittest.main()
