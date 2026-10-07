"""Generate original, disc-free benchmark geometry and copy this project's sample shaders."""
from pathlib import Path
import os
import json
import struct

ROOT = Path(__file__).resolve().parents[2]
MELEE = Path(os.environ.get('GW_MELEE') or ROOT / 'melee').expanduser().resolve()

def generate(destination=None):
    dest = Path(destination or MELEE / 'pc/scripts/examples/bench')
    model = dest / 'models'; model.mkdir(parents=True, exist_ok=True)
    shader = dest / 'shaders'; shader.mkdir(parents=True, exist_ok=True)
    # Six cube faces, with explicit normals, UVs and big-endian GXMS v2 fields.
    faces = [((0,0,1),[(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]),
             ((0,0,-1),[(1,-1,-1),(-1,-1,-1),(-1,1,-1),(1,1,-1)]),
             ((1,0,0),[(1,-1,1),(1,-1,-1),(1,1,-1),(1,1,1)]),
             ((-1,0,0),[(-1,-1,-1),(-1,-1,1),(-1,1,1),(-1,1,-1)]),
             ((0,1,0),[(-1,1,1),(1,1,1),(1,1,-1),(-1,1,-1)]),
             ((0,-1,0),[(-1,-1,-1),(1,-1,-1),(1,-1,1),(-1,-1,1)])]
    vertices, indices = [], []
    for normal, corners in faces:
        start = len(vertices)
        for point, uv in zip(corners, [(0,0),(1,0),(1,1),(0,1)]):
            vertices.append(struct.pack('>8f', *(v*4 for v in point), *uv, *normal))
        indices.extend(start+i for i in [0,1,2,0,2,3])
    header = struct.pack('>4sIIIfffII', b'GXMS',2,len(vertices),len(indices),8,8,8,36,36+len(vertices)*32)
    mesh = header + b''.join(vertices) + struct.pack('>36H', *indices)
    tex = struct.pack('>4sIIIIIIIIII', b'GXTX',1,6,4,4,0xffffffff,0,64,0,64,128)
    (model/'bench_white.gxtex').write_bytes(tex + bytes(64-len(tex)) + b'\xff'*64)
    for name, material, alpha in [('bench_lit', {'builtin':'lit'}, 0),
                                  ('bench_glass', {'builtin':'glass','opacity':.32,'roughness':.25,'tint':[.65,.85,1,1]},1)]:
        (model/(name+'.gxmesh')).write_bytes(mesh)
        (model/(name+'.coll.json')).write_text(json.dumps({'version':1,'atlas':'bench_white','alpha':alpha,'lines':[]}))
        (model/(name+'.material.json')).write_text(json.dumps(material))
    sources = [MELEE/'pc/geno/mods/shader-demo/shaders', MELEE/'pc/scripts/examples/surface-shaders/shaders']
    for source in sources:
        for path in source.glob('*.wgsl'): (shader/path.name).write_bytes(path.read_bytes())
    (shader/'clank.wgsl').write_text('return mix(previous_color(in.uv), vec4f(1.0,0.8,0.3,1.0), 0.12);\n')
    return dest

if __name__ == '__main__': print(generate())
