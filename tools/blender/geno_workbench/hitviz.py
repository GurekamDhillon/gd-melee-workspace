"""Hitbox visualization in the Workbench viewport (phase 1, read-only).

The spheres stay in overlays.py (one mesh per slot). This module adds what meshes cannot carry cheaply:
launch arrows and the Sakurai fan (gpu lines, POST_VIEW), the "slot . damage%" label and the badges
(blf text, POST_PIXEL), and the swept capsule (a wire mesh in the same GenoWB Overlays collection).

Data comes from what the Workbench already holds: the frame's `hitboxes` (slot, joint, world, radius),
the previous cached frame (the sweep) and the move's source records (damage, angle, kbg, bkb, fkb,
element...), joined by slot and frame. The per-frame draw list is rebuilt only when the frame, facing,
settings or source change, so playback does no per-redraw maths.
"""

import bpy

try:
    from . import hitviz_math as M
    from . import overlays, shapes
except ImportError:
    import hitviz_math as M
    import overlays
    import shapes

_STATE = { "items": [], "batches": None, "handles": []}
SWEEP_PREFIX = "GenoWB.sweep."
FLAG_NAMES = ("hv_arrows", "hv_labels", "hv_badges", "hv_sweep")


def _flags(props):
    return {name: bool(getattr(props, name, True)) for name in FLAG_NAMES}


def _session_inputs(info):
    """(source records, previous frame's info or None, frame) from the live session, if there is one."""
    try:
        try:
            from . import api
        except ImportError:
            import api
        session = api.session()
    except Exception:
        return [], None, int(info.get("frame", 0) or 0)
    frame = int(info.get("frame", getattr(session, "frame", 0)) or 0)
    row = getattr(session, "loaded_row", "") or info.get("row", "")
    prev = None
    if frame > 1 and row:
        try:
            prev = session.cache.get(row, frame - 1)
        except Exception:
            prev = None
    source = list(getattr(session, "hitboxes", []) or [])
    return source, prev, frame


def update(info, scene=None, props=None):
    """Rebuild the draw list for `info` and drive the sweep meshes. Returns the touched object names."""
    scene = scene or bpy.context.scene
    if props is None:
        props = getattr(scene, "geno_wb", None)
    flags = _flags(props)
    percent = int(getattr(props, "hv_percent", "50") or 0)
    weight = float(getattr(props, "hv_weight", M.DEFAULT_WEIGHT))
    show = bool(getattr(props, "show_hit", True))
    source, prev, frame = _session_inputs(info)
    # update() runs once per frame change (never per redraw); the draw callbacks only replay this list.
    items = M.build_items(info, prev, source, frame, percent, weight, flags) if show else []
    _STATE.update(items=items, batches=None)
    _tag_redraw()
    touched = set()
    touched |= _update_sweeps(scene, _STATE["items"] if flags["hv_sweep"] else [])
    return touched


def _update_sweeps(scene, items):
    touched = set()
    collection = overlays.ensure_collection(scene) if items else bpy.data.collections.get(overlays.COLLECTION)
    if collection is None:
        return touched
    for item in items:
        if not item["sweep"]:
            continue
        a, b = item["sweep"]
        color = tuple(item["rgb"]) + (0.18,)
        slot = item["slot"]
        material = overlays._material("GenoWB.sweep.mat" + str(slot % 4), color)
        obj = overlays._object(collection, SWEEP_PREFIX + str(slot), material, color, "WIRE")
        verts, faces = shapes.capsule_mesh(a, b, item["radius"], seg=10, rings=3)
        overlays._write_geometry(obj, {"verts": verts, "faces": faces})
        overlays._visibility(obj, True)
        touched.add(obj.name)
    for obj in collection.objects:
        if obj.name.startswith(SWEEP_PREFIX) and obj.name not in touched and overlays._owned(obj):
            overlays._visibility(obj, False)
    return touched


def clear_state():
    _STATE.update(items=[], batches=None)
    _tag_redraw()


def items():
    return _STATE["items"]


def _tag_redraw():
    wm = getattr(bpy.context, "window_manager", None)
    if wm is None:
        return
    try:
        for window in wm.windows:
            for area in window.screen.areas:
                if area.type == "VIEW_3D":
                    area.tag_redraw()
    except Exception:
        pass


# ---- drawing --------------------------------------------------------------------------------------

