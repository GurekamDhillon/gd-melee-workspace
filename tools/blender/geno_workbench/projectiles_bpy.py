"""Projectiles in the Blender scene: a "Projectiles" collection, spawn markers and the ghost path.

Each article of the fighter is a root object ``Proj.<name>`` (a small proxy mesh the artist replaces with the
projectile's look; its location is the article's ``spawn`` offset: X forward, Z up) with one child sphere per
hitbox (``Proj.<name>.hb<k>``: location = the hitbox ``offset``, uniform scale = its ``size``).  Everything else is a
custom property on the object (``gp_*`` on the root, ``gh_*`` on a hitbox), and the article exactly as the source has
it is kept as JSON in ``geno_article`` so keys this add-on does not know survive.  ``export_articles`` merges the
two (projectiles.unflatten), ``pending_ops`` diffs that against the server's copy: an unchanged import has no ops.

Axes: Melee (x, y up, z depth) <-> Blender (x, -z, y) as everywhere in this add-on (wbspace.to_blender_point).
The spawn markers are scene timeline markers named ``SPAWN <article> #<n>`` at the move frame the script's
``CALL geno.article.spawn`` runs on (the Workbench frame); dragging one and pressing Apply edits the script.
"""
from __future__ import annotations

import json

import bpy
from mathutils import Vector

try:
    from . import projectiles as P
    from . import wbspace as W
except ImportError:  # run as a plain module in the tests
    import projectiles as P
    import wbspace as W

COLLECTION = "Projectiles"
GHOST_COLLECTION = "Projectile Ghosts"
SRC = "geno_article"          # the article as the source has it (JSON)
INDEX = "geno_article_index"  # its index in the fighter's list, -1 for a new one
HB_SRC = "geno_hitbox"
OWNED = "_geno_proj"
TRANSFORM_FIELDS = {"spawn/#0", "spawn/#1"}           # carried by the root's location
TRANSFORM_HB = {"offset/#0", "offset/#1", "offset/#2", "size"}  # carried by the hitbox's location and scale
MARKER_PREFIX = "SPAWN "
SLOT_COLORS = [(1.0, 0.2, 0.2, 1.0), (0.2, 0.6, 1.0, 1.0), (0.3, 0.9, 0.3, 1.0), (1.0, 0.8, 0.1, 1.0)]


def _key(prefix, path):
    return prefix + path.replace("/#", "_").replace("/", "_")


def _ensure_collection(scene, name, parent=None):
    col = bpy.data.collections.get(name)
    if col is None:
        col = bpy.data.collections.new(name)
        col[OWNED] = True
    host = parent or scene.collection
    if col.name not in [c.name for c in host.children] and col.name not in [c.name for c in scene.collection.children_recursive]:
        host.children.link(col)
    return col


def fighter_collection(scene):
    """The collection holding the fighter's armature, else the scene's."""
    for obj in scene.objects:
        if obj.type == "ARMATURE" and obj.users_collection:
            col = obj.users_collection[0]
            if col != scene.collection and not col.get(OWNED):
                return col
    return scene.collection


def projectiles_collection(scene):
    return _ensure_collection(scene, COLLECTION, fighter_collection(scene))


def _sphere_mesh(name, radius=1.0, rings=6, segs=10):
    mesh = bpy.data.meshes.get(name)
    if mesh is not None:
        return mesh
    import math
    mesh = bpy.data.meshes.new(name)
    verts, faces = [(0, 0, -radius)], []
    for r in range(1, rings):
        phi = math.pi * r / rings - math.pi / 2
        for s in range(segs):
            th = 2 * math.pi * s / segs
            verts.append((radius * math.cos(phi) * math.cos(th), radius * math.cos(phi) * math.sin(th), radius * math.sin(phi)))
    verts.append((0, 0, radius))
    top = len(verts) - 1
    for s in range(segs):
        faces.append((0, 1 + s, 1 + (s + 1) % segs))
        faces.append((top, 1 + (rings - 2) * segs + (s + 1) % segs, 1 + (rings - 2) * segs + s))
    for r in range(rings - 2):
        for s in range(segs):
            a, b = 1 + r * segs + s, 1 + r * segs + (s + 1) % segs
            faces.append((a, b, b + segs, a + segs))
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    return mesh


