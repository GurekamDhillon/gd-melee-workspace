"""Build a minimal Ultimate Kirby c00 mesh on Melee Kirby's existing joint tree.

The output is an intermediate description consumed by kbbuild. It contains no
textures or model bytes and stays in the ignored build directory.
"""

import os
from pathlib import Path
import argparse
import json
import struct
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "experiment/tooling/ultimate/profile/blender/scripts/addons/smash-ultimate-blender/dependencies"))
sys.path.insert(0, str(ROOT / "experiment/brawl-kirby/tools/model"))
sys.path.insert(0, str(ROOT / "tools/mex_port"))
import ssbh_data_py as ssbh  # noqa: E402
import melee_skel  # noqa: E402
import mex_hsd  # noqa: E402

DEFAULT_SOURCE = Path(os.environ.get("GW_ULTIMATE_EXTRACT", str(Path(__file__).resolve().parents[3] / "_local" / "ultimate"))) / 'fighter/kirby/model/body/c00'
DEFAULT_OUT = ROOT / "_build/tmp/ultimate-kirby-model/mesh.json"
WORLD_REST_SCALE = 5.0 / 4.6

# Melee Kirby DFS JObj indices, verified against the Brawl Kirby bone map.
# Ultimate's extra face controls are folded to the closest Melee control.
BONE_MAP = {
    "Trans": 1, "Rot": 2, "Hip": 4, "Waist": 5, "Bust": 6,
    "Neck": 6, "Head": 6, "Body": 6,
    "Mouth1": 8, "MouthLc": 11, "MouthRc": 16,
    "MouthLd": 12, "MouthD1": 21, "MouthD2": 21,
    "MouthRd": 17, "MouthLa1": 13, "Cheek": 9,
    "MouthLb": 14, "MouthRb": 19, "MouthRa1": 18,
    "Puff": 10, "MouthLe": 15, "MouthRe": 20,
    "ClavicleC": 6, "ClavicleL": 22, "ShoulderL": 24,
    "ArmL": 25, "HandL": 26, "HaveL": 26,
    "ClavicleR": 27, "ShoulderR": 29,
    "ArmR": 30, "HandR": 31, "HaveR": 31,
    "LegC": 5, "LegL": 33, "KneeL": 34,
    "FootL": 36, "ToeL": 37, "LegR": 39,
    "KneeR": 40, "FootR": 42, "ToeR": 43,
    "Throw": 44, "FreeAttach": 44, "WeaponAttach": 44,
    "MouthL2": 12, "Mouth2": 8, "Headdress": 6,
    "EyeblinkL1": 6, "EyeblinkL2": 6,
    "EyeblinkR1": 6, "EyeblinkR2": 6,
}


def load_melee_rest(path):
    """Read any vanilla Kirby colour's DFS skeleton and rest world transforms."""
    archive = mex_hsd.Archive(path.read_bytes()).relocate(0)
    symbols = [name for name, _ in archive.publics if name.endswith("_Share_joint")]
    if len(symbols) != 1:
        raise ValueError(f"expected one Kirby joint symbol in {path}: {symbols}")
    root = archive.public(symbols[0])
    value = lambda offset: struct.unpack(">f", archive.data[offset:offset + 4])[0]
    joints = []

    def walk(offset, parent):
        while offset:
            joint = {
                "parent": parent,
                "rot": [value(offset + 0x14 + 4 * k) for k in range(3)],
                "scale": [value(offset + 0x20 + 4 * k) for k in range(3)],
                "trans": [value(offset + 0x2C + 4 * k) for k in range(3)],
            }
            index = len(joints)
            local = melee_skel.srt(joint["scale"], joint["rot"], joint["trans"])
            joint["world"] = local if parent < 0 else joints[parent]["world"] @ local
            joints.append(joint)
            child = archive.u32(offset + 8)
            if child:
                walk(child, index)
            offset = archive.u32(offset + 0xC)

    walk(root, -1)
    return joints


