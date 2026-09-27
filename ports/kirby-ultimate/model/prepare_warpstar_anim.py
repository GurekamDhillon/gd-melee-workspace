"""Decode Ultimate Warp Star Entry's Have/Rot motion for an HSD AnimJoint.

Output poses are game-derived and remain under _build/tmp. Placement is an
unanimated parent so the native host can offset the article to Kirby's spawn.
"""

from pathlib import Path
import argparse
import json
import subprocess

import numpy as np
from scipy.spatial.transform import Rotation


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SOURCE = ROOT / "experiment/tooling/ultimate/workspace/extracted/fighter/kirby/motion/warpstar/c00/j00entry.nuanmb"
DEFAULT_DECODER = ROOT / "experiment/tooling/ultimate/apps/SSBH-JSON/ssbh_data_json.exe"
DEFAULT_OUT = ROOT / "_build/tmp/ultimate-kirby-warpstar"
SCALE = 5.0 / 4.6


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--decoder", type=Path, default=DEFAULT_DECODER)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    decoded = args.out_dir / "warpstar-motion-source.json"
    subprocess.run([str(args.decoder), str(args.source), str(decoded)], check=True)
    source = json.loads(decoded.read_text(encoding="utf-8"))
    frames = round(source["final_frame_index"])
    if frames != 120:
        raise ValueError(f"expected 120-frame Warp Star Entry, got {frames}")
    nodes = {node["name"]: node for group in source["groups"]
             if group["group_type"] == "Transform" for node in group["nodes"]}
    result = {"source": str(args.source), "frames": frames, "scale": SCALE,
              "joint_order": ["Placement", "Have", "Rot"], "joints": {}}
    for name in ("Have", "Rot"):
        track = next(t for t in nodes[name]["tracks"] if t["name"] == "Transform")
        values = track["values"]["Transform"]
        if len(values) != frames + 1:
            raise ValueError(f"expected {frames + 1} poses on {name}, got {len(values)}")
        quats = np.asarray([[v["rotation"][axis] for axis in "xyzw"] for v in values])
        euler = np.unwrap(Rotation.from_quat(quats).as_euler("xyz"), axis=0)
        result["joints"][name] = [{
            "scale": [v["scale"][axis] for axis in "xyz"],
            "rotation": euler[index].tolist(),
            "translation": [SCALE * v["translation"][axis] for axis in "xyz"],
        } for index, v in enumerate(values)]
    output = args.out_dir / "warpstar-poses.json"
    output.write_text(json.dumps(result), encoding="utf-8")
    print(json.dumps({"poses": str(output), "frames": frames,
                      "joints": result["joint_order"]}, indent=2))


if __name__ == "__main__":
    main()
