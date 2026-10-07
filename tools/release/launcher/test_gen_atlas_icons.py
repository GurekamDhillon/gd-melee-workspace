import os, subprocess, sys, tempfile, unittest
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import gen_atlas_icons as G


class Icons(unittest.TestCase):
    def test_render_names_every_icon(self):
        text = G.render()
        for n in G.NAMES:
            self.assertIn('name == "%s"' % n, text)

    def test_relative_path(self):
        self.assertEqual(G.path_calls("M4 12l5 5 11-11", "check"), ["p.moveTo(4, 12);", "p.lineTo(9, 17);", "p.lineTo(20, 6);"])

    def test_unsupported_command_names_the_icon(self):
        with self.assertRaises(ValueError) as e:
            G.path_calls("M0 0A5 5 0 0 1 10 10", "round")
        self.assertIn("round", str(e.exception))

    def test_committed_header_is_current(self):
        self.assertEqual(subprocess.call([sys.executable, os.path.join(HERE, "gen_atlas_icons.py"), "--check"]), 0,
                         "atlas_icons.h is stale or edited: run gen_atlas_icons.py")

    def test_check_fails_when_edited_by_hand(self):
        p = os.path.join(tempfile.mkdtemp(), "atlas_icons.h")
        self.assertEqual(G.main([], out=p), 0)                      # write
        self.assertEqual(G.main(["--check"], out=p), 0)             # current
        with open(p, "a") as f:
            f.write("// hand edit" + chr(10))
        self.assertEqual(G.main(["--check"], out=p), 1)             # edited


if __name__ == "__main__":
    unittest.main()
