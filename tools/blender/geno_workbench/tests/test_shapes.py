import shapes as S
import wbspace as W


def test_sphere_counts_and_bounds():
    v, f = S.sphere_mesh((0, 0, 0), 2.0, seg=12, rings=4)
    assert len(v) == 2 + 7 * 12
    xs = [p[0] for p in v]; zs = [p[2] for p in v]
    assert abs(max(xs) - 2.0) < 1e-6 and abs(min(xs) + 2.0) < 1e-6
    assert all(0 <= i < len(v) for face in f for i in face)


def test_capsule_bounds():
    v, f = S.capsule_mesh((0, 0, 0), (0, 0, 5), 1.0, seg=12, rings=4)
    assert len(v) == 2 + 2 * 4 * 12
    zs = [p[2] for p in v]; xs = [p[0] for p in v]
    assert abs(min(zs) + 1) < 1e-6 and abs(max(zs) - 6) < 1e-6 and abs(max(xs) - 1) < 1e-6


def test_capsule_degenerate_equals_sphere():
    assert len(S.capsule_mesh((1, 1, 1), (1, 1, 1), 1.0)[0]) == len(S.sphere_mesh((1, 1, 1), 1.0)[0])


def test_overlay_geometry_is_in_blender_space():
    info = {"schema": 2, "bones": [], "hitboxes": [{"slot": 1, "active": True, "world": {"x": 1, "y": 2, "z": 3}, "radius": 2.0}],
            "hurtboxes": [{"a": {"x": 0, "y": 0, "z": 0}, "b": {"x": 0, "y": 4, "z": 0}, "radius": 1.0}],
            "ecb": {"bottom": {"x": 0, "y": 0}, "top": {"x": 0, "y": 9}, "left": {"x": -3, "y": 4.5}, "right": {"x": 3, "y": 4.5}},
            "floorY": 0.0, "root": {"pos": {"x": 5, "y": 0, "z": 0}}}
    g = S.overlay_geometry(info, {})
    hit = g["hit"][0]
    assert hit["slot"] == 1 and hit["active"]
    cx = sum(p[0] for p in hit["verts"]) / len(hit["verts"])
    cy = sum(p[1] for p in hit["verts"]) / len(hit["verts"])
    cz = sum(p[2] for p in hit["verts"]) / len(hit["verts"])
    assert abs(cx - 1) < 0.2 and abs(cy + 3) < 0.2 and abs(cz - 2) < 0.2   # (1,2,3) -> (1,-3,2)
    assert len(g["hurt"]) == 1 and len(g["ecb"]["verts"]) == 4 and len(g["ecb"]["edges"]) == 4
    assert all(abs(p[2] - 0.0) < 1e-9 for p in g["floor"]["verts"])        # floorY 0 -> Blender z 0
    zs = [p[2] for p in g["ecb"]["verts"]]
    assert min(zs) == 0 and max(zs) == 9


def test_overlay_geometry_tolerates_missing_parts():
    g = S.overlay_geometry({"schema": 2}, {})
    assert g["hit"] == [] and g["hurt"] == [] and g["ecb"]["verts"] == []


def test_capsule_has_closed_surface_for_oblique_axis():
    import math
    a, b = (2.0, -3.0, 4.0), (-1.0, 2.0, 7.0)
    v, f = S.capsule_mesh(a, b, 0.5, seg=8, rings=3)
    edge_uses = {}
    for face in f:
        for j, first in enumerate(face):
            second = face[(j + 1) % len(face)]
            edge = tuple(sorted((first, second)))
            edge_uses[edge] = edge_uses.get(edge, 0) + 1
    assert edge_uses and all(count == 2 for count in edge_uses.values())
    assert len(v) - len(edge_uses) + len(f) == 2

    direction = tuple(b[i] - a[i] for i in range(3))
    length = math.hypot(*direction)
    axis = tuple(value / length for value in direction)
    axial = [sum((p[i] - a[i]) * axis[i] for i in range(3)) for p in v]
    assert abs(min(axial) + 0.5) < 1e-9
    assert abs(max(axial) - (length + 0.5)) < 1e-9
