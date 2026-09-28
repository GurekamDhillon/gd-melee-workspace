"""Inspect local Ultimate Kirby visual assets without copying game data.

Run with the Python bundled with the local Ultimate Blender installation:
  <blender>/5.1/python/bin/python.exe experiment/ultimate-kirby/model/inspect_assets.py
"""

from collections import Counter
import os
from pathlib import Path
import argparse
import json
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
DEPENDENCIES = ROOT / "experiment/tooling/ultimate/profile/blender/scripts/addons/smash-ultimate-blender/dependencies"
sys.path.insert(0, str(DEPENDENCIES))
import ssbh_data_py as ssbh  # noqa: E402

DEFAULT_SOURCE = Path(os.environ.get("GW_ULTIMATE_EXTRACT", str(Path(__file__).resolve().parents[3] / "_local" / "ultimate"))) / 'fighter/kirby'


def inspect(source):
    model = source / "model/body/c00"
    motion = source / "motion/body/c00"
    mesh = ssbh.mesh_data.read_mesh(str(model / "model.numshb"))
    skel = ssbh.skel_data.read_skel(str(model / "model.nusktb"))
    modl = ssbh.modl_data.read_modl(str(model / "model.numdlb"))
    labels = {(e.mesh_object_name, e.mesh_object_subindex): e.material_label for e in modl.entries}
    bones = [b.name for b in skel.bones]
    objects = []
    all_positions = []
    for obj in mesh.objects:
        positions = obj.positions[0].data if obj.positions else np.empty((0, 3))
        all_positions.extend(positions.tolist())
        objects.append({
            "name": obj.name,
            "subindex": obj.subindex,
            "parent_bone": obj.parent_bone_name,
            "material": labels.get((obj.name, obj.subindex)),
            "vertices": len(positions),
            "triangles": len(obj.vertex_indices) // 3,
            "bounds": {"min": positions.min(axis=0).round(3).tolist(), "max": positions.max(axis=0).round(3).tolist()} if len(positions) else None,
            "influence_bones": [i.bone_name for i in obj.bone_influences],
            "uv_sets": [a.name for a in obj.texture_coordinates],
            "colors": [a.name for a in obj.color_sets],
        })
    mins = np.min(all_positions, axis=0).round(4).tolist()
    maxs = np.max(all_positions, axis=0).round(4).tolist()
    wanted = ("wait", "walk", "run", "squat", "jump", "specials")
    clips = sorted(p for p in motion.glob("*.nuanmb") if any(w in p.stem for w in wanted))
    animations = []
    for path in clips:
        anim = ssbh.anim_data.read_anim(str(path))
        animations.append({
            "name": path.stem,
            "frames": anim.final_frame_index + 1,
            "groups": [
                {"type": group.group_type.name, "nodes": len(group.nodes)}
                for group in anim.groups
            ],
        })
    return {
        "source_model": str(model),
        "bones": bones,
        "bone_count": len(bones),
        "object_count": len(objects),
        "objects": objects,
        "bounds": {"min": mins, "max": maxs},
        "modl_entries": len(modl.entries),
        "sampled_animations": animations,
        "totals": {
            "vertices": sum(o["vertices"] for o in objects),
            "triangles": sum(o["triangles"] for o in objects),
            "material_bones": dict(Counter(o["parent_bone"] for o in objects)),
        },
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--out", type=Path, default=ROOT / "_build/tmp/ultimate-kirby-model/asset_report.json")
    args = parser.parse_args()
    result = inspect(args.source)
    target = args.out
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("bone_count", "object_count", "bounds", "totals")}, indent=2))
    print("animation samples", len(result["sampled_animations"]))
    print("wrote", target)
