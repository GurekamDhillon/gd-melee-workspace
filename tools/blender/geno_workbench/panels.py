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
        start.enabled = not value.connected and not operators.owned_server_running()
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
        move.enabled = value.connected
        move.prop(settings, "move")
        move.operator("geno_wb.refresh_rows", text="", icon="FILE_REFRESH")

        controls = self.layout.column()
        controls.enabled = value.connected and value.info is not None
        controls.prop(settings, "frame", slider=True)
        buttons = controls.row(align=True)
        buttons.operator(
            "geno_wb.step", text=STRINGS["first_frame"]
        ).n = -settings.frame
        previous = buttons.row(align=True)
        previous.enabled = settings.frame > 0
        previous.operator(
            "geno_wb.step", text=STRINGS["previous_frame"]
        ).n = -1
        buttons.operator(
            "geno_wb.play",
            text=STRINGS["pause"] if settings.playing else STRINGS["play"],
            icon="PAUSE" if settings.playing else "PLAY",
        )
        following = buttons.row(align=True)
        following.enabled = settings.frame < 600
        following.operator(
            "geno_wb.step", text=STRINGS["next_frame"]
        ).n = 1
        buttons.operator(
            "geno_wb.step", text=STRINGS["last_frame"]
        ).n = 600 - settings.frame
        frame = value.info.get("frame", STRINGS["unknown"]) if value.info else STRINGS["unknown"]
        self.layout.label(text=STRINGS["engine_frame"].format(frame=frame))
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
        items = self.layout.column()
        items.enabled = value.connected
        items.template_list(
            "GENO_WB_UL_problems", "",
            settings, "problem_items", settings, "problem_index", rows=4,
        )
        if not value.problems:
            self.layout.label(text=STRINGS["no_problems"])
        button = self.layout.row()
        button.enabled = (
            value.connected and 0 <= settings.problem_index < len(value.problems)
        )
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
            apply.row = value.row
            apply.ordinal = settings.hitbox_index
        else:
            self.layout.label(text=STRINGS["no_hitboxes"])
        self.layout.operator(
            "geno_wb.rebuild_reload",
            text=STRINGS["rebuild_reload"], icon="FILE_REFRESH",
        )


CLASSES = (
    GENO_WB_UL_problems,
    GENO_WB_UL_hitboxes,
    GENO_WB_PT_connect,
    GENO_WB_PT_timeline,
    GENO_WB_PT_problems,
    GENO_WB_PT_hitbox,
)
