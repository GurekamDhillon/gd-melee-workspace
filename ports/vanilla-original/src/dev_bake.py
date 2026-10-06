"""Dev helper: bake named clips and print stats.   blender --background out/stage1_model.blend --python dev_bake.py -- Clip [Clip ...]"""
import bpy, sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C, anim_lib as A, clips_all, locostats
arm = bpy.data.objects["Courier_Armature"]; A.init_rig(arm)
CL = {c.name: c for c in clips_all.all_clips()}
for name in sys.argv[sys.argv.index("--") + 1:]:
    c = CL[name]
    frames, poses = A.bake_clip(c)
    m = c.metrics
    line = f"OUT {name} n={c.n} clear={m['scarf_clearance']} ang=" + ",".join(f"{k.split('_')[0]}{v:.0f}" for k, v in m["max_angle"].items() if k in ("forearm_L", "shin_L", "thigh_L", "upperarm_L"))
    hz = [p.v["hp"][2] for p in poses]
    line += f" hipz[{min(hz):.2f},{max(hz):.2f}]"
    if c.ref.get("ground_ref_speed"):
        line += " " + json.dumps(locostats.summarize(m["soles"], c.ref["ground_ref_speed"], c.loop))
    print(line)
json.dump({n: CL[n].metrics for n in sys.argv[sys.argv.index("--") + 1:]}, open(os.path.join(C.OUT, "dev_metrics.json"), "w"))
