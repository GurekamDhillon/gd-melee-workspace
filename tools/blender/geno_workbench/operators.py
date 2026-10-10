"""Workbench operators, coalesced scrubbing and owned-server lifecycle."""

from pathlib import Path
import os
import subprocess

import time

import bpy
from bpy.props import EnumProperty, FloatProperty, IntProperty, StringProperty

try:
    from . import api, client, launch, props
except ImportError:
    import api
    import client
    import launch
    import props


STRINGS = props.STRINGS
_server_process = None
_active_player = None
PLAY_STATS = {"shown": 0, "skipped": 0, "max_ms": 0}


def _redraw_ui():
    wm = getattr(bpy.context, "window_manager", None)
    for window in getattr(wm, "windows", ()):
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()


_CACHE_SHOWN = [""]


def _cache_timer():
    """Main-thread side of the background frame cache: progress text, redraws, length hints."""
    value = api.session()
    text = value.cache_text()
    if text != _CACHE_SHOWN[0]:
        _CACHE_SHOWN[0] = text
        _redraw_ui()
    return 0.25 if value.cache.loading else 0.5


def install_callbacks():
    value = api.session()
    value.prefetch = True
    if not bpy.app.timers.is_registered(_cache_timer):
        bpy.app.timers.register(_cache_timer, first_interval=0.25, persistent=True)
    value.on_change = props.sync_from_session
    props.set_frame_handler(_queue_frame)
    props.set_row_handler(_select_row)
    props.set_problem_handler(_select_problem)
    props.sync_from_session(value)


def _flush_pending_timer():
    """One bounded request per tick; returning None unregisters this timer."""
    value = api.session()
    if value.pending_frame is None:
        return None
    if not value.flush_pending():
        return None
    return 0.05 if value.pending_frame is not None else None


def _ensure_scrub_timer():
    if not bpy.app.timers.is_registered(_flush_pending_timer):
        bpy.app.timers.register(_flush_pending_timer, first_interval=0.05)


def _cancel_scrub():
    if bpy.app.timers.is_registered(_flush_pending_timer):
        bpy.app.timers.unregister(_flush_pending_timer)
    api.session().pending_frame = None


def stop_playback():
    global _active_player
    if _active_player is not None:
        try:
            _active_player._stop()
        except ReferenceError:
            # The operator died (an exception in modal frees its RNA).
            _active_player = None


def _queue_frame(settings, context):
    # Property updates only enqueue work and arm the timer; no client call.
    stop_playback()
    if api.session().coalesced_set_frame(settings.frame):
        _ensure_scrub_timer()


def _select_row(settings, context):
    value = api.session()
    name = settings.move
    if name == props.NO_ROW or name == value.source_row:
        return
    stop_playback()
    _cancel_scrub()
    value.load_row(name, refresh_hitboxes=True)
    props.sync_from_session(value, settings)


def _navigate_problem(settings, index):
    value = api.session()
    stop_playback()
    _cancel_scrub()
    success = value.goto_problem(index)
    props.sync_from_session(value, settings)
    if success:
        ordinal = value.problems[index].get("ordinal", 0)
        with props.suspend_frame_updates():
            settings.problem_index = index
            settings.hitbox_index = (
                ordinal if 0 <= ordinal < len(value.hitboxes) else -1
            )
        props.sync_editor(value, settings)
    return success


def _select_problem(settings, context):
    _navigate_problem(settings, settings.problem_index)


def owned_server_running():
    return _server_process is not None and _server_process.poll() is None


def stop_owned_server():
    """Terminate only the Popen returned to this add-on by start_serve."""
    global _server_process
    process = _server_process
    if process is None:
        return
    try:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1.0)
    except (OSError, subprocess.TimeoutExpired) as exc:
        if process.poll() is None:
            raise client.WbError(STRINGS["stop_failed"].format(error=exc)) from exc
    finally:
        if process.poll() is not None:
            _server_process = None


def shutdown():
    """Release timers, callbacks, the connection and the owned server."""
    stop_playback()
    _cancel_scrub()
    if bpy.app.timers.is_registered(_cache_timer):
        bpy.app.timers.unregister(_cache_timer)
    value = api.session()
    value.prefetch = False
    value.cache.reset("shutdown")
    value.on_change = None
    props.set_frame_handler(None)
    props.set_row_handler(None)
    props.set_problem_handler(None)
    success = value.disconnect()
    try:
        stop_owned_server()
    except client.WbError as exc:
        success = value.report_error(exc)
    return success


