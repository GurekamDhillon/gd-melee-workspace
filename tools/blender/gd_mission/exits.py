"""Maze v1 exit markers: one standard slot per side, in local game units."""
import math


def attach_exits(doc, markers):
    chunks = {c['id']: c for c in doc['chunks']}
    for marker in markers:
        def error(text):
            doc['errors'].append(marker['name'] + ': ' + text)
        chunk = chunks.get(marker['chunk'])
        if chunk is None:
            error('gd_exit_chunk must name an existing gd_chunk'); continue
        side, slot, traversal = marker['side'], marker['slot'], marker['traversal']
        if side not in ('left', 'right', 'up', 'down'):
            error('gd_exit must be left/right/up/down'); continue
        if isinstance(slot, bool) or slot != 1:
            error('gd_exit_slot must be 1 for maze contract v1'); continue
        allowed = ('walk',) if side in ('left', 'right') else ('climb', 'drop') if side == 'up' else ('drop',)
        if traversal not in allowed:
            error('invalid gd_exit_traversal for side'); continue
        w, h = chunk['right']-chunk['left'], chunk['top']-chunk['bottom']
        if abs(w-130) > .001 or abs(h-104) > .001:
            error('maze v1 chunks must be 130x104'); continue
        points = {'left': (0, 16), 'right': (130, 16), 'up': (65, 104), 'down': (65, 0)}
        x, y = points[side]
        values = (marker['x'], marker['y'])
        if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in values) or abs(marker['x']-chunk['left']-x) > .001 or abs(marker['y']-chunk['bottom']-y) > .001:
            error('exit marker must be at standard slot centre'); continue
        exits = chunk.setdefault('exits', [])
        if any(e['side'] == side and e['slot'] == slot for e in exits):
            error('duplicate exit side/slot'); continue
        exits.append(dict(side=side, slot=slot, traversal=traversal))
        chunk['size'] = dict(w=130, h=104)
    for chunk in doc['chunks']:
        if 'exits' in chunk:
            chunk['exits'].sort(key=lambda e: (e['side'], e['slot']))
