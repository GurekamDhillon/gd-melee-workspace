#!/usr/bin/env python3
"""authored_fighter.py - an AUTHORED fighter (glTF + manifest/skeleton/hurtbox JSON) -> the engine's inputs.

    python ports/ir/tools/authored_fighter.py mesh <art dir> <out dir> [--scale S]

<art dir> is a folder such as ports/vanilla-original/ (courier.glb under out/, textures under out/tex/,
manifest.json, skeleton.json, hurtboxes.json). Nothing here reads a game file: the input is original art and
the output is original data. Writes, under <out dir> (a build product, never committed):

    plan.json              the joint plan (TopN, TransN, XRotN, YRotN synthesized; depth-first order), the
                           Melee common-part table, role -> joint index, hurtboxes and ECB in joint-local space
    mesh_<costume>.json    the neutral mesh JSON that `fighterbuild build --authored` consumes, one per costume

glTF Y-up facing +Z is HSD model space, so no axis change is made (verified by skeleton.json: the toe bones
are at +Z). Scale is one uniform factor applied to translations, vertex positions and inverse binds.

Credit: glTF 2.0 (Khronos); the joint/parts planning is plan_parts.py (this repo).
"""
import argparse, re
import base64
import json
import math
import os
import struct
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import plan_parts  # noqa: E402
import figatree as F  # noqa: E402

# Courier role/bone -> Melee common part (plan_parts.COMMON). Bones not listed stay plain joints.
COMMON_OF = {
    "trans": "TransN", "hips": "HipN", "spine": "WaistN", "chest": "BustN", "neck": "NeckN", "head": "HeadN",
    "clavicle_L": "LShoulderN", "upperarm_L": "LShoulderJ", "forearm_L": "LArmJ", "hand_L": "LHandN",
    "thumb_L": "LThumbNa", "fingers_L": "L1stNa",
    "clavicle_R": "RShoulderN", "upperarm_R": "RShoulderJ", "forearm_R": "RArmJ", "hand_R": "RHandN",
    "thumb_R": "RThumbNa", "fingers_R": "R1stNa",
    "thigh_L": "LLegJ", "shin_L": "LKneeJ", "foot_L": "LFootJ",
    "thigh_R": "RLegJ", "shin_R": "RKneeJ", "foot_R": "RFootJ",
    "socket_item_R": "RHaveN", "shield_origin": "ThrowN",
}


def read_glb(path):
    b = open(path, "rb").read()
    jl = struct.unpack_from("<I", b, 12)[0]
    g = json.loads(b[20:20 + jl])
    off = 20 + jl
    bl, bt = struct.unpack_from("<II", b, off)
    assert bt == 0x004E4942
    return g, b[off + 8: off + 8 + bl]


def accessor(g, bin_, i):
    a = g["accessors"][i]
    bv = g["bufferViews"][a["bufferView"]]
    nc = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}[a["type"]]
    dt = {5126: "<f4", 5125: "<u4", 5123: "<u2", 5121: "u1"}[a["componentType"]]
    isz = np.dtype(dt).itemsize
    stride = bv.get("byteStride", nc * isz)
    base = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    if stride == nc * isz:
        arr = np.frombuffer(bin_, dtype=dt, count=a["count"] * nc, offset=base)
    else:
        arr = np.stack([np.frombuffer(bin_, dtype=dt, count=nc, offset=base + k * stride) for k in range(a["count"])])
    return arr.reshape(a["count"], nc) if nc > 1 else arr.reshape(a["count"])


def quat_to_mat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def mat_to_euler_zyx(r):
    """HSD: R = Rz * Ry * Rx (radians). Returns (rx, ry, rz)."""
    sy = -r[2][0]
    sy = max(-1.0, min(1.0, sy))
    ry = math.asin(sy)
    if abs(sy) < 0.999999:
        rx = math.atan2(r[2][1], r[2][2])
        rz = math.atan2(r[1][0], r[0][0])
    else:  # gimbal lock: put it all on Z
        rx = 0.0
        rz = math.atan2(-r[0][1], r[1][1])
    return rx, ry, rz


def quat_to_euler(q):
    return mat_to_euler_zyx(quat_to_mat(q))


