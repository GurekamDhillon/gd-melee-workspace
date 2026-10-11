"""Central UI strings and lazily constructed Blender RNA properties.

Importing STRINGS does not import bpy. Property annotations must be evaluated
normally: do not enable postponed annotation evaluation in this module.
"""

from contextlib import contextmanager
import json
import math


STRINGS: dict[str, str] = {
    "nla_panel": "Splice",
    "nla_helper_edit": "A hold or blend strip was moved, trimmed or removed independently. Restore the helper or lay out the recipe again; edit source strips to change segment timing.",
    "nla_clip": "Source clip",
    "nla_clip_help": "XV2 clip name or melee:<fighter>/<action>",
    "nla_clip_required": "Enter a source clip name.",
    "nla_import": "Import clip",
    "nla_import_help": "Import a local source clip onto the active, matching export armature",
    "nla_imported": "Imported clip: {name}",
    "nla_recipe_file": "Recipe file",
    "nla_recipe_file_help": "Optional override; defaults to splices.json in Project",
    "nla_recipe": "Recipe",
    "nla_recipe_help": "Choose a recipe from the selected file",
    "nla_choose_recipe": "Choose a recipe",
    "nla_example_suffix": " (EXAMPLE)",
    "nla_layout": "Lay out recipe",
    "nla_layout_help": "Create one editable NLA track with inserted blend frames",
    "nla_laid_out": "NLA recipe ready: {name}",
    "nla_save": "Save strips as recipe",
    "nla_save_help": "Append an AUTHORED, unwired recipe to splices.authored.json; retain previous entries",
    "nla_saved": "Saved {name} to {path}",
    "nla_bake_export": "Bake & export",
    "nla_bake_export_help": "Bake the current strips and export an AUTHORED clip through the Geno artist exporter",
    "nla_exported": "Exported AUTHORED clip {name}: {path}",
    "nla_export_path": "Export GLB",
    "nla_export_required": "Choose an output GLB path.",
    "nla_action_name": "Clip name",
    "nla_action_help": "Exported action name, at most 31 characters",
    "nla_height": "Source height",
    "nla_height_help": "Same height used to build this armature from the XV2 kit",
    "nla_object_mode": "Switch to Object Mode before editing splice strips.",
    "nla_tool_missing": "Source tool not found: {path}",
    "nla_tool_conflict": "A different source-tool checkout is already loaded; restart Blender before using {path}",
    "nla_context_missing": "The local xv2_to_artist.py needs the splice_context API from the splice lane. Update those source tools, then restart Blender.",
    "nla_import_failed": "Source GLB did not import exactly one animated armature.",
    "nla_rig_mismatch": "The active armature does not match the source export skeleton at bone {bone}. Load art built with the same height.",
    "nla_source_flags": "Mirror, yaw and loop need project source tools; compatible Blender action input only supports crop, speed, hold and blend.",
    "nla_sources_required": "Choose a recipe name and exactly one source: project or actions.",
    "nla_track_required": "Select exactly one Splice NLA track on the active armature.",
    "nla_unsupported_strip": "This strip cannot round-trip: use unmuted clip/hold strips, one repeat, full influence, no modifiers, animated time or overlap blending.",
    "nla_off_grid": "Strip duration does not match whole logic frames. Snap crops and speed to the recipe sample grid.",
    "nla_overlap": "Strips overlap; splice recipes insert blend frames between complete segments.",
    "nla_authored_path": "splices.authored.json must be a separate, regular file beside the project.",
    "nla_recipe_file_error": "Expected a goku-splices/1 recipe file.",
    "nla_source_action_missing": "A source action used by this track is missing.",
    "nla_clip_name": "Use a nonempty export clip name of at most 31 characters.",
    "nla_glb_required": "The export path must end in .glb.",
    "nla_edit_hint": "Edit crops, strip scale and spacing in the NLA Editor.",
    "nla_save_hint": "Saves new entries to splices.authored.json.",
    "nla_preview_hint": "After structural edits, Bake rebuilds transition poses.",
    "attributes_panel": "Attributes",
    "attributes_refresh": "Refresh attributes",
    "attributes_filter": "Filter",
    "attributes_apply": "Apply changed attributes",
    "attributes_changed": "Changed: {count}",
    "attributes_loaded": "fighter attributes loaded: {count}",
    "attribute_name_required": "Choose a fighter attribute.",
    "attribute_unknown": "Unknown fighter attribute: {name}",
    "attribute_edit_reply_invalid": "Invalid attribute edit reply: expected applied or proposed.",
    "attribute_source_edited": "attribute source updated; rebuild and reload to use these values",
    "attribute_override": "Override",
    "attribute_value": "Value",
    "attribute_value_help": "Stage a numeric value; the server's Geno schema determines its range",
    "attribute_missing": "No source value; set an explicit override.",
    "attribute_unbounded": "Unbounded by schema",
    "attribute_minimum": "Minimum {value}",
    "attribute_maximum": "Maximum {value}",
    "attribute_range": "{minimum} to {maximum}",
    "attributes_cache_old": "Source list may be stale; refresh attributes.",
    "attributes_connect": "Connect, then refresh attributes.",
    "attributes_ecb": "ECB shape comes from the fighter plan's joints.",
    "attributes_ecb_schema": "The Geno attribute schema has no numeric ECB fields.",
    "attributes_group_ground": "Ground",
    "attributes_group_air": "Air",
    "attributes_group_jump": "Jump",
    "attributes_group_landing": "Landing",
    "attributes_group_shield_ecb": "Shield / ECB",
    "attributes_group_misc": "Misc",
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
    "engine_exe": "Engine exe",
    "engine_exe_help": "melee-pc.exe for the server to start (default: GW_ENGINE_EXE)",
    "mods_dir": "Mods dir",
    "mods_dir_help": "Directory holding the fighter mod (default: GW_MODS_DIR)",
    "iso": "Disc image",
    "iso_help": "Disc image for the engine (default: GW_ISO_VANILLA); never stored in the project",
    "art": "Art override",
    "art_help": "Optional .blend or .glb path for the fighter loader",
    "row": "Move",
    "row_help": "Selected workbench row",
    "frame": "Frame",
    "frame_help": "Move frame: 1 is the first frame of the move (0 is the entry pose); independent of Blender's scene timeline",
    "playing": "Playing",
    "show_hit": "Hitboxes",
    "show_hurt": "Hurtboxes",
    "show_ecb": "ECB",
    "show_floor": "Floor",
    "hv_arrows": "Launch arrows",
    "hv_arrows_help": "Launch arrow per hitbox (Sakurai angle as a fan, meteors in blue)",
    "hv_labels": "Labels",
    "hv_labels_help": "slot and damage beside each hitbox",
    "hv_badges": "Badges",
    "hv_badges_help": "Element, set knockback, windbox, ground/air only, shield damage",
    "hv_sweep": "Swept capsule",
    "hv_sweep_help": "Sweep from last frame's position to this frame's",
    "hv_percent": "Target %",
    "hv_percent_help": "Victim percent the arrow length is computed at",
    "hv_weight": "Target weight",
    "hv_weight_help": "Victim weight for the knockback shown (Melee weight units)",
    "hitviz_panel": "Hitbox view",
    "hv_slot_legend": "Slot colours (slot 0 strongest)",
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
    "cache_loading": "caching frames {done}/{total}",
    "cache_ready": "{total} frames cached",
    "source_edited": "hitbox source updated; overlays still show the engine's previous build",
    "proposal_created": "proposal created: accept it in the Creator hub",
    "reloaded": "rebuilt and reloaded",
    "reloaded_mode": "rebuilt and reloaded ({mode} build {build:.1f} s, total {total:.1f} s)",
    "suggested": "suggested bone: {bone}",
    "no_suggestion": "no bone suggestion available",
    "restarted": "engine restarted: {engine}",
    "server_reused": "Reused existing server on 127.0.0.1:{port}; connect to continue",
    "server_started": "server ready on 127.0.0.1:{port}; connect to continue",
    "not_connected": "not connected: connect to a workbench server first",
    "invalid_reply": "invalid reply from {tool}: expected an object",
    "invalid_list": "invalid reply: {field} must be a list of objects",
    "invalid_integer": "{field} must be an integer greater than or equal to {minimum}",
    "invalid_number": "{field} must be a finite number",
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
    "timeline_panel": "Timeline",
    "problems_panel": "Problems",
    "hitbox_panel": "Hitbox",
    "select_move": "Choose move",
    "refresh_rows": "Refresh moves",
    "refresh_rows_help": "Refresh the move list from the workbench",
    "load_row": "Load move",
    "load_row_help": "Load the selected move and its source hitboxes",
    "step": "Step",
    "step_help": "Seek relative to the workbench frame",
    "step_count": "Frames",
    "first_frame": "|<",
    "previous_frame": "-1",
    "next_frame": "+1",
    "last_frame": ">|",
    "play": "Play",
    "pause": "Pause",
    "play_help": "Toggle playback at the Speed setting (default: real game speed, 60 logic frames per second), skipping frames if posing is slow; stops at frame 600",
    "play_started": "playing",
    "play_paused": "playback stopped",
    "play_limit": "playback stopped at frame 600",
    "play_end": "playback stopped at the end of the move (frame {frame})",
    "show_travel": "Show travel",
    "show_travel_help": "Show the real world motion (falling, sliding). Off: the fighter stays where the move started and only the body animates",
    "play_speed": "Speed",
    "play_speed_help": "Playback speed: real game speed is 60 logic frames per second; Scene fps follows the Blender scene's frame rate",
    "speed_1": "1x (60 fps)",
    "speed_05": "0.5x",
    "speed_025": "0.25x",
    "speed_scene": "Scene fps",
    "loop": "Loop",
    "loop_help": "Play again from frame 1 when the move ends",
    "move_length": "{frames} frames",
    "play_window_required": "Playback requires a Blender window.",
    "engine_frame": "Move frame: {frame}",
    "run_checks": "Run checks",
    "run_checks_help": "Check source hitboxes for problems",
    "goto_problem": "Go to problem",
    "goto_problem_help": "Load the problem's move at the hitbox's first active frame",
    "problem_index": "Problem",
    "problem_missing": "Select an existing problem.",
    "problem_item": "{kind}  {row} #{ordinal}  {message}",
    "no_problems": "No problems listed. Run checks to refresh.",
    "hitbox_index": "Hitbox",
    "hitbox_item": "#{ordinal}  joint {joint}  size {size}  {start}..{end}",
    "no_hitboxes": "No source hitboxes for this move.",
    "bone": "Bone",
    "damage": "Damage",
    "size": "Size",
    "x": "X",
    "y": "Y",
    "z": "Z",
    "angle": "Angle",
    "kbg": "Knockback growth",
    "fkb": "Fixed knockback",
    "bkb": "Base knockback",
    "start_frame": "Start frame",
    "end_frame": "End frame",
    "element": "Element",
    "element_help": "The hit's element (retail HitElement ids 0-16; the script accepts 0-31)",
    "shield": "Shield damage",
    "shield_help": "Extra damage to a shield; negative values are allowed (Metal Sonic uses -3)",
    "slot": "Slot",
    "slot_help": "Hitbox slot 0-3: the lowest slot wins when hitboxes overlap, and live hitboxes need different slots",
    "slot_readonly": "Slot {slot} (read-only: the Workbench writes slots 0-3)",
    "ground": "Hits grounded targets",
    "ground_help": "Off = air-only hitbox (hit_ground=0)",
    "air": "Hits airborne targets",
    "air_help": "Off = ground-only hitbox (hit_air=0)",
    "invalid_range": "{field} must be between {minimum} and {maximum}",
    "invalid_flag": "{field} must be true or false",
    "ordinal": "Ordinal",
    "suggest_bone": "Suggest limb",
    "add_hitbox": "Add hitbox",
    "add_hitbox_help": "Add a hitbox to this move's source at the shown frame (on the suggested limb if you asked, else the floor anchor); Rebuild + reload applies it",
    "delete_hitbox": "Delete hitbox",
    "delete_hitbox_help": "Remove the selected hitbox from the move's source; Rebuild + reload applies it",
    "hitbox_added": "hitbox #{ordinal} added on {bone} at frame {frame}; rebuild + reload to see it in the engine",
    "hitbox_deleted": "hitbox #{ordinal} deleted; rebuild + reload to apply",
    "bone_help": "The bone role this hitbox follows (joint=@ROLE@ in the move's source)",
    "bone_none": "(no bones listed)",
    "bone_raw": "{bone} (not a role)",
    "bone_group_body": "Body",
    "bone_group_arms": "Arms",
    "bone_group_legs": "Legs",
    "bone_group_anchors": "Anchors",
    "bone_group_other": "Other",
    "suggest_bone_help": "Put the suggested limb in the editor; Apply saves the change",
    "edit_hitbox": "Apply",
    "edit_hitbox_help": "Send only changed fields to the workbench source editor",
    "rebuild_reload": "Rebuild + reload",
    "rebuild_reload_help": "Rebuild source, reload the engine and restore this move and frame",
    "rebuild_cancel": "Cancel",
    "rebuild_cancel_help": "Stop the running build. The engine keeps its current build; rebuild again before relying on the package",
    "rebuild_cancelled": "rebuild cancelled: the package may be partly built, so rebuild again",
    "rebuild_running": "A rebuild or engine restart is running: wait for it to finish",
    "rebuild_cancel_idle": "No rebuild is running",
    "rebuild_why_full": "full build because: {reason}",
    "rebuild_progress": "{phase}: {percent:.0f}% ({elapsed:.0f} s)",
    "rebuild_progress_step": "{phase}: {step} {percent:.0f}% ({elapsed:.0f} s)",
    "rebuild_phase_build": "Building",
    "rebuild_phase_restart": "Restarting engine",
    "rebuild_phase_rows": "Reloading rows",
    "rebuild_phase_restore": "Restoring row and frame",
    "rebuild_phase_engine": "Restarting engine",
    "rebuild_started": "rebuild started",
    "rebuild_unavailable": "This project has no build configured (workbench.json rebuild): Rebuild + reload is unavailable",
    "no_roles": "This project has no role map (plan has no roles): checks and bone suggestions are unavailable",
    "stale_banner": "Source edited: rebuild + reload needed",
    "stale_overlays": "Overlays show the engine's previous build.",
    "no_changes": "no hitbox fields changed",
    "editor_missing": "Select a source hitbox before editing.",
    "bone_required": "Bone must be a nonempty name.",
    "unsupported_fields": "Unsupported hitbox fields: {fields}",
    "editor_baseline": "Editor baseline",
    "editor_source": "Editor source",
    "project_object_required": "workbench.json: expected an object",
    "project_invalid_path": "workbench.json: invalid path",
    "project_art_required": "workbench.json: art must be an object",
    "fighter_not_armature": "Select an armature before using the fighter workbench",
    "fighter_no_art": "Choose a .blend or .glb fighter art file",
    "fighter_verify_calibration": "Calibrate and apply a frame before verifying the pose",
    "project_aliases_required": "workbench.json: art.bone_aliases must be an object",
}