def _build_batches():
    import gpu
    from gpu_extras.batch import batch_for_shader

    shader = gpu.shader.from_builtin("POLYLINE_UNIFORM_COLOR")
    groups = {}
    for item in _STATE["items"]:
        if not item["lines"] and not item["fan"]:
            continue
        rgb = M.METEOR_RGB if item["meteor"] else item["rgb"]
        groups.setdefault((tuple(rgb) + (1.0,), 4.0), []).extend(item["lines"])
        groups.setdefault((tuple(item["rgb"]) + (0.8,), 2.0), []).extend(item["fan"])
    out = []
    for (color, width), segs in groups.items():
        if not segs:
            continue
        coords = [tuple(p) for seg in segs for p in seg]
        out.append((color, width, batch_for_shader(shader, "LINES", {"pos": coords})))
    return shader, out


def _draw_view():
    props = getattr(bpy.context.scene, "geno_wb", None)
    if props is None or not getattr(props, "hv_arrows", True) or not _STATE["items"]:
        return
    import gpu

    if _STATE["batches"] is None:
        _STATE["batches"] = _build_batches()
    shader, batches = _STATE["batches"]
    region = bpy.context.region
    size = (region.width, region.height) if region else (1, 1)
    gpu.state.blend_set("ALPHA")
    gpu.state.depth_test_set("NONE")
    shader.bind()
    shader.uniform_float("viewportSize", size)
    for color, width, batch in batches:
        shader.uniform_float("lineWidth", width)
        shader.uniform_float("color", color)
        batch.draw(shader)
    gpu.state.blend_set("NONE")


def _draw_text():
    import blf
    from bpy_extras.view3d_utils import location_3d_to_region_2d

    props = getattr(bpy.context.scene, "geno_wb", None)
    if props is None or not _STATE["items"]:
        return
    labels, badges = getattr(props, "hv_labels", True), getattr(props, "hv_badges", True)
    if not (labels or badges):
        return
    region, rv3d = bpy.context.region, bpy.context.region_data
    if region is None or rv3d is None:
        return
    font = 0
    blf.size(font, 15.0)
    blf.enable(font, blf.SHADOW)
    blf.shadow(font, 3, 0.0, 0.0, 0.0, 0.9)
    for item in _STATE["items"]:
        from mathutils import Vector

        centre = Vector(item["centre"])
        point = location_3d_to_region_2d(region, rv3d, centre + Vector((0.0, 0.0, item["radius"])))
        if point is None:
            continue
        rgb = item["rgb"]
        y = point.y + 6
        if labels:
            blf.color(font, rgb[0], rgb[1], rgb[2], 1.0)
            blf.position(font, point.x + 8, y, 0)
            blf.draw(font, item["label"])
            y -= 18
        if badges and item["badges"]:
            blf.color(font, 0.95, 0.95, 0.95, 1.0)
            for tag in item["badges"]:
                blf.position(font, point.x + 8, y, 0)
                blf.draw(font, "[" + tag + "]")
                y -= 16
    blf.disable(font, blf.SHADOW)


_ICONS = {"coll": None}


def swatch(slot):
    """icon_id of a solid swatch in the slot's colour (0 when previews are unavailable)."""
    coll = _ICONS["coll"]
    if coll is None:
        return 0
    name = "slot%d" % (int(slot) % 4)
    preview = coll.get(name)
    if preview is None:
        preview = coll.new(name)
        preview.icon_size = (32, 32)
        preview.image_size = (32, 32)
        rgb = M.slot_rgb(slot)
        preview.icon_pixels_float = [rgb[0], rgb[1], rgb[2], 1.0] * (32 * 32)
        preview.image_pixels_float = list(preview.icon_pixels_float)
    return preview.icon_id


def register():
    if _STATE["handles"]:
        return
    try:
        from bpy.utils import previews
        _ICONS["coll"] = previews.new()
    except Exception:
        _ICONS["coll"] = None
    space = bpy.types.SpaceView3D
    _STATE["handles"] = [
        space.draw_handler_add(_draw_view, (), "WINDOW", "POST_VIEW"),
        space.draw_handler_add(_draw_text, (), "WINDOW", "POST_PIXEL"),
    ]


def unregister():
    space = bpy.types.SpaceView3D
    for handle in _STATE["handles"]:
        try:
            space.draw_handler_remove(handle, "WINDOW")
        except Exception:
            pass
    _STATE["handles"] = []
    _STATE.update(items=[], batches=None)
    if _ICONS["coll"] is not None:
        try:
            from bpy.utils import previews
            previews.remove(_ICONS["coll"])
        except Exception:
            pass
        _ICONS["coll"] = None


def registered():
    return bool(_STATE["handles"])
