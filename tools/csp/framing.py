"""Per-asset crop rules and camera framing from a posed skeleton. Pure Python (no bpy).

Both render backends use this module. A fighter's UI images are different crops of
the same posed body (stock = head, select icon = head and shoulders, portrait =
upper body to the waist, results/large render = full body), so the camera for each
is computed from the fighter's own posed joints and skinned mesh, never from the
camera positions of some other character.

Geometry: a camera has an orthonormal basis (right, up, look), all 3-vectors in the
Blender world (Z up). A point's picture coordinates are (dot(right, p), dot(up, p)).
The crop rectangle for an asset is expressed in those coordinates; `camera_for`
turns it into a camera position and ortho scale / perspective distance.
"""
from dataclasses import dataclass
import math
import re


@dataclass(frozen=True)
class AssetSpec:
    key: str
    size: tuple          # retail pixel size (w, h)
    lo: str              # lowest anchor kept in frame: floor|hips|spine|chest|neck
    lo_offset: float     # fraction of body height added below that anchor (negative = cut above it)
    pad: float           # margin around the content, fraction of the content's larger side
    grow: str            # when the aspect needs more height: 'down' keeps the head, 'center' splits
    what: str
    trim: float = 0.0    # fraction of vertices ignored at each extreme (hair spikes in a head crop)


# Camera names are CSProject's (the Captain Falcon template); the sizes are the retail
# image sizes the package contract uses (tools/csp/outputs.py OUTPUTS, geno.md 22.12).
ASSETS = {
    'stock': AssetSpec('stock', (24, 24), 'neck', -0.03, 0.05, 'center', 'HUD stock icon: head', 0.04),
    'icon': AssetSpec('icon', (64, 56), 'chest', 0.0, 0.05, 'down', 'character select tile: head and shoulders', 0.015),
    'portrait': AssetSpec('portrait', (136, 188), 'spine', 0.0, 0.07, 'down', 'character select portrait: upper body to the waist'),
    'results': AssetSpec('results', (52, 74), 'floor', 0.0, 0.05, 'center', 'results card picture: full body'),
    'render': AssetSpec('render', (1000, 1500), 'floor', 0.0, 0.05, 'center', 'large render: full body'),
    'allstar': AssetSpec('allstar', (256, 230), 'hips', 0.0, 0.07, 'down', 'All-Star picture (use unverified): upper body'),
}

# CSProject camera name -> asset. 'Results_SD' is not a CSProject camera: it is the extra view
# both backends add so the 52x74 results card is framed for itself, not borrowed from CSP_SD.
CAMERA_ASSETS = (
    ('allstar', 'allstar'), ('cssicon', 'icon'), ('csp', 'portrait'), ('stc', 'stock'),
    ('stock', 'stock'), ('results', 'results'), ('render', 'render'),
)


def asset_for_camera(name):
    family = re.sub(r'[^a-z0-9]', '', name.lower())
    for token, asset in CAMERA_ASSETS:
        if token in family:
            return asset
    raise ValueError('No UI asset for camera ' + repr(name))


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def norm(v):
    length = math.sqrt(dot(v, v))
    if length < 1e-9:
        raise ValueError('zero-length vector')
    return tuple(x / length for x in v)


def facing_from_feet(feet, toes):
    """Horizontal facing unit vector from foot joints to the toe joints (both lists of 3-points)."""
    if not feet or len(feet) != len(toes):
        raise ValueError('need matching foot and toe joints to find facing')
    x = sum(t[0] - f[0] for f, t in zip(feet, toes))
    y = sum(t[1] - f[1] for f, t in zip(feet, toes))
    if abs(x) + abs(y) < 1e-6:
        raise ValueError('foot-to-toe direction is vertical; cannot find facing')
    return norm((x, y, 0.0))


