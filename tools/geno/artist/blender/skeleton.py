"""skeleton.py - the Geno export skeleton as data (pure Python; Blender-side scripts and the tests both import it).

Authoring space is Blender's: Z up, the character FACES -Y, its LEFT is +X, 1 unit = 1 Melee unit, soles at z=0.
(The glTF exporter's "+Y Up" maps this to glTF Y-up facing +Z, left +X: the engine's model space. docs/geno-artist-spec.md section 2.)

PROPORTIONS adjust the build; NAMES renames bones (the role stays). Every bone is (name, parent, head, tail, role, deform).
"""
import copy

DEFAULT_PROPORTIONS = {
    "ankle_h": 1.25,        # sole to ankle
    "hip_h": 5.4,           # sole to hip joint (leg length = hip_h)
    "torso_h": 3.4,         # hip joint to base of the neck
    "neck_h": 0.6,
    "head_h": 2.8,
    "shoulder_w": 1.9,      # centre line to shoulder joint
    "hip_w": 1.05,          # centre line to hip joint
    "upper_arm_len": 1.9,
    "lower_arm_len": 1.8,
    "hand_len": 0.8,
    "foot_len": 2.4,        # ankle to toe tip, forward
    "arm_angle_deg": 38,    # A-pose: arms this far from vertical
    "thickness": 1.0,       # scales every limb/torso radius
    "head_r": 1.6,
    "torso_w": 1.7,         # half width of the chest
    "torso_d": 1.2,         # half depth
}

# canonical bone name == role id, so a skeleton built with these names needs no role table at all
ROLE_IDS = ["root", "translation", "hips", "spine", "chest", "neck", "head", "head_top",
            "shoulder.L", "upper_arm.L", "lower_arm.L", "hand.L", "upper_leg.L", "lower_leg.L", "foot.L", "toe.L",
            "shoulder.R", "upper_arm.R", "lower_arm.R", "hand.R", "upper_leg.R", "lower_leg.R", "foot.R", "toe.R",
            "item_socket.R", "grab_anchor", "victim_anchor", "camera_focus", "shield_origin", "reflect_origin", "absorb_origin"]

SOCKET_ROLES = ["item_socket.R", "grab_anchor", "victim_anchor", "camera_focus", "shield_origin", "reflect_origin", "absorb_origin", "head_top"]


