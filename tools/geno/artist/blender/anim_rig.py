"""anim_rig.py - generate an animation control rig over a Geno deform armature (Goku, Falcon, any role-mapped fighter).

The deform armature is the one the game reads: its bone names, hierarchy and rest pose are NEVER changed. This module adds a
SECOND armature object (the control rig, "<Name>Ctrl") and drives the deform bones from it with constraints:

  FK-<bone>      one per deform bone, same rest matrix and hierarchy, Euler rotation. Hand-animate any chain here (spine, fingers, hair...).
  IK arms/legs   IKm-* two-bone solver chain (mechanism), IKo-* carriers that hand the IK result to the deform bones,
                 IK-hand.X / IK-ankle chain targets, IK-pole-*.X pole targets, foot roll (IK-roll.X) with heel/ball pivots.
  switch         custom property "ik" (0 = FK, 1 = IK) on IK-hand.X / IK-foot.X; drivers blend the deform constraints.
  root / COG     FK-<translation bone> is the root control, FK-<hips bone> the centre of gravity (COG).

Every deform bone gets a "GENO_FK" constraint (copy FK-<bone> in LOCAL space). The IK limb bones also get a "GENO_IK" constraint
(copy the IKo carrier in WORLD space) whose influence is the limb's "ik" property. Both are authoring-only: Workbench export and
hand_bake strip them on a throwaway copy, so the deform armature that is exported keeps zero constraints.

Re-generate any time (after Stage A rewrote goku.blend, or to rebuild a damaged rig): generate() deletes the old control rig and
its constraints first and keeps the deform armature untouched. Rig data is stored on the control object as custom property
"geno_limbs" so snap/switch work without re-deriving anything.

Roles: arm["geno"] JSON {"roles": {bone: role}} (Goku), or ROLE_TABLES (Falcon's retail JOBJ_n skeleton, which has no roles of its own).
"""
import json
import math

import bpy
from mathutils import Matrix, Vector

CTRL_SUFFIX = "Ctrl"
FK, IKM, IKO = "FK-", "IKm-", "IKo-"
SIDES = ("L", "R")

# Falcon's retail skeleton has bones named JOBJ_<joint index> and no role data; indices follow plan_parts.COMMON order
# (…LLegJA LLegJ LKneeJ LFootJA LFootJ…, LShoulderN LShoulderJA LShoulderJ LArmJ LHandN) checked against the rest positions.
ROLE_TABLES = {
    "geno-falcon": {
        "JOBJ_0": "root", "JOBJ_1": "translation", "JOBJ_4": "hips", "JOBJ_18": "spine", "JOBJ_19": "chest", "JOBJ_38": "neck",
        "JOBJ_39": "head",
        "JOBJ_21": "shoulder.L", "JOBJ_23": "upper_arm.L", "JOBJ_24": "lower_arm.L", "JOBJ_25": "hand.L",
        "JOBJ_7": "upper_leg.L", "JOBJ_8": "lower_leg.L", "JOBJ_10": "foot.L", "JOBJ_11": "toe.L",
        "JOBJ_42": "shoulder.R", "JOBJ_45": "upper_arm.R", "JOBJ_46": "lower_arm.R", "JOBJ_47": "hand.R",
        "JOBJ_13": "upper_leg.R", "JOBJ_14": "lower_leg.R", "JOBJ_16": "foot.R", "JOBJ_17": "toe.R",
    },
}


def deform_object(ctrl):
    return bpy.data.objects.get(ctrl.get("geno_deform", ""))


def ctrl_object(arm):
    return bpy.data.objects.get(arm.get("geno_ctrl", ""))


# ---------------------------------------------------------------- roles

def roles_of(arm):
    """{role: bone} for the deform armature."""
    raw = arm.get("geno", "")
    table = {}
    try:
        doc = json.loads(raw)
        table = doc.get("roles", {}) if isinstance(doc, dict) else {}
    except (TypeError, ValueError):
        table = ROLE_TABLES.get(str(raw), {})
    if not table:
        raise ValueError("armature has no roles (arm['geno']); cannot place IK. Roles needed: upper_arm.L/lower_arm.L/hand.L, upper_leg.L/lower_leg.L/foot.L (and .R)")
    names = {b.name for b in arm.data.bones}
    return {role: bone for bone, role in table.items() if bone in names}


def _is_below(bones, child, ancestor):
    b = bones[child]
    while b is not None:
        if b.name == ancestor:
            return True
        b = b.parent
    return False


