import tempfile
from pathlib import Path
import unittest

from tools.geno.moves_check import moves_diff


class LogCompletionTests(unittest.TestCase):
    def load_text(self, text):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.log"
            path.write_text(text, encoding="utf-8")
            return moves_diff.load(path)

    def test_incomplete_or_failed_runs_are_not_parity(self):
        record = 'MOVECHK {"name":"jab"}\n'
        for text in ("", record, record + "MOVECHK DONE 2\n",
                     record + "MOVECHK FAIL crash\nMOVECHK DONE 1\n",
                     record + 'MOVECHKPART air 1 2 {\nMOVECHK DONE 1\n'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.load_text(text)

    def test_complete_run_loads(self):
        records, _ = self.load_text('MOVECHK {"name":"jab"}\nMOVECHK DONE 1\n')
        self.assertEqual(set(records), {"jab"})


if __name__ == "__main__":
    unittest.main()