def busy_reason() -> str:
    """Why Workbench actions are disabled right now (a background rebuild/restart), else ''."""
    try:
        return STRINGS["rebuild_running"] if _session().busy else ""
    except Exception:
        return ""


def rebuild_progress_text(job) -> str:
    """One line for the sidebar and the status bar: phase, step, percent, seconds."""
    phase = STRINGS["rebuild_phase_" + job.phase]
    if job.detail:
        return STRINGS["rebuild_progress_step"].format(phase=phase, step=job.detail, percent=job.percent, elapsed=job.elapsed)
    return STRINGS["rebuild_progress"].format(phase=phase, percent=job.percent, elapsed=job.elapsed)


def _busy_poll(inner):
    # Blender requires poll(cls, context) with exactly two arguments, so the wrapped function is closed over.
    def poll(c, context):
        reason = busy_reason()
        if reason:
            c.poll_message_set(reason)
            return False
        return inner(c, context)
    return poll


def guard_busy(classes, allow=()):
    """Disable operators while a background rebuild runs, with the reason in the tooltip."""
    for cls in classes:
        if getattr(cls, "bl_idname", "") in allow or getattr(cls, "_busy_guarded", False):
            continue
        found = getattr(cls, "poll", None)   # own or inherited; a classmethod arrives bound
        inner = getattr(found, "__func__", None) or (lambda c, context: True)

        cls.poll = classmethod(_busy_poll(inner))
        cls._busy_guarded = True


