#!/usr/bin/env python3
"""build_ultimate_body.py - an Ultimate fighter's body skeleton as IR: instances/<fighter>.ultimate-body.ir.json.

Reads the extracted c00 model.nusktb with the upstream ssbh_lib v0.19.0 `ssbh_data_json`
(experiment/tooling/ultimate/apps/SSBH-JSON). Nothing here is fighter-specific: roles come from
ROLE, the bone names Ultimate uses across the roster (90-91 of 91 fighters carry every core name;
fingers 60-81). A fighter whose skeleton lacks a required role is reported, not guessed.

Conventions, checked on the data:
  - SSBH matrices are row-vector (translation in the last row); they are transposed here.
  - A file may list a child before its parent (Mario: 9 bones), so world matrices are resolved
    through the parent chain, never by list order.
  - Fingers: FingerX1n..X4n are index, middle, ring, pinky; FingerX5n is the thumb (on Mario it
    branches from FingerL10 and sits 0.2 from the hand where the others sit ~1.5 out).
  - Rest rotation is also given as HSD-order Euler angles (R = Rz*Ry*Rx) for comparison with Melee
    IR; where that is gimbal-locked the quaternion in the joint's provenance is authoritative.

    python ports/ir/tools/build_ultimate_body.py kirby [mario ...]
    python ports/ir/tools/build_ultimate_body.py --all
"""
import argparse
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import warnings
import zlib

import numpy as np
from scipy.spatial.transform import Rotation

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
# The user's own Ultimate extraction and the upstream tools (ssbh_lib, ParamXML) next to it.
TOOL = os.environ.get("GW_ULTIMATE_ROOT", os.path.join(ROOT, "experiment", "tooling", "ultimate"))
DECODER = os.path.join(TOOL, "apps", "SSBH-JSON", "ssbh_data_json.exe")
FIGHTERS = os.path.join(TOOL, "workspace", "extracted", "fighter")
OUT_DIR = os.path.join(ROOT, "_build", "tmp", "ir")  # disc-derived: git-ignored
SKEL = "skel:body"

# Ultimate bone name -> (IR role, Melee common part it stands for or None).
# The Melee names are PlCo's common part ids as build_kirby_melee.py lists them.
ROLE = {
    "Trans": ("trans_n", "TransN"), "Rot": ("x_rot", "XRotN"),
    "Hip": ("hip", "HipN"), "Waist": ("waist", "WaistN"), "Bust": ("chest", "BustN"),
    "Neck": ("neck", "NeckN"), "Head": ("head", "HeadN"),
    "Throw": ("throw_n", "ThrowN"), "Headdress": ("hat_attach", None),
}
for side in "LR":
    ROLE.update({
        f"Clavicle{side}": (f"clavicle_{side.lower()}", f"{side}ShoulderN"),
        f"Shoulder{side}": (f"shoulder_{side.lower()}", f"{side}ShoulderJ"),
        f"Arm{side}": (f"arm_{side.lower()}", f"{side}ArmJ"),
        f"Hand{side}": (f"hand_{side.lower()}", f"{side}HandN"),
        f"Have{side}": (f"hand_item_{side.lower()}", f"{side}HaveN"),
        f"Leg{side}": (f"leg_{side.lower()}", f"{side}LegJ"),
        f"Knee{side}": (f"knee_{side.lower()}", f"{side}KneeJ"),
        f"Foot{side}": (f"foot_{side.lower()}", f"{side}FootJ"),
        f"Toe{side}": (f"toe_{side.lower()}", None),
    })
    for n, finger in ((1, "index"), (2, "middle"), (3, "ring"), (4, "pinky"), (5, "thumb")):
        melee = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "Thumb"}[n]
        ROLE[f"Finger{side}{n}1"] = (f"finger_{finger}_1_{side.lower()}", f"{side}{melee}Na")
        ROLE[f"Finger{side}{n}2"] = (f"finger_{finger}_2_{side.lower()}", f"{side}{melee}Nb")
# Roles a Melee fighter cannot do without: the engine looks these parts up by id.
REQUIRED = ["trans_n", "hip", "waist", "head", "throw_n",
            "shoulder_l", "arm_l", "hand_item_l", "leg_l", "knee_l", "foot_l",
            "shoulder_r", "arm_r", "hand_item_r", "leg_r", "knee_r", "foot_r"]


_KIND_ROWS = None


def fighter_param_row(fighter):
    """Row of fighter_param_table naming this fighter, via upstream ParamXML (no label file needed:
    a Hash40 is the name's CRC32 with its length in the top byte)."""
    global _KIND_ROWS
    if _KIND_ROWS is None:
        exe = os.path.join(TOOL, "apps", "ParamXML", "ParamXML-win-x64", "ParamXML.exe")
        prc = os.path.join(FIGHTERS, "common", "param", "fighter_param.prc")
        with tempfile.TemporaryDirectory() as tmp:
            xml = os.path.join(tmp, "fp.xml")
            subprocess.run([exe, "-d", prc, "-o", xml], check=True, capture_output=True)
            text = open(xml, encoding="utf-8").read()
        field = hash40("fighter_kind")
        _KIND_ROWS = re.findall(r'<hash40 hash="%s">(0x[0-9A-F]+)</hash40>' % field, text)
    return _KIND_ROWS.index(hash40("fighter_kind_" + fighter))


def hash40(name):
    return "0x%02X%08X" % (len(name), zlib.crc32(name.encode()))


def rf(x):
    return float(f"{x:.6g}")


