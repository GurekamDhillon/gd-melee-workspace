"""export_fighter.py - preflight a Blender project and export the glb the Geno importer wants (with the settings that matter).

    blender -b my_fighter.blend --python tools/geno/artist/blender/export_fighter.py -- --out art/my_fighter.glb [--no-export]

Prints one line per finding:  GENO <BLOCKER|WARNING|INFO> <CODE> <where>: <message> | fix: <how>
and exits 1 on a blocker (nothing is exported). Next to the glb it writes <glb>.geno.json (roles, costumes, per-action hit frames, loop
and root-motion flags): the importer reads it, so fighter.json stays tiny. The same functions back the "Geno" panel (geno_panel.py).
"""
import json
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
for p in (ROOT, HERE):
    if p not in sys.path:
        sys.path.insert(0, p)
from tools.geno.artist import spec  # noqa: E402  (pure python)

OUT = []


def add(sev, code, where, msg, fix=""):
    OUT.append((sev, code, where, msg, fix))


def find_armature():
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    tagged = [o for o in arms if "geno" in o.keys()]
    if len(tagged) == 1:
        return tagged[0]
    if len(arms) == 1:
        return arms[0]
    return None


def meta_of(arm):
    try:
        return json.loads(arm["geno"]) if "geno" in arm.keys() else {}
    except ValueError:
        return {}


