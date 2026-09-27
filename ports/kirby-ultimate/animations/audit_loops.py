"""Measure first/end visible joint poses in a generated Kirby FigaTree set."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation

import convert_world as W


ROOT = Path(__file__).resolve().parents[3]
VISIBLE_JOINTS = (6, 24, 25, 29, 30, 36, 37, 42, 43)


def world_pose(tree, rest, frame):
    world = []
    for index, joint in enumerate(rest):
        parts = {"rotation": np.asarray(joint["rot"], dtype=float).copy(),
                 "translation": np.asarray(joint["trans"], dtype=float).copy(),
                 "scale": np.asarray(joint["scale"], dtype=float).copy()}
        for track in tree["joints"][index]:
            for part, kinds in W.local.TRACK_TYPE.items():
                if track["type"] in kinds:
                    parts[part][kinds.index(track["type"])] = W.local.F.evaluate(track["keys"], frame)
        matrix = W._srt(parts["translation"], Rotation.from_euler("xyz", parts["rotation"]),
                        parts["scale"])
        parent = joint["parent"]
        world.append((world[parent] @ matrix) if parent >= 0 else matrix)
    return world


def audit(manifest: Path, rows: set[int]):
    doc = json.loads(manifest.read_text())
    joints = json.loads((ROOT / "experiment/brawl-kirby/analysis/melee_model.json").read_text())["PlKbNr.dat"]["joints"]
    result = []
    for entry in doc["animations"]:
        row = entry["row"]
        if row not in rows:
            continue
        _, tree = W.local.F.parse_archive((manifest.parent / entry["file"]).read_bytes())
        first = world_pose(tree, joints, 0)
        last = world_pose(tree, joints, round(tree["frames"]))
        gaps = []
        for index in VISIBLE_JOINTS:
            translation = float(np.linalg.norm(last[index][:3, 3] - first[index][:3, 3]))
            axis = float(np.max(np.linalg.norm(last[index][:3, :3] - first[index][:3, :3], axis=0)))
            gaps.append((index, translation, axis))
        result.append({"row": row, "frames": tree["frames"],
                       "root_delta": (last[1][:3, 3] - first[1][:3, 3]).round(4).tolist(),
                       "max_visible_origin_gap": max(gaps, key=lambda x: x[1]),
                       "max_visible_axis_gap": max(gaps, key=lambda x: x[2])})
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--rows", type=int, nargs="*", default=[2, 7, 8, 9, 13, 16, 295, 296, 297, 298, 299])
    args = parser.parse_args()
    print(json.dumps(audit(args.manifest, set(args.rows)), indent=2))