def camera_basis(facing, yaw_degrees=0.0, pitch_degrees=0.0):
    """Basis of a camera that sees the fighter's front, turned by yaw (about Z) and pitched.

    Positive yaw moves the camera toward the fighter's left (character-left is
    facing x up). Pitch is positive when the camera looks slightly down.
    """
    fx, fy, _ = norm(facing)
    yaw = math.radians(yaw_degrees)
    # direction from the fighter to the camera: facing rotated by yaw.
    cx = fx * math.cos(yaw) - fy * math.sin(yaw)
    cy = fx * math.sin(yaw) + fy * math.cos(yaw)
    look_h = (-cx, -cy, 0.0)
    pitch = math.radians(pitch_degrees)
    look = norm((look_h[0] * math.cos(pitch), look_h[1] * math.cos(pitch), -math.sin(pitch)))
    right = norm((look[1] * 1.0 - look[2] * 0.0, look[2] * 0.0 - look[0] * 1.0, 0.0))  # look x Z
    up = norm((right[1] * look[2] - right[2] * look[1],
               right[2] * look[0] - right[0] * look[2],
               right[0] * look[1] - right[1] * look[0]))
    # right x look would be -up for a right-handed camera; flip so up points to world +Z.
    if up[2] < 0:
        up = tuple(-x for x in up)
    return {'right': right, 'up': up, 'look': look}


def anchor_points(joints, mesh_points):
    """Anchors (3-points) for the crop rules.

    joints: dict role-name -> 3-point for 'hips', 'spine', 'chest', 'neck', 'head' (any may
    be missing) and optional 'foot_l/foot_r/toe_l/toe_r'. mesh_points: skinned vertices of
    the visible fighter mesh in world space. floor = lowest vertex, top = highest vertex
    (hair and ornaments count). Missing joints fall back to fixed body fractions and are
    reported in 'fallback'.
    """
    if not mesh_points:
        raise ValueError('no fighter mesh points')
    low = min(mesh_points, key=lambda p: p[2])
    high = max(mesh_points, key=lambda p: p[2])
    height = high[2] - low[2]
    if height <= 1e-6:
        raise ValueError('fighter mesh has no height')
    cx = sum(p[0] for p in mesh_points) / len(mesh_points)
    cy = sum(p[1] for p in mesh_points) / len(mesh_points)
    fractions = {'hips': 0.53, 'spine': 0.62, 'chest': 0.72, 'neck': 0.82, 'head': 0.88}
    anchors, fallback = {'floor': low, 'top': high}, []
    for name, fraction in fractions.items():
        value = joints.get(name)
        if value is None:
            fallback.append(name)
            value = (cx, cy, low[2] + height * fraction)
        anchors[name] = tuple(value)
    anchors['height'] = height
    anchors['fallback'] = fallback
    return anchors


def crop_rect(asset, anchors, mesh_points, basis):
    """Crop rectangle (u_min, v_min, u_max, v_max) in picture coordinates, before aspect fitting.

    The vertical extent runs from the asset's lowest anchor to the top of the mesh. The
    horizontal extent is that of the mesh vertices at or above the lowest anchor's world
    height, so a stretched arm or a spiky head is inside the frame.
    """
    spec = ASSETS[asset] if isinstance(asset, str) else asset
    low_anchor = anchors[spec.lo]
    low_z = low_anchor[2] - spec.lo_offset * anchors['height']
    band = [p for p in mesh_points if p[2] >= low_z - 1e-6]
    if not band:
        raise ValueError('no mesh in crop band for ' + spec.key)
    us = sorted(dot(basis['right'], p) for p in band)
    vs = sorted(dot(basis['up'], p) for p in band)
    cut = int(len(band) * spec.trim)
    v_low = dot(basis['up'], (low_anchor[0], low_anchor[1], low_z))
    v_min = min(vs[0], v_low) if spec.lo == 'floor' else v_low
    return us[cut], v_min, us[len(us) - 1 - cut], vs[len(vs) - 1 - cut]


