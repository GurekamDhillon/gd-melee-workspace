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


def register():
    global _registered, _owns_scene_property

    try:
        import bpy
    except ImportError:
        return

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
