"""bpy helpers shared by both render workers: fighter meshes, joint readout, camera placement.

Imported by blender_render.py (Blender 3.5.1, CSProject backend) and own_render.py
(current Blender, own backend); keep it to API that both versions have.
"""
import math
from pathlib import Path
import sys

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from tools.csp import framing

import bpy
from mathutils import Matrix, Vector


def fighter_meshes(objects):
    """The skinned, textured body meshes. Helper meshes (a bone-shape icosphere at the
    origin, say) must not enter bounds: one such 2-unit sphere under Goku's feet made the
    CSProject path float him a few units off the floor."""
    meshes = [o for o in objects if o.type == 'MESH' and not o.hide_render]
    skinned = [o for o in meshes if any(m.type == 'ARMATURE' for m in o.modifiers) or o.parent_type == 'BONE'
               or o.vertex_groups]
    textured = [o for o in skinned if any(m is not None for m in o.data.materials)]
    return textured or skinned or meshes


def world_points(meshes):
    """World-space vertices of the evaluated (posed) meshes."""
    graph = bpy.context.evaluated_depsgraph_get()
    points = []
    for obj in meshes:
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        try:
            matrix = evaluated.matrix_world
            points.extend(tuple(matrix @ v.co) for v in mesh.vertices)
        finally:
            evaluated.to_mesh_clear()
    return points


def bone_point(rig, name):
    bone = rig.pose.bones.get(name)
    if bone is None:
        return None
    return tuple(rig.matrix_world @ bone.head)


def joint_points(rig, roles):
    """role -> world point for the roles the crop rules use; absent bones are left out."""
    found = {}
    for role, key in framing.ANCHOR_ROLES.items():
        name = roles.get(role)
        point = bone_point(rig, name) if name else None
        if point is not None:
            found[key] = point
    return found


def skeleton_frame_inputs(rig, roles, meshes):
    """(anchors, mesh points, facing) for the posed fighter."""
    bpy.context.view_layer.update()
    joints = joint_points(rig, roles)
    points = world_points(meshes)
    anchors = framing.anchor_points(joints, points)
    facing = None
    for left, right in (('leg_l', 'leg_r'), ('sh_l', 'sh_r')):
        if left in joints and right in joints:
            facing = framing.facing_from_sides(joints[left], joints[right])
            break
    if facing is None and all(k in joints for k in ('foot_l', 'toe_l', 'foot_r', 'toe_r')):
        facing = framing.facing_from_feet([joints['foot_l'], joints['foot_r']], [joints['toe_l'], joints['toe_r']])
    return anchors, points, facing


def matrix_for(location, basis):
    rotation = Matrix(framing.rotation_matrix(basis)).to_4x4()
    return Matrix.Translation(Vector(location)) @ rotation


def jsonable(plan):
    return {k: ([round(x, 5) for x in v] if isinstance(v, tuple) else v) for k, v in plan.items()
            if k not in ('look', 'up', 'right')}
