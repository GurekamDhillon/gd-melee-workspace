"""Headless Blender: add Palm Skip to a generated Pip starter, without converter edits."""
import json
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/geno/artist/blender"))
import actions as AC
import skeleton as SK

params = json.loads((Path(__file__).parent / "params.json").read_text())
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
bones = SK.build(params["proportions"], params["names"])
rig = AC.Rig(arm, bones, dict(SK.DEFAULT_PROPORTIONS, **params["proportions"]))


def pose(frame, frames, proportions):
    # Two distinct open-palm reaches, then a long recovery. No root translation.
    def pulse(center, before, after):
        span = before if frame < center else after
        return max(0.0, 1.0 - abs(frame - center) / span)
    reach = max(pulse(6, 6, 4), pulse(14, 4, 10))
    return {"upper_arm.R": {"f": 20 + 78 * reach, "o": -15},
            "lower_arm.R": {"f": -25 + 25 * reach},
            "upper_arm.L": {"f": 28, "o": -18},
            "lower_arm.L": {"f": 45}, "spine": {"f": 8 * reach}}


action = AC.make_action(rig, "PalmSkip", 41, pose, hit=[6, 14])
action["geno_rows"] = "SpecialN"
# Artist row mapping in fighter.json selects this clip for SpecialN.
arm.animation_data.action = bpy.data.actions.get("Wait")
bpy.ops.wm.save_as_mainfile(filepath=bpy.data.filepath)
print("PIP PalmSkip: 41 sampled keys, hit poses 6/14, duration 40 frames")
