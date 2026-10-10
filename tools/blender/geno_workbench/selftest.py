"""Headless integration checks using only the synthetic workbench fighter.

Run:
    blender --background --factory-startup --python-exit-code 1 \
        --python tools/blender/geno_workbench/selftest.py -- --out DIRECTORY
"""

import argparse
import copy
from contextlib import ExitStack
import json
import math
from pathlib import Path
import sys
import tempfile
import time
import traceback
from types import SimpleNamespace


_PACKAGE_DIR = Path(__file__).resolve().parent
for _directory in (_PACKAGE_DIR.parent, _PACKAGE_DIR):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

_CHECKS = []


def _one_line(value):
    return " ".join(str(value).splitlines())


def check(name, cond, detail=""):
    """Print one machine-readable result and stop immediately on failure."""
    passed = bool(cond)
    name = _one_line(name)
    detail = _one_line(detail)
    _CHECKS.append({"name": name, "ok": passed, "detail": detail})
    line = "GENO_WB_CHECK {} {}".format(name, "OK" if passed else "FAIL")
    if detail:
        line += " " + detail
    print(line, flush=True)
    if not passed:
        raise AssertionError(name + (": " + detail if detail else ""))


def _distance(a, b):
    return math.sqrt(sum((float(a[i]) - float(b[i])) ** 2 for i in range(3)))


def _matrix_tuple(matrix):
    return tuple(tuple(float(value) for value in row) for row in matrix)


def _matrix_error(a, b):
    return max(abs(a[row][col] - b[row][col])
               for row in range(4) for col in range(4))


def _bone_state(arm, name):
    bone = arm.pose.bones[name]
    return (
        _matrix_tuple(arm.matrix_world),
        _matrix_tuple(bone.matrix),
        _matrix_tuple(bone.matrix_basis),
    )


def _build_armature(plan, rest, space):
    import bpy
    from mathutils import Vector

    if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
        bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")

    check("rig_name_available", bpy.data.objects.get("SynthRig") is None)
    data = bpy.data.armatures.new("SynthRigData")
    arm = bpy.data.objects.new("SynthRig", data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)

    joints = [joint for joint in plan["joints"] if not joint.get("synth", False)]
    positions = {}
    for joint in joints:
        index = joint["index"]
        matrix = rest[index]
        positions[index] = Vector(space.to_blender_point(
            (matrix[0][3], matrix[1][3], matrix[2][3])
        ))

    bpy.ops.object.mode_set(mode="EDIT")
    try:
        bones = {}
        for joint in joints:
            index = joint["index"]
            head = positions[index]
            child = next(
                (item for item in joints if item.get("parent") == index), None
            )
            direction = (
                positions[child["index"]] - head
                if child is not None else Vector((0.0, 0.0, 1.0))
            )
            # A coincident child cannot define a bone direction.
            if direction.length < 1e-12:
                direction = Vector((0.0, 0.0, 1.0))
            direction.normalize()
            bone = data.edit_bones.new(joint["name"])
            bone.head = head
            bone.tail = head + direction
            bone.roll = 0.0
            bones[index] = bone

        for joint in joints:
            parent = joint.get("parent")
            if parent in bones:
                bones[joint["index"]].parent = bones[parent]
                bones[joint["index"]].use_connect = False
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")

    arm.animation_data_clear()
    bpy.context.scene.frame_set(0)
    bpy.context.view_layer.update()
    return arm


def _world_vertices(obj):
    import bpy

    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return [
        tuple(evaluated.matrix_world @ vertex.co)
        for vertex in evaluated.data.vertices
    ]


def _world_center(obj):
    vertices = _world_vertices(obj)
    if not vertices:
        raise AssertionError("Overlay has no evaluated vertices")
    return tuple(
        (min(point[axis] for point in vertices)
         + max(point[axis] for point in vertices)) * 0.5
        for axis in range(3)
    )


def _visible(collection, prefix):
    return [
        obj for obj in collection.objects
        if obj.name.startswith(prefix)
        and not obj.hide_viewport
        and not obj.hide_render
    ]


def _identities(collection):
    return {
        obj.name: (obj.as_pointer(), obj.data.as_pointer())
        for obj in collection.objects
    }


def _session_detail(session):
    for name in ("status", "last_error", "error"):
        value = getattr(session, name, "")
        if value:
            return str(value)
    return ""


def _require_success(name, result, session):
    # Some API methods return None on success; frame setters return bool.
    if result is False:
        check(name, False, _session_detail(session))


