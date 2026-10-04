"""Registry manifest tests use synthetic bytes, never disc locations."""
from pathlib import Path
import importlib.util
import unittest


class ManifestTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('roster_stress',Path(__file__).with_name('roster_stress.py'))
        self.m=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.m)

    def test_native_manifest_has_100_independent_rows(self):
        self.assertTrue(hasattr(self.m,'native_manifest'),'native manifest writer missing')
        raw=self.m.native_manifest('Sonic',31,30,100,b'table',b'fighter',b'animation')
        rows=self.m.read_native_manifest(raw)
        self.assertEqual(len(rows),100)
        self.assertEqual(rows[0]['name'],'Sonic 001')
        self.assertEqual(rows[-1]['name'],'Sonic 100')
        self.assertEqual(len({r['key'] for r in rows}),100)
        self.assertEqual({r['internal'] for r in rows},{31})

    def test_truncated_and_bad_version_refused(self):
        self.assertTrue(hasattr(self.m,'native_manifest'),'native manifest writer missing')
        raw=self.m.native_manifest('Sonic',31,30,100,b't',b'p',b'a')
        for bad in (raw[:-1],b'WRONG001'+raw[8:],raw+b'x'):
            with self.assertRaises(ValueError):self.m.read_native_manifest(bad)
        hidden=bytearray(raw);hidden[36+47]=1
        with self.assertRaises(ValueError):self.m.read_native_manifest(hidden)

    def test_manifest_bounds(self):
        self.assertTrue(hasattr(self.m,'native_manifest'),'native manifest writer missing')
        for n,k in [(0,31),(65535,31),(100,128)]:
            with self.assertRaises(ValueError):self.m.native_manifest('Sonic',k,30,n,b't',b'p',b'a')

    def test_native_catalogue_core_exists(self):
        root=Path(__file__).resolve().parents[2]
        self.assertTrue((root/'melee/pc/platform/gw_roster_catalog.h').exists(),
                        'dynamic catalogue core missing')


if __name__=='__main__':unittest.main()
