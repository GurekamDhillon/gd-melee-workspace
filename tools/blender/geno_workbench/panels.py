"""Connect, timeline, problems and source-hitbox panels in the Geno sidebar."""

import bpy

try:
    from . import api, operators, props
except ImportError:
    import api
    import operators
    import props


STRINGS = props.STRINGS


class GENO_WB_UL_problems(bpy.types.UIList):
    def draw_item(
        self, context, layout, data, item, icon,
        active_data, active_propname, index=0, flt_flag=0,
    ):
        layout.label(text=item.get("label", ""), icon="ERROR")


class GENO_WB_UL_hitboxes(bpy.types.UIList):
    def draw_item(
        self, context, layout, data, item, icon,
        active_data, active_propname, index=0, flt_flag=0,
    ):
        layout.label(text=item.get("label", ""), icon="SPHERE")


class GENO_WB_PT_connect(bpy.types.Panel):
    bl_idname = "GENO_WB_PT_connect"
    bl_label = STRINGS["addon_name"]
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = STRINGS["tab"]

    def draw(self, context):
        settings = context.scene.geno_wb
        value = api.session()
        box = self.layout.box()
        box.label(text=STRINGS["connect_panel"])
        box.prop(settings, "host")
        box.prop(settings, "port")
        box.prop(settings, "project")
        box.prop(settings, "launcher_exe")
        box.prop(settings, "engine_exe")
        box.prop(settings, "mods_dir")
        box.prop(settings, "iso_path")
        start = box.row()
        start.operator(
            "geno_wb.start_server", text=STRINGS["start_server"], icon="PLAY"
        )
        buttons = box.row(align=True)
        buttons.operator("geno_wb.connect", text=STRINGS["connect"], icon="LINKED")
        buttons.operator(
            "geno_wb.disconnect", text=STRINGS["disconnect"], icon="UNLINKED"
        )
        box.operator(
            "geno_wb.engine_restart",
            text=STRINGS["restart_engine"], icon="FILE_REFRESH",
        )
        box.label(
            text=settings.status, icon="ERROR" if value.last_error else "INFO"
        )


class GENO_WB_PT_timeline(bpy.types.Panel):
    bl_idname = "GENO_WB_PT_timeline"
    bl_label = STRINGS["timeline_panel"]
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = STRINGS["tab"]

    def draw(self, context):
        settings = context.scene.geno_wb
        value = api.session()
        move = self.layout.row(align=True)
        choice = move.row(align=True)
        choice.enabled = value.connected
        choice.prop(settings, "move")
        move.operator("geno_wb.refresh_rows", text="", icon="FILE_REFRESH")

        controls = self.layout.column()
        slider = controls.row()
        slider.enabled = value.connected and value.info is not None
        slider.prop(settings, "frame", slider=True)
        buttons = controls.row(align=True)
        buttons.operator(
            "geno_wb.step", text=STRINGS["first_frame"]
        ).n = -settings.frame
        previous = buttons.row(align=True)
        previous.operator(
            "geno_wb.step", text=STRINGS["previous_frame"]
        ).n = -1
        buttons.operator(
            "geno_wb.play",
            text=STRINGS["pause"] if settings.playing else STRINGS["play"],
            icon="PAUSE" if settings.playing else "PLAY",
        )
        following = buttons.row(align=True)
        following.operator(
            "geno_wb.step", text=STRINGS["next_frame"]
        ).n = 1
        buttons.operator(
            "geno_wb.step", text=STRINGS["last_frame"]
        ).n = 600 - settings.frame
        frame = value.info.get("frame", STRINGS["unknown"]) if value.info else STRINGS["unknown"]
        frames = value.row_frames()
        length = "  (" + STRINGS["move_length"].format(frames=frames) + ")" if frames else ""
        self.layout.label(text=STRINGS["engine_frame"].format(frame=frame) + length)
        done, total, loading = value.pump_cache()
        if total and (loading or done < total):
            row = self.layout.row()
            try:
                row.progress(factor=done / total, type="BAR", text=STRINGS["cache_loading"].format(done=done, total=total))
            except (AttributeError, TypeError):
                row.label(text=STRINGS["cache_loading"].format(done=done, total=total), icon="TIME")
        elif total:
            self.layout.label(text=STRINGS["cache_ready"].format(total=total), icon="CHECKMARK")
        self.layout.prop(settings, "play_speed")
        self.layout.prop(settings, "loop")
        self.layout.prop(settings, "show_travel")
        self.layout.label(
            text=settings.status, icon="ERROR" if value.last_error else "INFO"
        )


