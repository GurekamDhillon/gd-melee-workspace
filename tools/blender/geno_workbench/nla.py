"""Blender NLA authoring, backed by splice.py and the Geno artist exporter.

Segment actions contain sampled crops in segment-local frame coordinates. Their
NLA scale is the whole-recipe retime; stretching a strip changes recipe speed.
Explicit hold and bridge actions share endpoint poses with adjacent segments.
A B-frame bridge spans B+1 intervals and contains B INSERTED poses; there is no
NLA overlap or blend_in/out that could eat a source strike frame.

Public entry points: import_clip, lay_out_recipe, read_recipe, save_recipe,
bake, export_baked, bake_and_export. All bpy work is on the main thread.
"""
from contextlib import contextmanager
from copy import deepcopy
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import uuid

import bpy
from mathutils import Matrix

try:
    from . import nla_layout as timing
    from . import rig
    from .props import STRINGS
except ImportError:
    import nla_layout as timing
    import rig
    from props import STRINGS


META = "geno_wb_nla"
PART = "geno_wb_nla_part"
SOURCE = "geno_wb_clip"
EPSILON = 0.001


def _armature(arm):
    rig._require_main_thread()
    if arm is None or arm.type != "ARMATURE":
        raise ValueError(STRINGS["fighter_not_armature"])
    if bpy.context.mode != "OBJECT":
        raise ValueError(STRINGS["nla_object_mode"])
    return arm


def bind_slot(owner, action):
    """Bind an Object action on both legacy and slotted Blender versions."""
    slots = getattr(action, "slots", ())
    if slots and hasattr(owner, "action_slot"):
        owner.action_slot = slots[0]
    arm = getattr(owner, "id_data", None)
    if arm is not None and getattr(arm, "type", None) == "ARMATURE":
        paths = {curve.data_path for curve in _curves(action)}
        for pb in arm.pose.bones:
            if pb.path_from_id("rotation_quaternion") in paths:
                pb.rotation_mode = "QUATERNION"
            elif pb.path_from_id("rotation_axis_angle") in paths:
                pb.rotation_mode = "AXIS_ANGLE"
            elif pb.path_from_id("rotation_euler") in paths and pb.rotation_mode in {"QUATERNION", "AXIS_ANGLE"}:
                pb.rotation_mode = "XYZ"


def _curves(action):
    curves = []
    for layer in getattr(action, "layers", ()):
        for strip in layer.strips:
            for bag in getattr(strip, "channelbags", ()):
                curves.extend(bag.fcurves)
    return curves or list(getattr(action, "fcurves", ()))


def _frame(frame):
    integer = math.floor(frame)
    bpy.context.scene.frame_set(integer, subframe=frame - integer)
    bpy.context.view_layer.update()


@contextmanager
def _animation_state(arm):
    ad = arm.animation_data_create()
    action = ad.action
    slot = getattr(ad, "action_slot", None)
    nla_enabled = ad.use_nla
    action_settings = {key: getattr(ad, key) for key in ("action_blend_type", "action_extrapolation", "action_influence")}
    tracks = [(t, t.mute, t.is_solo) for t in ad.nla_tracks]
    scene = bpy.context.scene
    frame = scene.frame_current + scene.frame_subframe
    poses = [(p, p.matrix_basis.copy(), p.rotation_mode) for p in arm.pose.bones]
    try:
        ad.action = None
        ad.action_blend_type = "REPLACE"
        ad.action_influence = 1.0
        for track, _, _ in tracks:
            track.is_solo = False
            track.mute = True
        yield ad
    finally:
        ad.action = action
        if action is not None:
            if slot is not None and hasattr(ad, "action_slot"):
                ad.action_slot = slot
            else:
                bind_slot(ad, action)
        ad.use_nla = nla_enabled
        for key, val in action_settings.items():
            setattr(ad, key, val)
        for track, mute, solo in tracks:
            try:
                track.mute, track.is_solo = mute, solo
            except ReferenceError:
                pass
        for pb, matrix, mode in poses:
            pb.rotation_mode = mode
            pb.matrix_basis = matrix
        _frame(frame)


def _reset_pose(arm):
    # Imported glTF actions omit unanimated translation/scale channels. Do not
    # let the engine preview or the previously auditioned action fill them.
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
        pb.rotation_axis_angle = (0, 0, 1, 0)
        pb.scale = (1, 1, 1)


