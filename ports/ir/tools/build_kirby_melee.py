#!/usr/bin/env python3
"""build_kirby_melee.py - generate _build/tmp/ir/kirby.melee.ir.json from the vanilla disc.

The retarget target for ports/kirby-ultimate. Until now nothing described Melee Kirby: the animation
converter's joint numbers (ports/kirby-ultimate/animations/convert.py BONE_MAP) had no recorded
target. This reads the game's own tables instead of guessing:

  - PlKbNr.dat  the 46-joint tree: rest SRT, inverse bind, raw flags (JObj desc, sysdolphin jobj.h)
  - PlCo.dat    ftLoadCommonData[4] parts table and [5] placeholder list for Kirby (internal kind 4):
                the ftParts walk (ftparts.c ~l.405) gives each JObj a part slot, skipping the
                placeholder slots, and joint_to_part names the slot's common part
  - PlKb.dat    the motion table (ftDataKirby+0xC, 0x18-byte rows): figatree, script, flags
  - PlKbAJ.dat  each figatree's frame count and joint count

    python ports/ir/tools/build_kirby_melee.py
    python ports/ir/tools/validate.py _build/tmp/ir/kirby.melee.ir.json

Needs GW_ISO_VANILLA (from .env). The output describes disc data; it goes to _build/tmp/ir/ (git-ignored).
"""
import hashlib
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "mex_port"))
import mex_hsd  # noqa: E402

SRC = os.path.join(ROOT, "melee", "src", "melee")
OUT = os.path.join(ROOT, "_build", "tmp", "ir", "kirby.melee.ir.json")
KIND = 4  # internal FighterKind of Kirby
SKEL = "skel:body"

# Common part ids as PlCo's joint_to_part holds them. The decomp's Fighter_Part enum
# (ft/forward.h) has one entry fewer (no WaistB) and so is off by one from 16 on: Kirby's
# common part 52 hangs off YRotN like every fighter's ThrowN, where the enum says TransN2.
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
# Engine-neutral IR roles (assets.schema.json BoneRole) for the common parts that have one.
ROLE = {"TopN": "top_n", "TransN": "trans_n", "XRotN": "x_rot", "YRotN": "y_rot",
        "HipN": "hip", "WaistN": "waist", "BustN": "chest", "NeckN": "neck", "HeadN": "head",
        "LLegJA": "leg_root_l", "LLegJ": "leg_l", "LKneeJ": "knee_l", "LFootJA": "foot_root_l",
        "LFootJ": "foot_l", "RLegJA": "leg_root_r", "RLegJ": "leg_r", "RKneeJ": "knee_r",
        "RFootJA": "foot_root_r", "RFootJ": "foot_r",
        "LShoulderN": "clavicle_l", "LShoulderJA": "shoulder_root_l", "LShoulderJ": "shoulder_l",
        "LArmJ": "arm_l", "LHandN": "hand_l", "LHaveN": "hand_item_l",
        "RShoulderN": "clavicle_r", "RShoulderJA": "shoulder_root_r", "RShoulderJ": "shoulder_r",
        "RArmJ": "arm_r", "RHandN": "hand_r", "RHaveN": "hand_item_r",
        "ThrowN": "throw_n", "ExtraN": "extra"}
FLAG_TRAITS = [(1 << 0, "skinned_bone"), (1 << 2, "envelope_model"), (1 << 3, "classical_scale"),
               (1 << 4, "hidden"), (1 << 7, "lighting"), (1 << 16, "specular"),
               (1 << 28, "opaque_pass"), (1 << 29, "translucent_pass")]


def prov(conf, *ev, note=None):
    p = {"confidence": conf, "evidence": list(ev)}
    if note:
        p["note"] = note
    return p


def rf(x):
    return float(f"{x:.6g}")


def f32s(ar, off, n):
    return [rf(v) for v in struct.unpack(">%df" % n, bytes(ar.data[off:off + 4 * n]))]


def ptr(ar, off):
    return ar.u32(off) if off in ar.reloc_set else None


def cstr(ar, off):
    end = ar.data.index(b"\0", off)
    return bytes(ar.data[off:end]).decode("ascii", "replace")