def limbs_of(arm):
    """[{id, kind, side, chain:[upper, lower, end], toe}] for every complete arm/leg in the role map."""
    roles = roles_of(arm)
    bones = arm.data.bones
    out = []
    for side in SIDES:
        for kind, names in (("arm", ("upper_arm", "lower_arm", "hand")), ("leg", ("upper_leg", "lower_leg", "foot"))):
            chain = [roles.get(f"{n}.{side}") for n in names]
            if not all(chain) or not (_is_below(bones, chain[1], chain[0]) and _is_below(bones, chain[2], chain[1])):
                continue
            out.append({"id": f"{kind}.{side}", "kind": kind, "side": side, "chain": chain, "toe": roles.get(f"toe.{side}")})
    return out


# ---------------------------------------------------------------- helpers

def _update():
    bpy.context.view_layer.update()


def evaluated(obj):
    return obj.evaluated_get(bpy.context.evaluated_depsgraph_get())


def pose_matrix(obj, name):
    """Armature-space pose matrix of a bone as currently evaluated."""
    return evaluated(obj).pose.bones[name].matrix.copy()


def _widget(name, kind):
    coll = bpy.data.collections.get("GENO_RIG_WIDGETS")
    if coll is None:
        coll = bpy.data.collections.new("GENO_RIG_WIDGETS")
        bpy.context.scene.collection.children.link(coll)
        coll.hide_viewport = True
        coll.hide_render = True
    ob = bpy.data.objects.get(name)
    if ob is not None:
        return ob
    verts, edges = [], []

    def ring(plane, n=24):
        base = len(verts)
        for i in range(n):
            a = 2 * math.pi * i / n
            c, s = math.cos(a), math.sin(a)
            verts.append({"xz": (c, 0, s), "xy": (c, s, 0), "yz": (0, c, s)}[plane])
            edges.append((base + i, base + (i + 1) % n))

    if kind == "circle":
        ring("xz")
    elif kind == "sphere":
        ring("xz")
        ring("xy")
        ring("yz")
    elif kind == "cube":
        for x in (-1, 1):
            for y in (-1, 1):
                for z in (-1, 1):
                    verts.append((x * .7, y * .7, z * .7))
        for i in range(8):
            for j in (1, 2, 4):
                if not i & j:
                    edges.append((i, i | j))
    elif kind == "diamond":
        verts.extend([(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)])
        edges.extend([(a, b) for a in range(6) for b in range(a + 1, 6) if a // 2 != b // 2])
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, edges, [])
    ob = bpy.data.objects.new(name, mesh)
    coll.objects.link(ob)
    return ob


def _basis_matrix(origin, x_axis=None):
    """World-aligned rest matrix (bone Y = +Y, identity rotation) at origin, so local axes are the world axes."""
    m = Matrix.Identity(4)
    m.translation = origin
    return m


def _set_edit_matrix(eb, matrix, length):
    eb.matrix = matrix
    eb.length = max(length, 1e-4)


def _display_len(bone):
    if bone.length >= 0.3:
        return bone.length
    kids = [c for c in bone.children if (c.head_local - bone.head_local).length > 0.05]
    return min((c.head_local - bone.head_local).length for c in kids) if kids else 0.5


def remove_rig(arm):
    """Delete the control rig and the constraints it put on the deform armature. The deform bones themselves are not touched."""
    for pb in arm.pose.bones:
        for con in [c for c in pb.constraints if c.name.startswith("GENO_")]:
            pb.constraints.remove(con)
    if arm.animation_data:
        for d in [d for d in arm.animation_data.drivers if "GENO_" in d.data_path]:
            arm.animation_data.drivers.remove(d)
    old = ctrl_object(arm)
    if old is not None:
        data = old.data
        bpy.data.objects.remove(old, do_unlink=True)
        if data.users == 0:
            bpy.data.armatures.remove(data)
    for key in ("geno_ctrl",):
        if key in arm:
            del arm[key]


# ---------------------------------------------------------------- generate

def generate(arm, name=None):
    """Build the control rig for deform armature `arm`; returns the control object."""
    if arm is None or arm.type != "ARMATURE":
        raise ValueError("select the deform armature")
    if bpy.context.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    limbs = limbs_of(arm)
    if not limbs:
        raise ValueError("no complete arm/leg found in the role map")
    remove_rig(arm)
    roles = roles_of(arm)
    bones = arm.data.bones
    mats = {b.name: b.matrix_local.copy() for b in bones}
    name = name or arm.name.replace("Export", "").replace("_skeleton", "") + CTRL_SUFFIX
    data = bpy.data.armatures.new(name)
    ctrl = bpy.data.objects.new(name, data)
    ctrl.matrix_world = arm.matrix_world
    for coll in arm.users_collection:
        coll.objects.link(ctrl)
    ctrl["geno_deform"] = arm.name
    arm["geno_ctrl"] = ctrl.name
    ctrl.show_in_front = True
    data.display_type = "OCTAHEDRAL"
    root_role = roles.get("translation") or roles.get("root")
    hips_role = roles.get("hips")

    # global facing from the feet (the toe lies in front of the ankle); falls back to -Y
    fwd = Vector((0, 0, 0))
    for lb in limbs:
        if lb["kind"] == "leg" and lb["toe"]:
            d = bones[lb["toe"]].head_local - bones[lb["chain"][2]].head_local
            fwd += Vector((d.x, d.y, 0))
    fwd = fwd.normalized() if fwd.length > 1e-4 else Vector((0, -1, 0))
    up = Vector((0, 0, 1))
    lat = up.cross(fwd).normalized()
    info = {"facing": list(fwd), "limbs": {}, "root": root_role, "cog": hips_role}

    bpy.context.view_layer.objects.active = ctrl
    for o in bpy.context.selected_objects:
        o.select_set(False)
    ctrl.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    eds = data.edit_bones
    col_fk = data.collections.new("FK")
    col_ik = data.collections.new("IK")
    col_mech = data.collections.new("Mechanism")
    col_mech.is_visible = False

    def add(bname, matrix, length, parent=None, coll=None):
        eb = eds.new(bname)
        eb.head = (0, 0, 0)
        eb.tail = (0, 0, 1)
        _set_edit_matrix(eb, matrix, length)
        if parent:
            eb.parent = eds[parent]
        if coll is not None:
            coll.assign(eb)
        return eb

    for b in bones:                       # parents first: Armature.bones is in hierarchy order
        add(FK + b.name, mats[b.name], _display_len(b), (FK + b.parent.name) if b.parent else None, col_fk)

    root_fk = FK + root_role if root_role else None
    chain_info = {}
    for lb in limbs:
        u, l_, e = lb["chain"]
        hu, hl, he = (bones[x].head_local.copy() for x in (u, l_, e))
        total = (hl - hu).length + (he - hl).length
        side, lid = lb["side"], lb["id"]
        # pole direction: the bend of the rest pose; a straight limb bends the way a person's does (knees forward, elbows back)
        mid = hu + (he - hu) * ((hl - hu).dot(he - hu) / max((he - hu).length_squared, 1e-9))
        bend = hl - mid
        if bend.length < 0.02 * total:
            bend = fwd.copy() if lb["kind"] == "leg" else -fwd
        pdir = bend.normalized()
        pole_pos = hl + pdir * total * 0.6
        # mechanism chain: geometry-aligned so the IK solver works even when the deform bones are stubs pointing elsewhere
        for nm, head, tail in ((IKM + u, hu, hl), (IKM + l_, hl, he)):
            eb = eds.new(nm)
            eb.head, eb.tail = head, tail
            eb.align_roll(pdir)
            col_mech.assign(eb)
        eds[IKM + l_].parent = eds[IKM + u]
        eds[IKM + l_].use_connect = True
        par = bones[u].parent
        eds[IKM + u].parent = eds[FK + par.name] if par else None
        entry = {"fk": [FK + x for x in lb["chain"]], "ikm": [IKM + u, IKM + l_], "deform": list(lb["chain"]),
                 "pdir": list(pdir), "kind": lb["kind"], "side": side, "total": total}
        tgt_parent = root_fk
        if lb["kind"] == "arm":
            tgt = f"IK-hand.{side}"
            add(tgt, _basis_matrix(he), max(total * .12, .3), tgt_parent, col_ik)
            end_ctl = tgt
            entry.update(target=tgt, switch=tgt)
            carriers = [(u, IKM + u), (l_, IKM + l_), (e, tgt)]
            toe_carrier = None
        else:
            toe = lb["toe"]
            hf = bones[e].head_local
            ht = bones[toe].head_local if toe else hf + fwd * total * .3
            flen = max(Vector((ht.x - hf.x, ht.y - hf.y, 0)).length, 0.5)
            ground = 0.0
            heel = Vector((hf.x, hf.y, ground)) - fwd * flen * .45
            ball = Vector((ht.x, ht.y, ground))
            foot = f"IK-foot.{side}"
            add(foot, _basis_matrix(Vector((hf.x, hf.y, ground))), max(flen * .35, .3), tgt_parent, col_ik)

            def pivot_matrix(origin):
                m = Matrix((lat, up, lat.cross(up))).transposed()      # X = lateral, Y = up
                m = m.to_4x4()
                m.translation = origin
                return m
            heel_n, ball_n, ank_n, roll_n = f"IK-heel.{side}", f"IK-ball.{side}", f"IK-ankle.{side}", f"IK-roll.{side}"
            add(heel_n, pivot_matrix(heel), .5, foot, col_mech)
            add(ball_n, pivot_matrix(ball), .5, heel_n, col_mech)
            add(ank_n, _basis_matrix(he), .3, ball_n, col_mech)
            add(roll_n, pivot_matrix(Vector((ht.x, ht.y, ground)) + fwd * flen * .5), max(flen * .3, .3), foot, col_ik)
            end_ctl = ank_n
            entry.update(target=ank_n, switch=foot, foot=foot, heel=heel_n, ball=ball_n, roll=roll_n, ground=ground)
            carriers = [(u, IKM + u), (l_, IKM + l_), (e, ank_n)]
            toe_carrier = (toe, heel_n) if toe else None
        pole = f"IK-pole-{'knee' if lb['kind'] == 'leg' else 'elbow'}.{side}"
        add(pole, _basis_matrix(pole_pos), max(total * .06, .2), root_fk, col_ik)
        entry["pole"] = pole
        for dn, owner in carriers + ([toe_carrier] if toe_carrier else []):
            eb = eds.new(IKO + dn)
            eb.head, eb.tail = (0, 0, 0), (0, 0, 1)
            _set_edit_matrix(eb, mats[dn], _display_len(bones[dn]))
            eb.parent = eds[owner]
            col_mech.assign(eb)
        entry["carriers"] = [IKO + dn for dn, _ in carriers + ([toe_carrier] if toe_carrier else [])]
        entry["ik_deform"] = [dn for dn, _ in carriers + ([toe_carrier] if toe_carrier else [])]
        chain_info[lid] = (lb, entry, end_ctl)
        info["limbs"][lid] = entry
    bpy.ops.object.mode_set(mode="POSE")

    # ---- pose-bone setup: shapes, colours, rotation mode, constraints
    pbs = ctrl.pose.bones
    for b in bones:
        pb = pbs[FK + b.name]
        pb.rotation_mode = "XYZ"
        sd = _display_len(b)
        pb.custom_shape = _widget("GENO_circle", "circle")
        pb.use_custom_shape_bone_size = False
        r = min(max(sd * .25, .12), .7)
        pb.custom_shape_scale_xyz = (r, r, r)
        pb.custom_shape_rotation_euler = (0, 0, 0)
        pb.color.palette = "THEME04" if ("_L_" in b.name or b.name.endswith(".L")) else "THEME03" if ("_R_" in b.name or b.name.endswith(".R")) else "THEME09"
    if root_fk:
        pbs[root_fk].custom_shape = _widget("GENO_cube", "cube")
        pbs[root_fk].custom_shape_scale_xyz = (1.2, 1.2, 1.2)
        pbs[root_fk].color.palette = "THEME09"
    if hips_role:
        pbs[FK + hips_role].custom_shape = _widget("GENO_sphere", "sphere")
        pbs[FK + hips_role].custom_shape_scale_xyz = (.9, .9, .9)
    for lid, (lb, entry, end_ctl) in chain_info.items():
        for nm, shape, size in ((entry["target"] if lb["kind"] == "arm" else entry["foot"], "cube", .6),
                                (entry["pole"], "diamond", .35)):
            pb = pbs[nm]
            pb.custom_shape = _widget("GENO_" + shape, shape)
            pb.use_custom_shape_bone_size = False
            pb.custom_shape_scale_xyz = (size, size, size)
            pb.color.palette = "THEME01"
            pb.rotation_mode = "XYZ"
        if lb["kind"] == "leg":
            pb = pbs[entry["roll"]]
            pb.custom_shape = _widget("GENO_circle", "circle")
            pb.use_custom_shape_bone_size = False
            pb.custom_shape_scale_xyz = (.5, .5, .5)
            pb.color.palette = "THEME01"
            pb.rotation_mode = "XYZ"
            pb.lock_location = pb.lock_rotation = (True, True, True)
            pb.lock_rotation[0] = False
            pb.lock_scale = (True, True, True)
            for nm, lim in ((entry["heel"], (None, 0.0)), (entry["ball"], (0.0, None))):
                p = pbs[nm]
                p.rotation_mode = "XYZ"
                cr = p.constraints.new("COPY_ROTATION")
                cr.name = "GENO_ROLL"
                cr.target, cr.subtarget = ctrl, entry["roll"]
                cr.use_x, cr.use_y, cr.use_z = True, False, False
                cr.target_space = cr.owner_space = "LOCAL"
                lm = p.constraints.new("LIMIT_ROTATION")
                lm.name = "GENO_ROLL_LIMIT"
                lm.use_limit_x = True
                lm.min_x = lim[0] if lim[0] is not None else -math.pi
                lm.max_x = lim[1] if lim[1] is not None else math.pi
                lm.owner_space = "LOCAL"
        pbs[entry["switch"]]["ik"] = 0.0
        pbs[entry["switch"]].id_properties_ui("ik").update(min=0.0, max=1.0, soft_min=0.0, soft_max=1.0, description="0 = FK, 1 = IK")
        ik = pbs[entry["ikm"][1]].constraints.new("IK")
        ik.name = "GENO_IK_SOLVE"
        ik.target, ik.subtarget = ctrl, end_ctl
        ik.pole_target, ik.pole_subtarget = ctrl, entry["pole"]
        ik.chain_count = 2
        ik.use_tail = True
        ik.use_stretch = False
        entry["pole_angle"] = 0.0

    # ---- deform constraints
    ik_bones = set()
    for lid, (lb, entry, end_ctl) in chain_info.items():
        ik_bones.update(entry["ik_deform"])
    for b in bones:
        pb = arm.pose.bones[b.name]
        for con in [c for c in pb.constraints if c.name.startswith("GENO_")]:
            pb.constraints.remove(con)
        c = pb.constraints.new("COPY_TRANSFORMS")
        c.name = "GENO_FK"
        c.target, c.subtarget = ctrl, FK + b.name
        c.owner_space = c.target_space = "LOCAL"
    for lid, (lb, entry, end_ctl) in chain_info.items():
        for dn, car in zip(entry["ik_deform"], entry["carriers"]):
            pb = arm.pose.bones[dn]
            c = pb.constraints.new("COPY_TRANSFORMS")
            c.name = "GENO_IK"
            c.target, c.subtarget = ctrl, car
            c.owner_space = c.target_space = "WORLD"
            drv = c.driver_add("influence").driver
            drv.type = "AVERAGE"
            v = drv.variables.new()
            v.name = "ik"
            v.type = "SINGLE_PROP"
            v.targets[0].id = ctrl
            v.targets[0].data_path = f'pose.bones["{entry["switch"]}"]["ik"]'
    ctrl["geno_limbs"] = json.dumps(info)
    bpy.ops.object.mode_set(mode="OBJECT")
    _update()
    for lid in chain_info:
        info["limbs"][lid]["pole_angle"] = calibrate_pole(ctrl, arm, info["limbs"][lid])
    for lid, (lb, entry, end_ctl) in chain_info.items():
        if lb["kind"] == "leg":
            calibrate_roll(ctrl, entry)
    ctrl["geno_limbs"] = json.dumps(info)
    return ctrl


def limbs_info(ctrl):
    return json.loads(ctrl["geno_limbs"])


def _ik_error(ctrl, entry):
    """Sum of how far the mechanism chain pose is from its rest pose (the IK at rest must change nothing)."""
    bad = 0.0
    for nm in entry["ikm"]:
        rest = ctrl.data.bones[nm].matrix_local
        cur = pose_matrix(ctrl, nm)
        bad += (cur.translation - rest.translation).length
        bad += sum((cur.to_3x3()[i][j] - rest.to_3x3()[i][j]) ** 2 for i in range(3) for j in range(3))
    return bad


def calibrate_pole(ctrl, arm, entry):
    """Choose the IK pole angle that leaves the mechanism chain at its rest pose when the targets sit at rest."""
    pb = ctrl.pose.bones[entry["ikm"][1]]
    con = next(c for c in pb.constraints if c.type == "IK")
    best = (1e9, 0.0)
    for deg in range(-180, 180, 15):
        con.pole_angle = math.radians(deg)
        _update()
        err = _ik_error(ctrl, entry)
        if err < best[0]:
            best = (err, math.radians(deg))
    lo = best[1]
    for step in (7.5, 3.75, 1.875, .9375, .4688):
        for cand in (lo - math.radians(step), lo + math.radians(step)):
            con.pole_angle = cand
            _update()
            err = _ik_error(ctrl, entry)
            if err < best[0]:
                best = (err, cand)
        lo = best[1]
    con.pole_angle = best[1]
    _update()
    entry["pole_error"] = best[0]
    return best[1]


def calibrate_roll(ctrl, entry):
    """Make positive roll lift the heel (foot rolls onto the ball) regardless of the rig's orientation; returns 1/-1."""
    roll = ctrl.pose.bones[entry["roll"]]
    _update()
    z0 = pose_matrix(ctrl, entry["target"]).translation.z
    roll.rotation_euler[0] = .3
    _update()
    z1 = pose_matrix(ctrl, entry["target"]).translation.z
    roll.rotation_euler[0] = 0
    _update()
    entry["roll_lifts"] = z1 > z0
    return entry["roll_lifts"]


# ---------------------------------------------------------------- switch + snap

def set_ik(ctrl, limb_id, value):
    entry = limbs_info(ctrl)["limbs"][limb_id]
    ctrl.pose.bones[entry["switch"]]["ik"] = float(value)
    _update()


def get_ik(ctrl, limb_id):
    entry = limbs_info(ctrl)["limbs"][limb_id]
    return float(ctrl.pose.bones[entry["switch"]]["ik"])


def _set_matrix(ctrl, name, matrix):
    ctrl.pose.bones[name].matrix = matrix
    _update()


def snap_fk_to_ik(ctrl, limb_id):
    """Pose the FK controls of a limb where the IK pose currently puts the deform bones (so switching to FK does not jump)."""
    arm = deform_object(ctrl)
    entry = limbs_info(ctrl)["limbs"][limb_id]
    targets = {dn: pose_matrix(arm, dn) for dn in entry["ik_deform"]}
    for fk, dn in zip(entry["fk"], entry["deform"]):
        _set_matrix(ctrl, fk, targets[dn])
    if len(entry["ik_deform"]) > 3:
        toe = entry["ik_deform"][3]
        _set_matrix(ctrl, FK + toe, targets[toe])


def snap_ik_to_fk(ctrl, limb_id):
    """Pose the IK targets so the IK limb reproduces the FK pose (so switching to IK does not jump)."""
    arm = deform_object(ctrl)
    entry = limbs_info(ctrl)["limbs"][limb_id]
    fk_end = pose_matrix(ctrl, entry["fk"][2])
    bones = ctrl.data.bones
    carrier = entry["carriers"][2]
    if entry["kind"] == "leg":
        ctrl.pose.bones[entry["roll"]].rotation_euler[0] = 0
        _update()
        owner = entry["foot"]
    else:
        owner = entry["target"]
    rel = bones[owner].matrix_local.inverted() @ bones[carrier].matrix_local     # carrier rest relative to the controlled bone
    _set_matrix(ctrl, owner, fk_end @ rel.inverted())
    # pole: where the FK knee/elbow bends toward
    fk_u, fk_l, fk_e = (pose_matrix(ctrl, n).translation for n in entry["fk"])
    mid = fk_u + (fk_e - fk_u) * ((fk_l - fk_u).dot(fk_e - fk_u) / max((fk_e - fk_u).length_squared, 1e-9))
    bend = fk_l - mid
    total = entry["total"]
    if bend.length >= 0.02 * total:
        pos = fk_l + bend.normalized() * total * .6
        m = Matrix.Translation(pos)
        _set_matrix(ctrl, entry["pole"], m)


def auto_snap_on_switch(ctrl, limb_id, to_ik):
    """Switch a limb to IK (or FK) matching the current pose."""
    if to_ik:
        snap_ik_to_fk(ctrl, limb_id)
        set_ik(ctrl, limb_id, 1.0)
    else:
        snap_fk_to_ik(ctrl, limb_id)
        set_ik(ctrl, limb_id, 0.0)


# ---------------------------------------------------------------- bind / mute

def set_bound(arm, bound):
    """Mute (False) or enable (True) the GENO_ constraints on the deform armature, e.g. to look at a converted clip unchanged."""
    for pb in arm.pose.bones:
        for con in pb.constraints:
            if con.name.startswith("GENO_"):
                con.mute = not bound
    _update()
