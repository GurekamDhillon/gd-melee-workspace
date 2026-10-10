"""Splice sidebar operators; independent of a running workbench server."""
import json
from pathlib import Path
import sys

import bpy

try:
    from . import api, nla, props
except ImportError:
    import api
    import nla
    import props

STRINGS = props.STRINGS
_recipe_cache = {}
_recipe_strings = {}
NO_RECIPE = "__GENO_WB_NO_RECIPE__"


def project_path(settings):
    if not settings.project:
        raise ValueError(STRINGS["project_required"])
    project = Path(bpy.path.abspath(settings.project)).expanduser().resolve()
    if not project.is_dir():
        raise ValueError(STRINGS["invalid_project"].format(path=project))
    return project


def recipe_path(settings):
    return Path(bpy.path.abspath(settings.nla_recipe_file)).expanduser().resolve() if settings.nla_recipe_file else project_path(settings) / "splices.json"


def recipes(settings):
    path = recipe_path(settings)
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc.get("schema") != "goku-splices/1" or not isinstance(doc.get("recipes"), dict):
        raise ValueError(STRINGS["nla_recipe_file_error"])
    return doc["recipes"]


def recipe_items(settings, context=None):
    empty = [(NO_RECIPE, STRINGS["nla_choose_recipe"], STRINGS["nla_recipe_help"], 0)]
    try:
        path = recipe_path(settings)
        stat = path.stat()
        key = str(path), stat.st_mtime_ns, stat.st_size
        if key not in _recipe_cache:
            items = list(empty)
            for index, (name, recipe) in enumerate(recipes(settings).items(), 1):
                label = name + (STRINGS["nla_example_suffix"] if recipe.get("example") else "")
                note = recipe.get("note") or STRINGS["nla_recipe_help"]
                texts = [_recipe_strings.setdefault(s, s) for s in (name, label, str(note))]
                items.append((*texts, index))
            _recipe_cache.clear()
            _recipe_cache[key] = items
        return _recipe_cache[key]
    except (OSError, ValueError, TypeError, AttributeError):
        return empty


def _perform(operator, context, fn):
    try:
        from . import operators
    except ImportError:
        import operators
    operators.stop_playback()
    operators._cancel_scrub()
    try:
        message = fn(context.object, context.scene.geno_wb)
    except (Exception, SystemExit) as exc:
        api.session().report_error(exc)
        operator.report({"ERROR"}, str(exc))
        return {"CANCELLED"}
    api.session().set_status(message)
    operator.report({"INFO"}, message)
    return {"FINISHED"}


class _SpliceOperator:
    @classmethod
    def poll(cls, context):
        return context.object is not None and context.object.type == "ARMATURE" and context.mode == "OBJECT"


class GENO_WB_OT_import_clip(_SpliceOperator, bpy.types.Operator):
    bl_idname = "geno_wb.import_clip"
    bl_label = STRINGS["nla_import"]
    bl_description = STRINGS["nla_import_help"]
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        def run(arm, settings):
            reference = settings.nla_clip.strip()
            if not reference:
                raise ValueError(STRINGS["nla_clip_required"])
            action = nla.import_clip(arm, project_path(settings), reference, settings.nla_height)
            return STRINGS["nla_imported"].format(name=action.name)
        return _perform(self, context, run)


class GENO_WB_OT_layout_recipe(_SpliceOperator, bpy.types.Operator):
    bl_idname = "geno_wb.layout_recipe"
    bl_label = STRINGS["nla_layout"]
    bl_description = STRINGS["nla_layout_help"]
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        def run(arm, settings):
            choices = recipes(settings)
            name = settings.nla_recipe
            if name not in choices:
                raise ValueError(STRINGS["nla_choose_recipe"])
            track = nla.lay_out_recipe(arm, name, choices[name], project=project_path(settings), height=settings.nla_height)
            if not settings.nla_action_name:
                settings.nla_action_name = choices[name].get("row") or name
            return STRINGS["nla_laid_out"].format(name=track.name)
        return _perform(self, context, run)


class GENO_WB_OT_save_strips(_SpliceOperator, bpy.types.Operator):
    bl_idname = "geno_wb.save_strips"
    bl_label = STRINGS["nla_save"]
    bl_description = STRINGS["nla_save_help"]

    def execute(self, context):
        def run(arm, settings):
            track = nla.current_track(arm)
            meta = nla._metadata(arm)[track.name]
            path, name = nla.save_recipe(project_path(settings), meta["name"], nla.read_recipe(arm, track))
            return STRINGS["nla_saved"].format(name=name, path=path)
        return _perform(self, context, run)


class GENO_WB_OT_bake_export(_SpliceOperator, bpy.types.Operator):
    bl_idname = "geno_wb.bake_export"
    bl_label = STRINGS["nla_bake_export"]
    bl_description = STRINGS["nla_bake_export_help"]

    def execute(self, context):
        def run(arm, settings):
            if not settings.nla_export_path:
                raise ValueError(STRINGS["nla_export_required"])
            # An installed add-on may live outside the repo. The source tools
            # also set their own workspace path when project clips are loaded.
            workspace = Path(__file__).resolve().parents[3]
            if (workspace / "tools/geno/artist").is_dir() and str(workspace) not in sys.path:
                sys.path.insert(0, str(workspace))
            glb = bpy.path.abspath(settings.nla_export_path)
            action = nla.bake_and_export(arm, glb, name=settings.nla_action_name.strip() or None)
            return STRINGS["nla_exported"].format(name=action.name, path=glb)
        return _perform(self, context, run)


CLASSES = (GENO_WB_OT_import_clip, GENO_WB_OT_layout_recipe,
           GENO_WB_OT_save_strips, GENO_WB_OT_bake_export)
