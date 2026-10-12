"""Geno > Animate: the control rig and hand-animation panel (sidebar, N panel, tab "Geno").

Thin operators over tools/geno/artist/blender/{anim_rig,hand_bake,hand_layer}.py, which hold the logic and run headless too
(blender -b ... --python), see tools/blender/geno_workbench/tests/blender_anim_rig_check.py. Independent of a running workbench server.
"""
import json
import sys
from pathlib import Path

import bpy
from bpy.props import EnumProperty, StringProperty, PointerProperty, BoolProperty

_REGISTERED = False
HAND_REL = "anim/hand.json"


def _lib():
    """Import the shared rig modules; they live in the workspace (…/tools/geno/artist/blender), found from this file's real path."""
    workspace = Path(__file__).resolve().parents[3]
    if (workspace / "tools/geno/artist/blender/anim_rig.py").is_file() and str(workspace) not in sys.path:
        sys.path.insert(0, str(workspace))
    from tools.geno.artist.blender import anim_rig, hand_bake, hand_layer
    return anim_rig, hand_bake, hand_layer


def _deform(context):
    ob = context.object
    if ob is None or ob.type != "ARMATURE":
        raise ValueError("select the fighter's deform armature (or its control rig)")
    if "geno_deform" in ob:
        return bpy.data.objects[ob["geno_deform"]]
    return ob


def _ctrl(context):
    rig, _, _ = _lib()
    ctrl = rig.ctrl_object(_deform(context))
    if ctrl is None:
        raise ValueError("no control rig yet: click Generate rig")
    return ctrl


def hand_path(context):
    s = context.scene.geno_anim
    if s.hand_file:
        return Path(bpy.path.abspath(s.hand_file)).expanduser().resolve()
    project = getattr(getattr(context.scene, "geno_wb", None), "project", "")
    if not project:
        raise ValueError("set the Project (Connect panel) or a Hand file")
    base = Path(bpy.path.abspath(project)).expanduser().resolve()
    try:
        rel = json.loads((base / "workbench.json").read_text(encoding="utf-8")).get("hand", HAND_REL)
    except (OSError, ValueError):
        rel = HAND_REL
    return base / rel


def _fighter_name(context):
    try:
        return json.loads(_deform(context).get("geno", "{}")).get("fighter") or _deform(context).name
    except (ValueError, TypeError):
        return _deform(context).name


def _row_search(self, context, edit_text):
    return sorted(a.name for a in bpy.data.actions if not a.name.startswith("hand:") and edit_text.lower() in a.name.lower())[:200]


class GenoAnimProps(bpy.types.PropertyGroup):
    row: StringProperty(name="Row", description="Engine row (the converted clip's name) to hand-animate", search=_row_search)
    mode: EnumProperty(name="Mode", items=[("layer", "Layer", "Your edits are added on top of the converted clip"),
                                             ("replace", "Replace", "Start from the rest pose; the clip is entirely yours")], default="layer")
    hand_file: StringProperty(name="Hand file", subtype="FILE_PATH", description="Default: <Project>/anim/hand.json")
    status: StringProperty()


def _run(op, context, fn):
    try:
        message = fn()
    except Exception as exc:  # noqa: BLE001 - shown in the status bar
        context.scene.geno_anim.status = str(exc)
        op.report({"ERROR"}, str(exc))
        return {"CANCELLED"}
    context.scene.geno_anim.status = message
    op.report({"INFO"}, message)
    return {"FINISHED"}


class GENO_ANIM_OT_generate(bpy.types.Operator):
    bl_idname = "geno_anim.generate"
    bl_label = "Generate rig"
    bl_description = "Build the FK/IK control rig over the active deform armature (re-run after Stage A rewrote the file); deform bones are not changed"

    def execute(self, context):
        def go():
            rig, _, _ = _lib()
            arm = _deform(context)
            ctrl = rig.generate(arm)            # handles its own mode switches (explicit override, no pose-mode switch)
            for ob in list(context.view_layer.objects):
                ob.select_set(False)
            ctrl.select_set(True)
            context.view_layer.objects.active = ctrl
            info = rig.limbs_info(ctrl)
            extras = [n for n in ("spine", "look") if n in info] + (["shoulders"] if any("shoulder" in e for e in info["limbs"].values()) else [])
            return f"Control rig {ctrl.name}: {len(info['limbs'])} IK limbs, " + (", ".join(extras) if extras else "no spine/look-at/shoulder extras")
        return _run(self, context, go)


