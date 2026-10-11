"""Blender script: bake the default model-part visibility into an existing falcon.blend (no rebuild).

    blender -b falcon.blend --python apply_blend_parts.py -- parts.json [out.blend]

parts.json comes from `HsdExport --parts`. Saves over the open file unless out.blend is given.
"""
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import part_visibility  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
doc = part_visibility.load(args[0])
names = part_visibility.hidden_names(doc)
found, missing = part_visibility.apply_to_objects([o for o in bpy.data.objects if o.type == "MESH"], names)
_alpha = part_visibility.apply_alpha([o for o in bpy.data.objects if o.type == "MESH"], part_visibility.alpha_by_name(doc))
print("FALCON_ALPHA", _alpha)
_cull = part_visibility.apply_cull([o for o in bpy.data.objects if o.type == "MESH"], part_visibility.cull_names(doc))
print("FALCON_CULL", len(_cull))
print("FALCON_PARTS hidden=%d missing=%s" % (len(found), missing))
assert not missing, "parts.json names meshes this blend lacks: %s" % missing
bpy.ops.wm.save_as_mainfile(filepath=args[1] if len(args) > 1 else bpy.data.filepath)
