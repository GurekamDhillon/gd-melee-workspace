"""hurt.py - hurtbox capsules and the ECB for a Fighter: taken from the art when it declares them, else generated from the skeleton.

ENGINE: 1..15 capsules, each on a joint with joint-local endpoints a, b and a radius (pc/platform/geno_define_registry.inc gn_plan_parse).
The ECB is NOT read by the engine today (geno.md 22.4 "Open": ECB offsets are the donor's numbers); plan.json keeps it for the future.
Generated capsules are proposals sized from the mesh: check them in the LAB (hurtbox display, docs/geno-artist-spec.md section 9).
"""
import numpy as np

from . import model as M

HEIGHT = {"head": "high", "chest": "high", "torso": "mid", "upper_arm": "mid", "lower_arm": "mid", "hand": "mid",
          "upper_leg": "low", "lower_leg": "low", "foot": "low"}


def _pos(b):
    return b.world[:3, 3].copy()


def _auto_slots(f):
    rb = f.role_bone
    slots = []

    def add(id_, bone, a, b, kind):
        slots.append({"id": id_, "bone": bone, "a": a, "b": b, "height": HEIGHT[kind], "grabbable": True})

    head = rb.get("head")
    if head:
        top = rb.get("head_top")
        a = _pos(head)
        if top:
            b = _pos(top)
        else:
            b = a + np.array([0, 2.0, 0])
        add("head", head.name, a, b, "head")
    chest = rb.get("chest") or rb.get("spine")
    neck = rb.get("neck") or head
    if chest and neck:
        add("chest", chest.name, _pos(chest), _pos(neck), "chest")
    hips = rb.get("hips")
    if hips:
        up = rb.get("spine") or chest
        b = _pos(up) if up and up is not hips else _pos(hips) + np.array([0, 1.0, 0])
        add("torso", hips.name, _pos(hips), b, "torso")
    for s in ("L", "R"):
        ua, la, hd = rb.get("upper_arm." + s), rb.get("lower_arm." + s), rb.get("hand." + s)
        ul, ll, ft, toe = rb.get("upper_leg." + s), rb.get("lower_leg." + s), rb.get("foot." + s), rb.get("toe." + s)
        if ua and la:
            add("upper_arm_" + s, ua.name, _pos(ua), _pos(la), "upper_arm")
        if la and hd:
            add("lower_arm_" + s, la.name, _pos(la), _pos(hd), "lower_arm")
        elif la:
            d = _pos(la) - _pos(ua) if ua else np.array([0, -1.0, 0])
            add("lower_arm_" + s, la.name, _pos(la), _pos(la) + d, "lower_arm")
        if hd:
            kids = [b for b in f.bones if b.parent == hd.index and b.role in ("fingers." + s, "thumb." + s)]
            if kids:
                end = _pos(kids[0])
            else:
                d = _pos(hd) - _pos(la) if la else np.array([0, -1.0, 0])
                end = _pos(hd) + 0.5 * d
            add("hand_" + s, hd.name, _pos(hd), end, "hand")
        if ul and ll:
            add("upper_leg_" + s, ul.name, _pos(ul), _pos(ll), "upper_leg")
        if ll and ft:
            add("lower_leg_" + s, ll.name, _pos(ll), _pos(ft), "lower_leg")
        if ft:
            end = _pos(toe) if toe else _pos(ft) + np.array([0, 0, 1.5])
            add("foot_" + s, ft.name, _pos(ft), end, "foot")
    return slots


def hurtboxes(f, joints):
    given = f.hurtboxes_given
    if given:
        out = []
        for h in given:
            out.append({"id": h["id"], "bone": h["bone"], "a": list(h["a"]), "b": list(h["b"]), "radius": float(h["radius"]),
                        "height": h.get("height", "mid"), "grabbable": bool(h.get("grabbable", True))})
        return out
    slots = _auto_slots(f)
    m = M.mesh(f)
    pos, jts, wts = m["pos"], m["jts"].astype(int), m["wts"]
    dom = np.take_along_axis(jts, np.argmax(wts, axis=1)[:, None], axis=1)[:, 0]
    idx_of = {b.name: b.index for b in f.bones}
    out = []
    for s in slots[:15]:
        a, b = s["a"], s["b"]
        sel = pos[dom == idx_of[s["bone"]]]
        r = 0.9
        if len(sel):
            ab = b - a
            L2 = float(ab @ ab) or 1.0
            t = np.clip(((sel - a) @ ab) / L2, 0, 1)
            d = np.linalg.norm(sel - (a + t[:, None] * ab), axis=1)
            r = max(0.5, float(np.percentile(d, 75)) * 0.95)
        out.append({"id": s["id"], "bone": s["bone"], "a": [float(x) for x in a], "b": [float(x) for x in b], "radius": round(r, 3),
                    "height": s["height"], "grabbable": True})
    return out


def ecb(f):
    given = f.ecb
    if given:
        out = {}
        for k, v in given.items():
            if k == "notes":
                continue
            out[k] = v if not isinstance(v, dict) else {kk: (vv * f.scale if isinstance(vv, (int, float)) else vv) for kk, vv in v.items()}
        return out
    m = M.mesh(f)
    top = float(m["pos"][:, 1].max())
    half = float(np.abs(m["pos"][:, 0]).max())
    half = min(max(half * 0.55, 2.0), 4.0)
    st = {"top": round(top, 3), "bottom": 0.0, "left": -round(half, 3), "right": round(half, 3), "side_height": round(top * 0.47, 3)}
    cr = dict(st, top=round(top * 0.55, 3), side_height=round(top * 0.27, 3))
    return {"anchor_bone": f.role_bone["translation"].name, "standing": st, "crouch": cr, "aerial": dict(st)}
