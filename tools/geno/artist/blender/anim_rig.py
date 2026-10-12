"""anim_rig.py - generate an animation control rig over a Geno deform armature (Goku, Falcon, any role-mapped fighter).

The deform armature is the one the game reads: its bone names, hierarchy and rest pose are NEVER changed. This module adds a
SECOND armature object (the control rig, "<Name>Ctrl") and drives the deform bones from it with constraints:

  FK-<bone>      one per deform bone, same rest matrix and hierarchy, Euler rotation. Hand-animate any chain here (spine, fingers, hair...).
  IK arms/legs   IKm-* two-bone solver chain (mechanism), IKo-* carriers that hand the IK result to the deform bones,
                 IK-hand.X / IK-ankle chain targets, IK-pole-*.X pole targets, foot roll (IK-roll.X) with heel/ball pivots.
  switch         custom property "ik" (0 = FK, 1 = IK) on IK-hand.X / IK-foot.X; drivers blend the deform constraints.
  root / COG     FK-<translation bone> is the root control, FK-<hips bone> the centre of gravity (COG).

Rig v2 adds, from the same role table (every piece degrades to "skipped, with the reason" when a chain is missing):
  spaces         IK-hand.X / IK-foot.X (and their poles) have a "space" property (world / root / cog / chest / head) as Child Of
                 constraints with driven influences; set_space() switches it with a pose match, so nothing jumps; keyable.
  spine          IK-chest handle (child of the COG): its rotation is shared equally by the spine bones between hips and chest, ADDED on
                 the FK-spine controls (so FK keeps working); "spine" slider 0..1 on the handle.
  look-at        LK-target in front of the head: head (and neck, half as much) aim at it, added on the FK-neck/head; "look" slider.
  shoulders      the clavicle follows the IK hand (added on FK-shoulder, only while that arm is in IK); "shoulder" slider on IK-hand.X.
generate() prints a report of what each fighter got and stores it on the control object as "geno_report".

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
PREBEND = 0.003     # a limb that is straight at rest gets its IK mechanism elbow/knee nudged this fraction of the limb length toward the pole:
                   # Blender's IK cannot solve a perfectly straight chain (it stays straight and never reaches). The deform bones are unaffected.
SIDES = ("L", "R")
SPACE_ORDER = ("world", "root", "cog", "chest", "head")     # head only offered to hands
SPACE_PROP, SHOULDER_PROP, SPINE_PROP, LOOK_PROP = "space", "shoulder", "spine", "look"
SHOULDER_DEFAULT = 0.35        # how much of the clavicle's aim at the IK hand is applied
LOOK_NECK_SHARE = 0.5          # the neck turns this fraction of what the head does
AXIS_MIN_DOT = 0.8             # an aim bone's nearest local axis must point at least this much along the wanted direction
TRACK = {(0, 1): "TRACK_X", (0, -1): "TRACK_NEGATIVE_X", (1, 1): "TRACK_Y", (1, -1): "TRACK_NEGATIVE_Y",
         (2, 1): "TRACK_Z", (2, -1): "TRACK_NEGATIVE_Z"}

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


def needs_absolute(arm):
    """Retail rigs (Falcon: no role data of its own, JOBJ_n joints) are consumed from absolute poses; see hand_bake.bake_clip."""
    raw = arm.get("geno", "")
    try:
        json.loads(raw)
        return False
    except (TypeError, ValueError):
        return str(raw) in ROLE_TABLES


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


def _set_mode(obj, mode):
    """Put `obj` in `mode` from any context (a panel button runs the operator from the UI, a script from none).

    Makes the object visible and active, runs the mode switch with an explicit override (the operator's own context can name another
    object, or none), and raises a readable error if Blender still refuses.
    """
    if obj.mode == mode:
        return
    try:
        obj.hide_set(False)
    except RuntimeError:
        pass                                         # not in the view layer; the switch below reports it
    obj.hide_viewport = False
    obj.hide_select = False
    view_layer = bpy.context.view_layer
    for other in list(bpy.context.selected_objects):
        if other is not obj:
            other.select_set(False)
    obj.select_set(True)
    view_layer.objects.active = obj
    with bpy.context.temp_override(active_object=obj, object=obj, selected_objects=[obj], selected_editable_objects=[obj]):
        bpy.ops.object.mode_set(mode=mode)
    if obj.mode != mode:
        raise RuntimeError(f"cannot put {obj.name} in {mode} mode (object mode is {obj.mode}); is it in a hidden or excluded collection?")


def _nearest_axis(matrix, direction):
    """(axis index, sign, dot): which local axis of a bone (matrix_local) points most along `direction`."""
    best = (0, 1, -2.0)
    m3 = matrix.to_3x3()
    for i in range(3):
        d = m3.col[i].normalized().dot(direction)
        for sign in (1, -1):
            if sign * d > best[2]:
                best = (i, sign, sign * d)
    return best


def _prop(pb, name, value, lo, hi, text):
    pb[name] = value
    pb.id_properties_ui(name).update(min=lo, max=hi, soft_min=lo, soft_max=hi, description=text)


def _drive(ctrl, struct, path, expr, **variables):
    """Drive struct.path (a constraint's influence) by `expr` of custom properties: name=(control bone, property)."""
    drv = struct.driver_add(path).driver
    drv.type = "SCRIPTED"
    drv.expression = expr
    for name, (bone, prop) in variables.items():
        v = drv.variables.new()
        v.name = name
        v.type = "SINGLE_PROP"
        v.targets[0].id = ctrl
        v.targets[0].data_path = f'pose.bones["{bone}"]["{prop}"]'
    return drv


def _chain_between(bones, top, bottom):
    """Bone names below `top` down to `bottom` inclusive (top excluded); None when `bottom` is not below `top`."""
    out, b = [], bones.get(bottom)
    while b is not None and b.name != top:
        out.append(b.name)
        b = b.parent
    return list(reversed(out)) if b is not None and out else None


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


# ---------------------------------------------------------------- v2 plan: spaces, spine, look-at, shoulders

def space_list(roles, root_fk, kind):
    """[(space name, control bone or None)] a limb's IK controls can follow; duplicates (two roles on one bone) are dropped."""
    out, seen = [("world", None)], set()
    for name in SPACE_ORDER[1:]:
        if name == "head" and kind != "arm":
            continue
        bone = {"root": root_fk[len(FK):] if root_fk else None, "cog": roles.get("hips"), "chest": roles.get("chest"),
                "head": roles.get("head")}[name]
        if bone and bone not in seen:
            seen.add(bone)
            out.append((name, FK + bone))
    return out


def plan_extras(arm, roles, limbs, mats, fwd):
    """What a fighter gets beyond the limbs. Returns (plan, skipped) where skipped maps a feature to the reason it was left out."""
    bones = arm.data.bones
    plan, skipped = {"spine": None, "look": None, "shoulders": {}}, {}
    hips, chest = roles.get("hips"), roles.get("chest")
    chain = _chain_between(bones, hips, chest) if hips and chest else None
    if chain:
        plan["spine"] = {"bones": chain, "handle": "IK-chest", "origin": list(bones[chest].head_local)}
    else:
        skipped["spine"] = "no hips-to-chest bone chain in the role map" if hips and chest else "no hips/chest role"
    head, neck = roles.get("head"), roles.get("neck")
    if not head:
        skipped["look"] = "no head role"
    else:
        height = max(bones[head].head_local.z, 1.0)
        dist = 0.7 * height
        items = []
        for role, bn, share in (("neck", neck, LOOK_NECK_SHARE), ("head", head, 1.0)):
            if not bn or (role == "neck" and bn == head):
                continue
            axis, sign, dot = _nearest_axis(mats[bn], fwd)
            if dot < AXIS_MIN_DOT:
                if role == "head":
                    items = []
                    skipped["look"] = f"head bone {bn} has no local axis along the facing (best {dot:.2f})"
                    break
                continue
            point = bones[bn].head_local + (mats[bn].to_3x3().col[axis].normalized() * sign) * dist
            parent = bones[bn].parent
            items.append({"role": role, "bone": bn, "share": share, "track": TRACK[(axis, sign)], "point": list(point),
                          "mech": f"LKm-{bn}", "helper": f"LKt-{bn}", "parent_fk": (FK + parent.name) if parent else None})
        if items and items[-1]["role"] == "head":
            plan["look"] = {"target": "LK-target", "items": items, "point": items[-1]["point"]}
        elif "look" not in skipped:
            skipped["look"] = "head bone not usable"
    for lb in limbs:
        if lb["kind"] != "arm":
            continue
        side = lb["side"]
        sb = roles.get(f"shoulder.{side}")
        up, hand = lb["chain"][0], lb["chain"][2]
        if not sb or sb == up or not _is_below(bones, up, sb):
            skipped[f"shoulder.{side}"] = "no shoulder/clavicle bone above the upper arm"
            continue
        direction = bones[up].head_local - bones[sb].head_local
        if direction.length < 1e-4:
            skipped[f"shoulder.{side}"] = "shoulder and upper arm start at the same point"
            continue
        axis, sign, dot = _nearest_axis(mats[sb], direction.normalized())
        if dot < AXIS_MIN_DOT:
            skipped[f"shoulder.{side}"] = f"clavicle {sb} has no local axis along it (best {dot:.2f})"
            continue
        reach = (bones[hand].head_local - bones[sb].head_local).length
        point = bones[sb].head_local + (mats[sb].to_3x3().col[axis].normalized() * sign) * reach
        parent = bones[sb].parent
        plan["shoulders"][lb["id"]] = {"bone": sb, "fk": FK + sb, "track": TRACK[(axis, sign)], "point": list(point),
                                       "mech": f"SHm-{side}", "helper": f"SHt-{side}", "parent_fk": (FK + parent.name) if parent else None}
    return plan, skipped


# ---------------------------------------------------------------- generate

def generate(arm, name=None):
    """Build the control rig for deform armature `arm`; returns the control object.

    Works as a script and as a panel operator (see _set_mode); a failure leaves nothing in edit mode.
    """
    if arm is None or arm.type != "ARMATURE":
        raise ValueError("select the deform armature")
    try:
        return _generate(arm, name)
    except Exception:
        ctrl = ctrl_object(arm)
        if ctrl is not None and ctrl.mode != "OBJECT":
            try:
                _set_mode(ctrl, "OBJECT")
            except Exception:  # noqa: BLE001 - keep the original error
                pass
        raise


def _generate(arm, name=None):
    active = bpy.context.view_layer.objects.active
    if bpy.context.mode != "OBJECT" and active is not None:
        _set_mode(active, "OBJECT")
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
    plan, skipped = plan_extras(arm, roles, limbs, mats, fwd)

    _set_mode(ctrl, "EDIT")
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
        straight = bend.length < 0.02 * total          # bind-pose arms/legs are straight to within noise: the bend direction there is meaningless
        if straight:
            bend = fwd.copy() if lb["kind"] == "leg" else -fwd
        pdir = bend.normalized()
        if straight:
            hl = mid + pdir * PREBEND * total          # mechanism elbow only; the deform bones keep their own positions (carriers)
            total = (hl - hu).length + (he - hl).length
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
        tgt_parent = None          # IK targets and poles are parentless: their space is a Child Of switch (SPACE_ORDER)
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
        add(pole, _basis_matrix(pole_pos), max(total * .06, .2), None, col_ik)
        entry["pole"] = pole
        sp = space_list(roles, root_fk, lb["kind"])
        entry.update(space_ctl=[entry["target"] if lb["kind"] == "arm" else entry["foot"], pole], spaces=[n for n, _ in sp],
                     space_bones=[b for _, b in sp], space_default=1 if len(sp) > 1 and sp[1][0] == "root" else 0)
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

    # ---- v2 control bones: chest handle, look-at target, aim mechanisms
    if plan["spine"]:
        sp = plan["spine"]
        add(sp["handle"], _basis_matrix(Vector(sp["origin"])), max(_display_len(bones[roles["chest"]]), .8), FK + hips_role, col_ik)
    if plan["look"]:
        lk = plan["look"]
        add(lk["target"], _basis_matrix(Vector(lk["point"])), 1.0, root_fk, col_ik)
        for it in lk["items"]:
            add(it["mech"], mats[it["bone"]], _display_len(bones[it["bone"]]), it["parent_fk"], col_mech)
            add(it["helper"], _basis_matrix(Vector(it["point"])), .3, lk["target"], col_mech)
    for lid, sh in plan["shoulders"].items():
        add(sh["mech"], mats[sh["bone"]], _display_len(bones[sh["bone"]]), sh["parent_fk"], col_mech)
        add(sh["helper"], _basis_matrix(Vector(sh["point"])), .3, info["limbs"][lid]["target"], col_mech)
    _set_mode(ctrl, "OBJECT")                  # pose bones are editable in object mode; no pose-mode switch (it can fail from a panel operator)

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
        lowp = pbs[entry["ikm"][1]]                      # the elbow/knee is a hinge about its local X (align_roll put X across the bend plane)
        lowp.lock_ik_y = lowp.lock_ik_z = True
        lowp.use_ik_limit_x = True
        lowp.ik_min_x, lowp.ik_max_x = -math.pi, 0.0

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
    _build_spaces(ctrl, chain_info)
    _build_extras_pose(ctrl, arm, plan, info, chain_info)
    info["report"] = report_lines(ctrl, info, plan, skipped)
    ctrl["geno_report"] = "\n".join(info["report"])
    for line in info["report"]:
        print("GENO RIG", line)
    ctrl["geno_limbs"] = json.dumps(info)
    _update()
    for lid in chain_info:
        info["limbs"][lid]["pole_angle"] = calibrate_pole(ctrl, arm, info["limbs"][lid])
    for lid, (lb, entry, end_ctl) in chain_info.items():
        if lb["kind"] == "leg":
            calibrate_roll(ctrl, entry)
    ctrl["geno_limbs"] = json.dumps(info)
    return ctrl


def _build_spaces(ctrl, chain_info):
    """The "space" property and its Child Of constraints on every IK target and pole (world = no constraint)."""
    for lid, (lb, entry, end_ctl) in chain_info.items():
        sw = ctrl.pose.bones[entry["switch"]]
        names = entry["spaces"]
        _prop(sw, SPACE_PROP, entry["space_default"], 0, len(names) - 1,
              "Space the IK control follows: " + ", ".join(f"{i} {n}" for i, n in enumerate(names)) + ". Use the panel buttons: they keep the pose")
        for ctl in entry["space_ctl"]:
            pb = ctrl.pose.bones[ctl]
            for i, (sname, sbone) in enumerate(zip(names, entry["space_bones"])):
                if sbone is None:
                    continue
                c = pb.constraints.new("CHILD_OF")
                c.name = f"GENO_SPACE_{sname}"
                c.target, c.subtarget = ctrl, sbone
                c.inverse_matrix = (ctrl.matrix_world @ ctrl.data.bones[sbone].matrix_local).inverted()     # rest pose: no offset
                _drive(ctrl, c, "influence", f"1.0 if sp == {i} else 0.0", sp=(entry["switch"], SPACE_PROP))


def _style(pb, shape, size, palette):
    pb.custom_shape = _widget("GENO_" + shape, shape)
    pb.use_custom_shape_bone_size = False
    pb.custom_shape_scale_xyz = (size, size, size)
    pb.color.palette = palette
    pb.rotation_mode = "XYZ"


def _add_rotation(ctrl, pb, name, mech, expr, mix, target_space, owner_space, **variables):
    c = pb.constraints.new("COPY_ROTATION")
    c.name = name
    c.target, c.subtarget = ctrl, mech
    c.mix_mode = mix
    c.target_space, c.owner_space = target_space, owner_space
    c.euler_order = "XYZ"
    _drive(ctrl, c, "influence", expr, **variables)
    return c


def _build_extras_pose(ctrl, arm, plan, info, chain_info):
    """Spine handle, look-at and shoulder-follow constraints. All are ADDED on top of the FK controls and are zero at rest."""
    pbs = ctrl.pose.bones
    sp = plan["spine"]
    if sp:
        h = pbs[sp["handle"]]
        _style(h, "circle", 1.3, "THEME01")
        h.lock_location = h.lock_scale = (True, True, True)
        _prop(h, SPINE_PROP, 1.0, 0.0, 1.0, "How much of the chest handle's rotation the spine takes (0 = FK only)")
        n = len(sp["bones"])
        for bn in sp["bones"]:
            _add_rotation(ctrl, pbs[FK + bn], "GENO_SPINE", sp["handle"], f"sp / {n}", "AFTER", "LOCAL", "POSE", sp=(sp["handle"], SPINE_PROP))
        info["spine"] = {"bones": list(sp["bones"]), "handle": sp["handle"], "prop": SPINE_PROP}
    lk = plan["look"]
    if lk:
        t = pbs[lk["target"]]
        _style(t, "sphere", .7, "THEME01")
        t.lock_rotation = t.lock_scale = (True, True, True)
        _prop(t, LOOK_PROP, 0.0, 0.0, 1.0, "Look-at influence: how much the head (and half as much the neck) turns toward LK-target")
        for it in lk["items"]:
            aim = pbs[it["mech"]].constraints.new("DAMPED_TRACK")
            aim.name = "GENO_AIM"
            aim.target, aim.subtarget = ctrl, it["helper"]
            aim.track_axis = it["track"]
            _add_rotation(ctrl, pbs[FK + it["bone"]], "GENO_LOOK", it["mech"], f"lk * {it['share']}", "ADD", "LOCAL", "LOCAL", lk=(lk["target"], LOOK_PROP))
        info["look"] = {"target": lk["target"], "bones": [it["bone"] for it in lk["items"]], "prop": LOOK_PROP}
    for lid, sh in plan["shoulders"].items():
        e = info["limbs"][lid]
        sw = pbs[e["switch"]]
        _prop(sw, SHOULDER_PROP, SHOULDER_DEFAULT, 0.0, 1.0, "How much the clavicle follows this IK hand (raises it when the hand goes overhead); only while the arm is in IK")
        aim = pbs[sh["mech"]].constraints.new("DAMPED_TRACK")
        aim.name = "GENO_AIM"
        aim.target, aim.subtarget = ctrl, sh["helper"]
        aim.track_axis = sh["track"]
        _add_rotation(ctrl, pbs[sh["fk"]], "GENO_SHOULDER", sh["mech"], "sh * ik", "ADD", "LOCAL", "LOCAL",
                      sh=(e["switch"], SHOULDER_PROP), ik=(e["switch"], "ik"))
        e["shoulder"] = {"fk": sh["fk"], "deform": sh["bone"], "prop": SHOULDER_PROP}


def report_lines(ctrl, info, plan, skipped):
    """What this fighter's rig got, one line per feature (also printed by generate and kept in ctrl["geno_report"])."""
    out = [f"{ctrl.name}: " + (", ".join(info["limbs"]) or "no limbs") + " (IK + FK with pole" + ", foot roll on legs)"]
    missing = [i for i in ("arm.L", "arm.R", "leg.L", "leg.R") if i not in info["limbs"]]
    if missing:
        out.append("  limbs skipped: " + ", ".join(missing) + " (incomplete chain in the role map)")
    for lid, e in info["limbs"].items():
        names = e["spaces"]
        out.append(f"  {lid}: spaces {'/'.join(names)} (default {names[e['space_default']]})"
                   + (f"; clavicle {e['shoulder']['deform']} follows the hand" if "shoulder" in e else
                      "; no clavicle follow (" + skipped.get("shoulder." + e["side"], "leg") + ")" if e["kind"] == "arm" else ""))
    if plan["spine"]:
        out.append(f"  spine: handle {plan['spine']['handle']} over {len(plan['spine']['bones'])} bone(s) ({' > '.join(plan['spine']['bones'])}); COG = {FK}{info['cog']}")
    else:
        out.append("  spine: skipped (" + skipped.get("spine", "?") + "); FK controls only")
    if plan["look"]:
        out.append(f"  look-at: {plan['look']['target']} -> " + " + ".join(f"{it['role']} {it['bone']}" for it in plan["look"]["items"]))
    else:
        out.append("  look-at: skipped (" + skipped.get("look", "?") + ")")
    return out


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


def _swivel_error(ctrl, entry, shoulder, axis):
    """Angle (rad) between where the solved elbow/knee bends and where the pole target is, both seen along the shoulder->target axis."""
    perp = lambda v: v - axis * v.dot(axis)
    elbow = pose_matrix(ctrl, entry["ikm"][1]).translation
    pole = pose_matrix(ctrl, entry["pole"]).translation
    a, b = perp(elbow - shoulder), perp(pole - shoulder)
    if a.length < 1e-6 or b.length < 1e-6:
        return math.pi
    return a.angle(b)


def _search_angle(ctrl, entry, con, shoulder, axis):
    best = (9.0, 0.0)
    for deg in range(-180, 180, 15):
        con.pole_angle = math.radians(deg)
        _update()
        err = _swivel_error(ctrl, entry, shoulder, axis)
        if err < best[0]:
            best = (err, math.radians(deg))
    lo = best[1]
    for step in (7.5, 3.75, 1.875, .9375, .4688, .2344):
        for cand in (lo - math.radians(step), lo + math.radians(step)):
            con.pole_angle = cand
            _update()
            err = _swivel_error(ctrl, entry, shoulder, axis)
            if err < best[0]:
                best = (err, cand)
        lo = best[1]
    return best


def calibrate_pole(ctrl, arm, entry):
    """Choose the elbow/knee hinge direction and the IK pole angle.

    The target is pulled in so the limb must bend; the pole angle is the one that bends it toward the pole target. Both hinge
    directions are tried and the one that bends toward the pole AND leaves the chain at rest when the targets are at rest wins.
    (Matching the rest pose alone is ill-conditioned for the nearly straight arms and legs of a fighter's bind pose.)
    """
    low = ctrl.pose.bones[entry["ikm"][1]]
    con = next(c for c in low.constraints if c.type == "IK")
    owner = ctrl.pose.bones[entry["foot"] if entry["kind"] == "leg" else entry["target"]]
    rest_owner = pose_matrix(ctrl, owner.name)
    shoulder = pose_matrix(ctrl, entry["ikm"][0]).translation
    tip = pose_matrix(ctrl, entry["target"]).translation
    results = []
    for limits in ((-math.pi, 0.0), (0.0, math.pi)):
        low.ik_min_x, low.ik_max_x = limits
        set_world(ctrl, entry, owner.name, Matrix.Translation((shoulder - tip) * 0.35) @ rest_owner)       # pull the end 35% of the way in
        axis = (pose_matrix(ctrl, entry["target"]).translation - shoulder).normalized()
        err, angle = _search_angle(ctrl, entry, con, shoulder, axis)
        con.pole_angle = angle
        set_world(ctrl, entry, owner.name, rest_owner)
        drift = _ik_error(ctrl, entry)
        results.append((err + drift, err, drift, angle, limits))
    results.sort(key=lambda r: r[0])
    _, err, drift, angle, limits = results[0]
    low.ik_min_x, low.ik_max_x = limits
    con.pole_angle = angle
    set_world(ctrl, entry, owner.name, rest_owner)
    entry["pole_swivel_error_deg"] = math.degrees(err)
    entry["pole_error"] = drift                                   # drift of the chain from its rest pose with the targets at rest
    entry["hinge_limits"] = list(limits)
    return angle


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
    tag_switch(ctrl)


def tag_switch(ctrl):
    """Setting an ID property from Python does not tell the dependency graph; tag the rig so the "ik" drivers re-evaluate."""
    ctrl.update_tag()
    arm = deform_object(ctrl)
    if arm is not None:
        arm.update_tag()
    _update()


def get_ik(ctrl, limb_id):
    entry = limbs_info(ctrl)["limbs"][limb_id]
    return float(ctrl.pose.bones[entry["switch"]]["ik"])


def _set_matrix(ctrl, name, matrix):
    ctrl.pose.bones[name].matrix = matrix
    _update()


# ---------------------------------------------------------------- spaces

def get_space(ctrl, limb_or_entry):
    entry = limb_or_entry if isinstance(limb_or_entry, dict) else limbs_info(ctrl)["limbs"][limb_or_entry]
    return int(ctrl.pose.bones[entry["switch"]][SPACE_PROP])


def _space_delta(ctrl, entry, index):
    """Armature-space motion of the space bone since rest (identity for world): what the Child Of constraint adds to the control."""
    bone = entry["space_bones"][index]
    if bone is None:
        return Matrix.Identity(4)
    return pose_matrix(ctrl, bone) @ ctrl.data.bones[bone].matrix_local.inverted()


def set_world(ctrl, entry, name, matrix, index=None):
    """Pose control `name` so that it ends up at armature-space `matrix` while following space `index` (default: the current one).

    IK targets and poles are parentless with a Child Of per space, which pb.matrix = ... cannot see; this solves the local basis.
    Controls that are not space controls fall through to the plain setter.
    """
    if name not in entry.get("space_ctl", ()):
        _set_matrix(ctrl, name, matrix)
        return
    _update()
    index = get_space(ctrl, entry) if index is None else index
    rest = ctrl.data.bones[name].matrix_local
    ctrl.pose.bones[name].matrix_basis = rest.inverted() @ _space_delta(ctrl, entry, index).inverted() @ matrix
    _update()


def space_index(entry, space):
    names = entry["spaces"]
    if isinstance(space, str):
        if space not in names:
            raise ValueError(f"limb has no space '{space}' (has {', '.join(names)})")
        return names.index(space)
    return int(space)


def set_space(ctrl, limb_id, space, key=False):
    """Switch a limb's IK target + pole to another space without moving them in the world (so the pose does not jump).

    `space` is a name ("world", "root", "cog", "chest", "head") or an index into the limb's `spaces`. key=True keys the controls and
    the (stepped) "space" value at the current frame; key the frame before switching to hold the old behaviour up to it.
    """
    entry = limbs_info(ctrl)["limbs"][limb_id]
    idx = space_index(entry, space)
    if idx == get_space(ctrl, entry):
        return idx
    _update()
    worlds = {n: pose_matrix(ctrl, n) for n in entry["space_ctl"]}
    ctrl.pose.bones[entry["switch"]][SPACE_PROP] = idx
    tag_switch(ctrl)
    for n in entry["space_ctl"]:
        set_world(ctrl, entry, n, worlds[n], idx)
    tag_switch(ctrl)
    if key:
        key_space(ctrl, entry)
    return idx


def _fcurves(action):
    """All F-curves of an action (Blender 5 keeps them in slot channelbags, older versions on the action)."""
    out = []
    for layer in getattr(action, "layers", ()):
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", ()):
                out.extend(bag.fcurves)
    return out or list(getattr(action, "fcurves", ()))


def key_space(ctrl, entry, frame=None):
    """Key the limb's space-controlled bones and its "space" value (constant interpolation) at `frame` (default: current)."""
    frame = bpy.context.scene.frame_current if frame is None else frame
    for n in entry["space_ctl"]:
        pb = ctrl.pose.bones[n]
        pb.keyframe_insert("location", frame=frame, group=n)
        pb.keyframe_insert("rotation_euler", frame=frame, group=n)
    sw = ctrl.pose.bones[entry["switch"]]
    sw.keyframe_insert(f'["{SPACE_PROP}"]', frame=frame, group=entry["switch"])
    act = ctrl.animation_data.action if ctrl.animation_data else None
    path = f'pose.bones["{entry["switch"]}"]["{SPACE_PROP}"]'
    for fc in (_fcurves(act) if act is not None else ()):
        if fc.data_path == path:
            for kp in fc.keyframe_points:
                kp.interpolation = "CONSTANT"


# ---------------------------------------------------------------- clavicle hold (no shoulder jump when a limb switches FK <-> IK)

def shoulder_hold(ctrl, entry):
    """Remember where the deform clavicle is now; pair with shoulder_restore() after switching the limb's mode."""
    sh = entry.get("shoulder")
    if not sh:
        return None
    _update()
    return pose_matrix(deform_object(ctrl), sh["deform"])


def shoulder_restore(ctrl, entry, held, iters=8):
    """Adjust the FK clavicle control so the deform clavicle is where shoulder_hold() saw it (the follow is added on top of FK)."""
    sh = entry.get("shoulder")
    if not sh or held is None:
        return
    arm = deform_object(ctrl)
    guess = held.copy()                  # what we assign to the FK control; the follow constraint then adds its part on top
    for _ in range(iters):
        _set_matrix(ctrl, sh["fk"], guess)
        cur = pose_matrix(arm, sh["deform"])
        if max(abs(a - b) for r1, r2 in zip(cur, held) for a, b in zip(r1, r2)) < 1e-6:
            return
        guess = held @ cur.inverted() @ guess


def snap_fk_to_ik(ctrl, limb_id):
    """Pose the FK controls of a limb where the IK pose currently puts the deform bones (so switching to FK does not jump)."""
    arm = deform_object(ctrl)
    entry = limbs_info(ctrl)["limbs"][limb_id]
    _update()
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
    set_world(ctrl, entry, owner, fk_end @ rel.inverted())
    # pole: where the FK knee/elbow bends toward
    fk_u, fk_l, fk_e = (pose_matrix(ctrl, n).translation for n in entry["fk"])
    mid = fk_u + (fk_e - fk_u) * ((fk_l - fk_u).dot(fk_e - fk_u) / max((fk_e - fk_u).length_squared, 1e-9))
    bend = fk_l - mid
    total = entry["total"]
    if bend.length >= 0.02 * total:
        pos = fk_l + bend.normalized() * total * .6
        m = Matrix.Translation(pos)
        set_world(ctrl, entry, entry["pole"], m)


def auto_snap_on_switch(ctrl, limb_id, to_ik):
    """Switch a limb to IK (or FK) matching the current pose (the clavicle included: it only follows the hand in IK)."""
    entry = limbs_info(ctrl)["limbs"][limb_id]
    held = shoulder_hold(ctrl, entry)
    if to_ik:
        snap_ik_to_fk(ctrl, limb_id)
        set_ik(ctrl, limb_id, 1.0)
    else:
        snap_fk_to_ik(ctrl, limb_id)
        set_ik(ctrl, limb_id, 0.0)
    shoulder_restore(ctrl, entry, held)


# ---------------------------------------------------------------- bind / mute

def set_bound(arm, bound):
    """Mute (False) or enable (True) the GENO_ constraints on the deform armature, e.g. to look at a converted clip unchanged."""
    for pb in arm.pose.bones:
        for con in pb.constraints:
            if con.name.startswith("GENO_"):
                con.mute = not bound
    _update()