class GENO_ANIM_OT_new_clip(bpy.types.Operator):
    bl_idname = "geno_anim.new_clip"
    bl_label = "Start / restart clip"
    bl_description = "Create the hand action for the Row on the control rig, seeded from the converted clip (Layer) or the rest pose (Replace)"

    def execute(self, context):
        def go():
            _, bake, _ = _lib()
            s = context.scene.geno_anim
            act = bake.new_clip(_ctrl(context), s.row, s.mode)
            return f"{act.name}: {bake.frame_count(act)} frames, {s.mode}. Animate the FK/IK controls, then Bake + save."
        return _run(self, context, go)


class GENO_ANIM_OT_load_clip(bpy.types.Operator):
    bl_idname = "geno_anim.load_clip"
    bl_label = "Load saved clip"
    bl_description = "Re-create the editable action for the Row from the hand file (IK work comes back as FK keys)"

    def execute(self, context):
        def go():
            _, bake, layer = _lib()
            s = context.scene.geno_anim
            doc = layer.load(hand_path(context))
            if not doc or s.row not in doc["clips"]:
                raise ValueError(f"no saved hand clip '{s.row}' in {hand_path(context)}")
            act = bake.load_clip(_ctrl(context), doc, s.row)
            return f"Loaded {act.name} from {hand_path(context).name}"
        return _run(self, context, go)


class GENO_ANIM_OT_bake_save(bpy.types.Operator):
    bl_idname = "geno_anim.bake_save"
    bl_label = "Bake + save"
    bl_description = "Bake the hand action (IK included) to deform-bone deltas, check it against the rig, and write the hand file; then Rebuild + reload"

    def execute(self, context):
        def go():
            _, bake, _ = _lib()
            s = context.scene.geno_anim
            ctrl = _ctrl(context)
            act = ctrl.animation_data.action if ctrl.animation_data else None
            if act is None or not act.name.startswith(bake.ACTION_PREFIX):
                raise ValueError("the control rig is not playing a hand action: Start / restart clip first")
            row = act.get("geno_hand_row", act.name[len(bake.ACTION_PREFIX):])
            clip, rep = bake.bake_clip(ctrl, act, row, act.get("geno_hand_mode", s.mode))
            path = bake.save_clip(hand_path(context), _fighter_name(context), row, clip)
            return (f"Saved {row} to {path} ({rep['bones_stored']} bones, bake vs rig {rep['max_pos_err']:.5f} units / "
                    f"{rep['max_rot_err_rad']:.5f} rad). Now Rebuild + reload.")
        return _run(self, context, go)


class GENO_ANIM_OT_delete_clip(bpy.types.Operator):
    bl_idname = "geno_anim.delete_clip"
    bl_label = "Remove saved clip"
    bl_description = "Delete the Row from the hand file (the converted clip plays again after Rebuild)"

    def execute(self, context):
        def go():
            _, bake, _ = _lib()
            row = context.scene.geno_anim.row
            return f"Removed {row}" if bake.delete_clip(hand_path(context), row) else f"{row} was not in the hand file"
        return _run(self, context, go)


class GENO_ANIM_OT_snap(bpy.types.Operator):
    bl_idname = "geno_anim.snap"
    bl_label = "Switch limb"
    bl_description = "Switch the limb between FK and IK, matching the current pose so nothing jumps"
    limb: StringProperty()
    to_ik: BoolProperty(default=True)

    def execute(self, context):
        def go():
            rig, _, _ = _lib()
            ctrl = _ctrl(context)
            rig.auto_snap_on_switch(ctrl, self.limb, self.to_ik)
            return f"{self.limb}: {'IK' if self.to_ik else 'FK'} (key the new pose and the 'ik' value at this frame)"
        return _run(self, context, go)


class GENO_ANIM_OT_space(bpy.types.Operator):
    bl_idname = "geno_anim.space"
    bl_label = "Switch space"
    bl_description = "Make the IK hand/foot (and its pole) follow world, root, COG, chest or head, keeping the pose; keys the switch when Auto Keying is on"
    limb: StringProperty()
    space: StringProperty()

    def execute(self, context):
        def go():
            rig, _, _ = _lib()
            ctrl = _ctrl(context)
            rig.set_space(ctrl, self.limb, self.space, key=bool(context.scene.tool_settings.use_keyframe_insert_auto))
            return f"{self.limb} follows {self.space}"
        return _run(self, context, go)


