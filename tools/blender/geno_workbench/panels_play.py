"""Small independent Playtest panel; no engine connection is required."""
import bpy
from .props import STRINGS
from . import operators_play  # supplies this panel's centralized strings

_REGISTERED = False


class GENO_WB_PT_play(bpy.types.Panel):
    bl_idname = "GENO_WB_PT_play"
    bl_label = STRINGS["play_panel"]
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = STRINGS["tab"]
    bl_order = 21

    @classmethod
    def poll(cls, context):
        return context.scene is not None and hasattr(context.scene, "geno_wb")

    def draw(self, context):
        settings = context.scene.geno_wb
        self.layout.prop(settings, "project")
        row = self.layout.row(align=True)
        row.operator("geno_wb.play_lab", icon="PLAY")
        row.operator("geno_wb.play_cpu", icon="PLAY")
        if not settings.project.strip():
            self.layout.label(text=STRINGS["play_project_required"], icon="INFO")
        if settings.status:
            self.layout.label(text=settings.status, icon="INFO")


def register():
    global _REGISTERED
    if not _REGISTERED:
        bpy.utils.register_class(GENO_WB_PT_play)
        _REGISTERED = True


def unregister():
    global _REGISTERED
    if _REGISTERED:
        bpy.utils.unregister_class(GENO_WB_PT_play)
        _REGISTERED = False