def poll_ready(operator, *requirements):
    """Attach the first failed precondition to Blender's disabled-button tooltip."""
    for ready, reason in requirements:
        if not ready:
            operator.poll_message_set(reason)
            return False
    return True


NO_ROW = "__GENO_WB_NO_ROW__"
NO_BONE = "__GENO_WB_NO_BONE__"
_frame_handler = None
_row_handler = None
_problem_handler = None
_frame_sync_depth = 0
_row_signature = None
_row_items_cache = []
_row_strings = {}


def _session():
    try:
        from . import api
    except ImportError:
        import api
    return api.session()


def set_frame_handler(callback):
    """Install the coalescing frame handler, or None to disable it."""
    global _frame_handler
    _frame_handler = callback


def set_row_handler(callback):
    global _row_handler
    _row_handler = callback


def set_problem_handler(callback):
    global _problem_handler
    _problem_handler = callback


@contextmanager
def suspend_frame_updates():
    """Prevent synchronization from triggering frame or selection requests."""
    global _frame_sync_depth
    _frame_sync_depth += 1
    try:
        yield
    finally:
        _frame_sync_depth -= 1


def on_frame_changed(self, context):
    """Queue a workbench frame; never drive Blender's scene timeline."""
    if _frame_sync_depth == 0 and _frame_handler is not None:
        _frame_handler(self, context)