def _mat(name, color):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    return mat


def _set_prop(obj, key, value, kind, lo=None, hi=None):
    if kind == "bool":
        obj[key] = 1 if value else 0
    elif kind == "int":
        obj[key] = int(value)
    elif kind == "float":
        obj[key] = float(value)
    else:
        obj[key] = str(value)


def _get_prop(obj, key, default, kind):
    if key not in obj:
        return default
    v = obj[key]
    if kind == "bool":
        return bool(v)
    if kind == "int":
        return int(v)
    if kind == "float":
        return float(v)
    return str(v)


def _to_b(x, y, z=0.0):
    return Vector(W.to_blender_point((x, y, z)))


def _from_b(v):
    x, y, z = W.from_blender_point((v.x, v.y, v.z))
    return x, y, z


# --- import ----------------------------------------------------------------------------------------------------------
def clear_projectiles(scene=None):
    scene = scene or bpy.context.scene
    col = bpy.data.collections.get(COLLECTION)
    if col is None:
        return
    for obj in list(col.all_objects):
        if obj.get(OWNED):
            bpy.data.objects.remove(obj, do_unlink=True)


def import_articles(articles, scene=None, replace=True):
    """Build one root + hitbox spheres per article.  ``articles``: the list_articles reply (extra "index" key allowed)."""
    scene = scene or bpy.context.scene
    col = projectiles_collection(scene)
    if replace:
        clear_projectiles(scene)
    roots = []
    for i, raw in enumerate(articles):
        art = {k: v for k, v in raw.items() if k != "index"}
        roots.append(_make_article(col, art, raw.get("index", i)))
    return roots


def _make_article(col, art, index):
    name = art.get("name") or "Projectile%d" % index
    root = bpy.data.objects.new("Proj." + name, _sphere_mesh("Proj.proxy", 0.5))
    root[OWNED] = True
    col.objects.link(root)
    root.display_type = "WIRE"
    root[SRC] = P.canonical(art)
    root[INDEX] = int(index)
    flat = P.flatten(art)
    for path, _, kind in P.FIELDS:
        if path in TRANSFORM_FIELDS:
            continue
        _set_prop(root, _key("gp_", path), flat[path], kind)
    root.location = _to_b(flat["spawn/#0"], flat["spawn/#1"])
    # the proxy scale shows the model scale
    root.scale = (flat["scale"] * 1.0,) * 3 if False else (1.0, 1.0, 1.0)
    for k, hb in enumerate(flat["hitboxes"]):
        _make_hitbox(col, root, name, k, art["hitboxes"][k], hb)
    return root


def _make_hitbox(col, root, name, k, src, flat):
    obj = bpy.data.objects.new("Proj.%s.hb%d" % (name, k), _sphere_mesh("Proj.hitbox", 1.0))
    obj[OWNED] = True
    col.objects.link(obj)
    obj.parent = root
    obj[HB_SRC] = json.dumps(src, separators=(",", ":"))
    for path, _, kind in P.HITBOX_FIELDS:
        if path in TRANSFORM_HB:
            continue
        _set_prop(obj, _key("gh_", path), flat[path], kind)
    obj.location = _to_b(flat["offset/#0"], flat["offset/#1"], flat["offset/#2"])
    obj.scale = (float(flat["size"]),) * 3
    obj.display_type = "SOLID"
    obj.show_transparent = True
    slot = int(flat["slot"]) % 4
    mat = _mat("Proj.slot%d" % slot, SLOT_COLORS[slot][:3] + (0.35,))
    obj.data = obj.data
    obj.color = SLOT_COLORS[slot]
    if not obj.data.materials:
        obj.data.materials.append(mat)
    return obj


# --- export ----------------------------------------------------------------------------------------------------------
def roots(scene=None):
    scene = scene or bpy.context.scene
    col = bpy.data.collections.get(COLLECTION)
    if col is None:
        return []
    found = [o for o in col.all_objects if o.get(OWNED) and SRC in o and o.parent is None]
    return sorted(found, key=lambda o: (o.get(INDEX, -1) if o.get(INDEX, -1) >= 0 else 1 << 30, o.name))


def hitbox_children(root):
    kids = [c for c in root.children if c.get(OWNED) and HB_SRC in c]
    return sorted(kids, key=lambda c: c.name)


