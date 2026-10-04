"""Profile bootstrap cannot overwrite an existing or unreadable destination."""
import importlib.util
from pathlib import Path
import tempfile
import unittest


class ProfileTests(unittest.TestCase):
    def module(self):
        spec = importlib.util.spec_from_file_location('envoy_profile', Path(__file__).with_name('envoy_profile.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_new_profile_comes_from_lua_schema(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / 'profile.envoy'
            module.initialize(target)
            text = target.read_text(encoding='utf-8')
            self.assertTrue(text.startswith('ENVOY 4\nprofile 1 1 0 none\n'))
            self.assertIn('stat power C 0 0 C 0 0\n', text)
            self.assertEqual(text, module.default_bytes().decode('utf-8'))

    def test_existing_empty_corrupt_and_valid_files_preserved(self):
        module = self.module()
        for old in (b'', b'corrupt', module.default_bytes()):
            with tempfile.TemporaryDirectory() as temp:
                target = Path(temp) / 'profile.envoy'
                target.write_bytes(old)
                with self.assertRaises(FileExistsError):
                    module.initialize(target)
                self.assertEqual(target.read_bytes(), old)

    def test_destination_directory_refused(self):
        module = self.module()
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(OSError):
                module.initialize(Path(temp))


if __name__ == '__main__':
    unittest.main()
