"""Task 9 integration checks, called by Task 8 as selftest_edit.run(check).

Requires the add-on to be registered. Uses a fresh synthetic server and session
without pose or overlay hooks. Only RNA/operator checks require the existing
Blender scene. The real scrub timer callback is pumped explicitly because a
background --python script does not yield to Blender's event loop.
"""

import math
import sys
from pathlib import Path


def _package():
    """Import the add-on as a package (geno_workbench.*) and register it.

    The flat modules the main self-test uses are different module objects from the
    ones the registered operators import, so the edit flow must use the package's.
    Returns (package, registered_here)."""
    parent = str(Path(__file__).resolve().parent.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    import bpy
    import geno_workbench

    if hasattr(bpy.types.Scene, "geno_wb"):
        return geno_workbench, False
    geno_workbench.register()
    return geno_workbench, True


def run(check) -> None:
    """Register the add-on if needed, run the edit flow, unregister what we registered."""
    package, registered_here = _package()
    try:
        _flow(check)
    finally:
        if registered_here:
            package.unregister()


def _flow(check) -> None:
    import bpy
    from geno_workbench import api, client, operators, props
    from geno_workbench.fake_engine import FakeWorkbench

    def require(name, condition, detail=""):
        check(name, bool(condition), detail)
        if not condition:
            raise AssertionError(detail or name)

    scene = bpy.context.scene
    settings = getattr(scene, "geno_wb", None)
    if settings is None:
        raise AssertionError("add-on did not register the Scene property")
    original_scene_frame = scene.frame_current
    original_session = api.session()
    original_pending = original_session.pending_frame
    original_handlers = (
        props._frame_handler, props._row_handler, props._problem_handler
    )
    timer_was_registered = bpy.app.timers.is_registered(
        operators._flush_pending_timer
    )
    saved_names = (
        "row", "frame", "status", "stale", "move",
        "problem_index", "hitbox_index", "edit_row", "edit_ordinal",
        "edit_baseline", "edit_source_key",
    ) + tuple("edit_" + field for field in original_session.edit_fields)
    saved = {name: getattr(settings, name) for name in saved_names}

    operators.stop_playback()
    operators._cancel_scrub()
    fake = FakeWorkbench()
    value = None
    try:
        port = fake.start()
        value = api.WbSession(
            lambda: client.McpClient(
                host="127.0.0.1", port=port, timeout=2.0
            )
        )
        value.prefetch = False   # counted engine calls must be the scrub's own, not the cache fill's
        api._session = value
        operators.install_callbacks()
        require("edit-flow-connect", value.connect(), value.last_error)
        require("edit-flow-rows", value.refresh_rows(), value.last_error)
        require(
            "edit-flow-load",
            value.load_row("jab", refresh_hitboxes=True),
            value.last_error,
        )

        before_sets = sum(name == "set_frame" for name, args in fake.calls)
        previous_info = value.info
        for frame in range(10, 31):
            settings.frame = frame
        require(
            "edit-flow-queued",
            value.pending_frame == 30
            and value.info is previous_info
            and sum(name == "set_frame" for name, args in fake.calls) == before_sets
            and bpy.app.timers.is_registered(operators._flush_pending_timer),
        )

        # Dispatch the registered callback once without relying on GUI timing.
        bpy.app.timers.unregister(operators._flush_pending_timer)
        interval = operators._flush_pending_timer()
        require(
            "edit-flow-scrub",
            interval is None
            and value.pending_frame is None
            and value.info["frame"] == 30
            and settings.frame == 30
            and sum(name == "set_frame" and args.get("frame") == 30 for name, args in fake.calls) == 1,   # the 11 queued frames cost one engine call
            value.last_error,
        )
        require("edit-flow-source", bool(value.hitboxes))

        frames = []
        value.on_frame.append(lambda current: frames.append(current.frame))
        engine_info = value.info
        new_size = float(value.hitboxes[0].get("size", 1.0)) + 0.5
        result = bpy.ops.geno_wb.edit_hitbox(
            row="jab", ordinal=0, size=new_size
        )
        require(
            "edit-flow-stale",
            result == {"FINISHED"} and settings.stale and value.stale and fake.stale,
            value.last_error,
        )
        require(
            "edit-flow-source-only",
            value.info is engine_info
            and not frames
            and math.isclose(
                float(value.hitboxes[0]["size"]), new_size,
                rel_tol=1e-6, abs_tol=1e-6,
            ),
        )
        edit_args = [
            args for name, args in fake.calls if name == "edit_hitbox"
        ][-1]
        require(
            "edit-flow-sparse",
            set(edit_args) == {"row", "ordinal", "size"},
        )

        result = bpy.ops.geno_wb.rebuild_reload()
        require(
            "edit-flow-reload",
            result == {"FINISHED"}
            and not settings.stale and not value.stale and not fake.stale
            and value.row == "jab" and value.info["frame"] == 30
            and frames == [30],
            value.last_error,
        )

        # Bone dropdown, Add hitbox, Delete hitbox through the registered operators.
        ids = [item[0] for item in props.role_items(settings, None) if item[0]]
        require(
            "edit-flow-bone-dropdown",
            "CHEST" in ids and "HAND_R" in ids
            and settings.edit_bone == value.hitboxes[settings.hitbox_index]["joint"],
            f"{ids} {settings.edit_bone}",
        )
        count = len(value.hitboxes)
        result = bpy.ops.geno_wb.add_hitbox(frame=9, bone="CHEST")
        require(
            "edit-flow-add",
            result == {"FINISHED"} and len(value.hitboxes) == count + 1
            and settings.stale and settings.hitbox_index == value.last_added
            and settings.edit_bone == "CHEST" and len(settings.hitbox_items) == count + 1,
            f"{value.last_error} idx={settings.hitbox_index} bone={settings.edit_bone}",
        )
        result = bpy.ops.geno_wb.delete_hitbox()
        require(
            "edit-flow-delete",
            result == {"FINISHED"} and len(value.hitboxes) == count,
            value.last_error,
        )
        require("edit-flow-reload-2", bpy.ops.geno_wb.rebuild_reload() == {"FINISHED"}, value.last_error)

        # Exercise panel Apply, including preservation of unsaved RNA values
        # through an unrelated frame update.
        settings.edit_size = float(settings.edit_size) + 0.25
        require("edit-flow-draft-frame", value.set_frame(40), value.last_error)
        require(
            "edit-flow-draft",
            set(props.changed_hitbox_fields(settings)) == {"size"},
        )
        result = bpy.ops.geno_wb.edit_hitbox()
        require(
            "edit-flow-panel-apply",
            result == {"FINISHED"} and settings.stale,
            value.last_error,
        )

        fake.fail_next = "build failed"
        failed = value.rebuild_reload()
        require(
            "edit-flow-failure",
            failed is False and settings.stale and value.stale
            and "build failed" in value.last_error,
            value.last_error,
        )
        result = bpy.ops.geno_wb.rebuild_reload()
        require(
            "edit-flow-retry",
            result == {"FINISHED"} and not settings.stale
            and not value.stale and not fake.stale,
            value.last_error,
        )
        require(
            "edit-flow-scene-independent",
            scene.frame_current == original_scene_frame,
        )
        check('edit-flow', True)
    finally:
        operators.stop_playback()
        operators._cancel_scrub()
        if value is not None:
            value.on_change = None
            value.disconnect()
        try:
            fake.stop()
        finally:
            api._session = original_session
            original_session.pending_frame = original_pending
            props.set_frame_handler(original_handlers[0])
            props.set_row_handler(original_handlers[1])
            props.set_problem_handler(original_handlers[2])
            props.sync_from_session(original_session, settings)
            with props.suspend_frame_updates():
                for name, item in saved.items():
                    if name == "edit_bone":
                        props.set_edit_bone(settings, item)   # a dropdown: "" is no choice
                    else:
                        setattr(settings, name, item)
                settings.playing = False
            if timer_was_registered and original_pending is not None:
                operators._ensure_scrub_timer()


if __name__ == "__main__":
    # Standalone: blender --background --factory-startup --python selftest_edit.py
    def _check(name, cond, detail=""):
        print("GENO_WB_CHECK {} {} {}".format(name, "OK" if cond else "FAIL", detail).rstrip(), flush=True)
        if not cond:
            raise SystemExit(1)

    run(_check)
    print("GENO_WB_SELFTEST OK", flush=True)
