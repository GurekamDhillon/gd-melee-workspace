"""In-place posing: show the body animating at the row's start position, not falling or sliding.

The engine's frame data (and so every number in the workbench) is unchanged. Only what is posed and
drawn is shifted, by the root's displacement from where the row started; Show travel turns the shift off.
"""

from __future__ import annotations

from copy import deepcopy


def _root_pos(info):
    root = info.get("root") or {}
    pos = root.get("pos")
    if not isinstance(pos, dict):
        for bone in info.get("bones") or []:
            if bone.get("parent") == -1 and isinstance(bone.get("pos"), dict):
                pos = bone["pos"]
                break
    if not isinstance(pos, dict):
        return None
    return {k: float(pos.get(k, 0.0)) for k in ("x", "y", "z")}


def anchor_of(info):
    """The root position that stays put: the row's first frame."""
    return _root_pos(info) if isinstance(info, dict) else None


def _shift_point(point, d):
    if isinstance(point, dict):
        for k in ("x", "y", "z"):
            if k in point:
                point[k] = float(point[k]) - d[k]


def in_place(info, anchor):
    """A copy of `info` with everything moved so the root sits at `anchor`; `info` itself is untouched."""
    now = _root_pos(info) if isinstance(info, dict) else None
    if now is None or anchor is None:
        return info
    d = {k: now[k] - anchor[k] for k in ("x", "y", "z")}
    if not any(d.values()):
        return info
    out = deepcopy(info)
    for bone in out.get("bones") or []:
        _shift_point(bone.get("pos"), d)
        mtx = bone.get("mtx")
        if isinstance(mtx, list) and len(mtx) >= 12:
            for index, k in ((3, "x"), (7, "y"), (11, "z")):
                mtx[index] = float(mtx[index]) - d[k]
    _shift_point((out.get("root") or {}).get("pos"), d)
    for hit in out.get("hitboxes") or []:
        _shift_point(hit.get("world"), d)
    for hurt in out.get("hurtboxes") or []:
        _shift_point(hurt.get("a"), d)
        _shift_point(hurt.get("b"), d)
    ecb = out.get("ecb")
    if isinstance(ecb, dict):
        for point in ecb.values():
            _shift_point(point, d)
    if out.get("floorY") is not None:
        out["floorY"] = float(out["floorY"]) - d["y"]
    return out
