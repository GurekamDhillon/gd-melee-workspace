"""make_starter.py - generate the Geno starter project in Blender: export skeleton, sample mesh, labelled sockets, example actions.

    blender -b --python tools/geno/artist/blender/make_starter.py -- --out starter.blend [--name Starter] [--params params.json] [--no-actions]

params.json (all optional):
    {"proportions": {"hip_h": 4.2, "head_r": 2.2, ...},          # skeleton.DEFAULT_PROPORTIONS keys
     "names": {"hips": "Pelvis", "upper_arm.L": "LeftArm", ...}, # role id -> bone name (the role is stored on the armature)
     "colors": {"skin": [r,g,b], "cloth": [...], "accent": [...], "boots": [...]},
     "actions": ["Wait", "WalkMiddle", ...]}                     # default: the prototype set
Everything the file needs travels in it: the roles are the armature's `geno` custom property (exported as glTF extras), the actions
carry `geno_*` custom properties, hit frames are timeline-style markers stored on the action. No add-on is required to export.
"""
import json
import math
import os
import sys

import bpy
import bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import skeleton as SK  # noqa: E402
import actions as AC  # noqa: E402


def args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = {"out": "starter.blend", "name": "Starter", "params": None, "actions": True}
    i = 0
    while i < len(a):
        if a[i] == "--out": out["out"] = a[i + 1]; i += 2
        elif a[i] == "--name": out["name"] = a[i + 1]; i += 2
        elif a[i] == "--params": out["params"] = a[i + 1]; i += 2
        elif a[i] == "--no-actions": out["actions"] = False; i += 1
        else: i += 1
    return out