class GENO_WB_PT_problems(bpy.types.Panel):
    bl_idname = "GENO_WB_PT_problems"
    bl_label = STRINGS["problems_panel"]
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = STRINGS["tab"]

    def draw(self, context):
        settings = context.scene.geno_wb
        value = api.session()
        self.layout.operator(
            "geno_wb.run_checks", text=STRINGS["run_checks"], icon="CHECKMARK"
        )
        if not value.has_roles:
            self.layout.label(text=STRINGS["no_roles"], icon="INFO")
        items = self.layout.column()
        items.enabled = value.connected
        items.template_list(
            "GENO_WB_UL_problems", "",
            settings, "problem_items", settings, "problem_index", rows=4,
        )
        if not value.problems:
            self.layout.label(text=STRINGS["no_problems"])
        button = self.layout.row()
        button.operator(
            "geno_wb.goto_problem", text=STRINGS["goto_problem"]
        ).index = settings.problem_index


class GENO_WB_PT_hitbox(bpy.types.Panel):
    bl_idname = "GENO_WB_PT_hitbox"
    bl_label = STRINGS["hitbox_panel"]
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = STRINGS["tab"]

    def draw(self, context):
        settings = context.scene.geno_wb
        value = api.session()
        if value.stale:
            warning = self.layout.box()
            warning.alert = True
            warning.label(text=STRINGS["stale_banner"], icon="ERROR")
            warning.label(text=STRINGS["stale_overlays"])
        self.layout.template_list(
            "GENO_WB_UL_hitboxes", "",
            settings, "hitbox_items", settings, "hitbox_index", rows=4,
        )
        selected = 0 <= settings.hitbox_index < len(value.hitboxes)
        if selected:
            editor = self.layout.column(align=True)
            editor.enabled = value.connected
            editor.prop(settings, "edit_bone")
            row = editor.row(align=True)
            row.prop(settings, "edit_damage")
            row.prop(settings, "edit_size")
            row = editor.row(align=True)
            for field in ("x", "y", "z"):
                row.prop(settings, "edit_" + field)
            for field in ("angle", "kbg", "fkb", "bkb"):
                editor.prop(settings, "edit_" + field)
            row = editor.row(align=True)
            row.prop(settings, "edit_start_frame")
            row.prop(settings, "edit_end_frame")
            actions = editor.row(align=True)
            actions.operator(
                "geno_wb.suggest_bone", text=STRINGS["suggest_bone"]
            )
            apply = actions.operator(
                "geno_wb.edit_hitbox", text=STRINGS["edit_hitbox"]
            )
            apply.row = value.source_row
            apply.ordinal = settings.hitbox_index
        else:
            self.layout.label(text=STRINGS["no_hitboxes"])
        self.layout.operator(
            "geno_wb.rebuild_reload",
            text=STRINGS["rebuild_reload"], icon="FILE_REFRESH",
        )
        if not value.can_rebuild:
            self.layout.label(text=STRINGS["rebuild_unavailable"], icon="INFO")


class GENO_WB_PT_splice(bpy.types.Panel):
    bl_idname = "GENO_WB_PT_splice"
    bl_label = STRINGS["nla_panel"]
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = STRINGS["tab"]

    def draw(self, context):
        settings = context.scene.geno_wb
        body = self.layout.column()
        body.prop(settings, "project")
        body.prop(settings, "nla_height")
        body.prop(settings, "nla_clip")
        body.operator("geno_wb.import_clip", icon="IMPORT")
        body.prop(settings, "nla_recipe_file")
        body.prop(settings, "nla_recipe")
        body.operator("geno_wb.layout_recipe", icon="NLA")
        body.label(text=STRINGS["nla_edit_hint"])
        body.label(text=STRINGS["nla_preview_hint"])
        body.operator("geno_wb.save_strips", icon="FILE_TICK")
        body.label(text=STRINGS["nla_save_hint"])
        body.prop(settings, "nla_action_name")
        body.prop(settings, "nla_export_path")
        body.operator("geno_wb.bake_export", icon="EXPORT")


CLASSES = (
    GENO_WB_UL_problems,
    GENO_WB_UL_hitboxes,
    GENO_WB_PT_connect,
    GENO_WB_PT_timeline,
    GENO_WB_PT_problems,
    GENO_WB_PT_hitbox,
    GENO_WB_PT_splice,
)
