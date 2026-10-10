"""Reusable, world-space Blender meshes for Geno workbench overlays.

Only this module owns the tagged overlay datablocks. Hit slots 4 through 7
repeat the four specified slot colours. Geometry comes exclusively from shapes.
"""

import bpy
from mathutils import Matrix

try:
    from . import shapes
except ImportError:
    import shapes


COLLECTION = "GenoWB Overlays"

SLOT_COLORS = (
    (1.0, 0.15, 0.1, 0.55),
    (1.0, 0.55, 0.1, 0.55),
    (1.0, 0.9, 0.1, 0.55),
    (0.9, 0.2, 0.9, 0.55),
)
HURT_COLOR = (0.6, 0.9, 0.72, 0.2)   # pale: the hurtboxes frame the body, they must not dominate it
ECB_COLOR = (0.2, 0.6, 1.0, 1.0)
FLOOR_COLOR = (0.6, 0.6, 0.6, 1.0)

_OWNER_KEY = "_geno_wb_overlay_owned"
_MAX_HIT = 8
_MAX_HURT = 24


def _owned(block):
    return bool(block.get(_OWNER_KEY, False))


def _require_owned(block):
    if not _owned(block):
        raise ValueError(
            "Overlay name collision with an unowned datablock: " + block.name
        )


def _contains_collection(root, wanted):
    pending = [root]
    seen = set()
    while pending:
        collection = pending.pop()
        pointer = collection.as_pointer()
        if pointer in seen:
            continue
        seen.add(pointer)
        if collection == wanted:
            return True
        pending.extend(collection.children)
    return False


def ensure_collection(scene):
    """Return the single named collection, linking it to scene if needed."""
    collection = bpy.data.collections.get(COLLECTION)
    if collection is None:
        collection = bpy.data.collections.new(COLLECTION)
        collection[_OWNER_KEY] = True
    else:
        _require_owned(collection)

    if not _contains_collection(scene.collection, collection):
        scene.collection.children.link(collection)
    return collection


def _material(name, color):
    material = bpy.data.materials.get(name)
    if material is None:
        material = bpy.data.materials.new(name)
        material[_OWNER_KEY] = True
    else:
        _require_owned(material)
    material.diffuse_color = color
    return material


def _object(collection, name, material, color, display_type):
    obj = bpy.data.objects.get(name)
    if obj is None:
        mesh_name = name + ".mesh"
        mesh = bpy.data.meshes.get(mesh_name)
        if mesh is None:
            mesh = bpy.data.meshes.new(mesh_name)
            mesh[_OWNER_KEY] = True
        else:
            _require_owned(mesh)
            if mesh.users:
                raise ValueError("Overlay mesh is already in use: " + mesh_name)
        obj = bpy.data.objects.new(name, mesh)
        obj[_OWNER_KEY] = True
    else:
        _require_owned(obj)
        if obj.type != "MESH":
            raise ValueError("Overlay object is not a mesh: " + name)
        _require_owned(obj.data)

    if obj.name not in collection.objects:
        collection.objects.link(obj)

    # shapes supplies Blender world-space vertices.
    obj.parent = None
    obj.matrix_world = Matrix.Identity(4)
    obj.display_type = display_type
    obj.color = color
    obj.show_in_front = True
    obj.hide_select = True

    materials = obj.data.materials
    if len(materials) != 1 or materials[0] != material:
        materials.clear()
        materials.append(material)
    return obj


def _visibility(obj, visible):
    obj.hide_viewport = not visible
    obj.hide_render = not visible


def _write_geometry(obj, geometry):
    mesh = obj.data
    mesh.clear_geometry()
    mesh.from_pydata(
        geometry["verts"],
        geometry.get("edges", []),
        geometry.get("faces", []),
    )
    mesh.update()


