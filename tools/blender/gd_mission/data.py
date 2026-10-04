"""Deterministic Lua data encoding and Blender-to-game coordinates."""
import hashlib
import math
from .constants import UNITS


def coordinates(xyz):
    x, y, z = xyz
    return tuple(round(v, 4) + 0.0 for v in (x * UNITS, z * UNITS, -y * UNITS))


def model_name(content):
    return 'mesh_' + hashlib.sha256(content).hexdigest()[:43]


def lua(value):
    if value is None:
        return 'nil'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            raise ValueError('Lua data cannot contain non-finite numbers')
        return format(round(value, 4) + 0.0, '.4f').rstrip('0').rstrip('.') or '0'
    if isinstance(value, str):
        # Lua decimal escapes have three digits so the following byte is unambiguous.
        return '"' + ''.join('\\%03d' % ord(c) if ord(c) < 32 or c in '\\"'
                             else c for c in value) + '"'
    if isinstance(value, dict):
        return '{' + ','.join('[' + lua(k) + ']=' + lua(value[k])
                              for k in sorted(value, key=lambda k: (type(k).__name__, str(k)))
                              if not str(k).startswith('_')) + '}'
    if isinstance(value, (list, tuple)):
        return '{' + ','.join(lua(v) for v in value) + '}'
    raise ValueError('Unsupported Lua data type: ' + type(value).__name__)


def assign_chunk(x, y, chunks):
    """Half-open rectangles assign seam origins to exactly one chunk."""
    for chunk in sorted(chunks, key=lambda c: c['id']):
        if chunk['left'] <= x < chunk['right'] and chunk['bottom'] <= y < chunk['top']:
            return chunk['id']
    return None
