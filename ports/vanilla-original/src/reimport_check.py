"""Re-import out/courier.glb into an empty scene and compare it with the source (counts, clips, frame counts).
    blender --background --python reimport_check.py -- [out_dir]
Writes <out>/validation_reimport.json.
"""
import bpy, sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else C.OUT
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps = C.FPS   # glTF times are seconds; the importer converts with the scene fps
bpy.ops.import_scene.gltf(filepath=os.path.join(OUT, "courier.glb"))
cd = json.load(open(os.path.join(OUT, "clips_data.json")))
want = {c["name"]: c["frames"] for c in cd["clips"]}
meshes = [o for o in bpy.data.objects if o.type == "MESH" and len(o.vertex_groups) > 0]   # the importer also adds an Icosphere bone-shape helper
arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
res = dict(checks=[])
def check(name, ok, detail=""):
    res["checks"].append(dict(name=name, ok=bool(ok), detail=detail)); print(("PASS " if ok else "FAIL ") + name + (" : " + detail if detail else ""))
tris = sum(len(p.vertices) - 2 for o in meshes for p in o.data.polygons)
bones = sum(len(a.data.bones) for a in arms)
check("re-import: one mesh object", len(meshes) == 1, str(len(meshes)))
check("re-import: triangle count matches source (2580)", tris == json.load(open(os.path.join(OUT, "validation_blend.json")))["info"]["triangles"], str(tris))
check("re-import: bone count matches source", bones == len(C.BONES), f"{bones} vs {len(C.BONES)}")
names = {a.name: a for a in bpy.data.actions}
# the importer may suffix duplicates or prefix the armature; match by clip name containment
missing = [n for n in want if n not in names]
check("re-import: every clip came back as an action", not missing, f"{len(names)} actions; missing {missing[:5]}")
badfr = []
for n, f in want.items():
    a = names.get(n)
    if not a: continue
    fr = a.frame_range
    got = int(round(fr[1] - fr[0])) + 1
    if got != f: badfr.append((n, got, f))
check("re-import: frame counts match the declared counts", not badfr, str(badfr[:5]))
mx = 0
o = meshes[0]
vgn = [g.name for g in o.vertex_groups]
for v in o.data.vertices:
    mx = max(mx, len([g for g in v.groups if g.weight > 1e-6]))
check("re-import: <= 4 influences per vertex", mx <= 4, str(mx))
res["info"] = dict(triangles=tris, bones=bones, actions=len(names), vertices=len(o.data.vertices))
json.dump(res, open(os.path.join(OUT, "validation_reimport.json"), "w"), indent=1)
print("REIMPORT done")
