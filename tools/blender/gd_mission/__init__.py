"""GD Mission Blender add-on; pure modules remain importable without Blender."""
bl_info = dict(name='GD Mission exporter', author='GD', version=(1, 0, 0),
               blender=(4, 0, 0), location='View3D > Sidebar > GD Mission',
               description='Validate and export mission folders', category='Import-Export')


def register():
    from . import panel
    panel.register()


def unregister():
    from . import panel
    panel.unregister()