def build_plan(art, scale):
    g, binary = read_glb(os.path.join(art, "out", "courier.glb"))
    nodes = g["nodes"]
    skin = g["skins"][0]
    jn = skin["joints"]                         # glTF node indices, skin.joints order
    skin_pos = {n: i for i, n in enumerate(jn)}
    parent_node = {}
    for i, n in enumerate(nodes):
        for c in n.get("children", []):
            parent_node[c] = i
    # source joint list for plan_parts: skin order, parent = skin index of the parent node
    src = []
    for i, n in enumerate(jn):
        p = parent_node.get(n)
        src.append({"index": i, "name": nodes[n]["name"], "parent": skin_pos.get(p), "node": n})
    # synthesize XRotN under `trans` (hips and its siblings move under it; plan_parts adds YRotN)
    trans_i = next(j["index"] for j in src if j["name"] == "trans")
    xrot = {"index": len(src), "name": "XRotN", "parent": trans_i, "node": None}
    for j in src:
        if j["parent"] == trans_i:
            j["parent"] = xrot["index"]
    src.append(xrot)
    doc = {"document_id": "authored", "assets": {"skeletons": [{"joints": [
        {"index": j["index"], "name": ("Headdress" if j["name"] == "head_top" else j["name"]), "parent": j["parent"]}
        for j in src]}], "bone_roles": []}}
    common = dict(COMMON_OF)
    common["XRotN"] = "XRotN"
    for j in src:
        c = common.get(j["name"])
        if c:
            doc["assets"]["bone_roles"].append({"joint": j["index"], "provenance": {"note": "Melee common part " + c}})
    pl = plan_parts.plan(doc)
    # world rest matrices (glTF node space, Y-up +Z, no armature transform on the scene root)
    local = {}
    for n in range(len(nodes)):
        nd = nodes[n]
        t = np.array(nd.get("translation", [0, 0, 0]), dtype=float) * scale
        q = nd.get("rotation", [0, 0, 0, 1])
        m = np.eye(4)
        m[:3, :3] = quat_to_mat(q)          # node scale is 1 +- 1e-7 everywhere (validated by the art lane)
        m[:3, 3] = t
        local[n] = m
    world = {}

    def wm(n):
        if n in world:
            return world[n]
        p = parent_node.get(n)
        world[n] = (wm(p) if p is not None else np.eye(4)) @ local[n]
        return world[n]

    joints = []
    for pj in pl["joints"]:
        if pj["synthesized"]:
            # a synthesized joint is identity locally; its world is its parent's world (identity at TopN)
            joints.append({"name": pj["name"], "parent": pj["parent"], "local": np.eye(4), "synth": True})
        else:
            node = src[pj["source"]]["node"]
            if node is None:                      # XRotN, synthesized by this adapter
                joints.append({"name": pj["name"], "parent": pj["parent"], "local": np.eye(4), "synth": True})
                continue
            joints.append({"name": pj["name"] if pj["name"] != "Headdress" else "head_top", "parent": pj["parent"],
                           "local": local[node], "node": node, "synth": False})
    # a source joint whose parent in glTF differs from plan parent only through synthesized identities, so
    # the local transform is unchanged; world = chain of plan locals
    for i, j in enumerate(joints):
        j["world"] = (joints[j["parent"]]["world"] if j["parent"] is not None else np.eye(4)) @ j["local"]
    # consistency with glTF world for source joints
    err = max(float(np.abs(j["world"] - wm(j["node"])).max()) for j in joints if not j["synth"])
    assert err < 1e-4, "plan world differs from glTF world: %g" % err
    return g, binary, pl, joints, skin_pos, jn, src, err


