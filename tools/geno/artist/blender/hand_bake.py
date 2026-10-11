"""hand_bake.py - hand-animate a row on the control rig and bake it to the hand file (Blender side of hand_layer.py).

    new_clip(ctrl, row, mode="layer")        action "hand:<row>" on the control rig, seeded with the converted row (layer) or at rest (replace)
    load_clip(ctrl, doc, row)                re-create the action from the saved hand file (IK work comes back as FK keys)
    bake_clip(ctrl, action, row, mode)       -> (clip dict for hand_layer, report); IK and constraints are evaluated and baked to FK deltas
    save_clip(path, fighter, row, clip)      merge into the hand JSON (atomic, mtime unchanged if nothing changed)

The deform armature is the one the game reads, so the baked values are what the game gets: per frame the deform bones' VISUAL pose (rig
constraints, IK and all) is read, keyed onto a constraint-free throwaway copy of the deform armature, and exported through the same glTF
exporter the Workbench NLA bake uses, so the numbers are in the glTF local frame the converter works in. The same is done for the base
(converted row or rest). The hand file stores the difference (hand_layer.py). bake_clip also checks, per frame, that the baked FK copy
reproduces the rig's pose (position and rotation tolerance below) and that applying the stored delta to the base reproduces the hand pose.
"""
import json
import math
import os
import struct
import tempfile
from pathlib import Path

import bpy
import numpy as np
from mathutils import Euler, Matrix, Quaternion, Vector

from tools.geno.artist.blender import anim_rig as R
from tools.geno.artist.blender import hand_layer as HL

ACTION_PREFIX = "hand:"
POS_TOL = 1e-3          # armature units: baked FK copy vs rig
ROT_TOL = 1e-3          # radians
REPLAY_TOL = 2e-3       # radians: stored delta applied to the base vs the hand pose


# ---------------------------------------------------------------- Blender plumbing

def _curves(action):
    out = []
    for layer in getattr(action, "layers", ()):
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", ()):
                out.extend(bag.fcurves)
    return out or list(getattr(action, "fcurves", ()))


def _bind(owner, action):
    """Assign `action` to an animated datablock's animation_data, bind its slot and match the rotation modes it keys."""
    ad = owner.animation_data_create()
    if ad.action != action:
        ad.action = action
    if getattr(action, "slots", None) and hasattr(ad, "action_slot"):
        ad.action_slot = action.slots[0]
    paths = {c.data_path for c in _curves(action)}
    if owner.type == "ARMATURE":
        for pb in owner.pose.bones:
            if pb.path_from_id("rotation_quaternion") in paths:
                pb.rotation_mode = "QUATERNION"
            elif pb.path_from_id("rotation_euler") in paths and pb.rotation_mode in {"QUATERNION", "AXIS_ANGLE"}:
                pb.rotation_mode = "XYZ"


def _frame(f):
    bpy.context.scene.frame_set(int(f))
    bpy.context.view_layer.update()


def frame_count(action):
    return int(round(action.frame_range[1])) + 1


def converted_action(row):
    return bpy.data.actions.get(row)


def _key(obj, action, data_path, index, group, frames, values):
    fc = action.fcurve_ensure_for_datablock(obj, data_path, index=index, group_name=group)
    fc.keyframe_points.add(len(frames))
    flat = np.empty(2 * len(frames))
    flat[0::2], flat[1::2] = frames, values
    fc.keyframe_points.foreach_set("co", flat)
    for kp in fc.keyframe_points:
        kp.interpolation = "LINEAR"
    fc.update()


def read_visual(arm, n, before=None):
    """Per frame 0..n-1 the deform armature's evaluated pose. Returns {bone: dict(loc (n,3), quat (n,4 wxyz), scl (n,3), mat [n x Matrix])}."""
    bones = arm.data.bones
    out = {b.name: {"loc": np.zeros((n, 3)), "quat": np.zeros((n, 4)), "scl": np.ones((n, 3)), "mat": []} for b in bones}
    rest_rel = {}
    for b in bones:
        rest_rel[b.name] = (b.parent.matrix_local.inverted() @ b.matrix_local if b.parent else b.matrix_local.copy()).inverted()
    prev = {}
    for f in range(n):
        _frame(f)
        if before:
            before(f)
        ev = R.evaluated(arm)
        pm = {b.name: ev.pose.bones[b.name].matrix.copy() for b in bones}
        for b in bones:
            local = pm[b.parent.name].inverted() @ pm[b.name] if b.parent else pm[b.name]
            loc, q, s = (rest_rel[b.name] @ local).decompose()
            if b.name in prev and prev[b.name].dot(q) < 0:
                q = -q
            prev[b.name] = q
            o = out[b.name]
            o["loc"][f], o["quat"][f], o["scl"][f] = loc, q, s
            o["mat"].append(pm[b.name])
    return out


