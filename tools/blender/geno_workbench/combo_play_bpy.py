"""Play a combo string in the Blender scene (pure preview from clip data and routes; no engine needed).

``build`` lays the string's moves on the fighter's armature as one NLA track, back to back, each cut at the frame its route
to the next move opens (combo_play.plan_string), and adds what makes the cut points readable:

* scene timeline markers ``CANCEL <route> -> <next>`` at each cancel frame and ``ROUTE <input> <name> [lo-hi]`` at each
  route window start (Blender timeline markers have no colour, so the same information is also drawn in space);
* a "Combo String" collection: a ribbon above the fighter, one frame = one step along X.  Row 0 is the moves, the rows
  above are the routes' windows in the input colours (light green, heavy orange, special blue, jump yellow, grab purple,
  shield cyan), white ticks are the cancel frames and a moving playhead follows the scene frame;
* hitbox markers (wire spheres parented to the hitbox's bone, visible only on the frames the source says they are
  active) when ``hitboxes`` is on.  Offsets are not applied: the sphere sits on the joint (the engine overlay, which the
  panel's "Send to game" drives, is exact).

``clear`` removes all of it and restores the armature's own action.  Move frame n of a clip with crop c is action frame c + n.
"""
from __future__ import annotations

import bpy

try:
    from . import combo_play as C
except ImportError:  # run as a plain module in the tests
    import combo_play as C

TRACK = "Combo string"
COLLECTION = "Combo String"
OWNED = "_geno_combo"
PREV_ACTION = "geno_combo_prev_action"
SOLO = "geno_combo_prev_solo"
FRAME_W = 0.04          # metres per string frame in the ribbon
ROW_H = 0.06
MARKER_PREFIXES = (C.CANCEL_PREFIX, C.ROUTE_PREFIX)


def find_armature(scene, name=None):
    if name and name in bpy.data.objects:
        return bpy.data.objects[name]
    active = bpy.context.view_layer.objects.active if bpy.context.view_layer else None
    if active is not None and active.type == "ARMATURE":
        return active
    best = None
    for obj in scene.objects:
        if obj.type == "ARMATURE":
            if "geno_deform" not in obj and best is None:
                best = obj
    return best


def height_of(arm):
    """The fighter's height in scene units (highest bone head above the armature origin); the ribbon scales with it."""
    zs = [(arm.matrix_world @ b.head_local).z for b in arm.data.bones] or [1.0]
    return max(max(zs) - min(0.0, min(zs)), 0.5)


def scale_of(arm):
    """Ribbon scale: 1.0 for a 1.8 m fighter, bigger for a model in game units (Melee fighters are ~16 units tall)."""
    return height_of(arm) / 1.8


def _collection(scene):
    col = bpy.data.collections.get(COLLECTION)
    if col is None:
        col = bpy.data.collections.new(COLLECTION)
        col[OWNED] = True
    if col.name not in [c.name for c in scene.collection.children]:
        scene.collection.children.link(col)
    return col


def _emission(name, rgb, alpha=1.0):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        for n in list(nodes):
            nodes.remove(n)
        out = nodes.new("ShaderNodeOutputMaterial")
        em = nodes.new("ShaderNodeEmission")
        em.inputs["Color"].default_value = (*rgb, 1.0)
        em.inputs["Strength"].default_value = 1.0
        if alpha < 1.0:
            clear = nodes.new("ShaderNodeBsdfTransparent")
            mix = nodes.new("ShaderNodeMixShader")
            mix.inputs["Fac"].default_value = alpha
            mat.node_tree.links.new(clear.outputs["BSDF"], mix.inputs[1])
            mat.node_tree.links.new(em.outputs["Emission"], mix.inputs[2])
            mat.node_tree.links.new(mix.outputs["Shader"], out.inputs["Surface"])
            try:
                mat.surface_render_method = "BLENDED"
            except (AttributeError, TypeError):
                mat.blend_method = "BLEND"
        else:
            mat.node_tree.links.new(em.outputs["Emission"], out.inputs["Surface"])
        mat.diffuse_color = (*rgb, 1.0)
        mat[OWNED] = True
    return mat