def server_answers(port, timeout=2.0):
    """True when something on 127.0.0.1:port speaks the workbench protocol (engine_status)."""
    if not isinstance(port, int) or not 1 <= port <= 65535:
        return False
    probe = client.McpClient(host="127.0.0.1", port=port, timeout=timeout)
    try:
        probe.connect()
        probe.call("engine_status")
        return True
    except (client.WbError, OSError, ValueError):
        return False
    finally:
        probe.close()


def _project_root(project):
    """Project workspace fallback; GW_ROOT selects the shared config first."""
    if os.environ.get("GW_ROOT"):
        return None
    for directory in (project, *project.parents):
        if (directory / ".git").exists():
            return directory
    return None


def _configure_client(settings):
    host = settings.host.strip().lower()
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise client.WbError(STRINGS["non_loopback"])
    port = int(settings.port)
    if not 1 <= port <= 65535:
        raise client.WbError(STRINGS["invalid_port"])
    settings.host = "127.0.0.1"
    api.session().client_factory = lambda: client.McpClient(
        host="127.0.0.1", port=port, timeout=10.0
    )


def _finish(operator, context, success):
    value = api.session()
    props.sync_from_session(value, context.scene.geno_wb)
    if not success:
        # a refused action (no build / no roles) has a status but no error: a warning, not a failure
        operator.report({"ERROR"} if value.last_error else {"WARNING"}, value.last_error or value.status)
        return {"CANCELLED"}
    return {"FINISHED"}


class GENO_WB_OT_start_server(bpy.types.Operator):
    bl_idname = "geno_wb.start_server"
    bl_label = STRINGS["start_server"]
    bl_description = STRINGS["start_server_help"]

    @classmethod
    def poll(cls, context):
        return props.poll_ready(cls,
            (not owned_server_running(), STRINGS["server_already_running"]),
            (not api.session().connected, STRINGS["disconnect_first"]))

    def execute(self, context):
        global _server_process
        value = api.session()
        settings = context.scene.geno_wb
        try:
            if owned_server_running():
                raise client.WbError(STRINGS["server_already_running"])
            if value.connected:
                raise client.WbError(STRINGS["disconnect_first"])
            if settings.port and server_answers(int(settings.port)):
                # A server (e.g. launch_goku's) is already up on this port: use it, do not start a second
                # launcher that has no engine.
                message = STRINGS["server_reused"].format(port=int(settings.port))
                success = value.set_status(message)
                self.report({"INFO"}, message)
                return _finish(self, context, success)
            if not settings.project.strip():
                raise client.WbError(STRINGS["project_required"])
            project = Path(bpy.path.abspath(settings.project)).expanduser().resolve()
            if not project.is_dir():
                raise client.WbError(
                    STRINGS["invalid_project"].format(path=project)
                )
            if settings.launcher_exe.strip():
                executable = Path(
                    bpy.path.abspath(settings.launcher_exe)
                ).expanduser().resolve()
                if not executable.is_file():
                    raise client.WbError(
                        STRINGS["invalid_launcher"].format(path=executable)
                    )
                exe = str(executable)
            else:
                exe = launch.find_launcher(root=_project_root(project))
                if not exe:
                    raise client.WbError(STRINGS["launcher_missing"])
            argv, serve_env = launch.serve_launch(
                exe, str(project),
                engine_exe=bpy.path.abspath(settings.engine_exe) if settings.engine_exe.strip() else "",
                mods_dir=bpy.path.abspath(settings.mods_dir) if settings.mods_dir.strip() else "",
                iso=bpy.path.abspath(settings.iso_path) if settings.iso_path.strip() else "",
                root=_project_root(project),
            )
            process, port = launch.start_serve(argv, timeout=120, env=serve_env)
            _server_process = process
            settings.host = "127.0.0.1"
            settings.port = port
            success = value.set_status(
                STRINGS["server_started"].format(port=port)
            )
        except (client.WbError, OSError, ValueError, TypeError) as exc:
            success = value.report_error(exc)
        return _finish(self, context, success)


