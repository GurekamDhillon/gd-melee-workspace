"""Central UI strings and lazily constructed Blender RNA properties.

Importing STRINGS does not import bpy. This lets api.py share the same
messages while remaining usable with the standard library outside Blender.

Do not enable postponed annotation evaluation in this module: Blender needs
the evaluated property declarations in GenoWBProps.__annotations__.
"""

from contextlib import contextmanager


STRINGS: dict[str, str] = {
    "addon_name": "Geno Workbench",
    "tab": "Geno",
    "connect_panel": "Connect",
    "host": "Host",
    "host_help": "Loopback only; connections use 127.0.0.1",
    "port": "Port",
    "port_help": "Port printed by the workbench server; start a server to fill this",
    "project": "Project",
    "project_help": "Directory containing workbench.json",
    "launcher": "Launcher",
    "launcher_help": "Optional gd-melee-launcher executable override",
    "art": "Art override",
    "art_help": "Optional .blend or .glb path for the fighter loader",
    "row": "Move",
    "row_help": "Selected workbench row",
    "frame": "Frame",
    "frame_help": "Engine logic frame",
    "playing": "Playing",
    "show_hit": "Hitboxes",
    "show_hurt": "Hurtboxes",
    "show_ecb": "ECB",
    "show_floor": "Floor",
    "status_label": "Status",
    "pose_error": "Pose error",
    "pose_error_help": "Maximum measured position error in Melee units",
    "stale_label": "Rebuild needed",
    "start_server": "Start server",
    "start_server_help": "Start a local workbench server and fill its port",
    "connect": "Connect",
    "connect_help": "Connect to the local workbench server",
    "disconnect": "Disconnect",
    "disconnect_help": "Disconnect and stop the server started by this add-on",
    "restart_engine": "Restart engine",
    "restart_engine_help": "Ask the connected workbench server to restart the engine",
    "disconnected": "disconnected",
    "connected": "connected: {engine}",
    "unknown": "unknown",
    "error_status": "error: {error}",
    "stale_status": "stale: rebuild needed",
    "rows_loaded": "rows loaded: {count}",
    "frame_loaded": "row {row}, frame {frame}",
    "hitboxes_loaded": "source hitboxes loaded: {count}",
    "checks_loaded": "checks: {count} problem(s)",
    "source_edited": "hitbox source updated",
    "proposal_created": "proposal created: accept it in the Creator hub",
    "reloaded": "rebuilt and reloaded",
    "suggested": "suggested bone: {bone}",
    "no_suggestion": "no bone suggestion available",
    "restarted": "engine restarted: {engine}",
    "server_started": "server ready on 127.0.0.1:{port}; connect to continue",
    "not_connected": "not connected: connect to a workbench server first",
    "invalid_reply": "invalid reply from {tool}: expected an object",
    "invalid_list": "invalid reply: {field} must be a list of objects",
    "invalid_integer": "{field} must be an integer greater than or equal to {minimum}",
    "row_required": "select a row first",
    "invalid_row": "invalid frame reply: row must be a string",
    "no_frame": "no frame loaded",
    "callback_error": "UI update failed: {error}",
    "non_loopback": "Only loopback hosts are allowed; use 127.0.0.1.",
    "invalid_port": "Choose a port from 1 to 65535, or start a server first.",
    "project_required": "Choose a project directory before starting a server.",
    "invalid_project": "Project directory does not exist: {path}",
    "launcher_missing": "Launcher not found; set Launcher or GW_LAUNCHER.",
    "invalid_launcher": "Launcher executable does not exist: {path}",
    "server_already_running": "This add-on already owns a running server; disconnect first.",
    "disconnect_first": "Disconnect the current session before starting another server.",
    "stop_failed": "Could not stop the server started by this add-on: {error}",
    "already_registered": "Scene.geno_wb already exists; unregister the existing add-on first.",
    "registration_incomplete": "A previous registration needs cleanup; call unregister() first.",
    "cleanup_error": "Geno Workbench cleanup failed: {error}",
    "bootstrap_description": "Register Geno Workbench and connect to a local server.",
    "project_argument": "Project directory containing workbench.json",
    "port_argument": "Existing workbench server port on 127.0.0.1",
    "bootstrap_connect_failed": "Geno Workbench could not connect.",
    "bootstrap_fighter_failed": "Geno Workbench could not load the fighter.",
}

