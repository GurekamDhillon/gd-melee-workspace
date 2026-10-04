"""Recheck exit metadata for pure API callers as well as Blender collection."""
import math


def validate_exits(chunk):
    if 'exits' not in chunk:
        return []
    errors = []
    exits = chunk['exits']
    if not isinstance(exits, list):
        return ['exits must be a list']
    if chunk.get('size') != dict(w=130, h=104) or any(
            not isinstance(chunk.get(k), (int, float)) or not math.isfinite(chunk[k])
            for k in ('left', 'right', 'bottom', 'top')) or round(chunk['right'], 4)-round(chunk['left'], 4) != 130 or round(chunk['top'], 4)-round(chunk['bottom'], 4) != 104:
        errors.append('exit chunk size must be 130x104')
    seen = set()
    for e in exits:
        if not isinstance(e, dict):
            errors.append('exit must be a table'); continue
        side, slot = e.get('side'), e.get('slot')
        if side not in ('left', 'right', 'up', 'down') or isinstance(slot, bool) or slot != 1:
            errors.append('invalid exit side/slot'); continue
        if side in seen:
            errors.append('duplicate exit side/slot')
        seen.add(side)
        allowed = ('walk',) if side in ('left', 'right') else ('climb', 'drop') if side == 'up' else ('drop',)
        if e.get('traversal') not in allowed:
            errors.append('invalid exit traversal')
    return errors