def on_row_changed(self, context):
    if _frame_sync_depth == 0 and _row_handler is not None:
        _row_handler(self, context)


def _redraw_pose(settings):
    """Show travel changed: pose and overlays again from the frame already held (no engine call)."""
    try:
        try:
            from . import api
        except ImportError:
            import api
        session = api.session()
        if session.info is not None:
            session._fire_frame()
    except Exception:
        pass


def on_problem_changed(self, context):
    if (
        _frame_sync_depth == 0
        and self.problem_index >= 0
        and _problem_handler is not None
    ):
        _problem_handler(self, context)


def on_hitbox_changed(self, context):
    if _frame_sync_depth == 0:
        sync_editor(_session(), self)


def _keep_string(text):
    # Blender dynamic enums retain C pointers to callback-provided strings.
    return _row_strings.setdefault(text, text)


_GROUP_ORDER = ("body", "arms", "legs", "anchors")
_role_signature = None
_role_items_cache = []


def role_choices(roles, current=""):
    """[(heading, [names])] for the bone dropdown: the project's roles by group, then a stray current value.

    Pure data so it is testable without bpy. A current value that is not a role (a raw joint in an old
    script) is kept, in its own group, so it still displays and round-trips.
    """
    groups = {}
    for role in roles:
        name = role.get("name")
        if isinstance(name, str) and name:
            group = role.get("group") if role.get("group") in _GROUP_ORDER else "other"
            if name not in groups.setdefault(group, []):
                groups[group].append(name)
    known = {name for names in groups.values() for name in names}
    out = [(group, groups[group]) for group in (*_GROUP_ORDER, "other") if group in groups]
    if current and current not in known:
        out.append(("raw", [current]))
    return out


