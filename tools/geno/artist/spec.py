"""spec.py - the artist contract as data: roles, limits, clip table. Every value says where it comes from.

Three kinds of rule (docs/geno-artist-spec.md has the prose):
  ENGINE    the game rejects or misdraws without it (cited to a game-repo file)
  CONVERTER the importer chooses to refuse it today; relaxing it is converter work, not engine work
  COURIER   how the sample fighter happens to be built; copy it or not
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

# ---- limits --------------------------------------------------------------------------------------------------------
LIMITS = {
    # ENGINE: pc/geno/geno_plan.h GPL_MAX_JOINTS (256 including the synthesized TopN, XRotN, YRotN)
    "max_joints_engine": 256,
    # ENGINE: pc/platform/geno_define_registry.inc gn_plan_parse, hurtboxes must hold 1..15 capsules
    "max_hurtboxes": 15,
    # ENGINE: pc/geno/geno_plan.h GPL_MAX_CLIPS; clip names are stored in 32 bytes, symbols in 72
    "max_clips": 256,
    "max_clip_name": 31,
    # ENGINE: 351 motion rows (GPL_MAX_MOTIONS)
    "motion_rows": 351,
    # CONVERTER: ports/ir/tools/authored_fighter.py (influence check); 4 would fit the glTF format, >2 is untested in the engine path
    "max_influences": 2,
    # CONVERTER: fighterbuild --pc-palette 64 packs one piece with a 64-matrix palette (Program.cs:56); more distinct bones per piece is untested
    "palette_bones": 64,
    # ENGINE: one animation clip is read into a 128 KB buffer (geno.md 22.3: "buffer 128 KB"); a clip's encoded size is checked after encoding
    "clip_buffer_bytes": 0x20000,
    # CONVERTER: one mesh, one primitive, one material (the palette path builds one piece)
    "mesh_primitives": 1,
    # CONVERTER: the bank is 60 fps, one key per frame; a glTF sampled at another rate is refused
    "fps": 60,
}

# ---- roles ---------------------------------------------------------------------------------------------------------
# role -> Melee common part (plan_parts.COMMON); None = no part of its own (the converter keeps the bone as a plain joint)
ROLE_PART = {
    "translation": "TransN", "hips": "HipN", "spine": "WaistN", "chest": "BustN", "neck": "NeckN", "head": "HeadN",
    "grab_anchor": "ThrowN", "item_socket.R": "RHaveN", "item_socket.L": "LHaveN",
}
for _s, _p in (("L", "L"), ("R", "R")):
    ROLE_PART.update({
        "shoulder." + _s: _p + "ShoulderN", "upper_arm." + _s: _p + "ShoulderJ", "lower_arm." + _s: _p + "ArmJ",
        "hand." + _s: _p + "HandN", "thumb." + _s: _p + "ThumbNa", "fingers." + _s: _p + "1stNa",
        "upper_leg." + _s: _p + "LegJ", "lower_leg." + _s: _p + "KneeJ", "foot." + _s: _p + "FootJ",
    })
# roles with no Melee part (documentation / future use; the engine does not read them today, see spec section 4)
OTHER_ROLES = ["root", "head_top", "toe.L", "toe.R", "victim_anchor", "camera_focus", "shield_origin", "reflect_origin",
               "absorb_origin", "cloth_1", "cloth_2", "cloth_3", "cloth_4"]
ALL_ROLES = list(ROLE_PART) + OTHER_ROLES

# ENGINE: gn_plan_parse needs every ftdata entry to resolve; plan_parts.FIELDS says which roles those are.
REQUIRED = ["translation", "hips", "head", "upper_arm.L", "upper_arm.R", "lower_arm.L", "lower_arm.R", "upper_leg.L", "upper_leg.R",
            "lower_leg.L", "lower_leg.R", "foot.L", "foot.R", "item_socket.R", "grab_anchor"]
# Not needed to load, but a fighter without them animates or fights badly: warned, not refused.
RECOMMENDED_ROLES = ["spine", "chest", "neck", "head_top", "hand.L", "hand.R", "shoulder.L", "shoulder.R", "toe.L", "toe.R",
                     "shield_origin"]
SIDED = {"shoulder", "upper_arm", "lower_arm", "hand", "thumb", "fingers", "upper_leg", "lower_leg", "foot", "toe", "item_socket"}

# Legacy role names (the Courier's glTF extras) have no side; side comes from the bone name suffix.
def canonical_role(role, bone_name):
    if role in ALL_ROLES:
        return role
    if role in SIDED:
        m = re.search(r"(?:^|[._\-])([LR])$", bone_name) or re.search(r"(Left|Right)$", bone_name)
        if m:
            return "%s.%s" % (role, m.group(1)[0])
    return role


# Name hints for bones the artist did not map (used for a GUESS with a warning, never silently). Case-insensitive, side-aware.
_HINTS = [
    (r"^(hips?|pelvis|root_hips)$", "hips"), (r"^(spine|spine1|abdomen|waist|torso|lower_?spine)$", "spine"),
    (r"^(chest|spine2|upper_?spine|ribs?|thorax)$", "chest"), (r"^(neck|nape)$", "neck"), (r"^(head|skull)$", "head"),
    (r"^(head_?top|headtop|crown)$", "head_top"),
    (r"^(clavicle|shoulder|collar)$", "shoulder"), (r"^(upper_?arm|arm|humerus)$", "upper_arm"), (r"^(fore_?arm|lower_?arm|elbow)$", "lower_arm"),
    (r"^(hand|wrist)$", "hand"), (r"^(thumb\d?)$", "thumb"), (r"^(fingers?|palm|index\d?)$", "fingers"),
    (r"^(thigh|upper_?leg|femur)$", "upper_leg"), (r"^(shin|calf|lower_?leg|knee)$", "lower_leg"), (r"^(foot|ankle)$", "foot"),
    (r"^(toes?|ball)$", "toe"), (r"^(item_?socket|socket_?item|hold|weapon)$", "item_socket"),
    (r"^(grab_?anchor|throw_?n?)$", "grab_anchor"), (r"^(root)$", "root"), (r"^(trans|trans_?n|translation|motion)$", "translation"),
]


def guess_role(name):
    """Best role for a bone name by convention, or None. Understands .L/_L/L_/Left/Right and a mixamorig: style prefix."""
    n = re.sub(r"^(mixamorig:|DEF-|def_|CC_Base_)", "", name, flags=re.I)
    side = None
    m = re.search(r"(?:[._\-]|^)(L|R|left|right)(?:[._\-]|$)", n, flags=re.I) or re.search(r"(Left|Right)", n)
    if m:
        side = m.group(1)[0].upper()
        n = (n[:m.start()] + "_" + n[m.end():]).strip("._-")
    n = n.strip("._-")
    for pat, role in _HINTS:
        if re.match(pat, n, flags=re.I):
            if role in SIDED:
                return "%s.%s" % (role, side) if side else None
            return role
    return None


# ---- the clip table -------------------------------------------------------------------------------------------------
_TABLE = None


def clip_table():
    global _TABLE
    if _TABLE is None:
        _TABLE = json.load(open(os.path.join(DATA, "clip_table.json"), encoding="utf-8"))
        _TABLE["by_name"] = {r["name"]: r for r in _TABLE["rows"]}
    return _TABLE


def mario_joint_roles():
    d = json.load(open(os.path.join(DATA, "mario_joint_roles.json"), encoding="utf-8"))
    return {int(k): v for k, v in d["roles"].items()}


def game_dir():
    """The game checkout: GW_MELEE, else <workspace>/melee."""
    return os.environ.get("GW_MELEE") or os.path.abspath(os.path.join(HERE, "..", "..", "..", "melee"))


def workspace_root():
    return os.path.abspath(os.path.join(HERE, "..", "..", ".."))