def preflight(arm=None):
    del OUT[:]
    arm = arm or find_armature()
    if arm is None:
        add("BLOCKER", "NO_ARMATURE", "scene", "need exactly one armature (or exactly one tagged with the `geno` custom property); found %d" % len([o for o in bpy.data.objects if o.type == "ARMATURE"]),
            "delete helper/control armatures from the file, or bake the control rig onto the export skeleton (docs/geno-artist-spec.md section 8)")
        return None
    meta = meta_of(arm)
    roles = dict(meta.get("roles", {}))
    bone_names = {b.name for b in arm.data.bones}
    for bn in list(roles):
        if bn not in bone_names:
            add("WARNING", "ROLE_BONE", "armature '%s'" % arm.name, "role table names bone '%s', which does not exist" % bn, "rename the bone back or update the role table")
    have = set(roles.values()) | {b for b in bone_names if b in spec.ALL_ROLES}
    for r in spec.REQUIRED:
        if r not in have:
            guess = [b.name for b in arm.data.bones if spec.guess_role(b.name) == r]
            add("BLOCKER", "ROLE_MISSING", "role '%s'" % r, "no bone has this role", "Geno panel > Roles, or add it to the armature `geno` roles%s" % (" (candidate: %s)" % ", ".join(guess) if guess else ""))
    if len(arm.data.bones) + 2 > spec.LIMITS["max_joints_engine"]:
        add("BLOCKER", "BONE_COUNT", "armature '%s'" % arm.name, "%d bones; the engine holds 256 joints (3 are synthesized)" % len(arm.data.bones), "export only the deform skeleton")
    for ob in (arm,):
        if ob.parent is not None:
            add("BLOCKER", "ARMATURE_PARENT", "object '%s'" % ob.name, "the armature is parented to '%s'" % ob.parent.name, "clear the parent (Alt+P, Clear and Keep Transformation)")
        sc = ob.scale
        if max(abs(sc.x - 1), abs(sc.y - 1), abs(sc.z - 1)) > 1e-4 or max(abs(a) for a in ob.rotation_euler) > 1e-4 or ob.location.length > 1e-4:
            add("BLOCKER", "OBJECT_TRANSFORM", "object '%s'" % ob.name, "unapplied transform loc=%s rot=%s scale=%s" % (tuple(round(x, 3) for x in ob.location), tuple(round(math.degrees(a), 1) for a in ob.rotation_euler), tuple(round(x, 3) for x in sc)),
                "Object > Apply > All Transforms (with the armature and its meshes selected)")
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers)]
    others = [o for o in bpy.data.objects if o.type == "MESH" and o not in meshes]
    for o in others:
        add("WARNING", "MESH_NOT_SKINNED", "object '%s'" % o.name, "mesh without an Armature modifier on '%s': it is not exported" % arm.name, "add the modifier and weights, or ignore (props)")
    if len(meshes) != 1:
        add("BLOCKER", "MESH_COUNT", "meshes", "%d skinned meshes (%s); the converter builds ONE piece" % (len(meshes), ", ".join(o.name for o in meshes)), "join them: select all, Ctrl+J")
    for o in meshes:
        me = o.data
        sc = o.scale
        if max(abs(sc.x - 1), abs(sc.y - 1), abs(sc.z - 1)) > 1e-4 or max(abs(a) for a in o.rotation_euler) > 1e-4 or o.location.length > 1e-4:
            add("BLOCKER", "OBJECT_TRANSFORM", "object '%s'" % o.name, "unapplied transform", "Object > Apply > All Transforms")
        for m in o.modifiers:
            if m.type != "ARMATURE":
                add("BLOCKER", "MODIFIER", "object '%s'" % o.name, "modifier '%s' (%s) is not applied; the export ignores it" % (m.name, m.type), "Object > Apply > Modifier (a Mirror/Subsurf left on shows in Blender but not in the game)")
        if me.shape_keys:
            add("WARNING", "SHAPE_KEYS", "object '%s'" % o.name, "shape keys are not used by the game", "remove them or apply the mix")
        if len(me.materials) != 1:
            add("BLOCKER", "MATERIAL_SLOTS", "object '%s'" % o.name, "%d material slots; need exactly 1 (costumes swap the texture)" % len(me.materials), "merge to one material")
        if not me.uv_layers:
            add("BLOCKER", "NO_UV", "object '%s'" % o.name, "no UV map", "UV > Unwrap")
        gnames = {g.index: g.name for g in o.vertex_groups}
        stray = [g.name for g in o.vertex_groups if g.name not in bone_names]
        if stray:
            add("WARNING", "VGROUP_NO_BONE", "object '%s'" % o.name, "vertex groups without a bone (weights lost): %s" % ", ".join(stray[:6]), "rename the group to its bone's name or delete it")
        over, none_ = [], []
        for v in me.vertices:
            ws = [g.weight for g in v.groups if gnames.get(g.group) in bone_names and g.weight > 1e-6]
            if len(ws) > spec.LIMITS["max_influences"]:
                over.append(v.index)
            elif sum(ws) < 0.99:
                none_.append(v.index)
        if over:
            add("BLOCKER", "INFLUENCES", "object '%s' vertices %s" % (o.name, over[:6] + (["... (%d)" % len(over)] if len(over) > 6 else [])),
                "%d vertices with more than %d bone influences" % (len(over), spec.LIMITS["max_influences"]), "Weight Paint > Weights > Limit Total = 2, then Normalize All")
        if none_:
            add("BLOCKER", "UNWEIGHTED", "object '%s' vertices %s" % (o.name, none_[:6] + (["... (%d)" % len(none_)] if len(none_) > 6 else [])),
                "%d vertices carry no bone weight" % len(none_), "assign them to a deform bone (Edit Mode: select, Ctrl+G > Assign), then Normalize All")
        zs = [v.co.z for v in me.vertices]
        if zs and abs(min(zs)) > 0.5:
            add("WARNING", "SOLES", "object '%s'" % o.name, "lowest vertex is at z=%.2f; the soles should be at z=0" % min(zs), "move the character so its soles are on the ground plane")
        if zs and max(zs) - min(zs) < 6:
            add("WARNING", "SCALE_SMALL", "object '%s'" % o.name, "height %.2f; Melee fighters are 8..20 units (1 unit = 1 Melee unit, not a metre)" % (max(zs) - min(zs)), "scale up and apply")
    toe = next((arm.data.bones[b] for b, r in roles.items() if r == "toe.L" and b in arm.data.bones), None)
    foot = next((arm.data.bones[b] for b, r in roles.items() if r == "foot.L" and b in arm.data.bones), None)
    if toe and foot and toe.head_local.y > foot.head_local.y - 0.05:
        add("WARNING", "FACING", "armature '%s'" % arm.name, "the toe is not in front of the foot along -Y; the character must face -Y in Blender", "rotate the character (and apply) so it faces -Y; left is +X")
    sc = bpy.context.scene
    if sc.render.fps != 60 or sc.render.fps_base != 1.0:
        add("INFO", "FPS", "scene", "scene frame rate is %s/%s; the export sets 60" % (sc.render.fps, sc.render.fps_base))
    acts = [a for a in bpy.data.actions if a.use_fake_user or (arm.animation_data and arm.animation_data.action == a)]
    if not acts:
        add("BLOCKER", "NO_ACTIONS", "file", "no actions", "animate in an action and give it a fake user (shield icon)")
    table = spec.clip_table()["by_name"]
    for a in acts:
        if len(a.name) > spec.LIMITS["max_clip_name"]:
            add("BLOCKER", "CLIP_NAME", "action '%s'" % a.name, "name longer than 31 characters", "rename the action")
        if a.name not in table and not a.get("geno_rows"):
            add("WARNING", "CLIP_UNMAPPED", "action '%s'" % a.name, "not an engine row name and no `geno_rows` custom property: it will not play", "rename it to a row name (docs/geno-artist-checklist.md) or set custom property geno_rows=\"RowA,RowB\"")
        start = a.frame_range[0]
        if abs(start) > 1e-3 and not a.use_frame_range:
            add("INFO", "ACTION_START", "action '%s'" % a.name, "starts at frame %g; the export normalises each action to start at 0" % start)
        keyed = {fc.data_path.split('"')[1] for fc in _fcurves(a) if fc.data_path.startswith("pose.bones[")}
        for k in sorted(keyed - bone_names):
            add("WARNING", "ACTION_BONE", "action '%s'" % a.name, "keys bone '%s', which is not in the armature" % k, "delete those curves (a control rig? bake it: spec section 8)")
    return arm


