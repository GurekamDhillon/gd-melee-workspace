import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
import analyze as a


def part(i,region='torso',bounds=None):
    return {'index':i,'source':0,'joint':0,'material':0,'material_data':0,'triangles':20,'status':0,'hidden':0,
      'item_kind':-1,'item_ordinal':-1,'path':i,'area':10,'bounds':bounds or [0,0,0,3,3,3],
      'regions':{region:1},'visibility_model':-1,'visibility_state':-1}

class AnalysisTests(unittest.TestCase):
    def test_paired_ids_reject_static_background_and_blended_edges(self):
        color=a.palette(3);one=np.zeros((8,8,3),np.uint8);two=one.copy()
        one[2:6,2:6]=color[1];two[2:6,2:6]=255-color[1]
        one[0,0]=two[0,0]=color[0] # HUD collision has no matching inverse
        one[3,3]=(one[3,3].astype(int)//2).astype(np.uint8) # partially covered pixel
        ids,counts,clipped=a.decode_pair(one,two,3)
        self.assertEqual(counts.tolist(),[0,15,0]);self.assertEqual(ids[0,0],-1);self.assertFalse(clipped)

    def test_all_512_ids_roundtrip(self):
        colors=a.palette(512).reshape(16,32,3)
        ids,counts,_=a.decode_pair(colors,255-colors,512)
        np.testing.assert_array_equal(ids.ravel(),np.arange(512));self.assertTrue(np.all(counts==1))

    def test_png_builtin_matches_exact_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'image.png';pixels=np.arange(256,dtype=np.uint8).reshape(8,8,4)
            a.png_write(path,pixels);np.testing.assert_array_equal(a.png_read_builtin(path),pixels)

    def test_equipment_is_not_merged_into_hand(self):
        hand=part(0,'right_hand');sword=part(1,'right_hand',[0,0,0,.15,12,.2])
        for p in (hand,sword):p.update(key='d'+str(p['index']),mean_coverage=.1)
        groups=a.make_groups([hand,sword]);self.assertEqual(len(groups),2)
        self.assertTrue(sword['equipment_candidate']);self.assertEqual(sword['suggested_name'],'Equipment candidate')

    def test_wide_hand_attachment_stays_independent(self):
        hand,shield=part(0,'right_hand'),part(1,'right_hand',[0,0,0,8,8,1])
        for p in (hand,shield):p.update(key='d'+str(p['index']),mean_coverage=.1)
        self.assertEqual(len(a.make_groups([hand,shield])),2)

    def test_non_body_attachment_is_not_assumed_to_be_torso(self):
        sheath=part(0,'torso');sheath.update(joint=70,body_joint=0,key='d0',mean_coverage=.03)
        groups=a.make_groups([sheath]);self.assertTrue(groups[0]['equipment_candidate'])
        self.assertEqual(groups[0]['suggested_name'],'Attachment candidate #0')

    def test_symmetric_feet_mesh_is_not_claimed_as_one_foot(self):
        p=part(0);p['regions']={'left_foot':.47,'right_foot':.48,'left_leg':.05}
        self.assertEqual(a.classify(p)[:2],('feet',.95))

    def test_mixed_and_missing_mapping_are_honest(self):
        p=part(0);p['regions']={'torso':.55,'left_arm':.45}
        self.assertEqual(a.classify(p)[2],'Mixed body regions')
        p['regions']={};self.assertEqual(a.classify(p)[2],'Unclassified surface')
        p['regions']={'head':1};p['status']=2;self.assertLess(a.classify(p)[1],.7)

    def test_exclusive_visibility_requires_disjoint_masks(self):
        x,y=part(0),part(1);x.update(key='d0',visibility_model=2,visibility_state=3)
        y.update(key='d1',visibility_model=2,visibility_state=2)
        self.assertEqual(a.alternatives([x,y]),[])
        y['visibility_state']=4;self.assertEqual(len(a.alternatives([x,y])),1)

    def test_group_coverage_uses_visible_pixel_union_and_missing_as_zero(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);parts=[part(0),part(1)];colors=a.palette(2)
            for sample in range(2):
                one=np.zeros((20,20,3),np.uint8);two=one.copy()
                one[4:16,4:16]=colors[0];two[4:16,4:16]=255-colors[0]
                if sample==0:one[4:10,4:16]=colors[1];two[4:10,4:16]=255-colors[1]
                a.png_write(root/f'{sample}-a.png',one);a.png_write(root/f'{sample}-b.png',two)
                record={'parts':parts,'geometry_signature':'test','costume':0,'a':f'{sample}-a.png','b':f'{sample}-b.png',
                  'pose':'Wait','view':str(sample),'requested_frame':1,'actual_frame':0,'motion':14,'pose_execution':'forced_common_motion'}
                (root/f'{sample}.json').write_text(json.dumps(record))
            manifest=root/'falco-manifest.json';manifest.write_text(json.dumps({'character':'falco','asset_sha256':'abc','samples':['0.json','1.json'],'failures':[]}))
            report=a.analyze_manifest(manifest)
            self.assertAlmostEqual(report['controls'][0]['mean_coverage'],1)
            bykey={p['key']:p for p in report['parts']}
            self.assertAlmostEqual(bykey['d1']['mean_coverage'],.25)
            self.assertEqual(bykey['d1']['visible_fraction'],.5)
            self.assertFalse(report['shared_materials'][0]['coupled_by_current_api'])
            a.write_outputs(root,report);self.assertTrue((root/'falco-review.html').exists())
            self.assertFalse(a.apply_reviews(report,{'fingerprint':'stale','controls':[]}))
            review={'fingerprint':report['fingerprint'],'controls':[{'id':report['controls'][0]['id'],'label':'Reviewed jacket'}]}
            self.assertTrue(a.apply_reviews(report,review));self.assertEqual(report['controls'][0]['label'],'Reviewed jacket')

if __name__=='__main__':unittest.main()
