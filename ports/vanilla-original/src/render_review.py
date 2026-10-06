"""Headless review renders from BAKED clips (so the scarf follower, lag and breathing are in the picture).
    blender --background out/stage1_model.blend --python render_review.py -- <jobs.json>
jobs.json: {"src": "<dir of the anim_lib/clips to use>" (optional, default this src),
            "jobs": [{"out": png, "clip": name, "frame": int, "view": "left|front|three_quarter|back", "res": [w, h],
                      "scale": 17.0, "target": [x, y, z] (relative to the root motion), "sil": bool, "costume": "default"}]}
Used by review.py (the sheets) and by hand; a baked clip is cached per process.
"""
import bpy, sys, os, json
args = sys.argv[sys.argv.index("--") + 1:]
spec = json.load(open(args[0]))
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = spec.get("src") or HERE
sys.path.insert(0, SRC)
sys.path.insert(1, HERE)
import common as C, anim_lib as A, render_lib as R, clips_all
ob, arm = R.courier()
A.init_rig(arm)
CL = {c.name: c for c in clips_all.all_clips()}
CACHE = {}

def baked(name):
    if name not in CACHE:
        frames, poses = A.bake_clip(CL[name])
        frames = A.continuity_fix(frames)
        CACHE[name] = (frames, poses)
    return CACHE[name]

def apply(frames, f):
    f = max(0, min(len(frames) - 1, f))
    for b, (q, loc) in frames[f][1].items():
        pb = arm.pose.bones[b]; pb.rotation_mode = "QUATERNION"; pb.rotation_quaternion = q
        if loc is not None: pb.location = loc
    bpy.context.view_layer.update()

dump = {}
for name in spec.get("dump", []):
    frames, poses = baked(name)
    rows = []
    for p in poses:
        r, Pw, Aw = A.eval_pose(p, True)
        row = {k: [Pw[k].x, Pw[k].y, Pw[k].z] for k in ("hand_L", "hand_R", "foot_L", "foot_R", "head", "chest", "hips", "forearm_L", "forearm_R", "shin_L", "shin_R")}
        for sd in "LR":
            h, b_, t_ = A.sole_points(Pw, Aw, sd) if hasattr(A, "sole_points") else (Pw["foot_" + sd], Pw["foot_" + sd], Pw["foot_" + sd])
            row["heel_" + sd] = [h.x, h.y, h.z]; row["ball_" + sd] = [b_.x, b_.y, b_.z]; row["tip_" + sd] = [t_.x, t_.y, t_.z]
        row["tp"] = list(p.v["tp"])
        rows.append(row)
    dump[name] = rows
if dump:
    json.dump(dump, open(spec["dump_out"], "w"))
mode = None
for j in spec["jobs"]:
    sil = bool(j.get("sil"))
    if mode != sil:
        R.setup(tuple(j.get("res", (200, 256))), silhouette=sil); mode = sil
    frames, poses = baked(j["clip"])
    apply(frames, int(j["frame"]))
    if j.get("costume"): R.set_costume(ob, j["costume"])
    tp = poses[max(0, min(len(poses) - 1, int(j["frame"])))].v["tp"] if j.get("follow_root", True) else (0, 0, 0)
    t = j.get("target", (0, -1.0, 6.0))
    tgt = (t[0] + tp[0], t[1] - tp[1], t[2] + tp[2] * 0.8)
    R.render_view(j["out"], j.get("view", "left"), target=tgt, scale=j.get("scale", 17.0), res=tuple(j.get("res", (200, 256))))
print("RENDERED", len(spec["jobs"]), "jobs")
