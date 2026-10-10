"""Independent Fighter panel; register after operators_fighter."""

import bpy

try:
    from . import api, operators_fighter, pose
    from .props import STRINGS
except ImportError:
    import api
    import operators_fighter
    import pose
    from props import STRINGS


for _key, _value in {
    "fighter_panel_title": "Fighter",
    "fighter_panel_tab": "Geno",
    "fighter_art_override": "Art override",
    "fighter_uncalibrated": "Calibration: not set",
    "fighter_mapping_summary": "Mapped joints: {mapped} / {total}",
    "fighter_missing_summary": "Missing joints: {count}",
    "fighter_unmapped_summary": "Unmapped bones: {count}",
    "fighter_synth_summary": "Synthesized joints skipped: {count}",
    "fighter_scale_summary": "Calibration scale: {scale:.6g}",
    "fighter_error_summary": "Maximum head error: {error:.6g}",
    "fighter_not_verified": "Pose error: not verified for this frame",
}.items():
    STRINGS.setdefault(_key, _value)


def _text(key, **values):
    return STRINGS[key].format(**values)


class GENO_WB_PT_fighter(bpy.types.Panel):
    bl_idname = "GENO_WB_PT_fighter"
    bl_label = STRINGS["fighter_panel_title"]
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = STRINGS["fighter_panel_tab"]
    bl_order = 20

    @classmethod
    def poll(cls, context):
        return (
            context.scene is not None
            and hasattr(context.scene, "geno_wb_fighter")
        )

    def draw(self, context):
        layout = self.layout
        fighter = context.scene.geno_wb_fighter
        main = getattr(context.scene, "geno_wb", None)
        session = api.session()

        if main is not None:
            layout.prop(
                main, "blender_art", text=STRINGS["fighter_art_override"]
            )
        layout.prop_search(
            fighter, "armature", bpy.data, "objects",
            text=STRINGS["fighter_armature_label"],
        )
        row = layout.row(align=True)
        row.operator("geno_wb.load_fighter", icon="IMPORT")
        row.operator("geno_wb.calibrate", icon="ARMATURE_DATA")

        if fighter.art_path:
            row = layout.row()
            row.enabled = False
            row.prop(
                fighter, "art_path", text=STRINGS["fighter_art_path_label"]
            )

        arm = operators_fighter.active_armature(context)
        calibration = pose.calibration_for(arm)
        box = layout.box()
        if calibration is None:
            box.label(text=STRINGS["fighter_uncalibrated"], icon="INFO")
        else:
            jointmap, cal = calibration
            mapped = len(jointmap.by_index)
            box.label(text=_text(
                "fighter_mapping_summary",
                mapped=mapped,
                total=mapped + len(jointmap.missing_bones),
            ))
            box.label(text=_text(
                "fighter_missing_summary", count=len(jointmap.missing_bones)
            ))
            box.label(text=_text(
                "fighter_unmapped_summary", count=len(jointmap.unmapped_bones)
            ))
            box.label(text=_text(
                "fighter_synth_summary", count=len(jointmap.skipped_synth)
            ))
            box.label(text=_text("fighter_scale_summary", scale=cal.scale))
            if fighter.pose_error < 0:
                box.label(text=STRINGS["fighter_not_verified"])
            else:
                box.label(text=_text(
                    "fighter_error_summary", error=fighter.pose_error
                ))

        row = layout.row()
        row.operator("geno_wb.verify_pose", icon="CHECKMARK")
        status = getattr(main, "status", "") if main is not None else ""
        status = status or session.status
        if status:
            layout.label(
                text=status,
                icon="ERROR" if session.last_error else "INFO",
            )


_REGISTERED = False


def register():
    global _REGISTERED
    if not _REGISTERED:
        bpy.utils.register_class(GENO_WB_PT_fighter)
        _REGISTERED = True


def unregister():
    global _REGISTERED
    if _REGISTERED:
        bpy.utils.unregister_class(GENO_WB_PT_fighter)
        _REGISTERED = False
