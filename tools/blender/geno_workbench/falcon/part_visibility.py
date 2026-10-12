"""Which of a fighter model's DObjs the game draws in its default pose, from the fighter's model-part tables.

The engine hides every DObj named by a visibility table, then shows the ones in each model part's current state
(ftParts_8007487C / ftParts_80074D7C / ftParts_80074B6C in the decomp). A Melee fighter model therefore carries
more than one mesh set: Captain Falcon has the high-poly set (helmet, visor, eyes) and a low-poly set that is only
for distant camera LODs, and the glTF/DAT import draws all of them (no eyes, a grey slab at the shoulder).

`HsdExport --parts PlXx.dat PlXxNr.dat parts.json` dumps the tables; this module picks the hidden set (pure Python,
no bpy) and, inside Blender, applies it: hidden objects get hide_render + hide_viewport and `geno_part_hidden`.
Tables listed per costume row (a missing row falls back to row 0, as the game does):
    lods[lod][part][state] = DObj indices.   lod: high, low, metal (the metal model's own DObj list; not ours), metal_main.
"""
import json
from pathlib import Path

MAIN_LIST_LODS = ('high', 'low', 'metal_main')   # tables indexed into the main model's DObj list


def row_for(doc, costume):
    rows = {r['costume']: r for r in doc.get('rows', [])}
    row = rows.get(costume)
    if row is None or not row['lods'].get('high'):
        row = rows.get(0)
    return row


def select_hidden(doc, costume=0, lod='high', states=None):
    """DObj indices hidden for `costume` drawn at `lod` ('high' | 'low'); `states` = {part: state} (default 0).

    Everything any main-list table names starts hidden; the chosen LOD's entry for each model part's current state
    is shown again. A DObj no table names is always drawn."""
    row = row_for(doc, costume)
    if row is None:
        return []
    states = states or {}
    hidden, shown = set(), set()
    for name in MAIN_LIST_LODS:
        table = row['lods'].get(name)
        if not table:
            continue
        for part, part_states in enumerate(table):
            for state, indices in enumerate(part_states):
                hidden.update(indices)
                if name == lod and state == states.get(part, 0):
                    shown.update(indices)
    return sorted(hidden - shown)


def hidden_names(doc, costume=0, lod='high', states=None):
    names = {d['index']: d['name'] for d in doc['dobjs']}
    return [names[i] for i in select_hidden(doc, costume, lod, states) if i in names]


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def apply_to_objects(objects, hidden):
    """Inside Blender: hide the named objects. Returns (hidden names found, names the blend lacks)."""
    wanted = set(hidden)
    by_name = {o.name: o for o in objects}
    found = []
    for name in sorted(wanted):
        obj = by_name.get(name)
        if obj is None:
            continue
        obj.hide_render = True
        obj.hide_viewport = True
        obj['geno_part_hidden'] = 1
        found.append(name)
    return found, sorted(wanted - set(found))


def alpha_by_name(doc):
    """{object name: material alpha} for DObjs whose material is translucent (the glTF export loses it)."""
    return {d['name']: d['alpha'] for d in doc['dobjs'] if d.get('alpha') is not None}


def apply_alpha(objects, alphas):
    """Inside Blender: set the Principled Alpha of each named object's materials (hashed blend is already on).
    Returns the names changed."""
    changed = []
    for obj in objects:
        value = alphas.get(obj.name)
        if value is None:
            continue
        for mat in obj.data.materials:
            if mat is None or not mat.use_nodes:
                continue
            for node in mat.node_tree.nodes:
                if node.type == 'BSDF_PRINCIPLED' and 'Alpha' in node.inputs and not node.inputs['Alpha'].links:
                    node.inputs['Alpha'].default_value = value
                    changed.append(obj.name)
    return sorted(set(changed))


def cull_names(doc):
    """Names of DObjs the engine draws one-sided (POBJ CULLFRONT), whose glTF material is double-sided."""
    return {d['name'] for d in doc['dobjs'] if d.get('cull') == 'front'}


def apply_cull(objects, names):
    """Inside Blender: turn on backface culling on the named objects' materials. Returns the names changed."""
    changed = []
    for obj in objects:
        if obj.name in names:
            for mat in obj.data.materials:
                if mat is not None:
                    mat.use_backface_culling = True
            changed.append(obj.name)
    return sorted(changed)


def apply_replace_diffuse(objects):
    """Inside Blender: drop the material-diffuse multiply from textured materials (texture COLORMAP_REPLACE).

    HsdExport's glTF carries the MObj diffuse colour (Falcon: 179/255 = 0.70) as the baseColorFactor, and the importer
    multiplies the texture by it. The engine's tex0 is COLORMAP_REPLACE (every Falcon DObj but the two env-map ones),
    so the texture is the colour and the game's lighting brightens it; the 0.70 factor made the whole model, and most
    visibly the white shoulder armour (DObj 77/78, Image_32/33), render grey. The Mix node's B input goes to white.
    Returns the number of Mix nodes changed."""
    changed = 0
    for obj in objects:
        for mat in getattr(obj.data, 'materials', []):
            if mat is None or not mat.use_nodes:
                continue
            for node in mat.node_tree.nodes:
                if node.type == 'MIX' and node.data_type == 'RGBA' and node.blend_type == 'MULTIPLY':
                    sock = node.inputs[7]
                    if not sock.links and tuple(sock.default_value)[:3] != (1.0, 1.0, 1.0):
                        sock.default_value = (1.0, 1.0, 1.0, 1.0)
                        changed += 1
    return changed
