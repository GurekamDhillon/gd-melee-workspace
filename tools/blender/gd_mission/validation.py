"""Validation without bpy or filesystem mutation; diagnostics retain object names."""
import math
import re
from collections import Counter
from . import constants as C
from .data import assign_chunk
from .assets import estimate_asset_memory
from .exit_validation import validate_exits


def safe_name(name):
    return isinstance(name, str) and len(name) <= C.MAX_NAME and re.fullmatch(r'[A-Za-z0-9_-]+', name) is not None


def validate(doc):
    errors = list(doc.get('errors', []))
    parts = doc['level']['parts']
    chunks = doc.get('chunks', [])
    def error(name, text): errors.append(f'{name}: {text}')
    def number(v): return isinstance(v, (float, int)) and not isinstance(v, bool) and math.isfinite(v)
    def integer(v, lo, hi): return number(v) and v == int(v) and lo <= v <= hi
    def rect(r):
        return all(number(r.get(k)) for k in ('left', 'right', 'top', 'bottom')) and r['left'] < r['right'] and r['bottom'] < r['top']
    def camera(value, name):
        if not isinstance(value, dict): error(name, 'camera must be a table'); return
        if 'mode' in value and value['mode'] not in ('follow', 'chunk', 'shaft'):
            error(name, 'camera mode must be follow, chunk or shaft')
        for key, maximum in (('min_dist', 49000), ('fov', 89)):
            if key in value and (not number(value[key]) or not 1 <= round(value[key], 4) <= maximum):
                error(name, f'camera {key} must be 1..{maximum}')
        if 'window' in value:
            w = value['window']
            if not isinstance(w, dict) or any(not number(w.get(k)) or not 1 <= round(w[k], 4) <= 49000 for k in ('w', 'h')):
                error(name, 'camera window needs w and h in 1..49000 game units')
    if not chunks and len(parts) > C.MAX_PARTS:
        error(parts[C.MAX_PARTS].get('_name', 'Level'), f'{len(parts)} parts exceeds {C.MAX_PARTS}')
    ids = set()
    if len(chunks) > C.MAX_CHUNKS: error('Chunks', f'{len(chunks)} chunks exceeds {C.MAX_CHUNKS}')
    first = None
    for chunk in chunks:
        name = chunk.get('_name', chunk['id'])
        for diagnostic in validate_exits(chunk): error(name, diagnostic)
        if not safe_name(chunk['id']) or chunk['id'] in ids: error(name, 'invalid or duplicate chunk id')
        ids.add(chunk['id'])
        if 'camera' in chunk: camera(chunk['camera'], name)
        if not rect(chunk): error(name, 'invalid chunk rectangle')
        else:
            # Compare the four-place values that the Lua loader will actually see.
            r = {k: round(chunk[k], 4) for k in ('left', 'right', 'bottom', 'top')}
            if not rect(r): error(name, 'chunk rectangle collapses at four-place rounding')
            elif first is None: first = r
            else:
                w, h = first['right']-first['left'], first['top']-first['bottom']
                if abs(r['right']-r['left']-w) > 1e-6 or abs(r['top']-r['bottom']-h) > 1e-6:
                    error(name, 'chunks must have equal rectangle sizes for the runtime 3x3 grid')
                for key, size in (('left', w), ('bottom', h)):
                    cell = (r[key]-first[key])/size
                    if abs(cell-round(cell)) >= 1e-6:
                        error(name, 'chunks must align to the runtime grid')
    for i, a in enumerate(chunks):
        for b in chunks[i + 1:]:
            if rect(a) and rect(b) and max(a['left'], b['left']) < min(a['right'], b['right']) and max(a['bottom'], b['bottom']) < min(a['top'], b['top']):
                error(a['id'] + ' / ' + b['id'], 'overlapping chunk rectangles')
    counts = Counter()
    names = set()
    for p in parts:
        name = p.get('_name', p['part'])
        label = p.get('name')
        if not safe_name(label): error(name, 'instance name must contain 1..48 letters, numbers, underscores or hyphens')
        elif label in names: error(name, 'duplicate instance name ' + label)
        else: names.add(label)
        if not safe_name(p['part']): error(name, f'part name must contain 1..{C.MAX_NAME} letters, numbers, underscores or hyphens')
        for key in ('scale', 'scale_x', 'scale_y', 'scale_z'):
            value = p.get(key, 1)
            if not number(value) or not .001 <= abs(value) <= 100: error(name, 'invalid ' + key + ' (magnitude .001..100)')
        if not all(number(p.get(k)) and abs(p[k]) < C.WORLD_LIMIT for k in ('x', 'y', 'z')):
            error(name, 'invalid or out-of-world position')
        if chunks:
            chunk = assign_chunk(p['x'], p['y'], chunks)
            if chunk is None: error(name, 'origin is outside every chunk')
            else: counts[chunk] += 1
    for chunk, count in counts.items():
        if count > C.MAX_PARTS: error(chunk, f'{count} parts exceeds {C.MAX_PARTS} per chunk')
    for ob in doc.get('objects', []):
        name = ob['name']
        if ob['lines'] > C.MAX_LINES: error(name, f'{ob["lines"]} collision lines exceeds {C.MAX_LINES}')
        if ob['indices'] > C.MAX_INDICES: error(name, f'{ob["indices"]} indices exceeds {C.MAX_INDICES}')
        if ob.get('vertices', 0) > C.MAX_VERTICES: error(name, f'vertices exceeds {C.MAX_VERTICES}')
        if ob['lines'] and ob.get('collision', True) and ob.get('mirrored'): error(name, 'mirrored part owns collision')
    for kind in ('camera', 'blast'):
        if kind in doc['level']:
            value = doc['level'][kind]
            if kind == 'camera': camera(value, 'Level')
            if kind == 'blast' or (isinstance(value, dict) and any(k in value for k in ('left', 'right', 'top', 'bottom'))):
                if not isinstance(value, dict) or not rect(value): error(kind, 'invalid bounds rectangle')
    bounds = doc.get('bounds')
    if bounds and not rect(bounds): error('Level bounds', 'invalid rectangle')
    for marker in doc.get('markers', []):
        x, y = marker['x'], marker['y']
        if not number(x) or not number(y): error(marker['name'], 'non-finite marker position')
        elif bounds and rect(bounds):
            w, h = marker.get('w', 0) / 2, marker.get('h', 0) / 2
            if x-w < bounds['left'] or x+w > bounds['right'] or y-h < bounds['bottom'] or y+h > bounds['top']:
                error(marker['name'], 'marker outside level bounds')
    mission = doc['mission']
    name = 'Mission'
    if not mission.get('start'): error(name, 'start is required')
    objective = mission.get('objective', {})
    kind = objective.get('type')
    if kind not in ('reach_goal', 'defeat_all', 'defeat_then_goal'): error(name, 'objective is required and must be reach_goal, defeat_all or defeat_then_goal')
    if kind in ('reach_goal', 'defeat_then_goal') and not mission.get('goal'): error(name, 'objective needs a goal')
    enemies = mission.get('enemies', [])
    if kind in ('defeat_all', 'defeat_then_goal') and not enemies: error(name, 'objective needs an enemy')
    for key, maximum in (('time', 3600), ('lives', 99)):
        if key in objective and (not number(objective[key]) or not 1 <= objective[key] <= maximum or (key == 'lives' and objective[key] != int(objective[key]))):
            error(name, f'{key} must be 1..{maximum}')
    if len(enemies) > C.MAX_ENEMIES: error(name, f'more than {C.MAX_ENEMIES} enemies')
    waves = Counter()
    for enemy in enemies:
        name = enemy.get('_name', 'Enemy ' + str(enemy.get('kind')))
        if enemy.get('kind') not in C.ENEMY_KINDS: error(name, 'unknown enemy kind')
        wave = enemy.get('wave', 1)
        if not integer(wave, 1, C.MAX_WAVES): error(name, f'wave must be 1..{C.MAX_WAVES}')
        else: waves[wave] += 1
    for wave, count in waves.items():
        if count > C.MAX_WAVE_ENEMIES: error('Mission', f'wave {wave} exceeds {C.MAX_WAVE_ENEMIES} enemies')
    rules = set()
    for rule in mission.get('waves', []):
        name = rule.get('_name', 'Wave rule')
        wave = rule.get('wave')
        if wave not in waves: error(name, f'wave {wave} has no enemies')
        if wave in rules: error(name, 'duplicate wave rule')
        rules.add(wave)
        if ('time' in rule) == ('x' in rule): error(name, 'wave rule needs time XOR x')
        if 'time' in rule and (not number(rule['time']) or not 0 <= rule['time'] <= 3600): error(name, 'invalid wave time')
        if 'x' in rule and (not number(rule['x']) or rule.get('dir', 1) not in (-1, 1)): error(name, 'invalid wave position/direction')
    for collection, limit in (('checkpoints', C.MAX_CHECKPOINTS), ('triggers', C.MAX_TRIGGERS)):
        if len(mission.get(collection, [])) > limit: error('Mission', f'{collection} exceeds {limit}')
    zones = mission.get('checkpoints', []) + mission.get('triggers', []) + ([mission['goal']] if mission.get('goal') else [])
    for zone in zones:
        name = zone.get('_name', 'Zone')
        if any(not number(zone.get(k)) or not 0 < zone[k] <= C.MAX_ZONE for k in ('w', 'h')): error(name, f'zone size must be positive and <= {C.MAX_ZONE}')
    for trigger in mission.get('triggers', []):
        name = trigger.get('_name', 'Trigger')
        action = trigger.get('action')
        if action not in ('wave', 'message', 'collision', 'complete', 'fail'): error(name, 'unknown trigger action')
        if action == 'wave' and trigger.get('wave') not in waves: error(name, f'wave {trigger.get("wave")} has no enemies')
        if action == 'message':
            text = trigger.get('text')
            if not isinstance(text, str) or not 1 <= len(text.encode('utf-8')) <= 80 or any(ord(c) < 32 or ord(c) == 127 for c in text):
                error(name, 'message needs 1..80 printable UTF-8 bytes')
        if action == 'collision':
            at = trigger.get('at', {})
            if not all(number(at.get(k)) for k in ('x', 'y')) or not isinstance(trigger.get('open'), bool) or not number(trigger.get('r', 6.5)) or not 0 < trigger.get('r', 6.5) <= 200:
                error(name, 'collision trigger needs at, open and radius in (0,200]')
    pinned = estimate_asset_memory(doc)
    if pinned > C.ASSET_MEMORY_BUDGET:
        error('Mission assets', f'estimated {pinned} pinned bytes exceeds {C.ASSET_MEMORY_BUDGET}-byte budget')
    return errors