def fit_rect(rect, size, pad, grow='center'):
    """Pad the content rect and expand it to the image aspect. Returns (cu, cv, width, height)."""
    u0, v0, u1, v1 = rect
    aspect = size[0] / size[1]
    width, height = u1 - u0, v1 - v0
    margin = pad * max(width, height)
    u0, u1, v0, v1 = u0 - margin, u1 + margin, v0 - margin, v1 + margin
    width, height = u1 - u0, v1 - v0
    cu = (u0 + u1) / 2
    if width / height < aspect:
        width = height * aspect
        cv = (v0 + v1) / 2
    else:
        new_height = width / aspect
        # 'down' keeps the top edge (headroom stays put); 'center' splits the extra height.
        cv = v1 - new_height / 2 if grow == 'down' else (v0 + v1) / 2
        height = new_height
    return cu, cv, width, height


def camera_for(rect_fit, basis, *, lens=None, sensor=36.0, fit='AUTO'):
    """Camera placement for a fitted crop.

    Orthographic (lens None): ortho_scale = the larger crop side (Blender applies it to the
    larger image side). Perspective: distance so the crop fills the sensor-fit dimension:
    AUTO/larger side, HORIZONTAL = width, VERTICAL = height (distance = side * lens / sensor).
    The camera sits on the view axis through the crop centre.
    """
    cu, cv, width, height = rect_fit
    centre = tuple(basis['right'][i] * cu + basis['up'][i] * cv for i in range(3))
    if lens is None:
        scale = max(width, height)
        distance = max(scale * 4.0, 1.0)
    else:
        side = {'HORIZONTAL': width, 'VERTICAL': height}.get(fit, max(width, height))
        distance = side * lens / sensor
        scale = None
    position = tuple(centre[i] - basis['look'][i] * distance for i in range(3))
    return {'location': position, 'ortho_scale': scale, 'distance': distance, 'centre': centre,
            'width': width, 'height': height, 'look': basis['look'], 'up': basis['up'], 'right': basis['right']}


def plan(asset, anchors, mesh_points, basis, size=None, **camera):
    spec = ASSETS[asset]
    size = size or spec.size
    rect = crop_rect(asset, anchors, mesh_points, basis)
    fitted = fit_rect(rect, size, spec.pad, spec.grow)
    result = camera_for(fitted, basis, **camera)
    result['asset'] = asset
    result['rect'] = rect
    return result


def rotation_matrix(basis):
    """Camera-to-world rotation columns: X=right, Y=up, Z=-look (Blender cameras look down -Z)."""
    r, u, l = basis['right'], basis['up'], basis['look']
    return ((r[0], u[0], -l[0]), (r[1], u[1], -l[1]), (r[2], u[2], -l[2]))


def resolve_role_bones(plan_doc, aliases=None, overrides=None):
    """role -> bone name from a built plan.json ('roles' index lists + 'joints' names).

    aliases maps a plan joint name to the armature bone name (workbench art.bone_aliases,
    e.g. j7 -> JOBJ_7). overrides (ui_render.roles) wins. Returns only roles it can resolve.
    """
    aliases = aliases or {}
    joints = {j['index']: j['name'] for j in plan_doc.get('joints', [])}
    roles = plan_doc.get('roles') or {}
    result = {}
    for role, indices in roles.items():
        if isinstance(indices, list) and indices and indices[0] in joints:
            name = joints[indices[0]]
            result[role] = aliases.get(name, name)
    result.update(overrides or {})
    return result


# role names used by the crop rules -> keys in the 'joints' dict handed to anchor_points
ANCHOR_ROLES = {'hips': 'hips', 'spine': 'spine', 'chest': 'chest', 'neck': 'neck', 'head': 'head',
                'foot.L': 'foot_l', 'foot.R': 'foot_r', 'toe.L': 'toe_l', 'toe.R': 'toe_r'}