def _quads_object(col, name, quads, rgb, origin):
    """One mesh of rectangles (x0, x1, z0, z1) in the ribbon's plane, in one emission material."""
    verts, faces = [], []
    for (x0, x1, z0, z1) in quads:
        base = len(verts)
        verts += [(x0, 0.0, z0), (x1, 0.0, z0), (x1, 0.0, z1), (x0, 0.0, z1)]
        faces.append((base, base + 1, base + 2, base + 3))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    mesh.materials.append(_emission("Combo." + name, rgb))
    obj = bpy.data.objects.new(name, mesh)
    obj.location = origin
    obj.color = (*rgb, 1.0)
    obj[OWNED] = True
    col.objects.link(obj)
    return obj


def ribbon(scene, arm, plan, routes, col):
    """The coloured string ribbon; returns the objects."""
    total = C.total_frames(plan)
    k = scale_of(arm)
    fw, rh = FRAME_W * k, ROW_H * k
    origin = (arm.location.x - total * fw / 2, arm.location.y + 0.5 * k, arm.location.z + height_of(arm) + 0.35 * k)
    objs = []
    moves = [((seg["start"] - 1) * fw, (seg["start"] - 1 + seg["cut"]) * fw - 0.004 * k, 0.0, rh * 0.9) for seg in plan]
    objs.append(_quads_object(col, "Combo.moves", moves, (0.25, 0.27, 0.32), origin))
    by_input: dict[str, list] = {}
    for i, seg in enumerate(plan):
        last = seg["start"] + seg["cut"] - 1
        row = 0
        for route in routes:
            if seg["move"] not in C.sources(route) and "*" not in C.sources(route):
                continue
            lo, hi = C.window(route)
            first = max(seg["start"] + lo - 1, seg["start"])
            end = last if hi == 0 else min(seg["start"] + hi - 1, last)
            row += 1
            if end < first:
                continue
            z = row * rh
            by_input.setdefault(C.input_class(route), []).append(((first - 1) * fw, end * fw - 0.004 * k, z, z + rh * 0.8))
    for name, quads in by_input.items():
        objs.append(_quads_object(col, "Combo.route." + name, quads, C.INPUT_COLOURS[name], origin))
    ticks = [((seg["cancel_frame"]) * fw - 0.006 * k, seg["cancel_frame"] * fw + 0.006 * k, -rh * 0.3, rh * 7) for seg in plan if seg["linked"]]
    if ticks:
        objs.append(_quads_object(col, "Combo.cancel", ticks, (1.0, 1.0, 1.0), origin))
    head = _quads_object(col, "Combo.playhead", [(-0.006 * k, 0.006 * k, -rh * 0.5, rh * 7.5)], (1.0, 0.25, 0.2), origin)
    head.location.x = origin[0]
    head.keyframe_insert("location", index=0, frame=1)
    head.location.x = origin[0] + (total - 1) * fw
    head.keyframe_insert("location", index=0, frame=total)
    action = head.animation_data.action
    for fc in _fcurves(action):
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    objs.append(head)
    return objs


def _fcurves(action):
    try:
        return list(action.fcurves)
    except AttributeError:   # layered actions (Blender 4.4+)
        out = []
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    out.extend(bag.fcurves)
        return out


def _sphere_mesh():
    mesh = bpy.data.meshes.get("Combo.hit.sphere")
    if mesh is None:
        import bmesh
        mesh = bpy.data.meshes.new("Combo.hit.sphere")
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)
        bm.to_mesh(mesh)
        bm.free()
    return mesh


def hit_spheres(scene, arm, windows, col, unit):
    """A sphere per hitbox window, on its bone, visible only while active.  Returns (objects, missing bones)."""
    objs, missing = [], []
    bones = arm.data.bones
    for k, win in enumerate(windows):
        bone = win["bone"]
        if bone not in bones:
            missing.append(bone or "?")
            continue
        obj = bpy.data.objects.new("Combo.hit.%d.%d" % (win["segment"], win["slot"]), _sphere_mesh())
        obj.scale = (max(0.02, win["size"] * unit),) * 3
        obj.display_type = "WIRE"
        obj.data.materials.clear()
        obj.data.materials.append(_emission("Combo.hit", (1.0, 0.2, 0.15), 0.4))
        obj.parent, obj.parent_type, obj.parent_bone = arm, "BONE", bone
        obj.location = (0.0, -bones[bone].length, 0.0)       # a bone's children sit at its tail: put it back on the joint
        obj.color = (1.0, 0.25, 0.2, 1.0)
        obj[OWNED] = True
        col.objects.link(obj)
        for hide in (True,):
            obj.hide_viewport = obj.hide_render = hide
        for frame, state in ((1, True), (win["first"], False), (win["last"] + 1, True)):
            obj.hide_viewport = obj.hide_render = state
            obj.keyframe_insert("hide_viewport", frame=frame)
            obj.keyframe_insert("hide_render", frame=frame)
        if obj.animation_data and obj.animation_data.action:
            for fc in _fcurves(obj.animation_data.action):
                for kp in fc.keyframe_points:
                    kp.interpolation = "CONSTANT"
        objs.append(obj)
    return objs, missing


