"""Shared tables for the Vanilla Original fighter ("the Courier"): bones, roles, hurtboxes, ECB, costumes.
Pure Python (no bpy) so validators and tools can import it.

Authoring space (Blender): Z up, the character faces -Y, the character's LEFT is +X, 1 unit = 1 Melee unit
(the fighter stands about 11 units tall, soles at z=0). The glTF export maps (x,y,z) -> (x,z,-y): Y up, the
front faces +Z, left is +X, the same handedness and facing as HSD / Melee model space.
"""
import math, os
HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)                      # ports/vanilla-original
AUDIT = os.path.normpath(os.path.join(PKG, "..", "..", "_build", "audit-20261003", "geno-art"))
OUT = os.path.join(PKG, "out")                    # generated, git-ignored (see README)
FPS = 60

def S(x):  # mirror x for the right side
    return -x

# name, parent, head, tail, role, deform
# Heads/tails in authoring space. Left bones are at +X; the table builds the right side by mirroring.
_L = []
def _b(name, parent, head, tail, role, deform=True, side=None):
    _L.append(dict(name=name, parent=parent, head=head, tail=tail, role=role, deform=deform, side=side))

_b("root", None, (0, 0, 0), (0, 0, 0.6), "root", False)               # TopN-like: placement node, never animated
_b("trans", "root", (0, 0, 0), (0, 0, 0.5), "translation", False)     # TransN-like: the ONLY root-motion carrier
_b("hips", "trans", (0, 0, 5.4), (0, 0, 6.2), "hips")
_b("spine", "hips", (0, 0, 6.2), (0, 0, 7.2), "spine")
_b("chest", "spine", (0, 0, 7.2), (0, 0, 8.2), "chest")
_b("neck", "chest", (0, 0, 8.2), (0, 0, 8.8), "neck")
_b("head", "neck", (0, 0, 8.8), (0, 0, 11.6), "head")
for _s, _sx in (("L", 1), ("R", -1)):
    a = lambda x, y, z, sx=_sx: (x * sx, y, z)
    _b(f"clavicle_{_s}", "chest", a(0.3, 0, 7.8), a(1.8, 0, 7.8), "shoulder", True, _s)
    _b(f"upperarm_{_s}", f"clavicle_{_s}", a(1.9, 0, 7.75), a(3.07, 0, 6.25), "upper_arm", True, _s)
    _b(f"forearm_{_s}", f"upperarm_{_s}", a(3.07, 0, 6.25), a(4.18, 0, 4.83), "lower_arm", True, _s)
    _b(f"hand_{_s}", f"forearm_{_s}", a(4.18, 0, 4.83), a(4.80, 0, 4.04), "hand", True, _s)
    _b(f"thumb_{_s}", f"hand_{_s}", a(4.0, -0.45, 4.75), a(3.9, -0.95, 4.35), "thumb", True, _s)
    _b(f"fingers_{_s}", f"hand_{_s}", a(4.55, -0.15, 4.5), a(4.95, -0.15, 3.95), "fingers", True, _s)
    _b(f"thigh_{_s}", "hips", a(1.05, 0, 5.5), a(1.05, 0, 3.3), "upper_leg", True, _s)
    _b(f"shin_{_s}", f"thigh_{_s}", a(1.05, 0, 3.3), a(1.05, 0, 1.25), "lower_leg", True, _s)
    _b(f"foot_{_s}", f"shin_{_s}", a(1.05, 0, 1.25), a(1.05, -1.55, 0.55), "foot", True, _s)
    _b(f"toe_{_s}", f"foot_{_s}", a(1.05, -1.55, 0.55), a(1.05, -2.45, 0.45), "toe", True, _s)
_b("scarf1", "neck", (0, 0.9, 8.1), (0, 1.5, 7.2), "cloth_1")
_b("scarf2", "scarf1", (0, 1.5, 7.2), (0, 1.8, 6.0), "cloth_2")
_b("scarf3", "scarf2", (0, 1.8, 6.0), (0, 1.9, 4.7), "cloth_3")
_b("scarf4", "scarf3", (0, 1.9, 4.7), (0, 1.9, 3.5), "cloth_4")
# sockets / anchors: not deforming, tiny bones used as named transforms
_b("socket_item_R", "hand_R", (-4.35, -0.2, 4.45), (-4.35, -0.6, 4.45), "item_socket", False, "R")
_b("grab_anchor", "chest", (0, -3.2, 6.6), (0, -3.2, 7.1), "grab_anchor", False)
_b("victim_anchor", "hips", (0, 0, 5.6), (0, 0, 6.0), "victim_anchor", False)
_b("camera_focus", "chest", (0, 0, 7.4), (0, 0, 7.8), "camera_focus", False)
_b("shield_origin", "trans", (0, 0, 5.0), (0, 0, 5.4), "shield_origin", False)
_b("reflect_origin", "trans", (0, 0, 5.8), (0, 0, 6.2), "reflect_origin", False)
_b("absorb_origin", "trans", (0, 0, 5.4), (0, 0, 5.8), "absorb_origin", False)
_b("head_top", "head", (0, 0, 12.1), (0, 0, 12.5), "head_top", False)
BONES = _L
BONE = {b["name"]: b for b in BONES}
DEFORM = [b["name"] for b in BONES if b["deform"]]

