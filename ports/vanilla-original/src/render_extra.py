"""Extra review renders (headless Workbench): joint weight/wire views, hurtbox + ECB overlay, size comparison,
flat-black silhouette sheet of attack poses and ~120 px match-size sheet.
    blender --background out/stage1_model.blend --python render_extra.py -- <round> <kind> [<kind> ...]
kinds: weights | hurt | size | silsheet | smallsheet
"""
import bpy, bmesh, sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C, anim_lib as A, render_lib as R, clips_all
from mathutils import Vector

args = sys.argv[sys.argv.index("--") + 1:]
rnd, kinds = args[0], args[1:]
raw = os.path.join(C.AUDIT, "renders", rnd, "raw")
os.makedirs(raw, exist_ok=True)
ob, arm = R.courier()
A.init_rig(arm)
CL = {c.name: c for c in clips_all.all_clips()}

def apply(p):
    res = A.eval_pose(p, True)
    r, Pw, _ = res
    for b, (q, loc) in r.items():
        pb = arm.pose.bones[b]; pb.rotation_mode = "QUATERNION"; pb.rotation_quaternion = q
        if loc is not None: pb.location = loc
    bpy.context.view_layer.update()
    return Pw

def mat(name, rgb):
    m = bpy.data.materials.new(name); m.diffuse_color = (*rgb, 1); return m

def clip_pose(name, f):
    c = CL[name]; p = c.sample(float(f))
    if (p.v["fl"] is not None or p.v["fr"] is not None) and c.fit: p = A.fit_hips(p)
    return p