def seed_basis(arm, ctrl, row, mode, n):
    """The base the hand layer is measured from: the converted row's pose basis (layer) or the rest pose (replace)."""
    bones = [b.name for b in arm.data.bones]
    if mode == "replace":
        return {b: {"loc": np.zeros((n, 3)), "quat": np.tile([1., 0, 0, 0], (n, 1)), "scl": np.ones((n, 3))} for b in bones}
    act = converted_action(row)
    if act is None:
        raise ValueError(f"no converted clip named '{row}' to layer over (use mode 'replace' for a new clip)")
    ad = arm.animation_data_create()
    prev_action, prev_slot, use_nla = ad.action, getattr(ad, "action_slot", None), ad.use_nla
    modes = {pb.name: pb.rotation_mode for pb in arm.pose.bones}
    R.set_bound(arm, False)
    try:
        ad.use_nla = False
        _bind(arm, act)
        data = read_visual(arm, n)
    finally:
        ad.action = prev_action
        if prev_slot is not None and hasattr(ad, "action_slot") and prev_action is not None:
            ad.action_slot = prev_slot
        ad.use_nla = use_nla
        for pb in arm.pose.bones:
            pb.rotation_mode = modes[pb.name]
        R.set_bound(arm, True)
    return data


def hand_visual(arm, ctrl, action, n):
    """The deform armature as the rig drives it from `action`."""
    ad = arm.animation_data_create()
    prev_action, prev_slot, use_nla = ad.action, getattr(ad, "action_slot", None), ad.use_nla
    cad = ctrl.animation_data_create()
    ctrl_prev = cad.action
    try:
        ad.action = None
        ad.use_nla = False
        R.set_bound(arm, True)
        _bind(ctrl, action)
        return read_visual(arm, n)
    finally:
        cad.action = ctrl_prev
        ad.action = prev_action
        if prev_slot is not None and hasattr(ad, "action_slot") and prev_action is not None:
            ad.action_slot = prev_slot
        ad.use_nla = use_nla


def write_fk_action(ctrl, name, n, basis):
    """Key the FK controls with deform pose-basis values (they share rest matrices with the deform bones, so basis == FK basis)."""
    old = bpy.data.actions.get(name)
    if old is not None:
        for owner in (ctrl,):
            if owner.animation_data and owner.animation_data.action == old:
                owner.animation_data.action = None
        bpy.data.actions.remove(old)
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    ctrl.animation_data_create().action = act
    frames = np.arange(n, dtype=float)
    for pb in ctrl.pose.bones:
        if not pb.name.startswith(R.FK):
            continue
        d = basis.get(pb.name[len(R.FK):])
        if d is None:
            continue
        eul = np.zeros((n, 3))
        prev = Euler((0, 0, 0))
        for i in range(n):
            e = Quaternion(d["quat"][i]).to_euler("XYZ", prev)
            eul[i] = e
            prev = e
        base = f'pose.bones["{pb.name}"].'
        for k in range(3):
            _key(ctrl, act, base + "rotation_euler", k, pb.name, frames, eul[:, k])
            _key(ctrl, act, base + "location", k, pb.name, frames, d["loc"][:, k])
    bpy.context.scene.frame_start, bpy.context.scene.frame_end = 0, max(n - 1, 1)
    return act


# ---------------------------------------------------------------- glTF round trip