def read_parts(co):
    r = co.public("ftLoadCommonData")
    table = co.u32(co.u32(r + 16) + 4 * KIND)
    j2p, count = co.u32(table), co.u32(table + 8)
    joint_to_part = list(co.data[j2p:j2p + count])
    holes = []
    entry = ptr(co, co.u32(r + 20) + 4 * KIND)
    if entry is not None:
        arr, n = co.u32(entry), co.u32(entry + 4)
        holes = [co.data[arr + 4 * i] for i in range(n)]
    return joint_to_part, set(holes), count


def read_joints(nr):
    """Depth-first JObj walk, the order the ftParts walk and the figatrees use."""
    joints = []

    def walk(off, parent):
        while off is not None:
            flags = nr.u32(off + 4)
            inv = ptr(nr, off + 0x38)
            j = {"index": len(joints), "parent": parent, "flags": flags,
                 "rot": f32s(nr, off + 0x14, 3), "scale": f32s(nr, off + 0x20, 3),
                 "trans": f32s(nr, off + 0x2C, 3),
                 "inverse_bind": f32s(nr, inv, 12) if inv is not None else None,
                 "has_mesh": ptr(nr, off + 0x10) is not None and not flags & (1 << 5)}
            joints.append(j)
            child = ptr(nr, off + 8)
            if child is not None and not flags & (1 << 12):
                walk(child, j["index"])
            off = ptr(nr, off + 0xC)

    walk(nr.public("PlyKirby5K_Share_joint"), None)
    return joints


def submotion_names():
    names = []
    for path, enum, prefix, drop in (
            ("ft/kinds/ftCommon/forward.h", "ftCo_Submotion", "ftCo_SM_", ("None", "Count")),
            ("ft/kinds/ftKirby/forward.h", "ftKb_Submotion", "ftKb_SM_", ("Count", "SelfCount"))):
        text = open(os.path.join(SRC, path), encoding="utf-8").read()
        block = text[text.index("typedef enum %s {" % enum):]
        block = block[:block.index("} %s;" % enum)]
        names += [n for n in re.findall(prefix + r"(\w+)", block) if n not in drop]
    return names


def read_motions(pl, aj_raw, names):
    root = pl.public("ftDataKirby")
    table = ptr(pl, root + 0xC)
    rows = []
    for i, dn in enumerate(names):
        o = table + i * 0x18
        name_p, script = ptr(pl, o), ptr(pl, o + 0xC)
        w = [pl.u32(o + 4 * k) for k in range(6)]
        fig = cstr(pl, name_p) if name_p is not None else None
        frames = joint_count = None
        if fig and w[2]:
            sub = mex_hsd.Archive(aj_raw[w[1]:w[1] + w[2]])
            tree = sub.publics[0][1]
            joint_count = sub.u32(tree + 4)
            frames = rf(struct.unpack(">f", bytes(sub.data[tree + 8:tree + 12]))[0])
        rows.append({"index": i, "decomp": dn, "figatree": fig, "offset": w[1], "size": w[2],
                     "script": script, "flags": w[4], "frames": frames, "joint_count": joint_count})
    return rows


