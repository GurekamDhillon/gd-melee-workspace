"""Stage 2: bake every clip into a Blender action (one quaternion/location key per bone per frame) and write
stage2_anim.blend plus clips_data.json (the machine-readable clip table the exporter/validator use).

    blender --background out/stage1_model.blend --python build_clips.py -- [out_dir]
"""
import bpy, sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C, anim_lib as A, clips_all
from bpy_extras import anim_utils

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else C.OUT
arm = bpy.data.objects["Courier_Armature"]
A.init_rig(arm)
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"
arm.animation_data_create()
ad = arm.animation_data
KEYED = A.ANIMATED + [f"scarf{i}" for i in range(1, 5)]
KEYED = [b for b in dict.fromkeys(KEYED)]
LOC_BONES = ("trans", "hips")

def bake(clip):
    frames, poses = A.bake_clip(clip)
    frames = A.continuity_fix(frames)
    act = bpy.data.actions.new(clip.name)
    act.use_fake_user = True
    slot = act.slots.new(id_type='OBJECT', name=arm.name)
    ad.action = act
    ad.action_slot = slot
    cb = anim_utils.action_ensure_channelbag_for_slot(act, slot)
    n = len(frames)
    for b in KEYED:
        q = [frames[i][1][b][0] for i in range(n)]
        for k in range(4):
            fc = cb.fcurves.new(f'pose.bones["{b}"].rotation_quaternion', index=k, group_name=b)
            fc.keyframe_points.add(n)
            co = []
            for i in range(n):
                co += [float(i), float(q[i][k])]
            fc.keyframe_points.foreach_set("co", co)
            fc.keyframe_points.foreach_set("interpolation", [1] * n)   # LINEAR
            fc.update()
        if b in LOC_BONES:
            loc = [frames[i][1][b][1] for i in range(n)]
            for k in range(3):
                fc = cb.fcurves.new(f'pose.bones["{b}"].location', index=k, group_name=b)
                fc.keyframe_points.add(n)
                co = []
                for i in range(n):
                    co += [float(i), float(loc[i][k])]
                fc.keyframe_points.foreach_set("co", co)
                fc.keyframe_points.foreach_set("interpolation", [1] * n)
                fc.update()
    act.use_frame_range = True
    act.frame_start = 0; act.frame_end = max(1, n - 1)
    act.use_cyclic = bool(clip.loop)
    return act, poses

clips = clips_all.all_clips()
table = []
for c in clips:
    act, poses = bake(c)
    tr = ad.nla_tracks.new(); tr.name = c.name
    st = tr.strips.new(c.name, 0, act)
    st.action = act
    tp = [p.v["tp"] for p in poses]
    table.append(dict(name=c.name, frames=c.n, loop=bool(c.loop), serves=c.serves, status=c.status, category=c.category,
                      hit_frames=c.hit or [], root_motion=bool(c.root_motion),
                      root_motion_total=[round(x, 3) for x in tp[-1]] if c.root_motion else [0, 0, 0],
                      ref=c.ref, notes=c.notes, wind=c.wind))
ad.action = None
os.makedirs(OUT, exist_ok=True)
json.dump(dict(clips=table, aliases=clips_all.aliases()), open(os.path.join(OUT, "clips_data.json"), "w"), indent=1)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "stage2_anim.blend"))
print("STAGE2 clips", len(table), "frames", sum(t["frames"] for t in table), "->", os.path.join(OUT, "stage2_anim.blend"))