def _pose(arm, visual=False):
    if not visual:
        return {pb.name: pb.matrix_basis.copy() for pb in arm.pose.bones}
    evaluated = arm.evaluated_get(bpy.context.evaluated_depsgraph_get())
    result = {}
    for pb in arm.pose.bones:
        actual = evaluated.pose.bones[pb.name]
        kwargs = {}
        if pb.parent:
            kwargs = dict(parent_matrix=evaluated.pose.bones[pb.parent.name].matrix,
                          parent_matrix_local=pb.parent.bone.matrix_local)
        result[pb.name] = pb.bone.convert_local_to_pose(
            actual.matrix, pb.bone.matrix_local, invert=True, **kwargs)
    return result


def _mix(a, b, weight):
    result = {}
    for bone in a:
        at, aq, ass = a[bone].decompose()
        bt, bq, bs = b[bone].decompose()
        result[bone] = Matrix.LocRotScale(at.lerp(bt, weight), aq.slerp(bq, weight), ass.lerp(bs, weight))
    return result


def _sample(poses, frame):
    frame = max(0.0, min(float(frame), len(poses) - 1))
    lo = int(math.floor(frame))
    return _mix(poses[lo], poses[min(lo + 1, len(poses) - 1)], frame - lo)


def _action(arm, name, keyed_poses, metadata=None):
    """Key every pose channel, preserving quaternion hemisphere continuity."""
    action = bpy.data.actions.new(name)
    arm.animation_data_create().action = action
    previous = {}
    for frame, pose in keyed_poses:
        for pb in arm.pose.bones:
            loc, rotation, scale = pose[pb.name].decompose()
            if pb.name in previous and rotation.dot(previous[pb.name]) < 0:
                rotation.negate()
            previous[pb.name] = rotation.copy()
            pb.rotation_mode = "QUATERNION"
            pb.location, pb.rotation_quaternion, pb.scale = loc, rotation, scale
            for channel in ("location", "rotation_quaternion", "scale"):
                pb.keyframe_insert(channel, frame=frame, group=pb.name)
    for curve in _curves(action):
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR"
    if metadata is not None:
        action[PART] = json.dumps(metadata)
    return action


def _module(path, name):
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError(STRINGS["nla_tool_missing"].format(path=path))
    cached = sys.modules.get(name)
    if cached is not None:
        if Path(cached.__file__).resolve() != path:
            raise ValueError(STRINGS["nla_tool_conflict"].format(path=path))
        return cached
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    return module