def build(fighter):
    source = os.path.join(FIGHTERS, fighter, "model", "body", "c00", "model.nusktb")
    raw = open(source, "rb").read()
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "skel.json")
        subprocess.run([DECODER, source, out], check=True, capture_output=True)
        bones = json.load(open(out))["bones"]

    local = [np.asarray(b["transform"], dtype=float).T for b in bones]
    world = {}

    def world_of(i):
        if i not in world:
            p = bones[i]["parent_index"]
            world[i] = world_of(p) @ local[i] if p is not None else local[i]
        return world[i]

    joints, roles, gimbal, helpers = [], [], [], []
    for i, (b, m) in enumerate(zip(bones, local)):
        scale = np.linalg.norm(m[:3, :3], axis=0)
        rot = Rotation.from_matrix(m[:3, :3] / scale)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            euler = rot.as_euler("xyz")
        if caught:
            gimbal.append(b["name"])
        if b["name"].startswith("H_"):
            helpers.append(b["name"])
        joint = {"index": i, "name": b["name"], "parent": b["parent_index"],
                 "rest": {"translation": [rf(v) for v in m[:3, 3]],
                          "rotation_euler_rad": [rf(v) for v in euler],
                          "scale": [rf(v) for v in scale]},
                 "traits": (["skeleton_root"] if b["parent_index"] is None else []) +
                           (["billboard"] if b["billboard_type"] != "Disabled" else []),
                 "provenance": {"confidence": "verified", "evidence": ["ev:nusktb"],
                                "note": "rest quaternion xyzw %s; rest world translation %s" % (
                                    [rf(v) for v in rot.as_quat()],
                                    [rf(v) for v in world_of(i)[:3, 3]])}}
        if b["name"] in ROLE:
            role, melee = ROLE[b["name"]]
            joint["role_guess"] = role
            note = "bone name %s" % b["name"] + ("; Melee common part %s" % melee if melee else "")
            roles.append({"role": role, "joint": i, "skeleton": SKEL,
                          "provenance": {"confidence": "inferred", "evidence": ["ev:nusktb"],
                                         "note": note}})
        joints.append(joint)

    present = {r["role"] for r in roles}
    missing = [r for r in REQUIRED if r not in present]
    issues = []
    if missing:
        issues.append({"id": "issue:missing_roles", "title": "No bone for required role(s) %s" % missing,
                       "layer": "content", "severity": "latent", "status": "open",
                       "description": "The Melee engine looks these parts up by id. This skeleton has no "
                                      "bone with the standard name; a per-fighter mapping is needed.",
                       "provenance": {"confidence": "verified", "evidence": ["ev:nusktb"]}})
    doc = {
        "ir_version": "0.1.0",
        "document_id": f"{fighter}.ultimate-body",
        "subject": {"character": fighter, "game": "ssbu", "engine": "other",
                    "distribution": {"name": "Super Smash Bros. Ultimate 13.0.2", "kind": "retail",
                                     "media": "experiment/tooling/ultimate/workspace/extracted"},
                    "analysed_with": [{"tool": "ssbh_lib v0.19.0 ssbh_data_json (upstream release)"},
                                      {"tool": "ports/ir/tools/build_ultimate_body.py"}],
                    "notes": "Body skeleton only."},
        "evidence": [{"id": "ev:fighter_param", "kind": "file_bytes",
                      "path": "fighter/common/param/fighter_param.prc",
                      "note": "decoded with upstream ParamXML; field 'fighter_kind' = 0x0C541EF0B2"},
                     {"id": "ev:nusktb", "kind": "file_bytes",
                      "path": f"fighter/{fighter}/model/body/c00/model.nusktb",
                      "note": "sha256 " + hashlib.sha256(raw).hexdigest()}],
        "identity": {"names": {"internal": [fighter]},
                     "indices": [{"space": "ssbu.fighter_param_row", "value": fighter_param_row(fighter),
                                  "stability": "stable",
                                  "provenance": {"confidence": "verified", "evidence": ["ev:fighter_param"],
                                                 "note": "row of fighter_param.prc fighter_param_table whose "
                                                         "fighter_kind is hash40('fighter_kind_%s'); this is "
                                                         "table order, not the engine's FIGHTER_KIND" % fighter}}],
                     "provenance": {"confidence": "verified", "evidence": ["ev:nusktb"]}},
        "assets": {
            "skeletons": [{"id": SKEL, "name": "c00 body", "joint_count": len(joints),
                           "order": "file_order", "joints": joints,
                           "provenance": {"confidence": "verified", "evidence": ["ev:nusktb"],
                                          "note": "SSBH row-vector matrices transposed; world resolved via the "
                                                  "parent chain (file order may list children first). Euler is "
                                                  "HSD order, radians. Gimbal-locked (use the quaternion): %s. "
                                                  "%d helper (H_*) bones." % (gimbal, len(helpers))}}],
            "bone_roles": roles},
        "issues": issues,
        "coverage": {"identity": {"status": "summary"},
                     "assets.skeletons": {"status": "complete", "note": "c00 body skeleton"},
                     "assets.animations": {"status": "absent"}},
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f"{fighter}.ultimate-body.ir.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)
    return len(joints), len(roles), missing, len(helpers)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("fighters", nargs="*")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()
    names = sorted(os.path.basename(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(p)))))
                   for p in glob.glob(os.path.join(FIGHTERS, "*", "model", "body", "c00", "model.nusktb"))) \
        if args.all else args.fighters
    if not names:
        ap.error("name fighters or pass --all")
    incomplete = 0
    for n in names:
        joints, roles, missing, helpers = build(n)
        incomplete += bool(missing)
        print(f"{n:14} {joints:4} joints {helpers:3} helpers {roles:3} roles" +
              (f"  MISSING {missing}" if missing else ""))
    print(f"{len(names)} fighter(s), {incomplete} with missing required roles")


if __name__ == "__main__":
    sys.exit(main())