def role_items(self=None, context=None):
    """Dynamic enum items for the bone dropdown (body, arms, legs, anchors), current value included."""
    global _role_signature, _role_items_cache
    session = _session()
    current = ""
    try:
        index = self.hitbox_index if self is not None else -1
        if 0 <= index < len(session.hitboxes):
            box = session.hitboxes[index]
            current = str(box.get("bone", box.get("joint", "")) or "")
    except Exception:
        current = ""
    choices = role_choices(session.roles, current)
    signature = tuple((g, tuple(n)) for g, n in choices)
    if signature != _role_signature:
        _role_signature = signature
        items = []
        for group, names in choices:
            label = STRINGS.get("bone_group_" + group, group)
            items.append(("", _keep_string(label), ""))  # a heading inside the dropdown
            for name in names:
                shown = STRINGS["bone_raw"].format(bone=name) if group == "raw" else name
                items.append((_keep_string(name), _keep_string(shown), _keep_string(label)))
        if not items:   # an enum with no items at all makes Blender warn on every read
            items = [(NO_BONE, _keep_string(STRINGS["bone_none"]), "")]
        _role_items_cache = items
    return _role_items_cache


def set_edit_bone(settings, joint):
    """Select `joint` in the dropdown; a value it cannot show is left as is rather than raising."""
    try:
        settings.edit_bone = joint
        return True
    except (TypeError, ValueError):
        return False


def row_items(self=None, context=None):
    """Dynamic enum items, with retained strings and a stable empty choice."""
    global _row_signature, _row_items_cache
    names = []
    seen = {NO_ROW}
    for row in _session().rows:
        name = row.get("name")
        if isinstance(name, str) and name and name not in seen:
            seen.add(name)
            names.append(name)
    signature = tuple(names)
    if signature != _row_signature:
        _row_signature = signature
        _row_items_cache = [
            (NO_ROW, STRINGS["select_move"], STRINGS["row_help"], 0)
        ]
        for index, name in enumerate(names, 1):
            name = _keep_string(name)
            _row_items_cache.append((name, name, STRINGS["row_help"], index))
    return _row_items_cache


def _sync_labels(collection, labels):
    current = [item.get("label", "") for item in collection]
    if current == labels:
        return False
    collection.clear()
    for label in labels:
        item = collection.add()
        item["label"] = label
    return True


# HitElement (melee/lb/forward.h) 0..16, then the unused codes the assembler still accepts (17..31).
HIT_ELEMENTS = (
    "Normal", "Fire", "Electric", "Slash", "Coin", "Ice", "Nap (sleep 103 frames)", "Sleep (412 frames)",
    "Grab (catch)", "Ground", "Cape", "Inert", "Disable", "Darkness", "Screw Attack", "Lipstick", "ReDead grab",
)
ELEMENT_ITEMS = [
    (str(i), "%d  %s" % (i, HIT_ELEMENTS[i]) if i < len(HIT_ELEMENTS) else "%d  unused code" % i, "")
    for i in range(32)
]
EDIT_FLAGS = {"ground": "hit_ground", "air": "hit_air"}