def build(prop=None, names=None):
    """-> list of bone dicts. prop overrides DEFAULT_PROPORTIONS; names maps role id -> bone name."""
    import math
    p = dict(DEFAULT_PROPORTIONS)
    p.update(prop or {})
    names = names or {}
    bones = []

    def add(role, parent, head, tail, deform=True):
        bones.append({"role": role, "name": names.get(role, role), "parent": parent, "head": tuple(head), "tail": tuple(tail), "deform": deform})

    hip, th = p["hip_h"], p["torso_h"]
    neck0 = hip + th
    add("root", None, (0, 0, 0), (0, 0, 0.6), False)
    add("translation", "root", (0, 0, 0), (0, 0, 0.5), False)
    add("hips", "translation", (0, 0, hip), (0, 0, hip + 0.18 * th))
    add("spine", "hips", (0, 0, hip + 0.18 * th), (0, 0, hip + 0.5 * th))
    add("chest", "spine", (0, 0, hip + 0.5 * th), (0, 0, neck0))
    add("neck", "chest", (0, 0, neck0), (0, 0, neck0 + p["neck_h"]))
    add("head", "neck", (0, 0, neck0 + p["neck_h"]), (0, 0, neck0 + p["neck_h"] + p["head_h"]))
    top = neck0 + p["neck_h"] + p["head_h"]
    add("head_top", "head", (0, 0, top + 0.2), (0, 0, top + 0.6), False)
    sh_z = neck0 - 0.4
    ang = math.radians(p["arm_angle_deg"])
    for s, sx in (("L", 1), ("R", -1)):
        sw = p["shoulder_w"]
        add("shoulder." + s, "chest", (0.3 * sx, 0, sh_z), (sw * sx, 0, sh_z))
        ua, la, hl = p["upper_arm_len"], p["lower_arm_len"], p["hand_len"]
        d = (math.sin(ang) * sx, 0, -math.cos(ang))
        e1 = (sw * sx + d[0] * ua, 0, sh_z + d[2] * ua)
        e2 = (e1[0] + d[0] * la, 0, e1[2] + d[2] * la)
        e3 = (e2[0] + d[0] * hl, 0, e2[2] + d[2] * hl)
        add("upper_arm." + s, "shoulder." + s, (sw * sx, 0, sh_z), e1)
        add("lower_arm." + s, "upper_arm." + s, e1, e2)
        add("hand." + s, "lower_arm." + s, e2, e3)
        hw = p["hip_w"]
        knee = p["ankle_h"] + (hip - p["ankle_h"]) * 0.5
        add("upper_leg." + s, "hips", (hw * sx, 0, hip), (hw * sx, 0, knee))
        add("lower_leg." + s, "upper_leg." + s, (hw * sx, 0, knee), (hw * sx, 0, p["ankle_h"]))
        add("foot." + s, "lower_leg." + s, (hw * sx, 0, p["ankle_h"]), (hw * sx, -p["foot_len"] * 0.62, 0.55))
        add("toe." + s, "foot." + s, (hw * sx, -p["foot_len"] * 0.62, 0.55), (hw * sx, -p["foot_len"], 0.45))
    hand_r = [b for b in bones if b["role"] == "hand.R"][0]
    hx, hy, hz = hand_r["head"]
    add("item_socket.R", "hand.R", (hx - 0.1, -0.2, hz - 0.2), (hx - 0.1, -0.6, hz - 0.2), False)
    add("grab_anchor", "chest", (0, -(p["torso_d"] + 1.6), hip + 0.35 * th), (0, -(p["torso_d"] + 1.6), hip + 0.35 * th + 0.5), False)
    add("victim_anchor", "hips", (0, 0, hip + 0.1), (0, 0, hip + 0.5), False)
    add("camera_focus", "chest", (0, 0, hip + 0.5 * th), (0, 0, hip + 0.5 * th + 0.4), False)
    add("shield_origin", "translation", (0, 0, hip - 0.4), (0, 0, hip), False)
    add("reflect_origin", "translation", (0, 0, hip + 0.4), (0, 0, hip + 0.8), False)
    add("absorb_origin", "translation", (0, 0, hip), (0, 0, hip + 0.4), False)
    return bones


def default_hurtboxes(bones, prop=None):
    """15 capsules in authoring space {id, bone(name), a, b, radius, height}; the importer can also generate these itself."""
    p = dict(DEFAULT_PROPORTIONS)
    p.update(prop or {})
    by = {b["role"]: b for b in bones}
    t = p["thickness"]
    out = []

    def cap(id_, role, a_role, b_role, r, h):
        out.append({"id": id_, "bone": by[role]["name"], "a": list(by[a_role]["head"]), "b": list(by[b_role]["head"]), "radius": round(r * t, 3), "height": h, "grabbable": True})
    cap("head", "head", "head", "head_top", p["head_r"] * 0.9, "high")
    cap("chest", "chest", "chest", "neck", p["torso_w"] * 0.8, "high")
    cap("torso", "hips", "hips", "spine", p["torso_w"] * 0.75, "mid")
    for s in "LR":
        cap("upper_arm_" + s, "upper_arm." + s, "upper_arm." + s, "lower_arm." + s, 0.8, "mid")
        cap("lower_arm_" + s, "lower_arm." + s, "lower_arm." + s, "hand." + s, 0.8, "mid")
        cap("hand_" + s, "hand." + s, "hand." + s, "hand." + s, 1.1, "mid")
        cap("upper_leg_" + s, "upper_leg." + s, "upper_leg." + s, "lower_leg." + s, 1.0, "low")
        cap("lower_leg_" + s, "lower_leg." + s, "lower_leg." + s, "foot." + s, 0.95, "low")
        cap("foot_" + s, "foot." + s, "foot." + s, "toe." + s, 0.75, "low")
    return out
