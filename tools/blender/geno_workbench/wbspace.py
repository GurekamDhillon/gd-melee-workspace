"""Coordinate and calibration math, independent of Blender.

Engine/model space is Y up, forward +Z. Blender authoring space is Z up,
forward -Y. The coordinate conversion is engine (x, y, z) -> (x, -z, y).

Matrices act on column vectors. Engine matrices arrive as row-major 3x4
affine matrices; all functions here use immutable row-major 4x4 matrices.
world_to_model removes the entire root transform, including facing.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

Vec3 = tuple[float, float, float]
Row4 = tuple[float, float, float, float]
Mat4 = tuple[Row4, Row4, Row4, Row4]

C3 = (
    (1.0, 0.0, 0.0),
    (0.0, 0.0, -1.0),
    (0.0, 1.0, 0.0),
)
C4: Mat4 = (
    C3[0] + (0.0,),
    C3[1] + (0.0,),
    C3[2] + (0.0,),
    (0.0, 0.0, 0.0, 1.0),
)

_OLD_SCHEMA = "engine too old: no bone matrices (schema 2 needed)"


class SchemaError(ValueError):
    """frame_info cannot supply the transforms required for posing."""


def mat4_from_12(m: Sequence[float]) -> Mat4:
    """Expand a row-major affine 3x4 matrix without changing its axes."""
    if len(m) != 12:
        raise ValueError("expected 12 values for a row-major 3x4 matrix")
    values = tuple(float(value) for value in m)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("matrix values must be finite")
    return (
        (values[0], values[1], values[2], values[3]),
        (values[4], values[5], values[6], values[7]),
        (values[8], values[9], values[10], values[11]),
        (0.0, 0.0, 0.0, 1.0),
    )


def mul(a: Mat4, b: Mat4) -> Mat4:
    """Return a @ b."""
    return tuple(
        tuple(sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4))
        for i in range(4)
    )


def transpose(a: Mat4) -> Mat4:
    return tuple(tuple(a[j][i] for j in range(4)) for i in range(4))


def det3(a: Mat4) -> float:
    """Return the determinant of the upper-left 3x3 matrix."""
    x0, x1, x2 = a[0][:3]
    y0, y1, y2 = a[1][:3]
    z0, z1, z2 = a[2][:3]
    return (
        x0 * (y1 * z2 - y2 * z1)
        - x1 * (y0 * z2 - y2 * z0)
        + x2 * (y0 * z1 - y1 * z0)
    )


def affine_inverse(a: Mat4) -> Mat4:
    """Invert an affine matrix, including scale and shear."""
    determinant = det3(a)
    if not math.isfinite(determinant):
        raise ValueError("matrix determinant must be finite")
    if abs(determinant) < 1e-12:
        raise ValueError("singular matrix")

    x0, x1, x2 = a[0][:3]
    y0, y1, y2 = a[1][:3]
    z0, z1, z2 = a[2][:3]
    inverse3 = (
        (
            (y1 * z2 - y2 * z1) / determinant,
            (x2 * z1 - x1 * z2) / determinant,
            (x1 * y2 - x2 * y1) / determinant,
        ),
        (
            (y2 * z0 - y0 * z2) / determinant,
            (x0 * z2 - x2 * z0) / determinant,
            (x2 * y0 - x0 * y2) / determinant,
        ),
        (
            (y0 * z1 - y1 * z0) / determinant,
            (x1 * z0 - x0 * z1) / determinant,
            (x0 * y1 - x1 * y0) / determinant,
        ),
    )
    rows = tuple(
        row + (-sum(row[j] * a[j][3] for j in range(3)),)
        for row in inverse3
    )
    return rows + ((0.0, 0.0, 0.0, 1.0),)


def apply_point(m: Mat4, p: Sequence[float]) -> Vec3:
    x, y, z = (float(value) for value in p)
    return tuple(
        m[i][0] * x + m[i][1] * y + m[i][2] * z + m[i][3]
        for i in range(3)
    )


def to_blender_point(p: Sequence[float]) -> Vec3:
    x, y, z = (float(value) for value in p)
    return x, -z, y


def from_blender_point(b: Sequence[float]) -> Vec3:
    bx, by, bz = (float(value) for value in b)
    return bx, bz, -by


def to_blender_matrix(m: Mat4) -> Mat4:
    """Change both the world basis and the matrix's local basis."""
    return mul(mul(C4, m), transpose(C4))