def make_armature(name, bones):
    arm_data = bpy.data.armatures.new(name + "_Armature")
    arm = bpy.data.objects.new(name + "_Armature", arm_data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eb = {}
    for b in bones:
        e = arm_data.edit_bones.new(b["name"])
        e.head, e.tail = Vector(b["head"]), Vector(b["tail"])
        e.use_deform = b["deform"]
        eb[b["name"]] = e
    for b in bones:
        if b["parent"]:
            pn = [x for x in bones if x["role"] == b["parent"]][0]["name"]
            eb[b["name"]].parent = eb[pn]
            eb[b["name"]].use_connect = False
    # roll 0 everywhere: bone local axes are predictable (Y along the bone)
    for e in eb.values():
        e.roll = 0.0
    bpy.ops.object.mode_set(mode="OBJECT")
    # label the sockets so they are obvious in the viewport
    for b in bones:
        if not b["deform"]:
            pb = arm.pose.bones[b["name"]]
            pb.custom_shape_scale_xyz = (1, 1, 1)
    arm_data.display_type = "STICK"
    arm.show_in_front = True
    return arm


def tube(bm, a, b, rx0, ry0, rx1, ry1, rings, sides, cell, profile=None, uvl=None):
    """Elliptical tube from a to b. Cross-section axes: X (side) and the other horizontal axis. Returns list of vertex rings."""
    a, b = Vector(a), Vector(b)
    axis = (b - a)
    L = axis.length
    if L < 1e-6:
        axis = Vector((0, 0, 0.01)); L = 0.01
    ax = axis.normalized()
    ref = Vector((1, 0, 0)) if abs(ax.x) < 0.9 else Vector((0, 1, 0))
    u = (ref - ax * ref.dot(ax)).normalized()
    v = ax.cross(u).normalized()
    rows = []
    for i in range(rings):
        t = i / (rings - 1)
        k = profile(t) if profile else 1.0
        rx = (rx0 + (rx1 - rx0) * t) * k
        ry = (ry0 + (ry1 - ry0) * t) * k
        c = a + axis * t
        ring = []
        for j in range(sides):
            th = 2 * math.pi * j / sides
            ring.append(bm.verts.new(c + u * (rx * math.cos(th)) + v * (ry * math.sin(th))))
        rows.append(ring)
    u0, v0, cw, ch = cell
    for i in range(rings - 1):
        for j in range(sides):
            j2 = (j + 1) % sides
            f = bm.faces.new((rows[i][j], rows[i][j2], rows[i + 1][j2], rows[i + 1][j]))
            uvs = [(j, i), (j + 1, i), (j + 1, i + 1), (j, i + 1)]
            for lp, (jj, ii) in zip(f.loops, uvs):
                lp[uvl].uv = (u0 + cw * jj / sides, v0 + ch * ii / (rings - 1))
    # caps
    for ring, ii in ((rows[0], 0), (rows[-1], rings - 1)):
        f = bm.faces.new(ring if ii else list(reversed(ring)))
        for lp in f.loops:
            lp[uvl].uv = (u0 + cw * 0.5, v0 + ch * (0.0 if ii == 0 else 1.0))
    return rows


def sphere_profile(t):
    return max(0.25, math.sqrt(max(0.0, 1 - (2 * t - 1) ** 2)))


def make_mesh(name, arm, bones, prop, colors):
    p = dict(SK.DEFAULT_PROPORTIONS); p.update(prop or {})
    T = p["thickness"]
    by = {b["role"]: b for b in bones}
    mesh = bpy.data.meshes.new(name)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    pieces = []     # (bone name, parent bone name, rings list)
    cells = {}
    ci = [0]

    def cell():
        k = ci[0]; ci[0] += 1
        return ((k % 5) / 5.0, (k // 5) / 5.0, 0.2, 0.2)

    def piece(role, a_role=None, b_role=None, a=None, b=None, rx0=1, ry0=None, rx1=None, ry1=None, rings=5, sides=8, profile=None, color="cloth"):
        bone = by[role]
        pa = Vector(a if a else by[a_role or role]["head"])
        pb = Vector(b if b else by[b_role or role]["tail"])
        ry0 = rx0 if ry0 is None else ry0
        rx1 = rx0 if rx1 is None else rx1
        ry1 = ry0 if ry1 is None else ry1
        c = cell()
        rows = tube(bm, pa, pb, rx0 * T, ry0 * T, rx1 * T, ry1 * T, rings, sides, c, profile, uvl)
        pieces.append((bone["name"], bone["parent"], rows, pa, pb, color, c))

    hip = p["hip_h"]
    piece("hips", a=(0, 0, hip - 0.2), b=by["spine"]["head"], rx0=p["torso_w"] * 0.8, ry0=p["torso_d"], rx1=p["torso_w"] * 0.75, ry1=p["torso_d"], color="cloth")
    piece("spine", rx0=p["torso_w"] * 0.75, ry0=p["torso_d"], rx1=p["torso_w"] * 0.85, ry1=p["torso_d"], color="cloth")
    piece("chest", rx0=p["torso_w"] * 0.85, ry0=p["torso_d"], rx1=p["torso_w"] * 0.95, ry1=p["torso_d"] * 0.9, color="accent")
    piece("neck", rx0=0.55, rx1=0.5, rings=3, color="skin")
    piece("head", rx0=p["head_r"], ry0=p["head_r"] * 0.95, rings=9, sides=10, profile=sphere_profile, color="skin")
    for s in "LR":
        piece("upper_arm." + s, rx0=0.7, rx1=0.6, color="cloth")
        piece("lower_arm." + s, rx0=0.62, rx1=0.55, color="skin")
        piece("hand." + s, rx0=0.7, rx1=0.55, rings=4, sides=6, color="accent")
        piece("upper_leg." + s, rx0=0.95, rx1=0.8, color="cloth")
        piece("lower_leg." + s, rx0=0.8, rx1=0.65, color="cloth")
        fh = by["foot." + s]["head"]
        piece("foot." + s, a=(fh[0], fh[1] + 0.4, fh[2] - 0.3), b=by["toe." + s]["tail"], rx0=0.85, ry0=0.75, rx1=0.8, ry1=0.55, rings=4, sides=6, color="boots")
    for s in "LR":                                    # shoulders: a short stub so the arm joins the torso
        sh = by["shoulder." + s]
        piece("shoulder." + s, rx0=0.65, rx1=0.7, rings=3, color="accent")
    bm.normal_update()
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()
    # weights: each piece belongs to its bone; the first 40% of a limb blends toward its parent bone (<= 2 influences by construction)
    vg = {b["name"]: obj.vertex_groups.new(name=b["name"]) for b in bones if b["deform"]}
    idx = 0
    mesh_verts = mesh.vertices
    blend_for = {"hips": 0, "spine": 0, "chest": 0, "shoulder.L": 0, "shoulder.R": 0}
    role_of = {b["name"]: b["role"] for b in bones}
    name_of_parent = {b["name"]: ([x for x in bones if x["role"] == b["parent"]][0]["name"] if b["parent"] else None) for b in bones}
    for bone, parent, rows, pa, pb, color, c in pieces:
        n = sum(len(r) for r in rows)
        axis = pb - pa
        L2 = axis.length_squared or 1.0
        for k in range(n):
            vi = idx + k
            co = mesh_verts[vi].co
            t = max(0.0, min(1.0, (co - pa).dot(axis) / L2))
            w_own = 1.0
            par = name_of_parent[bone]
            if par in vg and role_of[bone] not in blend_for and not role_of[bone].startswith(("foot", "head", "neck")):
                if t < 0.4:
                    x = t / 0.4
                    w_own = 0.5 + 0.5 * (x * x * (3 - 2 * x))
                    vg[par].add([vi], 1.0 - w_own, "REPLACE")
            elif role_of[bone] in ("head", "neck", "foot.L", "foot.R") and par in vg and t < 0.25:
                x = t / 0.25
                w_own = 0.5 + 0.5 * (x * x * (3 - 2 * x))
                vg[par].add([vi], 1.0 - w_own, "REPLACE")
            vg[bone].add([vi], w_own, "REPLACE")
        idx += n
    # texture: a flat-coloured 160x160 atlas, one 32x32 cell per piece (5x5 grid)
    size = 160
    img = bpy.data.images.new(name + "_tex", size, size, alpha=True)
    px = [0.0] * (size * size * 4)
    cmap = {"skin": (0.93, 0.74, 0.58), "cloth": (0.20, 0.50, 0.55), "accent": (0.85, 0.55, 0.15), "boots": (0.18, 0.16, 0.22)}
    for k, v in (colors or {}).items():
        cmap[k] = tuple(v)
    for bone, parent, rows, pa, pb, color, c in pieces:
        x0, y0 = int(c[0] * size), int(c[1] * size)
        col = cmap.get(color, (0.5, 0.5, 0.5))
        for yy in range(32):
            for xx in range(32):
                shade = 0.82 + 0.18 * (1 if (xx // 4 + yy // 4) % 2 == 0 else 0)
                o = ((y0 + yy) * size + (x0 + xx)) * 4
                px[o:o + 4] = [col[0] * shade, col[1] * shade, col[2] * shade, 1.0]
    img.pixels = px
    img.pack()
    mat = bpy.data.materials.new(name + "_mat")
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.interpolation = "Closest"
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    obj.data.materials.append(mat)
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    obj.parent = arm
    for poly in mesh.polygons:
        poly.use_smooth = True
    return obj, img


def main():
    a = args()
    params = json.load(open(a["params"], encoding="utf-8")) if a["params"] else {}
    prop = params.get("proportions", {})
    names = params.get("names", {})
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = 60
    sc.unit_settings.system = "NONE"
    bones = SK.build(prop, names)
    arm = make_armature(a["name"], bones)
    obj, img = make_mesh(a["name"], arm, bones, prop, params.get("colors"))
    meta = {"schema": "geno-fighter-art/1", "fighter": a["name"],
            "roles": {b["name"]: b["role"] for b in bones},
            "costumes": [{"name": "default", "label": "Default"}]}
    arm["geno"] = json.dumps(meta)
    arm["geno_proportions"] = json.dumps({**SK.DEFAULT_PROPORTIONS, **prop})
    if a["actions"]:
        AC.make_actions(arm, bones, {**SK.DEFAULT_PROPORTIONS, **prop}, params.get("actions"))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(a["out"]))
    print("STARTER", a["out"], "bones", len(bones), "verts", len(obj.data.vertices), "actions", len(bpy.data.actions))


main()