def clear(scene, arm=None):
    arm = arm or find_armature(scene)
    removed = {"markers": 0, "objects": 0, "track": False}
    for m in list(scene.timeline_markers):
        if m.name.startswith(MARKER_PREFIXES):
            scene.timeline_markers.remove(m)
            removed["markers"] += 1
    col = bpy.data.collections.get(COLLECTION)
    if col is not None:
        for obj in list(col.objects):
            data = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if isinstance(data, bpy.types.Mesh) and data.users == 0:
                bpy.data.meshes.remove(data)
            removed["objects"] += 1
        bpy.data.collections.remove(col)
    shared = bpy.data.meshes.get("Combo.hit.sphere")
    if shared is not None and shared.users == 0:
        bpy.data.meshes.remove(shared)
    if arm is not None and arm.animation_data is not None:
        ad = arm.animation_data
        for track in list(ad.nla_tracks):
            if track.name == TRACK:
                ad.nla_tracks.remove(track)
                removed["track"] = True
        prev = arm.get(PREV_ACTION)
        if prev is not None:
            ad.action = bpy.data.actions.get(prev) if prev else None
            del arm[PREV_ACTION]
        solo = arm.get(SOLO)
        if solo is not None:
            for track in ad.nla_tracks:
                if track.name in list(solo):
                    track.is_solo = True
            del arm[SOLO]
    return removed


def build(scene, reply, add_buffer=False, hitboxes=True, arm=None, unit_scale=0.0):
    """Lay the string out.  `reply` is the server's string_plan result.  Returns a summary dict."""
    arm = arm or find_armature(scene)
    if arm is None:
        raise ValueError("no armature: load the fighter first")
    steps = reply.get("steps") or []
    routes = reply.get("routes") or []
    info = {s["move"]: {"length": s.get("frames", 0), "first_hit": s.get("first_hit", 0)} for s in steps}
    names = [s["move"] for s in steps]
    plan = C.plan_string(names, routes, info, int(reply.get("buffer", 5)), add_buffer)
    clear(scene, arm)
    ad = arm.animation_data_create()
    arm[PREV_ACTION] = ad.action.name if ad.action else ""
    ad.action = None
    solo = [t.name for t in ad.nla_tracks if t.is_solo]
    if solo:
        arm[SOLO] = solo
    for track in ad.nla_tracks:
        track.is_solo = False
    track = ad.nla_tracks.new()
    track.name = TRACK
    missing, placed = [], []
    for i, seg in enumerate(plan):
        step = steps[i]
        action = bpy.data.actions.get(step.get("clip") or "")
        if action is None:
            missing.append("%s (clip %s)" % (seg["move"], step.get("clip") or "none"))
            continue
        first, last = C.clip_range(seg, int(step.get("crop", 0)), action.frame_range[1])
        strip = track.strips.new(C.target_name(seg["move"]), seg["start"], action)
        strip.action_frame_start = first
        strip.action_frame_end = max(last, first + 1)
        strip.extrapolation = "HOLD" if not placed else "HOLD_FORWARD"
        placed.append(strip.name)
    track.is_solo = True
    total = C.total_frames(plan)
    scene.frame_start, scene.frame_end, scene.frame_current = 1, max(total, 1), 1
    marks = C.markers(plan, routes)
    for m in marks:
        scene.timeline_markers.new(m["name"], frame=m["frame"])
    col = _collection(scene)
    objs = ribbon(scene, arm, plan, routes, col)
    spheres, bone_missing = [], []
    windows = C.hit_windows(plan, steps)
    if hitboxes and windows:
        unit = unit_scale or (1.0 if height_of(arm) > 5.0 else height_of(arm) / 16.7)   # a model in game units needs none
        spheres, bone_missing = hit_spheres(scene, arm, windows, col, unit)
    return {"plan": plan, "frames": total, "strips": placed, "missing_clips": missing, "markers": marks,
            "ribbon": [o.name for o in objs], "hit_spheres": [o.name for o in spheres], "missing_bones": bone_missing}
