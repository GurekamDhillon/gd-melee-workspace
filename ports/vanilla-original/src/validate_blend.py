"""Blender-side validation of out/stage2_anim.blend (weights, actions, move readability, foot slide).
    blender --background out/stage2_anim.blend --python validate_blend.py -- [out_dir]
Writes <out>/validation_blend.json.
"""
import bpy, sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C, anim_lib as A, clips_all
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else C.OUT
arm = bpy.data.objects["Courier_Armature"]; mesh = bpy.data.objects["Courier"]
A.init_rig(arm)
res = dict(checks=[], info={})
def check(name, ok, detail=""):
    res["checks"].append(dict(name=name, ok=bool(ok), detail=detail))
    print(("PASS " if ok else "FAIL ") + name + (" : " + detail if detail else ""))

# ---- skin: influences, normalisation, unskinned vertices
me = mesh.data
vg_names = [g.name for g in mesh.vertex_groups]
deform = set(C.DEFORM)
mx, bad_norm, unskinned, nonbone = 0, 0, 0, 0
for v in me.vertices:
    ws = [(vg_names[g.group], g.weight) for g in v.groups if g.weight > 1e-6]
    mx = max(mx, len(ws))
    s = sum(w for _, w in ws)
    if not ws: unskinned += 1
    if abs(s - 1.0) > 1e-3: bad_norm += 1
    if any(n not in deform for n, _ in ws): nonbone += 1
check("max influences per vertex <= 4", mx <= 4, f"max {mx}")
check("weights normalised (sum 1 +- 1e-3)", bad_norm == 0, f"{bad_norm} vertices off")
check("no unskinned vertices", unskinned == 0, f"{unskinned} unskinned of {len(me.vertices)}")
check("weights only on deform bones", nonbone == 0)
tris = sum(len(p.vertices) - 2 for p in me.polygons)
res["info"].update(vertices=len(me.vertices), triangles=tris, bones=len(arm.data.bones), deform_bones=len(deform),
                   materials=len([m for m in bpy.data.materials if m.name.startswith("mat_")]), uv_layers=len(me.uv_layers))
check("triangles within budget (<= 4000)", tris <= 4000, str(tris))
check("bones within budget (<= 64 for a pc-palette 64 packing; total <= 90)", len(deform) <= 64 and len(arm.data.bones) <= 90, f"{len(deform)} deform / {len(arm.data.bones)} total")
check("one mesh, one material slot (packs into one skinned piece)", len(me.materials) == 1, f"{len(me.materials)} slot(s)")
check("every mesh has a real material", all(m is not None for m in me.materials))
check("UV layer present", len(me.uv_layers) >= 1)
# bone scale in rest pose
check("no bone scale in rest pose", all(abs(pb.scale[i] - 1) < 1e-6 for pb in arm.pose.bones for i in range(3)))
# all bone roles present for the engine's list
need_roles = ["root", "translation", "hips", "spine", "chest", "neck", "head", "shoulder", "upper_arm", "lower_arm", "hand", "upper_leg", "lower_leg",
              "foot", "toe", "item_socket", "grab_anchor", "victim_anchor", "camera_focus", "shield_origin", "reflect_origin", "absorb_origin", "head_top"]
have = {b["role"] for b in C.BONES}
check("all required roles present", all(r in have for r in need_roles), str([r for r in need_roles if r not in have]))
check("hurtbox count <= 15 (FighterHurtCapsule hurt_capsules[15])", len(C.HURTBOXES) <= 15, str(len(C.HURTBOXES)))
check("hurtbox bones exist", all(h["bone"] in C.BONE for h in C.HURTBOXES))


# ---- frozen mesh / skin / skeleton (the engine lane has already converted them): geometry, weights and bone table must not change
import hashlib
def _H(items): return hashlib.sha1("|".join(items).encode()).hexdigest()[:12]
_vg = {g.index: g.name for g in mesh.vertex_groups}
_pos = sorted("%.3f,%.3f,%.3f" % tuple(v.co) for v in me.vertices)
_ws = {}
for v in me.vertices:
    for g in v.groups: _ws[_vg[g.group]] = _ws.get(_vg[g.group], 0) + g.weight
_bs = ["%s|%s|%s|%s" % (b.name, b.parent.name if b.parent else "", tuple(round(x, 4) for x in b.head_local), tuple(round(x, 4) for x in b.tail_local)) for b in arm.data.bones]
_fz = json.load(open(os.path.join(C.PKG, "data", "frozen_contract.json")))["mesh"]
_got = dict(pos=_H(_pos), weights=_H(["%s:%.1f" % (k, _ws[k]) for k in sorted(_ws)]), bones=_H(_bs))
check("mesh vertices, skin weights and bone table are bit-for-bit the first lane's (frozen: the engine lane has converted them)", all(_got[k] == _fz[k] for k in _got), str(_got))

