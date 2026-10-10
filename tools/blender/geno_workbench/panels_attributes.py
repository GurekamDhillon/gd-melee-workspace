"""Separate, lazily registered Attributes panel; source edits use WbSession only."""
# Blender property annotations must be evaluated, not postponed.
try:
    from . import api, props
    from .attributes import AttributeDraft, GROUPS
except ImportError:
    import api
    import props
    from attributes import AttributeDraft, GROUPS

STRINGS = props.STRINGS
_registered_classes = []
_owns_property = False
_callback_owner = None
_previous_callback = None
_change_callback = None
_drafts = {}
_syncing = False


def range_text(metadata):
    bounds = metadata["range"]
    low, high = bounds.get("minimum"), bounds.get("maximum")
    if low is None and high is None:
        return STRINGS["attribute_unbounded"]
    if low is None:
        return STRINGS["attribute_maximum"].format(value=high)
    if high is None:
        return STRINGS["attribute_minimum"].format(value=low)
    return STRINGS["attribute_range"].format(minimum=low, maximum=high)


def _record(scene):
    sess = api.session()
    key = scene.as_pointer()
    identity = (id(sess), sess.project_dir)
    record = _drafts.get(key)
    if record is None or record["identity"] != identity:
        record = {"identity": identity, "draft": AttributeDraft(), "rows": None}
        _drafts[key] = record
    if record["rows"] is not sess.attributes:
        record["draft"].refresh(sess.attributes)
        record["rows"] = sess.attributes
    return record


def _sync_scene(scene):
    global _syncing
    if not hasattr(scene, "geno_wb_attributes"):
        return
    draft = _record(scene)["draft"]
    settings = scene.geno_wb_attributes
    _syncing = True
    try:
        settings.items.clear()
        for metadata in draft.rows:
            item = settings.items.add()
            item.name = metadata["name"]
            item.integer = metadata["type"] == "integer"
            value = draft.value(item.name)
            item.override = value is not None
            if value is None:
                low = metadata["range"].get("minimum")
                high = metadata["range"].get("maximum")
                value = max(0, low) if low is not None else 0
                if high is not None:
                    value = min(value, high)
            if item.integer:
                item.int_value = int(value)
            else:
                item.float_value = float(value)
    finally:
        _syncing = False


def sync_from_session(sess):
    import bpy
    for scene in bpy.data.scenes:
        _sync_scene(scene)


def _value_changed(item, context):
    global _syncing
    if _syncing or not context or not context.scene:
        return
    draft = _record(context.scene)["draft"]
    previous = draft.value(item.name)
    try:
        if item.override:
            draft.set(item.name, item.int_value if item.integer else item.float_value)
    except ValueError as error:
        _syncing = True
        try:
            if item.integer:
                item.int_value = int(previous or 0)
            else:
                item.float_value = float(previous or 0)
        finally:
            _syncing = False
        api.session().report_error(error)


def _override_changed(item, context):
    if _syncing or not context or not context.scene:
        return
    draft = _record(context.scene)["draft"]
    if item.override:
        _value_changed(item, context)
    else:
        draft.reset(item.name)


def draw_attributes(layout, settings, draft, sess):
    controls = layout.row(align=True)
    controls.enabled = sess.connected
    controls.operator("geno_wb.refresh_attributes", text=STRINGS["attributes_refresh"], icon="FILE_REFRESH")
    layout.prop(settings, "filter", text=STRINGS["attributes_filter"])
    if not draft.rows:
        layout.label(text=STRINGS["attributes_connect"], icon="INFO")
    if draft.rows and not getattr(sess, "attributes_current", True):
        layout.label(text=STRINGS["attributes_cache_old"], icon="ERROR")
    items = {item.name: item for item in settings.items}
    for group in GROUPS:
        visible = draft.filtered(settings.filter, group)
        if not visible and settings.filter:
            continue
        box = layout.box()
        shown = bool(settings.filter.strip()) or getattr(settings, "show_" + group, True)
        header = box.row()
        header.prop(settings, "show_" + group, text=STRINGS["attributes_group_" + group],
                    icon="TRIA_DOWN" if shown else "TRIA_RIGHT", emboss=False)
        if not shown:
            continue
        for metadata in visible:
            item = items.get(metadata["name"])
            if item is None:
                continue
            editor = box.row()
            editor.enabled = sess.connected and draft.value(item.name) is not None
            editor.alert = item.name in draft.changed
            editor.prop(item, "int_value" if item.integer else "float_value",
                        text=item.name.replace("_", " "))
            box.label(text=range_text(metadata) + " · " + metadata.get("unit", "scalar"))
            if metadata.get("value") is None:
                override = box.row()
                override.enabled = sess.connected
                override.prop(item, "override", text=STRINGS["attribute_override"])
            if metadata.get("description"):
                box.label(text=metadata["description"])
        if group == "shield_ecb":
            box.label(text=STRINGS["attributes_ecb"])
            box.label(text=STRINGS["attributes_ecb_schema"])
    layout.label(text=STRINGS["attributes_changed"].format(count=len(draft.changed)))
    apply = layout.row()
    apply.enabled = sess.connected and bool(draft.changed)
    apply.operator("geno_wb.apply_attributes", text=STRINGS["attributes_apply"], icon="CHECKMARK")
    rebuild = layout.row()
    rebuild.enabled = sess.connected and sess.can_rebuild and not draft.changed
    rebuild.operator("geno_wb.rebuild_reload", text=STRINGS["rebuild_reload"], icon="FILE_REFRESH")
    if sess.stale:
        warning = layout.row()
        warning.alert = True
        warning.label(text=STRINGS["stale_banner"], icon="ERROR")
    if not sess.can_rebuild:
        layout.label(text=STRINGS["rebuild_unavailable"], icon="INFO")
    if sess.status:
        layout.label(text=sess.status, icon="ERROR" if sess.last_error else "INFO")


