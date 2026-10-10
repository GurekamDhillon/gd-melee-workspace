"""Pure camera, costume, image and GXTX presentation contracts (geno.md §22.12)."""
from dataclasses import dataclass
from pathlib import Path
import re
import struct


@dataclass(frozen=True)
class OutputSpec:
    size: tuple[int, int]
    format: str
    palette: bool = False


OUTPUTS = {
    'icon': OutputSpec((64, 56), 'rgb5a3'),
    'portrait': OutputSpec((136, 188), 'rgb5a3'),
    'stock': OutputSpec((24, 24), 'rgba8'),
    'results': OutputSpec((52, 74), 'rgb5a3'),
    'emblem': OutputSpec((80, 64), 'rgba8'),
}
COSTUME_FIELDS = ('portrait', 'stock', 'results')


def camera_outputs(names, overrides=None):
    """Select package views; render all cameras independently of this mapping.

    Verified against the Captain Falcon template (Blender 3.5.1): CSP_SD, STC_SD and
    'CSS Icon_SD' are the real names; other aliases are guesses; explicit ui_render.fields takes priority and ambiguity fails.
    """
    names = list(names)
    overrides = overrides or {}
    if set(overrides) - {'icon', *COSTUME_FIELDS}:
        raise ValueError('Camera fields must be icon, portrait, stock or results')

    def choose(aliases):
        for alias in aliases:
            matches = [n for n in names if re.sub(r'[^a-z0-9]', '', n.lower()) == alias]
            if len(matches) > 1:
                raise ValueError('Ambiguous camera alias ' + alias + ': ' + ', '.join(matches))
            if matches:
                return matches[0]
        raise ValueError('Missing camera (' + ', '.join(aliases) + '); set ui_render.fields. Found: ' + ', '.join(names))

    aliases = {
        'portrait': ('cspsd',), 'results': ('resultssd', 'cspsd'),
        'stock': ('stcsd', 'stocksd', 'stockiconsd', 'stock'),
        'icon': ('cssiconsd', 'csssd', 'iconsd', 'stockhd', 'stockiconhd', 'stocksd', 'stockiconsd', 'stock'),
    }
    result = {}
    for field, options in aliases.items():
        name = overrides[field] if field in overrides else choose(options)
        if name not in names:
            raise ValueError('Unknown ' + field + ' camera: ' + str(name))
        result[field] = name
    return result


def enumerate_costumes(entry, source=None, source_dir=None, overrides=None):
    """Package order is authoritative; source art is paired by that order."""
    declared = entry.get('fighter', {}).get('costumes', [{}])
    if not isinstance(declared, list) or not 1 <= len(declared) <= 255:
        raise ValueError('Package must declare 1..255 costumes')
    source = source or {}
    inputs = source.get('costumes') or []
    if inputs and len(inputs) != len(declared):
        raise ValueError('Source and package costume counts differ')
    base = Path(source_dir or '.').resolve()
    overrides = overrides or {}
    if not isinstance(overrides, dict) or any(str(k) not in {str(i) for i in range(len(declared))} for k in overrides):
        raise ValueError('ui_render.costumes must map valid zero-based indices to inputs')
    result = []
    for i, costume in enumerate(declared):
        value = {'index': i, 'name': costume.get('name', 'Costume ' + str(i))}
        if inputs:
            value.update({k: inputs[i][k] for k in ('texture', 'art', 'material_colors', 'objects', 'collections') if k in inputs[i]})
        extra = overrides.get(str(i), overrides.get(i, {}))
        if not isinstance(extra, dict):
            raise ValueError('Each ui_render.costumes entry must be an object')
        value.update(extra)
        # Indices and labels cannot be changed by art overrides.
        value['index'], value['name'] = i, costume.get('name', 'Costume ' + str(i))
        for field in ('texture', 'art'):
            if value.get(field):
                value[field] = str((base / value[field]).resolve())
        result.append(value)
    return result


def select_costumes(costumes, selection='all'):
    if selection == 'all':
        return list(costumes)
    if not re.fullmatch(r'0|[1-9][0-9]*', str(selection)):
        raise ValueError('Costume must be a zero-based integer or all')
    index = int(selection)
    if index >= len(costumes):
        raise ValueError('Costume index out of range: ' + str(index))
    return [costumes[index]]


