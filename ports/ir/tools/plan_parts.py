#!/usr/bin/env python3
"""plan_parts.py - a fighter's Melee parts table and ftData joint fields, planned from its skeleton IR.

    python ports/ir/tools/plan_parts.py <fighter>.ultimate-body.ir.json [-o plan.json]

Input: a skeleton IR whose bone roles name Melee common parts (build_ultimate_body.py writes them).
Output: a plan the model/animation builders consume. It keeps the fighter's own skeleton and adds
only what the Melee engine needs:

  joints       the source joints plus the synthesized ones Melee's code expects and Ultimate rigs lack
               (TopN above the root; YRotN between XRotN and the hip). Synthesized joints are identity.
  parts        PlCo ftLoadCommonData[4] for the fighter: joint_to_part / part_to_joint over the 54
               common parts, parts_num = joint count, and no placeholder slots ([5] = NULL), so a
               part slot IS a joint index (Kirby's 13 placeholder slots exist only for his copy hat).
  ftdata       the ftData fields that name joints (x8 part bytes, x34, x38, x44, x54, x58, x30 bones),
               by role. The roles are the ones Melee's own fighters use (read from PlKb.dat and
               PlMr.dat on the vanilla disc; see FIELDS).
  unresolved   every role or field this skeleton cannot fill, instead of a guess.
"""
import argparse
import json
import os
import re
import sys

COMMON = ["TopN", "TransN", "XRotN", "YRotN", "HipN", "WaistN",
          "LLegJA", "LLegJ", "LKneeJ", "LFootJA", "LFootJ",
          "RLegJA", "RLegJ", "RKneeJ", "RFootJA", "RFootJ",
          "WaistB", "BustN",
          "LShoulderN", "LShoulderJA", "LShoulderJ", "LArmJ", "LHandN",
          "L1stNa", "L1stNb", "L2ndNa", "L2ndNb", "L3rdNa", "L3rdNb", "L4thNa", "L4thNb",
          "LHaveN", "LThumbNa", "LThumbNb", "NeckN", "HeadN",
          "RShoulderN", "RShoulderJA", "RShoulderJ", "RArmJ", "RHandN",
          "R1stNa", "R1stNb", "R2ndNa", "R2ndNb", "R3rdNa", "R3rdNb", "R4thNa", "R4thNb",
          "RHaveN", "RThumbNa", "RThumbNb", "ThrowN", "ExtraN"]
# Common parts with no joint of their own share another's (install_mk.py does the same for MK):
# the 'A' pre-joints fall back to their main joint, WaistB to the waist.
FALLBACK = {"LLegJA": "LLegJ", "LFootJA": "LFootJ", "RLegJA": "RLegJ", "RFootJA": "RFootJ",
            "LShoulderJA": "LShoulderJ", "RShoulderJA": "RShoulderJ", "WaistB": "WaistN",
            "ExtraN": "TransN"}
# What each ftData joint field holds, as roles, from Melee Kirby's and Mario's own values
# (vanilla PlKb.dat / PlMr.dat; both agree except the centre and the head-top joint).
# 'centre' = the waist when there is one (Mario), else the hip (Kirby).
# 'head_top' = the joint above the head (Mario: HeadN's child; Kirby: his hat point).
FIELDS = {
    "x8_part_bytes": ["RHaveN", "ThrowN", "head_top", "LFootJ", "RFootJ"],   # item, shield, head, feet
    "x34_centre": ["centre"],
    "x38_coin": ["centre", "TopN"],
    "x44_ecb": ["head_top", "RShoulderJ", "LShoulderJ", "RKneeJ", "LKneeJ", "HipN"],  # Mario's layout
    "x54_gfx": ["HeadN", "RArmJ", "LKneeJ", "RKneeJ", "LArmJ"],
    "x58_ik": [["RLegJ", "LLegJ"], ["RKneeJ", "LKneeJ"], ["RFootJ", "LFootJ"],
               ["RShoulderJ", "LShoulderJ"], ["RArmJ", "LArmJ"]],
    "x30_hurtbox_bones": ["WaistN", "HeadN", "RShoulderJ", "LShoulderJ", "RArmJ", "LArmJ",
                          "RLegJ", "LLegJ", "RKneeJ", "LKneeJ"],  # Mario's ten
}


# Fingers are optional: Melee's own Kirby has none (his part_to_joint is 255 for all twenty).
OPTIONAL = {c for c in COMMON if re.match(r"[LR](1st|2nd|3rd|4th|Thumb)N[ab]$", c)} | {"LHandN", "RHandN"}


