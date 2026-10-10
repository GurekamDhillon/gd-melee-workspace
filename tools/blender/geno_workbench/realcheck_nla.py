"""Real-data NLA check (needs local, git-ignored XV2 IR + cross-port clip.npz; writes nothing under git).

    GW_SITE=<dir with scipy+PIL for Blender's Python> blender --background --factory-startup --python-exit-code 1 \
      <goku.blend> --python tools/blender/geno_workbench/realcheck_nla.py -- --project ports/goku-xv2 --out <dir>
Prints GENO_WB_CHECK lines; any failure exits non-zero.
"""
import json
import os
from pathlib import Path
import sys

import bpy

for extra in filter(None, os.environ.get('GW_SITE', '').split(os.pathsep)):
    sys.path.insert(0, extra)  # scipy + Pillow for Blender's Python, installed with pip --target

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from geno_workbench import nla  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
project = Path(argv[argv.index("--project") + 1]).resolve()
out = Path(argv[argv.index("--out") + 1]).resolve()
out.mkdir(parents=True, exist_ok=True)

arm = bpy.data.objects["GokuExport"]
bpy.context.view_layer.objects.active = arm
for o in bpy.data.objects:
    o.select_set(o == arm)

for ref in ("GOK_ATC_024", "melee:luigi/AttackAirB"):
    a = nla.import_clip(arm, project, ref)
    print("GENO_WB_CHECK import %s -> action %s frames %s" % (ref, a.name, a.frame_range[:]))

doc = json.loads((project / "splices.json").read_text(encoding="utf-8-sig"))
for name in ("dair_thrust_hold", "bair_crossport_keep"):
    recipe = doc["recipes"][name]
    track = nla.lay_out_recipe(arm, name, recipe, project=project)
    back = nla.read_recipe(arm, track)
    expect = {k: recipe[k] for k in ("segments",) if k in recipe}
    print("GENO_WB_CHECK layout %s strips=%d" % (name, len(track.strips)))
    print("GENO_WB_CHECK readback %s segments_equal=%s" % (name, back["segments"] == recipe["segments"]))
    assert back["segments"] == recipe["segments"], (back, recipe)
    glb = out / (name + ".glb")
    action = nla.bake_and_export(arm, glb, track, name="wbnla_" + name)
    print("GENO_WB_CHECK bake_export %s action=%s glb=%s bytes=%d" % (name, action.name, glb.name, glb.stat().st_size))
    assert glb.stat().st_size > 0
print("GENO_WB_CHECK nla_real OK")