def _slot(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("Hitbox slot must be an integer")
    if not 0 <= value < _MAX_HIT:
        raise ValueError("Hitbox slot must be between 0 and 7")
    return value


def update(info, scene=None, props=None):
    """Update overlays and return visible hit/hurt counts.

    Accept both update(info, scene=None, props=None) and the original
    update(scene, info, props) calling convention.
    """
    if not isinstance(info, dict):
        info, scene = scene, info
    if not isinstance(info, dict):
        raise TypeError("Overlay frame_info must be a dictionary")

    if scene is None:
        scene = bpy.context.scene
    if props is None:
        props = getattr(bpy.context.scene, "geno_wb", None)

    show_hit = bool(getattr(props, "show_hit", True))
    show_hurt = bool(getattr(props, "show_hurt", True))
    show_ecb = bool(getattr(props, "show_ecb", True))
    show_floor = bool(getattr(props, "show_floor", True))

    # Generate and validate the frame before changing any existing meshes.
    geometry = shapes.overlay_geometry(info, None)
    source_slots = {
        _slot(hit["slot"])
        for hit in info.get("hitboxes", [])
        if hit.get("active", True)
    }
    hits = {}
    for hit in geometry["hit"]:
        slot = _slot(hit["slot"])
        if slot not in source_slots or not hit.get("active", True):
            continue
        if slot in hits:
            raise ValueError("Duplicate active hitbox slot: " + str(slot))
        hits[slot] = hit

    hurts = list(geometry["hurt"])
    if len(hurts) > _MAX_HURT:
        raise ValueError("A frame contains more than 24 hurtboxes")
    ecb = geometry["ecb"]
    floor = geometry["floor"]

    collection = ensure_collection(scene)

    # Absent entries retain their mesh storage but cannot remain visible.
    for obj in collection.objects:
        if _owned(obj):
            _visibility(obj, False)
            if obj.name.startswith("GenoWB.hit."):
                obj["geno_wb_active"] = False

    visible_hit = 0
    for slot, hit in sorted(hits.items()):
        color = SLOT_COLORS[slot % len(SLOT_COLORS)]
        material = _material("GenoWB.slot" + str(slot), color)
        obj = _object(
            collection, "GenoWB.hit." + str(slot), material, color, "SOLID"
        )
        _write_geometry(obj, hit)
        obj["geno_wb_slot"] = slot
        obj["geno_wb_active"] = True
        visible = show_hit and bool(hit["verts"])
        _visibility(obj, visible)
        visible_hit += int(visible)

    visible_hurt = 0
    for index, hurt in enumerate(hurts):
        material = _material("GenoWB.hurt", HURT_COLOR)
        obj = _object(
            collection,
            "GenoWB.hurt." + str(index),
            material,
            HURT_COLOR,
            "WIRE",
        )
        _write_geometry(obj, hurt)
        visible = show_hurt and bool(hurt["verts"])
        _visibility(obj, visible)
        visible_hurt += int(visible)

    for name, item, color, enabled in (
        ("GenoWB.ecb", ecb, ECB_COLOR, show_ecb),
        ("GenoWB.floor", floor, FLOOR_COLOR, show_floor),
    ):
        if item["verts"]:
            obj = _object(
                collection, name, _material(name, color), color, "WIRE"
            )
            _write_geometry(obj, item)
            _visibility(obj, enabled)

    return {"hit": visible_hit, "hurt": visible_hurt}


def clear(scene=None):
    """Remove owned overlays and their unused meshes/materials.

    The collection has one global name, so removal affects every scene that
    links it. Foreign objects placed in it are preserved in a scene collection.
    Datablocks without the ownership tag are never deleted.
    """
    if scene is None:
        scene = bpy.context.scene
    collection = bpy.data.collections.get(COLLECTION)
    if collection is not None and _owned(collection):
        for obj in list(collection.objects):
            if _owned(obj):
                bpy.data.objects.remove(obj, do_unlink=True)
            elif obj.name not in scene.collection.objects:
                scene.collection.objects.link(obj)

        for child in list(collection.children):
            if child.name not in scene.collection.children:
                scene.collection.children.link(child)

        bpy.data.collections.remove(collection)

    for meshes_or_materials in (bpy.data.meshes, bpy.data.materials):
        for block in list(meshes_or_materials):
            if _owned(block) and block.users == 0:
                meshes_or_materials.remove(block)
