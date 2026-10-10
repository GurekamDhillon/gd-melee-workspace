"""The hitbox timing the engine really runs versus the windows gameplay.json declares (dair, 2026-10-10)."""
import unittest
from tools.test_support import require_game

require_game('pc/geno/geno.h')
from tools.geno import report, script

BOX = "joint=3 damage=10 size=2.4 x=0 y=0 z=0 angle=361 kbg=90 fkb=0 bkb=15"


def words(text):
    return script.assemble(text, [])


class TimingTests(unittest.TestCase):
    # What the Workbench wrote: window 0 moved past window 1, and the new hitbox reused slot 0 at frame 12.
    BAD = ("wait_until 12\nhitbox slot=0 %s\nwait 4\nclear_hitboxes\n"
           "wait_until 9\nhitbox slot=0 %s\nwait 6\nclear_hitboxes\n"
           "wait_until 12\nhitbox slot=0 %s\nwait 3\nclear_hitboxes\nwait_until 26\niasa\n") % (BOX, BOX, BOX)
    GOOD = ("wait_until 9\nhitbox slot=0 %s\nwait_until 12\nhitbox slot=1 %s\nhitbox slot=2 %s\n"
            "wait_until 15\nclear_hitbox hit_idx=0\nclear_hitbox hit_idx=2\nwait_until 16\nclear_hitboxes\n"
            "wait_until 26\niasa\n") % (BOX, BOX, BOX)

    def test_rewound_wait_until_is_a_blocker_with_a_readable_reason(self):
        problems = report.timing_problems(words(self.BAD))
        self.assertTrue(any("wait_until 9 comes after frame 16" in p for p in problems), problems)
        self.assertTrue(any("wait_until 12 comes after frame 15" in p for p in problems), problems)

    def test_the_old_window_check_alone_accepted_the_bad_script(self):
        info = report.frames(words(self.BAD))
        self.assertEqual([(b['start'], b['end'] - b['start']) for b in info['hitboxes']], [(12, 4), (9, 6), (12, 3)])

    def test_overlapping_hitboxes_on_one_slot_are_reported(self):
        text = "wait_until 2\nhitbox slot=0 %s\nwait_until 3\nhitbox slot=0 %s\nwait_until 8\nclear_hitboxes\n" % (BOX, BOX)
        self.assertTrue(any("slot 0" in p for p in report.timing_problems(words(text))))

    def test_ordered_script_with_per_slot_clears_is_sound_and_windows_follow_file_order(self):
        w = words(self.GOOD)
        self.assertEqual(report.timing_problems(w), [])
        info = report.frames(w)
        self.assertEqual([(b['start'], b['end'] - b['start']) for b in info['hitboxes']], [(9, 6), (12, 4), (12, 3)])
        self.assertEqual([b['slot'] for b in info['hitboxes']], [0, 1, 2])


if __name__ == '__main__':
    unittest.main()