def export_article(root):
    """The article dict the scene says (the source article with this object's edits merged in)."""
    base = json.loads(root[SRC])
    flat = P.flatten(base)
    for path, _, kind in P.FIELDS:
        if path in TRANSFORM_FIELDS:
            continue
        flat[path] = _get_prop(root, _key("gp_", path), flat[path], kind)
    # location: forward (x) and up (z); compare in float32 so an unchanged import writes nothing
    fx, fy, _ = _from_b(root.location)
    for path, val in (("spawn/#0", fx), ("spawn/#1", fy)):
        if abs(val - float(flat[path])) > 1e-4:
            flat[path] = round(val, 4)
    boxes = []
    for k, child in enumerate(hitbox_children(root)):
        src = json.loads(child[HB_SRC])
        fh = P.flatten({"hitboxes": [src]})["hitboxes"][0]
        for path, _, kind in P.HITBOX_FIELDS:
            if path in TRANSFORM_HB:
                continue
            fh[path] = _get_prop(child, _key("gh_", path), fh[path], kind)
        ox, oy, oz = _from_b(child.location)
        for path, val in (("offset/#0", ox), ("offset/#1", oy), ("offset/#2", oz)):
            if abs(val - float(fh[path])) > 1e-4:
                fh[path] = round(val, 4)
        size = float(child.scale.x)
        if abs(size - float(fh["size"])) > 1e-4:
            fh["size"] = round(size, 4)
        boxes.append((src, fh))
    # keep each hitbox's own unknown keys: unflatten the list against the original entries
    base_boxes = base.get("hitboxes", [])
    flat["hitboxes"] = [fh for _, fh in boxes]
    merged = dict(base)
    merged["hitboxes"] = [src for src, _ in boxes] if boxes or "hitboxes" in base else base_boxes
    out = P.unflatten(merged, flat)
    if not boxes and "hitboxes" not in base:
        out.pop("hitboxes", None)
    return out


def export_articles(scene=None):
    return [(r.get(INDEX, -1), export_article(r)) for r in roots(scene)]


def pending_ops(server_articles, scene=None):
    """{index: ops} for the existing articles that differ from the server's copy, plus ``new``: [article, ...]."""
    result = {"edits": {}, "new": []}
    by_index = {a.get("index", i): {k: v for k, v in a.items() if k != "index"} for i, a in enumerate(server_articles)}
    for index, art in export_articles(scene):
        if index in by_index:
            ops = P.diff_ops(by_index[index], art)
            if ops:
                result["edits"][index] = ops
        else:
            result["new"].append(art)
    return result


def mark_synced(server_articles, scene=None):
    """After a successful apply: the source of each object is now the server's copy."""
    by_index = {a.get("index", i): {k: v for k, v in a.items() if k != "index"} for i, a in enumerate(server_articles)}
    for r in roots(scene):
        idx = r.get(INDEX, -1)
        if idx in by_index:
            r[SRC] = P.canonical(by_index[idx])
            for child, hb in zip(hitbox_children(r), by_index[idx].get("hitboxes", [])):
                child[HB_SRC] = json.dumps(hb, separators=(",", ":"))


def add_projectile(name="NewProjectile", scene=None):
    """A fresh article (a 3-unit ball, speed 2, 40 frames) as a new root; Apply sends it as add_article."""
    scene = scene or bpy.context.scene
    col = projectiles_collection(scene)
    art = {"name": name, "lifetime": 40, "velocity": [2.0, 0], "spawn": [8, 8], "max_live": 2,
           "hitboxes": [{"slot": 0, "damage": 5, "size": 3.0, "offset": [0, 0, 0], "angle": 361, "kbg": 50, "bkb": 20, "start": 1, "end": 0}]}
    root = _make_article(col, art, -1)
    return root


