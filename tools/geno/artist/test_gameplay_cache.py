"""Cached gameplay rebuild guard tests use authored synthetic paths only."""
import json
import os
from pathlib import Path
import tempfile
import unittest

from tools.geno.artist import gameplay_cache as cache


class GameplayCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.cfg = {'schema': 'geno-artist/1', 'key': 'pip',
                    'art': {'blend': 'pip.blend', 'glb': 'pip.glb'},
                    'attributes': {'weight': 90}, 'moves': {}}
        self.path = self.root / 'fighter.json'
        self.save()
        for name in ('pip.blend', 'pip.glb'): (self.root / name).write_text('authored fixture')
        self.out = self.root / 'build'
        self.out.mkdir()
        cache.write(self.path, self.out, token='Pip', costumes=[{'name': 'red', 'label': 'Red', 'team': 'red'}],
                    height=12.0, ref_speeds={'Run': 1.5})

    def save(self):
        self.path.write_text(json.dumps(self.cfg), encoding='utf-8')

    def test_gameplay_edits_keep_art_cache_and_reference_speeds(self):
        self.cfg.update(attributes={'weight': 110}, jumps={'max': 3},
                        moves={'hitbox_scale': 1.2}, name='New name')
        self.save()
        data = cache.read_current(self.path, self.out)
        self.assertEqual(data['token'], 'Pip')
        self.assertEqual(data['height'], 12.0)
        self.assertEqual(data['ref_speeds'], {'Run': 1.5})
        self.assertEqual(data['costumes'][0]['name'], 'red')

    def test_changed_art_is_refused_before_any_package_write(self):
        p = self.root / 'pip.blend'
        stamp = p.stat().st_mtime_ns
        os.utime(p, ns=(stamp + 1_000_000, stamp + 1_000_000))
        with self.assertRaisesRegex(ValueError, 'full build'):
            cache.read_current(self.path, self.out)

    def test_changed_clip_mapping_cannot_reuse_old_bank(self):
        self.cfg['clips'] = {'map': {'jab1': 'DifferentClip'}}
        self.save()
        with self.assertRaisesRegex(ValueError, 'full build'):
            cache.read_current(self.path, self.out)

    def test_missing_cache_requires_one_full_build(self):
        (self.out / cache.NAME).unlink()
        with self.assertRaisesRegex(ValueError, 'full build'):
            cache.read_current(self.path, self.out)

    def test_missing_art_does_not_count_as_current(self):
        (self.root / 'pip.glb').unlink()
        with self.assertRaisesRegex(ValueError, 'full build'):
            cache.read_current(self.path, self.out)

    def test_external_art_is_tracked_even_outside_the_project_directory(self):
        external = tempfile.TemporaryDirectory()
        self.addCleanup(external.cleanup)
        path = Path(external.name) / 'outside.glb'
        path.write_text('authored external fixture')
        self.cfg['art']['glb'] = str(path)
        self.save()
        cache.write(self.path, self.out, token='Pip', costumes=[], height=12, ref_speeds={})
        stamp = path.stat().st_mtime_ns
        os.utime(path, ns=(stamp + 1_000_000, stamp + 1_000_000))
        with self.assertRaisesRegex(ValueError, 'full build'):
            cache.read_current(self.path, self.out)

    def test_authored_comments_do_not_invalidate_stage_a(self):
        self.path.write_text('// Art and gameplay notes are supported\n' +
                             json.dumps(self.cfg) + '\n  // End note\n', encoding='utf-8')
        self.assertEqual(cache.read_current(self.path, self.out)['token'], 'Pip')


if __name__ == '__main__':
    unittest.main()