def _source_context(project, height):
    project = Path(project).expanduser().resolve()
    for path in (project.parent.parent, project / "tools"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    converter = _module(project / "tools/xv2_to_artist.py", "xv2_to_artist")
    splice = _module(project / "tools/splice.py", "splice")
    if not callable(getattr(converter, "splice_context", None)):
        raise ValueError(STRINGS["nla_context_missing"])
    source = converter.Source(project / "ir/goku.xv2.ir.json")
    mesh = converter.build_mesh(source, height)
    context = converter.splice_context(source, mesh)
    return converter, splice, mesh, context


def _import_clip_data(arm, converter, mesh, clip, name):
    """Reuse the source tool's GLB writer and Blender's importer for bone bases.

    No second source decoder, retarget solver, or Geno exporter lives here.
    Imported meshes/rigs are temporary; only the compatible action is retained.
    """
    selected = list(bpy.context.selected_objects)
    active = bpy.context.view_layer.objects.active
    try:
        with rig.import_transaction() as transaction:
            with tempfile.TemporaryDirectory(prefix="geno-nla-source-") as temp:
                path = Path(temp) / "clip.glb"
                anim = dict(rotation=clip.rot, hips=clip.hips, root=clip.root,
                            scale=clip.scl, frames=clip.n, loop=False)
                converter.emit_glb(mesh, {"nla_source": anim}, path)
                scene = bpy.context.scene
                fps, base = scene.render.fps, scene.render.fps_base
                try:
                    scene.render.fps, scene.render.fps_base = 60, 1.0
                    result = bpy.ops.import_scene.gltf(filepath=str(path))
                finally:
                    scene.render.fps, scene.render.fps_base = fps, base
                if "FINISHED" not in result:
                    raise ValueError(STRINGS["nla_import_failed"])
            imported = [o for o in transaction.new_data("objects") if o.type == "ARMATURE"]
            if len(imported) != 1:
                raise ValueError(STRINGS["nla_import_failed"])
            source_arm = imported[0]
            for bone in source_arm.data.bones:
                target = arm.data.bones.get(bone.name)
                if target is None or (bone.parent.name if bone.parent else None) != (target.parent.name if target.parent else None):
                    raise ValueError(STRINGS["nla_rig_mismatch"].format(bone=bone.name))
                error = max(abs(bone.matrix_local[i][j] - target.matrix_local[i][j]) for i in range(4) for j in range(4))
                if error > 1e-3:
                    raise ValueError(STRINGS["nla_rig_mismatch"].format(bone=bone.name))
            ad = source_arm.animation_data
            candidates = set()
            if ad:
                if ad.action:
                    candidates.add(ad.action)
                candidates.update(s.action for t in ad.nla_tracks for s in t.strips if s.action)
            if len(candidates) != 1:
                raise ValueError(STRINGS["nla_import_failed"])
            action = candidates.pop()
            action.name = name
            action.use_frame_range = False
            offset = action.frame_range[0]
            if offset:
                for curve in _curves(action):
                    for point in curve.keyframe_points:
                        point.co.x -= offset
                        point.handle_left.x -= offset
                        point.handle_right.x -= offset
                    curve.update()
            # Material images may have lived in the temporary GLB; no imported
            # geometry, source textures or extra actions remain in the scene.
            discard = [item for kind in rig._TRACKED_DATA for item in transaction.new_data(kind) if item != action]
            if discard:
                bpy.data.batch_remove(ids=tuple(discard))
            return action
    finally:
        for obj in list(bpy.context.selected_objects):
            obj.select_set(False)
        for obj in selected:
            if bpy.context.view_layer.objects.get(obj.name) == obj:
                obj.select_set(True)
        bpy.context.view_layer.objects.active = active


def import_clip(arm, project, reference, height=20.0):
    """Import an XV2 name or melee:<fighter>/<action> via splice_context.resolve."""
    _armature(arm)
    converter, splice, mesh, context = _source_context(project, height)
    source = context["resolve"](reference)
    count = int(math.floor(source.length)) + 1
    clip = splice.fill(source.sample(list(range(count))), context["rig"])
    with _animation_state(arm):
        action = _import_clip_data(arm, converter, mesh, clip, reference)
    action[SOURCE] = json.dumps(dict(clip=reference, length=count))
    action.use_fake_user = True
    arm.animation_data.action = action
    _reset_pose(arm)
    bind_slot(arm.animation_data, action)
    # An imported clip is auditioned as the active action, without recipe layers.
    for track in arm.animation_data.nla_tracks:
        track.mute = True
        track.is_solo = False
    return action


def _from_actions(arm, recipe, actions):
    """Synthetic/already-compatible Blender sources; data-free headless path.

    Source-space mirror/yaw and translation alignment belong to splice.bake.
    Use project= for those operations, never approximate them in Blender axes.
    """
    if recipe.get("loop") or any(s.get("mirror") or s.get("root_yaw") or s.get("yaw_ramp") for s in recipe["segments"]):
        raise ValueError(STRINGS["nla_source_flags"])
    lengths = {name: int(round(action.frame_range[1] - action.frame_range[0])) + 1 for name, action in actions.items()}
    raw_recipe = deepcopy(recipe)
    raw_recipe.pop("frames", None)
    raw = timing.layout(raw_recipe, lengths)
    poses = []
    ad = arm.animation_data_create()
    ad.use_nla = False
    for index, segment in enumerate(raw.segments):
        action = actions[segment.action_name]
        ad.action = action
        _reset_pose(arm)
        bind_slot(ad, action)
        part = []
        direction = -1 if segment.reversed else 1
        for frame in range(segment.samples):
            source_frame = segment.source_from + direction * frame / segment.scale
            # Fractional crops are sampled by slerp/lerp between source poses.
            lo = math.floor(source_frame)
            _frame(action.frame_range[0] + lo)
            a = _pose(arm)
            _frame(action.frame_range[0] + min(lo + 1, lengths[segment.action_name] - 1))
            part.append(_mix(a, _pose(arm), source_frame - lo))
        if index:
            blend = int(recipe["segments"][index].get("blend", recipe.get("blend", 3)))
            previous = poses[-1]
            for frame in range(blend):
                weight = (frame + 1) / (blend + 1)
                poses.append(_mix(previous, part[0], weight * weight * (3 - 2 * weight)))
        poses.extend(part)
        poses.extend([part[-1]] * segment.hold)
    value = timing.layout(recipe, lengths)
    if "frames" in recipe:
        poses = [_sample(poses, i * (len(poses) - 1) / (value.total_length - 1)) for i in range(value.total_length)]
    return value, poses, lengths, [recipe["row"]] if recipe.get("row") else []


def _from_project(arm, recipe, project, height):
    converter, splice, mesh, context = _source_context(project, height)
    lengths = {seg["clip"]: int(math.floor(context["resolve"](seg["clip"]).length)) + 1 for seg in recipe["segments"]}
    value = timing.layout(recipe, lengths)
    # Public bake owns reverse, speed, mirror, yaw, inserted blends, translation
    # alignment, bone scales, holds, global retime and optional loop easing.
    clip, _ = splice.bake("workbench", recipe, context["resolve"], context["rig"])
    action = _import_clip_data(arm, converter, mesh, clip, "NLA prepared")
    ad = arm.animation_data_create()
    ad.use_nla = False
    ad.action = action
    _reset_pose(arm)
    bind_slot(ad, action)
    poses = []
    for frame in range(value.total_length):
        _frame(action.frame_range[0] + frame)
        poses.append(_pose(arm))
    ad.action = None
    bpy.data.actions.remove(action)
    rows = splice.target_rows(recipe, *context["move_rows"]) if context.get("move_rows") else splice.target_rows(recipe)
    return value, poses, lengths, rows


def _part_action(arm, name, poses, start, end, rate, metadata):
    # Include EVERY integer output frame as well as the strip endpoints. Thus
    # whole-clip retime and quaternion sampling agree with splice.bake at every
    # exported frame, even when an NLA boundary is fractional.
    frames = sorted({start, end, *range(math.ceil(start), math.floor(end) + 1)})
    keyed = [((f - start) / rate, _sample(poses, f)) for f in frames]
    if len(keyed) == 1:
        keyed.append((EPSILON, keyed[0][1]))
    return _action(arm, name, keyed, metadata)


def _strip(track, action, start, end, rate, action_start=0.0):
    # Create beyond existing strips first: flooring a fractional boundary can
    # otherwise overlap the previous strip before RNA accepts the real start.
    temporary_start = math.ceil(max([start] + [s.frame_end for s in track.strips])) + 1
    strip = track.strips.new(action.name, temporary_start, action)
    bind_slot(strip, action)
    strip.action_frame_start = action_start
    strip.action_frame_end = action_start + (end - start) / rate
    strip.scale = rate
    strip.frame_start = start
    strip.frame_end = end
    strip.blend_type = "REPLACE"
    strip.extrapolation = "NOTHING"
    strip.use_auto_blend = False
    strip.blend_in = strip.blend_out = 0.0
    return strip


def _metadata(arm):
    return json.loads(arm.get(META, "{}"))


def lay_out_recipe(arm, name, recipe, *, project=None, actions=None, height=20.0):
    """Create/replace one managed track; select it for NLA preview.

    project is the directory containing workbench.json and tools/splice.py.
    actions is an alternative mapping of compatible Blender actions, used by the
    synthetic self-test. Existing unrelated tracks and source actions survive.
    """
    _armature(arm)
    if not name or (project is None) == (actions is None):
        raise ValueError(STRINGS["nla_sources_required"])
    old_data = _metadata(arm)
    track_name = next((n for n, m in old_data.items() if m["name"] == name), None)
    old_track = arm.animation_data.nla_tracks.get(track_name) if arm.animation_data and track_name else None
    with rig.import_transaction():
        with _animation_state(arm) as ad:
            if project is not None:
                value, poses, lengths, rows = _from_project(arm, recipe, project, height)
            else:
                value, poses, lengths, rows = _from_actions(arm, recipe, actions)
            rate = value.retime_scale
            prepared = []
            for index, segment in enumerate(value.segments):
                owner = uuid.uuid4().hex
                data = dict(kind="segment", owner=owner, segment=deepcopy(recipe["segments"][index]),
                            samples=segment.samples, length=lengths[segment.action_name])
                main = _part_action(arm, segment.action_name, poses, segment.frame_start, segment.frame_end, rate, data)
                # A single pose needs a positive NLA interval. Only its duplicate
                # endpoint is extended; the next helper starts at that endpoint.
                main_end = segment.frame_end if segment.samples > 1 else segment.frame_start + EPSILON * rate
                if value.raw_length == 1:
                    main_end = max(main_end, value.total_length - 1)
                prepared.append((main, segment.frame_start, main_end, 0.0))
                physical_end = main_end
                if segment.hold:
                    hold = _part_action(arm, "Hold", poses, segment.frame_end, segment.hold_end, rate,
                                        dict(kind="hold", owner=owner, trim=(physical_end - segment.frame_end) / rate))
                    prepared.append((hold, physical_end, segment.hold_end, (physical_end - segment.frame_end) / rate))
                    physical_end = segment.hold_end
                if index + 1 < len(value.segments):
                    next_start = value.segments[index + 1].frame_start
                    bridge = _part_action(arm, "Blend", poses, segment.hold_end, next_start, rate,
                                          dict(kind="bridge", owner=owner))
                    prepared.append((bridge, physical_end, next_start, (physical_end - segment.hold_end) / rate))
        track = arm.animation_data.nla_tracks.new()
        try:
            for action, start, end, crop in prepared:
                _strip(track, action, start, end, rate, crop)
        except Exception:
            arm.animation_data.nla_tracks.remove(track)
            raise
        # Commit only after the complete replacement track exists.
        if old_track is not None:
            arm.animation_data.nla_tracks.remove(old_track)
        track.name = track_name or "Splice: " + name
        canonical = timing.recipe_from_layout(value)
        old_data[track.name] = dict(name=name, recipe=canonical, rate=rate, lengths=lengths, rows=rows,
                                   project=str(Path(project).resolve()) if project is not None else None,
                                   actions={k: a.name for k, a in actions.items()} if actions is not None else None,
                                   height=height)
        arm[META] = json.dumps(old_data)
        ad = arm.animation_data
        ad.action = None
        ad.use_nla = True
        for other in ad.nla_tracks:
            other.is_solo = False
            other.mute = other != track
            other.select = other == track
        bpy.context.scene.frame_start = 0
        bpy.context.scene.frame_end = max(1, value.total_length - 1)
        _frame(0)
        return track


def current_track(arm):
    _armature(arm)
    data = _metadata(arm)
    tracks = list(arm.animation_data.nla_tracks) if arm.animation_data else []
    chosen = [t for t in tracks if t.name in data and t.select]
    if len(chosen) != 1:
        chosen = [t for t in tracks if t.name in data and not t.mute]
    if len(chosen) != 1:
        raise ValueError(STRINGS["nla_track_required"])
    return chosen[0]


def _whole(value, label):
    return timing._whole(value, label)


def read_recipe(arm, track=None):
    """Read crop, reverse, scale, order, holds and gaps from CURRENT strips.

    Strip origins are normalized to zero. Repeat, animated time/influence,
    overlaps, blend_in/out and off-grid edits cannot be losslessly expressed by
    splice.py and are rejected. Source marks outside a trimmed crop are dropped.
    """
    _armature(arm)
    track = track or current_track(arm)
    meta = _metadata(arm).get(track.name)
    if meta is None:
        raise ValueError(STRINGS["nla_track_required"])
    rate = meta["rate"]
    baseline = timing.layout(meta["recipe"], meta["lengths"])
    parts, holds = [], {}
    for strip in track.strips:
        if strip.type != "CLIP" or strip.action is None:
            raise ValueError(STRINGS["nla_unsupported_strip"])
        info = json.loads(strip.action.get(PART, "null"))
        if info is None and SOURCE in strip.action:
            source = json.loads(strip.action[SOURCE])
            info = dict(kind="segment", owner=strip.action.name, samples=source["length"], length=source["length"],
                        segment={"clip": source["clip"], "from": 0, "to": source["length"] - 1})
        if info is None:
            raise ValueError(STRINGS["nla_unsupported_strip"])
        if (strip.mute or abs(strip.repeat - 1) > 1e-6 or strip.use_animated_time or strip.use_animated_influence
                or strip.blend_type != "REPLACE" or strip.blend_in or strip.blend_out
                or abs(strip.influence - 1) > 1e-6 or len(strip.modifiers)):
            raise ValueError(STRINGS["nla_unsupported_strip"])
        if info["kind"] in {"hold", "bridge"} and strip.use_reverse:
            raise ValueError(STRINGS["nla_unsupported_strip"])
        if info["kind"] == "bridge":
            continue
        if info["kind"] == "hold":
            owner = info["owner"]
            if owner in holds:
                raise ValueError(STRINGS["nla_unsupported_strip"])
            holds[owner] = _whole((strip.frame_end - strip.frame_start) / rate + info.get("trim", 0), "hold")
        else:
            parts.append((strip, info))
    parts.sort(key=lambda p: p[0].frame_start)
    if not parts:
        raise ValueError(STRINGS["nla_track_required"])
    origin = parts[0][0].frame_start
    recipe = deepcopy(meta["recipe"])
    recipe["segments"] = []
    previous_end = -1
    lengths = {}
    for index, (strip, info) in enumerate(parts):
        original = info["segment"]
        item = deepcopy(original)
        direction = -1 if original["from"] > original["to"] else 1
        base_speed = original.get("speed", 1)
        first, last = strip.action_frame_start, strip.action_frame_end
        if info["samples"] == 1:
            # A single pose uses a tiny positive support interval, or the entire
            # retimed one-pose clip. Stretching it cannot imply source speed.
            duration = EPSILON * rate
            if baseline.raw_length == 1:
                duration = max(duration, baseline.total_length - 1)
            got = (strip.frame_end - strip.frame_start, first, last, strip.scale)
            want = (duration, 0.0, duration / rate, rate)
            if any(not math.isclose(a, b, rel_tol=0, abs_tol=1e-4) for a, b in zip(got, want)):
                raise ValueError(STRINGS["nla_off_grid"])
            item["from"], item["to"] = original["from"], original["to"]
            item["speed"] = base_speed
            span = 0
        else:
            # RNA stores scale as float32. Dividing by it can move speed just
            # above an integer-sample boundary and drop a pose in seg_times.
            # The logical strip span is integral; use it as the sample clock.
            span = _whole((strip.frame_end - strip.frame_start) / rate, "strip duration")
            if span <= 0:
                raise ValueError(STRINGS["nla_off_grid"])
            bounds = []
            for bound in (first, last):
                for endpoint in (0.0, info["samples"] - 1):
                    if math.isclose(bound, endpoint, rel_tol=0, abs_tol=1e-4):
                        bound = endpoint
                        break
                bounds.append(bound)
            first, last = bounds
            if strip.use_reverse:
                first, last = last, first
            item["from"] = original["from"] + direction * base_speed * first
            item["to"] = original["from"] + direction * base_speed * last
            speed = abs(item["to"] - item["from"]) / span
            if speed <= 0:
                raise ValueError(STRINGS["nla_off_grid"])
            if (math.isclose(speed, base_speed, rel_tol=1e-6, abs_tol=1e-9)
                    and timing.sample_count(item["from"], item["to"], base_speed) == span + 1):
                speed = base_speed
            item["speed"] = speed
            if (not strip.use_reverse and last == info["samples"] - 1
                    and timing.sample_count(item["from"], original["to"], speed) == span + 1):
                # Retain an unsampled crop tail only while it stays unsampled
                # at the edited speed.
                item["to"] = original["to"]
        item["hold"] = holds.get(info["owner"], 0)
        if "marks" in item:
            lo, hi = sorted((item["from"], item["to"]))
            item["marks"] = {k: f for k, f in item["marks"].items() if lo <= f <= hi}
        start = _whole((strip.frame_start - origin) / rate, "strip start")
        samples = timing.sample_count(item["from"], item["to"], item["speed"])
        if span != samples - 1:
            raise ValueError(STRINGS["nla_off_grid"])
        gap = start - previous_end - 1
        if gap < 0:
            raise ValueError(STRINGS["nla_overlap"])
        if index:
            item["blend"] = gap
        previous_end = start + samples + item["hold"] - 1
        recipe["segments"].append(item)
        lengths[item["clip"]] = info["length"]
    if "frames" in recipe and previous_end:
        recipe["frames"] = _whole(previous_end * rate, "retimed end") + 1
    value = timing.layout(recipe, lengths)
    canonical = timing.recipe_from_layout(value)
    if _primary_unchanged(parts, canonical, meta["recipe"], baseline, origin):
        _check_helpers(track, parts, value, origin)
    return canonical


def _primary_unchanged(parts, recipe, previous, baseline, origin):
    """Only edits to main strips justify regenerating stale helper placement."""
    if len(parts) != len(baseline.segments):
        return False

    def source_fields(segment):
        return {key: value for key, value in segment.items() if key not in {"hold", "blend"}}

    for (strip, _), current, old, segment in zip(parts, recipe["segments"], previous["segments"], baseline.segments):
        if source_fields(current) != source_fields(old):
            return False
        end = segment.frame_end if segment.samples > 1 else segment.frame_start + EPSILON * baseline.retime_scale
        if baseline.raw_length == 1:
            end = max(end, baseline.total_length - 1)
        got = (strip.frame_start - origin, strip.frame_end - origin)
        if any(not math.isclose(a, b, rel_tol=0, abs_tol=1e-4) for a, b in zip(got, (segment.frame_start, end))):
            return False
    return True


def _check_helpers(track, parts, value, origin):
    """Helper-only edits are not silently discarded by recipe readback."""
    expected = {}
    for index, ((strip, info), segment) in enumerate(zip(parts, value.segments)):
        owner = info["owner"]
        end = strip.frame_end
        if segment.hold:
            expected[("hold", owner)] = (end, origin + segment.hold_end,
                                         origin + segment.frame_end)
            end = origin + segment.hold_end
        if index + 1 < len(parts):
            expected[("bridge", owner)] = (end, parts[index + 1][0].frame_start,
                                           origin + segment.hold_end)
    actual = {}
    for strip in track.strips:
        data = json.loads(strip.action.get(PART, "{}"))
        if data.get("kind") in {"hold", "bridge"}:
            key = data["kind"], data["owner"]
            if key in actual:
                raise ValueError(STRINGS["nla_helper_edit"])
            actual[key] = strip
    if actual.keys() != expected.keys():
        raise ValueError(STRINGS["nla_helper_edit"])
    for key, (start, end, clock_start) in expected.items():
        strip = actual[key]
        want = (start, end, (start - clock_start) / value.retime_scale,
                (end - clock_start) / value.retime_scale, value.retime_scale)
        got = (strip.frame_start, strip.frame_end, strip.action_frame_start,
               strip.action_frame_end, strip.scale)
        if any(not math.isclose(a, b, rel_tol=0, abs_tol=1e-4) for a, b in zip(got, want)):
            raise ValueError(STRINGS["nla_helper_edit"])


def save_recipe(project, name, recipe):
    """Append a new AUTHORED, unwired entry; never open splices.json for writing."""
    project = Path(project).expanduser().resolve()
    if not project.is_dir():
        raise ValueError(STRINGS["invalid_project"].format(path=project))
    path = project / "splices.authored.json"
    if path.is_symlink() or path.resolve() == (project / "splices.json").resolve():
        raise ValueError(STRINGS["nla_authored_path"])
    document = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"schema": "goku-splices/1", "recipes": {}}
    if document.get("schema") != "goku-splices/1" or not isinstance(document.get("recipes"), dict):
        raise ValueError(STRINGS["nla_recipe_file_error"])
    new_name = name
    suffix = 1
    while new_name in document["recipes"]:
        new_name = f"{name}.{suffix:03d}"
        suffix += 1
    authored = deepcopy(recipe)
    authored.update(status="AUTHORED", wired=False, example=False)
    document["recipes"][new_name] = authored
    fd, temporary = tempfile.mkstemp(prefix=".splices-authored-", suffix=".json", dir=project)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(document, out, indent=2, allow_nan=False)
            out.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return path, new_name