class GENO_WB_OT_connect(bpy.types.Operator):
    bl_idname = "geno_wb.connect"
    bl_label = STRINGS["connect"]
    bl_description = STRINGS["connect_help"]

    def execute(self, context):
        stop_playback()
        _cancel_scrub()
        value = api.session()
        try:
            _configure_client(context.scene.geno_wb)
            success = value.connect()
            if success:
                success = value.refresh_rows()
        except (client.WbError, OSError, ValueError, TypeError) as exc:
            success = value.report_error(exc)
        return _finish(self, context, success)


class GENO_WB_OT_disconnect(bpy.types.Operator):
    bl_idname = "geno_wb.disconnect"
    bl_label = STRINGS["disconnect"]
    bl_description = STRINGS["disconnect_help"]

    def execute(self, context):
        stop_playback()
        _cancel_scrub()
        context.scene.geno_wb.playing = False
        value = api.session()
        success = value.disconnect()
        try:
            stop_owned_server()
        except client.WbError as exc:
            success = value.report_error(exc)
        return _finish(self, context, success)


class GENO_WB_OT_engine_restart(bpy.types.Operator):
    bl_idname = "geno_wb.engine_restart"
    bl_label = STRINGS["restart_engine"]
    bl_description = STRINGS["restart_engine_help"]

    @classmethod
    def poll(cls, context):
        return props.poll_ready(cls, (api.session().connected, STRINGS["not_connected"]))

    def execute(self, context):
        stop_playback()
        _cancel_scrub()
        context.scene.geno_wb.playing = False
        return _finish(self, context, api.session().engine_restart())


class GENO_WB_OT_refresh_rows(bpy.types.Operator):
    bl_idname = "geno_wb.refresh_rows"
    bl_label = STRINGS["refresh_rows"]
    bl_description = STRINGS["refresh_rows_help"]

    @classmethod
    def poll(cls, context):
        return props.poll_ready(cls, (api.session().connected, STRINGS["not_connected"]))

    def execute(self, context):
        return _finish(self, context, api.session().refresh_rows())