def _fcurves(a):
    out = []
    try:
        for layer in a.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    out.extend(cb.fcurves)
    except AttributeError:
        out.extend(getattr(a, "fcurves", []))
    return out


def do_export(arm, glb):
    sc = bpy.context.scene
    sc.render.fps, sc.render.fps_base = 60, 1.0
    meta = meta_of(arm)
    meshes = [o for o in bpy.data.objects if o.type == "MESH" and any(m.type == "ARMATURE" and m.object == arm for m in o.modifiers)]
    acts = [a for a in bpy.data.actions if a.use_fake_user or (arm.animation_data and arm.animation_data.action == a)]
    ad = arm.animation_data or arm.animation_data_create()
    for t in list(ad.nla_tracks):
        ad.nla_tracks.remove(t)
    clips = {}
    for a in acts:
        a.use_frame_range = False
        fr = a.frame_range
        n = int(round(fr[1] - fr[0]))
        a.use_frame_range = True
        a.frame_start, a.frame_end = fr[0], fr[1]
        tr = ad.nla_tracks.new()
        tr.name = a.name
        st = tr.strips.new(a.name, int(fr[0]), a)
        try:
            slot = a.slots[0] if len(a.slots) else None
            if slot is not None:
                st.action_slot = slot
        except (AttributeError, RuntimeError):
            pass
        hits = a.get("geno_hit_frames")
        hits = json.loads(hits) if isinstance(hits, str) else list(hits or [])
        hits = [int(h - fr[0]) for h in hits] if hits and min(hits) >= fr[0] and fr[0] != 0 else [int(h) for h in hits]
        for m in getattr(a, "pose_markers", []):
            if m.name.lower().startswith("hit"):
                hits.append(int(m.frame - fr[0]))
        clips[a.name] = {"hit_frames": sorted(set(hits)), "loop": bool(a.get("geno_loop", a.use_cyclic)), "root_motion": bool(a.get("geno_root_motion", False)),
                         "frames": n + 1, "rows": [r for r in str(a.get("geno_rows", "")).replace(" ", "").split(",") if r]}
    ad.action = None
    for pb in arm.pose.bones:
        pb.location, pb.rotation_quaternion, pb.scale = (0, 0, 0), (1, 0, 0, 0), (1, 1, 1)
    bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.object and bpy.context.object.mode != "OBJECT" else None
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    for m in meshes:
        m.select_set(True)
    bpy.context.view_layer.objects.active = arm
    os.makedirs(os.path.dirname(os.path.abspath(glb)), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=glb, export_format="GLB", use_selection=True, export_extras=True, export_yup=True, export_apply=False,
        export_animations=True, export_animation_mode="NLA_TRACKS", export_force_sampling=True, export_optimize_animation_size=False,
        export_frame_range=False, export_skins=True, export_influence_nb=4, export_all_influences=False, export_def_bones=False,
        export_leaf_bone=False, export_materials="EXPORT", export_image_format="AUTO", export_rest_position_armature=True,
        export_anim_slide_to_zero=False, export_reset_pose_bones=True)
    side = {"schema": "geno-fighter-sidecar/1", "fighter": meta.get("fighter", arm.name), "roles": meta.get("roles", {}),
            "costumes": meta.get("costumes", []), "clips": clips}
    if meta.get("hurtboxes"):
        side["hurtboxes"] = meta["hurtboxes"]
    json.dump(side, open(glb + ".geno.json", "w"), indent=1)
    return clips


def report():
    nb = 0
    for sev, code, where, msg, fix in OUT:
        print("GENO %s %s %s: %s%s" % (sev, code, where, msg, (" | fix: " + fix) if fix else ""))
        nb += sev == "BLOCKER"
    return nb


def main():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = a[a.index("--out") + 1] if "--out" in a else None
    arm = preflight()
    nb = report()
    if nb:
        print("GENO STOPPED: %d blocker(s); nothing exported" % nb)
        sys.exit(1)
    if "--no-export" in a or not out:
        print("GENO OK (preflight only)")
        return
    clips = do_export(arm, os.path.abspath(out))
    print("GENO EXPORTED %s (%d actions) + %s.geno.json" % (out, len(clips), out))


if __name__ == "__main__":
    main()