def _run(out_dir):
    import bpy

    try:
        from . import api, client, fake_engine, overlays, pose, rig, rigmap
        from . import wbspace as space
    except ImportError:
        import api
        import client
        import fake_engine
        import overlays
        import pose
        import rig
        import rigmap
        import wbspace as space

    scene = bpy.context.scene
    fake = fake_engine.FakeWorkbench()
    transports = []
    stopped = False
    arm = None
    summary = {}

    def client_factory():
        transport = client.McpClient(port=port, timeout=2.0)
        transports.append(transport)
        return transport

    def frame_info():
        # Read over the same transport used by WbSession. This avoids assuming
        # a private name for the session's cached frame_info attribute.
        info = transports[-1].call("frame_info")
        space.check_schema(info)
        return info

    try:
        port = fake.start()
        session = api.WbSession(client_factory=client_factory)
        result = session.connect()
        check("connect", result is not False, _session_detail(session))
        result = session.refresh_rows()
        names = {row["name"] for row in session.rows}
        check(
            "rows",
            result is not False and names == {"wait", "jab", "dair"},
            "names=" + ",".join(sorted(names)),
        )

        plan = fake_engine.synthetic_plan()
        plan_path = out_dir / "plan.json"
        plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
        session.project_dir = str(out_dir)
        session.plan_path = str(plan_path)
        session.bone_aliases = {}

        arm = _build_armature(plan, fake_engine.rest_world(plan), space)
        jm = rigmap.build_joint_map(plan, rig.bone_names(arm))
        check(
            "joint_map",
            jm.coverage() == 1.0 and len(jm.by_index) == 8
            and not jm.missing_bones and not jm.unmapped_bones,
            "coverage={} mapped={}".format(jm.coverage(), len(jm.by_index)),
        )
        check("rest_has_no_action", arm.animation_data is None)

        _require_success("rest_row", session.load_row("wait"), session)
        _require_success("rest_frame", session.set_frame(1), session)
        pose.calibrate(arm, session)
        calibrated = pose.calibration_for(arm)
        check("calibration_exists", calibrated is not None)
        calibrated_map, cal = calibrated
        check("calibration_map", calibrated_map.by_index == jm.by_index)
        check(
            "calibration_scale",
            math.isfinite(cal.scale) and abs(cal.scale - 1.0) < 1e-6,
            "scale={:.12g}".format(cal.scale),
        )
        check("calibration_offsets_present", set(jm.by_index).issubset(cal.k))
        translation_error = max(
            math.sqrt(sum(float(matrix[row][3]) ** 2 for row in range(3)))
            for matrix in cal.k.values()
        )
        check(
            "calibration_translation",
            math.isfinite(translation_error) and translation_error < 1e-6,
            "max_translation={:.12g}".format(translation_error),
        )

        max_head_err = 0.0
        max_rot_err = 0.0
        poses = 0
        for facing in (1, -1):
            fake.set_facing(facing)
            for row in ("wait", "jab", "dair"):
                _require_success("load_" + row, session.load_row(row), session)
                for frame in range(1, 21):
                    label = "pose.{}.{}.{}".format(facing, row, frame)
                    success = session.set_frame(frame)
                    _require_success(label, success, session)
                    info = frame_info()
                    applied = pose.apply_frame(arm, info, jm, cal)
                    bpy.context.view_layer.update()
                    verified = pose.verify_pose(arm, info, jm, eps=1e-3)
                    head_err = float(verified["max_err"])
                    rot_err = float(verified["rot_err"])
                    valid = (
                        bool(verified["ok"])
                        and verified["n"] == len(jm.by_index)
                        and not applied.skipped_mirrored
                        and not [j for j in applied.missing if j not in jm.skipped_synth]
                        and math.isfinite(head_err)
                        and math.isfinite(rot_err)
                        and head_err < 1e-3
                        and rot_err < 1e-3
                    )
                    check(
                        label, valid,
                        "max_head_err={:.9g} rot_err={:.9g} n={}".format(
                            head_err, rot_err, verified["n"]
                        ),
                    )
                    max_head_err = max(max_head_err, head_err)
                    max_rot_err = max(max_rot_err, rot_err)
                    poses += 1

        check("pose_count", poses == 120, "poses={}".format(poses))
        # The specified frames=40 counts 20 frames x 2 facings per row.
        print(
            "GENO_WB_POSE pose: max_head_err={:.9g} rot_err={:.9g} "
            "frames=40 facings=2 rows=3 poses={}".format(
                max_head_err, max_rot_err, poses
            ),
            flush=True,
        )
        summary.update(
            poses=poses, frames_per_row=40, facings=2,
            max_head_err=max_head_err, rot_err=max_rot_err,
        )

        options = SimpleNamespace(
            show_hit=True, show_hurt=True, show_ecb=True, show_floor=True
        )
        overlay_ids = None
        active_info = None
        for facing in (1, -1):
            fake.set_facing(facing)
            _require_success("overlay_row", session.load_row("jab"), session)
            _require_success("overlay_frame", session.set_frame(6), session)
            active_info = frame_info()
            counts = overlays.update(active_info, scene=scene, props=options)
            collection = overlays.ensure_collection(scene)
            visible_hits = _visible(collection, "GenoWB.hit.")
            visible_hurts = _visible(collection, "GenoWB.hurt.")
            check(
                "overlay_counts." + str(facing),
                counts == {"hit": 1, "hurt": 5}
                and len(visible_hits) == 1 and len(visible_hurts) == 5,
                "counts={!r}".format(counts),
            )
            hit = visible_hits[0]
            source = next(
                item for item in active_info["hitboxes"] if item["slot"] == 0
            )
            # frame_info producers use world, or pos for a world-space point.
            world = source["world"] if "world" in source else source["pos"]
            if isinstance(world, dict):
                world = (world["x"], world["y"], world["z"])
            center_error = _distance(
                _world_center(hit), space.to_blender_point(world)
            )
            check(
                "overlay_center." + str(facing),
                center_error < 1e-4,
                "error={:.9g}".format(center_error),
            )
            check(
                "overlay_hit_properties." + str(facing),
                hit.name == "GenoWB.hit.0"
                and hit.get("geno_wb_slot") == 0
                and hit.get("geno_wb_active") is True,
            )
            expected_color = overlays.SLOT_COLORS[0]
            material = hit.data.materials[0]
            check(
                "overlay_hit_color." + str(facing),
                material.name == "GenoWB.slot0"
                and all(abs(material.diffuse_color[i] - expected_color[i])
                        < 1e-6 for i in range(4)),
            )
            check(
                "overlay_hurt_wire." + str(facing),
                all(obj.display_type == "WIRE" for obj in visible_hurts),
            )
            if overlay_ids is None:
                overlay_ids = _identities(collection)
            else:
                check("overlay_facing_reuse", _identities(collection) == overlay_ids)

        first = overlays.ensure_collection(scene)
        second = overlays.ensure_collection(scene)
        matching_collections = [
            item.name for item in bpy.data.collections
            if item.name == overlays.COLLECTION
            or item.name.startswith(overlays.COLLECTION + ".")
        ]
        check(
            "overlay_collection_idempotent",
            first == second and matching_collections == [overlays.COLLECTION],
            repr(matching_collections),
        )
        collection = first
        ecb = bpy.data.objects["GenoWB.ecb"]
        floor = bpy.data.objects["GenoWB.floor"]
        check(
            "overlay_ecb",
            len(ecb.data.vertices) == 4 and ecb.display_type == "WIRE"
            and not ecb.hide_viewport and not ecb.hide_render,
        )
        floor_vertices = _world_vertices(floor)
        check(
            "overlay_floor",
            len(floor_vertices) == 4 and floor.display_type == "WIRE"
            and not floor.hide_viewport and not floor.hide_render
            and all(abs(vertex[2]) < 1e-6 for vertex in floor_vertices),
        )

        for frame in (4, 9):
            _require_success("inactive_frame", session.set_frame(frame), session)
            # Exercise the original scene-first call signature as well.
            counts = overlays.update(scene, frame_info(), options)
            check(
                "overlay_inactive." + str(frame),
                counts == {"hit": 0, "hurt": 5}
                and not _visible(collection, "GenoWB.hit.")
                and not bpy.data.objects["GenoWB.hit.0"]["geno_wb_active"],
            )
            check(
                "overlay_reuse." + str(frame),
                _identities(collection) == overlay_ids,
            )

        _require_success("active_again", session.set_frame(6), session)
        active_info = frame_info()
        options.show_hit = options.show_hurt = False
        options.show_ecb = options.show_floor = False
        counts = overlays.update(active_info, scene=scene, props=options)
        check(
            "overlay_toggles_off",
            counts == {"hit": 0, "hurt": 0}
            and all(obj.hide_viewport and obj.hide_render
                    for obj in collection.objects)
            and bpy.data.objects["GenoWB.hit.0"]["geno_wb_active"] is True,
        )
        options.show_hit = options.show_hurt = True
        options.show_ecb = options.show_floor = True
        counts = overlays.update(active_info, scene=scene, props=options)
        check(
            "overlay_toggles_on",
            counts == {"hit": 1, "hurt": 5}
            and _identities(collection) == overlay_ids,
        )

        object_names = list(overlay_ids)
        mesh_names = {obj.data.name for obj in collection.objects}
        material_names = {
            material.name for obj in collection.objects
            for material in obj.data.materials if material is not None
        }
        overlays.clear(scene)
        check(
            "overlay_clear",
            bpy.data.collections.get(overlays.COLLECTION) is None
            and all(bpy.data.objects.get(name) is None for name in object_names)
            and all(bpy.data.meshes.get(name) is None for name in mesh_names)
            and all(bpy.data.materials.get(name) is None
                    for name in material_names)
            and bpy.data.objects.get("SynthRig") == arm,
        )

        pose.apply_frame(arm, active_info, jm, cal)
        bpy.context.view_layer.update()
        hand_name = jm.by_index[8]
        before_mirror = _bone_state(arm, hand_name)
        mirrored = copy.deepcopy(active_info)
        mirrored_bone = next(
            bone for bone in mirrored["bones"] if bone["joint"] == 8
        )
        matrix = list(mirrored_bone["mtx"])
        for column in range(4):
            matrix[column] *= -1.0
        mirrored_bone["mtx"] = matrix
        applied = pose.apply_frame(arm, mirrored, jm, cal)
        bpy.context.view_layer.update()
        after_mirror = _bone_state(arm, hand_name)
        check("mirrored_joint_skipped", 8 in applied.skipped_mirrored)
        check(
            "mirrored_joint_unchanged",
            max(_matrix_error(a, b)
                for a, b in zip(before_mirror, after_mirror)) < 1e-6,
        )

        before_disconnect = _bone_state(arm, hand_name)
        fake.stop()
        stopped = True
        started = time.monotonic()
        success = session.set_frame(3)
        elapsed = time.monotonic() - started
        bpy.context.view_layer.update()
        check(
            "server_killed_returns_false",
            success is False and elapsed < 3.0,
            "result={!r} seconds={:.6f} {}".format(
                success, elapsed, _session_detail(session)
            ),
        )
        check(
            "server_killed_preserves_pose",
            _bone_state(arm, hand_name) == before_disconnect,
        )
        summary["server_killed_seconds"] = elapsed

        try:
            import selftest_edit
        except ImportError as exc:
            # Only an absent optional module is a skip. Missing dependencies
            # inside an installed selftest_edit must fail the overall test.
            if exc.name != "selftest_edit":
                raise
            print(
                "GENO_WB_SKIP edit selftest_edit.py is not available",
                flush=True,
            )
            summary["edit_checks"] = "unavailable"
        else:
            selftest_edit.run(check)
            summary["edit_checks"] = "ran"

        return summary
    finally:
        already_failing = sys.exc_info()[0] is not None
        cleanup_errors = []

        def cleanup(name, operation):
            try:
                operation()
            except Exception as exc:
                cleanup_errors.append(name + ": " + str(exc))

        if arm is not None:
            cleanup("release_preview", lambda: pose.release_preview(arm))
        cleanup("overlays", lambda: overlays.clear(scene))
        for transport in transports:
            cleanup("client", transport.close)
        if not stopped:
            cleanup("fake", fake.stop)
        if cleanup_errors:
            detail = "; ".join(cleanup_errors)
            if already_failing:
                print("GENO_WB_CLEANUP FAIL " + _one_line(detail), flush=True)
            else:
                raise RuntimeError(detail)


def main(argv=None):
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", help="Directory for the synthetic plan and results")
    args = parser.parse_args(argv)
    _CHECKS.clear()
    out_dir = None

    try:
        with ExitStack() as stack:
            if args.out:
                out_dir = Path(args.out).resolve()
            else:
                out_dir = Path(stack.enter_context(
                    tempfile.TemporaryDirectory(prefix="geno-wb-selftest-")
                ))
            out_dir.mkdir(parents=True, exist_ok=True)
            summary = _run(out_dir)
            summary.update(ok=True, checks=_CHECKS)
            (out_dir / "selftest_results.json").write_text(
                json.dumps(summary, indent=2) + "\n", encoding="utf-8"
            )
    except Exception as exc:
        traceback.print_exc()
        if out_dir is not None and out_dir.is_dir():
            try:
                (out_dir / "selftest_results.json").write_text(
                    json.dumps(
                        {"ok": False, "error": str(exc), "checks": _CHECKS},
                        indent=2,
                    ) + "\n",
                    encoding="utf-8",
                )
            except OSError:
                pass
        print("GENO_WB_SELFTEST FAIL " + _one_line(exc), flush=True)
        return 1

    print("GENO_WB_SELFTEST OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
