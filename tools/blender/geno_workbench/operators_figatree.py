"""File-browser operator over the headless-testable figatree importer."""
import json
from pathlib import Path

import bpy
from bpy.props import FloatProperty, StringProperty

try:
    from . import api, figatree_decode as D, props, rigmap
except ImportError:
    import api
    import figatree_decode as D
    import props
    import rigmap


class GENO_WB_OT_import_figatree(bpy.types.Operator):
    bl_idname = "geno_wb.import_figatree"
    bl_label = "Import fighter animations"
    bl_description = "Import a local AJ bank as editable actions on the matching deform rig; frame 1 is the first move frame"
    bl_options = {"REGISTER", "UNDO"}
    filename_ext = ".dat"
    filepath: StringProperty(name="Animation bank", subtype="FILE_PATH")
    filter_glob: StringProperty(default="*.dat", options={"HIDDEN"})
    plan_path: StringProperty(name="Joint plan", description="Matching plan.json; uses the project's art.bone_aliases", subtype="FILE_PATH")
    model_path: StringProperty(name="Costume model", description="Matching costume DAT containing the rest joint tree", subtype="FILE_PATH")
    model_symbol: StringProperty(name="Model joint symbol", description="Leave empty for a costume with one public _joint root")
    tolerance: FloatProperty(name="Pose tolerance", default=1e-4, min=1e-6, max=.1, precision=6)

    @classmethod
    def poll(cls, context):
        return props.poll_ready(cls,
            (context.object is not None and context.object.type == "ARMATURE", "Select the fighter's deform armature"),
            (context.mode == "OBJECT", "Switch to Object Mode to import animations"))

    def invoke(self, context, event):
        if not self.plan_path:
            self.plan_path = api.session().plan_path
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def execute(self, context):
        try:
            try:
                from .figatree_actions import create_actions
            except ImportError:
                from figatree_actions import create_actions
            if not self.plan_path or not self.model_path:
                raise D.FigatreeError("choose a Joint plan and its Costume model in the import options")
            plan = rigmap.load_plan(bpy.path.abspath(self.plan_path))
            clips = D.read_bank(Path(bpy.path.abspath(self.filepath)).read_bytes(), plan.get("bank"))
            rest = D.read_model(Path(bpy.path.abspath(self.model_path)).read_bytes(), self.model_symbol)
            settings = getattr(context.scene, "geno_wb", None)
            project = getattr(settings, "project", "")
            aliases = api.session().bone_aliases
            if project:
                config_path = Path(bpy.path.abspath(project)) / "workbench.json"
                if config_path.is_file():
                    config = json.loads(config_path.read_text(encoding="utf-8"))
                    aliases = config.get("art", {}).get("bone_aliases", {})
            if not isinstance(aliases, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in aliases.items()):
                raise D.FigatreeError("art.bone_aliases must map joint names to bone names")
            actions = create_actions(context.object, clips, rest, plan, aliases, self.tolerance)
        except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}
        message = f"Imported {len(actions)} fighter actions; choose an action in the Action Editor (first frame: 1)"
        api.session().set_status(message)
        self.report({"INFO"}, message)
        return {"FINISHED"}


CLASSES = (GENO_WB_OT_import_figatree,)
