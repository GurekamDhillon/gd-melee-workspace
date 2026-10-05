"""Static renders from a stage blend: turnaround, silhouette, costumes, small-size view, wireframe.
    blender --background <blend> --python render_static.py -- <raw_dir>
"""
import bpy, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import render_lib as R

import common as C
raw = os.path.join(C.AUDIT, "renders", sys.argv[sys.argv.index("--") + 1], "raw")
os.makedirs(raw, exist_ok=True)
ob, arm = R.courier()
sc = R.setup((512, 512))
for v in ("front", "left", "back", "three_quarter"):
    R.render_view(os.path.join(raw, f"turn_{v}.png"), v, target=(0, 0, 6.2), scale=15.0)
# costumes, three-quarter
for n in ("default", "red", "blue", "green"):
    R.set_costume(ob, n)
    R.render_view(os.path.join(raw, f"cos_{n}.png"), "three_quarter", target=(0, 0, 6.2), scale=15.0)
R.set_costume(ob, "default")
# silhouettes
R.setup((512, 512), bg=(1, 1, 1), silhouette=True)
for v in ("front", "left", "three_quarter"):
    R.render_view(os.path.join(raw, f"sil_{v}.png"), v, target=(0, 0, 6.2), scale=15.0)
# small, as in a match: ~120 px tall
R.setup((160, 160))
R.render_view(os.path.join(raw, "small_front.png"), "front", target=(0, 0, 6.2), scale=14.0, res=(160, 160))
R.render_view(os.path.join(raw, "small_three_quarter.png"), "three_quarter", target=(0, 0, 6.2), scale=14.0, res=(160, 160))
# wireframe: a grey solid copy plus a wireframe-modifier copy in black
R.setup((512, 512))
sc.display.shading.color_type = "MATERIAL"
gm = bpy.data.materials.new("grey"); gm.diffuse_color = (0.82, 0.84, 0.88, 1)
bm_ = bpy.data.materials.new("blk"); bm_.diffuse_color = (0.02, 0.02, 0.05, 1)
ob.data.materials[0] = gm
wob = ob.copy(); wob.data = ob.data.copy(); bpy.context.scene.collection.objects.link(wob)
wob.data.materials[0] = bm_
wm = wob.modifiers.new("wf", "WIREFRAME"); wm.thickness = 0.018; wm.use_even_offset = False
for v in ("front", "three_quarter"):
    R.render_view(os.path.join(raw, f"wire_{v}.png"), v, target=(0, 0, 6.2), scale=15.0)
print("RENDERED static")
