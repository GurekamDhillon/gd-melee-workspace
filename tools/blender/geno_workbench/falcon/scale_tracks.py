"""Per-clip joint scale, which the .smd animation format cannot carry.

`HsdExport --anim` writes <Clip>.scale.json next to <Clip>.smd when the clip animates any joint's scale
({"frames": N, "joints": {"<joint index>": [[sx, sy, sz] for frame 0..N]}}); Falcon's clips squash and stretch
their leg and arm joints, and the engine multiplies that into the joint's world matrix (all Falcon joints have
JOBJ_CLASSICAL_SCALING, which makes HSD_JObjMakeMatrix build plain S*R*T local matrices, no compensation).
Blender's pose-bone scale is the same quantity: the basis scale applies in the animated joint's own axes,
and with scale inheritance FULL (the default) a child's translation follows its parent's scale just as the
engine's parent * local concatenation does. So the sidecar maps one-to-one onto pose.bones["JOBJ_n"].scale.

Pure Python (no bpy) so the mapping is unit-tested; build_blend.py adds the F-curves.
"""
import json

BONE_PREFIX = "JOBJ_"


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def channels(doc, prefix=BONE_PREFIX):
    """[(data_path, array_index, bone_name, [(frame, value), ...])] for every animated scale axis."""
    out = []
    for key in sorted(doc.get("joints", {}), key=int):
        rows = doc["joints"][key]
        if len(rows) != doc["frames"] + 1:
            raise ValueError("joint %s has %d scale rows, expected %d" % (key, len(rows), doc["frames"] + 1))
        bone = "%s%d" % (prefix, int(key))
        for axis in range(3):
            out.append(('pose.bones["%s"].scale' % bone, axis, bone, [(f, float(row[axis])) for f, row in enumerate(rows)]))
    return out


def rest_channels(animated, frames, joint_count, prefix=BONE_PREFIX):
    """Constant scale-1 curves (two keys, first and last frame) for every joint the clip does not animate.

    Blender leaves a pose bone's un-keyed channel where the previous action put it, so an action that does not
    key a joint's scale would inherit whatever the last played clip left (Falcon's clips scale many joints, the
    rest don't). Keying every joint in every action makes each clip start from the rest scale, as the engine does
    (it resets each joint's SRT to the model's rest before applying a clip). `animated`: joint indices (as
    `channels` emits them) to skip."""
    skip = {int(j) for j in animated}
    out = []
    for joint in range(joint_count):
        if joint in skip:
            continue
        bone = "%s%d" % (prefix, joint)
        for axis in range(3):
            out.append(('pose.bones["%s"].scale' % bone, axis, bone, [(0, 1.0), (max(int(frames), 1), 1.0)]))
    return out