def world_to_model(root_m: Mat4, p: Sequence[float]) -> Vec3:
    """Express an engine-world point in the root joint's local frame."""
    return apply_point(affine_inverse(root_m), p)


def check_schema(info: dict) -> None:
    schema = info.get("schema", 1)
    if (
        not isinstance(schema, (int, float))
        or not math.isfinite(schema)
        or schema < 2
    ):
        raise SchemaError(_OLD_SCHEMA)

    bones = info.get("bones", [])
    if not isinstance(bones, (list, tuple)):
        raise SchemaError("frame_info bones must be a sequence")
    if any(not isinstance(bone, Mapping) or "mtx" not in bone for bone in bones):
        raise SchemaError(_OLD_SCHEMA)


def bone_matrices(info: dict) -> dict[int, Mat4]:
    """Read engine-world matrices; coordinate conversion is explicit."""
    check_schema(info)
    matrices: dict[int, Mat4] = {}
    for bone in info.get("bones", []):
        try:
            joint = int(bone["joint"])
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise SchemaError("frame_info bone has no valid joint index") from exc
        if joint in matrices:
            raise SchemaError(f"frame_info has duplicate joint {joint}")
        try:
            matrices[joint] = mat4_from_12(bone["mtx"])
        except (TypeError, ValueError, OverflowError) as exc:
            raise SchemaError(f"invalid matrix for joint {joint}: {exc}") from exc
    return matrices


def root_matrix(info: dict) -> Mat4:
    root = info.get("root")
    if not isinstance(root, Mapping) or "mtx" not in root:
        raise SchemaError("frame_info has no root")
    try:
        return mat4_from_12(root["mtx"])
    except (TypeError, ValueError, OverflowError) as exc:
        raise SchemaError(f"frame_info root has invalid matrix: {exc}") from exc


@dataclass
class Calibration:
    w0: Mat4
    k: dict[int, Mat4]
    scale: float


def calibrate_offsets(
    engine_rest: dict[int, Mat4],
    blender_rest: dict[int, Mat4],
    root_joint: int,
) -> Calibration:
    """Recover fixed bone-frame offsets from a shared reference pose.

    Both inputs are already in Blender world space. The engine reference
    root defines model axes. The Blender root's rotation belongs to its
    imported bone frame and must remain in K, including for the root bone.

    Consequently the Blender reference placement removes its root origin
    and uniform scale, but retains its root bone rotation as an offset.
    World placement and bone-frame rotation cannot be independently
    identified from a single pair of root matrices without this convention.
    """
    if root_joint not in engine_rest or root_joint not in blender_rest:
        raise ValueError(f"root joint {root_joint} missing from calibration")

    engine_root = engine_rest[root_joint]
    blender_root = blender_rest[root_joint]
    blender_determinant = det3(blender_root)
    if not math.isfinite(blender_determinant):
        raise ValueError("matrix determinant must be finite")
    if abs(blender_determinant) < 1e-12:
        raise ValueError("singular matrix")

    reference_scale = abs(blender_determinant) ** (1.0 / 3.0)
    blender_placement: Mat4 = (
        (reference_scale, 0.0, 0.0, blender_root[0][3]),
        (0.0, reference_scale, 0.0, blender_root[1][3]),
        (0.0, 0.0, reference_scale, blender_root[2][3]),
        (0.0, 0.0, 0.0, 1.0),
    )
    w0 = mul(engine_root, affine_inverse(blender_placement))
    common_joints = sorted(engine_rest.keys() & blender_rest.keys())
    offsets = {
        joint: mul(
            mul(affine_inverse(engine_rest[joint]), w0),
            blender_rest[joint],
        )
        for joint in common_joints
    }
    return Calibration(
        w0=w0,
        k=offsets,
        scale=abs(det3(w0)) ** (1.0 / 3.0),
    )


def target_matrix(engine_blender_m: Mat4, k: Mat4) -> Mat4:
    """Apply an offset. Pose callers must skip mirrored source matrices."""
    return mul(engine_blender_m, k)


def is_mirrored(m: Mat4) -> bool:
    return det3(m) < 0.0
