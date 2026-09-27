"""Small safety checks for the read-only stage-parts entry point."""

import importlib.util
from pathlib import Path
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("stage_parts", HERE / "stage_parts.py")
stage_parts = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stage_parts)


class StagePartsTest(unittest.TestCase):
    def test_env_path_handles_export_and_quotes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / ".env").write_text('export GW_ISO_ACE="disc.iso"\n', encoding="utf-8")
            self.assertEqual(stage_parts.iso_from_env(root), root / "disc.iso")

    def test_stage_name_is_allowlisted(self):
        self.assertEqual(stage_parts.stage_filename("GrNBa"), "GrNBa.dat")
        with self.assertRaises(ValueError):
            stage_parts.stage_filename("../GrNBa")

    def test_output_root_is_fixed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(stage_parts.output_root(root), root / "_build" / "tmp" / "stage-parts")


if __name__ == "__main__":
    unittest.main()