# DSL angle signs: the pose DSL uses (rx, ry, rz) in degrees with a per-bone meaning, converted to a raw
# rotation about the armature X, Y, Z axes by these signs. See anim_lib.py header for the meaning.
def _signs():
    s = {}
    for n in ("hips", "spine", "chest", "neck", "head"):
        s[n] = (1, 1, 1)           # rx lean forward, ry lean to the character's left, rz turn left
    for side, sy, sz in (("L", -1, 1), ("R", 1, -1)):
        s[f"upperarm_{side}"] = (-1, sy, sz)   # rx swing forward, ry abduct (out), rz twist
        s[f"forearm_{side}"] = (-1, sy, sz)    # rx flex (hand forward/up)
        s[f"hand_{side}"] = (-1, sy, sz)
        s[f"thumb_{side}"] = (-1, sy, sz)
        s[f"fingers_{side}"] = (-1, sy, sz)    # rx curl (fist) -- positive curls the fingers forward
        s[f"clavicle_{side}"] = (1, sy, -sz if side == "L" else -sz)  # ry shrug (up), rz protract
        s[f"thigh_{side}"] = (-1, sy, sz)      # rx lift forward, ry abduct
        s[f"shin_{side}"] = (1, sy, sz)        # rx knee flex (shin goes back)
        s[f"foot_{side}"] = (-1, sy, sz)       # rx toes up
        s[f"toe_{side}"] = (-1, sy, sz)
    for i in range(1, 5):
        s[f"scarf{i}"] = (1, 1, 1)             # rx tail lifts up, rz swings
    return s
SIGNS = _signs()

# Hurtboxes: the engine's capacity is FighterHurtCapsule hurt_capsules[15] (melee/src/melee/ft/types.h:1468),
# gd.hurtboxes fields are {id, bone, height, grabbable, a, b, radius}. Endpoints are given in the REST pose,
# authoring space (the converter derives bone-local offsets from the inverse bind matrices).
def _hb():
    h = []
    def add(id_, bone, a, b, r, height, grab=True):
        h.append(dict(id=id_, bone=bone, a=a, b=b, radius=r, height=height, grabbable=grab))
    add("head", "head", (0, 0, 9.75), (0, 0, 10.45), 1.8, "high")
    add("chest", "chest", (0, 0, 7.3), (0, 0, 8.0), 1.65, "high")
    add("torso", "hips", (0, 0, 5.5), (0, 0, 6.8), 1.55, "mid")
    for s, sx in (("L", 1), ("R", -1)):
        add(f"upperarm_{s}", f"upperarm_{s}", (1.9 * sx, 0, 7.75), (3.07 * sx, 0, 6.25), 0.8, "mid")
        add(f"lowerarm_{s}", f"forearm_{s}", (3.07 * sx, 0, 6.25), (4.18 * sx, 0, 4.83), 0.8, "mid")
        add(f"hand_{s}", f"hand_{s}", (4.4 * sx, 0, 4.55), (4.8 * sx, 0, 4.0), 1.1, "mid")
        add(f"thigh_{s}", f"thigh_{s}", (1.05 * sx, 0, 5.4), (1.05 * sx, 0, 3.4), 1.0, "low")
        add(f"shin_{s}", f"shin_{s}", (1.05 * sx, 0, 3.3), (1.05 * sx, 0, 1.4), 0.95, "low")
        add(f"foot_{s}", f"foot_{s}", (1.05 * sx, 0.2, 0.75), (1.05 * sx, -1.7, 0.65), 0.75, "low")
    return h
HURTBOXES = _hb()
assert len(HURTBOXES) == 15

# ECB (environment collision): the diamond of {top, bottom, left, right} the engine reads, in world units
# relative to the `trans` bone at rest (feet on the ground). Same convention as gd's `ecb = {top,bottom,left,right}`.
ECB = dict(
    anchor_bone="trans",
    standing=dict(top=11.7, bottom=0.0, left=-3.0, right=3.0, side_height=5.5),
    crouch=dict(top=6.4, bottom=0.0, left=-3.0, right=3.0, side_height=3.2),
    aerial=dict(top=11.7, bottom=0.0, left=-3.0, right=3.0, side_height=5.5),
    ledge_grab_box=dict(front=5.0, back=-1.0, up=3.0, down=-6.0),  # proposal: hang box in front of the face
    notes="Diamond ECB. Standing top is just above the helmet (11.7), below the crest (12.4); sampled from the animation root, "
          "not from bones. Values are proposals sized to this body (retail ECBs are a few units wide).",
)

COSTUMES = [
    # name, team, palette entries 0..15 (see PALETTE_CELLS), eye glow
    dict(name="default", team=None, desc="teal tunic, cream helmet, amber scarf"),
    dict(name="red", team="red", desc="crimson tunic, cream helmet, gold scarf"),
    dict(name="blue", team="blue", desc="cobalt tunic, cream helmet, white scarf"),
    dict(name="green", team="green", desc="forest tunic, cream helmet, lime scarf"),
]
