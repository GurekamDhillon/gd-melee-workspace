"""Plain Blender properties, operators and sidebar panel."""
import bpy
from .core import export_document, validate
from .scene import collect_scene, default_kit
from .console import reload_mission
from .assets import asset_warnings, estimate_asset_memory
from .authoring import CAMERA_KEYS


class GDSettings(bpy.types.PropertyGroup):
    mission_name: bpy.props.StringProperty(name='Mission name', default='mission')
    output: bpy.props.StringProperty(name='Output mod folder', subtype='DIR_PATH')
    kit: bpy.props.StringProperty(name='Kit models folder', subtype='DIR_PATH', default=str(default_kit()))


class GDValidate(bpy.types.Operator):
    bl_idname = 'gd_mission.validate'
    bl_label = 'Validate'
    def execute(self, context):
        settings = context.scene.gd_mission
        try:
            doc = collect_scene(context.scene, bpy.path.abspath(settings.kit))
            errors = validate(doc)
            for warning in asset_warnings(doc): self.report({'WARNING'}, warning)
            if errors:
                for error in errors: self.report({'ERROR'}, error)
                return {'CANCELLED'}
            self.report({'INFO'}, f'Mission is valid; estimated pinned assets {estimate_asset_memory(doc)/1048576:.2f} MiB')
            return {'FINISHED'}
        except (ValueError, OSError, TypeError) as exc:
            self.report({'ERROR'}, str(exc)); return {'CANCELLED'}


class GDExport(bpy.types.Operator):
    bl_idname = 'gd_mission.export'
    bl_label = 'Export'
    send: bpy.props.BoolProperty(default=False)
    def execute(self, context):
        settings = context.scene.gd_mission
        if not settings.output:
            self.report({'ERROR'}, 'Choose an output mod folder'); return {'CANCELLED'}
        try:
            doc = collect_scene(context.scene, bpy.path.abspath(settings.kit))
            for warning in asset_warnings(doc): self.report({'WARNING'}, warning)
            out = export_document(doc, bpy.path.abspath(settings.output), settings.mission_name)
            self.report({'INFO'}, 'Exported ' + str(out))
            if self.send:
                ok, message = reload_mission()
                self.report({'INFO'} if ok else {'WARNING'}, message)
            return {'FINISHED'}
        except (ValueError, OSError, TypeError) as exc:
            self.report({'ERROR'}, str(exc)); return {'CANCELLED'}


class GDCamera(bpy.types.Operator):
    bl_idname = 'gd_mission.camera'
    bl_label = 'Set camera properties'
    bl_options = {'REGISTER', 'UNDO'}
    chunk: bpy.props.BoolProperty(default=False)
    clear: bpy.props.BoolProperty(default=False)
    def execute(self, context):
        owner = context.object if self.chunk else context.scene
        if owner is None or (self.chunk and 'gd_chunk' not in owner): return {'CANCELLED'}
        defaults = dict(mode='chunk' if self.chunk else 'follow', window_w=250.0,
                        window_h=180.0, min_dist=300.0, fov=30.0)
        for key in CAMERA_KEYS:
            prop = 'gd_camera_' + key
            if self.clear:
                if prop in owner: del owner[prop]
            elif prop not in owner: owner[prop] = defaults[key]
        return {'FINISHED'}


class GDPanel(bpy.types.Panel):
    bl_label = 'GD Mission'
    bl_idname = 'GD_MISSION_PT_export'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'GD Mission'
    def draw(self, context):
        layout = self.layout; settings = context.scene.gd_mission
        for field in ('mission_name', 'output', 'kit'): layout.prop(settings, field)
        owners = [(context.scene, 'Level camera', False)]
        if context.object is not None and 'gd_chunk' in context.object:
            owners.append((context.object, 'Selected chunk camera override', True))
        labels = dict(mode='Mode (follow / chunk / shaft)', window_w='Window width (game units)',
                      window_h='Window height (game units)', min_dist='Minimum distance', fov='FOV (degrees)')
        for owner, title, chunk in owners:
            box = layout.box(); box.label(text=title)
            for key in CAMERA_KEYS:
                if 'gd_camera_' + key in owner:
                    box.prop(owner, '["gd_camera_' + key + '"]', text=labels[key])
            op = box.operator('gd_mission.camera', text='Add camera fields'); op.chunk = chunk
            op = box.operator('gd_mission.camera', text='Use runtime defaults'); op.chunk = chunk; op.clear = True
        layout.operator('gd_mission.validate')
        layout.operator('gd_mission.export')
        layout.operator('gd_mission.export', text='Export and send').send = True


CLASSES = (GDSettings, GDValidate, GDExport, GDCamera, GDPanel)


def register():
    for cls in CLASSES: bpy.utils.register_class(cls)
    bpy.types.Scene.gd_mission = bpy.props.PointerProperty(type=GDSettings)


def unregister():
    del bpy.types.Scene.gd_mission
    for cls in reversed(CLASSES): bpy.utils.unregister_class(cls)