def main(source, stock_costume, output, deform_face=False, rigid_limbs=False,
         preserve_world_rest=True, stock_face_patch=False):
    mesh = ssbh.mesh_data.read_mesh(str(source / "model.numshb"))
    skel = ssbh.skel_data.read_skel(str(source / "model.nusktb"))
    melee = load_melee_rest(stock_costume)
    assert len(melee) == 46 and len(skel.bones) == 53
    assert set(BONE_MAP) == {b.name for b in skel.bones}
    world = {b.name: np.asarray(skel.calculate_world_transform(b)).T for b in skel.bones}
    transforms = {
        name: melee[j]["world"] @ np.linalg.inv(world[name])
        for name, j in BONE_MAP.items()
    }
    # The default and puffed bodies are separate Melee visibility states.
    # FaceN is Ultimate's normal expression (EyeL6, open eye atlas).
    # Bodybig2 is a different expression (EyeL3) with shifted eye UVs.
    selection = [(3, "puffed-body"), (13, "normal-body")]
    if not stock_face_patch:
        selection.append((6, "eye"))
    selection.extend([(0, "arms"), (1, "feet")])
    targets = {"puffed-body": (0 if stock_face_patch else 1,),
               "normal-body": (3 if stock_face_patch else 4,), "eye": (0, 3),
                 "arms": (6, 18), "feet": (7, 19)}
    result = {str(i): {"tris": [], "source": role} for _, role in selection for i in targets[role]}
    stats = {"source_objects": [], "triangles": {}, "missing_weights": 0,
             "body_binding": "face controls" if deform_face else "rigid Body joint",
             "limb_binding": "rigid per side" if rigid_limbs else "weighted Melee joints",
             "geometry_space": "source world rest" if preserve_world_rest else "mapped bone local rest",
             "world_rest_scale": WORLD_REST_SCALE if preserve_world_rest else None,
             "stock_face_patch": stock_face_patch,
             "trimmed_vertices": 0, "max_weight_dropped": 0.0}
    for obj_index, role in selection:
        obj = mesh.objects[obj_index]
        pos = obj.positions[0].data[:, :3]
        normal = obj.normals[0].data[:, :3]
        if obj.parent_bone_name:
            parent_world = world[obj.parent_bone_name]
            pos = (np.c_[pos, np.ones(len(pos))] @ parent_world.T)[:, :3]
            normal = normal @ parent_world[:3, :3].T
        uv = obj.texture_coordinates[0].data[:, :2]
        influences = [[] for _ in range(len(pos))]
        if obj.parent_bone_name:
            influences = [[(obj.parent_bone_name, 1.0)] for _ in range(len(pos))]
        for influence in obj.bone_influences:
            for w in influence.vertex_weights:
                influences[w.vertex_index].append((influence.bone_name, float(w.vertex_weight)))
        assert all(influences), (obj.name, role)
        indices = obj.vertex_indices.tolist()
        for t in range(0, len(indices), 3):
            triangle = []
            side_votes = {"L": 0.0, "R": 0.0}
            for vertex_index in indices[t:t + 3]:
                weighted = influences[vertex_index]
                if role in ("puffed-body", "normal-body") and not deform_face:
                    weighted = [("Body", 1.0)]
                if preserve_world_rest:
                    # Source rigid-parent meshes are already expanded to model
                    # world space above. Preserve that facing orientation;
                    # mapped Melee bone axes differ, especially Body, whose
                    # Ultimate rest matrix cyclically permutes XYZ.
                    p = WORLD_REST_SCALE * pos[vertex_index]
                    n = normal[vertex_index]
                else:
                    blend = sum((weight * transforms[bone] for bone, weight in weighted), np.zeros((4, 4)))
                    p = (blend @ np.r_[pos[vertex_index], 1.0])[:3]
                    n = blend[:3, :3] @ normal[vertex_index]
                n /= np.linalg.norm(n) or 1.0
                mapped = {}
                for bone, weight in weighted:
                    j = BONE_MAP[bone]
                    mapped[j] = mapped.get(j, 0.0) + weight
                    if j in (22, 24, 25, 26, 33, 34, 36, 37): side_votes["L"] += weight
                    if j in (27, 29, 30, 31, 39, 40, 42, 43): side_votes["R"] += weight
                weights = sorted(mapped.items(), key=lambda x: -x[1])
                if len(weights) > 4:
                    stats["trimmed_vertices"] += 1
                    stats["max_weight_dropped"] = max(stats["max_weight_dropped"], sum(w for _, w in weights[4:]))
                    weights = weights[:4]
                total = sum(w for _, w in weights)
                weights = [[j, round(w / total, 2)] for j, w in weights if w / total >= 0.005]
                weights[0][1] = round(1.0 - sum(w for _, w in weights[1:]), 2)
                triangle.append({"p": p.round(6).tolist(), "n": n.round(6).tolist(),
                                 "uv": uv[vertex_index].round(6).tolist(), "w": weights})
            if role == "eye":
                # Melee has separate visibility groups for puffed and normal.
                for d in targets[role]:
                    result[str(d)]["tris"].append(triangle)
            else:
                d = targets[role][0 if side_votes["L"] >= side_votes["R"] else -1]
                if rigid_limbs and role in ("arms", "feet"):
                    # Preserve the weighted rest-space surface from above,
                    # but let one semantic Melee joint drive each full limb.
                    # This isolates envelope deformation from pose transfer.
                    joint = {6: 25, 18: 30, 7: 36, 19: 42}[d]
                    for vertex in triangle:
                        vertex["w"] = [[joint, 1.0]]
                result[str(d)]["tris"].append(triangle)
        stats["source_objects"].append({"name": obj.name, "subindex": obj.subindex,
                                        "parent_bone": obj.parent_bone_name,
                                        "role": role, "triangles": len(indices) // 3})
    stats["triangles"] = {k: len(v["tris"]) for k, v in result.items()}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"dobjs": result, "stats": stats}), encoding="utf-8")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--stock-costume", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--deform-face", action="store_true",
                        help="keep Ultimate face weights mapped to Melee mouth joints")
    parser.add_argument("--rigid-limbs", action="store_true",
                        help="bind each arm/foot part to one semantic Melee joint")
    parser.add_argument("--preserve-world-rest", dest="preserve_world_rest", action="store_true",
                        default=True, help="preserve Ultimate mesh world facing when mapping to Melee rig (default)")
    parser.add_argument("--mapped-bone-local", dest="preserve_world_rest", action="store_false",
                        help="diagnostic: map mesh to Melee bone-local rest")
    parser.add_argument("--stock-face-patch", action="store_true",
                        help="temporary control: keep Melee face patch and replace body only")
    args = parser.parse_args()
    main(args.source, args.stock_costume, args.out, args.deform_face,
         args.rigid_limbs, args.preserve_world_rest, args.stock_face_patch)