def main():
    iso = os.environ.get("GW_ISO_VANILLA")
    if not iso:
        sys.exit("GW_ISO_VANILLA is not set (source .env)")
    disc = mex_hsd.Gcm(iso)
    raw = {n: disc.read(n) for n in ("PlCo.dat", "PlKb.dat", "PlKbNr.dat", "PlKbAJ.dat")}
    co, pl, nr = (mex_hsd.Archive(raw[n]) for n in ("PlCo.dat", "PlKb.dat", "PlKbNr.dat"))

    joint_to_part, holes, parts_num = read_parts(co)
    joints = read_joints(nr)
    slot, part = [], 0
    for _ in joints:
        while part in holes:
            part += 1
        slot.append(part)
        part += 1
    if part != parts_num:
        sys.exit(f"part walk ends at {part}, table says {parts_num}")

    ev = ["ev:disc", "ev:plco"]
    ir_joints, roles, part_slots = [], [], []
    for j, s in zip(joints, slot):
        common = joint_to_part[s]
        cname = COMMON[common] if common < len(COMMON) else None
        traits = [t for bit, t in FLAG_TRAITS if j["flags"] & bit]
        if j["parent"] is None:
            traits.insert(0, "skeleton_root")
        if j["inverse_bind"]:
            traits.append("has_inverse_bind")
        joint = {"index": j["index"], "name": None, "parent": j["parent"],
                 "rest": {"translation": j["trans"], "rotation_euler_rad": j["rot"],
                          "scale": j["scale"]},
                 "traits": traits, "raw_flags": "0x%08X" % j["flags"]}
        part_slots.append({"joint": j["index"], "part_slot": s, "common_part": cname,
                           "has_mesh": j["has_mesh"]})
        if j["inverse_bind"]:
            joint["inverse_bind"] = j["inverse_bind"]
        if cname:
            joint["role_guess"] = ROLE.get(cname, cname)
            joint["provenance"] = prov("verified", *ev, note=f"part slot {s} -> common part {common} {cname}")
            if cname in ROLE:
                roles.append({"role": ROLE[cname], "joint": j["index"], "skeleton": SKEL,
                              "engine_index": {"space": "melee.common_part", "value": common},
                              "provenance": prov("verified", *ev, note=f"{cname}, part slot {s}")})
        else:
            joint["provenance"] = prov("verified", "ev:disc", note=f"part slot {s}: no common part; role unknown")
        ir_joints.append(joint)

    motions = read_motions(pl, raw["PlKbAJ.dat"], submotion_names())
    clips, clip_ids, subactions = [], {}, []
    for m in motions:
        sub_id = f"subaction:{m['index']}"
        clip_ref = None
        if m["figatree"]:
            clip_ref = clip_ids.get(m["figatree"])
            if clip_ref is None:
                action = re.search(r"_ACTION_(\w+?)_figatree", m["figatree"])
                clip_ref = f"clip:{action.group(1) if action else m['index']}"
                if clip_ref in clip_ids.values():
                    clip_ref += f"@{m['offset']:X}"
                clip_ids[m["figatree"]] = clip_ref
                clips.append({"id": clip_ref, "name": clip_ref[5:], "symbol": m["figatree"],
                              "file": "file:plkbaj", "offset": "0x%X" % m["offset"], "size": m["size"],
                              "frames": m["frames"],
                              "authored_for": {"skeleton": SKEL if m["flags"] & 0x3F == KIND else None,
                                               "engine_kind": {"space": "melee.retail.fighter_kind",
                                                               "value": m["flags"] & 0x3F},
                                               "joint_count": m["joint_count"]},
                              "used_by": [], "provenance": prov("verified", "ev:disc")})
                if clips[-1]["authored_for"]["skeleton"] is None:
                    del clips[-1]["authored_for"]["skeleton"]
            next(c for c in clips if c["id"] == clip_ref)["used_by"].append(sub_id)
        sub = {"id": sub_id, "index": {"space": "melee.subaction_id", "value": m["index"]},
               "name": m["decomp"], "clip": clip_ref, "empty": clip_ref is None,
               "flags": {"raw": "0x%08X" % m["flags"]},
               "provenance": prov("verified", "ev:disc", "ev:decomp")}
        if m["script"] is not None:
            sub["engine"] = {"melee.gc": {"script_offset": "0x%X" % m["script"]}}
        subactions.append(sub)

    files = []
    for name, role in (("PlKb.dat", "fighter_data"), ("PlKbNr.dat", "costume_model"),
                       ("PlKbAJ.dat", "animation_bank"), ("PlCo.dat", "other")):
        files.append({"id": "file:" + name[:-4].lower(), "name": name, "role": role,
                      "size": len(raw[name]), "sha256": hashlib.sha256(raw[name]).hexdigest(),
                      "container": {"format": "hsd_archive", "endianness": "big"},
                      "provenance": prov("verified", "ev:disc")})

    unknown = [j["index"] for j in ir_joints if "role_guess" not in j]
    doc = {
        "ir_version": "0.1.0",
        "document_id": "kirby.melee",
        "subject": {"character": "Kirby", "game": "ssbm", "engine": "melee.gc",
                    "distribution": {"name": "Super Smash Bros. Melee NTSC 1.02", "kind": "retail",
                                     "media": "GW_ISO_VANILLA"},
                    "analysed_with": [{"tool": "ports/ir/tools/build_kirby_melee.py"}],
                    "notes": "Retarget target for ports/kirby-ultimate. Skeleton, part roles and the "
                             "motion table only; attributes and scripts are in the brawl-kirby dump."},
        "evidence": [
            {"id": "ev:disc", "kind": "disc_image", "path": "GW_ISO_VANILLA",
             "note": "PlKb.dat, PlKbNr.dat, PlKbAJ.dat read directly"},
            {"id": "ev:plco", "kind": "disc_image", "path": "GW_ISO_VANILLA:PlCo.dat",
             "note": "ftLoadCommonData[4] parts table and [5] placeholder slots for internal kind 4; "
                     "slot assignment follows ftParts_80074B0C's walk (melee/src/melee/ft/ftparts.c)"},
            {"id": "ev:decomp", "kind": "decomp", "path": "melee/src/melee/ft/kinds/ftKirby/forward.h",
             "note": "submotion names (ftCo_Submotion + ftKb_Submotion)"}],
        "identity": {"names": {"display": {"en": "Kirby"}, "internal": ["Kirby", "Kb"], "series": "Kirby"},
                     "indices": [{"space": "melee.retail.fighter_kind", "value": KIND, "stability": "stable",
                                  "provenance": prov("verified", "ev:decomp")}],
                     "provenance": prov("verified", "ev:disc")},
        "resources": {"files": files},
        "assets": {
            "skeletons": [{"id": SKEL, "name": "PlyKirby5K_Share_joint", "file": "file:plkbnr",
                           "symbol": "PlyKirby5K_Share_joint", "joint_count": len(ir_joints),
                           "order": "depth_first", "joints": ir_joints,
                           "engine": {"melee.gc": {"part_slots": part_slots,
                                                   "placeholder_part_slots": sorted(holes)}},
                           "provenance": prov("verified", *ev, note=(
                               "Euler rotation is HSD's X then Y then Z (R = Rz*Ry*Rx), radians; "
                               "matrices compose parent * T * R * S with classical scale on every joint "
                               "that has the trait. Joints without a common part: %s." % unknown))}],
            "bone_roles": roles,
            "animations": {"container": "file:plkbaj",
                           "indexing": "ftDataKirby+0xC motion table: (figatree symbol, offset, size) per "
                                       "subaction row; the low 6 bits of the row flags name the authoring "
                                       "fighter kind",
                           "clips": clips,
                           "stats": {"clips": len(clips), "subaction_rows": len(subactions),
                                     "rows_without_clip": sum(s["empty"] for s in subactions)},
                           "provenance": prov("verified", "ev:disc")}},
        "behavior": {"subactions": subactions},
        "issues": [
            {"id": "issue:fighter_part_enum", "title": "Decomp Fighter_Part enum is one short of PlCo's common part ids",
             "layer": "ir", "severity": "latent", "status": "open",
             "description": "PlCo joint_to_part for Kirby uses ids up to 53; ft/forward.h Fighter_Part ends at 52 "
                            "(TransN2) and has no WaistB. This file names ids from 16 on with WaistB inserted, "
                            "so 52 is ThrowN (Kirby's joint for it hangs off YRotN). Confirm against the "
                            "ftCommon part-name table before relying on ids 16+.",
             "provenance": prov("inferred", "ev:plco", "ev:decomp")},
            {"id": "issue:unnamed_joints", "title": "%d joints have no common part" % len(unknown),
             "layer": "content", "severity": "info", "status": "open",
             "description": "Joints %s get no role from the parts table (Kirby's body, face and mouth "
                            "joints and two leg ends). Their roles need a model or animation inspection." % unknown,
             "provenance": prov("verified", "ev:plco")}],
        "coverage": {
            "identity": {"status": "summary"},
            "resources": {"status": "summary", "note": "the four files the skeleton and motions come from"},
            "assets.skeletons": {"status": "complete"},
            "assets.animations": {"status": "summary", "note": "clip index, frames, authoring kind and "
                                                              "joint count; keys are not decoded"},
            "behavior.subactions": {"status": "complete", "note": "rows, clips, script offsets and flags"},
            "behavior.actions": {"status": "absent"},
            "behavior.attributes": {"status": "absent", "note": "see experiment/brawl-kirby/analysis/melee_kirby.json"}},
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1)
    print(f"{OUT}: {len(ir_joints)} joints, {len(roles)} roles, {len(clips)} clips, "
          f"{len(subactions)} subactions; joints without a role: {unknown}")


if __name__ == "__main__":
    main()