index = {}
for kind in kinds:
    if kind == "weights":
        # a copy of the mesh coloured by the weight of one bone (blue 0 -> red 1) with a wireframe overlay
        R.setup((256, 256))
        sc = bpy.context.scene
        sh = sc.display.shading; sh.color_type = "VERTEX"; sh.light = "FLAT"
        wmesh = ob.copy(); wmesh.data = ob.data.copy(); sc.collection.objects.link(wmesh)
        wmesh.parent = arm; wmesh.modifiers.clear(); md = wmesh.modifiers.new("Armature", "ARMATURE"); md.object = arm
        ob.hide_render = True
        me = wmesh.data
        if me.color_attributes.get("Col"): me.color_attributes.remove(me.color_attributes["Col"])
        ca = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
        wf = wmesh.copy(); wf.data = wmesh.data; sc.collection.objects.link(wf)
        wf.parent = arm; wf.modifiers.clear(); md2 = wf.modifiers.new("Armature", "ARMATURE"); md2.object = arm
        wm_ = wf.modifiers.new("wf", "WIREFRAME"); wm_.thickness = 0.012; wm_.use_even_offset = False
        wf.data = wf.data.copy()
        cb = wf.data.color_attributes["Col"]
        for v in wf.data.vertices: cb.data[v.index].color = (0.02, 0.02, 0.06, 1)
        sh.color_type = "VERTEX"
        def color_for(bone):
            gi = wmesh.vertex_groups[bone].index
            for v in me.vertices:
                w = 0.0
                for g in v.groups:
                    if g.group == gi: w = g.weight
                col = (w, 0.15 + 0.5 * (1 - abs(2 * w - 1)), 1 - w, 1)
                ca.data[v.index].color = col
        joints = [("shoulder", "upperarm_L", "upperarm_L"), ("elbow", "forearm_L", "forearm_L"), ("hip", "thigh_L", "thigh_L"), ("knee", "shin_L", "shin_L")]
        idx = []
        for jn, bone, hb in joints:
            color_for(bone)
            for ang in (0, 90, 140):
                if jn == "shoulder": p = A.P(aL=(ang if ang else 0, 38 if ang == 0 else 20, 0, 10, 0), fl=None, fr=None)
                elif jn == "elbow": p = A.P(aL=(60 if ang else 0, 38 if ang == 0 else 20, 0, ang, 0), fl=None, fr=None)
                elif jn == "hip": p = A.P(lL=(ang, 0, 10, 0), fl=None, fr=None, hp=(0, 0, 0))
                else: p = A.P(lL=(30 if ang else 0, 0, ang, 0), fl=None, fr=None)
                Pw = apply(p)
                tgt = Pw[hb]
                tag = f"w_{jn}_{ang}"
                R.render_view(os.path.join(raw, tag + ".png"), "left" if jn in ("hip", "knee") else "three_quarter", target=(tgt.x, tgt.y, tgt.z), scale=6.5, res=(256, 256), dirv=(1, -0.2, 0.05) if jn in ("hip", "knee") else (0.5, -0.85, 0.15))
                idx.append(dict(file=tag + ".png", label=f"{jn} bend {ang}" if ang else f"{jn} rest"))
        index["weights"] = idx
    elif kind == "hurt":
        R.setup((384, 512))
        sc = bpy.context.scene
        sc.display.shading.color_type = "MATERIAL"
        grey = mat("grey", (0.80, 0.82, 0.86)); ob.data.materials[0] = grey
        apply(A.P(aL=(0, 38, 0, 0, 0), aR=(0, 38, 0, 0, 0), fl=None, fr=None, cuL=1, cuR=1))
        red = mat("red", (0.9, 0.1, 0.1))
        for h in C.HURTBOXES:
            a, b, r = Vector(h["a"]), Vector(h["b"]), h["radius"]
            bm = bmesh.new()
            d = (b - a); L = d.length
            bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=r, matrix=__import__("mathutils").Matrix.Translation(a))
            bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=r, matrix=__import__("mathutils").Matrix.Translation(b))
            cyl = bmesh.ops.create_cone(bm, cap_ends=False, segments=10, radius1=r, radius2=r, depth=L)
            q = Vector((0, 0, 1)).rotation_difference(d.normalized())
            M = __import__("mathutils").Matrix.Translation((a + b) / 2) @ q.to_matrix().to_4x4()
            for v in cyl["verts"]: v.co = M @ v.co
            me = bpy.data.meshes.new("hb"); bm.to_mesh(me); bm.free()
            o = bpy.data.objects.new("hb_" + h["id"], me); sc.collection.objects.link(o); me.materials.append(red)
            w = o.modifiers.new("wf", "WIREFRAME"); w.thickness = 0.03; w.use_even_offset = False
        # ECB diamond (standing)
        e = C.ECB["standing"]
        cu = bpy.data.curves.new("ecb", "CURVE"); cu.dimensions = "3D"; cu.bevel_depth = 0.07
        sp = cu.splines.new("POLY"); sp.points.add(3)
        pts = [(0, 0, e["bottom"]), (e["right"], 0, e["side_height"]), (0, 0, e["top"]), (e["left"], 0, e["side_height"])]
        for pnt, co in zip(sp.points, pts): pnt.co = (*co, 1)
        sp.use_cyclic_u = True
        eo = bpy.data.objects.new("ecb", cu); sc.collection.objects.link(eo); eo.data.materials.append(mat("blue", (0.1, 0.2, 0.95)))
        idx = []
        for v in ("front", "left", "three_quarter"):
            R.render_view(os.path.join(raw, f"hurt_{v}.png"), v, target=(0, 0, 6.2), scale=15.0, res=(384, 512))
            idx.append(dict(file=f"hurt_{v}.png", label=f"hurtboxes (red) and ECB diamond (blue): {v}"))
        index["hurt"] = idx
    elif kind == "size":
        R.setup((512, 512))
        sc = bpy.context.scene
        apply(A.P(aL=(0, 38, 0, 0, 0), aR=(0, 38, 0, 0, 0), fl=None, fr=None, cuL=1, cuR=1))
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
        me = bpy.data.meshes.new("stand"); bm.to_mesh(me); bm.free()
        blk = bpy.data.objects.new("standin", me); sc.collection.objects.link(blk)
        gm = mat("stand", (0.55, 0.57, 0.62)); me.materials.append(gm)
        # a stand-in block 5.4 wide x 3.6 deep x 9.5 tall, an ASSUMED retail-class proportion (not measured from any model)
        blk.scale = (5.4, 3.6, 9.5); blk.location = (-9.0, 0, 4.75)
        sc.display.shading.color_type = "TEXTURE"
        # the block has a plain grey material; Workbench texture mode uses material colour where there is no image
        R.render_view(os.path.join(raw, "size_front.png"), "front", target=(-4.5, 0, 6.2), scale=24.0, res=(512, 384))
        R.render_view(os.path.join(raw, "size_left.png"), "left", target=(-4.5, 0, 6.2), scale=24.0, res=(512, 384))
        index["size"] = [dict(file="size_front.png", label="Courier (right) vs 5.4x3.6x9.5 stand-in block (left): front"), dict(file="size_left.png", label="side")]
    elif kind in ("silsheet", "smallsheet"):
        names = [("Attack11", 3), ("Attack12", 3), ("Attack13", 5), ("AttackDash", 8), ("AttackS3S", 6), ("AttackHi3", 5), ("AttackLw3", 6), ("AttackS4S", 13),
                 ("AttackHi4", 10), ("AttackLw4", 6), ("AttackAirN", 6), ("AttackAirF", 19), ("AttackAirB", 7), ("AttackAirHi", 5), ("AttackAirLw", 15), ("Catch", 6),
                 ("ThrowF", 13), ("NRelease", 6), ("SLunge", 8), ("CounterStrike", 3), ("Wait", 0), ("Run", 4), ("JumpF", 12), ("Guard", 6)]
        if kind == "silsheet":
            R.setup((200, 200), bg=(1, 1, 1), silhouette=True); res = (200, 200); scale = 17.0
        else:
            R.setup((160, 160)); res = (160, 160); scale = 16.5
        idx = []
        for n, f in names:
            p = clip_pose(n, f); apply(p)
            tp = p.v["tp"]
            tag = f"{kind}_{n}_{f}"
            R.render_view(os.path.join(raw, tag + ".png"), "left", target=(0, -0.5, 6.0), scale=scale, res=res)
            idx.append(dict(file=tag + ".png", label=f"{n} f{f}"))
        index[kind] = idx
for k, v in index.items():
    json.dump(v, open(os.path.join(raw, f"index_{k}.json"), "w"))
print("RENDERED extra", kinds)
