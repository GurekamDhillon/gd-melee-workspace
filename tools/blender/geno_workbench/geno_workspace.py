"""The "Geno" workspace: a big 3D viewport, a timeline strip and the Geno sidebar tab.

The Qt Workbench is the main editor; Blender is the 3D viewport with a slim Geno panel. This module only
builds and activates a workspace (new file; no existing panel or operator is touched). It is created from a
duplicate of the user's current workspace the first time and reused afterwards, so registering twice never
makes a second one, and the user's other workspaces are never modified.

Unregister policy: the workspace is LEFT in place. A modified one cannot be told from an untouched one
reliably, and deleting something the user may have arranged is the worse mistake; unregister only stops the
frame-sync timer.
"""

NAME = "Geno"
SIDEBAR_TAB = "Geno"
# Area types the finished workspace must contain.
WANT_AREAS = ("VIEW_3D", "DOPESHEET_EDITOR")
SYNC_INTERVAL = 0.1


def frame_to_sync(scene_frame, wb_frame, connected, owns_pose_animation):
    """Scene frame the timeline should show, or None to leave it alone.

    The Workbench frame drives the pose live; mirroring it to the scene frame only moves the playhead. When
    the rig carries an action or NLA tracks (the baked view) the scene frame already drives the pose, so it
    is not touched.
    """
    if not connected or owns_pose_animation:
        return None
    try:
        wb_frame = int(wb_frame)
    except (TypeError, ValueError):
        return None
    return wb_frame if wb_frame != int(scene_frame) else None


def area_types(screen):
    return [a.type for a in screen.areas]


def _window():
    import bpy
    wm = bpy.context.window_manager
    return wm.windows[0] if wm and wm.windows else None


def find_workspace():
    import bpy
    return bpy.data.workspaces.get(NAME)


def ensure_workspace(window=None):
    """Return the Geno workspace, creating it by duplicating the current one if missing. None when no window."""
    import bpy
    existing = find_workspace()
    if existing is not None:
        return existing
    window = window or _window()
    if window is None:
        return None
    before = set(w.name for w in bpy.data.workspaces)
    with bpy.context.temp_override(window=window):
        bpy.ops.workspace.duplicate()
    made = [w for w in bpy.data.workspaces if w.name not in before]
    if not made:
        return None
    made[0].name = NAME
    _arrange(made[0], window)
    return made[0]


def _arrange(workspace, window):
    """Shape the new workspace's own screen through the data API (never through the window's current screen).

    Layout's arrangement is kept: a wide 3D viewport, the timeline strip along the bottom, and the narrow
    right column (properties over a small outliner). Area join/move operators are not used: they need a live
    UI event loop and left stray zero-size areas when run on a non-active screen.
    """
    screen = workspace.screens[0]
    for area in screen.areas:
        if area.type == "VIEW_3D":
            space = area.spaces.active
            space.show_region_ui = True
            space.overlay.show_overlays = True
            space.shading.type = "SOLID"
            space.clip_end = max(space.clip_end, 100000.0)
            _set_sidebar_tab(area)
    _front_view(window, screen)


def _set_sidebar_tab(area):
    for region in area.regions:
        if region.type == "UI":
            try:
                region.active_panel_category = SIDEBAR_TAB   # read-only in current Blender; the tab is clicked once
            except Exception:
                pass


def _front_view(window, screen):
    import bpy
    area = next((a for a in screen.areas if a.type == "VIEW_3D"), None)
    region = next((r for r in area.regions if r.type == "WINDOW"), None) if area else None
    if region is None:
        return
    try:
        with bpy.context.temp_override(window=window, screen=screen, area=area, region=region):
            bpy.ops.view3d.view_axis(type="FRONT")
            area.spaces.active.region_3d.view_perspective = "ORTHO"
    except Exception:
        pass


def frame_fighter(window=None):
    """Frame the loaded fighter (front, orthographic) in the Geno 3D view. Call once a fighter is loaded."""
    import bpy
    ws = find_workspace()
    window = window or _window()
    if ws is None or window is None:
        return False
    arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
    if arm is None:
        return False
    done = False
    try:
        screen = ws.screens[0]
        area = next((a for a in screen.areas if a.type == "VIEW_3D"), None)
        region = next((r for r in area.regions if r.type == "WINDOW"), None) if area else None
        if region is not None:
            meshes = [o for o in bpy.data.objects if o.type == "MESH" and o.parent == arm]
            with bpy.context.temp_override(window=window, screen=screen, area=area, region=region):
                was = [o for o in bpy.context.view_layer.objects if o.select_get()]
                bpy.ops.object.select_all(action="DESELECT")
                for obj in meshes or [arm]:
                    obj.select_set(True)
                bpy.ops.view3d.view_axis(type="FRONT")
                area.spaces.active.region_3d.view_perspective = "ORTHO"
                bpy.ops.view3d.view_selected()
                bpy.ops.object.select_all(action="DESELECT")
                for obj in was:
                    obj.select_set(True)
            done = True
    except Exception as exc:
        print("GENO_WB_REPORT geno_workspace_warning %s" % exc)
    return done


def activate(window=None):
    ws = ensure_workspace(window)
    window = window or _window()
    if ws is not None and window is not None:
        window.workspace = ws
    return ws


def on_session_ready():
    """Called by the bootstrap once a fighter is loaded: frame him, then make Geno the active workspace."""
    ws = ensure_workspace()
    if ws is not None:
        frame_fighter()
        activate()
    start_sync()
    return ws


def _sync_tick():
    import bpy
    try:
        from . import api
        session = api.session()
        scene = bpy.context.scene
        arm = next((o for o in bpy.data.objects if o.type == "ARMATURE"), None)
        ad = arm.animation_data if arm is not None else None
        owns = bool(ad and (ad.action or len(ad.nla_tracks)))
        target = frame_to_sync(scene.frame_current, session.frame, session.connected, owns)
        if target is not None:
            scene.frame_current = target
    except Exception:
        pass
    return SYNC_INTERVAL


def start_sync():
    import bpy
    if not bpy.app.timers.is_registered(_sync_tick):
        bpy.app.timers.register(_sync_tick, first_interval=SYNC_INTERVAL)


def stop_sync():
    import bpy
    if bpy.app.timers.is_registered(_sync_tick):
        bpy.app.timers.unregister(_sync_tick)


def _deferred_create():
    if _window() is None:
        return 0.5
    ensure_workspace()
    return None


def register():
    import bpy
    if find_workspace() is None:
        if _window() is not None:
            ensure_workspace()
        elif not bpy.app.timers.is_registered(_deferred_create):
            bpy.app.timers.register(_deferred_create, first_interval=0.5)


def unregister():
    import bpy
    stop_sync()
    if bpy.app.timers.is_registered(_deferred_create):
        bpy.app.timers.unregister(_deferred_create)
