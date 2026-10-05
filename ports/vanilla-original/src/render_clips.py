"""Render key poses of clips (headless Workbench), without baking actions.
    blender --background stage1_model.blend --python render_clips.py -- <round> <spec> [<spec> ...]
spec: moves | common | film:<clip>:<f,f,...> | one:<clip>:<f> | small:<clip>:<f>
Writes raw/<tag>.png plus raw/index_<specname>.json for sheets.py.
"""
import bpy, sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C, anim_lib as A, render_lib as R
import clips_all

args = sys.argv[sys.argv.index("--") + 1:]
rnd, specs = args[0], args[1:]
raw = os.path.join(C.AUDIT, "renders", rnd, "raw")
os.makedirs(raw, exist_ok=True)
ob, arm = R.courier()
A.init_rig(arm)
CL = {c.name: c for c in clips_all.all_clips()}

def pose_at(clip, f):
    p = clip.sample(float(f))
    if (p.v["fl"] is not None or p.v["fr"] is not None) and clip.fit:
        p = A.fit_hips(p)
    return p

def apply(p):
    res = A.eval_pose(p)
    for b, (q, loc) in res.items():
        pb = arm.pose.bones[b]; pb.rotation_mode = "QUATERNION"; pb.rotation_quaternion = q
        if loc is not None: pb.location = loc
    bpy.context.view_layer.update()

def shoot(path, clip, f, view="left", res=(200, 200), scale=17.0, target=(0, -0.5, 6.2)):
    p = pose_at(clip, f)
    # scarf rest: use the baked follow-through for fidelity
    apply(p)
    tp = p.v["tp"]
    tgt = (target[0] + tp[0], target[1] - tp[1], target[2] + tp[2] * 0.8)
    R.render_view(path, view, target=tgt, scale=scale, res=res)

sc = R.setup((200, 200))
for spec in specs:
    parts = spec.split(":")
    kind = parts[0]
    index = []
    if kind in ("moves", "common"):
        for c in CL.values():
            ismove = c.category == "move" or (c.category == "air" and c.hit is not None)
            if (kind == "moves") != ismove: continue
            f = int(c.hit[0]) if c.hit else (c.n // 2 if c.loop else int(c.n * 0.4))
            tag = f"{kind}_{c.name}_{f}"
            shoot(os.path.join(raw, tag + ".png"), c, f)
            index.append(dict(file=tag + ".png", label=f"{c.name} f{f}"))
        json.dump(index, open(os.path.join(raw, f"index_{kind}.json"), "w"))
    elif kind == "film":
        c = CL[parts[1]]; fr = [int(x) for x in parts[2].split(",")]
        view = parts[3] if len(parts) > 3 else "left"
        for f in fr:
            tag = f"film_{c.name}_{f}"
            shoot(os.path.join(raw, tag + ".png"), c, f, view=view, res=(192, 256), scale=17.0, target=(0, -1.2, 6.0))
            index.append(dict(file=tag + ".png", label=f"{c.name} f{f}"))
        json.dump(index, open(os.path.join(raw, f"index_film_{c.name}.json"), "w"))
    elif kind in ("one", "small"):
        c = CL[parts[1]]; f = int(parts[2])
        view = parts[3] if len(parts) > 3 else "left"
        res = (120, 120) if kind == "small" else (384, 384)
        shoot(os.path.join(raw, f"{kind}_{c.name}_{f}_{view}.png"), c, f, view=view, res=res)
print("RENDERED clips", specs)