def read_glb(path, animation=None):
    """The named (default first) animation of a .glb -> {node name: {"rotation": (n,4) xyzw, "translation": (n,3), "scale": (n,3)}}."""
    data = Path(path).read_bytes()
    off, doc, blob = 12, None, b""
    while off < len(data):
        size, kind = struct.unpack_from("<II", data, off)
        chunk = data[off + 8: off + 8 + size]
        off += 8 + size
        if kind == 0x4E4F534A:
            doc = json.loads(chunk)
        elif kind == 0x004E4942:
            blob = chunk
    width = {"SCALAR": 1, "VEC3": 3, "VEC4": 4}

    def accessor(i):
        a = doc["accessors"][i]
        view = doc["bufferViews"][a["bufferView"]]
        start = view.get("byteOffset", 0) + a.get("byteOffset", 0)
        k = width[a["type"]]
        return np.frombuffer(blob, dtype="<f4", count=a["count"] * k, offset=start).reshape(a["count"], k).astype(float)

    out = {}
    anim = doc["animations"][0] if animation is None else next(a for a in doc["animations"] if a.get("name") == animation)
    for ch in anim["channels"]:
        name = doc["nodes"][ch["target"]["node"]]["name"]
        out.setdefault(name, {})[ch["target"]["path"]] = accessor(anim["samplers"][ch["sampler"]]["output"])
    return out


def _clone_with_basis(arm, basis, n):
    """Constraint-free throwaway copy of the deform armature keyed with `basis` (loc, wxyz quat, scl per frame)."""
    clone = arm.copy()
    clone.name = arm.name + "_bake"
    clone.animation_data_clear()
    for coll in arm.users_collection:
        coll.objects.link(clone)
    for pb in clone.pose.bones:
        for c in list(pb.constraints):
            pb.constraints.remove(c)
        pb.rotation_mode = "QUATERNION"
    act = bpy.data.actions.new("hand_bake_tmp")
    clone.animation_data_create().action = act
    frames = np.arange(n, dtype=float)
    for pb in clone.pose.bones:
        d = basis[pb.name]
        base = f'pose.bones["{pb.name}"].'
        for k in range(3):
            _key(clone, act, base + "location", k, pb.name, frames, d["loc"][:, k])
            _key(clone, act, base + "scale", k, pb.name, frames, d["scl"][:, k])
        for k in range(4):
            _key(clone, act, base + "rotation_quaternion", k, pb.name, frames, d["quat"][:, k])
    return clone, act


def _export_arrays(arm, basis, n, workdir, tag):
    clone, act = _clone_with_basis(arm, basis, n)
    scene = bpy.context.scene
    fps = scene.render.fps, scene.render.fps_base
    start, end = scene.frame_start, scene.frame_end
    glb = Path(workdir) / f"{tag}.glb"
    selected, active = list(bpy.context.selected_objects), bpy.context.view_layer.objects.active
    try:
        scene.frame_start, scene.frame_end = 0, n - 1
        for o in list(bpy.context.selected_objects):
            o.select_set(False)
        clone.select_set(True)
        bpy.context.view_layer.objects.active = clone
        bpy.ops.export_scene.gltf(
            filepath=str(glb), export_format="GLB", use_selection=True, export_extras=False, export_yup=True, export_apply=False,
            export_animations=True, export_animation_mode="ACTIVE_ACTIONS", export_force_sampling=True,
            export_optimize_animation_size=False, export_frame_range=False, export_skins=False, export_leaf_bone=False,
            export_def_bones=False, export_reset_pose_bones=False, export_anim_slide_to_zero=False)
        arrays = read_glb(glb)
        # matrices of the constraint-free copy, for the bake-vs-rig check
        clone_mats = {pb.name: [] for pb in clone.pose.bones}
        for f in range(n):
            _frame(f)
            ev = R.evaluated(clone)
            for pb in clone.pose.bones:
                clone_mats[pb.name].append(ev.pose.bones[pb.name].matrix.copy())
    finally:
        scene.render.fps, scene.render.fps_base = fps
        scene.frame_start, scene.frame_end = start, end
        data = clone.data
        bpy.data.objects.remove(clone, do_unlink=True)
        bpy.data.actions.remove(act)
        for o in list(bpy.context.selected_objects):
            o.select_set(False)
        for o in selected:
            if o.name in bpy.data.objects:
                o.select_set(True)
        bpy.context.view_layer.objects.active = active if active and active.name in bpy.data.objects else None
    return arrays, clone_mats


# ---------------------------------------------------------------- bake

def _canon(q):
    q = np.asarray(q, float)
    return np.where(q[..., 3:4] < 0, -q, q)


