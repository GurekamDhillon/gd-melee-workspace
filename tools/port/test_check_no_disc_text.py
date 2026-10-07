"""python -m unittest tools/port/test_check_no_disc_text.py: the disc-text guard catches a decoded buffer reaching a log or a file."""
import os
import tempfile
import unittest

import check_no_disc_text as g

NL = chr(10)
BN = chr(92) + 'n'   # a backslash and an n: the C escape for a newline


def run(text):
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "src/melee/gm"))
    with open(os.path.join(d, "src/melee/gm/gmfrontend_atlas_data.inc"), "w", encoding="utf-8") as f:
        f.write(text)
    return g.problems(d)


class Guard(unittest.TestCase):
    def test_counts_only_passes(self):
        self.assertEqual(run('OSReport("frontend: sis probe: %d strings, %d chars, %d unknown glyphs\\n", n, c, u);\n'), [])

    def test_a_decoded_buffer_in_a_log_is_caught(self):
        self.assertEqual(len(run('OSReport("event %s\\n", name);\n')), 1)
        self.assertEqual(len(run('gw_log("msg: %s", buf);\n')), 1)
        self.assertEqual(len(run('fprintf(f, "%s", text);\n')), 1)

    def test_an_authored_screen_id_may_say_so(self):
        self.assertEqual(run('OSReport("frontend: Atlas data screen %s\\n", s->atlas_id); /* OK-NOTEXT */\n'), [])
        self.assertEqual(len(run('OSReport("frontend: Atlas data screen %s\\n", s->atlas_id);\n')), 1)

    def test_a_statement_that_spans_lines_is_one_statement(self):
        self.assertEqual(len(run(NL.join(['OSReport("event %s' + BN + '",', '         name);', '']))), 1)
        self.assertEqual(len(run(NL.join(['gw_log(', '    "msg: %s",', '    buf);', '']))), 1)

    def test_a_wrapped_format_is_one_format(self):
        self.assertEqual(len(run(NL.join(['OSReport("event "', '         "%s done' + BN + '", n);', '']))), 1)

    def test_a_marker_anywhere_in_a_wrapped_statement_counts(self):
        self.assertEqual(run(NL.join(['OSReport("screen %s' + BN + '",', '         s->atlas_id); /* OK-NOTEXT */', ''])), [])

    def test_the_door_files_are_covered(self):
        self.assertIn("pc/platform/gw_script_ui_set.inc", g.FILES)
        self.assertIn("pc/platform/gw_script_ui_data.inc", g.FILES)
        self.assertIn("src/melee/gm/gmfrontend_atlas_set.inc", g.FILES)

    def test_other_lines_are_ignored(self):
        self.assertEqual(run('snprintf(out, cap, "%s", name);\n'), [])


if __name__ == "__main__":
    unittest.main()
