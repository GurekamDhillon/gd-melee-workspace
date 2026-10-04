"""Explicit solid variants of otherwise one-way kit floor meshes."""
import json
from .constants import UNITS
from .data import model_name

SOLID_SPANS = {
    'bf_floor_4m': [(-2, 2)], 'bf_floor_2m': [(-1, 1)],
    'bf_balcony_4m': [(-2, 2)], 'bf_floor_opening_4m': [(-2, -1), (1, 2)],
}


def solid_floor_variant(part, binary, sidecar):
    if part not in SOLID_SPANS:
        raise ValueError('gd_solid is supported only on floor_4m, floor_2m, balcony_4m and floor_opening_4m kit parts')
    metadata = json.loads(sidecar)
    lines = [list(line) for line in metadata['lines'] if line[0] != 'ceiling']
    for line in lines:
        if line[0] == 'floor': line[5] &= ~1
    lines += [['ceiling', b*UNITS, -.4*UNITS, a*UNITS, -.4*UNITS, 0] for a, b in SOLID_SPANS[part]]
    metadata['lines'] = lines
    payload = (json.dumps(metadata, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')
    name = model_name(binary + payload)
    return name, {name+'.gxmesh': binary, name+'.coll.json': payload}, len(lines)