def _qmul(a, b):
    """Hamilton product of xyzw quaternion arrays (n, 4)."""
    ax, ay, az, aw = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    bx, by, bz, bw = b[..., 0], b[..., 1], b[..., 2], b[..., 3]
    return np.stack([aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
                     aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz], axis=-1)


def _qinv(q):
    return np.concatenate([-q[..., :3], q[..., 3:]], axis=-1)


def _qangle(q):
    return 2 * np.arctan2(np.linalg.norm(q[..., :3], axis=-1), np.abs(q[..., 3]))


def bake_clip(ctrl, action, row, mode="layer", note="", workdir=None, check=True):
    """Bake `action` (on the control rig) into a hand_layer clip dict. Returns (clip, report); raises ValueError if the bake disagrees with the rig."""
    arm = R.deform_object(ctrl)
    n = max(frame_count(action), 2)
    prior = {"frame": bpy.context.scene.frame_current, "ctrl": ctrl.animation_data.action if ctrl.animation_data else None}
    own = workdir is None
    workdir = workdir or tempfile.mkdtemp(prefix="hand_bake_")
    try:
        hand = hand_visual(arm, ctrl, action, n)
        seed = seed_basis(arm, ctrl, row, mode, n)
        ha, hmats = _export_arrays(arm, hand, n, workdir, "hand")
        sa, _ = _export_arrays(arm, seed, n, workdir, "seed")
    finally:
        _frame(prior["frame"])
    rot, loc, auth = {}, {}, {}
    worst_replay = 0.0
    for b in arm.data.bones:
        name = b.name
        if name not in ha or "rotation" not in ha[name]:
            continue
        qh, qs = _canon(ha[name]["rotation"]), _canon(sa[name]["rotation"])
        d = _canon(_qmul(_qinv(qs), qh))
        rot[name] = d
        if "translation" in ha[name]:
            loc[name] = ha[name]["translation"] - sa[name]["translation"]
        # the stored delta must put the base back on the hand pose
        again = _qmul(qs, np.round(d, 6))
        worst_replay = max(worst_replay, float(np.max(_qangle(_qmul(_qinv(again), qh)))))
    bones = HL.sparse_bones(rot, loc)
    for name in bones:
        dq = [Quaternion(seed[name]["quat"][i]).inverted() @ Quaternion(hand[name]["quat"][i]) for i in range(n)]
        dl = hand[name]["loc"] - seed[name]["loc"]
        auth[name] = {"dq": [[round(v, 6) for v in q] for q in dq], "dl": [[round(float(v), 6) for v in r] for r in dl]}
    clip = {"mode": mode, "frames": n, "bones": bones, "auth": auth}
    if note:
        clip["note"] = note
    # bake vs rig
    pos_err = rot_err = 0.0
    for name, mats in hmats.items():
        for f in range(n):
            a, b = hand[name]["mat"][f], mats[f]
            pos_err = max(pos_err, (a.translation - b.translation).length)
            rot_err = max(rot_err, Quaternion(a.to_quaternion()).rotation_difference(b.to_quaternion()).angle)
    report = {"row": row, "mode": mode, "frames": n, "bones_stored": len(bones), "max_pos_err": pos_err, "max_rot_err_rad": rot_err,
              "max_replay_err_rad": worst_replay, "moved_bones": sorted(bones)}
    if check and (pos_err > POS_TOL or rot_err > ROT_TOL or worst_replay > REPLAY_TOL):
        raise ValueError(f"bake of {row} disagrees with the rig: pos {pos_err:.5f}, rot {rot_err:.5f}, replay {worst_replay:.5f}")
    return clip, report


def save_clip(path, fighter, row, clip, fps=60):
    doc = HL.load(path) or HL.empty(fighter, fps)
    doc["clips"][row] = clip
    return HL.save(path, doc)


def delete_clip(path, row):
    doc = HL.load(path)
    if doc and row in doc["clips"]:
        del doc["clips"][row]
        HL.save(path, doc)
        return True
    return False


# ---------------------------------------------------------------- authoring entry points