# --- spawn markers ---------------------------------------------------------------------------------------------------
def sync_markers(spawns, articles, row, scene=None):
    """One timeline marker per spawn of ``row``; remembers what it showed so a drag can be detected."""
    scene = scene or bpy.context.scene
    for m in list(scene.timeline_markers):
        if m.name.startswith(MARKER_PREFIX):
            scene.timeline_markers.remove(m)
    record = {}
    for sp in spawns:
        if sp.get("row") != row:
            continue
        a = sp.get("article", 0)
        nm = articles[a]["name"] if 0 <= a < len(articles) else "article%d" % a
        label = "%s%s #%d" % (MARKER_PREFIX, nm, sp["ordinal"])
        scene.timeline_markers.new(label, frame=int(sp["frame"]))
        record[label] = {"row": row, "ordinal": int(sp["ordinal"]), "frame": int(sp["frame"])}
    scene["geno_spawn_markers"] = json.dumps(record)
    return record


def marker_edits(scene=None):
    """[{row, ordinal, frame}] for the spawn markers that were moved since sync_markers."""
    scene = scene or bpy.context.scene
    try:
        record = json.loads(scene.get("geno_spawn_markers", "{}"))
    except ValueError:
        return []
    out = []
    for m in scene.timeline_markers:
        was = record.get(m.name)
        if was and int(m.frame) != was["frame"]:
            out.append({"row": was["row"], "ordinal": was["ordinal"], "frame": int(m.frame)})
    return out


# --- ghost -------------------------------------------------------------------------------------------------------------
def _ghost_object(col, name, mesh_name, radius=None):
    obj = bpy.data.objects.get(name)
    if obj is None:
        mesh = bpy.data.meshes.new(mesh_name) if radius is None else _sphere_mesh("Ghost.sphere", 1.0)
        obj = bpy.data.objects.new(name, mesh)
        obj[OWNED] = True
        col.objects.link(obj)
    return obj


def clear_ghost(scene=None):
    for obj in list(bpy.data.objects):
        if obj.name.startswith("Ghost.") and obj.get(OWNED):
            bpy.data.objects.remove(obj, do_unlink=True)


def update_ghost(articles, spawns, row, frame, scene=None, base=(0.0, 0.0), facing=1, bone_base=None):
    """Draw each spawn of ``row``'s flight path and, at ``frame``, the projectile and its live hitboxes.

    ``bone_base(article) -> (x, y)`` supplies the world position of an article's ``bone`` (the live pose); else ``base``.
    Returns the ghost summary list (one dict per spawn) for tests and the panel.
    """
    scene = scene or bpy.context.scene
    col = _ensure_collection(scene, GHOST_COLLECTION)
    clear_ghost(scene)
    out = []
    for sp in spawns:
        if sp.get("row") != row or not (0 <= sp.get("article", 0) < len(articles)):
            continue
        art = {k: v for k, v in articles[sp["article"]].items() if k != "index"}
        b = base
        if bone_base is not None and int(art.get("bone", -1)) >= 0:
            got = bone_base(art)
            if got is not None:
                b = got
        g = P.ghost_at(art, int(sp["frame"]), int(frame), b, facing, float(sp.get("angle", 0)), int(sp.get("variant", 0)))
        tag = "%d.%d" % (sp["ordinal"], sp["article"])
        path = _ghost_object(col, "Ghost.path." + tag, "Ghost.path." + tag)
        pts = [W.to_blender_point((x, y, 0.0)) for x, y in g["path"]]
        path.data.clear_geometry()
        path.data.from_pydata(pts, [(i, i + 1) for i in range(len(pts) - 1)], [])
        path.data.update()
        path.color = (1.0, 0.85, 0.2, 1.0)
        path.show_in_front = True
        n = 0
        if g["root"] is not None:
            dot = _ghost_object(col, "Ghost.root." + tag, "", radius=1.0)
            dot.location = W.to_blender_point((g["root"][0], g["root"][1], 0.0))
            dot.scale = (0.4, 0.4, 0.4)
            dot.color = (1.0, 1.0, 1.0, 1.0)
            dot.display_type = "WIRE"
            for hx, hy, hr, slot, idx in g["hitboxes"]:
                h = _ghost_object(col, "Ghost.hb.%s.%d" % (tag, idx), "", radius=1.0)
                h.location = W.to_blender_point((hx, hy, 0.0))
                h.scale = (hr, hr, hr)
                h.display_type = "WIRE"
                h.color = SLOT_COLORS[slot % 4]
                n += 1
        out.append({"ordinal": sp["ordinal"], "article": sp["article"], "life": g["life"], "root": g["root"],
                    "hitboxes": n, "points": len(pts)})
    return out