class GENO_ANIM_OT_view_converted(bpy.types.Operator):
    bl_idname = "geno_anim.view_converted"
    bl_label = "Rig on / off"
    bl_description = "Mute or enable the rig's constraints on the deform armature (off: the converted clip plays as imported)"

    def execute(self, context):
        def go():
            rig, _, _ = _lib()
            arm = _deform(context)
            on = any(c.mute for pb in arm.pose.bones for c in pb.constraints if c.name.startswith("GENO_"))
            rig.set_bound(arm, on)
            return "rig on" if on else "rig off: deform armature plays its own action"
        return _run(self, context, go)


class GENO_ANIM_PT_panel(bpy.types.Panel):
    bl_idname = "GENO_ANIM_PT_panel"
    bl_label = "Animate (IK/FK)"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Geno"

    def draw(self, context):
        s = context.scene.geno_anim
        col = self.layout.column()
        col.operator("geno_anim.generate", icon="ARMATURE_DATA")
        col.separator()
        col.prop(s, "row")
        col.prop(s, "mode", expand=True)
        col.prop(s, "hand_file")
        r = col.row(align=True)
        r.operator("geno_anim.new_clip", icon="ADD")
        r.operator("geno_anim.load_clip", icon="IMPORT")
        col.operator("geno_anim.bake_save", icon="FILE_TICK")
        col.operator("geno_anim.delete_clip", icon="TRASH")
        col.operator("geno_anim.view_converted", icon="HIDE_OFF")
        ob = context.object
        if ob is not None and ob.type == "ARMATURE" and "geno_limbs" in ob:
            box = self.layout.box()
            box.label(text="Limbs: FK 0 .. IK 1")
            info = json.loads(ob["geno_limbs"])["limbs"]
            for lid, e in info.items():
                row = box.row(align=True)
                row.label(text=lid)
                row.prop(ob.pose.bones[e["switch"]], '["ik"]', text="", slider=True)
                a = row.operator("geno_anim.snap", text="to IK")
                a.limb, a.to_ik = lid, True
                b = row.operator("geno_anim.snap", text="to FK")
                b.limb, b.to_ik = lid, False
                if "spaces" in e:
                    srow = box.row(align=True)
                    srow.label(text="follows")
                    current = int(ob.pose.bones[e["switch"]].get("space", 0))
                    for i, sname in enumerate(e["spaces"]):
                        op = srow.operator("geno_anim.space", text=sname.title(), depress=(i == current))
                        op.limb, op.space = lid, sname
                if "shoulder" in e:
                    box.prop(ob.pose.bones[e["switch"]], '["shoulder"]', text=f"{lid} clavicle follow", slider=True)
            full = json.loads(ob["geno_limbs"])
            if "spine" in full or "look" in full:
                box2 = self.layout.box()
                box2.label(text="Torso and head")
                if "spine" in full:
                    box2.prop(ob.pose.bones[full["spine"]["handle"]], '["spine"]', text="Chest handle (IK-chest)", slider=True)
                if "look" in full:
                    box2.prop(ob.pose.bones[full["look"]["target"]], '["look"]', text="Look at (LK-target)", slider=True)
            if ob.get("geno_report"):
                box3 = self.layout.box()
                box3.label(text="What this rig has")
                for line in ob["geno_report"].splitlines()[1:]:
                    box3.label(text=line.strip()[:70])
        if s.status:
            self.layout.label(text=s.status[:120], icon="INFO")


CLASSES = (GenoAnimProps, GENO_ANIM_OT_generate, GENO_ANIM_OT_new_clip, GENO_ANIM_OT_load_clip, GENO_ANIM_OT_bake_save,
           GENO_ANIM_OT_delete_clip, GENO_ANIM_OT_snap, GENO_ANIM_OT_space, GENO_ANIM_OT_view_converted, GENO_ANIM_PT_panel)


def register():
    global _REGISTERED
    if _REGISTERED:
        return
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.geno_anim = PointerProperty(type=GenoAnimProps)
    _REGISTERED = True


def unregister():
    global _REGISTERED
    if not _REGISTERED:
        return
    del bpy.types.Scene.geno_anim
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
    _REGISTERED = False
