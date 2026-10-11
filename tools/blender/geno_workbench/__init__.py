"""Blender registration entry point; importing the package needs no bpy."""

bl_info = {
    "name": "Geno Workbench",
    "blender": (4, 0, 0),
    "category": "Animation",
    "description": "Viewer and editor front end for the Geno Workbench engine",
}

_registered = False
_registered_classes = []
_owns_scene_property = False


def add_site_dirs():
    """Make scipy and Pillow importable inside Blender's Python.

    Directories come from GW_SITE (os.pathsep separated); when it is unset the
    default is <workspace>/_build/wbnla-site (a `pip install --target` dir)
    if it exists. Returns the directories added. Safe to call repeatedly.
    """
    import os
    import sys
    from pathlib import Path

    raw = os.environ.get("GW_SITE", "")
    dirs = [d for d in raw.split(os.pathsep) if d]
    if not dirs:
        default = Path(__file__).resolve().parents[3] / "_build" / "wbnla-site"
        if default.is_dir():
            dirs = [str(default)]
    added = []
    for d in dirs:
        if d not in sys.path:
            sys.path.insert(0, d)
            added.append(d)
    return added



def register():
    global _registered, _owns_scene_property

    try:
        import bpy
    except ImportError:
        return

    add_site_dirs()

    if _registered:
        return

    from . import operators, panels, props

    if _registered_classes:
        raise RuntimeError(props.STRINGS["registration_incomplete"])
    if hasattr(bpy.types.Scene, "geno_wb"):
        raise RuntimeError(props.STRINGS["already_registered"])

    classes = (props.GenoWBProps, *operators.CLASSES, *panels.CLASSES)
    try:
        for cls in classes:
            bpy.utils.register_class(cls)
            _registered_classes.append(cls)

        bpy.types.Scene.geno_wb = bpy.props.PointerProperty(
            type=props.GenoWBProps,
            name=props.STRINGS["addon_name"],
        )
        _owns_scene_property = True
        operators.install_callbacks()
        from . import operators_fighter, panels_fighter, panels_attributes, operators_play, panels_play

        operators_fighter.register()
        panels_fighter.register()
        panels_attributes.register()
        operators_play.register()
        panels_play.register()
        from . import panels_ui, panels_projectiles, panels_combo

        panels_ui.register()
        panels_projectiles.register()
        panels_combo.register()
        from . import geno_workspace

        geno_workspace.register()
        from . import hitviz

        hitviz.register()
        from . import anim_ui
        anim_ui.register()
        _registered = True
    except Exception:
        try:
            unregister()
        except Exception as cleanup_error:
            print(props.STRINGS["cleanup_error"].format(error=cleanup_error))
        raise


def unregister():
    global _registered, _owns_scene_property

    try:
        import bpy
    except ImportError:
        return

    from . import api, operators

    _registered = False
    errors = []

    for name in ("panels_combo", "panels_projectiles", "anim_ui", "hitviz", "geno_workspace", "panels_play", "operators_play", "panels_ui", "panels_attributes", "panels_fighter", "operators_fighter"):
        try:
            module = __import__(f"{__name__}.{name}", fromlist=["unregister"])
            module.unregister()
        except Exception as exc:
            errors.append(str(exc))

    try:
        if not operators.shutdown():
            errors.append(api.session().last_error or api.session().status)
    except Exception as exc:
        errors.append(str(exc))

    if _owns_scene_property:
        try:
            if hasattr(bpy.types.Scene, "geno_wb"):
                del bpy.types.Scene.geno_wb
        except Exception as exc:
            errors.append(str(exc))
        else:
            _owns_scene_property = False

    for cls in reversed(tuple(_registered_classes)):
        try:
            bpy.utils.unregister_class(cls)
        except Exception as exc:
            errors.append(str(exc))
        else:
            _registered_classes.remove(cls)

    if errors:
        raise RuntimeError("; ".join(errors))
