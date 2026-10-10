"""Synthetic overlay meshes in Blender coordinates, with no scene access.

Mesh builders accept Blender-space points. overlay_geometry alone reads
engine positions and converts them through wbspace.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

if __package__:
    from . import wbspace as W
else:
    import wbspace as W

Vec3 = tuple[float, float, float]
Mesh = tuple[list[Vec3], list[tuple]]


def _point3(p: Sequence[float]) -> Vec3:
    if len(p) != 3:
        raise ValueError("expected a three-component point")
    point = tuple(float(value) for value in p)
    if not all(math.isfinite(value) for value in point):
        raise ValueError("point values must be finite")
    return point


def _xyz(value, default_z: float = 0.0) -> Vec3:
    if isinstance(value, Mapping):
        return _point3(
            (value["x"], value["y"], value.get("z", default_z))
        )
    if len(value) == 2:
        return _point3((value[0], value[1], default_z))
    return _point3(value)


def _blender_point(value, default_z: float = 0.0) -> Vec3:
    return W.to_blender_point(_xyz(value, default_z))


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _basis(axis: Vec3) -> tuple[Vec3, Vec3]:
    reference = (1.0, 0.0, 0.0) if abs(axis[0]) < 0.9 else (0.0, 1.0, 0.0)
    projection = sum(reference[i] * axis[i] for i in range(3))
    perpendicular = tuple(
        reference[i] - projection * axis[i] for i in range(3)
    )
    length = math.hypot(*perpendicular)
    u = tuple(value / length for value in perpendicular)
    return u, _cross(axis, u)


def _profile(length: float, radius: float, rings: int) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []

    def append(axial: float, radial: float) -> None:
        point = (axial, radial)
        if not points or point != points[-1]:
            points.append(point)

    for i in range(rings + 1):
        if i == 0:
            append(-radius, 0.0)
        elif i == rings:
            append(0.0, radius)
        else:
            theta = (math.pi / 2.0) * i / rings
            append(-radius * math.cos(theta), radius * math.sin(theta))

    for i in range(rings + 1):
        if i == 0:
            append(length, radius)
        elif i == rings:
            append(length + radius, 0.0)
        else:
            theta = (math.pi / 2.0) * i / rings
            append(length + radius * math.sin(theta), radius * math.cos(theta))

    return points


def capsule_mesh(
    a: Sequence[float],
    b: Sequence[float],
    r: float,
    seg: int = 12,
    rings: int = 4,
) -> Mesh:
    """Build a closed capsule with outward face winding.

    rings counts subdivisions per hemisphere. A zero-length capsule is a
    sphere; coincident equators are merged before vertices are generated.
    """
    if not isinstance(seg, int) or seg < 3:
        raise ValueError("seg must be an integer >= 3")
    if not isinstance(rings, int) or rings < 1:
        raise ValueError("rings must be an integer >= 1")
    radius = float(r)
    if not math.isfinite(radius) or radius < 0.0:
        raise ValueError("radius must be finite and non-negative")

    start = _point3(a)
    end = _point3(b)
    direction = tuple(end[i] - start[i] for i in range(3))
    length = math.hypot(*direction)
    if not math.isfinite(length):
        raise ValueError("capsule length must be finite")
    axis = (
        tuple(value / length for value in direction)
        if length > 0.0
        else (0.0, 0.0, 1.0)
    )
    u, v = _basis(axis)

    verts: list[Vec3] = []
    rows: list[list[int]] = []
    for axial, radial in _profile(length, radius, rings):
        if radial < 1e-9:
            rows.append([len(verts)])
            verts.append(
                tuple(start[i] + axial * axis[i] for i in range(3))
            )
            continue

        indices: list[int] = []
        for j in range(seg):
            angle = 2.0 * math.pi * j / seg
            cosine, sine = math.cos(angle), math.sin(angle)
            indices.append(len(verts))
            verts.append(
                tuple(
                    start[i]
                    + axial * axis[i]
                    + radial * (cosine * u[i] + sine * v[i])
                    for i in range(3)
                )
            )
        rows.append(indices)

    faces: list[tuple] = []
    for lower, upper in zip(rows, rows[1:]):
        if len(lower) == 1 and len(upper) == 1:
            continue
        for j in range(seg):
            following = (j + 1) % seg
            if len(lower) == 1:
                faces.append((lower[0], upper[following], upper[j]))
            elif len(upper) == 1:
                faces.append((lower[j], lower[following], upper[0]))
            else:
                faces.append(
                    (lower[j], lower[following], upper[following], upper[j])
                )

    return verts, faces


def sphere_mesh(
    c: Sequence[float],
    r: float,
    seg: int = 12,
    rings: int = 4,
) -> Mesh:
    return capsule_mesh(c, c, r, seg=seg, rings=rings)


def diamond(
    left: Sequence[float],
    bottom: Sequence[float],
    right: Sequence[float],
    top: Sequence[float],
) -> tuple[list[Vec3], list[tuple[int, int]]]:
    """Return bottom, right, top, left vertices and their perimeter."""
    verts = [_point3(bottom), _point3(right), _point3(top), _point3(left)]
    return verts, [(0, 1), (1, 2), (2, 3), (3, 0)]


def floor_quad(cx: float, cz_b: float, y_b: float, half: float) -> Mesh:
    """Build a horizontal quad from a converted Blender-space centre.

    cx and cz_b are its two horizontal centre components; y_b is height.
    """
    x, y, z = _point3((cx, cz_b, y_b))
    half_size = float(half)
    if not math.isfinite(half_size) or half_size < 0.0:
        raise ValueError("floor half-size must be finite and non-negative")
    verts = [
        (x - half_size, y - half_size, z),
        (x + half_size, y - half_size, z),
        (x + half_size, y + half_size, z),
        (x - half_size, y + half_size, z),
    ]
    return verts, [(0, 1, 2, 3)]


def overlay_geometry(info: dict, opts: dict | None = None) -> dict:
    """Return overlay geometry without modifying frame_info or a scene.

    Absent or incomplete parts produce empty geometry. Invalid numeric
    geometry raises ValueError. No root/facing transform is applied here:
    frame_info overlay positions are already engine-world positions.
    """
    options = {} if opts is None else opts
    seg = options.get("seg", 12)
    rings = options.get("rings", 4)
    geometry = {
        "hit": [],
        "hurt": [],
        "ecb": {"verts": [], "edges": []},
        "floor": {"verts": [], "faces": []},
    }

    for hit in info.get("hitboxes", []) or []:
        if not isinstance(hit, Mapping) or not all(
            key in hit for key in ("slot", "world", "radius")
        ):
            continue
        try:
            centre = _blender_point(hit["world"])
        except KeyError:
            continue
        verts, faces = sphere_mesh(centre, hit["radius"], seg=seg, rings=rings)
        geometry["hit"].append(
            {
                "slot": hit["slot"],
                "active": bool(hit.get("active", True)),
                "verts": verts,
                "faces": faces,
            }
        )

    for hurt in info.get("hurtboxes", []) or []:
        if not isinstance(hurt, Mapping) or not all(
            key in hurt for key in ("a", "b", "radius")
        ):
            continue
        try:
            a = _blender_point(hurt["a"])
            b = _blender_point(hurt["b"])
        except KeyError:
            continue
        verts, faces = capsule_mesh(a, b, hurt["radius"], seg=seg, rings=rings)
        geometry["hurt"].append({"verts": verts, "faces": faces})

    root = info.get("root") or {}
    root_position = root.get("pos") or {}
    root_x = float(root_position.get("x", 0.0))
    root_z = float(root_position.get("z", 0.0))

    ecb = info.get("ecb") or {}
    names = ("bottom", "right", "top", "left")
    if isinstance(ecb, Mapping) and all(name in ecb for name in names):
        try:
            points = {}
            for name in names:
                x, y, _ = _xyz(ecb[name], root_z)
                points[name] = W.to_blender_point((x, y, root_z))
        except KeyError:
            pass
        else:
            verts, edges = diamond(
                points["left"], points["bottom"], points["right"], points["top"]
            )
            geometry["ecb"] = {"verts": verts, "edges": edges}

    if "floorY" in info and info["floorY"] is not None:
        centre = W.to_blender_point((root_x, float(info["floorY"]), root_z))
        verts, faces = floor_quad(
            centre[0], centre[1], centre[2], options.get("floor_half", 30)
        )
        geometry["floor"] = {"verts": verts, "faces": faces}

    return geometry
