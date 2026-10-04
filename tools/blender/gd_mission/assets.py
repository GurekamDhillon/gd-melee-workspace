"""Resolve the mission's shared asset pool and estimate native pinned memory."""
import json
import struct
from . import constants as C


def used_assets(doc):
    dependencies = set()
    for part in {p['part'] for p in doc['level']['parts']}:
        dependencies.update((part + '.gxmesh', part + '.coll.json'))
        sidecar = doc['models'].get(part + '.coll.json')
        if sidecar:
            atlas = json.loads(sidecar).get('atlas')
            if atlas:
                dependencies.update((atlas + '.gxtex', atlas + '.glow.gxtex'))
    return {name: doc['models'][name] for name in sorted(dependencies) if name in doc['models']}


def estimate_asset_memory(doc):
    """All chunks loaded: each canonical mesh once, each colour/glow image once.

    The native loader pins the complete mesh blob but only GXTX image bytes.
    This is the current generation; prior scene pins/other mods are not observable.
    """
    size = 0
    for name, content in used_assets(doc).items():
        if name.endswith('.gxmesh'):
            size += len(content)
        elif name.endswith('.gxtex'):
            size += struct.unpack_from('>I', content, 28)[0] if len(content) >= 64 and content[:4] == b'GXTX' else len(content)
    return size


def asset_warnings(doc):
    size = estimate_asset_memory(doc)
    if size >= C.ASSET_MEMORY_BUDGET * C.ASSET_MEMORY_WARNING:
        return [f'Mission assets: estimated {size} pinned bytes ({size/1048576:.2f} MiB) '
                f'near/exceed the {C.ASSET_MEMORY_BUDGET}-byte ({C.ASSET_MEMORY_BUDGET/1048576:g} MiB) budget; '
                'prior scene generations and other mods add to this estimate']
    return []