def plan(doc, overrides=None):
    """overrides: {source bone name: Melee common part} for skeletons that break the naming
    convention (R.O.B., Ivysaur); they replace name-inferred roles for those parts."""
    sk = doc["assets"]["skeletons"][0]
    src = sk["joints"]
    common_of = {}
    for r in doc["assets"]["bone_roles"]:
        m = re.search(r"Melee common part (\w+)", r["provenance"].get("note", ""))
        if m:
            common_of[r["joint"]] = m.group(1)
    for name, common in (overrides or {}).items():
        idx = next((j["index"] for j in src if j.get("name") == name), None)
        if idx is None:
            sys.exit(f"override names a bone this skeleton lacks: {name}")
        common_of = {i: c for i, c in common_of.items() if c != common}
        common_of[idx] = common
    head_top = next((j["index"] for j in src if j.get("name") == "Headdress"), None)

    # ---- joints: source order, TopN prepended, YRotN inserted under XRotN -------------------------
    by_common = {c: i for i, c in common_of.items()}
    joints = [{"name": "TopN", "source": None, "parent": None, "synthesized": True}]
    remap = {}
    xrot = by_common.get("XRotN")
    for j in src:
        remap[j["index"]] = len(joints)
        joints.append({"name": j["name"], "source": j["index"], "parent": j["parent"],
                       "synthesized": False})
        if j["index"] == xrot:
            joints.append({"name": "YRotN", "source": None, "parent": ("src", xrot), "synthesized": True})
    yrot = next((i for i, j in enumerate(joints) if j["name"] == "YRotN"), None)
    for i, j in enumerate(joints):
        p = j["parent"]
        if j["synthesized"]:
            j["parent"] = remap[p[1]] if p else None
        elif p is None:
            j["parent"] = 0                                   # the old root hangs off TopN
        elif p == xrot and yrot is not None:
            j["parent"] = yrot                                # XRotN's children move under YRotN
        else:
            j["parent"] = remap[p]
    # HSD walks a joint tree depth-first (child before next sibling) and a figatree's tracks follow
    # that order, so the plan is reordered depth-first, siblings in file order. Ultimate's file
    # order is not that: it can even list a child before its parent (Mario: 9 bones).
    kids = {i: [] for i in range(len(joints))}
    for i, j in enumerate(joints):
        if j["parent"] is not None:
            kids[j["parent"]].append(i)
    order, stack = [], [0]
    while stack:
        i = stack.pop()
        order.append(i)
        stack.extend(reversed(kids[i]))
    if len(order) != len(joints):
        sys.exit("joint tree is not connected under TopN")
    new = {old: n for n, old in enumerate(order)}
    joints = [dict(joints[old], parent=None if joints[old]["parent"] is None else new[joints[old]["parent"]])
              for old in order]
    remap = {src: new[i] for src, i in remap.items()}
    yrot = new[yrot] if yrot is not None else None
    joint_of = {"TopN": 0}
    if yrot is not None:
        joint_of["YRotN"] = yrot
    for i, c in common_of.items():
        joint_of[c] = remap[i]

    # ---- parts table ------------------------------------------------------------------------------
    unresolved = []
    p2j = []
    for c in COMMON:
        j = joint_of.get(c, joint_of.get(FALLBACK.get(c)))
        p2j.append(255 if j is None else j)
        if j is None and c not in OPTIONAL:
            unresolved.append({"common_part": c, "why": "no bone with this role"})
    j2p = [255] * len(joints)
    for ci, c in enumerate(COMMON):
        if c in joint_of:                                     # primary roles only, not fallbacks
            j2p[joint_of[c]] = ci

    # ---- ftData joint fields ------------------------------------------------------------------------
    special = {"centre": joint_of.get("WaistN", joint_of.get("HipN")),
               "head_top": remap.get(head_top) if head_top is not None else None}
    if special["head_top"] is None and "HeadN" in joint_of:
        kids = [i for i, j in enumerate(joints) if j["parent"] == joint_of["HeadN"]]
        special["head_top"] = kids[0] if len(kids) == 1 else joint_of["HeadN"]  # else the head itself

    def resolve(field, role):
        if isinstance(role, list):
            return [resolve(field, r) for r in role]
        j = special.get(role) if role in special else joint_of.get(role, joint_of.get(FALLBACK.get(role)))
        if j is None:
            unresolved.append({"field": field, "role": role})
        return {"role": role, "joint": j, "name": joints[j]["name"] if j is not None else None}

    ftdata = {f: [resolve(f, r) for r in roles] for f, roles in FIELDS.items()}
    return {"fighter": doc["document_id"], "joint_count": len(joints),
            "synthesized": [j["name"] for j in joints if j["synthesized"]],
            "joints": [{"index": i, **j} for i, j in enumerate(joints)],
            "parts": {"parts_num": len(joints), "joint_to_part": j2p, "part_to_joint": p2j,
                      "placeholder_slots": None},
            "ftdata": ftdata, "unresolved": unresolved,
            "limits": {"max_ft_parts": 255, "over": len(joints) > 255}}  # MAX_FT_PARTS on PC (melee b8326c66c)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ir")
    ap.add_argument("-o", "--out")
    ap.add_argument("--roles", help="JSON {source bone name: Melee common part} overrides")
    args = ap.parse_args()
    overrides = json.load(open(args.roles, encoding="utf-8")) if args.roles else None
    result = plan(json.load(open(args.ir, encoding="utf-8")), overrides)
    text = json.dumps(result, indent=1)
    if args.out:
        open(args.out, "w", encoding="utf-8").write(text)
    print(f"{result['fighter']}: {result['joint_count']} joints (+{result['synthesized']}), "
          f"{sum(v != 255 for v in result['parts']['part_to_joint'])}/54 common parts mapped, "
          f"{len(result['unresolved'])} unresolved" + (", OVER the 255-joint cap" if result['limits']['over'] else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
