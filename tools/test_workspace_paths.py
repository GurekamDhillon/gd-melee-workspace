"""Portable-path regressions; all inputs are synthetic, no builds or private settings."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = load('checker', ROOT / 'tools/check_workspace_paths.py')
response = load('response', ROOT / 'tools/port/link_response.py')


class RelocationTests(unittest.TestCase):
    def test_secret_redaction_and_read_only(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / '.env'
            original = b'export GW_ISO_ACE="C:/private/DO-NOT-PRINT.iso"\n'
            path.write_bytes(original)
            rows = list(checker.scan(path, '.env'))
            self.assertIn('GW_ISO_ACE [value redacted]', rows[0])
            self.assertNotIn('DO-NOT-PRINT', '\n'.join(rows))
            self.assertEqual(path.read_bytes(), original)

    def test_absolute_formats(self):
        for value in ['C:/old/root', r'C:\old\root', '/c/old/root', '/mnt/c/old/root']:
            self.assertIsNotNone(checker.ABSOLUTE.search(value))
        self.assertIsNone(checker.ABSOLUTE.search('Hi/Lw/F/B'))

    def test_lane_list_survives_move_with_spaces_and_apostrophe(self):
        with tempfile.TemporaryDirectory(prefix="Melee's workspace ") as directory:
            workspace = Path(directory)
            (workspace / '_build').mkdir()
            (workspace / '_build/melee_link_objects.rsp').write_text('../masstest/out/game.obj\n../masstest/shimobj/native.obj\n')
            build = workspace / '_build/agents/lane one'
            rows = response.response_text(workspace, build).splitlines()
            self.assertEqual(rows, ['"../agents/lane one/masstest/out/game.obj"', '"../agents/lane one/masstest/shimobj/native.obj"'])
            for row in rows:
                self.assertTrue((workspace / '_build/ax86m' / row.strip('"')).resolve().is_relative_to(build))
            # Same layout at another root yields byte-identical, root-free response text.
            moved = workspace / 'new root'
            (moved / '_build').mkdir(parents=True)
            (moved / '_build/melee_link_objects.rsp').write_text('../masstest/out/game.obj\n../masstest/shimobj/native.obj\n')
            self.assertEqual(response.response_text(workspace, build), response.response_text(moved, moved / '_build/agents/lane one'))

    def test_unknown_response_entry_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            (workspace / '_build').mkdir()
            (workspace / '_build/melee_link_objects.rsp').write_text('C:/stale/object.obj\n')
            with self.assertRaises(ValueError):
                response.response_text(workspace, workspace / '_build/agents/test')

    def test_python_root_defaults_reach_repository(self):
        # Inspect default expressions without importing converters that access disc assets.
        import ast
        for path in ROOT.rglob('*.py'):
            if path == Path(__file__):
                continue
            tree = ast.parse(path.read_text(encoding='utf-8-sig'))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call) or len(node.args) < 2:
                    continue
                if ast.unparse(node.func) != 'os.environ.get' or not isinstance(node.args[0], ast.Constant) or node.args[0].value != 'GW_ROOT':
                    continue
                default = ast.Expression(node.args[1])
                if 'Path(__file__).resolve().parents[' in ast.unparse(default):
                    self.assertEqual(Path(eval(compile(default, str(path), 'eval'), {'Path': Path, '__file__': str(path)})), ROOT, str(path))


if __name__ == '__main__':
    unittest.main()