def _display(value):
    return format(value, "g") if isinstance(value, (int, float)) else str(value)


def _source_editor_values(box):
    values = {}
    for field in _session().edit_fields:
        if field == "bone":
            values[field] = str(box.get("bone", box.get("joint", "")))
            continue
        if field in EDIT_FLAGS:   # absent = true: an old launcher that lists neither flag changes nothing
            flag = box.get(EDIT_FLAGS[field], box.get(field, True))
            values[field] = flag if isinstance(flag, bool) else bool(flag)
            continue
        if field == "shield":
            box = dict(box, shield=box.get("shield_damage", box.get("shield", 0)))
        default = 1 if field in ("start_frame", "end_frame") else 0
        try:
            number = float(box.get(field, default))
            if not math.isfinite(number):
                number = default
        except (TypeError, ValueError, OverflowError):
            number = default
        if field in ("angle", "kbg", "fkb", "bkb", "start_frame", "end_frame", "element", "shield", "slot"):
            number = int(number)
        if field == "slot":
            number = max(0, min(3, number))   # a slot 4+ script shows read-only in the panel; the editor holds 3
        values[field] = number
        if field == "element":
            values[field] = str(max(0, min(31, number)))   # the enum's identifier
    return values


def sync_editor(value, settings):
    """Reload the editor only when selection or source changes.

    Baselines use values read back from RNA so float storage precision does not
    turn an untouched field into an edit during playback.
    """
    index = settings.hitbox_index
    if not value.source_row or not 0 <= index < len(value.hitboxes):
        settings.edit_row = ""
        settings.edit_ordinal = -1
        settings.edit_source_key = ""
        settings.edit_baseline = ""
        return
    box = value.hitboxes[index]
    key = json.dumps([value.source_row, index, box], sort_keys=True)
    if settings.edit_source_key == key:
        return
    with suspend_frame_updates():
        settings.edit_row = value.source_row
        settings.edit_ordinal = index
        for field, item in _source_editor_values(box).items():
            if field == "bone":
                set_edit_bone(settings, item)
            else:
                setattr(settings, "edit_" + field, item)
        baseline = {
            field: getattr(settings, "edit_" + field)
            for field in value.edit_fields
        }
        settings.edit_baseline = json.dumps(baseline, sort_keys=True)
        settings.edit_source_key = key


def changed_hitbox_fields(settings):
    """Return exactly the editor fields changed since its source refresh."""
    if not settings.edit_baseline:
        raise ValueError(STRINGS["editor_missing"])
    baseline = json.loads(settings.edit_baseline)
    changed = {
        field: getattr(settings, "edit_" + field)
        for field in _session().edit_fields
        if getattr(settings, "edit_" + field) != baseline.get(field)
    }
    if "element" in changed:
        changed["element"] = int(changed["element"])   # the enum holds its id as text
    return changed


def sync_from_session(value, settings=None):
    """Copy session state without triggering callbacks or overwriting drafts."""
    if settings is None:
        import bpy
        scene = getattr(bpy.context, "scene", None)
        settings = getattr(scene, "geno_wb", None)
        if settings is None:
            return

    with suspend_frame_updates():
        settings.row = value.row
        pending = getattr(value, "pending_frame", None)
        settings.frame = value.frame if pending is None else pending
        settings.status = value.status
        settings.stale = value.stale
        if not value.connected:
            settings.playing = False
        # Preserve compatibility with small callback test doubles.
        if not hasattr(settings, "move"):
            return
        choices = {item[0] for item in row_items()}
        settings.move = value.source_row if value.row in choices else NO_ROW
        problems = [
            STRINGS["problem_item"].format(
                kind=item.get("kind", ""),
                row=item.get("row", ""),
                ordinal=item.get("ordinal", 0),
                message=item.get("message", ""),
            )
            for item in value.problems
        ]
        if _sync_labels(settings.problem_items, problems):
            settings.problem_index = -1
        boxes = [
            STRINGS["hitbox_item"].format(
                ordinal=index,
                joint=item.get("joint", item.get("bone", "")),
                size=_display(item.get("size", 0)),
                start=item.get("start_frame", 1),
                end=item.get("end_frame", 1),
            )
            for index, item in enumerate(value.hitboxes)
        ]
        _sync_labels(settings.hitbox_items, boxes)
        if not boxes:
            settings.hitbox_index = -1
        elif not 0 <= settings.hitbox_index < len(boxes):
            settings.hitbox_index = 0
        sync_editor(value, settings)