_frame_handler = None
_frame_sync_depth = 0


def set_frame_handler(callback):
    """Install the timeline's frame-change handler, or None to disable it."""
    global _frame_handler
    _frame_handler = callback


@contextmanager
def suspend_frame_updates():
    """Prevent session-to-property synchronization from requesting a frame."""
    global _frame_sync_depth
    _frame_sync_depth += 1
    try:
        yield
    finally:
        _frame_sync_depth -= 1


def on_frame_changed(self, context):
    """Task 9 installs its coalescing scrub handler through set_frame_handler."""
    if _frame_sync_depth == 0 and _frame_handler is not None:
        _frame_handler(self, context)


def sync_from_session(value, settings=None):
    """Copy session state to Blender; injected as WbSession.on_change."""
    if settings is None:
        import bpy

        scene = getattr(bpy.context, "scene", None)
        settings = getattr(scene, "geno_wb", None)
        if settings is None:
            return

    with suspend_frame_updates():
        settings.row = value.row
        settings.frame = value.frame
        settings.status = value.status
        settings.stale = value.stale
        if not value.connected:
            settings.playing = False


def _make_property_group():
    import bpy
    from bpy.props import BoolProperty, FloatProperty, IntProperty, StringProperty

    class GenoWBProps(bpy.types.PropertyGroup):
        """Scene settings for the shared workbench session."""

        host: StringProperty(
            name=STRINGS["host"],
            description=STRINGS["host_help"],
            default="127.0.0.1",
        )
        port: IntProperty(
            name=STRINGS["port"],
            description=STRINGS["port_help"],
            default=0,
            min=0,
            max=65535,
        )
        project: StringProperty(
            name=STRINGS["project"],
            description=STRINGS["project_help"],
            subtype="DIR_PATH",
        )
        launcher_exe: StringProperty(
            name=STRINGS["launcher"],
            description=STRINGS["launcher_help"],
            subtype="FILE_PATH",
        )
        blender_art: StringProperty(
            name=STRINGS["art"],
            description=STRINGS["art_help"],
            subtype="FILE_PATH",
        )
        row: StringProperty(
            name=STRINGS["row"],
            description=STRINGS["row_help"],
        )
        frame: IntProperty(
            name=STRINGS["frame"],
            description=STRINGS["frame_help"],
            default=0,
            min=0,
            update=on_frame_changed,
        )
        playing: BoolProperty(
            name=STRINGS["playing"],
            default=False,
            options={"SKIP_SAVE"},
        )
        show_hurt: BoolProperty(name=STRINGS["show_hurt"], default=True)
        show_ecb: BoolProperty(name=STRINGS["show_ecb"], default=True)
        show_floor: BoolProperty(name=STRINGS["show_floor"], default=True)
        show_hit: BoolProperty(name=STRINGS["show_hit"], default=True)
        status: StringProperty(
            name=STRINGS["status_label"],
            default=STRINGS["disconnected"],
            options={"SKIP_SAVE"},
        )
        pose_error: FloatProperty(
            name=STRINGS["pose_error"],
            description=STRINGS["pose_error_help"],
            default=0.0,
            min=0.0,
            options={"SKIP_SAVE"},
        )
        stale: BoolProperty(
            name=STRINGS["stale_label"],
            default=False,
            options={"SKIP_SAVE"},
        )

    return GenoWBProps


def __getattr__(name):
    if name == "GenoWBProps":
        value = _make_property_group()
        globals()[name] = value
        return value
    raise AttributeError(name)