class GENO_WB_OT_load_row(bpy.types.Operator):
    bl_idname = "geno_wb.load_row"
    bl_label = STRINGS["load_row"]
    bl_description = STRINGS["load_row_help"]
    bl_property = "row"

    row: EnumProperty(name=STRINGS["row"], items=props.row_items)

    @classmethod
    def poll(cls, context):
        return props.poll_ready(cls, (api.session().connected, STRINGS["not_connected"]))

    def invoke(self, context, event):
        context.window_manager.invoke_search_popup(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        stop_playback()
        _cancel_scrub()
        value = api.session()
        if self.row == props.NO_ROW:
            return _finish(self, context, value.report_error(STRINGS["row_required"]))
        return _finish(
            self, context, value.load_row(self.row, refresh_hitboxes=True)
        )


class GENO_WB_OT_step(bpy.types.Operator):
    bl_idname = "geno_wb.step"
    bl_label = STRINGS["step"]
    bl_description = STRINGS["step_help"]

    n: IntProperty(name=STRINGS["step_count"], default=1)

    @classmethod
    def poll(cls, context):
        value = api.session()
        return props.poll_ready(cls,
            (value.connected, STRINGS["not_connected"]),
            (value.info is not None, STRINGS["no_frame"]))

    def execute(self, context):
        target = max(0, min(600, context.scene.geno_wb.frame + self.n))
        stop_playback()
        _cancel_scrub()
        return _finish(self, context, api.session().set_frame(target))


class GENO_WB_OT_play(bpy.types.Operator):
    bl_idname = "geno_wb.play"
    bl_label = STRINGS["play"]
    bl_description = STRINGS["play_help"]

    @classmethod
    def poll(cls, context):
        value = api.session()
        if _active_player is not None:
            return True
        return props.poll_ready(cls,
            (value.connected, STRINGS["not_connected"]),
            (value.info is not None, STRINGS["no_frame"]))

    def _stop(self):
        global _active_player
        import traceback
        frame = traceback.extract_stack(limit=3)[0]
        PLAY_STATS["stopped_at"] = "%s:%d" % (frame.name, frame.lineno)   # which branch ended playback (diagnostic)
        timer = getattr(self, "_timer", None)
        self._timer = None
        if timer is not None:
            try:
                self._wm.event_timer_remove(timer)
            except (ReferenceError, RuntimeError):
                pass
        settings = getattr(self, "_settings", None)
        # A superseded modal instance (pause then Play again) must not clear the new player's flag.
        if settings is not None and (_active_player is self or _active_player is None):
            try:
                settings.playing = False
            except ReferenceError:
                pass
        if _active_player is self:
            _active_player = None

    def execute(self, context):
        global _active_player
        value = api.session()
        if _active_player is not None:
            stop_playback()
            return _finish(self, context, value.set_status(STRINGS["play_paused"]))
        if value.row_frames() == 1 and value.frame >= 1:
            return _finish(
                self, context,
                value.set_status(STRINGS["play_end"].format(frame=value.frame)),
            )
        if value.pending_frame is not None and not value.flush_pending():
            _cancel_scrub()
            return _finish(self, context, False)
        _cancel_scrub()
        if value.frame >= 600:
            return _finish(self, context, value.set_status(STRINGS["play_limit"]))
        if context.window is None:
            return _finish(
                self, context,
                value.report_error(STRINGS["play_window_required"]),
            )
        self._wm = context.window_manager
        self._settings = context.scene.geno_wb
        self._timer = None
        render = context.scene.render
        self._rate = api.playback_rate(self._settings.play_speed, render.fps / (render.fps_base or 1.0))   # logic frames per second: real game speed x Speed setting
        self._origin = max(0, value.frame - 1)
        self._t0 = self._last_tick = time.monotonic()
        for key in PLAY_STATS:
            PLAY_STATS[key] = 0
        value.start_prefetch()
        try:
            self._timer = self._wm.event_timer_add(
                1 / min(60.0, self._rate), window=context.window
            )
            self._settings.playing = True
            _active_player = self
            self._wm.modal_handler_add(self)
            if not value.set_status(STRINGS["play_started"]):
                self._stop()
                return _finish(self, context, False)
        except (RuntimeError, ValueError) as exc:
            self._stop()
            return _finish(self, context, value.report_error(exc))
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        value = api.session()
        if _active_player is not self or not self._settings.playing:
            self._stop()
            return {"CANCELLED"}
        if not value.connected:
            self._stop()
            return _finish(self, context, False)
        if event.type in {"ESC", "RIGHTMOUSE"}:
            self._stop()
            value.set_status(STRINGS["play_paused"])
            return {"CANCELLED"}
        # Event has no .timer in the Python API; any window timer arrives as
        # TIMER, so pace by the wall clock: the frame shown is where the clock says
        # we are, and frames are skipped (not delayed) when posing is slow.
        if event.type != "TIMER":
            return {"PASS_THROUGH"}
        began = time.perf_counter()
        now = time.monotonic()
        limit = value.row_frames()
        if self._settings.frame >= 600 or value.frame >= 600:
            self._stop()
            return _finish(self, context, value.set_status(STRINGS["play_limit"]))
        cap = limit or 600
        position = self._origin + int((now - self._t0) * self._rate)   # 0-based frames since frame 1
        if position >= cap:
            if cap <= 1 or not self._settings.loop:
                if value.frame < cap and not self._show(value, cap):
                    self._stop()
                    return _finish(self, context, False)
                self._stop()
                return _finish(
                    self, context,
                    value.set_status(STRINGS["play_end"].format(frame=value.frame)),
                )
            position %= cap
        target = position + 1
        if target == value.frame:
            return {"PASS_THROUGH"}
        if not value.cache.has(value.loaded_row, target) and value.cache.loading:
            # still caching this far: hold the picture, and do not let the clock run away
            self._t0 += now - self._last_tick
            self._last_tick = now
            return {"PASS_THROUGH"}
        self._last_tick = now
        skipped = max(0, (target - value.frame - 1) if target > value.frame else 0)
        if not self._show(value, target):
            self._stop()
            return _finish(self, context, False)
        PLAY_STATS["shown"] += 1
        PLAY_STATS["skipped"] += skipped
        PLAY_STATS["max_ms"] = max(PLAY_STATS["max_ms"], (time.perf_counter() - began) * 1000)
        return {"RUNNING_MODAL"}

    def _show(self, value, frame):
        ok = value.set_frame(frame)
        if ok:
            props.sync_from_session(value, self._settings)
        return ok

    def cancel(self, context):
        self._stop()


class GENO_WB_OT_run_checks(bpy.types.Operator):
    bl_idname = "geno_wb.run_checks"
    bl_label = STRINGS["run_checks"]
    bl_description = STRINGS["run_checks_help"]

    @classmethod
    def poll(cls, context):
        value = api.session()
        return props.poll_ready(cls,
            (value.connected, STRINGS["not_connected"]),
            (value.has_roles, STRINGS["no_roles"]))

    def execute(self, context):
        return _finish(self, context, api.session().run_checks())


class GENO_WB_OT_goto_problem(bpy.types.Operator):
    bl_idname = "geno_wb.goto_problem"
    bl_label = STRINGS["goto_problem"]
    bl_description = STRINGS["goto_problem_help"]

    index: IntProperty(name=STRINGS["problem_index"], default=-1, min=-1)

    @classmethod
    def poll(cls, context):
        value = api.session()
        settings = getattr(context.scene, "geno_wb", None)
        return props.poll_ready(cls,
            (value.connected, STRINGS["not_connected"]),
            (settings is not None and 0 <= settings.problem_index < len(value.problems), STRINGS["problem_missing"]))

    def execute(self, context):
        settings = context.scene.geno_wb
        index = self.index if self.index >= 0 else settings.problem_index
        return _finish(self, context, _navigate_problem(settings, index))


class GENO_WB_OT_suggest_bone(bpy.types.Operator):
    bl_idname = "geno_wb.suggest_bone"
    bl_label = STRINGS["suggest_bone"]
    bl_description = STRINGS["suggest_bone_help"]

    @classmethod
    def poll(cls, context):
        value = api.session()
        settings = getattr(context.scene, "geno_wb", None)
        return props.poll_ready(cls,
            (value.connected, STRINGS["not_connected"]),
            (value.has_roles, STRINGS["no_roles"]),
            (settings is not None and 0 <= settings.hitbox_index < len(value.hitboxes), STRINGS["editor_missing"]))

    def execute(self, context):
        value = api.session()
        settings = context.scene.geno_wb
        success = value.suggest_bone(settings.hitbox_index)
        if success:
            suggested = (value.suggestion or {}).get("suggested")
            if suggested is not None and suggested != "":
                props.set_edit_bone(settings, str(suggested))
        return _finish(self, context, success)


class GENO_WB_OT_edit_hitbox(bpy.types.Operator):
    bl_idname = "geno_wb.edit_hitbox"
    bl_label = STRINGS["edit_hitbox"]
    bl_description = STRINGS["edit_hitbox_help"]

    row: StringProperty(name=STRINGS["row"])
    ordinal: IntProperty(name=STRINGS["ordinal"], default=-1, min=-1)
    bone: StringProperty(name=STRINGS["bone"])
    damage: FloatProperty(name=STRINGS["damage"], min=0.0)
    size: FloatProperty(name=STRINGS["size"], min=0.0)
    x: FloatProperty(name=STRINGS["x"])
    y: FloatProperty(name=STRINGS["y"])
    z: FloatProperty(name=STRINGS["z"])
    angle: IntProperty(name=STRINGS["angle"], min=0)
    kbg: IntProperty(name=STRINGS["kbg"], min=0)
    fkb: IntProperty(name=STRINGS["fkb"], min=0)
    bkb: IntProperty(name=STRINGS["bkb"], min=0)
    start_frame: IntProperty(name=STRINGS["start_frame"], default=1, min=0)
    end_frame: IntProperty(name=STRINGS["end_frame"], default=1, min=0)

    @classmethod
    def poll(cls, context):
        return props.poll_ready(cls, (api.session().connected, STRINGS["not_connected"]))

    def execute(self, context):
        value = api.session()
        settings = context.scene.geno_wb
        row = self.row or value.source_row
        ordinal = self.ordinal if self.ordinal >= 0 else settings.hitbox_index
        try:
            # Script calls send only explicitly set properties. A panel Apply
            # button has no field arguments and uses the editor's RNA baseline.
            changes = {
                field: getattr(self, field)
                for field in value.edit_fields
                if self.properties.is_property_set(field)
            }
            if not changes:
                if (
                    settings.edit_row != row
                    or settings.edit_ordinal != ordinal
                    or ordinal < 0
                ):
                    raise client.WbError(STRINGS["editor_missing"])
                changes = props.changed_hitbox_fields(settings)
            if not changes:
                return _finish(
                    self, context, value.set_status(STRINGS["no_changes"])
                )
            stop_playback()
            _cancel_scrub()
            success = value.edit_hitbox(row=row, ordinal=ordinal, **changes)
        except (client.WbError, ValueError, TypeError) as exc:
            success = value.report_error(exc)
        return _finish(self, context, success)


class GENO_WB_OT_add_hitbox(bpy.types.Operator):
    bl_idname = "geno_wb.add_hitbox"
    bl_label = STRINGS["add_hitbox"]
    bl_description = STRINGS["add_hitbox_help"]

    row: StringProperty(name=STRINGS["row"])
    frame: IntProperty(name=STRINGS["start_frame"], default=-1, min=-1)
    bone: StringProperty(name=STRINGS["bone"])

    @classmethod
    def poll(cls, context):
        value = api.session()
        return value.connected and bool(value.source_row)

    def execute(self, context):
        value = api.session()
        settings = context.scene.geno_wb
        try:
            # The limb Suggest limb picked, else nothing: the server defaults to the floor anchor.
            bone = self.bone or str((value.suggestion or {}).get("suggested") or "")
            frame = self.frame if self.frame >= 0 else value.frame
            stop_playback()
            _cancel_scrub()
            success = value.add_hitbox(
                frame=frame, bone=bone or None, row=self.row or value.source_row
            )
            if success and value.last_added is not None:
                with props.suspend_frame_updates():
                    settings.hitbox_index = value.last_added   # _finish syncs the editor onto it
        except (client.WbError, ValueError, TypeError) as exc:
            success = value.report_error(exc)
        return _finish(self, context, success)


class GENO_WB_OT_delete_hitbox(bpy.types.Operator):
    bl_idname = "geno_wb.delete_hitbox"
    bl_label = STRINGS["delete_hitbox"]
    bl_description = STRINGS["delete_hitbox_help"]

    row: StringProperty(name=STRINGS["row"])
    ordinal: IntProperty(name=STRINGS["ordinal"], default=-1, min=-1)

    @classmethod
    def poll(cls, context):
        return api.session().connected

    def execute(self, context):
        value = api.session()
        settings = context.scene.geno_wb
        try:
            ordinal = self.ordinal if self.ordinal >= 0 else settings.hitbox_index
            if ordinal < 0:
                raise client.WbError(STRINGS["editor_missing"])
            stop_playback()
            _cancel_scrub()
            success = value.delete_hitbox(ordinal, row=self.row or value.source_row)
        except (client.WbError, ValueError, TypeError) as exc:
            success = value.report_error(exc)
        return _finish(self, context, success)


class GENO_WB_OT_rebuild_reload(bpy.types.Operator):
    bl_idname = "geno_wb.rebuild_reload"
    bl_label = STRINGS["rebuild_reload"]
    bl_description = STRINGS["rebuild_reload_help"]

    @classmethod
    def poll(cls, context):
        value = api.session()
        return props.poll_ready(cls,
            (value.connected, STRINGS["not_connected"]),
            (value.can_rebuild, STRINGS["rebuild_unavailable"]))

    def execute(self, context):
        stop_playback()
        _cancel_scrub()
        return _finish(self, context, api.session().rebuild_reload())


CLASSES = (
    GENO_WB_OT_start_server,
    GENO_WB_OT_connect,
    GENO_WB_OT_disconnect,
    GENO_WB_OT_engine_restart,
    GENO_WB_OT_refresh_rows,
    GENO_WB_OT_load_row,
    GENO_WB_OT_step,
    GENO_WB_OT_play,
    GENO_WB_OT_run_checks,
    GENO_WB_OT_goto_problem,
    GENO_WB_OT_suggest_bone,
    GENO_WB_OT_edit_hitbox,
    GENO_WB_OT_add_hitbox,
    GENO_WB_OT_delete_hitbox,
    GENO_WB_OT_rebuild_reload,
)


# Registered/unregistered with the existing operator class lifecycle.
try:
    from .operators_nla import CLASSES as NLA_CLASSES
except ImportError:
    from operators_nla import CLASSES as NLA_CLASSES
CLASSES += NLA_CLASSES
