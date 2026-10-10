"""Independent play operators. Argument helpers import without Blender."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace

if __package__:
    from .props import NO_ROW, STRINGS
else:
    from props import NO_ROW, STRINGS

for _key, _text in {
    "play_panel": "Playtest",
    "play_lab": "Play in LAB",
    "play_cpu": "Play vs CPU",
    "play_project_required": "Choose a project in Connect before playing.",
    "play_rebuild": "Rebuild gameplay first",
    "play_stale": "Package is stale. Rebuild gameplay before play.",
    "play_starting": "Opening game; the result and log path appear here.",
    "play_launch_started": "Game launch started. Log: {path}",
    "play_failed": "Play failed: {error}",
    "play_helper_missing": "Play helper is missing: {path}",
    "play_workspace_missing": "Cannot find tools/geno/play.py. Choose a project inside its workspace or set GW_ROOT.",
    "play_python_missing": "Python not found: set GW_PYTHON or add Python to PATH.",
    "play_rebuild_unavailable": "Package is stale and the project has no gameplay rebuild configured.",
    "play_description": "Open the built fighter in a real-time game window; offer a gameplay rebuild when stale",
}.items():
    STRINGS.setdefault(_key, _text)

_JOBS = []
_CLASSES = []
_TIMER = False


def _play_script(project, env=None):
    env = os.environ if env is None else env
    source = Path(project).expanduser().resolve()
    start = source.parent if source.is_file() else source
    for directory in (start, *start.parents):
        if (directory / ".git").exists():
            script = directory / "tools/geno/play.py"
            if script.is_file():
                return script
            raise ValueError(STRINGS["play_helper_missing"].format(path=script))
    candidates = []
    if env.get("GW_ROOT", "").strip():
        candidates.append(Path(env["GW_ROOT"]).expanduser().resolve())
    candidates.append(Path(__file__).resolve().parents[3])
    for workspace in candidates:
        script = workspace / "tools/geno/play.py"
        if script.is_file():
            return script
    raise ValueError(STRINGS["play_workspace_missing"])


def _play_resolver(script):
    # A copied add-on can switch worktrees in one Blender process. Keep resolver
    # modules isolated by file so an earlier tools.geno import cannot pick the code.
    name = "_geno_wb_play_" + hashlib.sha256(str(script).encode()).hexdigest()[:16]
    module = sys.modules.get(name)
    if module is None:
        spec = importlib.util.spec_from_file_location(name, script)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module  # dataclasses reads its defining module
        try:
            spec.loader.exec_module(module)
        except Exception:
            sys.modules.pop(name, None)
            raise
    return module


def play_arguments(settings, mode, *, rebuild=False):
    """One argv shared by both operators. No shell quoting or display-label IDs."""
    args = [str(_play_script(settings.project)),
            "--project", settings.project]
    if mode == "vs":
        args.extend(("--vs", "cpu"))
    else:
        args.append("--lab")
        row = getattr(settings, "move", "")
        if not row or row == NO_ROW:
            row = getattr(settings, "row", "")
        if row and row != NO_ROW:
            args.extend(("--clip", row))
    args.append("--json")
    for name, option in (("engine_exe", "--engine-exe"), ("mods_dir", "--mods-dir"), ("iso", "--iso")):
        value = getattr(settings, name, "")
        if value:
            args.extend((option, value))
    if rebuild:
        args.append("--rebuild")
    return args


def _scene_settings(main, abspath):
    fields = {}
    for name, scene_name in (("project", "project"), ("engine_exe", "engine_exe"),
                             ("mods_dir", "mods_dir"), ("iso", "iso_path")):
        raw = getattr(main, scene_name, "").strip()
        fields[name] = abspath(raw) if raw else ""
    if not fields["project"]:
        raise ValueError(STRINGS["play_project_required"])
    fields.update(move=getattr(main, "move", ""), row=getattr(main, "row", ""))
    return SimpleNamespace(**fields)


def _settings(context):
    import bpy
    return _scene_settings(context.scene.geno_wb, bpy.path.abspath)


def _plan(context, mode):
    settings = _settings(context)
    resolver = _play_resolver(_play_script(settings.project))
    row = settings.move if settings.move and settings.move != NO_ROW else settings.row
    return resolver.resolve_project(settings.project, mode=mode, clip=row or None,
                           engine_exe=settings.engine_exe or None,
                           mods_dir=settings.mods_dir or None, iso=settings.iso or None)


def _status(settings, message):
    try:
        settings.status = message
    except (ReferenceError, RuntimeError):
        pass
    print("Geno Workbench: " + message)


def _poll_jobs():
    global _TIMER
    for process, output, settings in tuple(_JOBS):
        if process.poll() is None:
            continue
        output.seek(0)
        raw = output.read().decode("utf-8", errors="replace").strip()
        output.close()
        _JOBS.remove((process, output, settings))
        try:
            value = json.loads(raw)
            if process.returncode or not value.get("ok"):
                raise ValueError(value.get("error") or raw[-2000:])
            message = STRINGS["play_launch_started"].format(path=value["log_path"])
        except (ValueError, KeyError, TypeError) as exc:
            message = STRINGS["play_failed"].format(error=exc)
        _status(settings, message)
    if not _JOBS:
        _TIMER = False
        return None
    return 0.1


class _PlayOperator:
    mode = "lab"

    @classmethod
    def poll(cls, context):
        settings = getattr(getattr(context, "scene", None), "geno_wb", None)
        ready = settings is not None and bool(settings.project.strip())
        if not ready:
            cls.poll_message_set(STRINGS["play_project_required"])
        elif _JOBS:
            cls.poll_message_set(STRINGS["play_starting"])
        return ready and not _JOBS

    def invoke(self, context, event):
        try:
            plan = _plan(context, self.mode)
            if plan.stale:
                if not plan.rebuild_argv:
                    raise ValueError(STRINGS["play_rebuild_unavailable"])
                self.rebuild = True
                self._stale = plan.stale
                return context.window_manager.invoke_props_dialog(self, width=440)
            return self.execute(context)
        except (ValueError, OSError) as exc:
            message = STRINGS["play_failed"].format(error=exc)
            context.scene.geno_wb.status = message
            self.report({"ERROR"}, message)
            return {"CANCELLED"}

    def draw(self, context):
        self.layout.label(text=STRINGS["play_stale"], icon="ERROR")
        self.layout.prop(self, "rebuild")
        for reason in getattr(self, "_stale", ())[:3]:
            self.layout.label(text=reason)

    def execute(self, context):
        global _TIMER
        import bpy
        try:
            plan = _plan(context, self.mode)
            if plan.stale and not self.rebuild:
                raise ValueError(STRINGS["play_stale"])
            python = os.environ.get("GW_PYTHON", "").strip()
            if not python:
                python = shutil.which("python") or shutil.which("python3")
            if not python:
                raise ValueError(STRINGS["play_python_missing"])
            args = play_arguments(_settings(context), self.mode, rebuild=bool(self.rebuild))
            # A file cannot fill a pipe while Blender is busy; no long build blocks its UI.
            output = tempfile.TemporaryFile()
            try:
                process = subprocess.Popen([python, *args], cwd=plan.workspace,
                    stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
                    **({"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}))
            except Exception:
                output.close()
                raise
            _JOBS.append((process, output, context.scene.geno_wb))
            if not _TIMER:
                bpy.app.timers.register(_poll_jobs, first_interval=0.1)
                _TIMER = True
            context.scene.geno_wb.status = STRINGS["play_starting"]
            return {"FINISHED"}
        except (ValueError, OSError) as exc:
            message = STRINGS["play_failed"].format(error=exc)
            context.scene.geno_wb.status = message
            self.report({"ERROR"}, message)
            return {"CANCELLED"}


def register():
    import bpy
    from bpy.props import BoolProperty
    if _CLASSES:
        return

    class GENO_WB_OT_play_lab(_PlayOperator, bpy.types.Operator):
        bl_idname = "geno_wb.play_lab"
        bl_label = STRINGS["play_lab"]
        bl_description = STRINGS["play_description"]
        rebuild: BoolProperty(name=STRINGS["play_rebuild"], default=False, options={"SKIP_SAVE"})

    class GENO_WB_OT_play_cpu(_PlayOperator, bpy.types.Operator):
        bl_idname = "geno_wb.play_cpu"
        bl_label = STRINGS["play_cpu"]
        bl_description = STRINGS["play_description"]
        mode = "vs"
        rebuild: BoolProperty(name=STRINGS["play_rebuild"], default=False, options={"SKIP_SAVE"})

    try:
        guard = importlib.import_module((__package__ + "." if __package__ else "") + "props").guard_busy
        guard((GENO_WB_OT_play_lab, GENO_WB_OT_play_cpu))   # not while a rebuild is rewriting the package
        for cls in (GENO_WB_OT_play_lab, GENO_WB_OT_play_cpu):
            bpy.utils.register_class(cls)
            _CLASSES.append(cls)
    except Exception:
        unregister()
        raise


def unregister():
    import bpy
    # Let any accepted build/launch finish; its subprocess is independent of the panel.
    for cls in reversed(tuple(_CLASSES)):
        bpy.utils.unregister_class(cls)
        _CLASSES.remove(cls)