def fit_rgba(image, size):
    """Fit the camera crop without distortion, preserving alpha and padding."""
    from PIL import Image
    rgba = image.convert('RGBA')
    factor = min(size[0] / rgba.width, size[1] / rgba.height)
    scaled = (max(1, round(rgba.width * factor)), max(1, round(rgba.height * factor)))
    # Premultiplied interpolation avoids dark fringes on partially opaque edges.
    rgba = rgba.convert('RGBa').resize(scaled, Image.Resampling.LANCZOS).convert('RGBA')
    output = Image.new('RGBA', size)
    output.alpha_composite(rgba, ((size[0] - scaled[0]) // 2, (size[1] - scaled[1]) // 2))
    return output


def postprocess(image, outline=0, shadow=None, shadow_alpha=100):
    """Authored equivalents of stock outline and CSP shadow; no add-on operator guess."""
    from PIL import Image, ImageFilter, ImageChops
    rgba = image.convert('RGBA')
    alpha = rgba.getchannel('A')
    if not isinstance(outline, int) or not 0 <= outline <= 32:
        raise ValueError('outline must be an integer from 0 to 32')
    output = Image.new('RGBA', rgba.size)
    if shadow is not None:
        if len(shadow) != 2 or any(not isinstance(v, int) for v in shadow) or not 0 <= shadow_alpha <= 255:
            raise ValueError('shadow needs two integer offsets and alpha 0..255')
        layer = Image.new('RGBA', rgba.size)
        layer.putalpha(alpha.point(lambda a: (a * shadow_alpha + 127) // 255))
        # alpha_composite clips at edges, without wrapping like ImageChops.offset.
        output.alpha_composite(layer, tuple(shadow))
    if outline:
        layer = Image.new('RGBA', rgba.size)
        expanded = alpha.filter(ImageFilter.MaxFilter(2 * outline + 1))
        layer.putalpha(ImageChops.subtract(expanded, alpha))
        output.alpha_composite(layer)
    output.alpha_composite(rgba)
    return output


def merge_presentation(existing, generated, count):
    """Merge subset results with a complete index-preserving costume list."""
    if not 1 <= count <= 255 or any(i < 0 or i >= count for i in generated):
        raise ValueError('Invalid presentation costume count/index')
    result = dict(existing)
    if generated.get(0, {}).get('icon'):
        result['icon'] = generated[0]['icon']
    for field in COSTUME_FIELDS:
        if not any(field in values for values in generated.values()):
            continue
        previous = existing.get(field)
        # A missing results field needs its own converted zero fallback.
        # Portrait containers may have palettes, which results cannot use.
        previous = [previous] if isinstance(previous, str) else list(previous or [])
        zero = generated.get(0, {}).get(field) or (previous[0] if previous else None)
        if not zero:
            raise ValueError('Render costume zero first: no fallback for ' + field)
        values = [previous[i] if i < len(previous) else zero for i in range(count)]
        for i, fields in generated.items():
            if field in fields:
                values[i] = fields[field]
        result[field] = values
    for field, values in result.items():
        for name in values if isinstance(values, list) else [values]:
            if not isinstance(name, str) or not re.fullmatch(r'[!-~]+\.[gG][xX][tT][eE][xX]', name) or len(name) > 63 or '..' in name or any(c in name for c in '/\\:'):
                raise ValueError('Invalid presentation basename: ' + repr(name))
    return result


def validate_gxtex(path, spec):
    data = Path(path).read_bytes()
    if len(data) < 64:
        raise ValueError('Truncated GXTX: ' + str(path))
    magic, version, fmt, w, h, tlutfmt, entries, length, tlutlen, offset, _ = struct.unpack('>4s10I', data[:44])
    expected_format = {'rgb5a3': 5, 'rgba8': 6}[spec.format]
    expected_length = ((w + 3) // 4) * ((h + 3) // 4) * (32 if fmt == 5 else 64)
    if (magic != b'GXTX' or version != 1 or (w, h) != spec.size or fmt != expected_format
            or entries or tlutlen or tlutfmt != 0xFFFFFFFF or offset != 64
            or length != expected_length or len(data) != offset + length):
        raise ValueError('GXTX does not satisfy the non-paletted presentation contract: ' + str(path))
