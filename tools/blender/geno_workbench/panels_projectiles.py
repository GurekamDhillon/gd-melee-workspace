"""Geno > Projectiles: the fighter's articles as Blender objects, spawn markers and the ghost path.

Operators go through the session's edit_article / edit_spawn commands (the Workbench write path); nothing here
touches source files.  Rebuild + reload (Timeline/Hitbox panels) applies the change to the engine.
"""
import bpy
from bpy.props import BoolProperty

from . import api, projectiles as P, projectiles_bpy as PB
from .props import STRINGS

_CLASSES = []
_HOOK = {"on": False}


def _row(sess):
    return sess.loaded_row or sess.source_row


def refresh_ghost(sess, scene=None):
    scene = scene or bpy.context.scene
    if not scene.get("geno_proj_ghost", True) or not sess.articles:
        return []
    return PB.update_ghost(sess.articles, sess.spawns, _row(sess), int(sess.frame or 0), scene,
                           facing=int(getattr(sess, "facing", 1) or 1))


def _on_frame(sess):
    refresh_ghost(sess)


class GENO_WB_OT_proj_import(bpy.types.Operator):
    bl_idname = "geno_wb.proj_import"
    bl_label = "Load projectiles"
    bl_description = "Read the fighter's articles and spawn calls from the source and build the Projectiles collection"

    def execute(self, context):
        sess = api.session()
        if not sess.refresh_projectiles():
            self.report({"ERROR"}, sess.last_error or sess.status)
            return {"CANCELLED"}
        PB.import_articles(sess.articles, context.scene)
        context.scene["geno_proj_ghost"] = context.scene.get("geno_proj_ghost", True)
        PB.sync_markers(sess.spawns, sess.articles, _row(sess), context.scene)
        refresh_ghost(sess, context.scene)
        self.report({"INFO"}, sess.status)
        return {"FINISHED"}


class GENO_WB_OT_proj_apply(bpy.types.Operator):
    bl_idname = "geno_wb.proj_apply"
    bl_label = "Apply to source"
    bl_description = "Write the edited projectiles and dragged spawn markers to the source (then Rebuild + reload)"

    def execute(self, context):
        sess = api.session()
        plan = PB.pending_ops(sess.articles, context.scene)
        done = 0
        for index, ops in sorted(plan["edits"].items()):
            if not sess.edit_article(index, ops):
                self.report({"ERROR"}, sess.last_error or sess.status)
                return {"CANCELLED"}
            done += 1
        for art in plan["new"]:
            if not sess.add_article(art):
                self.report({"ERROR"}, sess.last_error or sess.status)
                return {"CANCELLED"}
            done += 1
        for edit in PB.marker_edits(context.scene):
            if not sess.edit_spawn(edit["row"], edit["ordinal"], frame=edit["frame"]):
                self.report({"ERROR"}, sess.last_error or sess.status)
                return {"CANCELLED"}
            done += 1
        PB.mark_synced(sess.articles, context.scene)
        PB.sync_markers(sess.spawns, sess.articles, _row(sess), context.scene)
        refresh_ghost(sess, context.scene)
        self.report({"INFO"}, "%d change(s) written; rebuild + reload to use them" % done if done else "nothing changed")
        return {"FINISHED"}


class GENO_WB_OT_proj_add(bpy.types.Operator):
    bl_idname = "geno_wb.proj_add"
    bl_label = "New projectile"
    bl_description = "Add a projectile object; Apply sends it as a new article"

    def execute(self, context):
        PB.add_projectile("NewProjectile%d" % (len(PB.roots(context.scene)) + 1), context.scene)
        return {"FINISHED"}