def _row_clips(manifest):
    """Animation ROW number (the engine's ftCo_SM_ subaction numbers) -> clip name, by the row's name: rows no motion state names are still
    played by number (the fall blend plays the FallF / FallB rows), so the engine needs a clip for every row. Names come from the decomp's
    own enum (source, not disc data); a row whose name matches no motion row or clip is None (the engine then plays Wait)."""
    gw = os.environ.get("GW_MELEE") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "melee")
    src = os.path.join(gw, "src", "melee", "ft", "kinds", "ftCommon", "forward.h")
    try:
        text = open(src, encoding="utf-8", errors="replace").read()
    except OSError:
        return []
    i = text.index("ftCo_SM_")
    body = text[text.rfind("typedef enum", 0, i):text.index("}", i)]
    names = [n for n, _ in re.findall(r"\b(ftCo_SM_\w+)\s*(=\s*[^,]+)?,", body)][1:]       # [0] is ftCo_SM_None = -1
    rowclip = {m["row"]: m["clip"] for m in manifest["motion_rows"] if m.get("clip")}
    clips = {c["name"] for c in manifest["clips"]}
    out = []
    for n in names:
        k = n[len("ftCo_SM_"):]
        out.append(rowclip.get(k) or (k if k in clips else None))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["mesh", "anim"])
    ap.add_argument("art")
    ap.add_argument("out")
    ap.add_argument("--scale", type=float, default=1.0)
    a = ap.parse_args()
    art, out, scale = a.art, a.out, a.scale
    os.makedirs(out, exist_ok=True)
    if a.cmd == "anim":
        return anim_main(art, out, scale)
    manifest = json.load(open(os.path.join(art, "manifest.json"), encoding="utf-8"))
    hurt = json.load(open(os.path.join(art, "hurtboxes.json"), encoding="utf-8"))
    g, binary, pl, joints, skin_pos, jn, src, err = build_plan(art, scale)
    name_to_plan = {j["name"]: i for i, j in enumerate(joints)}
    # skin joint index -> plan index
    skin_to_plan = [name_to_plan[g["nodes"][n]["name"]] for n in jn]

    # ---- joints for fighterbuild
    mj = []
    for i, j in enumerate(joints):
        loc = j["local"]
        rx, ry, rz = mat_to_euler_zyx(loc[:3, :3])
        inv = np.linalg.inv(j["world"])
        mj.append({"name": j["name"], "parent": -1 if j["parent"] is None else j["parent"],
                   "scale": [1.0, 1.0, 1.0], "rot": [rx, ry, rz], "trans": [float(x) for x in loc[:3, 3]],
                   "ibm": [float(x) for x in inv[:3, :].reshape(-1)]})
    # ---- geometry
    prim = g["meshes"][0]["primitives"][0]
    pos = accessor(g, binary, prim["attributes"]["POSITION"]).astype(float) * scale
    nrm = accessor(g, binary, prim["attributes"]["NORMAL"]).astype(float)
    uv = accessor(g, binary, prim["attributes"]["TEXCOORD_0"]).astype(float)
    jts = accessor(g, binary, prim["attributes"]["JOINTS_0"]).astype(int)
    wts = accessor(g, binary, prim["attributes"]["WEIGHTS_0"]).astype(float)
    idx = accessor(g, binary, prim["indices"]).astype(int)
    verts = []
    for v in range(len(pos)):
        w = [[skin_to_plan[int(jts[v][k])], float(wts[v][k])] for k in range(4) if wts[v][k] > 1e-6]
        s = sum(x[1] for x in w)
        w = [[x[0], x[1] / s] for x in w]
        if len(w) > 2:
            raise SystemExit("vertex %d has %d influences; the Courier contract is at most 2" % (v, len(w)))
        # merge duplicate joints
        merged = {}
        for jx, wx in w:
            merged[jx] = merged.get(jx, 0) + wx
        w = [[k, v2] for k, v2 in merged.items()]
        verts.append({"p": [float(x) for x in pos[v]], "n": [float(x) for x in nrm[v]], "uv": [float(uv[v][0]), float(uv[v][1])], "w": w})
    tris = [[verts[idx[i]], verts[idx[i + 1]], verts[idx[i + 2]]] for i in range(0, len(idx), 3)]
    costumes = [c["name"] for c in manifest["costumes"]]
    for cname in costumes:
        png = Image.open(os.path.join(art, "out", "tex", "costume_%s.png" % cname)).convert("RGBA")
        w, h = png.size
        mesh = {"joints": mj,
                "textures": [{"name": "costume_" + cname, "w": w, "h": h, "fmt": "RGBA8",
                              "rgba": base64.b64encode(png.tobytes()).decode()}],
                "dobjs": [{"object": "Courier", "subindex": 0, "group": None, "textures": ["costume_" + cname],
                           "wrap": [["ClampToEdge", "ClampToEdge"]],
                           "cull": "Cull_Outside", "xlu": False, "tris": tris}]}
        json.dump(mesh, open(os.path.join(out, "mesh_%s.json" % cname), "w"))
    # ---- plan: roles and local hurtboxes
    roles = {}
    for b in manifest["bones"]:
        roles.setdefault(b["role"], []).append(name_to_plan[b["name"]])
    by_name = {b: i for i, b in enumerate(j["name"] for j in joints)}

    def local_pt(bone, pt):
        j = joints[by_name[bone]]
        inv = np.linalg.inv(j["world"])
        p = inv @ np.array([pt[0] * scale, pt[1] * scale, pt[2] * scale, 1.0])
        return [round(float(x), 5) for x in p[:3]]

    hb = []
    for h in hurt["hurtboxes"]:
        hb.append({"id": h["id"], "joint": by_name[h["bone"]], "bone": h["bone"], "a": local_pt(h["bone"], h["a_gltf"]),
                   "b": local_pt(h["bone"], h["b_gltf"]), "radius": round(h["radius"] * scale, 5),
                   "height": h["height"], "grabbable": h["grabbable"]})
    plan = {"scale": scale, "joint_count": len(joints), "row_clips": _row_clips(manifest), "joints": [{"index": i, "name": j["name"], "parent": j["parent"], "synth": j["synth"]} for i, j in enumerate(joints)],
            "parts": pl["parts"], "ftdata": pl["ftdata"], "unresolved": pl["unresolved"],
            "roles": roles, "role_joint": {b["name"]: name_to_plan[b["name"]] for b in manifest["bones"]},
            "hurtboxes": hb, "ecb": {k: (v if not isinstance(v, dict) else {kk: (vv * scale if isinstance(vv, (int, float)) else vv) for kk, vv in v.items()}) for k, v in hurt["ecb"].items() if k != "notes"},
            "costumes": costumes, "world_check_error": err}
    json.dump(plan, open(os.path.join(out, "plan.json"), "w"), indent=1)
    print("authored_fighter: %d plan joints (+%s), %d tris, %d costumes, unresolved %s" %
          (len(joints), pl["synthesized"], len(tris), len(costumes), [u.get("common_part") or u.get("role") for u in pl["unresolved"]]))


