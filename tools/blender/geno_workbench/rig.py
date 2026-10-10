"""Load local fighter art without modifying its source files.

For a .blend containing several scenes, use its first stored scene. All
armatures and their skinned meshes are retained; a unique ``geno`` marker
selects the fighter when that scene contains several armatures.
"""

from pathlib import Path
import threading

import bpy

try:
    from .props import STRINGS
except ImportError:
    from props import STRINGS


for _key, _value in {
    "fighter_main_thread": "Fighter operations must run on Blender's main thread",
    "fighter_not_armature": "Select an armature before using the fighter workbench",
    "fighter_missing_art": "Fighter art file does not exist: {path}",
    "fighter_no_art": "Choose a .blend or .glb fighter art file",
    "fighter_wrong_extension": "Expected a {extension} fighter art file: {path}",
    "fighter_object_mode": "Switch to Object Mode before loading fighter art",
    "fighter_no_imported_armature": "No armature was found in fighter art: {path}",
    "fighter_ambiguous_armature": (
        "Several armatures were found in {path}; give exactly one a geno "
        "custom property: {names}"
    ),
    "fighter_import_failed": "Could not load fighter art {path}: {error}",
}.items():
    STRINGS.setdefault(_key, _value)


def _text(key, **values):
    return STRINGS[key].format(**values)


def _require_main_thread():
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError(STRINGS["fighter_main_thread"])


def _is_armature(obj):
    try:
        return obj is not None and obj.type == "ARMATURE"
    except ReferenceError:
        return False


def _choose_armature(objects, name=""):
    arms = [obj for obj in objects if _is_armature(obj)]
    if name:
        named = next((obj for obj in arms if obj.name == name), None)
        if named is not None:
            return named
    if len(arms) == 1:
        return arms[0]
    marked = [obj for obj in arms if "geno" in obj]
    return marked[0] if len(marked) == 1 else None


def find_armature(name=""):
    """Prefer the named armature, a single armature, then a unique geno rig."""
    _require_main_thread()
    return _choose_armature(bpy.data.objects, name)


def bone_names(arm):
    _require_main_thread()
    if not _is_armature(arm):
        raise RuntimeError(STRINGS["fighter_not_armature"])
    return [bone.name for bone in arm.data.bones]


_TRACKED_DATA = (
    "objects", "scenes", "collections", "meshes", "armatures", "actions",
    "materials", "textures", "images", "node_groups", "curves", "cameras",
    "lights", "worlds", "shape_keys",
)


class ImportTransaction:
    """Remove only newly imported datablocks if a load or calibration fails."""

    def __enter__(self):
        _require_main_thread()
        self.before = {
            name: {item.as_pointer() for item in getattr(bpy.data, name)}
            for name in _TRACKED_DATA
        }
        self.selected = list(bpy.context.selected_objects)
        self.active = bpy.context.view_layer.objects.active
        return self

    def new_data(self, name):
        previous = self.before[name]
        return [
            item for item in getattr(bpy.data, name)
            if item.as_pointer() not in previous
        ]

    def _restore_selection(self):
        layer = bpy.context.view_layer
        for obj in list(bpy.context.selected_objects):
            obj.select_set(False)
        for obj in self.selected:
            if layer.objects.get(obj.name) == obj:
                obj.select_set(True)
        if self.active is None:
            layer.objects.active = None
        elif layer.objects.get(self.active.name) == self.active:
            layer.objects.active = self.active

    def __exit__(self, exc_type, exc, traceback):
        if exc_type is not None:
            added = [
                item
                for name in _TRACKED_DATA
                for item in self.new_data(name)
            ]
            try:
                if added:
                    bpy.data.batch_remove(ids=tuple(added))
            finally:
                self._restore_selection()
                bpy.context.view_layer.update()
        return False


def import_transaction():
    """Also usable around load_fighter followed by calibration."""
    return ImportTransaction()


def _skinned_to(obj, armatures):
    if obj.type != "MESH":
        return False
    if obj.find_armature() in armatures:
        return True
    return any(
        modifier.type == "ARMATURE" and modifier.object in armatures
        for modifier in obj.modifiers
    )


def _art_path(value, extension):
    path = Path(bpy.path.abspath(str(value))).expanduser()
    if not path.is_file():
        raise RuntimeError(_text("fighter_missing_art", path=path))
    if path.suffix.lower() != extension:
        raise RuntimeError(_text(
            "fighter_wrong_extension", extension=extension, path=path
        ))
    return path.resolve()


def load_fighter(blend="", glb=""):
    """Append a .blend scene's rig objects, or import and clean up a .glb.

    Cleanup is restricted to this import. Existing scene objects and unskinned
    meshes are never deleted. A nonempty blend argument takes precedence.
    """
    _require_main_thread()
    if not blend and not glb:
        raise RuntimeError(STRINGS["fighter_no_art"])
    path = _art_path(blend or glb, ".blend" if blend else ".glb")
    if bpy.context.mode != "OBJECT":
        raise RuntimeError(STRINGS["fighter_object_mode"])

    try:
        with import_transaction() as transaction:
            destination = bpy.context.collection or bpy.context.scene.collection
            source_scene = None
            if blend:
                with bpy.data.libraries.load(str(path), link=False) as (src, dst):
                    if src.scenes:
                        dst.scenes = [src.scenes[0]]
                    else:
                        dst.objects = list(src.objects)
                    # Include reference actions even when they have no active user.
                    dst.actions = list(src.actions)
                if dst.scenes:
                    source_scene = dst.scenes[0]
                    candidates = list(source_scene.objects)
                else:
                    candidates = [obj for obj in dst.objects if obj is not None]
            else:
                result = bpy.ops.import_scene.gltf(filepath=str(path))
                if "FINISHED" not in result:
                    raise RuntimeError(str(result))
                candidates = transaction.new_data("objects")

            armatures = [obj for obj in candidates if _is_armature(obj)]
            arm = _choose_armature(armatures)
            if arm is None:
                key = (
                    "fighter_ambiguous_armature"
                    if armatures else "fighter_no_imported_armature"
                )
                raise RuntimeError(_text(
                    key, path=path,
                    names=", ".join(obj.name for obj in armatures),
                ))

            keep = set(armatures)
            keep.update(
                obj for obj in candidates if _skinned_to(obj, armatures)
            )
            world = {obj: obj.matrix_world.copy() for obj in keep}

            for obj in keep:
                if destination.objects.get(obj.name) != obj:
                    destination.objects.link(obj)
                if obj.parent is not None and obj.parent not in keep:
                    obj.parent = None
                    obj.matrix_world = world[obj]

            for imported_arm in armatures:
                for bone in imported_arm.pose.bones:
                    bone.custom_shape = None

            discard = [
                obj for obj in transaction.new_data("objects") if obj not in keep
            ]
            if discard:
                bpy.data.batch_remove(ids=tuple(discard))

            # The appended scene and its collection hierarchy were only a source
            # inventory. The retained objects now belong to the current collection.
            for scene in transaction.new_data("scenes"):
                bpy.data.scenes.remove(scene)
            for collection in transaction.new_data("collections"):
                bpy.data.collections.remove(collection, do_unlink=True)

            bpy.context.view_layer.update()
            for obj in list(bpy.context.selected_objects):
                obj.select_set(False)
            arm.hide_set(False)
            arm.select_set(True)
            bpy.context.view_layer.objects.active = arm
            return arm
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(_text(
            "fighter_import_failed", path=path, error=exc
        )) from exc
