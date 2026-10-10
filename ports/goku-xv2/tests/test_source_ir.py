"""Handoff acceptance tests, including checks the shared validator does not perform."""
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[3]
PORT=ROOT/'ports/goku-xv2'
def walk(x):
    yield x
    if isinstance(x,dict):
        for v in x.values(): yield from walk(v)
    if isinstance(x,list):
        for v in x: yield from walk(v)

class SourceIR(unittest.TestCase):
    def test_source_and_parity_contract(self):
        path=PORT/'ir/goku.xv2.ir.json'
        self.assertTrue(path.is_file(),'Source character document is missing')
        d=json.loads(path.read_text()); h=json.loads((PORT/'ir/host.melee.ir.json').read_text())
        self.assertEqual(d['subject']['engine'],'xv2.pc')
        schemas=json.loads((ROOT/'ports/ir/schema/behavior.schema.json').read_text())
        inputs=set(schemas['$defs']['Move']['properties']['input']['enum'])
        self.assertEqual({m['input'] for m in d['behavior']['moves']},inputs)
        self.assertGreaterEqual(len(d['assets']['skeletons']),3)
        self.assertEqual(len([s for s in d['assets']['skeletons'] if s.get('engine',{}).get('xv2.pc',{}).get('purpose')=='render']),3)
        ids={x['id'] for x in walk(d) if isinstance(x,dict) and isinstance(x.get('id'),str)}
        hostids={x['id'] for x in walk(h) if isinstance(x,dict) and isinstance(x.get('id'),str)}
        for row in d['parity']:
            self.assertIn(row['here'],ids)
            doc,ref=row['there'].split('#',1)
            self.assertEqual(doc,h['document_id']); self.assertIn(ref,hostids)
            self.assertTrue(row['differences'])
        for m in d['behavior']['moves']:
            self.assertTrue(any(p['here']==m['id'] for p in d['parity']),m['id'])
        for x in walk(d):
            if isinstance(x,dict):
                self.assertNotEqual(x.get('confidence'),'observed')
                if 'stability' in x: self.assertIn('space',x); self.assertIn('value',x)
                for field in ('vertices','keys','pixels'):
                    self.assertFalse(isinstance(x.get(field),list),f'Embedded bulk data: {field}')
        self.assertEqual(d['coverage']['behavior.attributes']['status'],'absent')
        self.assertEqual(d['coverage']['assets.audio']['status'],'absent')

if __name__=='__main__': unittest.main()
