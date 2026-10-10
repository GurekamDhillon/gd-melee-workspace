"""Focused numerical and generated-contract checks for the lossy art adapter."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('xv2_to_artist',ROOT/'ports/goku-xv2/tools/xv2_to_artist.py')
adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)


class Adapter(unittest.TestCase):
    def test_remap_merges_before_two_influence_limit(self):
        pairs,lost=adapter.reduce_weights(['f_A','f_B','b_R_Hand','b_L_Hand'],[.3,.3,.25,.15])
        self.assertEqual([x[0] for x in pairs],['b_C_Head','b_R_Hand'])
        self.assertAlmostEqual(sum(x[1] for x in pairs),1)
        self.assertAlmostEqual(lost,.15)

    def test_reflected_basis_and_slerp(self):
        np.testing.assert_allclose(adapter.BASIS@[0,0,-1],[0,0,1])
        self.assertEqual(np.linalg.det(adapter.BASIS),-1)
        q=adapter.sample_track([[0,0,0,0,1],[2,0,1,0,0]],[1],True)[0]
        np.testing.assert_allclose(abs(q),[0,2**-.5,0,2**-.5],atol=1e-7)

    def test_checksum_cannot_be_bypassed_with_cached_path(self):
        source=adapter.Source(ROOT/'ports/goku-xv2/ir/goku.xv2.ir.json')
        blob=source.assets['models'][0]['engine']['xv2.pc']['geometry']
        source.blob(blob)
        with self.assertRaisesRegex(ValueError,'Conflicting BlobRef'):
            source.blob({**blob,'sha256':'0'*64})

    def test_missing_parity_rejected(self):
        d=json.loads((ROOT/'ports/goku-xv2/ir/goku.xv2.ir.json').read_text())
        d['parity']=[]
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'ir.json';p.write_text(json.dumps(d))
            with self.assertRaisesRegex(ValueError,'parity'):
                adapter.Source(p)

    def test_throw_crop_and_all_role_parity_preserved(self):
        source=adapter.Source(ROOT/'ports/goku-xv2/ir/goku.xv2.ir.json')
        rs=adapter.row_specs(source)['ThrowF']
        # 2026-10-08 hurt/throw pass (tools/rowmap.py) replaced the 5x crop of BAC 601 with a 1x crop of the lift-and-toss f16-45
        self.assertEqual((rs['start'],rs['frames']),(16,30))
        self.assertNotIn('time_factor',rs)
        self.assertEqual(rs.get('events',[]),[],'BAC events must not override the authored crop')
        chest=[p for p in source.parity_rows if p['here'].endswith('/b_C_Chest')]
        self.assertEqual(len(chest),2,'Anatomical chest and authored grab-anchor decisions must both survive')

    def test_generated_skin_budgets_and_inverse_binds(self):
        cfg=ROOT/'_build/goku-xv2/author-source/fighter.json'
        self.assertTrue(cfg.exists(),'Run xv2_to_artist.py first')
        f=adapter.model.load(cfg)
        mesh=adapter.model.mesh(f)
        self.assertLessEqual(len(f.bones)+3,128)
        self.assertLessEqual(len(set(mesh['jts'][mesh['wts']>1e-6].astype(int))),64)
        self.assertLessEqual(int((mesh['wts']>1e-6).sum(axis=1).max()),2)
        np.testing.assert_allclose(mesh['wts'].sum(axis=1),1,atol=1e-6)
        self.assertAlmostEqual(float(mesh['pos'][:,1].min()),0,places=5)
        self.assertGreater(float(mesh['pos'][:,1].max()),8)
        self.assertLessEqual(float(mesh['pos'][:,1].max()),20.00001)
        ibm=adapter.model.AF.accessor(f.g,f.bin,f.skins[0]['inverseBindMatrices'])
        for bone,inv in zip(f.bones,ibm):
            np.testing.assert_allclose(bone.world@inv.reshape(4,4).T,np.eye(4),atol=2e-5)
        self.assertEqual(len(f.rows),351)
        for row in ('EscapeF','EscapeB'):
            self.assertTrue(f.clips[row].root_motion)
            self.assertIn(('b_C_Base','translation'),f.clips[row].chan)


if __name__=='__main__':unittest.main()
