"""Background-Blender check for the hitbox visualization.

    blender -b --factory-startup --python tools/blender/geno_workbench/selftest_hitviz.py

The draw handlers register once (twice is a no-op) and are gone after unregister; the overlay update
builds the draw list (label, badges, arrow, fan, meteor colour, sweep) and the sweep mesh object, then
clears; the toggles hide the pieces. Pixels are not checked (no GPU in background): see the screenshot.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import geno_workbench
from geno_workbench import hitviz, overlays


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        raise SystemExit(1)


def info(frame, x):
    return {"schema": 2, "row": "fair", "frame": frame, "facing": 1, "bones": [], "root": {"pos": {"x": 0, "y": 0, "z": 0}, "facing": 1},
            "hitboxes": [{"slot": 0, "active": True, "world": {"x": x, "y": 6.0, "z": 0.0}, "radius": 3.0},
                         {"slot": 1, "active": True, "world": {"x": x + 4, "y": 6.0, "z": 0.0}, "radius": 2.0}],
            "hurtboxes": [], "ecb": {}, "floorY": 0.0}


geno_workbench.register()
check(hitviz.registered() and len(hitviz._STATE["handles"]) == 2, "register adds the POST_VIEW and POST_PIXEL handlers")
hitviz.register()
check(len(hitviz._STATE["handles"]) == 2, "a second register adds no handler")

source = [
    {"ordinal": 0, "slot": 0, "joint": "LEG_R", "damage": 14, "angle": 270, "kbg": 100, "bkb": 30, "fkb": 0, "element": 0, "start_frame": 14, "end_frame": 16},
    {"ordinal": 1, "slot": 1, "joint": "LEG_R", "damage": 10, "angle": 361, "kbg": 100, "bkb": 20, "fkb": 0, "element": 2, "start_frame": 14, "end_frame": 16},
]
from geno_workbench import api
session = api.session()
session.hitboxes = source
session.loaded_row = "fair"
session.cache.row = "fair"
session.cache.frames = {14: info(14, 1.0)}

scene = bpy.context.scene
props = scene.geno_wb
overlays.update(info(15, 3.0), scene, props)
items = hitviz.items()
check(len(items) == 2, "two items for two active hitboxes")
check(items[0]["label"] == "0 \u00b7 14%" and items[0]["meteor"], "slot 0: label and meteor (270)")
check(items[1]["badges"] == ["electric"] and items[1]["fan"], "slot 1: electric badge and the Sakurai fan")
check(all(i["sweep"] is not None for i in items), "both sweep from the cached previous frame")
sweeps = [o for o in bpy.data.collections[overlays.COLLECTION].objects if o.name.startswith(hitviz.SWEEP_PREFIX)]
check(len(sweeps) == 2 and all(not o.hide_viewport for o in sweeps), "sweep capsules are visible mesh objects in the overlay collection")
overlays.update(info(15, 3.0), scene, props)
check(len([o for o in bpy.data.objects if o.name.startswith(hitviz.SWEEP_PREFIX)]) == 2, "a repeated update reuses the sweep objects")

props.hv_sweep = False
overlays.update(info(15, 3.0), scene, props)
check(all(o.hide_viewport for o in sweeps), "sweep toggle off hides the capsules")
props.hv_sweep = True
session.cache.frames = {}
overlays.update(info(15, 3.0), scene, props)
check(all(i["sweep"] is None for i in hitviz.items()), "no cached previous frame -> no sweep")

overlays.update({"schema": 2, "hitboxes": [], "hurtboxes": []}, scene, props)
check(hitviz.items() == [], "an empty frame clears the list")

overlays.clear(scene)
check(not [o for o in bpy.data.objects if o.name.startswith("GenoWB.")], "overlays.clear removes the sweep objects too")
geno_workbench.unregister()
check(not hitviz.registered() and hitviz._STATE["handles"] == [], "unregister removes both handlers")
check(not hasattr(bpy.types.Scene, "geno_wb"), "scene property removed")
print("GENO_HITVIZ_OK")
