"""Custom mesh GXMS v2 export (geometry/UVs, neutral atlas, explicit collision)."""
import json
import struct
from .constants import UNITS
from . import constants as C
from .data import coordinates, model_name

HEADER = struct.Struct('>4sIIIfffII')


def neutral_texture():
    header = struct.pack('>4sIIIIIIIIII', b'GXTX', 1, 6, 4, 4,
                         0xffffffff, 0, 64, 0, 64, 128)
    return header + bytes(64-len(header)) + b'\xff'*64


def export_mesh(ob, depsgraph):
    evaluated = ob.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles()
        vertices, indices, ids = [], [], {}
        uv = mesh.uv_layers.active
        for triangle in mesh.loop_triangles:
            for loop in triangle.loops:
                co = mesh.vertices[mesh.loops[loop].vertex_index].co
                normal = mesh.corner_normals[loop].vector
                tex = uv.data[loop].uv if uv else (.5, .5)
                # Mesh remains in the object's local frame; transform is in layout.
                point = coordinates(co)
                vertex = (*point, float(tex[0]), 1-float(tex[1]), normal.x, normal.z, -normal.y)
                packed = struct.pack('>8f', *vertex)
                if packed not in ids:
                    ids[packed] = len(vertices); vertices.append(packed)
                indices.append(ids[packed])
        if not vertices: raise ValueError(ob.name + ': mesh has no triangles')
        if len(vertices) > C.MAX_VERTICES or len(indices) > C.MAX_INDICES:
            raise ValueError(f'{ob.name}: mesh exceeds {C.MAX_VERTICES} vertices or {C.MAX_INDICES} indices')
        points = [struct.unpack('>8f', v)[:3] for v in vertices]
        extents = [max(p[a] for p in points)-min(p[a] for p in points) for a in range(3)]
        binary = HEADER.pack(b'GXMS', 2, len(vertices), len(indices),
                             *[max(.05 * UNITS, e) for e in extents], HEADER.size, HEADER.size + len(vertices)*32)
        binary += b''.join(vertices) + struct.pack('>%dH' % len(indices), *indices)
        raw_lines = ob.get('gd_collision_lines', '[]')
        lines = json.loads(raw_lines)
        if not isinstance(lines, list): raise ValueError(ob.name + ': gd_collision_lines must be a JSON list')
        converted = []
        for line in lines:
            if len(line) != 6 or line[0] not in ('floor', 'left_wall', 'right_wall', 'ceiling'):
                raise ValueError(ob.name + ': invalid collision line')
            converted.append([line[0], *(round(float(v)*UNITS, 4) for v in line[1:5]), int(line[5])])
        sidecar = json.dumps(dict(version=1, atlas='gd_neutral', lines=converted), separators=(',', ':')).encode()
        name = model_name(binary + sidecar)
        # GXTX v1 RGBA8 tiled 4x4: opaque white, shared by custom meshes.
        texture = neutral_texture()
        return name, {name+'.gxmesh': binary, name+'.coll.json': sidecar,
                      'gd_neutral.gxtex': texture}, len(vertices), len(indices), len(converted)
    finally:
        evaluated.to_mesh_clear()
