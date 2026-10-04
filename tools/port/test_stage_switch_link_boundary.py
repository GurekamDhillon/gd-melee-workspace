"""Source contract for the reported retargeted-link failures; no game build."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[2] / 'melee'

class StageLinkBoundary(unittest.TestCase):
    def test_reader_avoids_unprovided_libc(self):
        source = (ROOT / 'pc/gameworld/script_stage_dat.h').read_text()
        self.assertIsNone(re.search(r'\bmemchr\s*\(', source))

    def test_slot_uses_ground_accessor(self):
        source = (ROOT / 'pc/gameworld/script_stage_slots.inc').read_text()
        self.assertIsNone(re.search(r'\bstrchr\s*\(|\bstage_datas\b', source))
        self.assertIn('Ground_StageSlotDataFile(kind)', source)

if __name__ == '__main__':
    unittest.main()
