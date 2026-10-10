"""The Task 6 Connect box in the 3D View's Geno sidebar."""

import bpy

try:
    from . import api, operators, props
except ImportError:
    import api
    import operators
    import props


STRINGS = props.STRINGS


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

        start = box.row()
        start.enabled = not value.connected and not operators.owned_server_running()
        start.operator(
            "geno_wb.start_server", text=STRINGS["start_server"], icon="PLAY"
        )

        buttons = box.row(align=True)
        buttons.operator(
            "geno_wb.connect", text=STRINGS["connect"], icon="LINKED"
        )
        buttons.operator(
            "geno_wb.disconnect", text=STRINGS["disconnect"], icon="UNLINKED"
        )
        box.operator(
            "geno_wb.engine_restart",
            text=STRINGS["restart_engine"],
            icon="FILE_REFRESH",
        )

        icon = "ERROR" if value.last_error else "INFO"
        box.label(text=settings.status, icon=icon)


CLASSES = (GENO_WB_PT_connect,)
