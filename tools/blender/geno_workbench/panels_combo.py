"""Geno > Combo: pick a combo string and play it back to back in the viewport, cutting at each route's window.

Reads the strings from the Workbench server (``list_strings``), asks it for the moves, clips, hitboxes and routes
(``string_plan``) and lays the string out with combo_play_bpy.  A pure preview: the clips are the actions already in the
blend, nothing needs the game.  "Send to game" also runs the same sequence on the engine (``play_string``) when it is up.
"""
import bpy
from bpy.props import BoolProperty, EnumProperty

from . import api, combo_play_bpy as CB
from .props import STRINGS

_CLASSES = []
_STATE = {"strings": [], "last": None}


def _items(self, context):
    items = [(str(i), s.get("name", "string %d" % i), "%d steps" % len(s.get("steps", []))) for i, s in enumerate(_STATE["strings"])]
    return items or [("-1", "(no strings: Refresh)", "")]


def _request(tool, args=None):
    sess = api.session()
    return sess._request(tool, args)


class GENO_WB_OT_combo_refresh(bpy.types.Operator):
    bl_idname = "geno_wb.combo_refresh"
    bl_label = "Refresh strings"
    bl_description = "Read the combo strings of the project from the Workbench server"

    def execute(self, context):
        try:
            _STATE["strings"] = list(_request("list_strings").get("strings", []))
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        self.report({"INFO"}, "%d combo strings" % len(_STATE["strings"]))
        return {"FINISHED"}


class GENO_WB_OT_combo_play(bpy.types.Operator):
    bl_idname = "geno_wb.combo_play"
    bl_label = "Play string"
    bl_description = "Lay the string's moves back to back on the fighter and play them, cutting at each route's window"

    def execute(self, context):
        scene = context.scene
        index = int(scene.geno_combo_string) if str(scene.geno_combo_string).lstrip("-").isdigit() else -1
        if index < 0:
            self.report({"ERROR"}, "Refresh strings and pick one")
            return {"CANCELLED"}
        try:
            reply = _request("string_plan", {"index": index})
            summary = CB.build(scene, reply, add_buffer=scene.geno_combo_buffer, hitboxes=scene.geno_combo_hitboxes)
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        _STATE["last"] = summary
        note = ""
        if summary["missing_clips"]:
            note = "; no clip for: " + ", ".join(summary["missing_clips"])
        if scene.geno_combo_engine:
            try:
                _request("play_string", {"index": index, "add_buffer": bool(scene.geno_combo_buffer), "realtime": True})
            except Exception as exc:
                note += "; game: %s" % exc
        self.report({"INFO"}, "%d frames, %d cancels%s" % (summary["frames"], sum(1 for m in summary["markers"] if m["kind"] == "cancel"), note))
        if bpy.app.background is False and not context.screen.is_animation_playing:
            bpy.ops.screen.animation_play()
        return {"FINISHED"}


class GENO_WB_OT_combo_clear(bpy.types.Operator):
    bl_idname = "geno_wb.combo_clear"
    bl_label = "Clear string"
    bl_description = "Remove the string track, markers, ribbon and hitbox spheres and give the fighter its own action back"

    def execute(self, context):
        CB.clear(context.scene)
        return {"FINISHED"}


class GENO_WB_PT_combo(bpy.types.Panel):
    bl_idname = "GENO_WB_PT_combo"
    bl_label = "Combo"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = STRINGS["tab"]
    bl_order = 23

    @classmethod
    def poll(cls, context):
        return context.scene is not None and hasattr(context.scene, "geno_combo_string")

    def draw(self, context):
        lay = self.layout
        scene = context.scene
        row = lay.row(align=True)
        row.prop(scene, "geno_combo_string", text="")
        row.operator("geno_wb.combo_refresh", text="", icon="FILE_REFRESH")
        lay.prop(scene, "geno_combo_buffer")
        lay.prop(scene, "geno_combo_hitboxes")
        lay.prop(scene, "geno_combo_engine")
        row = lay.row(align=True)
        row.operator("geno_wb.combo_play", icon="PLAY")
        row.operator("geno_wb.combo_clear", icon="X")
        last = _STATE["last"]
        if last:
            lay.label(text="%d frames; %d strips" % (last["frames"], len(last["strips"])))
            for seg in last["plan"]:
                text = "%s: cut f%d" % (seg["move"], seg["cut"]) + (" (%s)" % seg["route"] if seg["linked"] else " (plays out)")
                lay.label(text=text)
            for item in last["missing_clips"]:
                lay.label(text="no clip: " + item, icon="ERROR")


def register():
    if _CLASSES:
        return
    bpy.types.Scene.geno_combo_string = EnumProperty(name="String", items=_items)
    bpy.types.Scene.geno_combo_buffer = BoolProperty(name="Cut at window start + buffer", default=False,
                                                     description="Cut buffer frames after the window opens (a late press) instead of at its start")
    bpy.types.Scene.geno_combo_hitboxes = BoolProperty(name="Hitbox markers", default=True,
                                                       description="Spheres on the hitbox bones while the source says they are active")
    bpy.types.Scene.geno_combo_engine = BoolProperty(name="Also send to the game", default=False,
                                                     description="Run the same sequence on the engine when it is connected")
    for cls in (GENO_WB_OT_combo_refresh, GENO_WB_OT_combo_play, GENO_WB_OT_combo_clear, GENO_WB_PT_combo):
        bpy.utils.register_class(cls)
        _CLASSES.append(cls)


def unregister():
    for cls in reversed(tuple(_CLASSES)):
        bpy.utils.unregister_class(cls)
        _CLASSES.remove(cls)
    for name in ("geno_combo_string", "geno_combo_buffer", "geno_combo_hitboxes", "geno_combo_engine"):
        if hasattr(bpy.types.Scene, name):
            delattr(bpy.types.Scene, name)
