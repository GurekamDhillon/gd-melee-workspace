"""Synthetic archives only: no disc required or written by these tests."""
import importlib.util
from pathlib import Path
import struct
import unittest
from tools.test_support import ROOT, require_path

HERE = Path(__file__).resolve().parent


def load_tool():
    spec = importlib.util.spec_from_file_location('roster_stress', HERE / 'roster_stress.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(m):
    data = bytearray(0x100)
    rel = set()
    def alloc(b):
        data.extend(bytes((-len(data)) % 4))
        at = len(data)
        data.extend(b)
        return at
    def put(o, v, ptr=False):
        struct.pack_into('>I', data, o, v)
        if ptr: rel.add(o)
    meta, ft, menu, ff, kd, kf = 64, 0x100, 0x190, 0x1A0, 0x260, 0x288
    data.extend(bytes(0x2B0-len(data)))
    for i, p in [(0,meta),(1,menu),(2,ft),(3,ff),(8,kd),(9,kf)]: put(i*4,p,True)
    nk = ne = 40
    for o,v in [(meta+4,nk),(meta+8,ne),(meta+12,1)]:put(o,v)
    name = alloc(b'Sonic\0'); pl = alloc(b'PlSn.dat\0')
    for off,nm,space,stride in m.FIGHTER_TABLES:
        rows = bytearray(nk*stride)
        if nm == 'names':
            for e in range(ne): struct.pack_into('>I', rows,e*4,name)
        elif nm == 'pl_file':
            for k in range(nk):struct.pack_into('>II',rows,k*8,pl,0)
        elif nm == 'ft_kind_desc':
            for e in range(ne):rows[e*3:e*3+3]=bytes([e,255,0])
        else:
            for k in range(nk): rows[k*stride:(k+1)*stride]=bytes([k])*stride
        t=alloc(rows);put(ft+off,t,True)
        if nm in ('names','pl_file'):
            for k in range(nk):rel.add(t+k*stride)
    for i in range(46):
        stride = 8 if i in (29,30) else 4
        t=alloc(b''.join(bytes([k])*stride for k in range(nk)));put(ff+4*i,t,True)
    for i,st in enumerate((8,4,4,4,1,4,4,4,4,4)):
        t=alloc(bytes(nk*st));put(kd+4*i,t,True)
    for i in range(9):
        t=alloc(bytes(nk*4));put(kf+4*i,t,True)
    css=alloc(bytes(0xDC)+bytes([0,31,0,0,20,20])+bytes(22)+bytes(28))
    put(menu+4,css,True)
    data.extend(bytes((-len(data))%4))
    r=b''.join(struct.pack('>I',o) for o in sorted(rel))
    tail=struct.pack('>II',0,0)+b'mexData\0'
    body=bytes(data)+r+tail
    return struct.pack('>5I',32+len(body),len(data),len(rel),1,0)+bytes(12)+body


class RosterTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue((HERE/'roster_stress.py').exists(), 'generator is missing')
        self.m=load_tool()

    def test_clones_preserve_bosses_and_relocations(self):
        raw=fixture(self.m)
        result, info=self.m.clone_mxdt(raw,31,31,3,existing_slots=7)
        a=self.m.mex_hsd.Archive(result); u=a.u32; b=a.public('mexData'); meta=u(b);ft=u(b+8)
        self.assertEqual([u(meta+4),u(meta+8),u(meta+12)],[43,43,4])
        desc=u(ft+12)
        self.assertEqual(list(a.data[desc+34*3:desc+34*3+3]),[37,255,0])
        self.assertEqual(list(a.data[desc+40*3:desc+40*3+3]),[34,255,0])
        names=u(ft)
        self.assertEqual(a.cstr(u(names+40*4)),'Sonic 001')
        self.assertEqual(a.cstr(u(names+42*4)),'Sonic 003')
        pl=u(ft+4)
        self.assertIn(pl+34*8,a.reloc_set)
        self.assertEqual(a.cstr(u(pl+34*8)),'PlSn.dat')
        self.assertEqual(info['slots_after'],10)
        self.assertEqual(len(info['tables']),98)
        for r in a.reloc_offsets:
            self.assertLess(r+3,len(a.data))
            self.assertLess(u(r),len(a.data))

    def test_limit_explains_largest_count(self):
        with self.assertRaisesRegex(ValueError,'largest admissible N is 63'):
            self.m.check_capacity(65,65,56,31,100)
        self.assertEqual(self.m.check_capacity(65,65,56,31,63),63)

    def test_invalid_count_and_table_are_rejected(self):
        for n in (-1,0):
            with self.assertRaises(ValueError):self.m.check_capacity(65,65,56,31,n)
        raw=bytearray(fixture(self.m));struct.pack_into('>I',raw,32+0x100+4,len(raw))
        with self.assertRaises(ValueError):self.m.clone_mxdt(bytes(raw),31,31,1,7)

    def test_output_cannot_escape_ignored_root(self):
        for name in ('../escape','a/b','C:\\escape','', '.', '..'):
            with self.assertRaises(ValueError):self.m.output_folder(name)

    def test_texture_remap_reads_original_keys(self):
        require_path(ROOT / 'experiment/brawl-kirby/tools/texanim_keys.py',
                     'requires optional experiment/brawl-kirby texture animation helper')
        # Rotating [A,B,C] into [C,A,B] exposes an in-place cascading-copy bug.
        raw=fixture(self.m);w=self.m.Writer(raw)
        stream=w.append(bytes([1,10,1,1,20,1,1,30]))
        f=w.append(bytes(20));w.put(f+4,8);w.data[f+12]=12;w.data[f+13]=0x60;w.put(f+16,stream)
        ao=w.append(bytes(16));w.put(ao+8,f)
        tex=w.append(bytes(16));w.put(tex+8,ao)
        self.m.remap_texanim(w,tex,[(0,2),(1,0),(2,1)],3)
        keys=self.m.texanim_keys._decode(w.data,f)
        self.assertEqual([k[2][0] for k in keys],[30,10,20])
        self.assertEqual(struct.unpack_from('>f',w.data,ao+4)[0],3)

    def test_custom_source_name(self):
        out,_=self.m.clone_mxdt(fixture(self.m),31,31,1,7,'Metal Sonic')
        ar=self.m.mex_hsd.Archive(out);ft=ar.u32(ar.public('mexData')+8)
        self.assertEqual(ar.cstr(ar.u32(ar.u32(ft)+40*4)),'Metal Sonic 001')


if __name__=='__main__':unittest.main()