# ------------------------------------------------------------------------------------------------- animation bank
FRAC_ROT = (1 << 5) | 12      # s16, 1/4096 rad (0.014 deg)
SYMBOL_FMT = "PlyCourier_Share_ACTION_%s_figatree"


def _unwrap_euler(qs):
    """quaternions (n,4) -> (n,3) HSD euler angles, each frame on the branch nearest the previous."""
    out = []
    prev = None
    for q in qs:
        rx, ry, rz = quat_to_euler(q)
        cands = []
        for (ax, ay, az) in ((rx, ry, rz), (rx + math.pi, math.pi - ry, rz + math.pi)):
            for kx in (-1, 0, 1):
                for ky in (-1, 0, 1):
                    for kz in (-1, 0, 1):
                        cands.append((ax + 2 * math.pi * kx, ay + 2 * math.pi * ky, az + 2 * math.pi * kz))
        if prev is None:
            e = (rx, ry, rz)
        else:
            e = min(cands, key=lambda c: (c[0] - prev[0]) ** 2 + (c[1] - prev[1]) ** 2 + (c[2] - prev[2]) ** 2)
        out.append(e)
        prev = e
    return np.array(out)


def _encode_channel(vals, frac):
    """one value per frame -> (obj-independent key bytes, fv, fs)."""
    vals = [float(v) for v in vals]
    if frac is not None and max(abs(v) for v in vals) > 7.9 and (frac >> 5) == 1:
        frac = (1 << 5) | 10           # s16 holds +-8 rad at 1/4096; a channel that unwraps past a turn and a half (a scarf in a thrown clip) takes 1/1024 (+-32 rad)
    if max(vals) - min(vals) < 1e-5:
        # NOT a single CON key: the engine's FObj state machine takes a key's interpolation op from the key BEFORE
        # it (fobj.c FObjLoadData: op_intrp = op, then op is parsed), so a one-key track ends in state 6 with
        # op_intrp 0 and writes an UNINITIALISED value (0) to the joint every frame. Measured: every constant
        # channel zeroed its joint's rotation / translation (thigh rest pi lost, hips height lost). Two LIN keys with
        # the same value hold it, the way a retail track would.
        pts = [(0, vals[0], 0.0), (max(1, len(vals) - 1), vals[0], 0.0)]
        body, fv, fs, _ = F.encode_mixed_spline(pts, [F.LIN] * 2, frac)
        return body, fv, fs
    pts = [(i, v, 0.0) for i, v in enumerate(vals)]
    body, fv, fs, _ = F.encode_mixed_spline(pts, [F.LIN] * len(pts), frac)
    return body, fv, fs