def bake(arm, track=None, name=None):
    """Bake visual NLA poses to one zero-based AUTHORED action; retain the track."""
    _armature(arm)
    track = track or current_track(arm)
    meta = _metadata(arm)[track.name]
    recipe = read_recipe(arm, track)
    if recipe != meta["recipe"]:
        # Structural strip edits change the seam endpoint poses. Rebuild through
        # the same source pipeline before baking, so gaps and alignment follow
        # the edited crop/order/speed, rather than stale bridge actions.
        sources = None
        if meta["actions"] is not None:
            sources = {k: bpy.data.actions.get(v) for k, v in meta["actions"].items()}
            if any(a is None for a in sources.values()):
                raise ValueError(STRINGS["nla_source_action_missing"])
        track = lay_out_recipe(arm, meta["name"], recipe, project=meta["project"], actions=sources, height=meta["height"])
        meta = _metadata(arm)[track.name]
    value = timing.layout(recipe, meta["lengths"])
    name = name or recipe.get("row") or meta["name"]
    if not name or len(name) > 31:
        raise ValueError(STRINGS["nla_clip_name"])
    segments = [s for s in track.strips if json.loads(s.action.get(PART, "{}" )).get("kind") == "segment"]
    origin = min(s.frame_start for s in segments)
    with rig.import_transaction():
        with _animation_state(arm) as ad:
            ad.use_nla = True
            track.mute = False
            for strip in track.strips:
                bind_slot(strip, strip.action)
            _reset_pose(arm)
            poses = []
            for frame in range(value.total_length):
                _frame(origin + frame)
                poses.append((frame, _pose(arm, visual=True)))
            ad.use_nla = False
            unique = name
            suffix = 1
            while bpy.data.actions.get(unique) is not None:
                ending = f".{suffix:03d}"
                unique = name[:31 - len(ending)] + ending
                suffix += 1
            action = _action(arm, unique, poses)
    action.use_fake_user = True
    action["geno_status"] = "AUTHORED"
    action["geno_loop"] = bool(recipe.get("loop"))
    action["geno_hit_frames"] = json.dumps(sorted({m.frame for m in value.marks if m.label.lower().startswith("hit")}))
    action["geno_splice_recipe"] = json.dumps(recipe)
    if meta.get("rows"):
        action["geno_rows"] = ",".join(meta["rows"])
    roles = json.loads(arm.get("geno", "{}")).get("roles", {})
    roots = [bone for bone, role in roles.items() if role == "translation"]
    action["geno_root_motion"] = any(
        bone in poses[0][1] and any((pose[bone].translation - poses[0][1][bone].translation).length > 1e-5
                                   for _, pose in poses[1:]) for bone in roots)
    return action