def _classes(bpy):
    class GenoWBAttributeItem(bpy.types.PropertyGroup):
        name: bpy.props.StringProperty()
        integer: bpy.props.BoolProperty()
        override: bpy.props.BoolProperty(name=STRINGS["attribute_override"], update=_override_changed)
        int_value: bpy.props.IntProperty(name=STRINGS["attribute_value"],
                                         description=STRINGS["attribute_value_help"], update=_value_changed)
        float_value: bpy.props.FloatProperty(name=STRINGS["attribute_value"],
                                             description=STRINGS["attribute_value_help"], precision=6, update=_value_changed)

    class GenoWBAttributes(bpy.types.PropertyGroup):
        filter: bpy.props.StringProperty(name=STRINGS["attributes_filter"])
        items: bpy.props.CollectionProperty(type=GenoWBAttributeItem)

    for group in GROUPS:
        GenoWBAttributes.__annotations__["show_" + group] = bpy.props.BoolProperty(
            name=STRINGS["attributes_group_" + group], default=False)

    class GENO_WB_OT_refresh_attributes(bpy.types.Operator):
        bl_idname = "geno_wb.refresh_attributes"
        bl_label = STRINGS["attributes_refresh"]

        def execute(self, context):
            ok = api.session().refresh_attributes()
            if not ok:
                self.report({"ERROR"}, api.session().last_error)
            return {"FINISHED"} if ok else {"CANCELLED"}

    class GENO_WB_OT_apply_attributes(bpy.types.Operator):
        bl_idname = "geno_wb.apply_attributes"
        bl_label = STRINGS["attributes_apply"]

        def execute(self, context):
            ok = _record(context.scene)["draft"].apply(api.session())
            _sync_scene(context.scene)
            if not ok:
                self.report({"ERROR"}, api.session().last_error)
            return {"FINISHED"} if ok else {"CANCELLED"}

    class GENO_WB_PT_attributes(bpy.types.Panel):
        bl_idname = "GENO_WB_PT_attributes"
        bl_label = STRINGS["attributes_panel"]
        bl_space_type = "VIEW_3D"
        bl_region_type = "UI"
        bl_category = STRINGS["tab"]

        def draw(self, context):
            draw_attributes(self.layout, context.scene.geno_wb_attributes,
                            _record(context.scene)["draft"], api.session())

    return (GenoWBAttributeItem, GenoWBAttributes, GENO_WB_OT_refresh_attributes,
            GENO_WB_OT_apply_attributes, GENO_WB_PT_attributes)


def register():
    global _owns_property, _callback_owner, _previous_callback, _change_callback
    import bpy
    if _registered_classes:
        return
    if hasattr(bpy.types.Scene, "geno_wb_attributes"):
        raise RuntimeError("Scene.geno_wb_attributes already exists")
    try:
        classes = _classes(bpy)
        for cls in classes:
            bpy.utils.register_class(cls)
            _registered_classes.append(cls)
        bpy.types.Scene.geno_wb_attributes = bpy.props.PointerProperty(type=classes[1])
        _owns_property = True
        sess = api.session()
        previous = sess.on_change
        def changed(value):
            if previous:
                previous(value)
            sync_from_session(value)
        _callback_owner, _previous_callback, _change_callback = sess, previous, changed
        sess.on_change = changed
        sync_from_session(sess)
    except Exception:
        unregister()
        raise


def unregister():
    global _owns_property, _callback_owner, _previous_callback, _change_callback
    import bpy
    errors = []
    if _callback_owner is not None and _callback_owner.on_change is _change_callback:
        _callback_owner.on_change = _previous_callback
    _callback_owner = _previous_callback = _change_callback = None
    if _owns_property:
        try:
            del bpy.types.Scene.geno_wb_attributes
            _owns_property = False
        except Exception as error:
            errors.append(str(error))
    for cls in reversed(tuple(_registered_classes)):
        try:
            bpy.utils.unregister_class(cls)
            _registered_classes.remove(cls)
        except Exception as error:
            errors.append(str(error))
    _drafts.clear()
    if errors:
        raise RuntimeError("; ".join(errors))
