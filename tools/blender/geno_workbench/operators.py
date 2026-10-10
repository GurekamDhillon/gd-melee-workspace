"""Connection operators and ownership of the add-on's optional server."""

from pathlib import Path
import subprocess

import bpy

try:
    from . import api, client, launch, props
except ImportError:
    import api
    import client
    import launch
    import props


STRINGS = props.STRINGS
_server_process = None


def install_callbacks():
    value = api.session()
    value.on_change = props.sync_from_session
    props.sync_from_session(value)


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
            raise client.WbError(
                STRINGS["stop_failed"].format(error=exc)
            ) from exc
    finally:
        if process.poll() is not None:
            _server_process = None


def shutdown():
    """Release callbacks, the connection, and any server owned by this module."""
    value = api.session()
    value.on_change = None
    props.set_frame_handler(None)
    success = value.disconnect()
    try:
        stop_owned_server()
    except client.WbError as exc:
        success = value.report_error(exc)
    return success


def _project_root(project):
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
        operator.report({"ERROR"}, value.last_error or value.status)
        return {"CANCELLED"}
    return {"FINISHED"}


class GENO_WB_OT_start_server(bpy.types.Operator):
    bl_idname = "geno_wb.start_server"
    bl_label = STRINGS["start_server"]
    bl_description = STRINGS["start_server_help"]

    def execute(self, context):
        global _server_process

        value = api.session()
        settings = context.scene.geno_wb
        try:
            if owned_server_running():
                raise client.WbError(STRINGS["server_already_running"])
            if value.connected:
                raise client.WbError(STRINGS["disconnect_first"])
            if not settings.project.strip():
                raise client.WbError(STRINGS["project_required"])

            project = Path(
                bpy.path.abspath(settings.project)
            ).expanduser().resolve()
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

            process, port = launch.start_serve(
                launch.serve_argv(exe, str(project)),
                timeout=30,
            )
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
        value = api.session()
        try:
            _configure_client(context.scene.geno_wb)
            success = value.connect()
        except (client.WbError, OSError, ValueError, TypeError) as exc:
            success = value.report_error(exc)
        return _finish(self, context, success)


class GENO_WB_OT_disconnect(bpy.types.Operator):
    bl_idname = "geno_wb.disconnect"
    bl_label = STRINGS["disconnect"]
    bl_description = STRINGS["disconnect_help"]

    def execute(self, context):
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
        return api.session().connected

    def execute(self, context):
        context.scene.geno_wb.playing = False
        return _finish(self, context, api.session().engine_restart())


CLASSES = (
    GENO_WB_OT_start_server,
    GENO_WB_OT_connect,
    GENO_WB_OT_disconnect,
    GENO_WB_OT_engine_restart,
)
