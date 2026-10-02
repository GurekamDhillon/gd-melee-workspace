#!/usr/bin/env python3
"""Build original opaque room parts for the native roguelite model API.

All geometry and pixels originate in this file. The binary conventions follow
pc/scripts/examples/runtime_models/make_models.py and assets_src/bf_interior/
export_kit.py; their meshes, bakes, textures and any disc art are not inputs.
X is travel, Y height, +Z towards camera. Platform tops are local Y=0.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[2]
HEADER = struct.Struct('>4sIIIfffII')
THEMES = ('cobalt', 'fire', 'frost')
TYPES = ('platform', 'post', 'beam', 'portal', 'sigil', 'station', 'fascia')
# Eight 4x4 solid swatches: deep structure, cobalt, ivory, gold, theme accent,
# quieter structural trim, dark underside, bright cap. All pixels are opaque.
BASE_PALETTE = ((16, 26, 44), (30, 58, 140), (242, 239, 228), (240, 180, 41),
                (240, 180, 41), (84, 104, 138), (10, 14, 24), (222, 229, 243))
ACCENTS = {'cobalt': (240, 180, 41), 'fire': (255, 128, 80), 'frost': (143, 222, 246)}


class Mesh:
    def __init__(self):
        self.vertices = []
        self.indices = []

    def face(self, points, color):
        a, b, c = points[:3]
        u, v = [b[i] - a[i] for i in range(3)], [c[i] - a[i] for i in range(3)]
        n = (u[1]*v[2] - u[2]*v[1], u[2]*v[0] - u[0]*v[2], u[0]*v[1] - u[1]*v[0])
        length = math.sqrt(sum(x*x for x in n))
        assert length > 0
        normal = tuple(x / length for x in n)
        base = len(self.vertices)
        # Centre sampling prevents bleeding between solid swatches under linear filtering.
        uv = ((color + .5) / 8, .5)
        self.vertices.extend((*p, *uv, *normal) for p in points)
        for i in range(1, len(points) - 1):
            self.indices.extend((base, base+i, base+i+1))

    def box(self, x0, x1, y0, y1, z0, z1, color):
        assert x0 < x1 and y0 < y1 and z0 < z1
        corners = ((x0,y0,z0), (x1,y0,z0), (x1,y1,z0), (x0,y1,z0),
                   (x0,y0,z1), (x1,y0,z1), (x1,y1,z1), (x0,y1,z1))
        for face in ((0,3,2,1), (4,5,6,7), (0,4,7,3), (1,2,6,5), (3,7,6,2), (0,1,5,4)):
            self.face([corners[i] for i in face], color)

    def prism(self, polygon, z0, z1, color):
        """Convex CCW XY polygon, extruded with flat corner normals."""
        self.face([(x,y,z1) for x,y in polygon], color)
        self.face([(x,y,z0) for x,y in reversed(polygon)], color)
        for i, (x,y) in enumerate(polygon):
            nx, ny = polygon[(i+1) % len(polygon)]
            self.face([(x,y,z0), (nx,ny,z0), (nx,ny,z1), (x,y,z1)], color)

    def bounds(self):
        return {'min': [min(v[i] for v in self.vertices) for i in range(3)],
                'max': [max(v[i] for v in self.vertices) for i in range(3)]}

    def binary(self):
        bounds = self.bounds()
        # GXMS dimension order is width, depth, height, matching the existing exporters.
        dimensions = [bounds['max'][i] - bounds['min'][i] for i in (0,2,1)]
        voff = HEADER.size
        ioff = voff + len(self.vertices)*32
        assert len(self.vertices) <= 65535 and len(self.indices) <= 65535
        return (HEADER.pack(b'GXMS', 2, len(self.vertices), len(self.indices), *dimensions, voff, ioff)
                + b''.join(struct.pack('>8f', *v) for v in self.vertices)
                + struct.pack(f'>{len(self.indices)}H', *self.indices))


def authored_mesh(kind):
    """Small open architectural kit, with no ornamental fake standing surfaces."""
    m = Mesh()
    if kind == 'platform':
        m.box(-.5,.5, -1,-.12, -2.5,2.5, 1)
        m.box(-.5,.5, -.12,0, -2.5,2.5, 2)
        m.box(-.5,.5, -.65,-.30, 2.51,2.7, 4)
    elif kind == 'post':
        m.box(-1.25,1.25, 0,31, -1.2,1.2, 0)
        m.box(-2,2, 31,34, -1.4,1.4, 1)
        m.box(-.14,.14, 3,30, 1.21,1.4, 4)
        m.box(-1.35,1.35, 0,1, -1.3,1.3, 5)
    elif kind == 'beam':
        m.box(-.5,.5, -.8,.8, -1,1, 1)
        m.box(-.5,.5, -.15,.15, 1.01,1.15, 4)
    elif kind == 'portal':
        for lo, hi in ((-5,-3.5),(3.5,5)):
            m.box(lo,hi, 0,16, -.9,.9, 1)
            m.box(lo+.35,hi-.35, 1,15, .91,1.05, 4)
        m.box(-5,5, 15,17, -.9,.9, 2)
        # An original left arrow; runtime mirrors it for right-side exits.
        m.prism(((-2.5,19),(0,16.8),(0,21.2)), -.45,.65, 3)
        m.box(0,2.5, 18.4,19.6, -.45,.65, 3)
    elif kind == 'sigil':
        # Three offset rhombi and a split vertical stem: abstract inherited-chain mark.
        for x,y in ((-2,3),(2,7),(-2,11)):
            m.prism(((x-2,y),(x,y-2),(x+2,y),(x,y+2)), -.45,.45, 4)
        m.box(-.35,.35, 0,13, -.6,-.46, 3)
    elif kind == 'station':
        m.box(-6,6, 0,2, -2,2, 1)
        m.box(-4,4, 2,3, -1.5,1.5, 2)
        m.box(-1.5,1.5, 3,11, -1.2,1.2, 5)
        m.box(-1.1,1.1, 3.5,10.5, 1.21,1.35, 4)
        m.box(-5,5, 11,12, -1.4,1.4, 3)
        for x in (-4,4):
            m.box(x-.45,x+.45, 3,8, -.6,.6, 2)
    elif kind == 'fascia':
        # Beneath the native FD floor; never advertises another walkable top.
        m.box(-1,1, -4,-1.8, -1.8,1.8, 0)
        m.box(-1,1, -2.8,-2.45, 1.81,1.95, 4)
    else:
        raise ValueError(f'Unknown authored part: {kind}')
    return m


def atlas_bytes(theme):
    palette = list(BASE_PALETTE)
    palette[4] = ACCENTS[theme]
    # Native GXTX offsets 28/36 are image byte size / image offset respectively.
    header = struct.pack('>11I', 0x47585458, 1, 6, 32, 4, 0xFFFFFFFF, 0, 512, 0, 64, 0)
    # RGBA8 GX tiling: each 4x4 tile is 16 AR pairs followed by 16 GB pairs.
    tiles = b''.join(bytes((255,r))*16 + bytes((g,b))*16 for r,g,b in palette)
    return header.ljust(64, b'\0') + tiles


def build(mod):
    """Installer entry: create only this kit's files in <mod>/models; return manifest."""
    root = Path(mod) / 'models'
    root.mkdir(parents=True, exist_ok=True)
    # Generated output stays untracked even in an otherwise visible _build review folder.
    # Existing owner rules are preserved; names here are restricted to this authored kit.
    ignore = root / '.gitignore'
    if not ignore.exists():
        ignore.write_text('rogue_room_*.gxmesh\nrogue_room_*.coll.json\n'
                          'rogue_room_palette_*.gxtex\nroom-assets.json\n.gitignore\n', encoding='utf-8')
    manifest = {'version': 1, 'provenance': 'Original procedural geometry and pixels in tools/roguelite/room_assets.py',
                'format_references': ['pc/scripts/examples/runtime_models/make_models.py',
                                      'pc/assets_src/bf_interior/export_kit.py'],
                'coordinates': {'x': 'travel', 'y': 'height', 'z': 'positive towards camera'},
                'collision': 'All sidecars empty; Rooms spawns collision=false; root owns physics',
                'budgets': {'unique_models': 21, 'max_room_instances': 20}, 'models': {}, 'atlases': {}}
    for theme in THEMES:
        atlas = atlas_bytes(theme)
        atlas_name = f'rogue_room_palette_{theme}'
        (root / f'{atlas_name}.gxtex').write_bytes(atlas)
        manifest['atlases'][atlas_name] = {'width': 32, 'height': 4,
                                         'sha256': hashlib.sha256(atlas).hexdigest()}
        for kind in TYPES:
            name = f'rogue_room_{kind}_{theme}'
            mesh = authored_mesh(kind)
            data = mesh.binary()
            (root / f'{name}.gxmesh').write_bytes(data)
            (root / f'{name}.coll.json').write_text(json.dumps(
                {'version': 1, 'atlas': atlas_name, 'lines': []}, separators=(',', ':')) + '\n', encoding='utf-8')
            manifest['models'][name] = {'type': kind, 'theme': theme, 'bounds': mesh.bounds(),
                                        'vertices': len(mesh.vertices), 'triangles': len(mesh.indices)//3,
                                        'sha256': hashlib.sha256(data).hexdigest()}
    (root / 'room-assets.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mod-dir', type=Path, default=ROOT / '_build/roguelite-room-assets')
    args = parser.parse_args()
    result = build(args.mod_dir)
    print(f'Wrote {len(result["models"])} original room models and {len(result["atlases"])} atlases to {args.mod_dir / "models"}')
