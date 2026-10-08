"""Asset-free output safety tests for the local Sora converter."""
from pathlib import Path
import unittest

import trail_define


class OutputSafetyTests(unittest.TestCase):
    def test_only_build_descendants_are_outputs(self):
        root = Path.cwd()
        install = root / "_build" / "baseline"
        namespace = root / "_build" / "tmp" / "geno-slice8"
        self.assertEqual(trail_define.output_destination(namespace / "generated", install),
                         (namespace / "generated").resolve())
        for output in (root / "ports" / "generated", root / "_build", install,
                       install / "child", root / "_build" / ".." / "ports",
                       namespace, root / "_build" / "generated",
                       root / "ports" / "_build" / "tmp" / "geno-slice8" / "generated"):
            with self.subTest(output=output), self.assertRaises(ValueError):
                trail_define.output_destination(output, install)
        with self.assertRaises(ValueError):
            trail_define.output_destination(namespace / "generated", install,
                                           [namespace / "generated" / "moveset.json"])


if __name__ == "__main__":
    unittest.main()
