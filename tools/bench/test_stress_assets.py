import importlib.util
from pathlib import Path
import struct
import tempfile
import unittest

spec=importlib.util.spec_from_file_location('stress_assets',Path(__file__).with_name('generate_stress_assets.py'))
assets=importlib.util.module_from_spec(spec);spec.loader.exec_module(assets)

class StressAssetsTests(unittest.TestCase):
    def test_generated_mesh_bounds_indices_and_atlas(self):
        with tempfile.TemporaryDirectory() as temp:
            root=assets.generate(temp)
            data=(root/'models/bench_lit.gxmesh').read_bytes()
            magic,version,nv,ni,x,y,z,vo,io=struct.unpack_from('>4sIIIfffII',data)
            self.assertEqual((magic,version,nv,ni,vo,io),(b'GXMS',2,24,36,36,804))
            self.assertEqual(len(data),io+ni*2)
            self.assertLess(max(struct.unpack_from('>36H',data,io)),nv)
            tex=(root/'models/bench_white.gxtex').read_bytes()
            self.assertEqual(len(tex),128)
            self.assertEqual(struct.unpack_from('>4sIIII',tex),(b'GXTX',1,6,4,4))
            self.assertTrue((root/'shaders/cel-outline.wgsl').exists())
            self.assertTrue((root/'models/bench_glass.material.json').exists())

if __name__=='__main__':unittest.main()
