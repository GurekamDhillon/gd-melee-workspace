"""hand_layer.py - the hand-animation file format (pure Python + numpy/scipy, no Blender).

A hand file holds ONLY the artist's own work: per row, per deform bone, per frame, the DELTA the artist added on top of a base.
No source clip is copied into it (nothing XV2-, Nintendo- or disc-derived), so it is safe to commit and diff. The converter
(ports/goku-xv2/tools/xv2_to_artist.py) applies it as the last step of its animation pass; nothing the converter does ever
writes to it, and rerunning the converter / Stage A never loses it.

    {
      "schema": "geno-hand/1",
      "fighter": "Goku",
      "fps": 60,
      "clips": {
        "Attack11": {
          "mode": "layer",          # layer: delta on top of the converted clip of the same row;  replace: delta on top of the REST pose
          "frames": 24,             # authored length; the row keeps its own length (shorter: last delta held, longer: cropped, both reported)
          "note": "jab1: longer wind-up",
          "bones": {"b_L_Arm1": {"rot": [[x, y, z, w], ...], "loc": [[x, y, z], ...]}},   # rot/loc optional; omitted bones are untouched (layer) or at rest (replace)
          "auth": {"b_L_Arm1": {"dq": [[w, x, y, z], ...], "dl": [[x, y, z], ...]}}      # Blender-side basis deltas, used only to reload the clip into the rig
        }
      }
    }

rot  : unit quaternion D (xyzw) in the bone's glTF local frame; the bone ends at  base_rotation * D.
loc  : translation delta in the bone's glTF local frame (only the hips and translation bones carry translation); base_translation + loc.
base : the converted row (mode "layer") or the rest pose (mode "replace").
"""
from __future__ import annotations

import json
import math
from pathlib import Path

SCHEMA = "geno-hand/1"
MODES = ("layer", "replace")
EPS_ROT = 5e-4      # radians; a bone whose rotation delta never exceeds this is not stored
EPS_LOC = 1e-4


def empty(fighter, fps=60):
    return {"schema": SCHEMA, "fighter": fighter, "fps": fps, "clips": {}}


def load(path):
    path = Path(path)
    if not path.is_file():
        return None
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    validate(doc)
    return doc


def save(path, doc):
    validate(doc)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(doc, indent=1, sort_keys=True) + "\n"
    if path.is_file() and path.read_text(encoding="utf-8") == text:
        return path          # keep the mtime: an unchanged hand file must not trigger a Stage A rebuild
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    return path


def _finite(rows, width, label):
    for r in rows:
        if len(r) != width or not all(isinstance(v, (int, float)) and math.isfinite(v) for v in r):
            raise ValueError(f"{label}: expected {width} finite numbers per frame")


def validate(doc):
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA:
        raise ValueError(f"hand file: schema must be {SCHEMA}")
    for row, clip in doc.get("clips", {}).items():
        if not row or len(row) > 31:
            raise ValueError(f"hand clip name '{row}': 1..31 characters")
        if clip.get("mode") not in MODES:
            raise ValueError(f"{row}: mode must be one of {MODES}")
        n = clip.get("frames")
        if not isinstance(n, int) or n < 1:
            raise ValueError(f"{row}: frames must be a positive integer")
        for bone, ch in clip.get("bones", {}).items():
            if "rot" in ch:
                if len(ch["rot"]) != n:
                    raise ValueError(f"{row}/{bone}: rot has {len(ch['rot'])} frames, clip has {n}")
                _finite(ch["rot"], 4, f"{row}/{bone}/rot")
            if "loc" in ch:
                if len(ch["loc"]) != n:
                    raise ValueError(f"{row}/{bone}: loc has {len(ch['loc'])} frames, clip has {n}")
                _finite(ch["loc"], 3, f"{row}/{bone}/loc")
    return doc


def _fit(array, count):
    """n x k -> count x k: crop, or hold the last frame."""
    import numpy as np
    a = np.asarray(array, dtype=float)
    if len(a) >= count:
        return a[:count]
    return np.concatenate([a, np.repeat(a[-1:], count - len(a), axis=0)])


def sparse_bones(rot, loc, tol_rot=EPS_ROT, tol_loc=EPS_LOC):
    """Per-bone arrays (xyzw rot N x 4, loc N x 3, either may be None) -> the JSON "bones" dict, keeping only bones the artist moved."""
    import numpy as np
    out = {}
    for bone in sorted(set(rot) | set(loc)):
        entry = {}
        r = rot.get(bone)
        if r is not None:
            r = np.asarray(r, float)
            ang = 2 * np.arctan2(np.linalg.norm(r[:, :3], axis=1), np.abs(r[:, 3]))   # not arccos(w): ill-conditioned near identity
            if ang.max() > tol_rot:
                entry["rot"] = [[round(float(v), 6) for v in row] for row in r]
        l = loc.get(bone)
        if l is not None:
            l = np.asarray(l, float)
            if np.abs(l).max() > tol_loc:
                entry["loc"] = [[round(float(v), 6) for v in row] for row in l]
        if entry:
            out[bone] = entry
    return out


def apply_clip(clip, *, count, rotations, rest_q, hips, root, hips_bone, root_bone, rest_hips):
    """Apply one hand clip to a converted row, in place where possible.

    rotations : {bone: (count, 4) xyzw}   rest_q: {bone: xyzw}   hips: (count, 3)   root: (count, 3) or None
    Returns (hips, root, report). A "replace" clip starts every bone from the rest pose; "layer" starts from what the converter made.
    """
    import numpy as np
    from scipy.spatial.transform import Rotation as R
    mode = clip["mode"]
    n = clip["frames"]
    notes = []
    if n != count:
        notes.append(f"authored {n} frames, row has {count}: {'last delta held' if n < count else 'cropped'}")
    if mode == "replace":
        for bone in rotations:
            if bone in rest_q:
                rotations[bone] = np.repeat(np.asarray(rest_q[bone], float)[None, :], count, axis=0)
        hips = np.repeat(np.asarray(rest_hips, float)[None, :], count, axis=0)
        root = None
    moved, unknown, dropped = [], [], []
    for bone, ch in clip.get("bones", {}).items():
        if "rot" in ch:
            if bone not in rotations:
                unknown.append(bone)
            else:
                base = rotations[bone]
                out = (R.from_quat(base) * R.from_quat(_fit(ch["rot"], count))).as_quat()
                rotations[bone] = out
                moved.append(bone)
        if "loc" in ch:
            delta = _fit(ch["loc"], count)
            if bone == hips_bone:
                hips = hips + delta
            elif bone == root_bone:
                root = (np.zeros((count, 3)) if root is None else root) + delta
            else:
                dropped.append(bone)
    report = {"mode": mode, "frames": n, "bones": len(clip.get("bones", {})), "rotated": sorted(moved), "notes": notes}
    if unknown:
        report["unknown_bones"] = sorted(unknown)
    if dropped:
        report["translation_dropped"] = sorted(dropped)
    return hips, root, report