def anim_main(art, out, scale):
    g, binary, pl, joints, skin_pos, jn, src, err = build_plan(art, scale)
    manifest = json.load(open(os.path.join(art, "manifest.json"), encoding="utf-8"))
    nodes = g["nodes"]
    name_to_plan = {j["name"]: i for i, j in enumerate(joints)}
    bank = bytearray()
    clip_root_motion = {c["name"]: bool(c.get("root_motion")) for c in manifest["clips"]}
    rows = {}
    worst = 0.0
    for an in g["animations"]:
        chans = {}
        for ch in an["channels"]:
            tgt = nodes[ch["target"]["node"]]["name"]
            path = ch["target"]["path"]
            if path == "scale" or tgt not in name_to_plan:
                continue
            smp = an["samplers"][ch["sampler"]]
            times = accessor(g, binary, smp["input"]).astype(float)
            vals = accessor(g, binary, smp["output"]).astype(float)
            chans[(tgt, path)] = (times, vals)
        nframes = max(len(t) for t, _ in chans.values())
        tracks = []
        for j in joints:                                   # plan order == depth-first == figatree track order
            jt = []
            nm = j["name"]
            if not j["synth"] and (nm, "rotation") in chans:
                t, q = chans[(nm, "rotation")]
                assert len(t) == nframes, (an["name"], nm, len(t), nframes)
                eul = _unwrap_euler(q)
                for k, ty in enumerate((1, 2, 3)):       # ROTX, ROTY, ROTZ
                    body, fv, fs = _encode_channel(eul[:, k], FRAC_ROT)
                    jt.append((ty, body, fv, fs))
            # The engine's animation step honours translation only on the translation parts (TransN, HipN and the
            # Melee root nodes): a translation track on any other joint zeroed that joint's offset in the game
            # (measured: every limb collapsed to the root). So: hips always, trans only in root-motion clips, nothing else.
            if not j["synth"] and (nm, "translation") in chans and (nm == "hips" or (nm == "trans" and clip_root_motion.get(an["name"]))):
                t, v = chans[(nm, "translation")]
                v = v * scale
                for k, ty in enumerate((5, 6, 7)):       # TRAX, TRAY, TRAZ
                    body, fv, fs = _encode_channel(v[:, k], None)
                    jt.append((ty, body, fv, fs))
            tracks.append(jt)
        sym = SYMBOL_FMT % an["name"]
        arc = F.build_tree_archive(sym, nframes - 1, tracks)
        # verify: decode and evaluate against the source at every frame (rotation: angle error in radians)
        _, tree = F.parse_archive(arc)
        for ji, j in enumerate(joints):
            nm = j["name"]
            if (nm, "rotation") in chans and not j["synth"]:
                t, q = chans[(nm, "rotation")]
                eul = _unwrap_euler(q)
                trk = {tr["type"]: tr for tr in tree["joints"][ji]}
                for f in range(0, nframes, max(1, nframes // 12)):
                    got = [F.evaluate(trk[ty]["keys"], f) for ty in (1, 2, 3)]
                    worst = max(worst, max(abs(got[k] - eul[f][k]) for k in range(3)))
        off = len(bank)
        bank += arc
        while len(bank) % 0x20:
            bank.append(0)
        rows[an["name"]] = {"symbol": sym, "frames": nframes, "offset": off, "bytes": len(arc),
                            "tracks": sum(len(t) for t in tracks)}
    open(os.path.join(out, "GnCourierAJ.dat"), "wb").write(bytes(bank))
    json.dump({"clips": rows, "bytes": len(bank), "max_euler_error_rad": worst, "tree_frames": "frames-1",
               "rot_precision": "s16 1/4096 rad", "plan_joints": len(joints)},
              open(os.path.join(out, "bank.json"), "w"), indent=1)
    pj = os.path.join(out, "plan.json")        # the engine reads ONE file: fold the bank and the row map into the plan
    if os.path.exists(pj):
        plan = json.load(open(pj, encoding="utf-8"))
        plan["bank"] = {"file": "GnCourierAJ.dat", "bytes": len(bank), "clips": rows}
        plan["motion_rows"] = [{"motion": r["motion"], "row": r["row"], "clip": r["clip"], "status": r["status"]}
                               for r in manifest["motion_rows"]]
        json.dump(plan, open(pj, "w"), indent=1)
    print("authored_fighter anim: %d clips, %d bytes, max euler error %.5f rad" % (len(rows), len(bank), worst))


if __name__ == "__main__":
    main()