class GENO_WB_OT_proj_add_spawn(bpy.types.Operator):
    bl_idname = "geno_wb.proj_add_spawn"
    bl_label = "Spawn at this frame"
    bl_description = "Add a CALL geno.article.spawn for the selected projectile at the shown frame of the loaded move"

    def execute(self, context):
        sess = api.session()
        obj = context.active_object
        while obj is not None and obj.parent is not None:
            obj = obj.parent
        if obj is None or PB.SRC not in obj or obj.get(PB.INDEX, -1) < 0:
            self.report({"ERROR"}, "Select an applied projectile first")
            return {"CANCELLED"}
        if not sess.add_spawn(_row(sess), int(sess.frame or 0), int(obj[PB.INDEX])):
            self.report({"ERROR"}, sess.last_error or sess.status)
            return {"CANCELLED"}
        PB.sync_markers(sess.spawns, sess.articles, _row(sess), context.scene)
        refresh_ghost(sess, context.scene)
        return {"FINISHED"}


class GENO_WB_OT_proj_ghost(bpy.types.Operator):
    bl_idname = "geno_wb.proj_ghost"
    bl_label = "Refresh ghost"
    bl_description = "Redraw the projectile paths for the shown frame"

    def execute(self, context):
        refresh_ghost(api.session(), context.scene)
        return {"FINISHED"}


class GENO_WB_PT_projectiles(bpy.types.Panel):
    bl_idname = "GENO_WB_PT_projectiles"
    bl_label = "Projectiles"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = STRINGS["tab"]
    bl_order = 22

    @classmethod
    def poll(cls, context):
        return context.scene is not None and hasattr(context.scene, "geno_wb")

    def draw(self, context):
        sess = api.session()
        lay = self.layout
        row = lay.row(align=True)
        row.operator("geno_wb.proj_import", icon="IMPORT")
        row.operator("geno_wb.proj_apply", icon="EXPORT")
        row = lay.row(align=True)
        row.operator("geno_wb.proj_add", icon="ADD")
        row.operator("geno_wb.proj_add_spawn", icon="MARKER")
        lay.prop(context.scene, '["geno_proj_ghost"]', text="Ghost path") if "geno_proj_ghost" in context.scene else None
        for r in PB.roots(context.scene):
            sel = r == context.active_object or (context.active_object is not None and context.active_object.parent == r)
            box = lay.box() if sel else lay
            line = box.row()
            line.label(text=P.summary(PB.export_article(r)), icon="MESH_UVSPHERE")
            if not sel:
                continue
            col = box.column(align=True)
            for path, _, kind in P.FIELDS:
                if path in PB.TRANSFORM_FIELDS or path in ("name",):
                    continue
                col.prop(r, '["%s"]' % PB._key("gp_", path), text=path)
            col.label(text="spawn: object location (X forward, Z up)")
        active = context.active_object
        if active is not None and PB.HB_SRC in active:
            box = lay.box()
            box.label(text="Hitbox (size = scale, offset = location)")
            col = box.column(align=True)
            for path, _, kind in P.HITBOX_FIELDS:
                if path in PB.TRANSFORM_HB:
                    continue
                col.prop(active, '["%s"]' % PB._key("gh_", path), text=path)
        spawns = [s for s in sess.spawns if s.get("row") == _row(sess)]
        if spawns:
            box = lay.box()
            box.label(text="Spawns in %s (drag the timeline markers)" % _row(sess))
            for s in spawns:
                name = sess.articles[s["article"]]["name"] if 0 <= s.get("article", -1) < len(sess.articles) else "?"
                box.label(text="f%d  %s" % (s["frame"], name))
        if sess.stale:
            lay.label(text="Source edited: Rebuild + reload to apply", icon="INFO")


def register():
    if _CLASSES:
        return
    for cls in (GENO_WB_OT_proj_import, GENO_WB_OT_proj_apply, GENO_WB_OT_proj_add, GENO_WB_OT_proj_add_spawn,
                GENO_WB_OT_proj_ghost, GENO_WB_PT_projectiles):
        bpy.utils.register_class(cls)
        _CLASSES.append(cls)
    sess = api.session()
    if _on_frame not in sess.on_frame:
        sess.on_frame.append(_on_frame)
        _HOOK["on"] = True


def unregister():
    sess = api.session()
    if _on_frame in sess.on_frame:
        sess.on_frame.remove(_on_frame)
    _HOOK["on"] = False
    for cls in reversed(tuple(_CLASSES)):
        bpy.utils.unregister_class(cls)
        _CLASSES.remove(cls)