def nla_recipe_items(self, context=None):
    # Lazy import: the string table and existing pure props tests need no bpy.
    try:
        from .operators_nla import recipe_items
    except ImportError:
        from operators_nla import recipe_items
    return recipe_items(self, context)


def _make_property_group():
    import bpy
    from bpy.props import (
        BoolProperty, CollectionProperty, EnumProperty, FloatProperty,
        IntProperty, StringProperty,
    )

    class GenoWBProps(bpy.types.PropertyGroup):
        """Scene settings; engine frames are independent of scene frames."""

        host: StringProperty(name=STRINGS["host"], description=STRINGS["host_help"], default="127.0.0.1")
        port: IntProperty(name=STRINGS["port"], description=STRINGS["port_help"], default=0, min=0, max=65535)
        project: StringProperty(name=STRINGS["project"], description=STRINGS["project_help"], subtype="DIR_PATH")
        launcher_exe: StringProperty(name=STRINGS["launcher"], description=STRINGS["launcher_help"], subtype="FILE_PATH")
        engine_exe: StringProperty(name=STRINGS["engine_exe"], description=STRINGS["engine_exe_help"], subtype="FILE_PATH")
        mods_dir: StringProperty(name=STRINGS["mods_dir"], description=STRINGS["mods_dir_help"], subtype="DIR_PATH")
        iso_path: StringProperty(name=STRINGS["iso"], description=STRINGS["iso_help"], subtype="FILE_PATH")
        blender_art: StringProperty(name=STRINGS["art"], description=STRINGS["art_help"], subtype="FILE_PATH")
        row: StringProperty(name=STRINGS["row"], description=STRINGS["row_help"])
        move: EnumProperty(name=STRINGS["row"], description=STRINGS["row_help"], items=row_items, update=on_row_changed, options={"SKIP_SAVE"})
        frame: IntProperty(name=STRINGS["frame"], description=STRINGS["frame_help"], default=0, min=0, max=600, update=on_frame_changed)
        playing: BoolProperty(name=STRINGS["playing"], default=False, options={"SKIP_SAVE"})
        show_travel: BoolProperty(name=STRINGS["show_travel"], description=STRINGS["show_travel_help"], default=False, update=lambda self, context: _redraw_pose(self))
        play_speed: EnumProperty(
            name=STRINGS["play_speed"], description=STRINGS["play_speed_help"],
            items=[
                ("1", STRINGS["speed_1"], ""),
                ("0.5", STRINGS["speed_05"], ""),
                ("0.25", STRINGS["speed_025"], ""),
                ("scene", STRINGS["speed_scene"], ""),
            ],
            default="1",
        )
        loop: BoolProperty(name=STRINGS["loop"], description=STRINGS["loop_help"], default=True)
        show_hurt: BoolProperty(name=STRINGS["show_hurt"], default=True)
        show_ecb: BoolProperty(name=STRINGS["show_ecb"], default=True)
        show_floor: BoolProperty(name=STRINGS["show_floor"], default=True)
        show_hit: BoolProperty(name=STRINGS["show_hit"], default=True)
        hv_arrows: BoolProperty(name=STRINGS["hv_arrows"], description=STRINGS["hv_arrows_help"], default=True, update=lambda self, context: _redraw_pose(self))
        hv_labels: BoolProperty(name=STRINGS["hv_labels"], description=STRINGS["hv_labels_help"], default=True, update=lambda self, context: _redraw_pose(self))
        hv_badges: BoolProperty(name=STRINGS["hv_badges"], description=STRINGS["hv_badges_help"], default=True, update=lambda self, context: _redraw_pose(self))
        hv_sweep: BoolProperty(name=STRINGS["hv_sweep"], description=STRINGS["hv_sweep_help"], default=True, update=lambda self, context: _redraw_pose(self))
        hv_percent: EnumProperty(
            name=STRINGS["hv_percent"], description=STRINGS["hv_percent_help"],
            items=[("0", "0%", ""), ("50", "50%", ""), ("100", "100%", "")], default="50",
            update=lambda self, context: _redraw_pose(self),
        )
        hv_weight: FloatProperty(name=STRINGS["hv_weight"], description=STRINGS["hv_weight_help"], default=100.0, min=1.0, max=400.0, update=lambda self, context: _redraw_pose(self))
        status: StringProperty(name=STRINGS["status_label"], default=STRINGS["disconnected"], options={"SKIP_SAVE"})
        pose_error: FloatProperty(name=STRINGS["pose_error"], description=STRINGS["pose_error_help"], default=0.0, min=0.0, options={"SKIP_SAVE"})
        stale: BoolProperty(name=STRINGS["stale_label"], default=False, options={"SKIP_SAVE"})

        nla_clip: StringProperty(name=STRINGS["nla_clip"], description=STRINGS["nla_clip_help"])
        nla_recipe_file: StringProperty(name=STRINGS["nla_recipe_file"], description=STRINGS["nla_recipe_file_help"], subtype="FILE_PATH")
        nla_recipe: EnumProperty(name=STRINGS["nla_recipe"], description=STRINGS["nla_recipe_help"], items=nla_recipe_items, options={"SKIP_SAVE"})
        nla_height: FloatProperty(name=STRINGS["nla_height"], description=STRINGS["nla_height_help"], default=20.0, min=8.0, max=20.0)
        nla_export_path: StringProperty(name=STRINGS["nla_export_path"], subtype="FILE_PATH")
        nla_action_name: StringProperty(name=STRINGS["nla_action_name"], description=STRINGS["nla_action_help"], maxlen=31)

        # Base PropertyGroup entries hold display-only ID properties. This
        # requires no additional PropertyGroup registration in __init__.py.
        problem_items: CollectionProperty(name=STRINGS["problems_panel"], type=bpy.types.PropertyGroup, options={"SKIP_SAVE"})
        problem_index: IntProperty(name=STRINGS["problem_index"], default=-1, min=-1, update=on_problem_changed, options={"SKIP_SAVE"})
        hitbox_items: CollectionProperty(name=STRINGS["show_hit"], type=bpy.types.PropertyGroup, options={"SKIP_SAVE"})
        hitbox_index: IntProperty(name=STRINGS["hitbox_index"], default=-1, min=-1, update=on_hitbox_changed, options={"SKIP_SAVE"})
        edit_row: StringProperty(name=STRINGS["row"], options={"SKIP_SAVE"})
        edit_ordinal: IntProperty(name=STRINGS["ordinal"], default=-1, min=-1, options={"SKIP_SAVE"})
        edit_baseline: StringProperty(name=STRINGS["editor_baseline"], options={"HIDDEN", "SKIP_SAVE"})
        edit_source_key: StringProperty(name=STRINGS["editor_source"], options={"HIDDEN", "SKIP_SAVE"})
        edit_bone: EnumProperty(name=STRINGS["bone"], description=STRINGS["bone_help"], items=role_items, options={"SKIP_SAVE"})
        edit_damage: FloatProperty(name=STRINGS["damage"], min=0.0, options={"SKIP_SAVE"})
        edit_size: FloatProperty(name=STRINGS["size"], min=0.0, options={"SKIP_SAVE"})
        edit_x: FloatProperty(name=STRINGS["x"], options={"SKIP_SAVE"})
        edit_y: FloatProperty(name=STRINGS["y"], options={"SKIP_SAVE"})
        edit_z: FloatProperty(name=STRINGS["z"], options={"SKIP_SAVE"})
        edit_angle: IntProperty(name=STRINGS["angle"], min=0, options={"SKIP_SAVE"})
        edit_kbg: IntProperty(name=STRINGS["kbg"], min=0, options={"SKIP_SAVE"})
        edit_fkb: IntProperty(name=STRINGS["fkb"], min=0, options={"SKIP_SAVE"})
        edit_bkb: IntProperty(name=STRINGS["bkb"], min=0, options={"SKIP_SAVE"})
        edit_start_frame: IntProperty(name=STRINGS["start_frame"], default=1, min=0, options={"SKIP_SAVE"})
        edit_end_frame: IntProperty(name=STRINGS["end_frame"], default=1, min=0, options={"SKIP_SAVE"})
        edit_element: EnumProperty(name=STRINGS["element"], description=STRINGS["element_help"], items=ELEMENT_ITEMS, options={"SKIP_SAVE"})
        edit_shield: IntProperty(name=STRINGS["shield"], description=STRINGS["shield_help"], min=-128, max=127, options={"SKIP_SAVE"})
        edit_slot: IntProperty(name=STRINGS["slot"], description=STRINGS["slot_help"], min=0, max=3, options={"SKIP_SAVE"})
        edit_ground: BoolProperty(name=STRINGS["ground"], description=STRINGS["ground_help"], default=True, options={"SKIP_SAVE"})
        edit_air: BoolProperty(name=STRINGS["air"], description=STRINGS["air_help"], default=True, options={"SKIP_SAVE"})

    return GenoWBProps


def __getattr__(name):
    if name == "GenoWBProps":
        value = _make_property_group()
        globals()[name] = value
        return value
    raise AttributeError(name)
