"""Instance labels and optional camera custom properties."""
import re

CAMERA_KEYS = ('mode', 'window_w', 'window_h', 'min_dist', 'fov')


def instance_name(source, used):
    base = re.sub(r'[^A-Za-z0-9_-]', '_', str(source))[:48] or 'Part'
    candidate = base
    suffix = 1
    while candidate in used:
        tail = '_' + str(suffix)
        candidate = base[:48-len(tail)] + tail
        suffix += 1
    used.add(candidate)
    return candidate


def camera_properties(owner):
    if not any('gd_camera_' + k in owner for k in CAMERA_KEYS): return None
    result = {}
    for key in ('mode', 'min_dist', 'fov'):
        if 'gd_camera_' + key in owner: result[key] = owner['gd_camera_' + key]
    if any('gd_camera_window_' + k in owner for k in ('w', 'h')):
        result['window'] = {k: owner['gd_camera_window_' + k] for k in ('w', 'h')
                            if 'gd_camera_window_' + k in owner}
    return result