# ---- actions
cd = json.load(open(os.path.join(OUT, "clips_data.json")))
clip_by_name = {c["name"]: c for c in cd["clips"]}
acts = {a.name: a for a in bpy.data.actions}
check("an action per clip", set(acts) == set(clip_by_name), f"{len(acts)} actions / {len(clip_by_name)} clips")
required_bones = [b["name"] for b in C.BONES if b["deform"]] + ["trans"]
from bpy_extras import anim_utils
bad_frames, bad_keys, scale_keys, euler_keys, short = [], [], 0, 0, []
total_frames = 0
for name, c in clip_by_name.items():
    a = acts[name]
    slot = a.slots[0]
    cb = anim_utils.action_ensure_channelbag_for_slot(a, slot)
    byb = {}
    for fc in cb.fcurves:
        dp = fc.data_path
        if dp.endswith(".scale"): scale_keys += 1
        if dp.endswith(".rotation_euler"): euler_keys += 1
        b = dp.split('"')[1]
        byb.setdefault(b, []).append((dp.rsplit(".", 1)[1], len(fc.keyframe_points)))
        if len(fc.keyframe_points) != c["frames"]: bad_frames.append((name, dp, len(fc.keyframe_points)))
    miss = [b for b in required_bones if b not in byb]
    if miss: bad_keys.append((name, miss))
    total_frames += c["frames"]
check("every clip keyed on every required role bone", not bad_keys, str(bad_keys[:3]))
check("every channel has the declared frame count", not bad_frames, str(bad_frames[:3]))
check("no scale channels in any clip", scale_keys == 0, str(scale_keys))
check("no euler channels (quaternion only)", euler_keys == 0)
res["info"]["clips"] = len(clip_by_name); res["info"]["total_frames"] = total_frames

# ---- loops loop cleanly: the first and last+1 pose differ by no more than one frame step
CL = {c.name: c for c in clips_all.all_clips()}
jumps = []
def vec_state(clip, f):
    p = clip.sample(float(f))
    if (p.v["fl"] is not None or p.v["fr"] is not None) and clip.fit: p = A.fit_hips(p)
    r, Pw, Aw = A.eval_pose(p, True)
    return Pw
for n, c in CL.items():
    if not c.loop: continue
    P0, Pn, Pm = vec_state(c, 0), vec_state(c, c.n - 1), vec_state(c, c.n)   # frame n wraps to 0
    # compare the wrap step (n-1 -> n==0) with the typical step (0 -> 1)
    P1 = vec_state(c, 1)
    def d(Pa, Pb): return max((Pa[b] - Pb[b]).length for b in ("hand_L", "hand_R", "foot_L", "foot_R", "head"))
    wrap, step = d(Pn, P0), max(d(P0, P1), 0.05)
    if wrap > 3.0 * step + 0.25: jumps.append((n, round(wrap, 2), round(step, 2)))
check("loops wrap without a pop (wrap step <= 3x typical step + 0.25)", not jumps, str(jumps[:4]))

# ---- move readability: the striking limb peaks (is within 90% of its local maximum reach) on the hit frame
reads = {}
for n, c in CL.items():
    if not c.hit or c.category not in ("move", "air"): continue
    h = int(c.hit[0])
    if n.startswith('Throw') or n == 'AttackDash': continue   # a throw's frame is the release; the dash attack strikes with the whole body (shoulder), not a reaching limb
    lo, hi = max(0, h - 4), min(c.n - 1, h + 6)
    reach = []
    for f in range(lo, hi + 1):
        Pw = vec_state(c, f)
        ctr = Pw["chest"]
        reach.append(max((Pw[b] - ctr).length for b in ("hand_L", "hand_R", "foot_L", "foot_R", "head")))
    at = reach[h - lo]
    reads[n] = round(at / max(reach), 3)
res["info"]["move_reach_ratio_at_hit"] = reads
weak = {k: v for k, v in reads.items() if v < 0.85}
check("striking pose is within 85% of the clip's max reach on the hit frame (window hit-4..hit+6; throws and the whole-body dash attack excluded)", not weak, str(weak))

# ---- foot slide: stance foot speed uniformity in the walk/run cycles
slide = {}
for n in ("WalkSlow", "WalkMiddle", "WalkFast", "Run", "LiftWalk"):
    c = CL[n]
    seqs = {"L": [], "R": []}
    for f in range(c.n + 1):
        Pw = vec_state(c, f)
        for s in "LR":
            q = Pw[f"foot_{s}"]
            seqs[s].append((q.y, q.z))
    speeds, planted = [], 0
    for s in "LR":
        for i in range(c.n):
            y0, z0 = seqs[s][i]; y1, z1 = seqs[s][i + 1]
            if z0 < 1.25 + 0.12 and z1 < 1.25 + 0.12 and abs(z0 - 1.25) < 0.12:
                speeds.append(abs(y1 - y0)); planted += 1
    ref = c.ref["ground_ref_speed"]
    mean = sum(speeds) / max(1, len(speeds))
    var = max(speeds) - min(speeds) if speeds else 0
    slide[n] = dict(ref_speed=ref, stance_mean_speed=round(mean, 4), stance_speed_spread=round(var, 4), planted_frames=planted)
res["info"]["foot_slide"] = slide
bad = {k: v for k, v in slide.items() if abs(v["stance_mean_speed"] - v["ref_speed"]) > 0.2 * v["ref_speed"]}
check("stance foot ground speed matches the clip's declared ground_ref_speed (+-20%)", not bad, str(bad))
json.dump(res, open(os.path.join(OUT, "validation_blend.json"), "w"), indent=1)
print("VALIDATE_BLEND done", sum(1 for c in res["checks"] if c["ok"]), "/", len(res["checks"]), "passed")