def export_baked(arm, action, glb):
    """Preflight and export a temporary rig copy with the existing exporter.

    export_fighter.do_export clears its target's tracks and looks at all fake
    user actions. Scope those effects to a copy and restore fake users, selection,
    timeline and frame rate even if preflight or export fails.
    """
    _armature(arm)
    workspace = Path(__file__).resolve().parents[3]
    if (workspace / "tools/geno/artist").is_dir() and str(workspace) not in sys.path:
        sys.path.insert(0, str(workspace))
    from tools.geno.artist.blender import export_fighter as exporter

    glb = Path(glb).expanduser().resolve()
    if glb.suffix.lower() != ".glb":
        raise ValueError(STRINGS["nla_glb_required"])
    selected = list(bpy.context.selected_objects)
    active = bpy.context.view_layer.objects.active
    scene = bpy.context.scene
    fps = scene.render.fps, scene.render.fps_base
    frame = scene.frame_current + scene.frame_subframe
    fake_users = [(a, a.use_fake_user) for a in bpy.data.actions]
    added = []
    try:
        clone = arm.copy()
        scene.collection.objects.link(clone)
        added.append(clone)
        clone.animation_data_clear()
        clone.animation_data_create().action = action
        bind_slot(clone.animation_data, action)
        for constraint in list(clone.constraints):
            clone.constraints.remove(constraint)
        for pb in clone.pose.bones:
            for constraint in list(pb.constraints):
                pb.constraints.remove(constraint)
        for mesh in list(scene.objects):
            if mesh.type != "MESH" or not any(m.type == "ARMATURE" and m.object == arm for m in mesh.modifiers):
                continue
            copy = mesh.copy()
            scene.collection.objects.link(copy)
            added.append(copy)
            if copy.parent == arm:
                matrix = copy.matrix_world.copy()
                copy.parent = clone
                copy.matrix_world = matrix
            for modifier in copy.modifiers:
                if modifier.type == "ARMATURE" and modifier.object == arm:
                    modifier.object = clone
        for other, _ in fake_users:
            other.use_fake_user = other == action
        exporter.preflight(clone)
        blockers = [item for item in exporter.OUT if item[0] == "BLOCKER"]
        if blockers:
            raise ValueError("; ".join(f"{code}: {message}" for _, code, _, message, _ in blockers))
        action["geno_status"] = "AUTHORED"
        exporter.do_export(clone, str(glb))
        sidecar = Path(str(glb) + ".geno.json")
        document = json.loads(sidecar.read_text(encoding="utf-8"))
        document["clips"][action.name]["status"] = "AUTHORED"
        sidecar.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        return glb
    finally:
        if added:
            bpy.data.batch_remove(ids=tuple(added))
        for other, fake in fake_users:
            other.use_fake_user = fake
        scene.render.fps, scene.render.fps_base = fps
        for obj in list(bpy.context.selected_objects):
            obj.select_set(False)
        for obj in selected:
            if bpy.context.view_layer.objects.get(obj.name) == obj:
                obj.select_set(True)
        bpy.context.view_layer.objects.active = active
        _frame(frame)


def bake_and_export(arm, glb, track=None, name=None):
    action = bake(arm, track, name)
    export_baked(arm, action, glb)
    return action
