"""Source contract for the reported retargeted-link failures; no game build."""
import re
import unittest
from tools.test_support import require_game

class StageLinkBoundary(unittest.TestCase):
    def test_reader_avoids_unprovided_libc(self):
        source = require_game('pc/gameworld/script_stage_dat.h').read_text()
        self.assertIsNone(re.search(r'\bmemchr\s*\(', source))

    def test_slot_uses_ground_accessor(self):
        source = require_game('pc/gameworld/script_stage_slots.inc').read_text()
        self.assertIsNone(re.search(r'\bstrchr\s*\(|\bstage_datas\b', source))
        self.assertIn('Ground_StageSlotDataFile(kind)', source)

if __name__ == '__main__':
    unittest.main()
