"""geno_panel.py - a "Geno" tab in the 3D viewport sidebar: Validate, Export, Build + install, role and hit-frame helpers.

Install: Blender > Edit > Preferences > Add-ons > Install from Disk... (or run this file from the Text Editor: Alt+P).
The panel only calls the same functions the command line uses (export_fighter.py, `python -m tools.geno.artist build`), so a result
you get here is the result `build` gives. Set the repo folder (the workspace root) and the fighter.json once; they are saved in the file.
"""
bl_info = {"name": "Geno fighter tools", "author": "GD's Melee", "version": (1, 0, 0), "blender": (4, 2, 0), "location": "3D View > Sidebar > Geno",
           "description": "Validate, export and build a Geno fighter", "category": "Import-Export"}

import json
import os
import subprocess
import sys

import bpy

_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)


def _ef():
    import importlib
    import export_fighter
    importlib.reload(export_fighter)
    return export_fighter


def _text(name, body):
    t = bpy.data.texts.get(name) or bpy.data.texts.new(name)
    t.clear()
    t.write(body)
    return t


class GENO_OT_validate(bpy.types.Operator):
    bl_idname, bl_label, bl_description = "geno.validate", "Validate", "Check the project against the Geno rules (no export)"

    def execute(self, ctx):
        ef = _ef()
        ef.preflight()
        lines = ["%s %s %s: %s%s" % (s, c, w, m, (" | fix: " + f) if f else "") for s, c, w, m, f in ef.OUT]
        _text("Geno Report", "\n".join(lines) or "No findings.")
        nb = sum(1 for o in ef.OUT if o[0] == "BLOCKER")
        self.report({"ERROR" if nb else "INFO"}, "%d blocker(s), %d warning(s): see the Text Editor 'Geno Report'" % (nb, sum(1 for o in ef.OUT if o[0] == "WARNING")))
        return {"FINISHED"}


class GENO_OT_export(bpy.types.Operator):
    bl_idname, bl_label, bl_description = "geno.export", "Export glb", "Preflight, then export the glb and its .geno.json sidecar"

    def execute(self, ctx):
        ef = _ef()
        arm = ef.preflight()
        if any(o[0] == "BLOCKER" for o in ef.OUT) or arm is None:
            _text("Geno Report", "\n".join("%s %s %s: %s | fix: %s" % o for o in ef.OUT))
            self.report({"ERROR"}, "Blockers: nothing exported. See 'Geno Report'.")
            return {"CANCELLED"}
        glb = bpy.path.abspath(ctx.scene.geno_glb)
        clips = ef.do_export(arm, glb)
        self.report({"INFO"}, "Exported %s (%d actions)" % (glb, len(clips)))
        return {"FINISHED"}


class GENO_OT_build(bpy.types.Operator):
    bl_idname, bl_label, bl_description = "geno.build", "Export + Build + Install", "Export, validate, build and install into the isolated test mods folder"

    def execute(self, ctx):
        r = bpy.ops.geno.export()
        if r != {"FINISHED"}:
            return {"CANCELLED"}
        sc = ctx.scene
        cfg = bpy.path.abspath(sc.geno_config)
        env = dict(os.environ)
        p = subprocess.run([sc.geno_python or "python", "-m", "tools.geno.artist", "build", cfg], cwd=bpy.path.abspath(sc.geno_repo), capture_output=True, text=True, env=env)
        _text("Geno Build", p.stdout + p.stderr)
        self.report({"INFO" if p.returncode == 0 else "ERROR"}, "Build %s: see the Text Editor 'Geno Build' (restart the game to see changes)" % ("ok" if p.returncode == 0 else "FAILED"))
        return {"FINISHED"} if p.returncode == 0 else {"CANCELLED"}


class GENO_OT_set_role(bpy.types.Operator):
    bl_idname, bl_label, bl_description = "geno.set_role", "Set role of active bone", "Store the chosen role for the active bone on the armature"
    role: bpy.props.StringProperty(name="Role")

    def execute(self, ctx):
        ef = _ef()
        arm = ctx.object
        if arm is None or arm.type != "ARMATURE" or not arm.data.bones.active:
            self.report({"ERROR"}, "select the armature and an active bone")
            return {"CANCELLED"}
        meta = ef.meta_of(arm)
        meta.setdefault("roles", {})[arm.data.bones.active.name] = self.role or ctx.scene.geno_role
        arm["geno"] = json.dumps(meta)
        return {"FINISHED"}


class GENO_OT_mark_hit(bpy.types.Operator):
    bl_idname, bl_label, bl_description = "geno.mark_hit", "Mark hit frame", "Record the current frame as the strike (first hit) frame of the active action"

    def execute(self, ctx):
        arm = ctx.object
        act = arm.animation_data.action if arm and arm.animation_data else None
        if act is None:
            self.report({"ERROR"}, "no active action")
            return {"CANCELLED"}
        f = int(ctx.scene.frame_current - act.frame_range[0])
        hits = json.loads(act["geno_hit_frames"]) if isinstance(act.get("geno_hit_frames"), str) else []
        hits = sorted(set(hits + [f]))
        act["geno_hit_frames"] = json.dumps(hits)
        self.report({"INFO"}, "%s: hit frames %s" % (act.name, hits))
        return {"FINISHED"}


class GENO_PT_main(bpy.types.Panel):
    bl_label, bl_idname, bl_space_type, bl_region_type, bl_category = "Geno fighter", "GENO_PT_main", "VIEW_3D", "UI", "Geno"

    def draw(self, ctx):
        l, sc = self.layout, ctx.scene
        l.prop(sc, "geno_glb")
        l.prop(sc, "geno_config")
        l.prop(sc, "geno_repo")
        l.prop(sc, "geno_python")
        l.operator("geno.validate", icon="CHECKMARK")
        l.operator("geno.export", icon="EXPORT")
        l.operator("geno.build", icon="PLAY")
        b = l.box()
        b.prop(sc, "geno_role")
        b.operator("geno.set_role").role = ""
        l.operator("geno.mark_hit", icon="MARKER")


CLASSES = (GENO_OT_validate, GENO_OT_export, GENO_OT_build, GENO_OT_set_role, GENO_OT_mark_hit, GENO_PT_main)


def register():
    S = bpy.types.Scene
    S.geno_glb = bpy.props.StringProperty(name="glb", subtype="FILE_PATH", default="//art/fighter.glb")
    S.geno_config = bpy.props.StringProperty(name="fighter.json", subtype="FILE_PATH", default="//fighter.json")
    S.geno_repo = bpy.props.StringProperty(name="Repo folder", subtype="DIR_PATH", default="")
    S.geno_python = bpy.props.StringProperty(name="Python", default="python")
    S.geno_role = bpy.props.StringProperty(name="Role", default="hips")
    for c in CLASSES:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(CLASSES):
        bpy.utils.unregister_class(c)
    for n in ("geno_glb", "geno_config", "geno_repo", "geno_python", "geno_role"):
        delattr(bpy.types.Scene, n)


if __name__ == "__main__":
    register()
