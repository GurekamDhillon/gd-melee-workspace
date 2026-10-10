"""Small independent UI-render panel. No changes to panels.py or Hitbox."""
import os
from pathlib import Path
import subprocess
import uuid

import bpy

from . import api, ui_command
from .props import STRINGS

for _key, _value in {
    'ui_panel': 'UI Art', 'ui_render': 'Render UI',
    'ui_render_help': 'Render this fighter through portable Blender 3.5.1 and install package UI art',
    'ui_python': 'Host Python', 'ui_costume': 'Costume', 'ui_pose': 'Pose override',
    'ui_pose_help': 'Optional row:frame; empty uses the selected Workbench move and frame',
    'ui_costume_help': 'all or a zero-based costume number',
    'ui_started': 'Rendering UI; log: {path}', 'ui_finished': 'UI rendered; log: {path}',
    'ui_failed': 'UI render failed ({code}); log: {path}',
    'ui_busy': 'A UI render is already running', 'ui_cancel': 'Stop UI render',
    'ui_cancelling': 'Stopping UI render',
}.items():
    STRINGS.setdefault(_key, _value)

_PROCESS = None
_LOG = None
_LOG_PATH = None
_CANCEL = None
_ROOT = None
_OWNER = None
_CLASSES = []


class GenoUIProps(bpy.types.PropertyGroup):
    python: bpy.props.StringProperty(name=STRINGS['ui_python'], subtype='FILE_PATH')
    costume: bpy.props.StringProperty(name=STRINGS['ui_costume'], description=STRINGS['ui_costume_help'], default='all')
    pose: bpy.props.StringProperty(name=STRINGS['ui_pose'], description=STRINGS['ui_pose_help'])
    status: bpy.props.StringProperty(options={'SKIP_SAVE'})


def _redraw():
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


def _poll():
    global _PROCESS, _LOG, _OWNER
    if _PROCESS is None:
        return None
    code = _PROCESS.poll()
    if code is None:
        return 0.25
    if _LOG is not None:
        _LOG.close()
        _LOG = None
    if _OWNER is not None and hasattr(_OWNER, 'geno_wb_ui'):
        key = 'ui_finished' if code == 0 else 'ui_failed'
        _OWNER.geno_wb_ui.status = STRINGS[key].format(code=code, path=_LOG_PATH)
    _PROCESS, _OWNER = None, None
    _redraw()
    return None


class GENO_WB_OT_render_ui(bpy.types.Operator):
    bl_idname = 'geno_wb.render_ui'
    bl_label = STRINGS['ui_render']
    bl_description = STRINGS['ui_render_help']

    def execute(self, context):
        global _PROCESS, _LOG, _LOG_PATH, _CANCEL, _ROOT, _OWNER
        if _PROCESS is not None:
            self.report({'ERROR'}, STRINGS['ui_busy'])
            return {'CANCELLED'}
        props, ui = context.scene.geno_wb, context.scene.geno_wb_ui
        try:
            project = Path(bpy.path.abspath(props.project)).expanduser().resolve()
            root = ui_command.workspace_for(project)
            _ROOT = root
            work = ui_command.generated_path(root, 'workbench')
            work.mkdir(parents=True, exist_ok=True)
            token = uuid.uuid4().hex
            _LOG_PATH = ui_command.generated_path(root, work / (token + '.log'))
            _CANCEL = ui_command.generated_path(root, work / (token + '.cancel'))
            session = api.session()
            command = ui_command.render_command(
                project, root=root, row=session.loaded_row or props.row or session.row or 'Wait',
                frame=props.frame, costume=ui.costume, pose=ui.pose or None,
                art=bpy.path.abspath(props.blender_art) if props.blender_art else '',
                python=bpy.path.abspath(ui.python) if ui.python else None, cancel_file=_CANCEL,
            )
            _LOG = _LOG_PATH.open('w', encoding='utf-8')
            _PROCESS = subprocess.Popen(command, cwd=root, env=dict(os.environ, GW_ROOT=str(root)),
                                        stdout=_LOG, stderr=subprocess.STDOUT,
                                        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            _OWNER = context.scene
            ui.status = STRINGS['ui_started'].format(path=_LOG_PATH)
            bpy.app.timers.register(_poll, first_interval=0.25)
            return {'FINISHED'}
        except Exception as exc:
            if _LOG is not None:
                _LOG.close()
                _LOG = None
            ui.status = str(exc)
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}


class GENO_WB_OT_cancel_ui(bpy.types.Operator):
    bl_idname = 'geno_wb.cancel_ui'
    bl_label = STRINGS['ui_cancel']

    def execute(self, context):
        if _PROCESS is not None and _CANCEL is not None:
            ui_command.generated_path(_ROOT, _CANCEL).touch()
            context.scene.geno_wb_ui.status = STRINGS['ui_cancelling']
        return {'FINISHED'}


class GENO_WB_PT_ui(bpy.types.Panel):
    bl_idname = 'GENO_WB_PT_ui'
    bl_label = STRINGS['ui_panel']
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Geno'
    bl_order = 25

    def draw(self, context):
        ui = context.scene.geno_wb_ui
        layout = self.layout
        layout.prop(ui, 'python')
        layout.prop(ui, 'costume')
        layout.prop(ui, 'pose')
        row = layout.row()
        row.enabled = _PROCESS is None
        row.operator('geno_wb.render_ui', icon='RENDER_STILL')
        if _PROCESS is not None:
            layout.operator('geno_wb.cancel_ui', icon='CANCEL')
        if ui.status:
            layout.label(text=ui.status, icon='INFO')


def register():
    if _CLASSES:
        return
    if hasattr(bpy.types.Scene, 'geno_wb_ui'):
        raise RuntimeError('Scene.geno_wb_ui is already registered')
    try:
        for cls in (GenoUIProps, GENO_WB_OT_render_ui, GENO_WB_OT_cancel_ui, GENO_WB_PT_ui):
            bpy.utils.register_class(cls)
            _CLASSES.append(cls)
        bpy.types.Scene.geno_wb_ui = bpy.props.PointerProperty(type=GenoUIProps)
    except Exception:
        unregister()
        raise


def unregister():
    global _PROCESS, _LOG, _OWNER
    if _PROCESS is not None and _PROCESS.poll() is None:
        ui_command.generated_path(_ROOT, _CANCEL).touch()
        # The host polls this file and stops only its own Blender child. Avoid
        # terminating the host first, which would orphan the renderer.
        try:
            _PROCESS.wait(timeout=10)
        except subprocess.TimeoutExpired:
            print('Geno UI render is still stopping; log:', _LOG_PATH)
    if bpy.app.timers.is_registered(_poll):
        bpy.app.timers.unregister(_poll)
    if _LOG is not None:
        _LOG.close()
        _LOG = None
    _PROCESS, _OWNER = None, None
    if hasattr(bpy.types.Scene, 'geno_wb_ui'):
        del bpy.types.Scene.geno_wb_ui
    for cls in reversed(tuple(_CLASSES)):
        bpy.utils.unregister_class(cls)
        _CLASSES.remove(cls)