def new_clip(ctrl, row, mode="layer", frames=None):
    """Start (or restart) the hand action for `row` on the control rig. layer: seeded from the converted row; replace: rest pose."""
    arm = R.deform_object(ctrl)
    if len(row) > 31:
        raise ValueError("row name too long (31)")
    conv = converted_action(row)
    n = frames or (frame_count(conv) if conv else 30)
    basis = seed_basis(arm, ctrl, row, mode, n)
    act = write_fk_action(ctrl, ACTION_PREFIX + row, n, basis)
    act["geno_hand_row"], act["geno_hand_mode"] = row, mode
    _focus(arm, ctrl, act)
    return act


def load_clip(ctrl, doc, row):
    """Re-create the editable action from the hand file: base + the stored Blender-basis deltas, as FK keys."""
    clip = doc["clips"][row]
    arm = R.deform_object(ctrl)
    n = clip["frames"]
    basis = seed_basis(arm, ctrl, row, clip["mode"], n)
    for name, a in clip.get("auth", {}).items():
        if name not in basis:
            continue
        d = basis[name]
        dq = np.asarray(a["dq"], float)
        for i in range(n):
            d["quat"][i] = np.array(Quaternion(d["quat"][i]) @ Quaternion(dq[i]))
        d["loc"] = d["loc"] + np.asarray(a["dl"], float)
    act = write_fk_action(ctrl, ACTION_PREFIX + row, n, basis)
    act["geno_hand_row"], act["geno_hand_mode"] = row, clip["mode"]
    _focus(arm, ctrl, act)
    return act


def _focus(arm, ctrl, act):
    """Show the rig playing `act`; the deform armature follows through its constraints (its own action is cleared, remembered)."""
    ad = arm.animation_data_create()
    if ad.action is not None:
        arm["geno_prev_action"] = ad.action.name
        ad.action = None
    R.set_bound(arm, True)
    _bind(ctrl, act)
    _frame(0)


# ---------------------------------------------------------------- FK <-> IK baking over the whole clip

def _limb_channels(ctrl, entry, ik):
    """[(pose bone name, data path)] that make up one limb's IK controls (ik=True) or FK controls (False)."""
    if ik:
        names = [entry["foot"] if entry["kind"] == "leg" else entry["target"], entry["pole"]]
        if entry["kind"] == "leg":
            names.append(entry["roll"])
        out = [(n, "location") for n in names] + [(n, "rotation_euler") for n in names[:1]]
        return out + ([(entry["roll"], "rotation_euler")] if entry["kind"] == "leg" else [])
    names = list(entry["fk"])
    if entry["kind"] == "leg" and len(entry["ik_deform"]) > 3:
        names.append(R.FK + entry["ik_deform"][3])
    return [(n, "rotation_euler") for n in names] + [(n, "location") for n in names[:1]]


def limb_switch(ctrl, limb_id, to_ik, frames=None):
    """Bake a limb from FK to IK (or back) on every frame of the playing hand action, so the animator can then edit the other mode.

    Pass 1 reads each frame's pose in the current mode and snaps the other mode's controls onto it; pass 2 keys those controls and
    the limb's "ik" switch (1 = IK, 0 = FK) on every frame.
    """
    entry = R.limbs_info(ctrl)["limbs"][limb_id]
    act = ctrl.animation_data.action
    n = frames or frame_count(act)
    switch = ctrl.pose.bones[entry["switch"]]
    R.set_ik(ctrl, limb_id, 0.0 if to_ik else 1.0)
    keep = bpy.context.scene.frame_current
    channels = _limb_channels(ctrl, entry, to_ik)
    names = sorted({c[0] for c in channels})
    poses = []
    for f in range(n):
        _frame(f)
        R.set_ik(ctrl, limb_id, 0.0 if to_ik else 1.0)
        (R.snap_ik_to_fk if to_ik else R.snap_fk_to_ik)(ctrl, limb_id)
        poses.append({nm: (ctrl.pose.bones[nm].location.copy(), ctrl.pose.bones[nm].rotation_euler.copy()) for nm in names})
    for f in range(n):
        _frame(f)
        for nm in names:
            pb = ctrl.pose.bones[nm]
            pb.location, pb.rotation_euler = poses[f][nm]
        for nm, path in channels:
            ctrl.pose.bones[nm].keyframe_insert(path, frame=f, group=nm)
        switch["ik"] = 1.0 if to_ik else 0.0
        switch.keyframe_insert('["ik"]', frame=f, group=entry["switch"])
    R.tag_switch(ctrl)
    _frame(keep)
    return n
